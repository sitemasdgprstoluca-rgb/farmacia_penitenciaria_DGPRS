"""Script para verificar integridad completa del sistema."""
import os
import sys
from decimal import Decimal

import django
from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.db.models import Count, Sum, F

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from core.models import Centro, Producto, Lote, Requisicion, DetalleRequisicion, Movimiento  # noqa: E402

User = get_user_model()

print("=" * 80)
print("VERIFICACION DE INTEGRIDAD DEL SISTEMA - FARMACIA PENITENCIARIA")
print("=" * 80)

print("\nESTADISTICAS GENERALES")
print("-" * 80)
print(f"Usuarios registrados: {User.objects.count()}")
print(f"Centros penitenciarios: {Centro.objects.count()}")
print(f"Productos en catalogo: {Producto.objects.count()}")
try:
    print(f"Lotes registrados: {Lote.objects.count()}")
except OperationalError as exc:
    print(f"Lotes registrados: ERROR ({exc})")
print(f"Requisiciones totales: {Requisicion.objects.count()}")
print(f"Movimientos de inventario: {Movimiento.objects.count()}")

print("\nINTEGRIDAD DE USUARIOS")
print("-" * 80)
usuarios_sin_centro = User.objects.filter(centro__isnull=True, is_superuser=False).count()
usuarios_con_centro = User.objects.filter(centro__isnull=False).count()
print(f"Usuarios con centro asignado: {usuarios_con_centro}")
print(f"Usuarios sin centro (no-superuser): {usuarios_sin_centro}")

print("\nINTEGRIDAD DE PRODUCTOS Y LOTES")
print("-" * 80)
try:
    productos_sin_lotes = Producto.objects.annotate(num_lotes=Count("lotes")).filter(num_lotes=0).count()
    productos_con_lotes = Producto.objects.annotate(num_lotes=Count("lotes")).filter(num_lotes__gt=0).count()
    print(f"Productos con lotes: {productos_con_lotes}")
    print(f"Productos sin lotes: {productos_sin_lotes}")
    lotes_stock_negativo = Lote.objects.filter(cantidad_actual__lt=0).count()
    lotes_stock_mayor = Lote.objects.filter(cantidad_actual__gt=F("cantidad_inicial")).count()
    print(f"Lotes con stock negativo: {lotes_stock_negativo}")
    print(f"Lotes con stock > cantidad inicial: {lotes_stock_mayor}")
except OperationalError as exc:
    print(f"No se pudo verificar lotes (posible migracion pendiente): {exc}")

print("\nINTEGRIDAD DE REQUISICIONES")
print("-" * 80)
requisiciones_por_estado = Requisicion.objects.values("estado").annotate(total=Count("id"))
for item in requisiciones_por_estado:
    print(f"  {item['estado']:15}: {item['total']:3} requisiciones")
req_sin_detalles = Requisicion.objects.annotate(num_detalles=Count("detalles")).filter(num_detalles=0).count()
print(f"Requisiciones sin detalles: {req_sin_detalles}")
req_autorizadas_sin_autorizador = Requisicion.objects.filter(estado="autorizada", autorizador__isnull=True).count()
print(f"Requisiciones autorizadas sin autorizador: {req_autorizadas_sin_autorizador}")

print("\nINTEGRIDAD DE MOVIMIENTOS")
print("-" * 80)
movimientos_por_tipo = Movimiento.objects.values("tipo").annotate(total=Count("id"))
for item in movimientos_por_tipo:
    print(f"  {item['tipo']:15}: {item['total']:3} movimientos")
mov_sin_lote = Movimiento.objects.filter(lote__isnull=True).count()
mov_cantidad_invalida = Movimiento.objects.filter(cantidad__lte=0).count()
print(f"Movimientos sin lote: {mov_sin_lote}")
print(f"Movimientos con cantidad <= 0: {mov_cantidad_invalida}")

print("\nFIN DE VERIFICACION")
