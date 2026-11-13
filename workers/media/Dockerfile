FROM python:3.13.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd --create-home --uid 10001 repwise
WORKDIR /app

COPY apps/api /app/apps/api
RUN pip install /app/apps/api

USER repwise
CMD ["celery", "-A", "repwise_api.worker.celery_app", "worker", "--loglevel=INFO", "--concurrency=1"]
