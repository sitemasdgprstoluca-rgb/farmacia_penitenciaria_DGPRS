#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script rápido: Verificar created_by_id en lotes

Ejecutar desde Django shell:
    python manage.py shell
    exec(open('scripts/check_created_by_lotes.py').read())
"""

from django.db import connection

print("=" * 80)
print("VERIFICACIÓN: Campo created_by_id en lotes")
print("=" * 80)

with connection.cursor() as cursor:
    # Verificar si la columna existe
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'lotes' AND column_name = 'created_by_id';
    """)
    
    columna = cursor.fetchone()
    
    if not columna:
        print("\n⚠️  La columna 'created_by_id' NO EXISTE en la tabla 'lotes'")
        print("   Esto explica por qué no se muestra el usuario creador.")
        print("\n   Solución: Ejecutar migración para agregar la columna:")
        print("   ALTER TABLE lotes ADD COLUMN created_by_id BIGINT;")
    else:
        print(f"\n✓ La columna 'created_by_id' EXISTE:")
        print(f"  - Tipo: {columna[1]}")
        print(f"  - Nullable: {columna[2]}")
        
        # Ver cuántos lotes tienen created_by_id
        cursor.execute("""
            SELECT 
                COUNT(*) as total_lotes,
                COUNT(created_by_id) as lotes_con_created_by,
                COUNT(*) - COUNT(created_by_id) as lotes_sin_created_by
            FROM lotes
            WHERE activo = true;
        """)
        
        totales = cursor.fetchone()
        total, con_created, sin_created = totales
        
        print(f"\n📊 Estadísticas de lotes activos:")
        print(f"  - Total de lotes: {total}")
        print(f"  - Con created_by_id: {con_created} ({100*con_created/total if total > 0 else 0:.1f}%)")
        print(f"  - SIN created_by_id: {sin_created} ({100*sin_created/total if total > 0 else 0:.1f}%)")
        
        if sin_created > 0:
            print(f"\n⚠️  HAY {sin_created} LOTES SIN created_by_id")
            print("   Estos aparecerán como 'Sistema' en la interfaz")
            
            # Ver si tienen parcialidades con usuario
            cursor.execute("""
                SELECT 
                    l.id,
                    l.numero_lote,
                    p.clave,
                    l.created_at,
                    COUNT(lp.id) as num_parcialidades,
                    COUNT(lp.usuario_id) as parc_con_usuario,
                    MIN(u.username) as primer_usuario_parcialidad
                FROM lotes l
                LEFT JOIN productos p ON l.producto_id = p.id
                LEFT JOIN lote_parcialidades lp ON l.id = lp.lote_id
                LEFT JOIN users u ON lp.usuario_id = u.id
                WHERE l.activo = true AND l.created_by_id IS NULL
                GROUP BY l.id, l.numero_lote, p.clave, l.created_at
                ORDER BY l.created_at DESC
                LIMIT 10;
            """)
            
            lotes = cursor.fetchall()
            
            if lotes:
                print("\n   Primeros 10 lotes sin created_by_id:")
                print("   " + "-" * 76)
                print(f"   {'ID':<6} {'Lote':<15} {'Producto':<10} {'Fecha':<12} {'Parc':<4} {'Usuario Parcialidad'}")
                print("   " + "-" * 76)
                
                for lote in lotes:
                    lote_id, numero, clave, fecha, num_parc, parc_usuario, username = lote
                    fecha_str = fecha.strftime('%Y-%m-%d') if fecha else 'N/A'
                    print(f"   {lote_id:<6} {numero:<15} {clave or 'N/A':<10} {fecha_str:<12} {num_parc:<4} {username or 'NINGUNO'}")
                
                if any(lote[6] for lote in lotes):  # Si alguno tiene usuario en parcialidad
                    print("\n   ✓ Algunos lotes tienen usuario en sus parcialidades")
                    print("     El sistema intentará usar ese usuario como creador")
                else:
                    print("\n   ⚠️  Estos lotes NO tienen usuario ni en created_by_id ni en parcialidades")
                    print("      Aparecerán como 'Sistema' hasta que se corrijan")

print("\n" + "=" * 80)
