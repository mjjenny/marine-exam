# ── Backend: Flask API served by gunicorn ────────────────────────────────
FROM python:3.12-slim

# Faster, quieter Python; Flask CLI knows the app for `flask db upgrade`.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=wsgi.py

WORKDIR /app

# Install the app + its dependencies (from pyproject.toml). psycopg2-binary,
# Pillow/pdfplumber and boto3 all ship manylinux wheels, so no build toolchain
# is needed on the slim image.
COPY . .
RUN pip install .

RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

# Container health = the app's /health endpoint (python is already present).
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/health').status==200 else sys.exit(1)"

# Runs DB migrations, then starts gunicorn (see docker-entrypoint.sh).
ENTRYPOINT ["./docker-entrypoint.sh"]
