FROM python:3.13-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

RUN useradd -m appuser && mkdir -p /app/data && chown -R appuser /app
USER appuser

EXPOSE 7860
CMD uvicorn src.api:app --host 0.0.0.0 --port ${PORT:-7860}
