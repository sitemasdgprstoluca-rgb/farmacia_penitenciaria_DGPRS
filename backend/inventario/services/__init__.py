"""
Módulo de servicios para inventario.

ISS-011, ISS-021: Servicios transaccionales para operaciones críticas.
"""

from .requisicion_service import (
    RequisicionService,
    RequisicionServiceError,
    StockInsuficienteError,
    EstadoInvalidoError,
    PermisoRequisicionError,
    CentroPermissionMixin,
)

__all__ = [
    'RequisicionService',
    'RequisicionServiceError',
    'StockInsuficienteError',
    'EstadoInvalidoError',
    'PermisoRequisicionError',
    'CentroPermissionMixin',
]
