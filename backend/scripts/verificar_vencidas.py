#!/usr/bin/env python
"""
FLUJO V2: Script para verificar requisiciones vencidas

Este script debe ejecutarse periódicamente (cron job) para marcar
como vencidas las requisiciones que han pasado su fecha límite de recolección.

Uso:
    python manage.py shell < scripts/verificar_vencidas.py
    
O como cron job:
    0 0 * * * cd /path/to/backend && python manage.py shell < scripts/verificar_vencidas.py

También puede llamarse via API:
    POST /api/requisiciones/verificar-vencidas/
"""

import os
import sys
import django

# Configurar Django si se ejecuta como script independiente
if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

from django.utils import timezone
from django.db import transaction
from inventario.models import Requisicion, HistorialEstadoRequisicion


def verificar_vencidas(dry_run=False):
    """
    Verifica y marca como vencidas las requisiciones que pasaron
    su fecha límite de recolección.
    
    Args:
        dry_run: Si True, solo reporta sin hacer cambios
        
    Returns:
        dict con estadísticas de la operación
    """
    ahora = timezone.now()
    
    # Buscar requisiciones surtidas con fecha límite vencida
    requisiciones_vencidas = Requisicion.objects.filter(
        estado='surtida',
        fecha_recoleccion_limite__isnull=False,
        fecha_recoleccion_limite__lt=ahora
    )
    
    total = requisiciones_vencidas.count()
    marcadas = 0
    errores = []
    
    print(f"[{ahora}] Verificando requisiciones vencidas...")
    print(f"Encontradas: {total} requisición(es) con fecha límite vencida")
    
    if dry_run:
        print("MODO DRY-RUN: No se harán cambios")
        for req in requisiciones_vencidas:
            print(f"  - {req.folio}: límite {req.fecha_recoleccion_limite}")
        return {
            'total': total,
            'marcadas': 0,
            'errores': [],
            'dry_run': True
        }
    
    for req in requisiciones_vencidas:
        try:
            with transaction.atomic():
                estado_anterior = req.estado
                req.estado = 'vencida'
                req.motivo_vencimiento = (
                    f"Fecha límite de recolección vencida: {req.fecha_recoleccion_limite}"
                )
                req.save()
                
                # Registrar en historial
                HistorialEstadoRequisicion.objects.create(
                    requisicion=req,
                    estado_anterior=estado_anterior,
                    estado_nuevo='vencida',
                    accion='marcar_vencida',
                    motivo=req.motivo_vencimiento,
                    usuario=None  # Acción automática del sistema
                )
                
                marcadas += 1
                print(f"  ✓ {req.folio} marcada como vencida")
                
        except Exception as e:
            error_msg = f"Error en {req.folio}: {str(e)}"
            errores.append(error_msg)
            print(f"  ✗ {error_msg}")
    
    print(f"\nResumen: {marcadas}/{total} marcadas, {len(errores)} errores")
    
    return {
        'total': total,
        'marcadas': marcadas,
        'errores': errores,
        'dry_run': False
    }


if __name__ == "__main__":
    # Parsear argumentos
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv
    
    resultado = verificar_vencidas(dry_run=dry_run)
    
    # Salir con código de error si hubo problemas
    if resultado['errores']:
        sys.exit(1)
    sys.exit(0)
