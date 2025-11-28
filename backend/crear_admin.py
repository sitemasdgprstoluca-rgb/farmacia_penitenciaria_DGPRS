#!/usr/bin/env python
"""
Script para crear usuario administrador.

USO SEGURO:
    # Opción 1: Variables de entorno
    ADMIN_USERNAME=admin ADMIN_PASSWORD=MiClave123! ADMIN_EMAIL=admin@ejemplo.com python crear_admin.py
    
    # Opción 2: Interactivo (pedirá la contraseña de forma segura)
    python crear_admin.py
    
    # Opción 3: Usar el comando de Django (recomendado)
    python manage.py createsuperuser

NOTA: Este script NO usa credenciales por defecto por seguridad.
"""
import os
import sys
import getpass
import django

# Configurar Django - usar config.settings (no backend.settings)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

User = get_user_model()


def get_password_securely():
    """Obtiene contraseña de forma segura (env var o input oculto)."""
    password = os.environ.get('ADMIN_PASSWORD')
    if password:
        return password
    
    # Pedir contraseña de forma interactiva
    while True:
        password = getpass.getpass("Ingrese contraseña para admin: ")
        if len(password) < 8:
            print("⚠️  La contraseña debe tener al menos 8 caracteres")
            continue
        password_confirm = getpass.getpass("Confirme contraseña: ")
        if password != password_confirm:
            print("⚠️  Las contraseñas no coinciden")
            continue
        return password


def main():
    # Obtener credenciales desde variables de entorno o interactivamente
    username = os.environ.get('ADMIN_USERNAME')
    email = os.environ.get('ADMIN_EMAIL')
    
    if not username:
        username = input("Username [admin]: ").strip() or 'admin'
    
    if not email:
        while True:
            email = input("Email [admin@farmacia.gob.mx]: ").strip() or 'admin@farmacia.gob.mx'
            try:
                validate_email(email)
                break
            except ValidationError:
                print("⚠️  Email inválido, intente de nuevo")
    
    # Verificar si el usuario ya existe
    existing_user = User.objects.filter(username=username).first()
    if existing_user:
        print(f"\n⚠️  El usuario '{username}' ya existe.")
        response = input("¿Desea actualizar la contraseña? [s/N]: ").strip().lower()
        if response != 's':
            print("Operación cancelada.")
            sys.exit(0)
        password = get_password_securely()
        existing_user.set_password(password)
        existing_user.save()
        print(f"\n✅ Contraseña actualizada para '{username}'")
        sys.exit(0)
    
    # Crear nuevo usuario
    password = get_password_securely()
    
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        first_name=os.environ.get('ADMIN_FIRST_NAME', 'Super'),
        last_name=os.environ.get('ADMIN_LAST_NAME', 'Admin'),
    )
    
    print(f"\n✅ Usuario superadmin creado exitosamente")
    print(f"   Username: {username}")
    print(f"   Email: {email}")
    print(f"   Es superusuario: {user.is_superuser}")
    print("\n⚠️  IMPORTANTE: Guarde la contraseña en un lugar seguro.")
    print("   No se mostrará ni almacenará en texto plano.")


if __name__ == '__main__':
    main()
