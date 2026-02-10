"""
Test inline de reportes sin truncamiento - ejecutar con manage.py shell
"""
from datetime import datetime, timedelta
from io import BytesIO
import os

# Datos de prueba con textos largos
DATOS_TRAZABILIDAD = [
    {
        'fecha': datetime.now() - timedelta(days=2),
        'tipo': 'ENTRADA',
        'numero_lote': '25072052',
        'cantidad': 7,
        'centro_nombre': 'CENTRO PENITENCIARIO RIO SANTIAGO DE ALTA SEGURIDAD',
        'usuario': 'Farmacia Central Admin',
        'numero_expediente': 'EXP-2026-00123',
        'observaciones': '[CONFIRMADO]SAL-0197-23 VALE Entregado correctamente al centro',
    },
    {
        'fecha': datetime.now() - timedelta(days=1),
        'tipo': 'SALIDA',
        'subtipo_salida': 'REQUISICION',
        'numero_lote': '25072052',
        'cantidad': 7,
        'centro_nombre': 'CENTRO PENITENCIARIO RIO SANTIAGO DE ALTA SEGURIDAD',
        'usuario': 'farmacia@g...',
        'numero_expediente': '-',
        'observaciones': '[CONFIRMADO]SAL-0197-23 VALE medicamento distribuido',
    },
    {
        'fecha': datetime.now(),
        'tipo': 'SALIDA',
        'numero_lote': '25072052',
        'cantidad': 65,
        'centro_nombre': 'CENTRO PENITENCIARIO RIO SANTIAGO DE ALTA SEGURIDAD',
        'usuario': 'Farmacia C...',
        'numero_expediente': '-',
        'observaciones': '[CONFIRMADO] Surtir medicamento Tableta',
    },
    {
        'fecha': datetime.now(),
        'tipo': 'SALIDA',
        'numero_lote': '25072052',
        'cantidad': 2,
        'centro_nombre': 'Farmacia Central',
        'usuario': 'Farmacia C...',
        'numero_expediente': '-',
        'observaciones': 'SALIDA_POR_REQUISICION REQ-20260108-212',
    },
    {
        'fecha': datetime.now(),
        'tipo': 'ENTRADA',
        'numero_lote': '25072052',
        'cantidad': 2,
        'centro_nombre': 'CENTRO PENITENCIARIO RIO SANTIAGO DE ALTA SEGURIDAD',
        'usuario': 'Farmacia C...',
        'numero_expediente': '-',
        'observaciones': 'ENTRADA_POR_REQUISICION REQ-20260108-237 transferencia completada',
    },
    {
        'fecha': datetime.now(),
        'tipo': 'SALIDA',
        'numero_lote': '25072052',
        'cantidad': 2,
        'centro_nombre': 'CENTRO PENITENCIARIO MEDICO CEN ESPECIALIZADO',
        'usuario': 'Farmacia C...',
        'numero_expediente': '-',
        'observaciones': 'No sube nueva media',
    },
]

PRODUCTO_INFO = {
    'clave': '615',
    'descripcion': 'KETOCONAZOL /CLINDAMICINA',
    'unidad_medida': 'CAJA CON 7 OVULOS',
    'precio_unitario': None,
    'stock_actual': 0,
    'stock_minimo': 1,
    'numero_contrato': 'CONT-PRUEBA-139',
    'numero_lote': '25072052',
    'fecha_caducidad': '01/07/2027',
    'proveedor': '[EJEMPLO] Laboratorio - ELIMINAR',
    'titulo_centro': 'TODOS LOS CENTROS (CONSOLIDADO)',
}

print("="*60)
print("TEST: Generando PDF de Trazabilidad")
print("="*60)

from core.utils.pdf_reports import generar_reporte_trazabilidad

buffer = generar_reporte_trazabilidad(
    DATOS_TRAZABILIDAD,
    producto_info=PRODUCTO_INFO,
    filtros={'centro': 'todos'}
)

output_path = 'test_trazabilidad_output.pdf'
with open(output_path, 'wb') as f:
    f.write(buffer.getvalue())

print(f"✓ PDF generado: {len(buffer.getvalue())} bytes")
print(f"  Guardado en: {os.path.abspath(output_path)}")

# Test PDF de movimientos
print("\n" + "="*60)
print("TEST: Generando PDF de Movimientos")
print("="*60)

from core.utils.pdf_reports import generar_reporte_movimientos

transacciones = [
    {
        'referencia': 'SALIDA_POR_REQUISICION REQ-20260101-001 VALE ENTREGADO',
        'fecha': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'tipo': 'SALIDA',
        'centro_origen': 'Farmacia Central',
        'centro_destino': 'CENTRO PENITENCIARIO RIO SANTIAGO DE ALTA SEGURIDAD',
        'total_productos': 2,
        'total_cantidad': 25,
        'detalles': [
            {'producto': 'KETOCONAZOL /CLINDAMICINA CAJA CON 7 OVULOS', 'lote': '25072052', 'cantidad': 10},
            {'producto': 'PARACETAMOL 500MG TABLETAS CAJA CON 100', 'lote': 'LOT-2025-001', 'cantidad': 15},
        ]
    },
    {
        'referencia': 'ENTRADA_POR_REQUISICION REQ-20260101-002',
        'fecha': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'tipo': 'ENTRADA',
        'centro_origen': 'CENTRO PENITENCIARIO MEDICO CEN ESPECIALIZADO',
        'centro_destino': 'Farmacia Central',
        'total_productos': 1,
        'total_cantidad': 50,
        'detalles': [
            {'producto': 'IBUPROFENO 400MG TABLETAS CAJA CON 30', 'lote': 'IBU-2025-100', 'cantidad': 50},
        ]
    },
]

buffer2 = generar_reporte_movimientos(
    transacciones,
    filtros={'centro': 'todos', 'titulo_centro': 'TODOS LOS CENTROS'}
)

output_path2 = 'test_movimientos_output.pdf'
with open(output_path2, 'wb') as f:
    f.write(buffer2.getvalue())

print(f"✓ PDF generado: {len(buffer2.getvalue())} bytes")
print(f"  Guardado en: {os.path.abspath(output_path2)}")

print("\n" + "="*60)
print("PRUEBAS COMPLETADAS")
print("="*60)
print("Por favor abre los archivos PDF generados para verificar")
print("que los nombres de centros y observaciones NO se cortan.")
