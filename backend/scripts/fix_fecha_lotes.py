"""
FIX URGENTE: Sincronizar fecha_fabricacion de lotes con sus parcialidades.

Para lotes que tienen parcialidades pero no tienen fecha_fabricacion,
copia la fecha de la primera parcialidad al campo fecha_fabricacion del lote.

EJECUCIÓN EN RENDER:
1. Ir a Render Dashboard > tu servicio > Shell
2. Ejecutar: python manage.py shell
3. Copiar y pegar este código

O desde línea de comandos:
python manage.py shell < scripts/fix_fecha_lotes.py
"""

from core.models import Lote, LoteParcialidad
from django.db import transaction

def fix_lotes_sin_fecha():
    """
    Sincroniza fecha_fabricacion de lotes usando sus parcialidades.
    """
    print("=" * 60)
    print("FIX: Sincronizar fecha_fabricacion desde parcialidades")
    print("=" * 60)
    
    # Buscar lotes activos sin fecha_fabricacion
    lotes_sin_fecha = Lote.objects.filter(
        fecha_fabricacion__isnull=True,
        activo=True
    ).select_related('producto')
    
    total = lotes_sin_fecha.count()
    print(f"\nLotes activos sin fecha_fabricacion: {total}")
    
    if total == 0:
        print("✓ Todos los lotes ya tienen fecha_fabricacion")
        return
    
    actualizados = 0
    sin_parcialidad = 0
    
    with transaction.atomic():
        for lote in lotes_sin_fecha:
            # Buscar la primera parcialidad del lote
            parcialidad = LoteParcialidad.objects.filter(
                lote=lote
            ).order_by('fecha_entrega').first()
            
            if parcialidad and parcialidad.fecha_entrega:
                # Actualizar el lote con la fecha de la parcialidad
                lote.fecha_fabricacion = parcialidad.fecha_entrega
                lote.save(update_fields=['fecha_fabricacion'])
                actualizados += 1
                print(f"  ✓ Lote {lote.numero_lote} ({lote.producto.clave if lote.producto else '?'}): fecha = {parcialidad.fecha_entrega}")
            else:
                # Si no tiene parcialidad, usar created_at
                if lote.created_at:
                    from django.utils import timezone
                    fecha = lote.created_at.date() if hasattr(lote.created_at, 'date') else lote.created_at
                    lote.fecha_fabricacion = fecha
                    lote.save(update_fields=['fecha_fabricacion'])
                    actualizados += 1
                    print(f"  ✓ Lote {lote.numero_lote}: fecha = {fecha} (de created_at)")
                else:
                    sin_parcialidad += 1
                    print(f"  ! Lote {lote.numero_lote}: sin parcialidad ni created_at")
    
    print(f"\n{'=' * 60}")
    print(f"RESULTADO:")
    print(f"  - Lotes actualizados: {actualizados}")
    print(f"  - Sin datos para sincronizar: {sin_parcialidad}")
    print("=" * 60)

# Ejecutar automáticamente
fix_lotes_sin_fecha()
