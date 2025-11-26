# AutoDocs – Full-Stack Documentation Generator

AutoDocs ingests a zip of your codebase, enqueues a background job, and emits developer docs (README, API docs, UML, tests, architecture). It runs as a full SaaS-style stack: FastAPI backend, Celery worker, Postgres, Redis, and a Next.js frontend. LLM output defaults to OpenRouter; OpenAI is used as a fallback.

## Stack
- Backend: FastAPI + SQLAlchemy + Pydantic Settings
- Worker: Celery (Redis broker/backend)
- DB/Cache: Postgres, Redis
- Frontend: Next.js
- LLM: OpenRouter (default) or OpenAI; safe mode can disable LLM calls

## Quick Start (Docker)
```bash
# Copy/adjust env
cp .env.example .env
# Start everything
docker-compose up -d
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

## Env Vars (key ones)
- `OPENROUTER_API_KEY` (recommended default)
- `OPENROUTER_BASE_URL` (default `https://openrouter.ai/api/v1`)
- `OPENAI_API_KEY` (fallback)
- `MODEL_NAME` (e.g., `gpt-3.5-turbo` or `gpt-4o-mini`)
- `SAFE_MODE_NO_LLM` (`false` to use LLMs; `true` for static offline output)
- `DATABASE_URL`, `REDIS_URL`
- `UPLOADS_DIR`, `ARTIFACTS_DIR`
- `DOWNLOAD_TOKEN` (optional Bearer token required for artifact downloads)

## API
- `POST /api/jobs/upload` – multipart file upload (zip); enqueues a job
- `GET /api/jobs` – list jobs
- `GET /api/jobs/{job_id}` – job status + artifacts
- `GET /api/jobs/{job_id}/artifacts/{filename}` – download an artifact (honors `DOWNLOAD_TOKEN` if set)
- Debug helpers:
  - `POST /api/debug/enqueue-sample` – enqueue sample zip
  - `POST /api/debug/reprocess-placeholders` – requeue placeholder artifacts
  - `GET /api/debug/provider` – provider config status

## How It Works
1) Upload a zip → backend saves to `UPLOADS_DIR` and enqueues `process_job`.
2) Celery worker reads the upload, gathers code snippets, calls LLM (or static mode), writes docs to `ARTIFACTS_DIR/<job_id>/`.
3) Frontend lists jobs; artifacts are downloadable via the backend.

## Development Notes
- Worker runs with `--concurrency=1` to reduce rate-limit risk.
- OpenRouter is preferred; if unreachable, the worker falls back to OpenAI when a key is present.
- Safe mode (`SAFE_MODE_NO_LLM=true`) produces deterministic, static docs without LLM calls.

## Troubleshooting
- 429 rate limits: lower concurrency (already 1), wait/retry, or use a higher-quota key.
- OpenRouter DNS issues: verify `OPENROUTER_BASE_URL` and connectivity from the container.
- Downloads 401: set `DOWNLOAD_TOKEN` in `.env` or omit the header when it’s blank.
- Celery warnings about broker retries are informational; set `broker_connection_retry_on_startup=True` if desired.

## Useful Commands
```bash
docker-compose logs -f backend
docker-compose logs -f worker
docker-compose exec backend poetry run alembic upgrade head  # if migrations are added
docker-compose up -d --force-recreate backend worker         # restart backend/worker
```
