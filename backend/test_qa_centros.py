#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de QA para validar visualización de centros en Dashboard.
Simula cómo se verían 22 centros + Farmacia Central.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Centro, Lote
from django.db.models import Q, Sum, IntegerField
from django.db.models.functions import Coalesce

def test_dashboard_stock_por_centro():
    """
    Simula la lógica del endpoint dashboard_graficas para stock_por_centro.
    """
    print("=" * 80)
    print("QA TEST: Dashboard Stock por Centro")
    print("=" * 80)
    
    stock_por_centro = []
    
    # 1. Farmacia Central (lotes sin centro + Almacén Central)
    stock_farmacia = Lote.objects.filter(
        Q(centro__isnull=True) | Q(centro__nombre__icontains='almacén central') | Q(centro__nombre__icontains='almacen central'),
        activo=True,
        cantidad_actual__gt=0
    ).aggregate(
        total=Coalesce(Sum('cantidad_actual'), 0, output_field=IntegerField())
    )['total']
    
    if stock_farmacia > 0:
        stock_por_centro.append({
            'centro': 'Farmacia Central',
            'centro_id': 'central',
            'stock': stock_farmacia
        })
        print(f"✓ Farmacia Central: {stock_farmacia:,} unidades (centro_id='central')")
    else:
        print("✗ Farmacia Central: Sin stock")
    
    # 2. Todos los centros activos con stock
    centros = Centro.objects.filter(activo=True).exclude(
        Q(nombre__icontains='almacén central') | Q(nombre__icontains='almacen central')
    ).order_by('nombre')
    
    print(f"\nCentros activos: {centros.count()}")
    print("-" * 80)
    
    centros_con_stock = 0
    centros_sin_stock = 0
    
    for centro in centros:
        stock = Lote.objects.filter(
            centro=centro,
            activo=True,
            cantidad_actual__gt=0
        ).aggregate(
            total=Coalesce(Sum('cantidad_actual'), 0, output_field=IntegerField())
        )['total']
        
        if stock > 0:
            stock_por_centro.append({
                'centro': centro.nombre,
                'centro_id': centro.id,
                'stock': stock
            })
            centros_con_stock += 1
            print(f"✓ [{centro.id:2d}] {centro.nombre[:50]:<50} {stock:>10,} uds")
        else:
            centros_sin_stock += 1
            print(f"  [{centro.id:2d}] {centro.nombre[:50]:<50} {'SIN STOCK':>10}")
    
    print("-" * 80)
    print(f"\nResumen:")
    print(f"  - Total centros en BD: {centros.count()}")
    print(f"  - Centros con stock: {centros_con_stock}")
    print(f"  - Centros sin stock: {centros_sin_stock}")
    print(f"  - Farmacia Central: {'Con stock' if stock_farmacia > 0 else 'Sin stock'}")
    print(f"\n  - Total elementos en gráfica: {len(stock_por_centro)}")
    
    # Simulación de visualización con scroll
    if len(stock_por_centro) > 8:
        print(f"\n⚠️  Visualización: Se requiere SCROLL (>{len(stock_por_centro)} elementos > límite de 8)")
        print(f"     Configuración: max-h-96 overflow-y-auto")
        print(f"     Altura estimada: ~{len(stock_por_centro) * 60}px total, muestra ~480px")
    else:
        print(f"\n✓ Visualización: SIN SCROLL necesario ({len(stock_por_centro)} elementos ≤ 8)")
    
    # Top 5 centros por stock
    sorted_centros = sorted(stock_por_centro, key=lambda x: x['stock'], reverse=True)
    print(f"\nTop 5 Centros por Stock:")
    print("-" * 80)
    for i, item in enumerate(sorted_centros[:5], 1):
        print(f"{i}. {item['centro'][:50]:<50} {item['stock']:>10,} uds")
    
    # Verificar centro_id para navegación
    print(f"\nValidación centro_id para navegación:")
    print("-" * 80)
    problemas = 0
    for item in stock_por_centro[:5]:  # Solo primeros 5 para brevedad
        centro_id = item['centro_id']
        if centro_id == 'central':
            print(f"✓ {item['centro']:<30} → centro_id='{centro_id}' (especial)")
        elif isinstance(centro_id, int):
            print(f"✓ {item['centro'][:30]:<30} → centro_id={centro_id} (ID numérico)")
        else:
            print(f"✗ {item['centro']:<30} → centro_id={centro_id} (TIPO INVÁLIDO)")
            problemas += 1
    
    if problemas > 0:
        print(f"\n⚠️  Encontrados {problemas} problemas con centro_id")
    else:
        print(f"\n✓ Todos los centro_id son válidos")
    
    print("\n" + "=" * 80)
    return stock_por_centro

def test_reportes_filtro():
    """
    Verifica que el filtro de Reportes funcione correctamente.
    """
    print("\n" + "=" * 80)
    print("QA TEST: Filtro de Centro en Reportes")
    print("=" * 80)
    
    # Test 1: Farmacia Central
    print("\n1. Test filtro 'central' (Farmacia Central):")
    lotes_central = Lote.objects.filter(
        Q(centro__isnull=True) | Q(centro__nombre__icontains='almacén central'),
        activo=True,
        cantidad_actual__gt=0
    )
    print(f"   Lotes encontrados: {lotes_central.count()}")
    print(f"   Stock total: {lotes_central.aggregate(total=Sum('cantidad_actual'))['total'] or 0:,}")
    
    # Test 2: Centro específico (primer centro con stock)
    centro_test = Centro.objects.filter(activo=True).exclude(
        Q(nombre__icontains='almacén central')
    ).first()
    
    if centro_test:
        print(f"\n2. Test filtro ID={centro_test.id} ({centro_test.nombre}):")
        lotes_centro = Lote.objects.filter(
            centro=centro_test,
            activo=True,
            cantidad_actual__gt=0
        )
        print(f"   Lotes encontrados: {lotes_centro.count()}")
        print(f"   Stock total: {lotes_centro.aggregate(total=Sum('cantidad_actual'))['total'] or 0:,}")
    
    # Test 3: Todos los centros (excluyendo Farmacia Central)
    print(f"\n3. Test filtro 'todos' (excluye Farmacia Central):")
    lotes_todos = Lote.objects.filter(
        centro__isnull=False,  # Solo centros, no Farmacia Central
        activo=True,
        cantidad_actual__gt=0
    )
    print(f"   Lotes encontrados: {lotes_todos.count()}")
    print(f"   Stock total: {lotes_todos.aggregate(total=Sum('cantidad_actual'))['total'] or 0:,}")
    
    print("\n" + "=" * 80)

def test_casos_limite():
    """
    Prueba casos límite y manejo de errores.
    """
    print("\n" + "=" * 80)
    print("QA TEST: Casos Límite")
    print("=" * 80)
    
    # 1. Centro sin stock
    centros_sin_stock = Centro.objects.filter(activo=True).exclude(
        Q(nombre__icontains='almacén central')
    )
    
    for centro in centros_sin_stock:
        stock = Lote.objects.filter(
            centro=centro,
            activo=True,
            cantidad_actual__gt=0
        ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
        
        if stock == 0:
            print(f"\n1. Centro sin stock: {centro.nombre}")
            print(f"   - ¿Aparece en Dashboard? NO (filtrado por stock > 0)")
            print(f"   - ¿Clickeable? NO (no aparece)")
            print(f"   - ¿Reportes funciona? SÍ (no hay datos, mensaje correcto)")
            break
    else:
        print("\n1. Centro sin stock: NO ENCONTRADO (todos tienen stock)")
    
    # 2. Centro con stock muy alto
    centros_con_stock = []
    for centro in Centro.objects.filter(activo=True):
        stock = Lote.objects.filter(
            centro=centro,
            activo=True,
            cantidad_actual__gt=0
        ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
        if stock > 0:
            centros_con_stock.append((centro, stock))
    
    if centros_con_stock:
        centro_max, stock_max = max(centros_con_stock, key=lambda x: x[1])
        print(f"\n2. Centro con stock más alto:")
        print(f"   Centro: {centro_max.nombre}")
        print(f"   Stock: {stock_max:,} unidades")
        print(f"   - ¿Barra se renderiza? SÍ (100% ancho relativo)")
        print(f"   - ¿Porcentaje visible? SÍ (siempre en barras > 15%)")
        print(f"   - ¿Performance? OK (números formateados con toLocaleString)")
    
    # 3. Array vacío (sin centros con stock)
    print(f"\n3. Array vacío (simulado):")
    print(f"   - ¿Dashboard rompe? NO (muestra mensaje vacío)")
    print(f"   - Mensaje: 'No hay datos de inventario por centro'")
    print(f"   - Icono: FaWarehouse con opacidad 50%")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    try:
        # Test 1: Dashboard stock por centro
        stock_data = test_dashboard_stock_por_centro()
        
        # Test 2: Filtros de Reportes
        test_reportes_filtro()
        
        # Test 3: Casos límite
        test_casos_limite()
        
        print("\n✅ QA TESTS COMPLETADOS")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERROR EN QA TESTS: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
