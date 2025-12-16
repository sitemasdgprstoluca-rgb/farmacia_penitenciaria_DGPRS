/**
 * ISS-001 FIX (audit27): Máquina de estados para requisiciones - FLUJO V2
 * 
 * Soporta el flujo jerárquico completo:
 * - Centro: borrador → pendiente_admin → pendiente_director → enviada
 * - Farmacia: enviada → en_revision → autorizada → en_surtido → surtida → entregada
 * - Especiales: devuelta, vencida, rechazada, cancelada
 * 
 * ISS-004 FIX: Permisos dinámicos desde API cuando disponibles
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { requisicionesAPI } from '../services/api';

/**
 * Estados posibles de una requisición - FLUJO V2
 * Alineados con backend/inventario/services/state_machine.py
 * @readonly
 * @enum {string}
 */
export const ESTADOS_REQUISICION = {
  // Estados del flujo del centro
  BORRADOR: 'borrador',
  PENDIENTE_ADMIN: 'pendiente_admin',
  PENDIENTE_DIRECTOR: 'pendiente_director',
  
  // Estados del flujo de farmacia
  ENVIADA: 'enviada',
  EN_REVISION: 'en_revision',
  AUTORIZADA: 'autorizada',
  EN_SURTIDO: 'en_surtido',
  SURTIDA: 'surtida',
  ENTREGADA: 'entregada',
  
  // Estados finales negativos
  RECHAZADA: 'rechazada',
  VENCIDA: 'vencida',
  CANCELADA: 'cancelada',
  DEVUELTA: 'devuelta',
  
  // Compatibilidad legacy
  PENDIENTE: 'pendiente',           // mapea a pendiente_admin
  APROBADA: 'aprobada',             // mapea a autorizada
  EN_PROCESO: 'en_proceso',         // mapea a en_surtido
  SURTIDA_PARCIAL: 'surtida_parcial', // mapea a en_surtido
  PARCIAL: 'parcial',               // deprecated
};

/**
 * Mapeo de estados legacy a V2
 */
export const MAPEO_ESTADOS_LEGACY = {
  'pendiente': 'pendiente_admin',
  'aprobada': 'autorizada',
  'en_proceso': 'en_surtido',
  'surtida_parcial': 'en_surtido',
  'parcial': 'en_surtido',
};

/**
 * Normaliza un estado (soporta legacy)
 */
export const normalizarEstado = (estado) => {
  if (!estado) return ESTADOS_REQUISICION.BORRADOR;
  const estadoLower = estado.toLowerCase();
  return MAPEO_ESTADOS_LEGACY[estadoLower] || estadoLower;
};

/**
 * Acciones posibles sobre una requisición - FLUJO V2
 * @readonly
 * @enum {string}
 */
export const ACCIONES_REQUISICION = {
  // Acciones de edición
  EDITAR: 'editar',
  ELIMINAR: 'eliminar',
  VER: 'ver',
  IMPRIMIR: 'imprimir',
  DUPLICAR: 'duplicar',
  
  // Flujo Centro
  ENVIAR_ADMIN: 'enviar_admin',
  AUTORIZAR_ADMIN: 'autorizar_admin',
  AUTORIZAR_DIRECTOR: 'autorizar_director',
  
  // Flujo Farmacia
  RECIBIR_FARMACIA: 'recibir_farmacia',
  AUTORIZAR_FARMACIA: 'autorizar_farmacia',
  INICIAR_SURTIDO: 'iniciar_surtido',
  SURTIR: 'surtir',
  CONFIRMAR_ENTREGA: 'confirmar_entrega',
  
  // Acciones especiales
  DEVOLVER: 'devolver',
  REENVIAR: 'reenviar',
  RECHAZAR: 'rechazar',
  CANCELAR: 'cancelar',
  MARCAR_VENCIDA: 'marcar_vencida',
  
  // Legacy (compatibilidad)
  ENVIAR: 'enviar',
  APROBAR: 'aprobar',
  SURTIR_PARCIAL: 'surtir_parcial',
};

/**
 * Definición de la máquina de estados V2
 * Cada estado tiene las acciones y transiciones válidas
 */
const TRANSICIONES_V2 = {
  [ESTADOS_REQUISICION.BORRADOR]: {
    acciones: [
      ACCIONES_REQUISICION.EDITAR,
      ACCIONES_REQUISICION.ENVIAR_ADMIN,
      ACCIONES_REQUISICION.ELIMINAR,
      ACCIONES_REQUISICION.VER,
      ACCIONES_REQUISICION.DUPLICAR,
    ],
    transiciones: {
      [ACCIONES_REQUISICION.ENVIAR_ADMIN]: ESTADOS_REQUISICION.PENDIENTE_ADMIN,
      [ACCIONES_REQUISICION.ELIMINAR]: null,
    },
    grupo: 'centro',
  },
  
  [ESTADOS_REQUISICION.PENDIENTE_ADMIN]: {
    acciones: [
      ACCIONES_REQUISICION.AUTORIZAR_ADMIN,
      ACCIONES_REQUISICION.DEVOLVER,
      ACCIONES_REQUISICION.RECHAZAR,
      ACCIONES_REQUISICION.VER,
      ACCIONES_REQUISICION.IMPRIMIR,
    ],
    transiciones: {
      [ACCIONES_REQUISICION.AUTORIZAR_ADMIN]: ESTADOS_REQUISICION.PENDIENTE_DIRECTOR,
      [ACCIONES_REQUISICION.DEVOLVER]: ESTADOS_REQUISICION.DEVUELTA,
      [ACCIONES_REQUISICION.RECHAZAR]: ESTADOS_REQUISICION.RECHAZADA,
    },
    grupo: 'centro',
  },
  
  [ESTADOS_REQUISICION.PENDIENTE_DIRECTOR]: {
    acciones: [
      ACCIONES_REQUISICION.AUTORIZAR_DIRECTOR,
      ACCIONES_REQUISICION.DEVOLVER,
      ACCIONES_REQUISICION.RECHAZAR,
      ACCIONES_REQUISICION.VER,
      ACCIONES_REQUISICION.IMPRIMIR,
    ],
    transiciones: {
      [ACCIONES_REQUISICION.AUTORIZAR_DIRECTOR]: ESTADOS_REQUISICION.ENVIADA,
      [ACCIONES_REQUISICION.DEVOLVER]: ESTADOS_REQUISICION.DEVUELTA,
      [ACCIONES_REQUISICION.RECHAZAR]: ESTADOS_REQUISICION.RECHAZADA,
    },
    grupo: 'centro',
  },
  
  [ESTADOS_REQUISICION.ENVIADA]: {
    acciones: [
      ACCIONES_REQUISICION.RECIBIR_FARMACIA,
      ACCIONES_REQUISICION.VER,
      ACCIONES_REQUISICION.IMPRIMIR,
    ],
    transiciones: {
      [ACCIONES_REQUISICION.RECIBIR_FARMACIA]: ESTADOS_REQUISICION.EN_REVISION,
    },
    grupo: 'farmacia',
  },
  
  [ESTADOS_REQUISICION.EN_REVISION]: {
    acciones: [
      ACCIONES_REQUISICION.AUTORIZAR_FARMACIA,
      ACCIONES_REQUISICION.DEVOLVER,
      ACCIONES_REQUISICION.RECHAZAR,
      ACCIONES_REQUISICION.VER,
      ACCIONES_REQUISICION.IMPRIMIR,
    ],
    transiciones: {
      [ACCIONES_REQUISICION.AUTORIZAR_FARMACIA]: ESTADOS_REQUISICION.AUTORIZADA,
      [ACCIONES_REQUISICION.DEVOLVER]: ESTADOS_REQUISICION.DEVUELTA,
      [ACCIONES_REQUISICION.RECHAZAR]: ESTADOS_REQUISICION.RECHAZADA,
    },
    grupo: 'farmacia',
  },
  
  [ESTADOS_REQUISICION.AUTORIZADA]: {
    acciones: [
      ACCIONES_REQUISICION.INICIAR_SURTIDO,
      ACCIONES_REQUISICION.VER,
      ACCIONES_REQUISICION.IMPRIMIR,
    ],
    transiciones: {
      // FLUJO CORREGIDO: Al iniciar surtido se puede completar y entregar automáticamente
      [ACCIONES_REQUISICION.INICIAR_SURTIDO]: ESTADOS_REQUISICION.EN_SURTIDO,
    },
    grupo: 'farmacia',
  },
  
  [ESTADOS_REQUISICION.EN_SURTIDO]: {
    acciones: [
      ACCIONES_REQUISICION.SURTIR,
      ACCIONES_REQUISICION.VER,
      ACCIONES_REQUISICION.IMPRIMIR,
    ],
    transiciones: {
      // FLUJO CORREGIDO: Al surtir se entrega automáticamente (sin confirmación del centro)
      [ACCIONES_REQUISICION.SURTIR]: ESTADOS_REQUISICION.ENTREGADA,
    },
    grupo: 'farmacia',
  },
  
  [ESTADOS_REQUISICION.SURTIDA]: {
    // ESTADO LEGACY: Se mantiene por compatibilidad pero sin acción de centro
    // NUEVO FLUJO: Ya NO se usa este estado (se pasa directo a ENTREGADA)
    acciones: [
      // ELIMINADO: CONFIRMAR_ENTREGA (automático al surtir)
      ACCIONES_REQUISICION.MARCAR_VENCIDA,
      ACCIONES_REQUISICION.VER,
      ACCIONES_REQUISICION.IMPRIMIR,
    ],
    transiciones: {
      // ELIMINADO: CONFIRMAR_ENTREGA (automático)
      [ACCIONES_REQUISICION.MARCAR_VENCIDA]: ESTADOS_REQUISICION.VENCIDA,
    },
    grupo: 'farmacia',
  },
  
  [ESTADOS_REQUISICION.DEVUELTA]: {
    acciones: [
      ACCIONES_REQUISICION.REENVIAR,
      ACCIONES_REQUISICION.CANCELAR,
      ACCIONES_REQUISICION.VER,
      ACCIONES_REQUISICION.DUPLICAR,
    ],
    transiciones: {
      [ACCIONES_REQUISICION.REENVIAR]: ESTADOS_REQUISICION.BORRADOR,
      [ACCIONES_REQUISICION.CANCELAR]: ESTADOS_REQUISICION.CANCELADA,
    },
    grupo: 'centro',
  },
  
  // Estados terminales
  [ESTADOS_REQUISICION.ENTREGADA]: {
    acciones: [ACCIONES_REQUISICION.VER, ACCIONES_REQUISICION.IMPRIMIR, ACCIONES_REQUISICION.DUPLICAR],
    transiciones: {},
    grupo: 'terminal',
  },
  [ESTADOS_REQUISICION.RECHAZADA]: {
    acciones: [ACCIONES_REQUISICION.VER, ACCIONES_REQUISICION.DUPLICAR],
    transiciones: {},
    grupo: 'terminal',
  },
  [ESTADOS_REQUISICION.VENCIDA]: {
    acciones: [ACCIONES_REQUISICION.VER],
    transiciones: {},
    grupo: 'terminal',
  },
  [ESTADOS_REQUISICION.CANCELADA]: {
    acciones: [ACCIONES_REQUISICION.VER, ACCIONES_REQUISICION.DUPLICAR],
    transiciones: {},
    grupo: 'terminal',
  },
};

/**
 * Mapeo de acciones a permisos requeridos - V2
 */
const PERMISOS_ACCIONES_V2 = {
  [ACCIONES_REQUISICION.EDITAR]: 'editarRequisicion',
  [ACCIONES_REQUISICION.ELIMINAR]: 'eliminarRequisicion',
  [ACCIONES_REQUISICION.VER]: 'verRequisiciones',
  [ACCIONES_REQUISICION.IMPRIMIR]: 'verRequisiciones',
  [ACCIONES_REQUISICION.DUPLICAR]: 'crearRequisicion',
  
  // Flujo Centro
  [ACCIONES_REQUISICION.ENVIAR_ADMIN]: 'crearRequisicion',
  [ACCIONES_REQUISICION.AUTORIZAR_ADMIN]: 'autorizarAdminRequisicion',
  [ACCIONES_REQUISICION.AUTORIZAR_DIRECTOR]: 'autorizarDirectorRequisicion',
  
  // Flujo Farmacia
  [ACCIONES_REQUISICION.RECIBIR_FARMACIA]: 'recibirFarmaciaRequisicion',
  [ACCIONES_REQUISICION.AUTORIZAR_FARMACIA]: 'autorizarFarmaciaRequisicion',
  [ACCIONES_REQUISICION.INICIAR_SURTIDO]: 'surtirRequisicion',
  [ACCIONES_REQUISICION.SURTIR]: 'surtirRequisicion',
  // DEPRECATED: Ya no se usa (surtir entrega automáticamente)
  // [ACCIONES_REQUISICION.CONFIRMAR_ENTREGA]: 'confirmarEntregaRequisicion',
  
  // Especiales
  [ACCIONES_REQUISICION.DEVOLVER]: 'devolverRequisicion',
  [ACCIONES_REQUISICION.REENVIAR]: 'crearRequisicion',
  [ACCIONES_REQUISICION.RECHAZAR]: 'rechazarRequisicion',
  [ACCIONES_REQUISICION.CANCELAR]: 'cancelarRequisicion',
  [ACCIONES_REQUISICION.MARCAR_VENCIDA]: 'marcarVencidaRequisicion',
  
  // Legacy
  [ACCIONES_REQUISICION.ENVIAR]: 'crearRequisicion',
  [ACCIONES_REQUISICION.APROBAR]: 'aprobarRequisicion',
  [ACCIONES_REQUISICION.SURTIR_PARCIAL]: 'surtirRequisicion',
};

/**
 * Etiquetas y colores para cada estado - V2
 */
export const ESTADOS_UI = {
  [ESTADOS_REQUISICION.BORRADOR]: {
    label: 'Borrador',
    color: 'gray',
    bgClass: 'bg-gray-100',
    textClass: 'text-gray-700',
    badgeClass: 'bg-gray-100 text-gray-700',
    icon: '📝',
    descripcion: 'Requisición en edición',
  },
  [ESTADOS_REQUISICION.PENDIENTE_ADMIN]: {
    label: 'Pendiente Admin',
    color: 'yellow',
    bgClass: 'bg-yellow-100',
    textClass: 'text-yellow-700',
    badgeClass: 'bg-yellow-100 text-yellow-700',
    icon: '⏳',
    descripcion: 'Esperando autorización del Administrador',
  },
  [ESTADOS_REQUISICION.PENDIENTE_DIRECTOR]: {
    label: 'Pendiente Director',
    color: 'amber',
    bgClass: 'bg-amber-100',
    textClass: 'text-amber-700',
    badgeClass: 'bg-amber-100 text-amber-700',
    icon: '⏳',
    descripcion: 'Esperando autorización del Director',
  },
  [ESTADOS_REQUISICION.ENVIADA]: {
    label: 'Enviada',
    color: 'blue',
    bgClass: 'bg-blue-100',
    textClass: 'text-blue-700',
    badgeClass: 'bg-blue-100 text-blue-700',
    icon: '📤',
    descripcion: 'Enviada a Farmacia Central',
  },
  [ESTADOS_REQUISICION.EN_REVISION]: {
    label: 'En Revisión',
    color: 'indigo',
    bgClass: 'bg-indigo-100',
    textClass: 'text-indigo-700',
    badgeClass: 'bg-indigo-100 text-indigo-700',
    icon: '🔍',
    descripcion: 'Farmacia está revisando',
  },
  [ESTADOS_REQUISICION.AUTORIZADA]: {
    label: 'Autorizada',
    color: 'cyan',
    bgClass: 'bg-cyan-100',
    textClass: 'text-cyan-700',
    badgeClass: 'bg-cyan-100 text-cyan-700',
    icon: '✅',
    descripcion: 'Autorizada, pendiente de surtido',
  },
  [ESTADOS_REQUISICION.EN_SURTIDO]: {
    label: 'En Surtido',
    color: 'purple',
    bgClass: 'bg-purple-100',
    textClass: 'text-purple-700',
    badgeClass: 'bg-purple-100 text-purple-700',
    icon: '📦',
    descripcion: 'En preparación',
  },
  [ESTADOS_REQUISICION.SURTIDA]: {
    label: 'Surtida',
    color: 'green',
    bgClass: 'bg-green-100',
    textClass: 'text-green-700',
    badgeClass: 'bg-green-100 text-green-700',
    icon: '✅',
    descripcion: 'Lista para recolección',
  },
  [ESTADOS_REQUISICION.ENTREGADA]: {
    label: 'Entregada',
    color: 'emerald',
    bgClass: 'bg-emerald-100',
    textClass: 'text-emerald-700',
    badgeClass: 'bg-emerald-100 text-emerald-700',
    icon: '🎉',
    descripcion: 'Entregada y confirmada',
  },
  [ESTADOS_REQUISICION.DEVUELTA]: {
    label: 'Devuelta',
    color: 'orange',
    bgClass: 'bg-orange-100',
    textClass: 'text-orange-700',
    badgeClass: 'bg-orange-100 text-orange-700',
    icon: '↩️',
    descripcion: 'Devuelta para corrección',
  },
  [ESTADOS_REQUISICION.RECHAZADA]: {
    label: 'Rechazada',
    color: 'red',
    bgClass: 'bg-red-100',
    textClass: 'text-red-700',
    badgeClass: 'bg-red-100 text-red-700',
    icon: '❌',
    descripcion: 'Rechazada',
  },
  [ESTADOS_REQUISICION.VENCIDA]: {
    label: 'Vencida',
    color: 'rose',
    bgClass: 'bg-rose-100',
    textClass: 'text-rose-700',
    badgeClass: 'bg-rose-100 text-rose-700',
    icon: '⏰',
    descripcion: 'No se recolectó a tiempo',
  },
  [ESTADOS_REQUISICION.CANCELADA]: {
    label: 'Cancelada',
    color: 'gray',
    bgClass: 'bg-gray-200',
    textClass: 'text-gray-600',
    badgeClass: 'bg-gray-200 text-gray-600',
    icon: '🚫',
    descripcion: 'Cancelada por el solicitante',
  },
  // Legacy
  [ESTADOS_REQUISICION.PENDIENTE]: {
    label: 'Pendiente',
    color: 'yellow',
    bgClass: 'bg-yellow-100',
    textClass: 'text-yellow-700',
    badgeClass: 'bg-yellow-100 text-yellow-700',
    icon: '⏳',
    descripcion: 'Pendiente de autorización',
  },
  [ESTADOS_REQUISICION.APROBADA]: {
    label: 'Aprobada',
    color: 'blue',
    bgClass: 'bg-blue-100',
    textClass: 'text-blue-700',
    badgeClass: 'bg-blue-100 text-blue-700',
    icon: '✅',
    descripcion: 'Aprobada',
  },
  [ESTADOS_REQUISICION.EN_PROCESO]: {
    label: 'En Proceso',
    color: 'indigo',
    bgClass: 'bg-indigo-100',
    textClass: 'text-indigo-700',
    badgeClass: 'bg-indigo-100 text-indigo-700',
    icon: '📦',
    descripcion: 'En proceso de surtido',
  },
  [ESTADOS_REQUISICION.SURTIDA_PARCIAL]: {
    label: 'Surtida Parcial',
    color: 'orange',
    bgClass: 'bg-orange-100',
    textClass: 'text-orange-700',
    badgeClass: 'bg-orange-100 text-orange-700',
    icon: '📦',
    descripcion: 'Parcialmente surtida',
  },
};

/**
 * Grupos de estados para filtros/pestañas
 */
export const GRUPOS_ESTADOS = {
  centro: {
    label: 'En Centro',
    estados: [
      ESTADOS_REQUISICION.BORRADOR,
      ESTADOS_REQUISICION.PENDIENTE_ADMIN,
      ESTADOS_REQUISICION.PENDIENTE_DIRECTOR,
      ESTADOS_REQUISICION.DEVUELTA,
    ],
  },
  farmacia: {
    label: 'En Farmacia',
    estados: [
      ESTADOS_REQUISICION.ENVIADA,
      ESTADOS_REQUISICION.EN_REVISION,
      ESTADOS_REQUISICION.AUTORIZADA,
      ESTADOS_REQUISICION.EN_SURTIDO,
      ESTADOS_REQUISICION.SURTIDA,
    ],
  },
  completadas: {
    label: 'Completadas',
    estados: [ESTADOS_REQUISICION.ENTREGADA],
  },
  finalizadas: {
    label: 'Finalizadas',
    estados: [
      ESTADOS_REQUISICION.RECHAZADA,
      ESTADOS_REQUISICION.VENCIDA,
      ESTADOS_REQUISICION.CANCELADA,
    ],
  },
};

/**
 * Estados terminales (no permiten más transiciones)
 */
export const ESTADOS_TERMINALES = [
  ESTADOS_REQUISICION.ENTREGADA,
  ESTADOS_REQUISICION.RECHAZADA,
  ESTADOS_REQUISICION.VENCIDA,
  ESTADOS_REQUISICION.CANCELADA,
];

/**
 * Estados editables
 */
export const ESTADOS_EDITABLES = [
  ESTADOS_REQUISICION.BORRADOR,
  ESTADOS_REQUISICION.DEVUELTA,
];

/**
 * Verifica si una transición es válida
 */
export const esTransicionValida = (estadoActual, accion) => {
  const estadoNorm = normalizarEstado(estadoActual);
  const config = TRANSICIONES_V2[estadoNorm];
  if (!config) return false;
  return config.acciones.includes(accion);
};

/**
 * Obtiene el siguiente estado después de una acción
 */
export const obtenerSiguienteEstado = (estadoActual, accion) => {
  const estadoNorm = normalizarEstado(estadoActual);
  const config = TRANSICIONES_V2[estadoNorm];
  if (!config) return null;
  return config.transiciones[accion] ?? null;
};

/**
 * Obtiene las acciones permitidas para un estado y permisos dados
 */
export const obtenerAccionesPermitidas = (estado, permisos = {}, options = {}) => {
  const estadoNorm = normalizarEstado(estado);
  const config = TRANSICIONES_V2[estadoNorm];
  if (!config) return [];

  // ISS-004 FIX: Si hay transiciones dinámicas del API, usarlas
  if (options.transicionesAPI && Array.isArray(options.transicionesAPI)) {
    return config.acciones.filter(accion => {
      // Verificar si la acción está en las transiciones del API
      const accionEnAPI = options.transicionesAPI.includes(accion);
      if (!accionEnAPI && !['ver', 'imprimir', 'duplicar'].includes(accion)) {
        return false;
      }
      return true;
    });
  }

  return config.acciones.filter(accion => {
    const permisoRequerido = PERMISOS_ACCIONES_V2[accion];
    
    if (!permisoRequerido) return true;
    if (!permisos[permisoRequerido]) return false;
    
    // Reglas adicionales por rol
    if (accion === ACCIONES_REQUISICION.EDITAR && !options.esCreador) {
      return permisos.editarCualquierRequisicion || false;
    }
    
    return true;
  });
};

/**
 * Obtiene el grupo al que pertenece un estado
 */
export const obtenerGrupoEstado = (estado) => {
  const estadoNorm = normalizarEstado(estado);
  const config = TRANSICIONES_V2[estadoNorm];
  return config?.grupo || 'desconocido';
};

/**
 * Cache para transiciones del API
 */
let transicionesAPICache = null;
let transicionesCacheTime = 0;
const CACHE_TTL = 5 * 60 * 1000; // 5 minutos

/**
 * Hook para usar la máquina de estados de requisiciones - V2
 */
export const useRequisicionEstado = (requisicion, permisos = {}, options = {}) => {
  const [transicionesAPI, setTransicionesAPI] = useState(null);
  const [loadingTransiciones, setLoadingTransiciones] = useState(false);
  
  const estado = requisicion?.estado || ESTADOS_REQUISICION.BORRADOR;
  const estadoNormalizado = normalizarEstado(estado);

  // ISS-004 FIX: Cargar transiciones disponibles del API
  useEffect(() => {
    const cargarTransiciones = async () => {
      // Verificar cache
      if (transicionesAPICache && Date.now() - transicionesCacheTime < CACHE_TTL) {
        setTransicionesAPI(transicionesAPICache);
        return;
      }

      if (!options.usarTransicionesAPI) return;

      setLoadingTransiciones(true);
      try {
        const response = await requisicionesAPI.getTransicionesDisponibles();
        transicionesAPICache = response.data;
        transicionesCacheTime = Date.now();
        setTransicionesAPI(response.data);
      } catch (error) {
        console.warn('[useRequisicionEstado] Error cargando transiciones:', error);
      } finally {
        setLoadingTransiciones(false);
      }
    };

    cargarTransiciones();
  }, [options.usarTransicionesAPI]);
  
  const accionesPermitidas = useMemo(() => {
    return obtenerAccionesPermitidas(estadoNormalizado, permisos, {
      esCreador: options.esCreador ?? false,
      transicionesAPI: transicionesAPI?.[estadoNormalizado] || null,
    });
  }, [estadoNormalizado, permisos, options.esCreador, transicionesAPI]);

  const estadoUI = useMemo(() => {
    return ESTADOS_UI[estadoNormalizado] || ESTADOS_UI[estado] || ESTADOS_UI[ESTADOS_REQUISICION.BORRADOR];
  }, [estadoNormalizado, estado]);

  const puedeEjecutar = useCallback((accion) => {
    return accionesPermitidas.includes(accion);
  }, [accionesPermitidas]);

  const siguienteEstado = useCallback((accion) => {
    return obtenerSiguienteEstado(estadoNormalizado, accion);
  }, [estadoNormalizado]);

  const grupoEstado = useMemo(() => {
    return obtenerGrupoEstado(estadoNormalizado);
  }, [estadoNormalizado]);

  const esFinal = useMemo(() => {
    return ESTADOS_TERMINALES.includes(estadoNormalizado);
  }, [estadoNormalizado]);

  const esEditable = useMemo(() => {
    return ESTADOS_EDITABLES.includes(estadoNormalizado);
  }, [estadoNormalizado]);

  const esEnCentro = useMemo(() => {
    return GRUPOS_ESTADOS.centro.estados.includes(estadoNormalizado);
  }, [estadoNormalizado]);

  const esEnFarmacia = useMemo(() => {
    return GRUPOS_ESTADOS.farmacia.estados.includes(estadoNormalizado);
  }, [estadoNormalizado]);

  return {
    // Estado
    estado: estadoNormalizado,
    estadoOriginal: estado,
    estadoUI,
    grupoEstado,
    
    // Acciones
    accionesPermitidas,
    puedeEjecutar,
    siguienteEstado,
    loadingTransiciones,
    
    // Flags
    esFinal,
    esEditable,
    esEnCentro,
    esEnFarmacia,
    esCancelable: puedeEjecutar(ACCIONES_REQUISICION.CANCELAR),
    
    // Helpers V2
    puedeEditar: puedeEjecutar(ACCIONES_REQUISICION.EDITAR),
    puedeEnviarAdmin: puedeEjecutar(ACCIONES_REQUISICION.ENVIAR_ADMIN),
    puedeAutorizarAdmin: puedeEjecutar(ACCIONES_REQUISICION.AUTORIZAR_ADMIN),
    puedeAutorizarDirector: puedeEjecutar(ACCIONES_REQUISICION.AUTORIZAR_DIRECTOR),
    puedeRecibirFarmacia: puedeEjecutar(ACCIONES_REQUISICION.RECIBIR_FARMACIA),
    puedeAutorizarFarmacia: puedeEjecutar(ACCIONES_REQUISICION.AUTORIZAR_FARMACIA),
    puedeSurtir: puedeEjecutar(ACCIONES_REQUISICION.SURTIR),
    puedeConfirmarEntrega: puedeEjecutar(ACCIONES_REQUISICION.CONFIRMAR_ENTREGA),
    puedeDevolver: puedeEjecutar(ACCIONES_REQUISICION.DEVOLVER),
    puedeReenviar: puedeEjecutar(ACCIONES_REQUISICION.REENVIAR),
    puedeRechazar: puedeEjecutar(ACCIONES_REQUISICION.RECHAZAR),
    puedeCancelar: puedeEjecutar(ACCIONES_REQUISICION.CANCELAR),
    puedeEliminar: puedeEjecutar(ACCIONES_REQUISICION.ELIMINAR),
    puedeVer: puedeEjecutar(ACCIONES_REQUISICION.VER),
    puedeImprimir: puedeEjecutar(ACCIONES_REQUISICION.IMPRIMIR),
    puedeDuplicar: puedeEjecutar(ACCIONES_REQUISICION.DUPLICAR),
    
    // Legacy compatibility
    puedeEnviar: puedeEjecutar(ACCIONES_REQUISICION.ENVIAR_ADMIN),
    puedeAprobar: puedeEjecutar(ACCIONES_REQUISICION.AUTORIZAR_ADMIN) || 
                   puedeEjecutar(ACCIONES_REQUISICION.AUTORIZAR_DIRECTOR),
  };
};

export default useRequisicionEstado;
