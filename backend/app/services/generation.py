from __future__ import annotations

import textwrap
import zipfile
from pathlib import Path
from typing import Iterable, List

import logging

from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Artifact, Job, JobStatus
from app.utils.storage import artifact_path


def _read_code_snippets(upload_path: Path, limit: int = 4000) -> str:
    """
    Pull a small preview of the uploaded project. This keeps the demo snappy while
    still giving the LLM enough structure to produce plausible docs.
    """
    if upload_path.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(upload_path, "r") as zip_ref:
                snippets: list[str] = []
                for name in zip_ref.namelist():
                    if name.endswith("/") or len(snippets) > 6:
                        continue
                    try:
                        content = zip_ref.read(name).decode("utf-8", errors="ignore")
                        snippets.append(f"# File: {name}\n{content[:800]}")
                    except Exception:
                        continue
                return "\n\n".join(snippets)[:limit]
        except zipfile.BadZipFile:
            return upload_path.read_text(encoding="utf-8", errors="ignore")[:limit]
    return upload_path.read_text(encoding="utf-8", errors="ignore")[:limit]


def _llm():
    if not settings.openai_api_key:
        return None
    try:
        return ChatOpenAI(model=settings.model_name, temperature=0.4)
    except Exception as exc:
        # Some OpenAI client versions or environment setups may cause the
        # underlying client constructor to raise validation errors (for
        # example when unexpected kwargs like 'proxies' are forwarded).
        # Rather than crash the worker, log and fall back to the offline
        # generator so artifacts can still be created.
        logging.exception("Failed to initialize ChatOpenAI; falling back to offline: %s", exc)
        return None


def _fallback(title: str) -> str:
    return textwrap.dedent(
        f"""
        # {title}
        AutoDocs is ready to generate this artifact. Add an OPENAI_API_KEY and
        restart the worker to see live AI output.
        """
    ).strip()


def _generate_sections(project_context: str) -> dict[str, str]:
    llm = _llm()
    prompts = {
        "README": "Write a concise README with setup instructions and a feature list.",
        "API Docs": "Produce REST API docs with endpoints, parameters, and responses.",
        "UML": "Describe a high-level UML diagram in Mermaid syntax.",
        "Tests": "Suggest starter test cases covering the main user flows.",
        "Architecture": "Summarize the architecture, queues, and data stores.",
    }

    if not llm:
        return {title: _fallback(title) for title in prompts.keys()}

    artifacts: dict[str, str] = {}
    for title, instruction in prompts.items():
        message = (
            "You are AutoDocs, an assistant that drafts developer documentation.\n"
            "Use the provided code context to keep names accurate.\n\n"
            f"Project context:\n{project_context}\n\n"
            f"Task: {instruction}\nKeep output tight and actionable."
        )
        result = llm.invoke(message)
        artifacts[title] = result.content
    return artifacts


def run_generation_pipeline(db: Session, job: Job, upload_path: Path) -> List[Artifact]:
    context = _read_code_snippets(upload_path)
    sections = _generate_sections(context)

    created: List[Artifact] = []
    for title, content in sections.items():
        artifact = Artifact(
            job_id=job.id,
            type=title.lower().replace(" ", "_"),
            title=title,
            path=str(artifact_path(job.id, f"{title.lower().replace(' ', '_')}.md")),
            content=content,
        )
        # Persist to disk for quick downloads
        Path(artifact.path).parent.mkdir(parents=True, exist_ok=True)
        Path(artifact.path).write_text(content, encoding="utf-8")

        db.add(artifact)
        created.append(artifact)

    job.status = JobStatus.completed
    job.progress = 100
    return created
