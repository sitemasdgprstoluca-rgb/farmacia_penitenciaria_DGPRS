"""Verificar si las tablas de Caja Chica existen en la base de datos"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection

tables = [
    'compras_caja_chica', 
    'detalle_compras_caja_chica', 
    'inventario_caja_chica', 
    'movimientos_caja_chica', 
    'historial_compras_caja_chica'
]

print('=' * 50)
print('VERIFICACIÓN DE TABLAS - MÓDULO CAJA CHICA')
print('=' * 50)

all_exist = True
with connection.cursor() as cursor:
    for table in tables:
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s)",
            [table]
        )
        exists = cursor.fetchone()[0]
        status = '✓ EXISTE' if exists else '✗ NO EXISTE'
        print(f'{table}: {status}')
        if not exists:
            all_exist = False

print('=' * 50)
if all_exist:
    print('✓ Todas las tablas existen - Puede ejecutar las pruebas')
else:
    print('✗ Faltan tablas - Debe ejecutar la migración SQL')
    print('')
    print('Para crear las tablas, ejecute en Supabase SQL Editor:')
    print('  Archivo: backend/migrations_sql/create_compras_caja_chica.sql')
