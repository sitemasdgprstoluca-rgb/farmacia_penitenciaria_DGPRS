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

echo "=== Applying custom SQL migrations (PostgreSQL only) ==="
python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection
if connection.vendor != 'postgresql':
    print('Skipping SQL migration: not PostgreSQL (current: ' + connection.vendor + ')')
else:
    with connection.cursor() as c:
        c.execute('ALTER TABLE movimientos ADD COLUMN IF NOT EXISTS fecha_salida TIMESTAMP WITH TIME ZONE NULL')
        c.execute('CREATE INDEX IF NOT EXISTS idx_movimientos_fecha_salida ON movimientos (fecha_salida) WHERE fecha_salida IS NOT NULL')
    print('fecha_salida column ensured')
"

echo "=== Running migrations ==="
python manage.py migrate --no-input

echo "=== Setting admin password (PostgreSQL only) ==="
# HALLAZGO #8: Solo ejecutar en PostgreSQL, no en SQLite fallback
python scripts/set_admin_password.py

echo "=== Enabling donations module for ADMIN and FARMACIA users ==="
python scripts/habilitar_donaciones.py

echo "=== Build complete ==="
