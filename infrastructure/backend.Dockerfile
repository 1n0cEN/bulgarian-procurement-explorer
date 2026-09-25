FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock && useradd --create-home app
COPY backend backend
COPY pipeline pipeline
COPY database database
COPY alembic.ini .
COPY data/cohort data/cohort
RUN mkdir -p data/quarantine && chown -R app:app /app
USER app
