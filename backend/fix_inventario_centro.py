"""
Script para limpiar el inventario del centro penitenciario.
Crea movimientos de dispensación retroactivos para que el stock quede en 0.
"""
import os
import sys
import django

# Setup Django - DEBE ser config.settings (no backend.settings)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from django.contrib.auth import get_user_model
from inventario.models import Lote, Movimiento, Centro

User = get_user_model()

def limpiar_inventario_centro():
    """Crea movimientos de dispensación para lotes con stock en el centro."""
    
    # Buscar centro penitenciario
    centro = Centro.objects.filter(nombre__icontains='Santiaguito').first()
    if not centro:
        print('ERROR: Centro no encontrado')
        return
    
    print(f'Centro: {centro.nombre}')
    
    # Buscar lotes con stock
    lotes_activos = Lote.objects.filter(centro=centro, cantidad_actual__gt=0)
    total_lotes = lotes_activos.count()
    
    if total_lotes == 0:
        print('No hay lotes con stock en el centro. Nada que hacer.')
        return
    
    print(f'Lotes con stock: {total_lotes}')
    
    # Usuario para los movimientos
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.first()
    print(f'Usuario para movimientos: {admin_user.username}')
    
    stock_total = sum(l.cantidad_actual for l in lotes_activos)
    print(f'Stock total a dispensar: {stock_total}')
    print()
    
    with transaction.atomic():
        for lote in lotes_activos:
            cantidad = lote.cantidad_actual
            
            # Crear movimiento de dispensación
            Movimiento.objects.create(
                tipo='salida',
                producto=lote.producto,
                lote=lote,
                centro_origen=centro,
                centro_destino=None,  # Sale a pacientes
                cantidad=cantidad,
                motivo='[CONFIRMADO] Dispensación retroactiva a internos del centro',
                usuario=admin_user,
                subtipo_salida='dispensacion'
            )
            
            # Actualizar lote a stock 0
            lote.cantidad_actual = 0
            lote.activo = False
            lote.save(update_fields=['cantidad_actual', 'activo', 'updated_at'])
            
            print(f'  ✓ Lote {lote.numero_lote}: dispensado {cantidad} unidades')
    
    print()
    print(f'✓ Completado: {total_lotes} lotes dispensados, {stock_total} unidades')
    
    # Verificar que quedó en 0
    stock_final = Lote.objects.filter(centro=centro, cantidad_actual__gt=0).count()
    print(f'Lotes con stock después: {stock_final}')

if __name__ == '__main__':
    limpiar_inventario_centro()
