from pathlib import Path
import socket

from fastapi import APIRouter, HTTPException, Depends

from app.core.config import settings
from app.db.session import get_session
from sqlalchemy.orm import Session
from app.models import Job, JobStatus, Artifact
from app.workers.tasks import process_job

router = APIRouter()


@router.get("/provider")
def provider_status():
    """Return whether OpenRouter is configured and resolvable, and if OpenAI key is present."""
    openrouter_configured = bool(settings.openrouter_api_key and settings.openrouter_base_url)
    openrouter_resolvable = False
    if openrouter_configured:
        try:
            host = settings.openrouter_base_url
            # parse host (allow full URL)
            from urllib.parse import urlparse

            parsed = urlparse(host)
            hostname = parsed.hostname or host
            socket.getaddrinfo(hostname, 443)
            openrouter_resolvable = True
        except Exception:
            openrouter_resolvable = False

    return {
        "openrouter_configured": openrouter_configured,
        "openrouter_resolvable": openrouter_resolvable,
        "openrouter_base_url": settings.openrouter_base_url,
        "openai_key_present": bool(settings.openai_api_key),
    }


@router.post("/enqueue-sample")
def enqueue_sample(db: Session = Depends(get_session)):
    """Enqueue a sample job using `sample_micro_saas.zip` in the uploads dir.

    This is a dev helper so you can trigger processing without running the
    requeue script inside the container.
    """
    upload_path = Path(settings.uploads_dir) / "sample_micro_saas.zip"
    # Try common container path as well
    if not upload_path.exists():
        alt = Path("/app") / settings.uploads_dir
        upload_path = alt / "sample_micro_saas.zip"

    if not upload_path.exists():
        raise HTTPException(status_code=404, detail=f"Sample upload not found at {upload_path}")

    job = Job(filename="sample_micro_saas.zip", status=JobStatus.pending, progress=0)
    db.add(job)
    db.commit()
    db.refresh(job)

    process_job.delay(job.id, str(upload_path))
    return {"enqueued_job_id": job.id}


@router.post("/reprocess-placeholders")
def reprocess_placeholders(db: Session = Depends(get_session)):
    """Find artifacts containing the offline placeholder text and re-enqueue
    their parent jobs for reprocessing.
    """
    placeholder = "AutoDocs is ready to generate this artifact."
    artifacts = db.query(Artifact).filter(Artifact.content.ilike(f"%{placeholder}%")).all()
    if not artifacts:
        return {"reprocessed": []}

    job_ids = {a.job_id for a in artifacts}
    enqueued = []
    for jid in job_ids:
        job = db.get(Job, jid)
        if not job:
            continue
        # mark pending and enqueue using uploads dir path
        job.status = JobStatus.pending
        job.progress = 0
        db.commit()
        upload_path = Path("/app") / settings.uploads_dir / job.filename
        process_job.delay(job.id, str(upload_path))
        enqueued.append(job.id)

    return {"reprocessed": enqueued}
