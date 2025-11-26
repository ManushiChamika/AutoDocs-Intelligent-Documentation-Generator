from pathlib import Path

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Job, JobStatus
from app.services.generation import run_generation_pipeline
from app.workers.celery_app import celery_app
from app.services.generation import RateLimitError


@celery_app.task(bind=True, name="process_job", max_retries=5)
def process_job(self, job_id: str, upload_path: str) -> str:
    db: Session = SessionLocal()
    job: Job | None = None
    try:
        job = db.get(Job, job_id)
        if not job:
            return "job_not_found"

        job.status = JobStatus.processing
        job.progress = 5
        db.commit()

        run_generation_pipeline(db, job, Path(upload_path))
        db.commit()
        return "ok"
    except RateLimitError as rl:  # upstream rate limit — retry the task later
        # Requeue this Celery task with a backoff
        try:
            countdown = 60 * (self.request.retries + 1)
            self.retry(exc=rl, countdown=countdown)
        finally:
            db.close()
        # unreachable
    except Exception as exc:  # noqa: BLE001
        if job:
            job.status = JobStatus.failed
            job.error_message = str(exc)
            db.commit()
        raise
    finally:
        db.close()
