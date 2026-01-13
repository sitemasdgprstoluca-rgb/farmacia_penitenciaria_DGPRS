#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de diagnóstico para requisición que muestra ENTREGADA pero sin productos en centro.
Ejecutar con: python manage.py shell < diagnostico_requisicion.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Requisicion, Movimiento, Lote, DetalleRequisicion
from django.db.models import Q

print("=" * 80)
print("DIAGNÓSTICO DE REQUISICIÓN ENTREGADA SIN PRODUCTOS EN CENTRO")
print("=" * 80)

# PRIMERO: Verificar si hay ALGÚN movimiento con referencia REQ-20260112-1887
print("\n🔎 BUSCANDO MOVIMIENTOS CON REFERENCIA REQ-20260112-1887...")
movimientos_ref = Movimiento.objects.filter(
    Q(referencia__icontains='REQ-20260112-1887') | 
    Q(motivo__icontains='REQ-20260112-1887')
)
print(f"   Encontrados: {movimientos_ref.count()} movimientos")
for mov in movimientos_ref:
    print(f"   - ID={mov.pk}, Tipo={mov.tipo}, Cantidad={mov.cantidad}, Ref={mov.referencia}, Motivo={mov.motivo[:50] if mov.motivo else 'N/A'}...")

# SEGUNDO: Verificar stock de productos en Almacén Central
print("\n🔎 VERIFICANDO STOCK EN ALMACÉN CENTRAL (centro=NULL)...")
from core.models import Producto
productos_claves = ['615', '617', '618']
for clave in productos_claves:
    prod = Producto.objects.filter(clave=clave).first()
    if prod:
        lotes_almacen = Lote.objects.filter(
            producto=prod,
            centro__isnull=True,
            activo=True
        )
        total_stock = sum(l.cantidad_actual for l in lotes_almacen)
        print(f"   Producto {clave}: {lotes_almacen.count()} lotes, Stock total: {total_stock}")
        for lote in lotes_almacen[:3]:
            print(f"      - Lote {lote.numero_lote}: {lote.cantidad_actual} unidades")

print("\n" + "=" * 80)

# Buscar requisiciones con estado 'entregada'
requisiciones_entregadas = Requisicion.objects.filter(
    estado='entregada'
).select_related('centro_origen', 'centro_destino').order_by('-fecha_entrega')[:5]

print(f"\n📋 Últimas {requisiciones_entregadas.count()} requisiciones ENTREGADAS:")
print("-" * 80)

for req in requisiciones_entregadas:
    print(f"\n🔹 REQUISICIÓN: {req.numero}")
    print(f"   Estado: {req.estado}")
    print(f"   Centro Origen: {req.centro_origen.nombre if req.centro_origen else 'NULL (Almacén Central)'}")
    print(f"   Centro Destino: {req.centro_destino.nombre if req.centro_destino else 'NULL (Almacén Central)'}")
    print(f"   Fecha Entrega: {req.fecha_entrega}")
    
    # Buscar detalles de la requisición
    detalles = req.detalles.all().select_related('producto', 'lote')
    print(f"\n   📦 DETALLES ({detalles.count()} items):")
    for det in detalles:
        print(f"      - {det.producto.clave}: Solicitado={det.cantidad_solicitada}, "
              f"Autorizado={det.cantidad_autorizada}, Surtido={det.cantidad_surtida}, "
              f"Lote={det.lote.numero_lote if det.lote else 'NULL'}")
    
    # Buscar movimientos asociados a esta requisición
    movimientos = Movimiento.objects.filter(requisicion=req).select_related(
        'lote__producto', 'centro_origen', 'centro_destino'
    )
    print(f"\n   📊 MOVIMIENTOS ASOCIADOS ({movimientos.count()} movimientos):")
    for mov in movimientos:
        centro_origen_str = mov.centro_origen.nombre if mov.centro_origen else 'NULL (Almacén Central)'
        centro_destino_str = mov.centro_destino.nombre if mov.centro_destino else 'NULL (Almacén Central)'
        centro_lote_str = mov.lote.centro.nombre if mov.lote and mov.lote.centro else 'NULL (Almacén Central)'
        print(f"      - {mov.tipo.upper()}: {mov.lote.producto.clave if mov.lote else 'N/A'}, "
              f"Cantidad={mov.cantidad}, "
              f"Lote.Centro={centro_lote_str}, "
              f"Origen={centro_origen_str}, "
              f"Destino={centro_destino_str}, "
              f"Motivo={mov.motivo[:50] if mov.motivo else 'N/A'}...")
    
    # Buscar lotes del centro_origen (que es quien pidió)
    if req.centro_origen:
        centro_solicitante = req.centro_origen
        lotes_centro = Lote.objects.filter(
            centro=centro_solicitante,
            activo=True,
            cantidad_actual__gt=0
        ).select_related('producto')
        
        print(f"\n   🏥 LOTES EN CENTRO '{centro_solicitante.nombre}' ({lotes_centro.count()} lotes activos con stock):")
        for lote in lotes_centro[:10]:
            print(f"      - {lote.producto.clave}: Lote={lote.numero_lote}, Stock={lote.cantidad_actual}")
        
        # ¿Hay lotes relacionados con los productos de esta requisición?
        productos_req = [det.producto for det in detalles]
        lotes_req_productos = Lote.objects.filter(
            centro=centro_solicitante,
            producto__in=productos_req
        )
        print(f"\n   🔍 LOTES EN CENTRO para productos de esta REQ ({lotes_req_productos.count()} lotes):")
        for lote in lotes_req_productos:
            print(f"      - {lote.producto.clave}: Lote={lote.numero_lote}, "
                  f"Stock={lote.cantidad_actual}, Activo={lote.activo}")
    
    print("\n" + "=" * 80)

# Verificar si hay movimientos de ENTRADA que NO tienen lote en el centro
print("\n\n🔎 VERIFICANDO MOVIMIENTOS DE ENTRADA SIN LOTE CORRECTO...")
movimientos_entrada = Movimiento.objects.filter(
    tipo='entrada',
    motivo__icontains='REQUISICION'
).select_related('lote__centro', 'centro_destino')[:20]

for mov in movimientos_entrada:
    lote_centro = mov.lote.centro.nombre if mov.lote and mov.lote.centro else 'NULL'
    mov_destino = mov.centro_destino.nombre if mov.centro_destino else 'NULL'
    print(f"MOV ID={mov.pk}: Tipo={mov.tipo}, "
          f"Lote.Centro={lote_centro}, "
          f"Mov.centro_destino={mov_destino}, "
          f"Motivo={mov.motivo[:40] if mov.motivo else 'N/A'}...")

print("\n✅ Diagnóstico completado")
