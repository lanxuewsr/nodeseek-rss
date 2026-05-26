FROM python:3.12-slim

# Prevent .pyc files and enable unbuffered stdout (better for Docker logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py storage.py monitor.py templates.py notifier.py bot.py main.py ./

# SQLite database and log files live here; mount host volumes to persist them.
VOLUME ["/app/data"]
VOLUME ["/app/logs"]

CMD ["python", "main.py"]
