"""
Utilidades del módulo core.

Exports:
- ExcelExporter: Clase para generar archivos Excel con formato profesional
- export_queryset_to_excel: Función rápida para exportar querysets
"""

from core.utils.excel_export import ExcelExporter, export_queryset_to_excel

__all__ = ['ExcelExporter', 'export_queryset_to_excel']
