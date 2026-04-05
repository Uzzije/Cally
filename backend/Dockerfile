FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt

RUN pip install --upgrade pip setuptools wheel \
    && pip install -r /app/backend/requirements.txt

COPY backend /app/backend

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
