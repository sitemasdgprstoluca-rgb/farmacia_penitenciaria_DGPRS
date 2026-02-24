"""
Script para verificar y corregir el esquema de lote_parcialidades.
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.db import connection

def verificar_columnas():
    """Ver las columnas actuales de lote_parcialidades."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'lote_parcialidades'
            ORDER BY ordinal_position
        """)
        columnas = {row[0]: row for row in cursor.fetchall()}
        
        print('=== COLUMNAS ACTUALES EN lote_parcialidades ===')
        for col_name, (_, data_type, nullable) in columnas.items():
            print(f'  {col_name:25} {data_type:20} nullable={nullable}')
        
        return columnas

def agregar_columnas_faltantes(columnas_actuales):
    """Agregar columnas que faltan según el modelo."""
    columnas_necesarias = {
        'es_sobreentrega': "ALTER TABLE lote_parcialidades ADD COLUMN IF NOT EXISTS es_sobreentrega BOOLEAN DEFAULT FALSE",
        'motivo_override': "ALTER TABLE lote_parcialidades ADD COLUMN IF NOT EXISTS motivo_override TEXT",
        'usuario_id': "ALTER TABLE lote_parcialidades ADD COLUMN IF NOT EXISTS usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL",
    }
    
    with connection.cursor() as cursor:
        for col_name, sql in columnas_necesarias.items():
            if col_name not in columnas_actuales:
                print(f'\n[+] Agregando columna: {col_name}')
                try:
                    cursor.execute(sql)
                    print(f'    ✓ Columna {col_name} agregada correctamente')
                except Exception as e:
                    print(f'    ✗ Error: {e}')
            else:
                print(f'\n[=] Columna {col_name} ya existe')

def main():
    print('=' * 60)
    print('CORRECCIÓN DE ESQUEMA: lote_parcialidades')
    print('=' * 60)
    
    columnas = verificar_columnas()
    
    print('\n' + '-' * 60)
    print('AGREGANDO COLUMNAS FALTANTES')
    print('-' * 60)
    
    agregar_columnas_faltantes(columnas)
    
    print('\n' + '-' * 60)
    print('VERIFICACIÓN FINAL')
    print('-' * 60)
    
    verificar_columnas()
    
    print('\n' + '=' * 60)
    print('FIN')
    print('=' * 60)

if __name__ == '__main__':
    main()
