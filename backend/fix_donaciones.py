#!/usr/bin/env python
"""
Script simple para habilitar donaciones - EJECUTAR EN RENDER SHELL
Uso: python fix_donaciones.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

print("🔧 Habilitando módulo de donaciones...")
print("=" * 60)

# Actualizar TODOS los usuarios ADMIN, FARMACIA y superusers
usuarios = User.objects.filter(rol__in=['ADMIN', 'FARMACIA']) | User.objects.filter(is_superuser=True)

if not usuarios.exists():
    print("❌ No se encontraron usuarios ADMIN o FARMACIA")
else:
    actualizados = usuarios.update(perm_donaciones=True)
    print(f"✅ {actualizados} usuario(s) actualizados")
    
    # Mostrar usuarios actualizados
    for u in usuarios:
        u.refresh_from_db()
        print(f"   • {u.username} ({u.rol or 'SUPERUSER'}) - perm_donaciones={u.perm_donaciones}")

print("\n✅ Completado. Cierra sesión y vuelve a iniciar sesión.")
