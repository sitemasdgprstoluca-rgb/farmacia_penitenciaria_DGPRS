# -*- coding: utf-8 -*-
"""
Módulo de re-exportación para compatibilidad.

IMPORTANTE: Este archivo es un STUB que re-exporta desde views/__init__.py
El código real está en views_legacy.py (importado por views/__init__.py)

Refactorización audit34:
- views_legacy.py: Código monolítico original (7654 líneas)
- views/__init__.py: Re-exporta desde views_legacy.py
- views/base.py, views/movimientos.py, etc.: Módulos preparados para futura migración

NO MODIFICAR ESTE ARCHIVO - Cambios deben hacerse en views_legacy.py
"""

# Re-exportar todo desde views/__init__.py (que a su vez importa de views_legacy.py)
from inventario.views import *  # noqa: F401, F403

# Exportar explícitamente para IDEs y herramientas de análisis
from inventario.views import (
    # ViewSets
    ProductoViewSet,
    CentroViewSet,
    LoteViewSet,
    MovimientoViewSet,
    RequisicionViewSet,
    HojaRecoleccionViewSet,
    # Dashboard
    dashboard_resumen,
    dashboard_graficas,
    # Trazabilidad
    trazabilidad_producto,
    trazabilidad_lote,
    # Reportes
    reporte_inventario,
    reporte_movimientos,
    reporte_caducidades,
    reporte_requisiciones,
    reportes_precarga,
    reporte_medicamentos_por_caducar,
    reporte_bajo_stock,
    reporte_consumo,
    # Helpers
    CustomPagination,
    is_farmacia_or_admin,
    has_global_read_access,
    get_user_centro,
    registrar_movimiento_stock,
    validar_archivo_excel,
    validar_archivo_pdf,
    validar_archivo_imagen,
    cargar_workbook_seguro,
    validar_filas_excel,
    invalidar_cache_dashboard,
    # Constantes
    EXCEL_MAGIC_BYTES,
    leer_archivo_con_limite,
)







