from app.db.session import SessionLocal
from app.models import Artifact
from sqlalchemy import select

DB = SessionLocal()
for a in DB.execute(select(Artifact)).scalars():
    print(a.id, a.job_id, a.type, a.path)
