# ─── Build / install stage ───────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --user -r /app/requirements.txt


# ─── Runtime stage ───────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/app/.local/bin:$PATH" \
    PORT=7860 \
    APP_ENV=production

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 app

COPY --from=builder /root/.local /home/app/.local
RUN chown -R app:app /home/app/.local

WORKDIR /app
COPY --chown=app:app backend ./backend
COPY --chown=app:app alembic.ini ./alembic.ini

# HuggingFace Spaces & local model cache
RUN mkdir -p /app/data/models && chown -R app:app /app/data

USER app
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:${PORT}/healthz || exit 1

# Try migrations but don't fail if DB not ready — app handles DB gracefully
CMD ["sh", "-c", "alembic upgrade head || true && uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
