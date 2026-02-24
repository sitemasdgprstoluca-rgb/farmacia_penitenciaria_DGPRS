"""
Script para sincronizar fecha_fabricacion de lotes existentes.

Si un lote no tiene fecha_fabricacion pero tiene parcialidades,
toma la fecha de la primera parcialidad (más antigua) como fecha de recepción.

Ejecutar con: python manage.py shell < scripts/sync_lotes_fecha.py
O: python -c "exec(open('scripts/sync_lotes_fecha.py').read())"

Seguro para ejecutar múltiples veces (idempotente).
"""
import os
import sys
import django

# Setup Django si no está configurado
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    django.setup()

from core.models import Lote, LoteParcialidad
from django.db.models import Min
from django.db import transaction

def sync_lotes_sin_fecha():
    """
    Sincroniza fecha_fabricacion de lotes que no la tienen pero sí tienen parcialidades.
    """
    print("=" * 60)
    print("SINCRONIZACIÓN DE FECHAS EN LOTES")
    print("=" * 60)
    
    # Buscar lotes sin fecha_fabricacion
    lotes_sin_fecha = Lote.objects.filter(
        fecha_fabricacion__isnull=True,
        activo=True
    )
    
    total_sin_fecha = lotes_sin_fecha.count()
    print(f"\nLotes activos sin fecha_fabricacion: {total_sin_fecha}")
    
    if total_sin_fecha == 0:
        print("✓ Todos los lotes ya tienen fecha_fabricacion")
        return
    
    actualizados = 0
    errores = []
    
    with transaction.atomic():
        for lote in lotes_sin_fecha:
            # Buscar la primera parcialidad (fecha más antigua)
            primera_parcialidad = LoteParcialidad.objects.filter(
                lote=lote
            ).order_by('fecha_entrega').first()
            
            if primera_parcialidad:
                # Usar la fecha de la primera entrega
                lote.fecha_fabricacion = primera_parcialidad.fecha_entrega
                lote.save(update_fields=['fecha_fabricacion'])
                actualizados += 1
                print(f"  ✓ Lote {lote.numero_lote}: fecha_fabricacion = {primera_parcialidad.fecha_entrega} (de parcialidad)")
            else:
                # Si no tiene parcialidades, usar created_at
                if lote.created_at:
                    lote.fecha_fabricacion = lote.created_at.date()
                    lote.save(update_fields=['fecha_fabricacion'])
                    actualizados += 1
                    print(f"  ✓ Lote {lote.numero_lote}: fecha_fabricacion = {lote.created_at.date()} (de created_at)")
                else:
                    errores.append(f"Lote {lote.id} ({lote.numero_lote}): sin parcialidades ni created_at")
    
    print(f"\n{'=' * 60}")
    print(f"RESUMEN:")
    print(f"  - Lotes actualizados: {actualizados}")
    print(f"  - Errores: {len(errores)}")
    if errores:
        print(f"\nErrores detallados:")
        for err in errores:
            print(f"  ! {err}")
    print("=" * 60)

if __name__ == '__main__':
    sync_lotes_sin_fecha()
