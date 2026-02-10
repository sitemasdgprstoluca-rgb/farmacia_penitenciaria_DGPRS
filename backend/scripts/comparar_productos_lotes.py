import pandas as pd
import re

# Leer el Excel de lotes
df_lotes = pd.read_excel(r'C:\Users\zarag\Downloads\lotes_2025-12-15.xlsx', header=1)
headers = df_lotes.iloc[0].tolist()
df_lotes = df_lotes.iloc[1:]
df_lotes.columns = headers
df_lotes = df_lotes.dropna(subset=['Clave', 'Número Lote'])
df_lotes['Clave'] = df_lotes['Clave'].astype(str).str.replace('.0', '', regex=False).str.strip()

# Obtener claves únicas de lotes
claves_en_lotes = set(df_lotes['Clave'].unique())
print(f'Claves únicas en archivo de lotes: {len(claves_en_lotes)}')
print(f'Claves: {sorted(claves_en_lotes)}')

# Leer el SQL de productos para ver qué productos tenemos
with open('productos_supabase_con_conflictos_corregido.sql', 'r', encoding='utf-8') as f:
    sql_productos = f.read()

# Extraer claves de productos del SQL
claves_en_productos = set(re.findall(r"VALUES \('(\d+)'", sql_productos))
print(f'\n\nClaves únicas en SQL de productos: {len(claves_en_productos)}')
print(f'Claves: {sorted(claves_en_productos)}')

# Encontrar claves que están en lotes pero NO en productos
claves_faltantes = claves_en_lotes - claves_en_productos
print(f'\n\n⚠️  PRODUCTOS FALTANTES ({len(claves_faltantes)}):')
for clave in sorted(claves_faltantes):
    productos = df_lotes[df_lotes['Clave'] == clave]['Nombre Producto'].unique()
    lotes_count = len(df_lotes[df_lotes['Clave'] == clave])
    print(f'  Clave {clave}: {productos[0]} ({lotes_count} lotes)')

# Contar lotes que NO se insertarán
lotes_sin_producto = df_lotes[df_lotes['Clave'].isin(claves_faltantes)]
print(f'\n\n📊 RESUMEN:')
print(f'Total lotes en Excel: {len(df_lotes)}')
print(f'Lotes que SÍ se pueden insertar: {len(df_lotes) - len(lotes_sin_producto)}')
print(f'Lotes que NO se pueden insertar (falta producto): {len(lotes_sin_producto)}')
