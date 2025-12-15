import re

# Contar INSERTs y verificar claves únicas
with open('lotes_supabase_insert.sql', 'r', encoding='utf-8') as f:
    contenido = f.read()

# Contar INSERT INTO
inserts = contenido.count('INSERT INTO lotes')
print(f'Total INSERT INTO lotes: {inserts}')

# Contar comentarios de lote
lotes = contenido.count('-- Lote:')
print(f'Total comentarios "-- Lote:": {lotes}')

# Contar ON CONFLICT
conflicts = contenido.count('ON CONFLICT')
print(f'Total ON CONFLICT: {conflicts}')

# Extraer números de lote
numeros_lote = re.findall(r"'([^']+)',\s*p\.id,", contenido)
print(f'\nTotal números de lote extraídos: {len(numeros_lote)}')
print(f'Números de lote únicos: {len(set(numeros_lote))}')

# Mostrar los primeros 10 y últimos 10
print(f'\nPrimeros 10 lotes:')
for i, lote in enumerate(numeros_lote[:10], 1):
    print(f'  {i}. {lote}')

print(f'\nÚltimos 10 lotes:')
for i, lote in enumerate(numeros_lote[-10:], len(numeros_lote)-9):
    print(f'  {i}. {lote}')

# Extraer y contar claves de productos
claves_productos = re.findall(r"WHERE p\.clave = '(\d+)'", contenido)
print(f'\n\nTotal claves de productos: {len(claves_productos)}')
print(f'Claves únicas: {len(set(claves_productos))}')

# Distribución de lotes por producto
from collections import Counter
distribucion = Counter(claves_productos)
print(f'\nTop 10 productos con más lotes:')
for clave, cantidad in distribucion.most_common(10):
    print(f'  Producto {clave}: {cantidad} lotes')
