FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY apps/atelier-api/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app

WORKDIR /app/apps/atelier-api

CMD ["sh", "-lc", "python -m alembic -c alembic.ini upgrade head && python -m uvicorn atelier_api.main:app --host 0.0.0.0 --port 9000 --app-dir /app/apps/atelier-api"]
