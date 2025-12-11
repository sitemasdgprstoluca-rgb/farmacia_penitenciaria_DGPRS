/**
 * Hook para manejar el estado de una requisición
 * 
 * REFACTORIZADO (audit27): Ahora re-exporta desde useRequisicionEstadoV2
 * para soportar el flujo jerárquico V2 (admin/director/farmacia)
 */

// Re-exportar todo desde V2 para compatibilidad
export {
  ESTADOS_REQUISICION,
  ACCIONES_REQUISICION,
  ESTADOS_UI,
  GRUPOS_ESTADOS,
  ESTADOS_TERMINALES,
  ESTADOS_EDITABLES,
  MAPEO_ESTADOS_LEGACY,
  normalizarEstado,
  esTransicionValida,
  obtenerSiguienteEstado,
  obtenerAccionesPermitidas,
  obtenerGrupoEstado,
  useRequisicionEstado,
} from './useRequisicionEstadoV2';

// Re-exportar el hook como default
export { default } from './useRequisicionEstadoV2';

/**
 * LEGACY EXPORTS - mantener para compatibilidad con código existente
 */

/**
 * Estados posibles de una requisición (legacy - usar ESTADOS_REQUISICION de V2)
 * @deprecated Usar ESTADOS_REQUISICION de useRequisicionEstadoV2
 * @readonly
 * @enum {string}
 */
export const ESTADOS_REQUISICION_LEGACY = {
  BORRADOR: 'borrador',
  PENDIENTE: 'pendiente',
  APROBADA: 'aprobada',
  EN_PROCESO: 'en_proceso',
  SURTIDA_PARCIAL: 'surtida_parcial',
  SURTIDA: 'surtida',
  RECHAZADA: 'rechazada',
  CANCELADA: 'cancelada',
};

/**
 * Acciones posibles sobre una requisición (legacy)
 * @deprecated Usar ACCIONES_REQUISICION de useRequisicionEstadoV2
 */
export const ACCIONES_REQUISICION_LEGACY = {
  EDITAR: 'editar',
  ENVIAR: 'enviar',
  APROBAR: 'aprobar',
  RECHAZAR: 'rechazar',
  SURTIR: 'surtir',
  SURTIR_PARCIAL: 'surtir_parcial',
  CANCELAR: 'cancelar',
  ELIMINAR: 'eliminar',
  VER: 'ver',
  IMPRIMIR: 'imprimir',
  DUPLICAR: 'duplicar',
};
