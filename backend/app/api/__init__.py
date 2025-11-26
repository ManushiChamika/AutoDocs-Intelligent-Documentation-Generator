from fastapi import APIRouter

from app.api.routes import jobs
from app.api.routes import debug

api_router = APIRouter(prefix="/api")
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(debug.router, prefix="/debug", tags=["debug"])
