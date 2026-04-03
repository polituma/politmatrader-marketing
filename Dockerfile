FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies in a separate layer for cache efficiency
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app
COPY alembic.ini .
COPY alembic ./alembic

# Create non-root user for security
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE ${PORT:-8080}

# Railway provides its own healthcheck; remove Docker-level HEALTHCHECK
# to avoid port conflicts when Railway overrides the CMD via startCommand.

# Default CMD — Railway's startCommand in railway.toml overrides this
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8080", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
