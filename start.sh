#!/usr/bin/env bash
# Start script for Render
set -o errexit

echo "=== Starting Gunicorn server ==="
cd backend
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2
