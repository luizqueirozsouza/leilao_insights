# AGENTS.md

## Quick Start

```bash
uv sync                                          # install deps (Python 3.13+, requires uv)
uv run python backend_django/manage.py migrate    # needs .env + running PostgreSQL
uv run python backend_django/manage.py runserver  # Django on :8000
uv run uvicorn backend_fastapi.main:app --port 8001  # FastAPI (stub) on :8001
```

## Repo Layout

- `backend_django/` — Django project (API, admin, management commands). App label is `backend_django.auctions`, not `auctions`.
- `backend_fastapi/` — FastAPI stub with placeholder AI endpoints. Not production logic yet.
- `frontend/` — Static HTML/JS/CSS. No build step. API base URL set in `frontend/config.js`.
- `extrai.py` / `ingest.py` — Standalone scripts for the CSV download → DB pipeline.
- `data/` — Local CSV snapshots (gitignored).

## Critical Details

- **No SQLite.** PostgreSQL only. The app will not start without a running Postgres and a `.env` at repo root.
- **Custom CORS middleware** at `backend_django.core.middleware.CorsMiddleware` — no `django-cors-headers` package. Origins configured via `CORS_ALLOWED_ORIGINS` env var.
- **Explicit `db_table`** on models: `Auction` → `current_imoveis`, `AuctionEvent` → `changes`. The `snapshot_imoveis` table is accessed via raw SQL in `ingest.py` and the `ingest_auctions` management command.
- **Production Django runs ASGI** (`backend_django.core.asgi`), not WSGI. The `Dockerfile` and `docker-compose.yml` both use uvicorn.

## Data Pipeline

- `sync_auctions` — combined extract + ingest (preferred).
- `extrai_auctions` — download only.
- `ingest_auctions` — load only.
- All commands take `--date YYYY-MM-DD` and `--verbose`.

**CSV cleanup behavior differs between interfaces** (easy to get wrong):
- Django management commands: **delete CSVs by default** after successful ingest. Use `--keep-csv` to preserve.
- Standalone scripts (`extrai.py` / `ingest.py`): **keep CSVs by default**. Use `--delete-csv` to remove.

Ingest aborts if CSVs for all 27 UFs are not present.

## Testing / Linting

No test runner, linter, formatter, or typecheck is configured. `auctions/tests.py` is empty. If adding tests, set up pytest or Django TestCase before writing any.

## CI

`.github/workflows/daily-sync.yml` — runs at 08:00 BRT. Extracts CSVs on the GitHub runner (avoids Caixa 403 blocks on VPS IPs), SCPs the snapshot to the VPS, then ingests inside the Docker container via `docker exec`.

Required GitHub secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, optionally `VPS_PORT`.

## Frontend

No framework, no bundler. Open `frontend/index.html` directly or via Live Server. The API base is `window.LEILAO_CONFIG.API_BASE` in `frontend/config.js`.
