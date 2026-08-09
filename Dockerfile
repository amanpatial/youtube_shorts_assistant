# Multi-stage production image for API + worker (Phase 19).
# Build: docker build -t shorts-assistant:local .
# Run API:  docker run --rm -p 8080:8080 --env-file .env shorts-assistant:local
# Run worker: docker run --rm --env-file .env shorts-assistant:local python -m shorts_assistant.worker

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PIP_NO_CACHE_DIR=1

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser \
    && mkdir -p /app \
    && chown appuser:appuser /app

WORKDIR /app

COPY --from=builder /install /usr/local
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser src ./src

USER appuser

EXPOSE 8080

# Default: API. Compose overrides command for worker / migrate.
CMD ["uvicorn", "shorts_assistant.api.app:app", "--host", "0.0.0.0", "--port", "8080"]
