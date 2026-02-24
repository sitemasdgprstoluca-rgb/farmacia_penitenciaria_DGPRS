"""
Script para verificar y corregir el esquema de lote_parcialidades.
Verifica columnas, índices y constraints necesarios.
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
        
        print('=== COLUMNAS EN lote_parcialidades ===')
        for col_name, (_, data_type, nullable) in columnas.items():
            print(f'  {col_name:25} {data_type:20} nullable={nullable}')
        
        return columnas

def verificar_indices():
    """Ver los índices actuales de lote_parcialidades."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'lote_parcialidades'
            ORDER BY indexname
        """)
        indices = cursor.fetchall()
        
        print('\n=== ÍNDICES EN lote_parcialidades ===')
        for idx_name, idx_def in indices:
            is_unique = 'UNIQUE' in idx_def.upper()
            print(f'  {"[UNIQUE]" if is_unique else "[INDEX]"} {idx_name}')
        
        return {row[0]: row[1] for row in indices}

def verificar_constraints():
    """Ver los constraints de lote_parcialidades."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT conname, contype, pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'lote_parcialidades'::regclass
            ORDER BY conname
        """)
        constraints = cursor.fetchall()
        
        print('\n=== CONSTRAINTS EN lote_parcialidades ===')
        tipos = {'p': 'PRIMARY KEY', 'f': 'FOREIGN KEY', 'c': 'CHECK', 'u': 'UNIQUE'}
        for con_name, con_type, con_def in constraints:
            print(f'  [{tipos.get(con_type, con_type):12}] {con_name}: {con_def}')
        
        return {row[0]: row for row in constraints}

def agregar_columnas_faltantes(columnas_actuales):
    """Agregar columnas que faltan según el modelo."""
    columnas_necesarias = {
        'es_sobreentrega': "ALTER TABLE lote_parcialidades ADD COLUMN IF NOT EXISTS es_sobreentrega BOOLEAN DEFAULT FALSE",
        'motivo_override': "ALTER TABLE lote_parcialidades ADD COLUMN IF NOT EXISTS motivo_override TEXT",
        'usuario_id': "ALTER TABLE lote_parcialidades ADD COLUMN IF NOT EXISTS usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL",
    }
    
    print('\n--- Verificando columnas faltantes ---')
    with connection.cursor() as cursor:
        for col_name, sql in columnas_necesarias.items():
            if col_name not in columnas_actuales:
                print(f'[+] Agregando columna: {col_name}')
                try:
                    cursor.execute(sql)
                    print(f'    ✓ Columna {col_name} agregada')
                except Exception as e:
                    print(f'    ✗ Error: {e}')
            else:
                print(f'[=] Columna {col_name} ya existe')

def agregar_indices_faltantes(indices_actuales):
    """Agregar índices que faltan."""
    indices_necesarios = {
        'idx_lote_parcialidades_lote_id': 
            "CREATE INDEX IF NOT EXISTS idx_lote_parcialidades_lote_id ON lote_parcialidades(lote_id)",
        'idx_lote_parcialidades_fecha': 
            "CREATE INDEX IF NOT EXISTS idx_lote_parcialidades_fecha ON lote_parcialidades(fecha_entrega)",
        'idx_lote_parcialidades_sobreentrega': 
            "CREATE INDEX IF NOT EXISTS idx_lote_parcialidades_sobreentrega ON lote_parcialidades(es_sobreentrega) WHERE es_sobreentrega = true",
        'idx_lote_parcialidades_unique_entrega': 
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_lote_parcialidades_unique_entrega ON lote_parcialidades (lote_id, fecha_entrega, COALESCE(numero_factura, ''))",
    }
    
    print('\n--- Verificando índices faltantes ---')
    with connection.cursor() as cursor:
        for idx_name, sql in indices_necesarios.items():
            if idx_name not in indices_actuales:
                print(f'[+] Creando índice: {idx_name}')
                try:
                    cursor.execute(sql)
                    print(f'    ✓ Índice {idx_name} creado')
                except Exception as e:
                    print(f'    ✗ Error: {e}')
            else:
                print(f'[=] Índice {idx_name} ya existe')

def main():
    print('=' * 70)
    print('VERIFICACIÓN DE ESQUEMA: lote_parcialidades')
    print('=' * 70)
    
    columnas = verificar_columnas()
    indices = verificar_indices()
    constraints = verificar_constraints()
    
    print('\n' + '=' * 70)
    print('CORRECCIÓN DE FALTANTES')
    print('=' * 70)
    
    agregar_columnas_faltantes(columnas)
    agregar_indices_faltantes(indices)
    
    print('\n' + '=' * 70)
    print('VERIFICACIÓN FINAL')
    print('=' * 70)
    
    verificar_columnas()
    verificar_indices()
    verificar_constraints()
    
    print('\n' + '=' * 70)
    print('FIN')
    print('=' * 70)

if __name__ == '__main__':
    main()
