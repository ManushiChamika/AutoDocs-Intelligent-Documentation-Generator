from pathlib import Path
from typing import Tuple

from fastapi import UploadFile

from app.core.config import settings


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_upload(upload: UploadFile) -> Tuple[str, Path]:
    uploads_root = Path(settings.uploads_dir)
    _ensure_dir(uploads_root)

    destination = uploads_root / upload.filename
    with destination.open("wb") as buffer:
        buffer.write(upload.file.read())

    return upload.filename, destination


def artifact_path(job_id: str, filename: str) -> Path:
    root = Path(settings.artifacts_dir) / job_id
    _ensure_dir(root)
    return root / filename
