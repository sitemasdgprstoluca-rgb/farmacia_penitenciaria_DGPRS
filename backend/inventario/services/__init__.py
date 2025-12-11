"""
Módulo de servicios para inventario.

ISS-011, ISS-021: Servicios transaccionales para operaciones críticas.
ISS-012: Máquina de estados para requisiciones.
ISS-013: Validaciones de contrato.
ISS-015: Generación atómica de folios.
ISS-017: Filtrado de reportes por permisos.
ISS-020: Validación de stock.
ISS-023: Motivo de rechazo obligatorio.
ISS-024: Validación de inventario por centro.
ISS-025: Trazabilidad de lotes.
ISS-026: Reconciliación de inventario.
ISS-033: Optimización de queries N+1.

=== Sprint 3: Mejoras de Calidad ===
ISS-005: Preflight check de stock.
ISS-007: Detalle de errores en importación.
ISS-009: Detalle de verificación de integridad.
ISS-016: Manager de soft-delete consistente.
ISS-031: Sanitización de archivos importados.
ISS-032: Audit log centralizado.
ISS-035: Exportaciones streaming.
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
    # ISS-021 FIX (audit9): Funciones centralizadas de stock
    calcular_stock_producto,
    calcular_stock_batch,
)

from .folio_generator import (
    FolioGenerator,
    FolioMixin,
    generar_folio_atomico,
)

from .contract_validators import (
    TipoValidacion,
    ResultadoValidacion,
    ContratoValidacion,
    RequisicionContractValidator,
    LoteTrazabilidadValidator,
    MovimientoContractValidator,
    validar_requisicion_contrato,
    validar_movimiento_cantidad,
)

from .report_filters import (
    QueryOptimizer,
    FiltroReporte,
    ReportPermissionFilter,
    ReportGenerator,
    optimizar_query,
    filtrar_por_permisos,
)

# === Sprint 3: Servicios de Calidad ===

from .preflight_check import (
    PreflightStockCheck,
    PreflightResult,
    PreflightItem,
    NivelAlerta,
)

from .import_handler import (
    DataSanitizer,
    ImportErrorCollector,
    ImportError as ErrorImportacion,  # Alias para compatibilidad
    ErrorCategory as CategoriaError,  # Alias para compatibilidad
    SafeImporter,
    ImportResult,
    ErrorSeverity,
)

from .soft_delete_manager import (
    SoftDeleteQuerySet,
    SoftDeleteManager,
    SoftDeleteMixin,
    SoftDeleteService,
)

from .audit_log import (
    AuditLogger,
    AuditEntry,
    AuditAction,
    AuditSeverity,
    audit_action,
    audit_model_changes,
)

from .streaming_export import (
    StreamingExporter,
    ReportExporter,
)

from .integrity_check import (
    VerificadorIntegridad,
    ProblemaIntegridad,
    ResultadoVerificacion,
    NivelSeveridad,
    CategoriaVerificacion,
    verificar_integridad_rapida,
    obtener_reporte_completo,
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
    # Folio Generator (ISS-015)
    'FolioGenerator',
    'FolioMixin',
    'generar_folio_atomico',
    # Contract Validators (ISS-013, ISS-023, ISS-025)
    'TipoValidacion',
    'ResultadoValidacion',
    'ContratoValidacion',
    'RequisicionContractValidator',
    'LoteTrazabilidadValidator',
    'MovimientoContractValidator',
    'validar_requisicion_contrato',
    'validar_movimiento_cantidad',
    # Report Filters (ISS-017, ISS-033)
    'QueryOptimizer',
    'FiltroReporte',
    'ReportPermissionFilter',
    'ReportGenerator',
    'optimizar_query',
    'filtrar_por_permisos',
    # === Sprint 3: Mejoras de Calidad ===
    # Preflight Check (ISS-005)
    'PreflightStockCheck',
    'PreflightResult',
    'PreflightItem',
    'NivelAlerta',
    # Import Handler (ISS-007, ISS-031)
    'DataSanitizer',
    'ImportErrorCollector',
    'ErrorImportacion',
    'CategoriaError',
    'SafeImporter',
    # Soft Delete Manager (ISS-016)
    'SoftDeleteQuerySet',
    'SoftDeleteManager',
    'SoftDeleteMixin',
    'SoftDeleteService',
    # Audit Log (ISS-032)
    'AuditLogger',
    'AuditEntry',
    'AuditAction',
    'AuditSeverity',
    'audit_action',
    'audit_model_changes',
    # Streaming Export (ISS-035)
    'StreamingExporter',
    'ReportExporter',
    # Integrity Check (ISS-009)
    'VerificadorIntegridad',
    'ProblemaIntegridad',
    'ResultadoVerificacion',
    'NivelSeveridad',
    'CategoriaVerificacion',
    'verificar_integridad_rapida',
    'obtener_reporte_completo',
]
