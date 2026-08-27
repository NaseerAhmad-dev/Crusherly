FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY entrypoint.sh ./

# The `azure` extra is installed unconditionally so the same image works whether
# STORAGE_PROVIDER/Application Insights wiring is enabled via environment variables
# (see app/core/config.py) — no separate "production" image variant is maintained.
RUN pip install --upgrade pip \
    && pip install ".[azure]" \
    && chmod +x entrypoint.sh \
    && useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
