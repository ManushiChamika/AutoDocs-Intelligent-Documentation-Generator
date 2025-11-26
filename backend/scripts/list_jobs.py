from app.db.session import SessionLocal
from app.models import Job
from sqlalchemy import select

DB = SessionLocal()
for j in DB.execute(select(Job)).scalars():
    print(j.id, j.filename, j.status, j.progress, j.error_message)
