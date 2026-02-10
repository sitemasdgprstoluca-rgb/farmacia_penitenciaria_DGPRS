"""
Prueba de importación de lotes con archivo que contiene lotes nuevos
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.utils.excel_importer import importar_lotes_desde_excel
from core.models import Lote

# Archivo con lotes nuevos
archivo = r'C:\Users\zarag\Downloads\REVISAR\lotes_nuevos_test.xlsx'

print("=" * 80)
print("PRUEBA DE IMPORTACIÓN DE LOTES NUEVOS")
print("=" * 80)

# Contar antes
lotes_antes = Lote.objects.count()
print(f"\n📊 Lotes en BD antes: {lotes_antes}")

# Importar
print(f"\n🔄 Importando desde: {os.path.basename(archivo)}")
print("   (Archivo con 5 lotes modificados con números únicos)")

resultado = importar_lotes_desde_excel(archivo, usuario=1)

# Contar después
lotes_despues = Lote.objects.count()
nuevos = lotes_despues - lotes_antes

print(f"\n{'='*80}")
print("📊 RESULTADO:")
print(f"{'='*80}")
print(f"  Exitosa: {resultado['exitosa']}")
print(f"  Total procesados: {resultado['total']}")
print(f"  ✓ Exitosos: {resultado['exitosos']}")
print(f"  ✗ Fallidos: {resultado['fallidos']}")
print(f"  📈 Tasa de éxito: {(resultado['exitosos']/resultado['total']*100) if resultado['total'] > 0 else 0:.1f}%")

if resultado.get('actualizados', 0) > 0:
    print(f"  ⚠  Actualizados: {resultado['actualizados']}")
if resultado.get('creados', 0) > 0:
    print(f"  ✨ Creados: {resultado['creados']}")

print(f"\n📦 Lotes en BD después: {lotes_despues}")
print(f"  Diferencia: +{nuevos}")

# Mostrar errores si hay
if resultado['errores']:
    print(f"\n⚠️  ERRORES ({len(resultado['errores'])} total):")
    
    # Agrupar por tipo
    duplicados = [e for e in resultado['errores'] if 'ya existe' in e.lower()]
    otros = [e for e in resultado['errores'] if 'ya existe' not in e.lower()]
    
    if duplicados:
        print(f"\n  DUPLICADOS ({len(duplicados)}):")
        for err in duplicados[:5]:
            print(f"      {err}")
        if len(duplicados) > 5:
            print(f"      ... y {len(duplicados) - 5} más")
    
    if otros:
        print(f"\n  OTROS ERRORES ({len(otros)}):")
        for err in otros[:10]:
            print(f"      {err}")
        if len(otros) > 10:
            print(f"      ... y {len(otros) - 10} más")

# Resultado final
print(f"\n{'='*80}")
if resultado['exitosos'] >= 5:
    print("✅ IMPORTACIÓN EXITOSA: Se crearon los 5 lotes nuevos")
elif resultado['exitosos'] > 0:
    print(f"⚠️  IMPORTACIÓN PARCIAL: Se crearon {resultado['exitosos']}/5 lotes")
else:
    print("❌ IMPORTACIÓN FALLIDA: No se creó ningún lote nuevo")
print(f"{'='*80}")
