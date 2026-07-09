FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Runs once and exits (0 on success). Scheduling is handled by the host
# platform (cron / DigitalOcean App Platform scheduled job / Render cron).
CMD ["python", "main.py"]
