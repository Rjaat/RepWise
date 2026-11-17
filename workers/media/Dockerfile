FROM python:3.13.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 repwise
WORKDIR /app

COPY apps/api /app/apps/api
RUN pip install '/app/apps/api[inference]'

USER repwise
CMD ["celery", "-A", "repwise_api.worker.celery_app", "worker", "--loglevel=INFO", "--concurrency=1"]
