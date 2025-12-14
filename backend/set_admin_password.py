#!/usr/bin/env python
"""
Script para configurar contraseña de admin en producción.
Solo se ejecuta si estamos usando PostgreSQL (no SQLite fallback).

HALLAZGO #8: Detectar motor de BD antes de ejecutar comandos específicos de producción.
"""
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    import django
    django.setup()
    
    from django.db import connection
    from core.models import User
    
    # Detectar motor de BD
    vendor = connection.vendor
    
    if vendor != 'postgresql':
        print(f"INFO: Usando {vendor} como BD. Saltando configuración de admin (solo para PostgreSQL/producción).")
        return
    
    # Estamos en PostgreSQL (producción con Supabase)
    try:
        user = User.objects.get(username='admin')
        user.set_password('Admin123!')
        user.save()
        print('Admin password set successfully!')
    except User.DoesNotExist:
        print('WARNING: Usuario admin no existe. Crear manualmente con: python manage.py createsuperuser')
    except Exception as e:
        print(f'ERROR setting admin password: {e}')
        # No fallar el deployment por esto
        sys.exit(0)

if __name__ == '__main__':
    main()
