#!/bin/sh

echo "--- Starting PadelUp Backend Startup Script ---"

# Apply database migrations
echo "--- Running Migrations ---"
python manage.py migrate --no-input

# Collect static files
echo "--- Collecting Static Files ---"
python manage.py collectstatic --no-input

# Start Gunicorn
echo "--- Starting Gunicorn ---"
exec gunicorn backend.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 4 \
    --worker-class gthread \
    --access-logfile - \
    --error-logfile - \
    --log-level debug \
    --timeout 120
