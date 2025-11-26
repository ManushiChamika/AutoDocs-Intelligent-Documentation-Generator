from __future__ import annotations

import textwrap
import zipfile
from pathlib import Path
from typing import Iterable, List

import logging
import os
import sys
import re
import socket
from urllib.parse import urlparse

import openai
import time
import urllib.error
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Artifact, Job, JobStatus
from app.utils.storage import artifact_path


class RateLimitError(Exception):
    """Raised when the upstream LLM provider returns a rate limit (HTTP 429)."""
    pass


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


def _load_router_prefixes() -> dict[str, str]:
    """Parse app/api/__init__.py to extract router prefixes."""
    api_init = Path(__file__).resolve().parents[1] / "api" / "__init__.py"
    prefixes: dict[str, str] = {}
    if not api_init.exists():
        return prefixes
    text = api_init.read_text(encoding="utf-8", errors="ignore")
    pattern = r"include_router\(\s*(\w+)\.router,\s*prefix=['\"]([^'\"]*)['\"]"
    for match in re.finditer(pattern, text):
        module, prefix = match.groups()
        prefixes[module] = prefix
    return prefixes


def _discover_routes() -> list[str]:
    """Lightweight static scan of FastAPI route decorators for API listing."""
    routes_dir = Path(__file__).resolve().parents[1] / "api" / "routes"
    base_prefix = "/api"
    router_prefixes = _load_router_prefixes()
    found: set[str] = set()
    for path in routes_dir.glob("*.py"):
        module_name = path.stem
        router_prefix = router_prefixes.get(module_name, "")
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in re.finditer(r"@router\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]*)['\"]", text):
            method, route_path = match.groups()
            suffix = f"/{route_path.lstrip('/')}" if route_path else ""
            full_path = f"{base_prefix}{router_prefix}{suffix}"
            found.add(f"{method.upper()} {full_path}")
    return sorted(found)


def _summarize_structure() -> str:
    """Return a simple folder/role overview."""
    lines = [
        "backend/app/api - FastAPI routes (jobs upload/list/download, debug helpers)",
        "backend/app/models - SQLAlchemy models for Job and Artifact",
        "backend/app/schemas - Pydantic response schemas",
        "backend/app/services - generation pipeline and helpers",
        "backend/app/workers - Celery app + background tasks",
        "backend/app/utils - storage helpers",
        "backend/app/core - settings and config",
        "frontend/pages - Next.js routes for job list and artifact views",
        "frontend/components - shared UI pieces",
        "storage/uploads - uploaded zips",
        "storage/artifacts - generated docs",
    ]
    return "\n".join(f"- {line}" for line in lines)


def _static_sections(project_context: str) -> dict[str, str]:
    """Generate documentation without any LLM calls."""
    routes = _discover_routes()
    structure = _summarize_structure()
    route_lines = "\n".join(f"- {r}" for r in routes) if routes else "- (no routes discovered)"

    readme = textwrap.dedent(
        f"""
        # AutoDocs (Safe Mode)

        This run uses static analysis only - no LLM calls. The service still works as a
        full-stack documentation automation platform with background workers and file
        processing.

        ## What you get
        - API routes enumerated from the FastAPI codebase
        - Folder and service overview
        - Test skeletons to start coverage

        ## How it works
        1) A zip is uploaded via the jobs API.
        2) A Celery worker processes the upload and writes artifacts under `storage/artifacts/<job_id>/`.
        3) Artifacts are downloadable via the backend `GET /api/jobs/{{job_id}}/artifacts/{{filename}}` route.

        ## Running locally
        - Backend: `docker-compose up backend worker` (uses Postgres + Redis)
        - Frontend: `docker-compose up frontend` (Next.js)
        - Upload endpoint: `POST /api/jobs/upload` with a zip file

        If LLM access is restored, disable safe mode (`SAFE_MODE_NO_LLM=0`) to re-enable
        AI-generated drafts.
        """
    ).strip()

    api_docs = textwrap.dedent(
        f"""\
# API Endpoints (static scan)

{route_lines}

Notes:
- Upload: `POST /api/jobs/upload` accepts multipart file upload.
- Download artifacts: `GET /api/jobs/{{job_id}}/artifacts/{{filename}}`.
- Debug helpers live under `/api/debug` (sample enqueue, provider status).
"""
    ).strip()

    architecture = textwrap.dedent(
        f"""
        # Architecture (static)

        - FastAPI backend serving job CRUD and artifact download
        - Celery worker pulling jobs from Redis and writing artifacts to disk
        - Postgres for job + artifact metadata
        - Redis as broker/backend for Celery
        - Next.js frontend consuming the `/api` endpoints

        ## Folders
        {structure}

        ## Job lifecycle
        1) Upload: enqueue Celery task with file path
        2) Worker: parses project, generates docs, saves under `storage/artifacts/<job_id>/`
        3) Client: lists jobs via `GET /api/jobs` and downloads artifacts per job
        """
    ).strip()

    tests = textwrap.dedent(
        """
        # Test Skeletons (pytest)

        ```python
        import io
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        def test_upload_and_list_jobs(tmp_path, monkeypatch):
            # Upload a tiny zip
            content = io.BytesIO(b"PK\\x03\\x04")  # minimal zip header
            files = {"file": ("demo.zip", content, "application/zip")}
            resp = client.post("/api/jobs/upload", files=files)
            assert resp.status_code == 200
            job_id = resp.json()["id"]

            # Job should appear in listing
            resp = client.get("/api/jobs")
            assert any(job["id"] == job_id for job in resp.json()["items"])

        def test_download_requires_existing_artifact():
            resp = client.get("/api/jobs/fake/artifacts/missing.md")
            assert resp.status_code == 404
        ```
        """
    ).strip()

    uml = textwrap.dedent(
        """
        ```mermaid
        flowchart TD
          Uploader -->|POST /api/jobs/upload| Backend
          Backend -->|Enqueue| Celery[Celery Worker]
          Celery -->|Writes| Storage[(storage/artifacts/<job_id>)]
          Backend -->|GET /api/jobs| Client
          Client -->|Download artifact| Backend
        ```
        """
    ).strip()

    return {
        "README": readme,
        "API Docs": api_docs,
        "Architecture": architecture,
        "Tests": tests,
        "UML": uml,
    }


def _llm():
    if not settings.openai_api_key and not settings.openrouter_api_key:
        return None
    try:
        # Ensure no proxy envvars are leaked into the client constructors;
        # some HTTP clients try to translate those into kwargs which may not
        # be accepted by the installed versions.
        for _v in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            os.environ.pop(_v, None)
        # Prefer OpenRouter when configured; otherwise use OpenAI.
        if settings.openrouter_api_key and settings.openrouter_base_url:
            api_key = settings.openrouter_api_key
            api_base = settings.openrouter_base_url
        elif settings.openai_api_key:
            api_key = settings.openai_api_key
            api_base = None
        else:
            return None
        return ChatOpenAI(
            model=settings.model_name,
            temperature=0.4,
            openai_api_key=api_key,
            openai_api_base=api_base,
        )
    except Exception as exc:
        # Some OpenAI client versions or environment setups may cause the
        # underlying client constructor to raise validation errors (for
        # example when unexpected kwargs like 'proxies' are forwarded).
        # Rather than crash the worker, log and fall back to other methods
        # so artifacts can still be created.
        logging.exception("Failed to initialize ChatOpenAI: %s", exc)
        return None


def _invoke_openai_direct(prompt: str, model: str | None = None) -> str:
    """
    Use the installed `openai` package directly as a fallback when
    `ChatOpenAI` (LangChain) cannot initialize due to compatibility issues.
    Returns the assistant text output.
    """
    # Avoid proxy envvars leaking into the client constructors.
    for _v in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.pop(_v, None)

    # Allow overriding model for quick tests
    model_to_use = model or settings.model_name

    import json
    import urllib.request
    import socket
    from urllib.parse import urlparse

    # Select endpoint and key: prefer OpenRouter when configured.
    use_openrouter = bool(settings.openrouter_api_key and settings.openrouter_base_url)

    if use_openrouter:
        base = settings.openrouter_base_url.rstrip("/")
        url = f"{base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
    else:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
    payload = {
        "model": model_to_use,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 800,
    }

    # Retry/backoff on 429 to improve resilience for transient rate limits.
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
            data = json.loads(body)
            choice = data.get("choices", [])[0]
            msg = (choice.get("message") or {}) if isinstance(choice, dict) else None
            if isinstance(msg, dict) and msg.get("content"):
                return msg.get("content")
            return choice.get("text") or choice.get("content") or ""
        except urllib.error.HTTPError as he:
            if he.code == 429:
                if attempt < max_attempts:
                    wait = 2 ** attempt
                    logging.warning("OpenAI 429 rate limit (attempt %d/%d) - backing off %ds", attempt, max_attempts, wait)
                    time.sleep(wait)
                    continue
                # Exhausted attempts - surface a dedicated RateLimitError so callers
                # can choose to retry the job later instead of writing placeholders.
                logging.error("OpenAI rate limit exceeded after %d attempts", max_attempts)
                raise RateLimitError("Upstream rate limit (HTTP 429)") from he
            logging.exception("OpenAI HTTP error (code=%s) on attempt %d: %s", getattr(he, 'code', None), attempt, he)
            raise
        except Exception as exc:
            logging.exception("Direct openai invocation failed (http) on attempt %d: %s", attempt, exc)
            raise


def _fallback(title: str) -> str:
    return textwrap.dedent(
        f"""
        # {title}
        AutoDocs is ready to generate this artifact. Add an OPENAI_API_KEY and
        restart the worker to see live AI output.
        """
    ).strip()


def _generate_sections(project_context: str) -> dict[str, str]:
    prompts = {
        "README": "Write a concise README with setup instructions and a feature list.",
        "API Docs": "Produce REST API docs with endpoints, parameters, and responses.",
        "UML": "Describe a high-level UML diagram in Mermaid syntax.",
        "Tests": "Suggest starter test cases covering the main user flows.",
        "Architecture": "Summarize the architecture, queues, and data stores.",
    }

    artifacts: dict[str, str] = {}

    # Safe mode: skip LLMs entirely and return static, code-driven docs.
    if settings.safe_mode_no_llm:
        return _static_sections(project_context)

    llm = _llm()

    # If LangChain client is available, use it. Otherwise, if an API key
    # exists try calling the `openai` package directly as a fallback. If no
    # key is present, generate offline placeholders.
    if llm:
        for title, instruction in prompts.items():
            message = (
                "You are AutoDocs, an assistant that drafts developer documentation.\n"
                "Use the provided code context to keep names accurate.\n\n"
                f"Project context:\n{project_context}\n\n"
                f"Task: {instruction}\nKeep output tight and actionable."
            )
            try:
                result = llm.invoke(message)
                artifacts[title] = result.content
            except openai.RateLimitError as e:
                # Surface a controlled error so the Celery worker can retry later.
                raise RateLimitError("Upstream rate limit (HTTP 429)") from e
            except Exception as exc:
                # If the upstream call fails for any other reason, log and
                # fall back to placeholder content so the pipeline still
                # produces artifacts.
                logging.exception("ChatOpenAI call failed for %s: %s", title, exc)
                artifacts[title] = _fallback(title)
        return artifacts

    if settings.openai_api_key or settings.openrouter_api_key:
        # Try direct openai/openrouter calls per-prompt
        for title, instruction in prompts.items():
            prompt = (
                "You are AutoDocs, an assistant that drafts developer documentation.\n"
                "Use the provided code context to keep names accurate.\n\n"
                f"Project context:\n{project_context}\n\n"
                f"Task: {instruction}\nKeep output tight and actionable."
            )
            try:
                artifacts[title] = _invoke_openai_direct(prompt)
            except Exception as e:
                # If a rate limit occurred, propagate so the Celery task can retry
                if isinstance(e, RateLimitError):
                    raise
                artifacts[title] = _fallback(title)
        return artifacts

    # No LLM available and no API key configured - return offline placeholders.
    return {title: _fallback(title) for title in prompts.keys()}


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
