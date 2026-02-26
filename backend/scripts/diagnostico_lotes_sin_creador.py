#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de diagnóstico: Lotes sin creador identificable

Identifica lotes que NO tienen:
- created_by_id en la tabla lotes, Y
- Ninguna parcialidad con usuario

Esto ayuda a detectar problemas de integridad de datos antes de que
afecten el rendimiento o la visualización en la UI.

Uso:
    python manage.py shell < scripts/diagnostico_lotes_sin_creador.py
    # O desde el shell de Django:
    exec(open('scripts/diagnostico_lotes_sin_creador.py').read())
"""

from django.db import connection
from core.models import Lote, LoteParcialidad
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 80)
print("DIAGNÓSTICO: Lotes sin creador identificable")
print("=" * 80)

# Query SQL directa para encontrar lotes problemáticos
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT 
            l.id,
            l.numero_lote,
            l.producto_id,
            p.clave as producto_clave,
            l.cantidad_inicial,
            l.created_at,
            l.created_by_id,
            COUNT(lp.id) as num_parcialidades,
            COUNT(CASE WHEN lp.usuario_id IS NOT NULL THEN 1 END) as parcialidades_con_usuario
        FROM lotes l
        LEFT JOIN productos p ON l.producto_id = p.id
        LEFT JOIN lote_parcialidades lp ON l.id = lp.lote_id
        WHERE l.activo = true
        GROUP BY l.id, l.numero_lote, l.producto_id, p.clave, l.cantidad_inicial, l.created_at, l.created_by_id
        HAVING 
            l.created_by_id IS NULL 
            AND COUNT(CASE WHEN lp.usuario_id IS NOT NULL THEN 1 END) = 0
        ORDER BY l.created_at DESC;
    """)
    
    lotes_problematicos = cursor.fetchall()

print(f"\n✓ Total de lotes activos: {Lote.objects.filter(activo=True).count()}")
print(f"✓ Lotes con created_by_id: {Lote.objects.filter(activo=True).exclude(created_by_id__isnull=True).count()}")

if lotes_problematicos:
    print(f"\n⚠️  ENCONTRADOS {len(lotes_problematicos)} LOTES SIN CREADOR IDENTIFICABLE:")
    print("-" * 80)
    print(f"{'ID':<8} {'Lote':<15} {'Producto':<12} {'Cant':<6} {'Fecha Creación':<20} {'Parcialidades'}")
    print("-" * 80)
    
    for lote in lotes_problematicos:
        lote_id, numero_lote, producto_id, producto_clave, cantidad, fecha, created_by, num_parc, parc_con_usuario = lote
        print(f"{lote_id:<8} {numero_lote:<15} {producto_clave or 'N/A':<12} {cantidad:<6} {fecha.strftime('%Y-%m-%d %H:%M') if fecha else 'N/A':<20} {num_parc}/{parc_con_usuario}")
    
    print("\n" + "=" * 80)
    print("RECOMENDACIONES:")
    print("=" * 80)
    print("1. Investigar cómo se crearon estos lotes (importación manual, fallo en perform_create)")
    print("2. Si es posible, asignar created_by_id retroactivamente:")
    print("   - Revisar logs de auditoría (tabla auditoria_logs)")
    print("   - Revisar registros de importación (tabla importacion_logs)")
    print("3. Como último recurso, asignar a un usuario 'Sistema' o 'Importación Masiva'")
    print("\nEjemplo de corrección manual:")
    print("   UPDATE lotes SET created_by_id = (SELECT id FROM users WHERE username = 'admin' LIMIT 1)")
    print("   WHERE id IN (1, 2, 3...);")
else:
    print(f"\n✅ PERFECTO: Todos los lotes activos tienen creador identificable")
    print("   (ya sea por created_by_id o por parcialidades con usuario)")

# Verificar lotes con created_by_id pero usuario no existe
print("\n" + "=" * 80)
print("VERIFICACIÓN ADICIONAL: Lotes con created_by_id inválido")
print("=" * 80)

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT 
            l.id,
            l.numero_lote,
            l.created_by_id
        FROM lotes l
        LEFT JOIN users u ON l.created_by_id = u.id
        WHERE l.created_by_id IS NOT NULL
          AND u.id IS NULL
          AND l.activo = true;
    """)
    
    lotes_usuario_invalido = cursor.fetchall()

if lotes_usuario_invalido:
    print(f"\n⚠️  ENCONTRADOS {len(lotes_usuario_invalido)} LOTES CON USUARIO INEXISTENTE:")
    for lote in lotes_usuario_invalido:
        print(f"   - Lote ID {lote[0]} ('{lote[1]}') apunta a usuario_id {lote[2]} que no existe")
    print("\n   Estos lotes necesitan corrección inmediata:")
    print("   UPDATE lotes SET created_by_id = NULL WHERE id IN (...);")
else:
    print("✅ Todos los created_by_id apuntan a usuarios válidos")

print("\n" + "=" * 80)
print("DIAGNÓSTICO COMPLETADO")
print("=" * 80)
