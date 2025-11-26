from typing import List
from pathlib import Path as SysPath

from fastapi.responses import FileResponse
from fastapi import HTTPException, Request

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.core.config import settings
from app.models import Job, JobStatus
from app.schemas import JobList, JobRead
from app.utils.storage import save_upload
from app.workers.tasks import process_job

router = APIRouter()


@router.post("/upload", response_model=JobRead)
async def upload_codebase(
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
) -> JobRead:
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a name")

    filename, path = save_upload(file)

    job = Job(filename=filename, status=JobStatus.pending, progress=0)
    db.add(job)
    db.commit()
    db.refresh(job)

    process_job.delay(job.id, str(path))
    return JobRead.model_validate(job, from_attributes=True)


@router.get("", response_model=JobList)
async def list_jobs(db: Session = Depends(get_session)) -> JobList:
    statement = select(Job).order_by(Job.created_at.desc())
    # When relationships are eager-loaded against collections, SQLAlchemy
    # returns duplicate rows for parent objects. Call `unique()` to
    # de-duplicate results before calling `scalars().all()`.
    jobs: List[Job] = db.execute(statement).unique().scalars().all()
    return JobList(
        items=[JobRead.model_validate(job, from_attributes=True) for job in jobs],
        total=len(jobs),
    )


@router.get("/{job_id}/artifacts/{filename}")
async def download_artifact(job_id: str, filename: str, request: Request) -> FileResponse:
    """Serve a generated artifact file for download.

    Files are written to `settings.artifacts_dir/<job_id>/<filename>` by the worker.
    """
    artifacts_root = SysPath(settings.artifacts_dir)
    file_path = artifacts_root / job_id / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    # If a download token is configured, require Authorization: Bearer <token>
    token = settings.download_token
    if token:
        auth = request.headers.get("authorization") or ""
        if not auth.lower().startswith("bearer ") or auth.split(None, 1)[1] != token:
            raise HTTPException(status_code=401, detail="Unauthorized")
    return FileResponse(path=str(file_path), filename=filename, media_type="application/octet-stream")


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: str, db: Session = Depends(get_session)) -> JobRead:
    job: Job | None = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobRead.model_validate(job, from_attributes=True)
