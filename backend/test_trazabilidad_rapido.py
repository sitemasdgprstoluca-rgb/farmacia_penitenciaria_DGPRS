# -*- coding: utf-8 -*-
"""
Tests rápidos de trazabilidad y PDF - Sin pytest, usando Django directamente
Ejecutar: python test_trazabilidad_rapido.py
"""
import os
import sys

# Configurar Django ANTES de cualquier importación
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from datetime import datetime, timedelta
from django.utils import timezone
from io import BytesIO

# Importaciones del proyecto
from core.models import (
    User as Usuario, Centro, Producto, Lote, Movimiento,
    Donacion, DetalleDonacion, SalidaDonacion
)
from core.utils.pdf_reports import (
    generar_reporte_trazabilidad,
    generar_reporte_movimientos,
    generar_recibo_salida_movimiento,
    generar_recibo_salida_donacion
)

print("=" * 70)
print("TESTS RÁPIDOS - TRAZABILIDAD Y PDF")
print("=" * 70)

passed = 0
failed = 0

def test(name, condition, error_msg=""):
    """Helper para tests."""
    global passed, failed
    if condition:
        print(f"✅ PASS: {name}")
        passed += 1
    else:
        print(f"❌ FAIL: {name} - {error_msg}")
        failed += 1


# ============================================
# 1. TESTS DE MODELOS
# ============================================
print("\n--- 1. VERIFICACIÓN DE MODELOS ---")

test(
    "Modelo Donacion existe",
    hasattr(Donacion, '_meta'),
    "Modelo Donacion no encontrado"
)

test(
    "Modelo DetalleDonacion existe",
    hasattr(DetalleDonacion, '_meta'),
    "Modelo DetalleDonacion no encontrado"
)

test(
    "Modelo SalidaDonacion existe",
    hasattr(SalidaDonacion, '_meta'),
    "Modelo SalidaDonacion no encontrado"
)

test(
    "Modelo Movimiento existe",
    hasattr(Movimiento, '_meta'),
    "Modelo Movimiento no encontrado"
)

# ============================================
# 2. TESTS DE FUNCIONES PDF
# ============================================
print("\n--- 2. VERIFICACIÓN DE FUNCIONES PDF ---")

test(
    "Función generar_recibo_salida_movimiento existe",
    callable(generar_recibo_salida_movimiento),
    "Función no es callable"
)

test(
    "Función generar_recibo_salida_donacion existe",
    callable(generar_recibo_salida_donacion),
    "Función no es callable"
)

test(
    "Función generar_reporte_trazabilidad existe",
    callable(generar_reporte_trazabilidad),
    "Función no es callable"
)

test(
    "Función generar_reporte_movimientos existe",
    callable(generar_reporte_movimientos),
    "Función no es callable"
)

# ============================================
# 3. TEST PDF RECIBO MOVIMIENTO
# ============================================
print("\n--- 3. GENERACIÓN PDF RECIBO MOVIMIENTO ---")

try:
    movimiento_data = {
        'id': 999,
        'folio': 999,
        'fecha': timezone.now().isoformat(),
        'tipo': 'salida',
        'subtipo_salida': 'transferencia',
        'centro_origen': {'nombre': 'Almacén Central'},
        'centro_destino': {'nombre': 'Centro Test'},
        'cantidad': 50,
        'producto': 'Producto Test',
        'producto_clave': 'TEST-001',
        'lote': 'LOTE-TEST-001',
        'presentacion': 'Caja x 100',
        'usuario': 'Usuario Test',
        'observaciones': 'Prueba de generación PDF'
    }
    
    pdf_buffer = generar_recibo_salida_movimiento(movimiento_data, finalizado=False)
    
    test(
        "PDF movimiento retorna BytesIO",
        isinstance(pdf_buffer, BytesIO),
        f"Tipo: {type(pdf_buffer)}"
    )
    
    pdf_content = pdf_buffer.getvalue()
    test(
        "PDF movimiento tiene contenido",
        len(pdf_content) > 0,
        f"Tamaño: {len(pdf_content)}"
    )
    
    test(
        "PDF movimiento es válido (header %PDF)",
        pdf_content[:4] == b'%PDF',
        f"Header: {pdf_content[:10]}"
    )
    
    # Test con finalizado=True
    pdf_finalizado = generar_recibo_salida_movimiento(movimiento_data, finalizado=True)
    test(
        "PDF movimiento finalizado genera correctamente",
        isinstance(pdf_finalizado, BytesIO) and len(pdf_finalizado.getvalue()) > 0,
        "Error en generación"
    )
    
except Exception as e:
    test("PDF movimiento generación", False, str(e))

# ============================================
# 4. TEST PDF RECIBO DONACIÓN (NO MODIFICADO)
# ============================================
print("\n--- 4. GENERACIÓN PDF RECIBO DONACIÓN (SIN MODIFICAR) ---")

try:
    donacion_data = {
        'id': 888,
        'numero': 'DON-TEST-001',
        'fecha': timezone.now().isoformat(),
        'donante': 'Donante Test',
        'centro_destino': 'Centro Donación Test',
        'estado': 'recibida'
    }
    
    items_data = [
        {
            'producto': 'Producto Donación A',
            'cantidad': 100,
            'lote': 'LOTE-DON-001',
            'fecha_caducidad': (timezone.now().date() + timedelta(days=365)).isoformat()
        },
        {
            'producto': 'Producto Donación B',
            'cantidad': 50,
            'lote': 'LOTE-DON-002',
            'fecha_caducidad': (timezone.now().date() + timedelta(days=180)).isoformat()
        }
    ]
    
    pdf_donacion = generar_recibo_salida_donacion(donacion_data, items_data, finalizado=False)
    
    test(
        "PDF donación retorna BytesIO",
        isinstance(pdf_donacion, BytesIO),
        f"Tipo: {type(pdf_donacion)}"
    )
    
    pdf_don_content = pdf_donacion.getvalue()
    test(
        "PDF donación tiene contenido",
        len(pdf_don_content) > 0,
        f"Tamaño: {len(pdf_don_content)}"
    )
    
    test(
        "PDF donación es válido",
        pdf_don_content[:4] == b'%PDF',
        f"Header: {pdf_don_content[:10]}"
    )
    
    # Test con finalizado=True
    pdf_don_final = generar_recibo_salida_donacion(donacion_data, items_data, finalizado=True)
    test(
        "PDF donación finalizado genera correctamente",
        isinstance(pdf_don_final, BytesIO) and len(pdf_don_final.getvalue()) > 0,
        "Error en generación"
    )

except Exception as e:
    test("PDF donación generación", False, str(e))

# ============================================
# 5. TEST PDF TRAZABILIDAD
# ============================================
print("\n--- 5. GENERACIÓN PDF TRAZABILIDAD ---")

try:
    trazabilidad_data = [
        {
            'fecha': timezone.now().strftime('%d/%m/%Y %H:%M'),
            'tipo': 'ENTRADA',
            'lote': 'LOTE-001',
            'cantidad': 100,
            'centro': 'Almacén Central',
            'usuario': 'Admin',
            'observaciones': 'Entrada inicial de prueba'
        },
        {
            'fecha': (timezone.now() - timedelta(hours=2)).strftime('%d/%m/%Y %H:%M'),
            'tipo': 'SALIDA',
            'lote': 'LOTE-001',
            'cantidad': -25,
            'centro': 'Centro Test',
            'usuario': 'Farmacia',
            'observaciones': 'Transferencia'
        }
    ]
    
    producto_info = {
        'clave': 'PROD-TEST',
        'descripcion': 'Producto para trazabilidad',
        'unidad_medida': 'PIEZA',
        'stock_actual': 500,
        'stock_minimo': 10
    }
    
    pdf_traz = generar_reporte_trazabilidad(trazabilidad_data, producto_info=producto_info)
    
    test(
        "PDF trazabilidad retorna BytesIO",
        isinstance(pdf_traz, BytesIO),
        f"Tipo: {type(pdf_traz)}"
    )
    
    pdf_traz_content = pdf_traz.getvalue()
    test(
        "PDF trazabilidad tiene contenido",
        len(pdf_traz_content) > 0,
        f"Tamaño: {len(pdf_traz_content)}"
    )
    
    test(
        "PDF trazabilidad es válido",
        pdf_traz_content[:4] == b'%PDF',
        f"Header: {pdf_traz_content[:10]}"
    )

except Exception as e:
    test("PDF trazabilidad generación", False, str(e))

# ============================================
# 6. TEST PDF MOVIMIENTOS
# ============================================
print("\n--- 6. GENERACIÓN PDF MOVIMIENTOS ---")

try:
    movimientos_data = [
        {
            'id': 1,
            'fecha': timezone.now().strftime('%d/%m/%Y %H:%M'),
            'tipo': 'entrada',
            'producto': 'Producto A',
            'lote': 'LOTE-A',
            'cantidad': 100,
            'centro': 'Almacén Central',
            'usuario': 'Admin',
            'motivo': 'Ingreso inicial'
        },
        {
            'id': 2,
            'fecha': timezone.now().strftime('%d/%m/%Y %H:%M'),
            'tipo': 'salida',
            'producto': 'Producto A',
            'lote': 'LOTE-A',
            'cantidad': -30,
            'centro': 'Centro Test',
            'usuario': 'Farmacia',
            'motivo': 'Transferencia'
        }
    ]
    
    pdf_movs = generar_reporte_movimientos(movimientos_data)
    
    test(
        "PDF movimientos retorna BytesIO",
        isinstance(pdf_movs, BytesIO),
        f"Tipo: {type(pdf_movs)}"
    )
    
    pdf_movs_content = pdf_movs.getvalue()
    test(
        "PDF movimientos tiene contenido",
        len(pdf_movs_content) > 0,
        f"Tamaño: {len(pdf_movs_content)}"
    )
    
    test(
        "PDF movimientos es válido",
        pdf_movs_content[:4] == b'%PDF',
        f"Header: {pdf_movs_content[:10]}"
    )

except Exception as e:
    test("PDF movimientos generación", False, str(e))

# ============================================
# 7. VERIFICACIÓN DE DATOS EN BD
# ============================================
print("\n--- 7. VERIFICACIÓN DE DATOS EN BD ---")

productos_count = Producto.objects.count()
test(
    f"Productos en BD: {productos_count}",
    productos_count >= 0,
    "Error al contar productos"
)

lotes_count = Lote.objects.filter(activo=True).count()
test(
    f"Lotes activos en BD: {lotes_count}",
    lotes_count >= 0,
    "Error al contar lotes"
)

movimientos_count = Movimiento.objects.count()
test(
    f"Movimientos en BD: {movimientos_count}",
    movimientos_count >= 0,
    "Error al contar movimientos"
)

donaciones_count = Donacion.objects.count()
test(
    f"Donaciones en BD: {donaciones_count}",
    donaciones_count >= 0,
    "Error al contar donaciones"
)

# ============================================
# 8. VERIFICAR FIRMA DE FUNCIONES
# ============================================
print("\n--- 8. VERIFICACIÓN DE FIRMAS DE FUNCIONES ---")

import inspect

# generar_recibo_salida_movimiento
sig_mov = inspect.signature(generar_recibo_salida_movimiento)
params_mov = list(sig_mov.parameters.keys())
test(
    "Firma generar_recibo_salida_movimiento tiene parámetros correctos",
    'movimiento_data' in params_mov and 'finalizado' in params_mov,
    f"Parámetros: {params_mov}"
)

# generar_recibo_salida_donacion
sig_don = inspect.signature(generar_recibo_salida_donacion)
params_don = list(sig_don.parameters.keys())
test(
    "Firma generar_recibo_salida_donacion tiene parámetros correctos",
    'movimiento_data' in params_don and 'items_data' in params_don and 'finalizado' in params_don,
    f"Parámetros: {params_don}"
)

# ============================================
# RESUMEN
# ============================================
print("\n" + "=" * 70)
print(f"RESUMEN: {passed} PASADOS / {failed} FALLIDOS de {passed + failed} tests")
print("=" * 70)

if failed == 0:
    print("✅ TODOS LOS TESTS PASARON EXITOSAMENTE")
else:
    print("⚠️  ALGUNOS TESTS FALLARON - REVISAR ARRIBA")

# Exit code para CI/CD
sys.exit(0 if failed == 0 else 1)
