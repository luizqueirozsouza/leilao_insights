# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                                                              # install deps (Python 3.13+, requires uv)
uv run python backend_django/manage.py migrate                       # run migrations (needs .env + PostgreSQL)
uv run python backend_django/manage.py runserver                     # Django on :8000
uv run uvicorn backend_fastapi.main:app --host 0.0.0.0 --port 8001  # FastAPI on :8001

# Data pipeline
uv run python backend_django/manage.py sync_auctions --date YYYY-MM-DD --verbose   # combined extract + ingest
uv run python backend_django/manage.py extrai_auctions --date YYYY-MM-DD --verbose # download only
uv run python backend_django/manage.py ingest_auctions --date YYYY-MM-DD --verbose # load only

# Standalone scripts (alternative to management commands)
uv run python extrai.py --date YYYY-MM-DD --verbose
uv run python ingest.py --date YYYY-MM-DD --verbose --delete-csv

# Daily pipeline (runs on VPS cron)
uv run python pipeline/run_daily_pipeline.py --verbose
```

## Architecture

Three separate deployments from the same repo:

- **`frontend/`** — Static HTML/JS/CSS, no build step. Deployed to Cloudflare Pages. API base URL configured in `frontend/config.js` via `window.LEILAO_CONFIG.API_BASE`.
- **`backend_django/`** — Django 6 project with REST API, Django Admin, and management commands. Runs as ASGI via uvicorn on VPS (EasyPanel). The Django app label is `backend_django.auctions`, not `auctions`.
- **`backend_fastapi/`** — FastAPI stub for future AI/analytics endpoints. Not production logic yet.

Data flow: CSVs are downloaded from Caixa on the GitHub Actions runner (to avoid VPS IP blocks), SCP'd to VPS, then ingested into PostgreSQL inside the Docker container via `docker exec`.

## Database

PostgreSQL only — no SQLite fallback. The app fails to start without a running Postgres and a `.env` at the repo root.

Three key tables (managed via raw SQL and Django ORM):
- `snapshot_imoveis` — raw daily CSV loads (accessed via raw SQL in `ingest.py` and `ingest_auctions` command)
- `current_imoveis` — current state used by the API (`Auction` model, explicit `db_table`)
- `changes` — `ENTER`/`EXIT`/`UPDATE` events (`AuctionEvent` model, explicit `db_table`)

Ingest aborts if CSVs for all 27 Brazilian UFs are not present.

## Critical Details

- **Custom CORS middleware** at `backend_django/core/middleware.py` — there is no `django-cors-headers` package. Origins are set via `CORS_ALLOWED_ORIGINS` env var.
- **Production runs ASGI**, not WSGI. Both `Dockerfile` and `docker-compose.yml` use uvicorn with `backend_django.core.asgi`.
- **CSV cleanup differs by interface** — easy to get wrong:
  - Django management commands: delete CSVs by default after ingest. Use `--keep-csv` to preserve.
  - Standalone scripts (`extrai.py`/`ingest.py`): keep CSVs by default. Use `--delete-csv` to remove.
- **`pipeline/`** — DLT-based daily pipeline used by the VPS cron (`run_daily_pipeline.py` → `ingest_dlt.py` → `notify_telegram.py`). This is separate from the Django management commands.

## Django API Endpoints

- `GET /api/stats` — general statistics
- `GET /api/filters` — dynamic filter options
- `GET /api/cidades/?uf=SP` — cities by state
- `GET /api/bairros/?uf=SP&cidade=Sao+Paulo` — neighborhoods
- `GET /api/stats/filtered` — filtered mean/median
- `GET /api/properties` — property listing

## Environment Variables

Required in `.env` at repo root:

```env
host=localhost
port=5432
database="db_leiloes"
user="postgres"
password="..."
sslmode="disable"
SECRET_KEY="..."
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:5500
```

Additional vars for the pipeline:
```env
PIPELINE_TZ=America/Sao_Paulo
DLT_PIPELINE_NAME=leilao_snapshot_daily
DLT_DATASET_NAME=public
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

## Testing / Linting

No test runner, linter, formatter, or typecheck is configured. `auctions/tests.py` is empty. If adding tests, set up pytest or Django TestCase first.

## CI

`.github/workflows/daily-sync.yml` has `workflow_dispatch` only (schedule removed). Required secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, optionally `VPS_PORT`.
