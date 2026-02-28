FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY apps/server/pyproject.toml apps/server/uv.lock apps/server/README.md /app/
RUN uv sync --frozen --no-dev --no-install-project

COPY apps/server/app /app/app
COPY apps/server/scripts /app/scripts
COPY apps/server/worker.py /app/worker.py
COPY apps/server/data /app/data
COPY apps/server/main.py /app/main.py
COPY backend/data/models /app/backend/data/models

EXPOSE 8000
