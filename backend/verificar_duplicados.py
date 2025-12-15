import pandas as pd

# Leer el Excel de lotes
df_lotes = pd.read_excel(r'C:\Users\zarag\Downloads\lotes_2025-12-15.xlsx', header=1)
headers = df_lotes.iloc[0].tolist()
df_lotes = df_lotes.iloc[1:]
df_lotes.columns = headers
df_lotes = df_lotes.dropna(subset=['Clave', 'Número Lote'])
df_lotes['Clave'] = df_lotes['Clave'].astype(str).str.replace('.0', '', regex=False).str.strip()

# Verificar duplicados de número_lote + producto
print('Verificando combinaciones numero_lote + clave_producto...\n')
df_lotes['combo'] = df_lotes['Número Lote'].astype(str) + '-' + df_lotes['Clave']
duplicados = df_lotes[df_lotes.duplicated(subset='combo', keep=False)]

if len(duplicados) > 0:
    print(f'⚠️  Encontrados {len(duplicados)} registros duplicados (mismo lote + producto):\n')
    for combo in duplicados['combo'].unique():
        dup = duplicados[duplicados['combo'] == combo]
        print(f'  {combo}:')
        for idx, row in dup.iterrows():
            print(f'    - {row["Nombre Producto"]} | Cant: {row["Cantidad Inicial"]}')
else:
    print('✅ No hay duplicados de numero_lote + producto')

# Verificar solo por número de lote
print('\n\nVerificando números de lote únicos...\n')
lotes_duplicados = df_lotes[df_lotes.duplicated(subset='Número Lote', keep=False)]

if len(lotes_duplicados) > 0:
    print(f'⚠️  Números de lote que se repiten ({len(lotes_duplicados)} registros):')
    for num_lote in lotes_duplicados['Número Lote'].unique():
        dup = df_lotes[df_lotes['Número Lote'] == num_lote]
        print(f'\n  Lote: {num_lote} ({len(dup)} veces)')
        for idx, row in dup.iterrows():
            print(f'    - Producto {row["Clave"]}: {row["Nombre Producto"]}')
else:
    print('✅ Todos los números de lote son únicos')

print(f'\n\n📊 RESUMEN:')
print(f'Total registros: {len(df_lotes)}')
print(f'Números de lote únicos: {df_lotes["Número Lote"].nunique()}')
print(f'Combinaciones únicas (lote + producto): {df_lotes["combo"].nunique()}')
