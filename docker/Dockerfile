# syntax=docker/dockerfile:1
# ── Stage 1: dependency builder ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.deploy.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.deploy.txt

# ── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /install /usr/local

COPY backend/ ./backend/
COPY frontend/ ./frontend/

RUN mkdir -p /data/orion

ENV PYTHONPATH=/app/backend
ENV PERSISTENCE_DB=/data/orion/orion.db
ENV AUTH_ENABLED=true
ENV DEBUG=false
ENV ORION_LLM_ENABLED=false

EXPOSE 8000

# Cloud Run supplies PORT at runtime (normally 8080); keep 8000 as the local
# Docker fallback.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
