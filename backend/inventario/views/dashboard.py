# -*- coding: utf-8 -*-
"""
Módulo de Dashboard para inventario.

Funciones de dashboard extraídas de views_legacy.py:
- dashboard_resumen: KPIs principales (productos, stock, lotes, movimientos)
- dashboard_graficas: Datos para gráficas (consumo mensual, stock por centro, requisiciones)
- dashboard_analytics: Analytics avanzados (top productos, centros, donaciones, caja chica, caducidades)

Características:
- Implementa caché para mejorar rendimiento
- Filtra por centro según permisos del usuario
- Admin/farmacia pueden ver datos globales o filtrar por centro específico

Nota: Por ahora se re-exporta desde views_legacy.py para mantener compatibilidad.
"""

from inventario.views_legacy import (
    dashboard_resumen,
    dashboard_graficas,
    dashboard_analytics,
)

__all__ = [
    'dashboard_resumen',
    'dashboard_graficas',
    'dashboard_analytics',
]
