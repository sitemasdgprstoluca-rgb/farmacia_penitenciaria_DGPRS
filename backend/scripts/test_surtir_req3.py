"""
Script para probar el surtido de la requisición 3
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Requisicion
from django.contrib.auth import get_user_model
from inventario.services import RequisicionService
from inventario.views_legacy import is_farmacia_or_admin, get_user_centro

User = get_user_model()

print("="*80)
print("PRUEBA DE SURTIDO DE REQUISICIÓN 3")
print("="*80)

# 1. Obtener la requisición
try:
    req = Requisicion.objects.get(pk=3)
    print(f"\n✓ Requisición encontrada:")
    print(f"  - ID: {req.pk}")
    print(f"  - Número/Folio: {req.numero or req.folio or 'N/A'}")
    print(f"  - Estado: {req.estado}")
except Requisicion.DoesNotExist:
    print(f"\n⚠️ No existe requisición con ID=3")
    sys.exit(1)

# 2. Obtener usuario farmacia
try:
    user_farmacia = User.objects.get(username='farmacia')
    print(f"\n✓ Usuario farmacia encontrado:")
    print(f"  - Username: {user_farmacia.username}")
    print(f"  - Rol: {user_farmacia.rol}")
except User.DoesNotExist:
    print(f"\n⚠️ No existe usuario 'farmacia'")
    sys.exit(1)

# 3. Intentar surtir
print(f"\n{'='*80}")
print(f"INTENTANDO SURTIR REQUISICIÓN {req.pk}")
print(f"{'='*80}")

try:
    service = RequisicionService(req, user_farmacia)
    
    print(f"\n✓ Servicio creado correctamente")
    print(f"  Iniciando proceso de surtido...")
    
    resultado = service.surtir(
        is_farmacia_or_admin_fn=is_farmacia_or_admin,
        get_user_centro_fn=get_user_centro
    )
    
    print(f"\n{'='*80}")
    print(f"✓ ¡SURTIDO EXITOSO!")
    print(f"{'='*80}")
    print(f"\nResultado:")
    print(f"  - Success: {resultado.get('success')}")
    print(f"  - Estado final: {resultado.get('estado_final', 'N/A')}")
    print(f"  - Mensaje: {resultado.get('mensaje', 'N/A')}")
    
    # Refrescar requisición para ver el estado actualizado
    req.refresh_from_db()
    print(f"\nEstado actualizado de la requisición:")
    print(f"  - Estado: {req.estado}")
    print(f"  - Fecha surtido: {req.fecha_surtido if hasattr(req, 'fecha_surtido') else 'N/A'}")
    
    # Mostrar detalles de lo que se surtió
    if 'items_surtidos' in resultado:
        print(f"\nProductos surtidos:")
        for item in resultado['items_surtidos'][:5]:  # Mostrar primeros 5
            print(f"  - {item.get('producto_clave')}: {item.get('cantidad')} unidades desde lote {item.get('lote_numero')}")
    
except Exception as e:
    print(f"\n{'='*80}")
    print(f"❌ ERROR AL SURTIR")
    print(f"{'='*80}")
    print(f"\nTipo de error: {type(e).__name__}")
    print(f"Mensaje: {str(e)}")
    
    import traceback
    print(f"\nTraceback completo:")
    print(traceback.format_exc())
    
    sys.exit(1)

print(f"\n{'='*80}")
print(f"PRUEBA COMPLETADA EXITOSAMENTE")
print(f"{'='*80}")
