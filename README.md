# AutoDocs – Intelligent Documentation Generator

AI-driven micro SaaS that ingests a codebase and auto-generates a README, API docs, UML sketch, starter tests, and an architecture overview. Built to showcase a full-stack pipeline: FastAPI + Celery + Postgres/SQLAlchemy on the backend with a Next.js control room up front.

## Why it’s cool
- LLM-powered docs via LangChain + OpenAI
- Async queue with Celery + Redis for long-running work
- Postgres audit trail of jobs/artifacts via SQLAlchemy
- File uploads + background processing of real codebases
- Polished React/Next.js UI with live job polling

## Stack
- Backend: FastAPI, Celery, Redis, SQLAlchemy, Postgres
- AI: LangChain + OpenAI (model configurable)
- Frontend: Next.js (React + TypeScript), Axios

## Project layout
```
backend/
  app/
    api/            # FastAPI routers
    core/           # Settings
    db/             # Engine + session
    models/         # SQLAlchemy models
    schemas/        # Pydantic response models
    services/       # LangChain/OpenAI orchestration
    utils/          # File helpers
    workers/        # Celery config + tasks
    main.py         # FastAPI entrypoint
  requirements.txt
  Dockerfile
frontend/
  components/       # UI building blocks
  lib/              # API client helpers
  pages/            # Next.js pages (index + _app)
  styles/           # Global styles
  types/            # Shared TypeScript types
  package.json, Dockerfile, tsconfig.json, etc.
docker-compose.yml  # Postgres + Redis + backend + worker + frontend
.env.example        # Copy to .env and set secrets
storage/            # Uploads + generated artifacts (gitignored)
```

## Quick start (Docker)
1. `cp .env.example .env` and add a real `OPENAI_API_KEY`.
2. `docker-compose up --build` to launch Postgres, Redis, FastAPI, Celery worker, and Next.js UI.
3. Open http://localhost:3000, upload a `.zip` of a repo, and watch docs roll in. API lives at http://localhost:8000/docs.

## Local dev (without Docker)
### Backend + worker
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows
pip install -r backend/requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --app-dir backend
celery -A app.workers.celery_app worker --loglevel=info --workdir backend
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000/api` when running the frontend locally.

## Key endpoints
- `POST /api/jobs/upload` — upload a repo snapshot/zip, enqueue Celery job
- `GET /api/jobs` — list jobs and artifacts
- `GET /api/jobs/{job_id}` — job status detail

## Notes
- Without `OPENAI_API_KEY`, the worker returns friendly placeholder docs so the flow still demos end-to-end.
- Uploaded files and generated artifacts live under `storage/` (mounted in Docker and gitignored).
