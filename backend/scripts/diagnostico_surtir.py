#!/usr/bin/env python
"""
Script de diagnóstico para el endpoint de surtir requisiciones.
Ejecutar en el servidor con: python manage.py shell < scripts/diagnostico_surtir.py

Este script verifica:
1. Estado de requisiciones pendientes de surtir
2. Stock disponible en farmacia central
3. Detalles de requisiciones con sus cantidades
4. Posibles problemas de datos
"""

import os
import sys
import django

# Setup Django si se ejecuta directamente
if not hasattr(django, 'apps') or not django.apps.apps.ready:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

from django.utils import timezone
from django.db.models import Sum, F
from django.db.models.functions import Coalesce
from core.models import Requisicion, DetalleRequisicion, Lote, Producto, Centro, Usuario
from core.constants import ESTADOS_COMPROMETIDOS

print("=" * 80)
print("DIAGNÓSTICO DE SURTIR REQUISICIONES")
print("=" * 80)

hoy = timezone.now().date()
print(f"\nFecha actual: {hoy}")

# 1. Verificar requisiciones en estado autorizada/en_surtido
print("\n" + "=" * 40)
print("1. REQUISICIONES PENDIENTES DE SURTIR")
print("=" * 40)

estados_surtibles = ['autorizada', 'en_surtido', 'autorizada_farmacia', 'parcial']
requisiciones = Requisicion.objects.filter(estado__in=estados_surtibles)
print(f"Total requisiciones en estados surtibles: {requisiciones.count()}")

for req in requisiciones[:10]:
    centro_nombre = req.centro.nombre if req.centro else "Sin centro"
    print(f"\n  ID: {req.pk}")
    print(f"  Número: {req.numero}")
    print(f"  Estado: {req.estado}")
    print(f"  Centro: {centro_nombre}")
    print(f"  Fecha creación: {req.created_at}")
    
    # Verificar detalles
    detalles = req.detalles.all()
    print(f"  Detalles: {detalles.count()}")
    
    for det in detalles[:5]:
        producto_info = f"{det.producto.clave} - {det.producto.nombre[:30]}..." if det.producto else "SIN PRODUCTO"
        print(f"    - {producto_info}")
        print(f"      Solicitada: {det.cantidad_solicitada}, Autorizada: {det.cantidad_autorizada}, Surtida: {det.cantidad_surtida}")
        if det.cantidad_autorizada is None:
            print(f"      ⚠️ ALERTA: cantidad_autorizada es NULL!")
        if det.lote:
            print(f"      Lote específico: {det.lote.numero_lote}")

# 2. Verificar stock en farmacia central
print("\n" + "=" * 40)
print("2. STOCK EN FARMACIA CENTRAL")
print("=" * 40)

# Lotes en farmacia central (centro=NULL)
lotes_farmacia = Lote.objects.filter(
    centro__isnull=True,
    activo=True,
    cantidad_actual__gt=0
)
print(f"Total lotes activos en farmacia central: {lotes_farmacia.count()}")

# Lotes NO vencidos
lotes_vigentes = lotes_farmacia.filter(fecha_caducidad__gte=hoy)
print(f"Lotes vigentes (no vencidos): {lotes_vigentes.count()}")

# Lotes vencidos
lotes_vencidos = lotes_farmacia.filter(fecha_caducidad__lt=hoy)
print(f"Lotes VENCIDOS: {lotes_vencidos.count()}")

# Stock total
stock_total = lotes_vigentes.aggregate(total=Sum('cantidad_actual'))['total'] or 0
print(f"Stock total disponible (vigente): {stock_total}")

# Mostrar primeros 10 lotes
print("\nPrimeros 10 lotes en farmacia central:")
for lote in lotes_vigentes.select_related('producto')[:10]:
    print(f"  - {lote.producto.clave}: {lote.numero_lote} = {lote.cantidad_actual} unidades (vence: {lote.fecha_caducidad})")

# 3. Verificar si hay productos sin stock
print("\n" + "=" * 40)
print("3. PRODUCTOS EN REQUISICIONES VS STOCK")
print("=" * 40)

for req in requisiciones[:5]:
    print(f"\nRequisición {req.numero}:")
    for det in req.detalles.select_related('producto').all():
        if not det.producto:
            print(f"  ⚠️ Detalle sin producto (ID: {det.pk})")
            continue
            
        # Verificar stock para este producto
        stock = Lote.objects.filter(
            producto=det.producto,
            centro__isnull=True,
            activo=True,
            cantidad_actual__gt=0,
            fecha_caducidad__gte=hoy
        ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
        
        requerido = (det.cantidad_autorizada or det.cantidad_solicitada or 0) - (det.cantidad_surtida or 0)
        
        status = "✓" if stock >= requerido else "❌ INSUFICIENTE"
        print(f"  {status} {det.producto.clave}: necesita {requerido}, stock disponible: {stock}")

# 4. Verificar centros
print("\n" + "=" * 40)
print("4. CENTROS EN EL SISTEMA")
print("=" * 40)

centros = Centro.objects.all()
print(f"Total centros: {centros.count()}")
for centro in centros:
    lotes_centro = Lote.objects.filter(centro=centro, activo=True).count()
    print(f"  - {centro.nombre} (ID: {centro.pk}): {lotes_centro} lotes")

# 5. Verificar usuarios de farmacia
print("\n" + "=" * 40)
print("5. USUARIOS DE FARMACIA")
print("=" * 40)

usuarios_farmacia = Usuario.objects.filter(rol__in=['farmacia', 'admin_farmacia', 'admin'])
print(f"Usuarios con rol de farmacia: {usuarios_farmacia.count()}")
for u in usuarios_farmacia[:5]:
    print(f"  - {u.username} (rol: {u.rol})")

# 6. Stock comprometido
print("\n" + "=" * 40)
print("6. STOCK COMPROMETIDO POR OTRAS REQUISICIONES")
print("=" * 40)

comprometido = DetalleRequisicion.objects.filter(
    requisicion__estado__in=ESTADOS_COMPROMETIDOS
).values('producto__clave', 'producto__nombre').annotate(
    total_autorizado=Sum('cantidad_autorizada'),
    total_surtido=Sum('cantidad_surtida'),
    pendiente=Sum(F('cantidad_autorizada') - Coalesce(F('cantidad_surtida'), 0))
).filter(pendiente__gt=0)

print(f"Productos con stock comprometido: {comprometido.count()}")
for item in list(comprometido)[:10]:
    print(f"  - {item['producto__clave']}: {item['pendiente']} pendientes")

# 7. Verificar posibles problemas de datos
print("\n" + "=" * 40)
print("7. VERIFICACIÓN DE INTEGRIDAD")
print("=" * 40)

# Detalles sin producto
detalles_sin_producto = DetalleRequisicion.objects.filter(producto__isnull=True).count()
print(f"Detalles sin producto: {detalles_sin_producto}")

# Requisiciones sin centro
req_sin_centro = Requisicion.objects.filter(centro__isnull=True).count()
print(f"Requisiciones sin centro: {req_sin_centro}")

# Lotes con cantidad negativa
lotes_negativos = Lote.objects.filter(cantidad_actual__lt=0).count()
print(f"Lotes con cantidad negativa: {lotes_negativos}")

# Productos sin lotes en farmacia
productos_en_detalles = DetalleRequisicion.objects.filter(
    requisicion__estado__in=estados_surtibles
).values_list('producto_id', flat=True).distinct()

productos_sin_lotes = []
for prod_id in productos_en_detalles:
    if prod_id:
        tiene_lote = Lote.objects.filter(
            producto_id=prod_id,
            centro__isnull=True,
            activo=True,
            cantidad_actual__gt=0,
            fecha_caducidad__gte=hoy
        ).exists()
        if not tiene_lote:
            productos_sin_lotes.append(prod_id)

print(f"Productos en requisiciones surtibles SIN stock en farmacia: {len(productos_sin_lotes)}")
if productos_sin_lotes:
    for pid in productos_sin_lotes[:5]:
        p = Producto.objects.filter(pk=pid).first()
        if p:
            print(f"  - {p.clave}: {p.nombre[:40]}...")

print("\n" + "=" * 80)
print("FIN DEL DIAGNÓSTICO")
print("=" * 80)
