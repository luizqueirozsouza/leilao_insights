FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-cache

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "backend_django.core.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
