FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run both the worker and the beat scheduler in a single process for simplicity
CMD ["celery", "-A", "app.celery_app", "worker", "--beat", "--loglevel=info", "--scheduler=celery.beat:PersistentScheduler"]
