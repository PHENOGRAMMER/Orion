# syntax=docker/dockerfile:1
# ── Stage 1: dependency builder ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /install /usr/local

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY fine_tuned_model/ ./fine_tuned_model/

RUN mkdir -p /data/orion

ENV PYTHONPATH=/app/backend
ENV PERSISTENCE_DB=/data/orion/orion.db
ENV AUTH_ENABLED=true
ENV DEBUG=false

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
