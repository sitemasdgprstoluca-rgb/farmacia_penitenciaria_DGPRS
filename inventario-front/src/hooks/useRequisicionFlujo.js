/**
 * FLUJO V2: Hook para manejo de transiciones de estado de requisiciones
 * 
 * Proporciona:
 * - Acciones disponibles según rol y estado
 * - Validación de transiciones
 * - Llamadas a API con manejo de errores
 */

import { useState, useCallback, useMemo } from 'react';
import { requisicionesAPI } from '../services/api';
import { usePermissions } from './usePermissions';
import { 
  TRANSICIONES_REQUISICION, 
  ESTADOS_FINALES,
  REQUISICION_ESTADOS 
} from '../constants/strings';
import { toast } from 'react-hot-toast';

/**
 * Mapeo de acciones a endpoints y permisos requeridos
 * ISS-PERFILES FIX: Incluir roles legacy (usuario_centro, usuario_normal, admin_sistema, superusuario)
 */
const ACCIONES_FLUJO = {
  enviar_admin: {
    endpoint: 'enviarAdmin',
    label: 'Enviar a Administrador',
    estadosPermitidos: ['borrador'],
    estadoResultante: 'pendiente_admin',
    rolesPermitidos: ['medico', 'usuario_centro', 'usuario_normal', 'admin', 'admin_sistema', 'superusuario', 'farmacia'],
    confirmacion: true,
    color: 'blue',
  },
  autorizar_admin: {
    endpoint: 'autorizarAdmin',
    label: 'Autorizar (Admin)',
    estadosPermitidos: ['pendiente_admin'],
    estadoResultante: 'pendiente_director',
    // ISS-FIX: Incluir 'centro' para usuarios adminCentro que tienen ese rol
    rolesPermitidos: ['administrador_centro', 'centro', 'admin', 'admin_sistema', 'superusuario'],
    confirmacion: true,
    color: 'green',
  },
  autorizar_director: {
    endpoint: 'autorizarDirector',
    label: 'Autorizar (Director)',
    estadosPermitidos: ['pendiente_director'],
    estadoResultante: 'enviada',
    // ISS-FIX: Incluir 'centro' para usuarios directorCentro que pueden tener ese rol
    rolesPermitidos: ['director_centro', 'centro', 'admin', 'admin_sistema', 'superusuario'],
    confirmacion: true,
    color: 'green',
  },
  recibir_farmacia: {
    endpoint: 'recibirFarmacia',
    label: 'Recibir en Farmacia',
    estadosPermitidos: ['enviada'],
    estadoResultante: 'en_revision',
    rolesPermitidos: ['farmacia', 'admin', 'admin_farmacia', 'admin_sistema', 'superusuario'],
    confirmacion: true,
    color: 'cyan',
  },
  autorizar_farmacia: {
    endpoint: 'autorizarFarmacia',
    label: 'Autorizar y Asignar Fecha',
    estadosPermitidos: ['en_revision', 'enviada'],
    estadoResultante: 'autorizada',
    rolesPermitidos: ['farmacia', 'admin', 'admin_farmacia', 'admin_sistema', 'superusuario'],
    requiereFechaRecoleccion: true,
    confirmacion: true,
    color: 'indigo',
  },
  surtir: {
    endpoint: 'surtir',
    label: 'Surtir y Entregar',
    estadosPermitidos: ['autorizada', 'parcial', 'en_surtido'],
    // CAMBIO CRÍTICO: Surtir ahora va directo a ENTREGADA (sin paso intermedio)
    estadoResultante: 'entregada',
    rolesPermitidos: ['farmacia', 'admin', 'admin_farmacia', 'admin_sistema', 'superusuario'],
    confirmacion: true,
    color: 'green',
  },
  // DEPRECATED: confirmar_entrega ya no se usa - surtir entrega automáticamente
  // Se mantiene comentado por si se necesita revertir
  /*
  confirmar_entrega: {
    endpoint: 'confirmarEntrega',
    label: 'Confirmar Entrega',
    estadosPermitidos: ['surtida'],
    estadoResultante: 'entregada',
    rolesPermitidos: ['farmacia', 'admin', 'admin_sistema', 'superusuario'],
    requiereLugarEntrega: true,
    confirmacion: true,
    color: 'green',
  },
  */
  devolver: {
    endpoint: 'devolver',
    label: 'Devolver al Centro',
    estadosPermitidos: ['pendiente_admin', 'pendiente_director', 'en_revision'],
    estadoResultante: 'devuelta',
    // ISS-FIX: Incluir 'centro' para usuarios que pueden tener ese rol genérico
    rolesPermitidos: ['administrador_centro', 'director_centro', 'centro', 'farmacia', 'admin', 'admin_farmacia', 'admin_sistema', 'superusuario'],
    requiereMotivo: true,
    confirmacion: true,
    color: 'amber',
  },
  reenviar: {
    endpoint: 'reenviar',
    label: 'Reenviar',
    estadosPermitidos: ['devuelta'],
    estadoResultante: 'pendiente_admin',
    rolesPermitidos: ['medico', 'centro', 'usuario_centro', 'usuario_normal', 'admin', 'admin_sistema', 'superusuario'],
    confirmacion: true,
    color: 'blue',
  },
  rechazar: {
    endpoint: 'rechazar',
    label: 'Rechazar',
    estadosPermitidos: ['pendiente_admin', 'pendiente_director', 'enviada', 'en_revision'],
    estadoResultante: 'rechazada',
    // ISS-FIX: Incluir 'centro' para usuarios con ese rol genérico
    rolesPermitidos: ['administrador_centro', 'director_centro', 'centro', 'farmacia', 'admin', 'admin_farmacia', 'admin_sistema', 'superusuario'],
    requiereMotivo: true,
    confirmacion: true,
    color: 'red',
  },
  cancelar: {
    endpoint: 'cancelar',
    label: 'Cancelar',
    // ISS-TRANSICIONES FIX: Según spec, cancelar solo desde borrador, autorizada, en_surtido, devuelta
    estadosPermitidos: ['borrador', 'autorizada', 'en_surtido', 'devuelta'],
    estadoResultante: 'cancelada',
    rolesPermitidos: ['medico', 'centro', 'usuario_centro', 'usuario_normal', 'farmacia', 'admin', 'admin_sistema', 'superusuario'],
    requiereMotivo: false,
    confirmacion: true,
    color: 'gray',
  },
  marcar_vencida: {
    endpoint: 'marcarVencida',
    label: 'Marcar como Vencida',
    estadosPermitidos: ['surtida'],
    estadoResultante: 'vencida',
    rolesPermitidos: ['admin'],
    requiereMotivo: false,
    confirmacion: true,
    color: 'red',
  },
};

/**
 * Hook principal para el flujo de requisiciones
 */
export function useRequisicionFlujo() {
  const { user, getRolPrincipal } = usePermissions();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // ISS-DIRECTOR FIX: Usar rol_efectivo del backend si está disponible
  // rol_efectivo ya incluye inferencia de rol cuando el campo está vacío
  const rolUsuario = useMemo(() => {
    const rol = (user?.rol_efectivo || user?.rol || '').toLowerCase() || getRolPrincipal()?.toLowerCase() || '';
    return rol;
  }, [user, getRolPrincipal]);
  
  const esSuperuser = user?.is_superuser || false;
  
  /**
   * Verifica si una transición es válida según las reglas
   */
  const esTransicionValida = useCallback((estadoActual, estadoNuevo) => {
    const transicionesPermitidas = TRANSICIONES_REQUISICION[estadoActual] || [];
    return transicionesPermitidas.includes(estadoNuevo);
  }, []);
  
  /**
   * FLUJO V2: Verifica si el usuario puede ejecutar una acción
   * Validación estricta por rol Y estado
   */
  const puedeEjecutarAccion = useCallback((accionKey, estadoActual) => {
    const accion = ACCIONES_FLUJO[accionKey];
    if (!accion) return false;
    
    // 1. Verificar que el estado actual permite esta acción
    if (!accion.estadosPermitidos.includes(estadoActual)) {
      return false;
    }
    
    // 2. Superuser puede todo
    if (esSuperuser) return true;
    
    const rolLower = rolUsuario.toLowerCase();
    
    // 3. FLUJO V2: Validación ESTRICTA por rol y acción específica
    // Cada acción solo la puede hacer el rol correspondiente
    
    switch (accionKey) {
      // === ACCIONES DEL CENTRO PENITENCIARIO ===
      case 'enviar_admin':
        // Solo médicos/usuarios del centro pueden enviar a admin
        return ['medico', 'usuario_centro', 'usuario_normal'].includes(rolLower);
      
      case 'autorizar_admin':
        // Solo administrador del centro en estado pendiente_admin
        return ['administrador_centro', 'admin_centro'].includes(rolLower) && estadoActual === 'pendiente_admin';
      
      case 'autorizar_director':
        // Solo director del centro en estado pendiente_director
        return ['director_centro', 'director'].includes(rolLower) && estadoActual === 'pendiente_director';
      
      // === ACCIONES DE FARMACIA ===
      case 'recibir_farmacia':
        // Solo farmacia cuando llega la requisición (enviada)
        return ['farmacia', 'admin_farmacia'].includes(rolLower) && estadoActual === 'enviada';
      
      case 'autorizar_farmacia':
        // Farmacia autoriza en en_revision o enviada (si omite recibir)
        return ['farmacia', 'admin_farmacia'].includes(rolLower) && 
               ['en_revision', 'enviada'].includes(estadoActual);
      
      case 'surtir':
        // Farmacia surte cuando está autorizada, en_surtido o parcial
        return ['farmacia', 'admin_farmacia'].includes(rolLower) && 
               ['autorizada', 'en_surtido', 'parcial'].includes(estadoActual);
      
      // === ACCIONES DE DEVOLUCIÓN/RECHAZO ===
      case 'devolver':
        // Admin/Director/Farmacia pueden devolver según el estado
        if (estadoActual === 'pendiente_admin' && ['administrador_centro', 'admin_centro'].includes(rolLower)) return true;
        if (estadoActual === 'pendiente_director' && ['director_centro', 'director'].includes(rolLower)) return true;
        if (estadoActual === 'en_revision' && ['farmacia', 'admin_farmacia'].includes(rolLower)) return true;
        return false;
      
      case 'reenviar':
        // El solicitante original puede reenviar desde devuelta
        return ['medico', 'usuario_centro', 'usuario_normal'].includes(rolLower) && estadoActual === 'devuelta';
      
      case 'rechazar':
        // Cada rol rechaza en su etapa específica
        if (estadoActual === 'pendiente_admin' && ['administrador_centro', 'admin_centro'].includes(rolLower)) return true;
        if (estadoActual === 'pendiente_director' && ['director_centro', 'director'].includes(rolLower)) return true;
        if (['enviada', 'en_revision'].includes(estadoActual) && ['farmacia', 'admin_farmacia'].includes(rolLower)) return true;
        return false;
      
      case 'cancelar':
        // Quien creó puede cancelar en estados tempranos, farmacia en estados de farmacia
        if (['borrador', 'devuelta'].includes(estadoActual) && 
            ['medico', 'usuario_centro', 'usuario_normal'].includes(rolLower)) return true;
        if (['autorizada', 'en_surtido'].includes(estadoActual) && 
            ['farmacia', 'admin_farmacia'].includes(rolLower)) return true;
        return false;
      
      default:
        return false;
    }
  }, [rolUsuario, esSuperuser]);
  
  /**
   * Obtiene las acciones disponibles para una requisición
   */
  const getAccionesDisponibles = useCallback((requisicion) => {
    if (!requisicion) return [];
    
    const estadoActual = requisicion.estado?.toLowerCase();
    
    // Estados finales no tienen acciones
    if (ESTADOS_FINALES.includes(estadoActual)) {
      return [];
    }
    
    const acciones = [];
    
    Object.entries(ACCIONES_FLUJO).forEach(([key, config]) => {
      if (puedeEjecutarAccion(key, estadoActual)) {
        acciones.push({
          key,
          ...config,
        });
      }
    });
    
    return acciones;
  }, [puedeEjecutarAccion]);
  
  /**
   * Ejecuta una acción del flujo
   */
  const ejecutarAccion = useCallback(async (accionKey, requisicionId, data = {}) => {
    const accion = ACCIONES_FLUJO[accionKey];
    if (!accion) {
      throw new Error(`Acción desconocida: ${accionKey}`);
    }
    
    const apiMethod = requisicionesAPI[accion.endpoint];
    if (!apiMethod) {
      throw new Error(`Endpoint no implementado: ${accion.endpoint}`);
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiMethod(requisicionId, data);
      return response.data;
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.message || 'Error al ejecutar la acción';
      setError(errorMsg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);
  
  /**
   * Obtiene el historial de cambios de estado
   */
  const getHistorial = useCallback(async (requisicionId) => {
    setLoading(true);
    try {
      const response = await requisicionesAPI.getHistorial(requisicionId);
      return response.data;
    } catch (err) {
      const errorMsg = err.response?.data?.error || 'Error al obtener historial';
      setError(errorMsg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);
  
  /**
   * Obtiene información del estado
   */
  const getEstadoInfo = useCallback((estado) => {
    const estadoLower = estado?.toLowerCase();
    const estadoKey = Object.keys(REQUISICION_ESTADOS).find(
      key => REQUISICION_ESTADOS[key].value === estadoLower
    );
    return estadoKey ? REQUISICION_ESTADOS[estadoKey] : null;
  }, []);
  
  /**
   * Verifica si un estado es final
   */
  const esEstadoFinal = useCallback((estado) => {
    return ESTADOS_FINALES.includes(estado?.toLowerCase());
  }, []);
  
  return {
    // Estado
    loading,
    error,
    rolUsuario,
    esSuperuser,
    
    // Métodos de validación
    esTransicionValida,
    puedeEjecutarAccion,
    getAccionesDisponibles,
    esEstadoFinal,
    getEstadoInfo,
    
    // Métodos de ejecución
    ejecutarAccion,
    getHistorial,
    
    // Constantes exportadas
    ACCIONES_FLUJO,
  };
}

export default useRequisicionFlujo;
