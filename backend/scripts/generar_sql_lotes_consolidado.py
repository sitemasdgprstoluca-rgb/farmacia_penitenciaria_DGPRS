import pandas as pd
from datetime import datetime

# Leer el archivo Excel
file_path = r'C:\Users\zarag\Downloads\lotes_2025-12-15.xlsx'
df = pd.read_excel(file_path, header=1)

# La primera fila tiene los encabezados reales
headers = df.iloc[0].tolist()
df = df.iloc[1:]  # Remover la fila de encabezados
df.columns = headers

# Limpiar y preparar datos
df = df.dropna(subset=['Clave', 'Número Lote'])
df['Clave'] = df['Clave'].astype(str).str.replace('.0', '', regex=False).str.strip()

print(f'Total lotes antes de consolidar: {len(df)}')

# Consolidar lotes duplicados (mismo numero_lote + producto) sumando cantidades
df_consolidado = df.groupby(['Número Lote', 'Clave'], as_index=False).agg({
    'Nombre Producto': 'first',
    'Cantidad Inicial': 'sum',
    'Cantidad Actual': 'sum',
    'Fecha Fabricación': 'first',
    'Fecha Caducidad': 'min',  # Usamos la fecha más próxima
    'Precio Unitario': 'first',
    'Número Contrato': 'first',
    'Marca': 'first',
    'Ubicación': 'first',
    'Centro': 'first',
    'Activo': 'first'
})

print(f'Total lotes después de consolidar: {len(df_consolidado)}')
print(f'Lotes eliminados por duplicado: {len(df) - len(df_consolidado)}')

# Generar SQL con lotes consolidados
sql_output = []
sql_output.append('-- Script de inserción de lotes para Supabase (CONSOLIDADO)')
sql_output.append('-- Generado: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
sql_output.append('-- Total de lotes: ' + str(len(df_consolidado)))
sql_output.append('-- Nota: Lotes duplicados fueron consolidados sumando cantidades')
sql_output.append('')
sql_output.append('-- IMPORTANTE: Los productos deben estar ya insertados en la tabla productos')
sql_output.append('')
sql_output.append('-- Verificar productos existentes (opcional)')
sql_output.append('SELECT COUNT(*) as total_productos FROM productos;')
sql_output.append('')
sql_output.append('-- =============================================================================')
sql_output.append('-- INSERCIÓN DE LOTES CONSOLIDADOS')
sql_output.append('-- =============================================================================')
sql_output.append('')

# Procesar cada lote
contador = 0
for idx, row in df_consolidado.iterrows():
    try:
        clave = str(row['Clave']).strip()
        numero_lote = str(row['Número Lote']).strip()
        cantidad_inicial = int(row['Cantidad Inicial']) if pd.notna(row['Cantidad Inicial']) else 0
        cantidad_actual = int(row['Cantidad Actual']) if pd.notna(row['Cantidad Actual']) else 0
        
        # Fechas
        fecha_fab = row['Fecha Fabricación']
        if pd.notna(fecha_fab):
            fecha_fab_str = pd.to_datetime(fecha_fab).strftime('%Y-%m-%d')
        else:
            fecha_fab_str = None
        
        fecha_cad = row['Fecha Caducidad']
        if pd.notna(fecha_cad):
            fecha_cad_str = pd.to_datetime(fecha_cad).strftime('%Y-%m-%d')
        else:
            print(f"⚠️  Saltando lote {numero_lote} - falta fecha caducidad")
            continue  # Fecha caducidad es obligatoria
        
        precio = float(row['Precio Unitario']) if pd.notna(row['Precio Unitario']) else 0
        numero_contrato = str(row['Número Contrato']).strip() if pd.notna(row['Número Contrato']) else '2025'
        marca = str(row['Marca']).strip() if pd.notna(row['Marca']) else 'S/N'
        ubicacion = str(row['Ubicación']).strip() if pd.notna(row['Ubicación']) else 'FARMCIA'
        activo = str(row['Activo']).strip().lower() == 'activo' if pd.notna(row['Activo']) else True
        
        # Generar INSERT
        sql_output.append(f'-- Lote: {numero_lote} - Producto: {clave} (Cant Total: {cantidad_actual})')
        sql_output.append('INSERT INTO lotes (')
        sql_output.append('    numero_lote, producto_id, cantidad_inicial, cantidad_actual,')
        sql_output.append('    fecha_fabricacion, fecha_caducidad, precio_unitario,')
        sql_output.append('    numero_contrato, marca, ubicacion, centro_id, activo')
        sql_output.append(') ')
        sql_output.append('SELECT')
        sql_output.append(f"    '{numero_lote}',")
        sql_output.append(f"    p.id,")
        sql_output.append(f"    {cantidad_inicial},")
        sql_output.append(f"    {cantidad_actual},")
        if fecha_fab_str:
            sql_output.append(f"    '{fecha_fab_str}',")
        else:
            sql_output.append(f"    NULL,")
        sql_output.append(f"    '{fecha_cad_str}',")
        sql_output.append(f"    {precio},")
        sql_output.append(f"    '{numero_contrato}',")
        sql_output.append(f"    '{marca}',")
        sql_output.append(f"    '{ubicacion}',")
        sql_output.append(f"    NULL,  -- centro_id (NULL = farmacia central)")
        sql_output.append(f"    {'TRUE' if activo else 'FALSE'}")
        sql_output.append('FROM productos p')
        sql_output.append(f"WHERE p.clave = '{clave}'")
        sql_output.append('ON CONFLICT (numero_lote, producto_id) DO NOTHING;')
        sql_output.append('')
        contador += 1
    except Exception as e:
        print(f"❌ Error procesando lote {numero_lote}: {e}")
        continue

# Queries de verificación
sql_output.append('')
sql_output.append('-- =============================================================================')
sql_output.append('-- VERIFICACIÓN POST-INSERCIÓN')
sql_output.append('-- =============================================================================')
sql_output.append('')
sql_output.append('-- Contar lotes insertados')
sql_output.append('SELECT COUNT(*) as total_lotes FROM lotes;')
sql_output.append('')
sql_output.append('-- Lotes por producto (top 10)')
sql_output.append('SELECT ')
sql_output.append('    p.clave,')
sql_output.append('    p.nombre,')
sql_output.append('    COUNT(l.id) as total_lotes,')
sql_output.append('    SUM(l.cantidad_actual) as stock_total')
sql_output.append('FROM productos p')
sql_output.append('LEFT JOIN lotes l ON p.id = l.producto_id')
sql_output.append('GROUP BY p.id, p.clave, p.nombre')
sql_output.append('ORDER BY total_lotes DESC')
sql_output.append('LIMIT 10;')
sql_output.append('')
sql_output.append("-- Verificar lotes próximos a caducar (6 meses)")
sql_output.append('SELECT ')
sql_output.append('    l.numero_lote,')
sql_output.append('    p.clave,')
sql_output.append('    p.nombre,')
sql_output.append('    l.fecha_caducidad,')
sql_output.append('    l.cantidad_actual')
sql_output.append('FROM lotes l')
sql_output.append('JOIN productos p ON l.producto_id = p.id')
sql_output.append("WHERE l.fecha_caducidad <= CURRENT_DATE + INTERVAL '6 months'")
sql_output.append('AND l.cantidad_actual > 0')
sql_output.append('ORDER BY l.fecha_caducidad')
sql_output.append('LIMIT 20;')

# Guardar archivo
output_file = 'lotes_supabase_consolidado.sql'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(sql_output))

print(f'\n✅ Archivo generado: {output_file}')
print(f'📊 Total de INSERTs generados: {contador}')
print(f'\n⚠️  NOTA: Los lotes duplicados fueron consolidados sumando sus cantidades')
