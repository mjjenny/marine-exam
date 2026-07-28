#!/bin/sh
# Applies any pending database migrations, then launches the production server.
# `flask db upgrade` is idempotent, so it is safe to run on every container start
# (single backend instance). The DB is guaranteed reachable because compose gates
# this container on the db service being healthy.
set -e

echo "==> Applying database migrations (flask db upgrade)"
flask db upgrade

echo "==> Starting gunicorn on :8000"
exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    wsgi:app
