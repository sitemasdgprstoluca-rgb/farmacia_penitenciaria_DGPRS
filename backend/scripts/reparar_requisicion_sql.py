#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para reparar una requisición que quedó en estado inconsistente.
Usa SQL directo para bypasear el trigger de validación de transiciones.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
from django.utils import timezone

print("=" * 80)
print("REPARACIÓN DE REQUISICIÓN (SQL DIRECTO)")
print("=" * 80)

FOLIO = 'REQ-20260112-1887'

with connection.cursor() as cursor:
    # 1. Verificar que no hay movimientos
    cursor.execute("""
        SELECT COUNT(*) FROM movimientos 
        WHERE requisicion_id = (SELECT id FROM requisiciones WHERE numero = %s)
    """, [FOLIO])
    mov_count = cursor.fetchone()[0]
    
    if mov_count > 0:
        print(f"❌ La requisición tiene {mov_count} movimientos - No se puede reparar")
    else:
        print(f"✅ Sin movimientos - Procediendo...")
        
        # 2. Deshabilitar trigger temporalmente
        cursor.execute("ALTER TABLE requisiciones DISABLE TRIGGER trigger_validar_transicion_requisicion")
        print("   Trigger deshabilitado temporalmente")
        
        try:
            # 3. Resetear cantidades surtidas en detalles
            cursor.execute("""
                UPDATE detalles_requisicion 
                SET cantidad_surtida = 0 
                WHERE requisicion_id = (SELECT id FROM requisiciones WHERE numero = %s)
            """, [FOLIO])
            print(f"   ✅ Detalles reseteados: {cursor.rowcount} filas")
            
            # 4. Revertir estado de la requisición
            timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                UPDATE requisiciones 
                SET estado = 'autorizada',
                    fecha_surtido = NULL,
                    fecha_entrega = NULL,
                    surtidor_id = NULL,
                    notas = COALESCE(notas, '') || %s,
                    updated_at = NOW()
                WHERE numero = %s
            """, [f"\n[REPARACIÓN {timestamp}] Estado revertido por inconsistencia (sin movimientos)", FOLIO])
            print(f"   ✅ Estado revertido a 'autorizada'")
            
        finally:
            # 5. Re-habilitar trigger
            cursor.execute("ALTER TABLE requisiciones ENABLE TRIGGER trigger_validar_transicion_requisicion")
            print("   Trigger re-habilitado")
        
        print("\n✅ REPARACIÓN COMPLETADA")
        print(f"   La requisición {FOLIO} está ahora en estado 'autorizada'")

print("=" * 80)
