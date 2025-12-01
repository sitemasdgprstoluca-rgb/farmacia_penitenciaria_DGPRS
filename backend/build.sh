#!/usr/bin/env bash
# Script de build para Render

set -o errexit  # Salir en caso de error

echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Collecting static files ==="
python manage.py collectstatic --no-input

echo "=== Running migrations ==="
python manage.py migrate --no-input

echo "=== Creating/updating admin user ==="
python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
import os

User = get_user_model()
admin_password = os.environ.get('ADMIN_PASSWORD', 'Admin123!')

# Crear o actualizar admin
admin, created = User.objects.update_or_create(
    username='admin',
    defaults={
        'email': 'admin@farmacia.gob.mx',
        'is_staff': True,
        'is_superuser': True,
        'is_active': True,
        'rol': 'admin_sistema',
        'first_name': 'Administrador',
        'last_name': 'Sistema',
    }
)
admin.set_password(admin_password)
admin.save()

if created:
    print(f'{User.objects.count()} objects imported automatically (use -v 2 for details).')
print('Admin password set!')
EOF

echo "=== Build complete ==="
