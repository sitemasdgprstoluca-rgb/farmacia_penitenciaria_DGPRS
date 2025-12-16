"""
Script para diagnosticar la requisición 3 que el usuario está intentando surtir
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Centro, Lote, Requisicion, DetalleRequisicion
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone

User = get_user_model()

print("="*80)
print("DIAGNÓSTICO DE REQUISICIÓN 3")
print("="*80)

# 1. Obtener la requisición
try:
    req = Requisicion.objects.get(pk=3)
    print(f"\n✓ Requisición encontrada:")
    print(f"  - ID: {req.pk}")
    print(f"  - Número/Folio: {req.numero or req.folio or 'N/A'}")
    print(f"  - Estado: {req.estado}")
    print(f"  - Centro destino: {req.centro.nombre if req.centro else 'Sin centro'}")
    if req.centro:
        print(f"  - Centro destino ID: {req.centro.id}")
except Requisicion.DoesNotExist:
    print(f"\n⚠️ No existe requisición con ID=3")
    # Buscar requisiciones disponibles
    reqs = Requisicion.objects.all()[:5]
    print(f"\nRequisiciones disponibles (primeras 5):")
    for r in reqs:
        print(f"  - ID {r.pk}: {r.numero or r.folio or 'Sin número'} - Estado: {r.estado}")
    sys.exit(1)

# 2. Ver detalles de la requisición
print(f"\n{'='*80}")
print(f"PRODUCTOS SOLICITADOS:")
print(f"{'='*80}")

hoy = timezone.now().date()
detalles = req.detalles.select_related('producto').all()

for det in detalles:
    print(f"\nProducto: {det.producto.clave} - {det.producto.nombre}")
    print(f"  - Cantidad solicitada: {det.cantidad_solicitada}")
    print(f"  - Cantidad autorizada: {det.cantidad_autorizada}")
    print(f"  - Cantidad surtida: {det.cantidad_surtida or 0}")
    pendiente = (det.cantidad_autorizada or det.cantidad_solicitada) - (det.cantidad_surtida or 0)
    print(f"  - Pendiente de surtir: {pendiente}")
    
    # Verificar stock en farmacia central
    lotes_disponibles = Lote.objects.filter(
        centro__isnull=True,  # Farmacia central
        producto=det.producto,
        activo=True,
        cantidad_actual__gt=0,
        fecha_caducidad__gte=hoy
    ).order_by('fecha_caducidad')
    
    stock_total = sum(l.cantidad_actual for l in lotes_disponibles)
    
    print(f"  - Stock disponible en farmacia: {stock_total} unidades")
    print(f"  - Lotes disponibles: {lotes_disponibles.count()}")
    
    if stock_total >= pendiente:
        print(f"  ✓ Stock suficiente para surtir")
        for l in lotes_disponibles[:3]:
            print(f"    - Lote {l.numero_lote}: {l.cantidad_actual} uds (vence: {l.fecha_caducidad})")
    else:
        print(f"  ⚠️ Stock insuficiente. Faltante: {pendiente - stock_total}")
        if lotes_disponibles.exists():
            print(f"    Lotes disponibles:")
            for l in lotes_disponibles:
                print(f"    - Lote {l.numero_lote}: {l.cantidad_actual} uds (vence: {l.fecha_caducidad})")

# 3. Verificar usuario farmacia
print(f"\n{'='*80}")
print(f"USUARIO FARMACIA:")
print(f"{'='*80}")

try:
    user_farmacia = User.objects.get(username='farmacia')
    print(f"  - Username: {user_farmacia.username}")
    print(f"  - Rol: {user_farmacia.rol}")
    print(f"  - Centro asignado: {user_farmacia.centro.nombre if user_farmacia.centro else 'Sin centro (Farmacia Central)'}")
    print(f"  - Es superuser: {user_farmacia.is_superuser}")
    print(f"  - Es staff: {user_farmacia.is_staff}")
except User.DoesNotExist:
    print(f"  ⚠️ No existe usuario 'farmacia'")

# 4. Verificar permisos
print(f"\n{'='*80}")
print(f"VERIFICACIÓN DE PERMISOS:")
print(f"{'='*80}")

from inventario.services import is_farmacia_or_admin, get_user_centro

try:
    es_farmacia = is_farmacia_or_admin(user_farmacia)
    print(f"  - is_farmacia_or_admin: {es_farmacia}")
    
    user_centro = get_user_centro(user_farmacia)
    print(f"  - Centro del usuario: {user_centro.nombre if user_centro else 'Sin centro (Farmacia Central)'}")
except Exception as e:
    print(f"  ⚠️ Error al verificar permisos: {e}")

# 5. Verificar si puede surtir
print(f"\n{'='*80}")
print(f"¿PUEDE SURTIR?")
print(f"{'='*80}")

estado_valido = req.estado.lower() in ['autorizada', 'en_surtido', 'parcial']
print(f"  - Estado válido para surtir: {estado_valido}")
print(f"  - Estado actual: {req.estado}")
print(f"  - Estados válidos: autorizada, en_surtido, parcial")

if estado_valido:
    print(f"\n  ✓ La requisición puede ser surtida (estado correcto)")
else:
    print(f"\n  ⚠️ La requisición NO puede ser surtida en su estado actual")
    print(f"     Se requiere autorizar primero la requisición")

# 6. Verificar transición de estado
print(f"\n{'='*80}")
print(f"MÁQUINA DE ESTADOS:")
print(f"{'='*80}")

from inventario.services.state_machine import EstadoRequisicion

try:
    estado_enum = EstadoRequisicion.from_string(req.estado)
    print(f"  - Estado actual (enum): {estado_enum}")
    print(f"  - Estado actual (valor): {estado_enum.value}")
except Exception as e:
    print(f"  ⚠️ Error al procesar estado: {e}")

print(f"\nTransiciones posibles desde '{req.estado}':")
from inventario.services.state_machine import TRANSICIONES_REQUISICION
transiciones_disponibles = [
    t for t in TRANSICIONES_REQUISICION 
    if t['origen'].lower() == req.estado.lower()
]
for t in transiciones_disponibles:
    print(f"  - {t['origen']} → {t['destino']} (acción: {t.get('accion', 'N/A')})")

if not transiciones_disponibles:
    print(f"  ⚠️ No hay transiciones disponibles desde '{req.estado}'")
