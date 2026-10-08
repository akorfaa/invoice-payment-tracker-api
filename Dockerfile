FROM python:3.11-slim

# No .pyc files, and print logs immediately instead of buffering them.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first: this layer is cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Then only the code the app needs. Tests, scripts and .env never go in.
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# Don't run as root inside the container.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# Render sets $PORT; fall back to 8000 elsewhere. "exec" lets Docker's stop
# signal reach uvicorn so the app shuts down cleanly.
# --proxy-headers / --forwarded-allow-ips: Render's proxy terminates HTTPS and
# forwards plain HTTP to us. Trusting its headers makes redirects and URLs use
# https. This is safe only because the container is not reachable except
# through Render's proxy.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]