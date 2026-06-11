#!/bin/sh
set -e

PORT="${PORT:-8000}"

echo "==> Migraciones..."
python manage.py migrate --noinput

echo "==> Archivos estáticos..."
python manage.py collectstatic --noinput

echo "==> Gunicorn en 0.0.0.0:${PORT} (workers=${WEB_CONCURRENCY:-2})"
exec gunicorn Technova.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
