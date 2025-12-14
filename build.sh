#!/usr/bin/env bash
# Root build script - Redirects to backend
set -o errexit

echo "=== Root build detected - Redirecting to backend ==="
cd backend

echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Collecting static files ==="
python manage.py collectstatic --no-input

echo "=== Running migrations ==="
python manage.py migrate --no-input

echo "=== Setting admin password ==="
python set_admin_password.py

echo "=== Build complete ==="
