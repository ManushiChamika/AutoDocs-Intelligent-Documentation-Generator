from app.db.session import SessionLocal
from app.models import Job, JobStatus
from app.workers.tasks import process_job

DB = SessionLocal()
job = Job(filename='sample_micro_saas.zip', status=JobStatus.pending, progress=0)
DB.add(job)
DB.commit()
DB.refresh(job)
print('Enqueued job id:', job.id)
process_job.delay(job.id, '/app/storage/uploads/sample_micro_saas.zip')
