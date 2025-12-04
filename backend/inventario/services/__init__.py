"""
Módulo de servicios para inventario.

ISS-011, ISS-021: Servicios transaccionales para operaciones críticas.
ISS-012: Máquina de estados para requisiciones.
ISS-020: Validación de stock.
ISS-024: Validación de inventario por centro.
ISS-026: Reconciliación de inventario.
"""

from .requisicion_service import (
    RequisicionService,
    RequisicionServiceError,
    StockInsuficienteError,
    EstadoInvalidoError,
    PermisoRequisicionError,
    CentroPermissionMixin,
)

from .state_machine import (
    EstadoRequisicion,
    RequisicionStateMachine,
    TransicionInvalidaError,
    PrecondicionFallidaError,
    StateMachineMixin,
)

from .inventory_validation import (
    StockValidationService,
    StockValidationResult,
    StockValidationError,
    CentroInventoryValidator,
    InventoryReconciliationService,
    ReconciliacionResult,
    validar_stock_para_requisicion,
    validar_acceso_lote_usuario,
    reconciliar_inventario,
)

__all__ = [
    # Requisicion Service
    'RequisicionService',
    'RequisicionServiceError',
    'StockInsuficienteError',
    'EstadoInvalidoError',
    'PermisoRequisicionError',
    'CentroPermissionMixin',
    # State Machine
    'EstadoRequisicion',
    'RequisicionStateMachine',
    'TransicionInvalidaError',
    'PrecondicionFallidaError',
    'StateMachineMixin',
    # Inventory Validation
    'StockValidationService',
    'StockValidationResult',
    'StockValidationError',
    'CentroInventoryValidator',
    'InventoryReconciliationService',
    'ReconciliacionResult',
    'validar_stock_para_requisicion',
    'validar_acceso_lote_usuario',
    'reconciliar_inventario',
]
