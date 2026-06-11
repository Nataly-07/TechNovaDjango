#!/bin/sh
set -e

PORT="${PORT:-8000}"

if [ -z "$DATABASE_URL" ] && [ "${TECHNOVA_ENV:-}" != "dev" ]; then
  echo "ERROR: DATABASE_URL no está definida."
  echo "En Railway: New → Database → PostgreSQL, luego vincula DATABASE_URL al servicio web."
  exit 1
fi

echo "==> Migraciones..."
python manage.py migrate --noinput

if [ ! -d "staticfiles" ] || [ -z "$(ls -A staticfiles 2>/dev/null)" ]; then
  echo "==> Archivos estáticos (fallback)..."
  python manage.py collectstatic --noinput
fi

echo "==> Gunicorn en 0.0.0.0:${PORT} (workers=${WEB_CONCURRENCY:-2})"
exec gunicorn Technova.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
