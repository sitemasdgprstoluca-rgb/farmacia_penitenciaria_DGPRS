# -*- coding: utf-8 -*-
"""
Módulo de Trazabilidad para inventario.

Funciones de trazabilidad extraídas de views_legacy.py:
- trazabilidad_producto: Trazabilidad completa de un producto por clave
- trazabilidad_lote: Trazabilidad de un lote específico por código
- trazabilidad_buscar: Búsqueda general de trazabilidad
- trazabilidad_autocomplete: Autocompletado para búsqueda rápida
- trazabilidad_global: Vista global de trazabilidad del sistema
- trazabilidad_producto_exportar: Exportar trazabilidad de producto a Excel/PDF
- trazabilidad_lote_exportar: Exportar trazabilidad de lote a Excel/PDF
- exportar_control_inventarios: Exportar control de inventarios completo
- exportar_control_mensual: Exportar control mensual de almacén (Formato A)

Seguridad:
- Filtra por centro según permisos del usuario
- Admin/farmacia pueden ver trazabilidad global

Nota: Por ahora se re-exporta desde views_legacy.py para mantener compatibilidad.
"""

from inventario.views_legacy import (
    trazabilidad_producto,
    trazabilidad_lote,
    trazabilidad_buscar,
    trazabilidad_autocomplete,
    trazabilidad_global,
    trazabilidad_producto_exportar,
    trazabilidad_lote_exportar,
    exportar_control_inventarios,
    exportar_control_mensual,
)

__all__ = [
    'trazabilidad_producto',
    'trazabilidad_lote',
    'trazabilidad_buscar',
    'trazabilidad_autocomplete',
    'trazabilidad_global',
    'trazabilidad_producto_exportar',
    'trazabilidad_lote_exportar',
    'exportar_control_inventarios',
    'exportar_control_mensual',
]
