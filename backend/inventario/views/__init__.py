# -*- coding: utf-8 -*-
"""
Módulo de Views para inventario.

Estructura modular completada (ISS-014):
- base.py: Imports, constantes, helpers y paginación compartida
- productos.py: ProductoViewSet (CRUD de productos)
- centros.py: CentroViewSet (CRUD de centros penitenciarios)
- lotes.py: LoteViewSet (CRUD de lotes con FEFO)
- movimientos.py: MovimientoViewSet (entradas, salidas, ajustes)
- requisiciones.py: RequisicionViewSet (flujo V2 de requisiciones)
- hojas_recoleccion.py: HojaRecoleccionViewSet
- dashboard.py: Funciones de dashboard (KPIs, gráficas)
- reportes.py: Funciones de reportes y exportaciones
- trazabilidad.py: Funciones de trazabilidad de productos/lotes
- salida_masiva.py: Funciones de salida masiva

Los módulos actúan como puentes hacia views_legacy.py para mantener
compatibilidad mientras se completa la migración incremental.
"""

# ViewSets desde módulos dedicados
from inventario.views.productos import ProductoViewSet
from inventario.views.centros import CentroViewSet
from inventario.views.lotes import LoteViewSet
from inventario.views.movimientos import MovimientoViewSet
from inventario.views.requisiciones import RequisicionViewSet
from inventario.views.hojas_recoleccion import HojaRecoleccionViewSet

# Dashboard desde módulo dedicado
from inventario.views.dashboard import (
    dashboard_resumen,
    dashboard_graficas,
)

# Trazabilidad desde módulo dedicado
from inventario.views.trazabilidad import (
    trazabilidad_producto,
    trazabilidad_lote,
    trazabilidad_buscar,
    trazabilidad_autocomplete,
    trazabilidad_global,
    trazabilidad_producto_exportar,
    trazabilidad_lote_exportar,
    exportar_control_inventarios,
)

# Reportes desde módulo dedicado
from inventario.views.reportes import (
    reporte_inventario,
    reporte_movimientos,
    reporte_caducidades,
    reporte_requisiciones,
    reportes_precarga,
    reporte_medicamentos_por_caducar,
    reporte_bajo_stock,
    reporte_consumo,
)

# Helpers y utilidades desde base.py
from inventario.views.base import (
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
    EXCEL_MAGIC_BYTES,
    leer_archivo_con_limite,
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
    'trazabilidad_buscar',
    'trazabilidad_autocomplete',
    'trazabilidad_global',
    'trazabilidad_producto_exportar',
    'trazabilidad_lote_exportar',
    'exportar_control_inventarios',
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
    'has_global_read_access',
    'get_user_centro',
    'registrar_movimiento_stock',
    'validar_archivo_excel',
    'validar_archivo_pdf',
    'validar_archivo_imagen',
    'cargar_workbook_seguro',
    'validar_filas_excel',
    'invalidar_cache_dashboard',
    # Constantes
    'EXCEL_MAGIC_BYTES',
    'leer_archivo_con_limite',
]

