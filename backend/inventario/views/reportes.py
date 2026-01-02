# -*- coding: utf-8 -*-
"""
Módulo de Reportes para inventario.

Funciones de reportes extraídas de views_legacy.py:
- reporte_inventario: Reporte de inventario actual por centro/producto
- reporte_movimientos: Reporte de movimientos con filtros de fecha/tipo
- reporte_caducidades: Reporte de lotes próximos a caducar
- reporte_requisiciones: Reporte de requisiciones por estado/centro
- reporte_medicamentos_por_caducar: Medicamentos próximos a vencer
- reporte_bajo_stock: Productos con stock bajo mínimo
- reporte_consumo: Análisis de consumo por periodo
- reportes_precarga: Datos de precarga para filtros de reportes

Nota: Por ahora se re-exporta desde views_legacy.py para mantener compatibilidad.
La migración completa del código se hará de forma incremental.
"""

from inventario.views_legacy import (
    reporte_inventario,
    reporte_movimientos,
    reporte_caducidades,
    reporte_requisiciones,
    reporte_medicamentos_por_caducar,
    reporte_bajo_stock,
    reporte_consumo,
    reportes_precarga,
)

__all__ = [
    'reporte_inventario',
    'reporte_movimientos',
    'reporte_caducidades',
    'reporte_requisiciones',
    'reporte_medicamentos_por_caducar',
    'reporte_bajo_stock',
    'reporte_consumo',
    'reportes_precarga',
]
