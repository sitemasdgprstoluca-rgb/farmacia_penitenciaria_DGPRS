# -*- coding: utf-8 -*-
"""
Módulo de Views para inventario.

Refactorización audit34: El monolítico views.py (7654 líneas) se ha preparado
para separación en módulos especializados.

FASE 1 (audit34): Módulos base creados
- base.py: Imports, constantes, helpers y paginación compartida
- productos.py: ProductoViewSet
- centros.py: CentroViewSet
- lotes.py: LoteViewSet
- movimientos.py: MovimientoViewSet
- hojas_recoleccion.py: HojaRecoleccionViewSet

PENDIENTE FASE 2: 
- requisiciones.py: RequisicionViewSet (~3800 líneas)
- reportes.py: Funciones de reportes
- dashboard.py: Funciones de dashboard

Por ahora, se re-exporta todo desde views_legacy.py (views.py original renombrado)
para mantener compatibilidad con api_urls.py sin romper nada.
"""

# Re-exportar todo desde el archivo original (ahora views_legacy.py)
# Esto mantiene 100% compatibilidad mientras los módulos se validan
from inventario.views_legacy import (
    # ViewSets
    ProductoViewSet,
    CentroViewSet,
    LoteViewSet,
    MovimientoViewSet,
    RequisicionViewSet,
    HojaRecoleccionViewSet,
    # Funciones de dashboard
    dashboard_resumen,
    dashboard_graficas,
    # Funciones de trazabilidad
    trazabilidad_producto,
    trazabilidad_lote,
    # Funciones de reportes
    reporte_inventario,
    reporte_movimientos,
    reporte_caducidades,
    reporte_requisiciones,
    reportes_precarga,
    reporte_medicamentos_por_caducar,
    reporte_bajo_stock,
    reporte_consumo,
    # Helpers y utilidades
    CustomPagination,
    is_farmacia_or_admin,
    get_user_centro,
    registrar_movimiento_stock,
    validar_archivo_excel,
    validar_archivo_pdf,
    validar_archivo_imagen,
    cargar_workbook_seguro,
    validar_filas_excel,
    invalidar_cache_dashboard,
)

__all__ = [
    # ViewSets
    'ProductoViewSet',
    'CentroViewSet',
    'LoteViewSet',
    'MovimientoViewSet',
    'RequisicionViewSet',
    'HojaRecoleccionViewSet',
    # Dashboard
    'dashboard_resumen',
    'dashboard_graficas',
    # Trazabilidad
    'trazabilidad_producto',
    'trazabilidad_lote',
    # Reportes
    'reporte_inventario',
    'reporte_movimientos',
    'reporte_caducidades',
    'reporte_requisiciones',
    'reportes_precarga',
    'reporte_medicamentos_por_caducar',
    'reporte_bajo_stock',
    'reporte_consumo',
    # Helpers
    'CustomPagination',
    'is_farmacia_or_admin',
    'get_user_centro',
    'registrar_movimiento_stock',
    'validar_archivo_excel',
    'validar_archivo_pdf',
    'validar_archivo_imagen',
    'cargar_workbook_seguro',
    'validar_filas_excel',
    'invalidar_cache_dashboard',
]

