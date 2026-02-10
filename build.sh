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

echo "=== Applying custom SQL migrations ==="
python manage.py dbshell -- < migrations_sql/add_fecha_salida_movimientos.sql 2>/dev/null || python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute('ALTER TABLE movimientos ADD COLUMN IF NOT EXISTS fecha_salida TIMESTAMP WITH TIME ZONE NULL')
    c.execute('CREATE INDEX IF NOT EXISTS idx_movimientos_fecha_salida ON movimientos (fecha_salida) WHERE fecha_salida IS NOT NULL')
print('fecha_salida column ensured')
"

echo "=== Running migrations ==="
python manage.py migrate --no-input

echo "=== Setting admin password ==="
python scripts/set_admin_password.py

echo "=== Enabling donations module ==="
python scripts/habilitar_donaciones.py

echo "=== Build complete ==="
