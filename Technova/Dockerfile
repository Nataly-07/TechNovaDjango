FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn whitenoise

COPY . .

EXPOSE 8000

CMD gunicorn Technova.wsgi:application --bind 0.0.0.0:$PORT