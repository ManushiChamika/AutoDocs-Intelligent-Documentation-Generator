from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.job import JobStatus


class ArtifactRead(BaseModel):
    id: str
    type: str
    title: str
    path: Optional[str] = None
    content: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    filename: str


class JobRead(BaseModel):
    id: str
    filename: str
    status: JobStatus
    progress: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    artifacts: List[ArtifactRead] = []

    model_config = {"from_attributes": True}


class JobList(BaseModel):
    items: List[JobRead]
    total: int
