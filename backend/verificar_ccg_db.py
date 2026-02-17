#!/usr/bin/env python
"""
Script de verificación directa de cantidad_contrato_global en base de datos.

Este script consulta directamente la base de datos para verificar si los lotes
tienen el campo cantidad_contrato_global correctamente guardado.

Uso:
    python verificar_ccg_db.py

Resultado:
    Muestra todos los lotes con su CCG (si existe) y la fecha de creación.
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Lote
from django.utils import timezone
from datetime import timedelta


def verificar_lotes_recientes():
    """Verifica lotes creados en las últimas 24 horas."""
    print("\n" + "=" * 80)
    print("🔍 VERIFICACIÓN DE CANTIDAD_CONTRATO_GLOBAL EN BASE DE DATOS")
    print("=" * 80)
    
    # Buscar lotes recientes (últimas 24 horas)
    hace_24h = timezone.now() - timedelta(hours=24)
    lotes_recientes = Lote.objects.filter(
        created_at__gte=hace_24h
    ).select_related('producto').order_by('-created_at')
    
    if not lotes_recientes.exists():
        print("\n⚠️  No hay lotes creados en las últimas 24 horas.")
        print("\n📊 Mostrando los 10 lotes más recientes...")
        lotes_recientes = Lote.objects.all().select_related('producto').order_by('-created_at')[:10]
    
    print(f"\n📦 Total de lotes encontrados: {lotes_recientes.count()}")
    print("-" * 80)
    
    con_ccg = 0
    sin_ccg = 0
    
    for lote in lotes_recientes:
        producto_info = f"{lote.producto.clave} - {lote.producto.nombre}" if lote.producto else "Sin producto"
        
        print(f"\n🔹 ID: {lote.id}")
        print(f"   Lote: {lote.numero_lote}")
        print(f"   Producto: {producto_info}")
        print(f"   Contrato: {lote.numero_contrato or 'Sin contrato'}")
        print(f"   Cant. Inicial: {lote.cantidad_inicial}")
        print(f"   Cant. Contrato Lote: {lote.cantidad_contrato or 'NULL'}")
        
        if lote.cantidad_contrato_global is not None:
            print(f"   ✅ Cant. Contrato Global: {lote.cantidad_contrato_global}")
            con_ccg += 1
        else:
            print(f"   ❌ Cant. Contrato Global: NULL")
            sin_ccg += 1
        
        print(f"   Creado: {lote.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 80)
    
    print(f"\n📊 RESUMEN:")
    print(f"   ✅ Lotes CON cantidad_contrato_global: {con_ccg}")
    print(f"   ❌ Lotes SIN cantidad_contrato_global: {sin_ccg}")
    
    if con_ccg == 0 and lotes_recientes.count() > 0:
        print("\n" + "⚠️ " * 30)
        print("\n🔴 DIAGNÓSTICO: Ningún lote tiene cantidad_contrato_global")
        print("\n📋 POSIBLES CAUSAS:")
        print("   1. La plantilla Excel NO tiene la columna 'Cantidad Contrato Global'")
        print("   2. La plantilla es de una versión anterior (v1.x)")
        print("   3. La columna existe pero está vacía o tiene formato incorrecto")
        print("\n💡 SOLUCIÓN:")
        print("   1. Descarga la plantilla NUEVA desde el sistema:")
        print("      → Ir a 'Gestión de Lotes'")
        print("      → Hacer clic en el botón '📋 Plantilla'")
        print("      → Descargar el archivo Excel")
        print("   2. Verifica que la columna H sea 'Cantidad Contrato Global'")
        print("   3. Llena los datos con la cantidad TOTAL del contrato")
        print("   4. Re-importa el archivo")
        print("\n" + "⚠️ " * 30)
    elif con_ccg > 0:
        print("\n✅ El sistema está funcionando correctamente.")
        print("   Los lotes tienen cantidad_contrato_global guardada.")
    
    print("\n" + "=" * 80)
    print("✅ Verificación completada")
    print("=" * 80 + "\n")


def verificar_lotes_por_contrato(numero_contrato):
    """Verifica todos los lotes de un contrato específico."""
    print("\n" + "=" * 80)
    print(f"🔍 VERIFICACIÓN DE LOTES DEL CONTRATO: {numero_contrato}")
    print("=" * 80)
    
    lotes = Lote.objects.filter(
        numero_contrato=numero_contrato
    ).select_related('producto').order_by('producto__clave', 'numero_lote')
    
    if not lotes.exists():
        print(f"\n⚠️  No se encontraron lotes con el contrato {numero_contrato}")
        return
    
    print(f"\n📦 Total de lotes: {lotes.count()}")
    print("-" * 80)
    
    # Agrupar por producto
    por_producto = {}
    for lote in lotes:
        clave = lote.producto.clave if lote.producto else "SIN_PRODUCTO"
        if clave not in por_producto:
            por_producto[clave] = []
        por_producto[clave].append(lote)
    
    for clave, lotes_producto in por_producto.items():
        print(f"\n📦 Producto: {clave}")
        
        ccg_values = set(l.cantidad_contrato_global for l in lotes_producto if l.cantidad_contrato_global is not None)
        
        if ccg_values:
            if len(ccg_values) == 1:
                print(f"   ✅ Todos los lotes tienen CCG: {ccg_values.pop()}")
            else:
                print(f"   ⚠️  INCONSISTENCIA: Diferentes valores de CCG: {ccg_values}")
        else:
            print(f"   ❌ Ningún lote tiene CCG")
        
        total_recibido = sum(l.cantidad_inicial for l in lotes_producto)
        print(f"   📊 Total recibido: {total_recibido}")
        print(f"   🔢 Número de lotes: {len(lotes_producto)}")
        
        for lote in lotes_producto:
            print(f"      • {lote.numero_lote}: {lote.cantidad_inicial} unidades (CCG: {lote.cantidad_contrato_global or 'NULL'})")
    
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Verificar lotes de un contrato específico
        numero_contrato = sys.argv[1]
        verificar_lotes_por_contrato(numero_contrato)
    else:
        # Verificar lotes recientes
        verificar_lotes_recientes()
    
    print("\n💡 TIP: Para verificar un contrato específico:")
    print("   python verificar_ccg_db.py CONT-2025-001")
    print()
