/**
 * ISS-006 FIX: Máquina de estados para requisiciones
 * Centraliza las transiciones válidas de estados de requisiciones
 * y calcula las acciones permitidas según el estado actual y permisos
 */
import { useMemo, useCallback } from 'react';

/**
 * Estados posibles de una requisición
 * @readonly
 * @enum {string}
 */
export const ESTADOS_REQUISICION = {
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
 * Acciones posibles sobre una requisición
 * @readonly
 * @enum {string}
 */
export const ACCIONES_REQUISICION = {
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

/**
 * Definición de la máquina de estados
 * Cada estado tiene las transiciones válidas que puede hacer
 */
const TRANSICIONES = {
  [ESTADOS_REQUISICION.BORRADOR]: {
    acciones: [
      ACCIONES_REQUISICION.EDITAR,
      ACCIONES_REQUISICION.ENVIAR,
      ACCIONES_REQUISICION.ELIMINAR,
      ACCIONES_REQUISICION.VER,
      ACCIONES_REQUISICION.DUPLICAR,
    ],
    transiciones: {
      [ACCIONES_REQUISICION.ENVIAR]: ESTADOS_REQUISICION.PENDIENTE,
      [ACCIONES_REQUISICION.ELIMINAR]: null, // Eliminación física
    },
  },
  [ESTADOS_REQUISICION.PENDIENTE]: {
    acciones: [
      ACCIONES_REQUISICION.APROBAR,
      ACCIONES_REQUISICION.RECHAZAR,
      ACCIONES_REQUISICION.CANCELAR,
      ACCIONES_REQUISICION.VER,
      ACCIONES_REQUISICION.IMPRIMIR,
    ],
    transiciones: {
      [ACCIONES_REQUISICION.APROBAR]: ESTADOS_REQUISICION.APROBADA,
      [ACCIONES_REQUISICION.RECHAZAR]: ESTADOS_REQUISICION.RECHAZADA,
      [ACCIONES_REQUISICION.CANCELAR]: ESTADOS_REQUISICION.CANCELADA,
    },
  },
  [ESTADOS_REQUISICION.APROBADA]: {
    acciones: [
      ACCIONES_REQUISICION.SURTIR,
      ACCIONES_REQUISICION.SURTIR_PARCIAL,
      ACCIONES_REQUISICION.CANCELAR,
      ACCIONES_REQUISICION.VER,
      ACCIONES_REQUISICION.IMPRIMIR,
    ],
    transiciones: {
      [ACCIONES_REQUISICION.SURTIR]: ESTADOS_REQUISICION.SURTIDA,
      [ACCIONES_REQUISICION.SURTIR_PARCIAL]: ESTADOS_REQUISICION.SURTIDA_PARCIAL,
      [ACCIONES_REQUISICION.CANCELAR]: ESTADOS_REQUISICION.CANCELADA,
    },
  },
  [ESTADOS_REQUISICION.EN_PROCESO]: {
    acciones: [
      ACCIONES_REQUISICION.SURTIR,
      ACCIONES_REQUISICION.SURTIR_PARCIAL,
      ACCIONES_REQUISICION.CANCELAR,
      ACCIONES_REQUISICION.VER,
      ACCIONES_REQUISICION.IMPRIMIR,
    ],
    transiciones: {
      [ACCIONES_REQUISICION.SURTIR]: ESTADOS_REQUISICION.SURTIDA,
      [ACCIONES_REQUISICION.SURTIR_PARCIAL]: ESTADOS_REQUISICION.SURTIDA_PARCIAL,
      [ACCIONES_REQUISICION.CANCELAR]: ESTADOS_REQUISICION.CANCELADA,
    },
  },
  [ESTADOS_REQUISICION.SURTIDA_PARCIAL]: {
    acciones: [
      ACCIONES_REQUISICION.SURTIR,
      ACCIONES_REQUISICION.SURTIR_PARCIAL,
      ACCIONES_REQUISICION.VER,
      ACCIONES_REQUISICION.IMPRIMIR,
    ],
    transiciones: {
      [ACCIONES_REQUISICION.SURTIR]: ESTADOS_REQUISICION.SURTIDA,
      [ACCIONES_REQUISICION.SURTIR_PARCIAL]: ESTADOS_REQUISICION.SURTIDA_PARCIAL,
    },
  },
  [ESTADOS_REQUISICION.SURTIDA]: {
    acciones: [
      ACCIONES_REQUISICION.VER,
      ACCIONES_REQUISICION.IMPRIMIR,
      ACCIONES_REQUISICION.DUPLICAR,
    ],
    transiciones: {},
  },
  [ESTADOS_REQUISICION.RECHAZADA]: {
    acciones: [
      ACCIONES_REQUISICION.VER,
      ACCIONES_REQUISICION.DUPLICAR,
    ],
    transiciones: {},
  },
  [ESTADOS_REQUISICION.CANCELADA]: {
    acciones: [
      ACCIONES_REQUISICION.VER,
      ACCIONES_REQUISICION.DUPLICAR,
    ],
    transiciones: {},
  },
};

/**
 * Mapeo de acciones a permisos requeridos
 */
const PERMISOS_ACCIONES = {
  [ACCIONES_REQUISICION.EDITAR]: 'editarRequisicion',
  [ACCIONES_REQUISICION.ENVIAR]: 'crearRequisicion',
  [ACCIONES_REQUISICION.APROBAR]: 'aprobarRequisicion',
  [ACCIONES_REQUISICION.RECHAZAR]: 'aprobarRequisicion',
  [ACCIONES_REQUISICION.SURTIR]: 'surtirRequisicion',
  [ACCIONES_REQUISICION.SURTIR_PARCIAL]: 'surtirRequisicion',
  [ACCIONES_REQUISICION.CANCELAR]: 'cancelarRequisicion',
  [ACCIONES_REQUISICION.ELIMINAR]: 'eliminarRequisicion',
  [ACCIONES_REQUISICION.VER]: 'verRequisiciones',
  [ACCIONES_REQUISICION.IMPRIMIR]: 'verRequisiciones',
  [ACCIONES_REQUISICION.DUPLICAR]: 'crearRequisicion',
};

/**
 * Etiquetas y colores para cada estado
 */
export const ESTADOS_UI = {
  [ESTADOS_REQUISICION.BORRADOR]: {
    label: 'Borrador',
    color: 'gray',
    bgClass: 'bg-gray-100',
    textClass: 'text-gray-700',
    badgeClass: 'bg-gray-100 text-gray-700',
  },
  [ESTADOS_REQUISICION.PENDIENTE]: {
    label: 'Pendiente',
    color: 'yellow',
    bgClass: 'bg-yellow-100',
    textClass: 'text-yellow-700',
    badgeClass: 'bg-yellow-100 text-yellow-700',
  },
  [ESTADOS_REQUISICION.APROBADA]: {
    label: 'Aprobada',
    color: 'blue',
    bgClass: 'bg-blue-100',
    textClass: 'text-blue-700',
    badgeClass: 'bg-blue-100 text-blue-700',
  },
  [ESTADOS_REQUISICION.EN_PROCESO]: {
    label: 'En Proceso',
    color: 'indigo',
    bgClass: 'bg-indigo-100',
    textClass: 'text-indigo-700',
    badgeClass: 'bg-indigo-100 text-indigo-700',
  },
  [ESTADOS_REQUISICION.SURTIDA_PARCIAL]: {
    label: 'Surtida Parcial',
    color: 'orange',
    bgClass: 'bg-orange-100',
    textClass: 'text-orange-700',
    badgeClass: 'bg-orange-100 text-orange-700',
  },
  [ESTADOS_REQUISICION.SURTIDA]: {
    label: 'Surtida',
    color: 'green',
    bgClass: 'bg-green-100',
    textClass: 'text-green-700',
    badgeClass: 'bg-green-100 text-green-700',
  },
  [ESTADOS_REQUISICION.RECHAZADA]: {
    label: 'Rechazada',
    color: 'red',
    bgClass: 'bg-red-100',
    textClass: 'text-red-700',
    badgeClass: 'bg-red-100 text-red-700',
  },
  [ESTADOS_REQUISICION.CANCELADA]: {
    label: 'Cancelada',
    color: 'gray',
    bgClass: 'bg-gray-200',
    textClass: 'text-gray-600',
    badgeClass: 'bg-gray-200 text-gray-600',
  },
};

/**
 * Verifica si una transición es válida
 * @param {string} estadoActual - Estado actual de la requisición
 * @param {string} accion - Acción a ejecutar
 * @returns {boolean}
 */
export const esTransicionValida = (estadoActual, accion) => {
  const config = TRANSICIONES[estadoActual];
  if (!config) return false;
  return config.acciones.includes(accion);
};

/**
 * Obtiene el siguiente estado después de una acción
 * @param {string} estadoActual - Estado actual
 * @param {string} accion - Acción ejecutada
 * @returns {string|null} - Nuevo estado o null si no cambia
 */
export const obtenerSiguienteEstado = (estadoActual, accion) => {
  const config = TRANSICIONES[estadoActual];
  if (!config) return null;
  return config.transiciones[accion] ?? null;
};

/**
 * Obtiene las acciones permitidas para un estado y permisos dados
 * @param {string} estado - Estado actual de la requisición
 * @param {Object} permisos - Objeto de permisos del usuario
 * @param {Object} options - Opciones adicionales
 * @param {boolean} options.esCreador - Si el usuario es el creador de la requisición
 * @returns {string[]} - Lista de acciones permitidas
 */
export const obtenerAccionesPermitidas = (estado, permisos = {}, options = {}) => {
  const config = TRANSICIONES[estado];
  if (!config) return [];

  return config.acciones.filter(accion => {
    const permisoRequerido = PERMISOS_ACCIONES[accion];
    
    // Si no hay permiso definido, permitir la acción
    if (!permisoRequerido) return true;
    
    // Verificar permiso
    if (!permisos[permisoRequerido]) return false;
    
    // Reglas adicionales
    if (accion === ACCIONES_REQUISICION.EDITAR && !options.esCreador) {
      // Solo el creador puede editar borradores
      return permisos.editarCualquierRequisicion || false;
    }
    
    return true;
  });
};

/**
 * Hook para usar la máquina de estados de requisiciones
 * @param {Object} requisicion - Requisición actual
 * @param {Object} permisos - Permisos del usuario
 * @param {Object} options - Opciones adicionales
 * @returns {Object} - Utilidades de la máquina de estados
 */
export const useRequisicionEstado = (requisicion, permisos = {}, options = {}) => {
  const estado = requisicion?.estado || ESTADOS_REQUISICION.BORRADOR;
  
  const accionesPermitidas = useMemo(() => {
    return obtenerAccionesPermitidas(estado, permisos, {
      esCreador: options.esCreador ?? false,
    });
  }, [estado, permisos, options.esCreador]);

  const estadoUI = useMemo(() => {
    return ESTADOS_UI[estado] || ESTADOS_UI[ESTADOS_REQUISICION.BORRADOR];
  }, [estado]);

  const puedeEjecutar = useCallback((accion) => {
    return accionesPermitidas.includes(accion);
  }, [accionesPermitidas]);

  const siguienteEstado = useCallback((accion) => {
    return obtenerSiguienteEstado(estado, accion);
  }, [estado]);

  const esFinal = useMemo(() => {
    return [
      ESTADOS_REQUISICION.SURTIDA,
      ESTADOS_REQUISICION.RECHAZADA,
      ESTADOS_REQUISICION.CANCELADA,
    ].includes(estado);
  }, [estado]);

  const esEditable = useMemo(() => {
    return estado === ESTADOS_REQUISICION.BORRADOR;
  }, [estado]);

  const esCancelable = useMemo(() => {
    return puedeEjecutar(ACCIONES_REQUISICION.CANCELAR);
  }, [puedeEjecutar]);

  return {
    estado,
    estadoUI,
    accionesPermitidas,
    puedeEjecutar,
    siguienteEstado,
    esFinal,
    esEditable,
    esCancelable,
    // Helpers para acciones comunes
    puedeEditar: puedeEjecutar(ACCIONES_REQUISICION.EDITAR),
    puedeEnviar: puedeEjecutar(ACCIONES_REQUISICION.ENVIAR),
    puedeAprobar: puedeEjecutar(ACCIONES_REQUISICION.APROBAR),
    puedeRechazar: puedeEjecutar(ACCIONES_REQUISICION.RECHAZAR),
    puedeSurtir: puedeEjecutar(ACCIONES_REQUISICION.SURTIR),
    puedeEliminar: puedeEjecutar(ACCIONES_REQUISICION.ELIMINAR),
    puedeCancelar: esCancelable,
    puedeVer: puedeEjecutar(ACCIONES_REQUISICION.VER),
    puedeImprimir: puedeEjecutar(ACCIONES_REQUISICION.IMPRIMIR),
    puedeDuplicar: puedeEjecutar(ACCIONES_REQUISICION.DUPLICAR),
  };
};

export default useRequisicionEstado;
