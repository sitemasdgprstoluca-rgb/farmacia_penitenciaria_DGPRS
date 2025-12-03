#!/usr/bin/env python
"""Fix NULL values in tables before migration."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()

# Fix movimientos
cursor.execute("UPDATE movimientos SET lugar_entrega = '' WHERE lugar_entrega IS NULL")
print(f"Movimientos actualizados: {cursor.rowcount}")

# Fix configuracion_sistema
cursor.execute("UPDATE configuracion_sistema SET nombre_institucion = 'Secretaría de Seguridad' WHERE nombre_institucion IS NULL")
print(f"Config nombre_institucion: {cursor.rowcount}")

cursor.execute("UPDATE configuracion_sistema SET subtitulo_institucion = 'Dirección General de Prevención y Reinserción Social' WHERE subtitulo_institucion IS NULL")
print(f"Config subtitulo_institucion: {cursor.rowcount}")
