FROM python:3.12-slim
WORKDIR /workspace
COPY deploy/worker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY app /workspace/app
ENV PYTHONUNBUFFERED=1 LOG_CONSOLE_ENABLE=False LOG_FILE_ENABLE=False HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
CMD ["celery", "-A", "app.infrastructure.queue.celery_app:celery_app", "worker", "--loglevel=WARNING", "--concurrency=1"]
