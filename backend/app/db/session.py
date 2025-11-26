from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
