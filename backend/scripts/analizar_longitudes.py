import pandas as pd

# Leer el archivo original
df = pd.read_csv(r'C:\Users\zarag\Downloads\Plantilla_Productos.csv')

print("=== Longitud máxima por columna ===")
for col in df.columns:
    max_len = df[col].astype(str).str.len().max()
    print(f"{col}: max={max_len}")

print("\n=== Valores que exceden 50 caracteres ===")
for col in df.columns:
    largos = df[df[col].astype(str).str.len() > 50]
    if len(largos) > 0:
        print(f"\n{col} ({len(largos)} valores):")
        for idx, row in largos.head(5).iterrows():
            val = str(row[col])[:100]
            print(f"  - [{len(str(row[col]))} chars] {val}")
