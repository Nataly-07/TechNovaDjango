FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TECHNOVA_ENV=prod

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/entrypoint.sh

# collectstatic en build (más rápido el arranque → healthcheck pasa antes)
ENV DJANGO_SECRET_KEY=build-collectstatic-only-min-32-characters-long
RUN python manage.py collectstatic --noinput

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
