#!/usr/bin/env bash
# Script de build para Render

set -o errexit  # Salir en caso de error

echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Collecting static files ==="
python manage.py collectstatic --no-input

echo "=== Showing pending migrations ==="
python manage.py showmigrations

echo "=== Running migrations ==="
python manage.py migrate --no-input

echo "=== Running migrations ==="
python manage.py migrate --no-input

echo "=== Setting admin password (PostgreSQL only) ==="
# HALLAZGO #8: Solo ejecutar en PostgreSQL, no en SQLite fallback
python set_admin_password.py

echo "=== Build complete ==="
