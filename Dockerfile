FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    cron \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-cache

COPY . .

COPY docker/leilao-sync.cron /etc/cron.d/leilao-sync
RUN chmod 0644 /etc/cron.d/leilao-sync \
    && touch /var/log/leilao-sync.log

EXPOSE 8000

CMD ["sh", "-c", "cron && exec uv run uvicorn backend_django.core.asgi:application --host 0.0.0.0 --port 8000"]
