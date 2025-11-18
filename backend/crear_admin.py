#!/usr/bin/env python
"""Script para crear usuario admin"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import User
from django.contrib.auth.models import Group

# Crear o actualizar usuario admin
user, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@farmacia.gob.mx',
        'first_name': 'Super',
        'last_name': 'Admin',
        'is_superuser': True,
        'is_staff': True
    }
)

# Establecer contraseña
user.set_password('Admin@2025')
user.is_superuser = True
user.is_staff = True
user.save()

print(f"✅ Usuario admin {'creado' if created else 'actualizado'} exitosamente")
print(f"   Username: admin")
print(f"   Password: Admin@2025")
print(f"   Es superusuario: {user.is_superuser}")
