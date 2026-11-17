FROM python:3.13.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd --create-home --uid 10001 repwise
WORKDIR /app/apps/api

COPY apps/api /app/apps/api
RUN pip install /app/apps/api

USER repwise
EXPOSE 8010
CMD ["uvicorn", "repwise_api.main:app", "--host", "0.0.0.0", "--port", "8010"]
