"""
Script de diagnóstico para verificar inconsistencia de inventario en lote Q0425297
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db.models import Sum
from core.models import Lote, Movimiento, Producto

def diagnosticar_lote(numero_lote):
    print(f"\n{'='*60}")
    print(f"DIAGNÓSTICO DE LOTE: {numero_lote}")
    print(f"{'='*60}\n")
    
    # 1. Buscar todos los lotes con ese número
    lotes = Lote.objects.filter(numero_lote__iexact=numero_lote).select_related('producto', 'centro')
    
    if not lotes.exists():
        print(f"❌ No se encontró ningún lote con número: {numero_lote}")
        return
    
    print(f"📦 Lotes encontrados: {lotes.count()}\n")
    
    total_stock_lotes = 0
    for lote in lotes:
        centro_nombre = lote.centro.nombre if lote.centro else 'Farmacia Central (NULL)'
        print(f"  Lote ID: {lote.id}")
        print(f"  - Centro: {centro_nombre}")
        print(f"  - Producto: {lote.producto.clave} - {lote.producto.nombre}")
        print(f"  - Cantidad Inicial: {lote.cantidad_inicial}")
        print(f"  - Cantidad Actual: {lote.cantidad_actual}")
        print(f"  - Activo: {lote.activo}")
        print(f"  - Número Contrato: {lote.numero_contrato or 'N/A'}")
        print()
        total_stock_lotes += lote.cantidad_actual or 0
    
    print(f"📊 TOTAL STOCK EN LOTES: {total_stock_lotes}\n")
    
    # 2. Buscar movimientos
    lotes_ids = list(lotes.values_list('id', flat=True))
    movimientos = Movimiento.objects.filter(lote_id__in=lotes_ids).order_by('fecha')
    
    print(f"📋 Movimientos encontrados: {movimientos.count()}\n")
    
    saldo_calculado = 0
    for mov in movimientos:
        saldo_calculado += mov.cantidad
        centro_destino = mov.centro_destino.nombre if mov.centro_destino else '-'
        centro_origen = mov.centro_origen.nombre if mov.centro_origen else '-'
        lote_centro = mov.lote.centro.nombre if mov.lote and mov.lote.centro else 'Farmacia Central'
        
        print(f"  [{mov.fecha.strftime('%Y-%m-%d %H:%M')}] {mov.tipo.upper():10} | "
              f"Cantidad: {mov.cantidad:+6} | Saldo: {saldo_calculado:6} | "
              f"Origen: {centro_origen:20} | Destino: {centro_destino:20} | "
              f"Lote en: {lote_centro}")
    
    # 3. Calcular totales
    total_entradas = movimientos.filter(tipo='entrada').aggregate(t=Sum('cantidad'))['t'] or 0
    total_salidas = movimientos.filter(tipo='salida').aggregate(t=Sum('cantidad'))['t'] or 0
    
    print(f"\n📈 RESUMEN DE MOVIMIENTOS:")
    print(f"  - Total Entradas: {total_entradas}")
    print(f"  - Total Salidas: {total_salidas}")
    print(f"  - Saldo Calculado: {saldo_calculado}")
    
    # 4. Verificar consistencia
    print(f"\n✅ VERIFICACIÓN DE CONSISTENCIA:")
    print(f"  - Stock en Lotes (BD): {total_stock_lotes}")
    print(f"  - Saldo por Movimientos: {saldo_calculado}")
    
    diferencia = total_stock_lotes - saldo_calculado
    if diferencia != 0:
        print(f"  ⚠️  DIFERENCIA DETECTADA: {diferencia} unidades")
        print(f"      Esto significa que hay {abs(diferencia)} unidades que no tienen movimiento registrado")
    else:
        print(f"  ✓ Los datos son consistentes")


if __name__ == '__main__':
    # Diagnosticar el lote problemático
    diagnosticar_lote('Q0425297')
