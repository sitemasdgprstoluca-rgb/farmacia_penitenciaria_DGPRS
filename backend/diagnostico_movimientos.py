"""
Diagnóstico de movimientos para el período 01-03 enero 2026.
Ejecutar con: python -m pytest diagnostico_movimientos.py -v -s
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
django.setup()

from core.models import Movimiento
from django.db.models import Sum, Count

def diagnosticar():
    """Diagnóstico de movimientos."""
    print("\n" + "="*80)
    print("DIAGNÓSTICO DE MOVIMIENTOS - Período 01-03 Enero 2026")
    print("="*80 + "\n")
    
    # Tipos
    tipos_suma = ['entrada', 'ajuste_positivo', 'devolucion']
    tipos_resta = ['salida', 'ajuste', 'ajuste_negativo', 'merma', 'caducidad', 'transferencia']
    
    # Obtener movimientos del período
    movimientos = Movimiento.objects.filter(
        fecha__date__gte='2026-01-01',
        fecha__date__lte='2026-01-03'
    ).select_related('lote__producto', 'centro_origen', 'centro_destino').order_by('-fecha')
    
    print(f"Total movimientos en período: {movimientos.count()}\n")
    
    # Mostrar cada movimiento
    print("DETALLE DE MOVIMIENTOS:")
    print("-" * 120)
    print(f"{'ID':<6} {'REF':<30} {'TIPO':<15} {'CANT':<8} {'PRODUCTO':<30} {'ORIGEN':<15} {'DESTINO':<15}")
    print("-" * 120)
    
    total_entradas = 0
    total_salidas = 0
    count_entradas = 0
    count_salidas = 0
    transacciones = {}
    
    for mov in movimientos:
        tipo_mov = mov.tipo.lower()
        amount = abs(mov.cantidad) if tipo_mov in tipos_resta else mov.cantidad
        ref = mov.referencia or f"MOV-{mov.id}"
        
        producto = mov.lote.producto.clave if mov.lote and mov.lote.producto else 'N/A'
        origen = mov.centro_origen.nombre[:15] if mov.centro_origen else 'F.Central'
        destino = mov.centro_destino.nombre[:15] if mov.centro_destino else 'F.Central'
        
        clasificacion = "ENTRADA" if tipo_mov in tipos_suma else "SALIDA"
        print(f"{mov.id:<6} {ref[:30]:<30} {tipo_mov.upper():<15} {mov.cantidad:<8} {producto:<30} {origen:<15} {destino:<15} -> {clasificacion}")
        
        # Agrupar por referencia
        if ref not in transacciones:
            transacciones[ref] = {
                'tipo': tipo_mov.upper(),
                'productos': 0,
                'cantidad': 0
            }
        transacciones[ref]['productos'] += 1
        transacciones[ref]['cantidad'] += amount
        
        # Calcular totales
        if tipo_mov in tipos_suma:
            total_entradas += amount
            count_entradas += 1
        else:
            total_salidas += amount
            count_salidas += 1
    
    print("-" * 120)
    
    print(f"\nTRANSACCIONES AGRUPADAS ({len(transacciones)}):")
    print("-" * 60)
    for ref, data in transacciones.items():
        print(f"  {ref}: tipo={data['tipo']}, productos={data['productos']}, cantidad={data['cantidad']}")
    
    print(f"\n{'='*60}")
    print("RESUMEN CALCULADO:")
    print(f"{'='*60}")
    print(f"  total_transacciones: {len(transacciones)}")
    print(f"  total_movimientos:   {movimientos.count()}")
    print(f"  total_entradas:      {total_entradas} unidades")
    print(f"  count_entradas:      {count_entradas} registros")
    print(f"  total_salidas:       {total_salidas} unidades")
    print(f"  count_salidas:       {count_salidas} registros")
    print(f"  diferencia:          {total_entradas - total_salidas} unidades")
    print(f"{'='*60}\n")
    
    # Verificar tipos únicos
    tipos_unicos = Movimiento.objects.filter(
        fecha__date__gte='2026-01-01',
        fecha__date__lte='2026-01-03'
    ).values_list('tipo', flat=True).distinct()
    print(f"Tipos de movimiento en BD: {list(tipos_unicos)}")

if __name__ == '__main__':
    diagnosticar()
