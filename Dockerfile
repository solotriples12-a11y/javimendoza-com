FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

EXPOSE 8000

# Fetch stats on container start so the first request shows real data,
# then hand off to gunicorn. Subsequent updates come from a daily cron.
CMD sh -c "python update_stats.py || true; exec gunicorn --bind 0.0.0.0:8000 --workers 2 --access-logfile - app:app"
