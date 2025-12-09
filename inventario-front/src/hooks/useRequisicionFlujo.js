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
 */
const ACCIONES_FLUJO = {
  enviar_admin: {
    endpoint: 'enviarAdmin',
    label: 'Enviar a Administrador',
    estadosPermitidos: ['borrador'],
    estadoResultante: 'pendiente_admin',
    rolesPermitidos: ['medico', 'admin', 'farmacia'],
    confirmacion: true,
    color: 'blue',
  },
  autorizar_admin: {
    endpoint: 'autorizarAdmin',
    label: 'Autorizar (Admin)',
    estadosPermitidos: ['pendiente_admin'],
    estadoResultante: 'pendiente_director',
    rolesPermitidos: ['administrador_centro', 'admin'],
    confirmacion: true,
    color: 'green',
  },
  autorizar_director: {
    endpoint: 'autorizarDirector',
    label: 'Autorizar (Director)',
    estadosPermitidos: ['pendiente_director'],
    estadoResultante: 'enviada',
    rolesPermitidos: ['director_centro', 'admin'],
    confirmacion: true,
    color: 'green',
  },
  recibir_farmacia: {
    endpoint: 'recibirFarmacia',
    label: 'Recibir en Farmacia',
    estadosPermitidos: ['enviada'],
    estadoResultante: 'en_revision',
    rolesPermitidos: ['farmacia', 'admin', 'admin_farmacia'],
    confirmacion: true,
    color: 'cyan',
  },
  autorizar_farmacia: {
    endpoint: 'autorizarFarmacia',
    label: 'Autorizar y Asignar Fecha',
    estadosPermitidos: ['en_revision', 'enviada'],
    estadoResultante: 'autorizada',
    rolesPermitidos: ['farmacia', 'admin', 'admin_farmacia'],
    requiereFechaRecoleccion: true,
    confirmacion: true,
    color: 'indigo',
  },
  surtir: {
    endpoint: 'surtir',
    label: 'Surtir',
    estadosPermitidos: ['autorizada', 'parcial'],
    estadoResultante: 'surtida',
    rolesPermitidos: ['farmacia', 'admin', 'admin_farmacia'],
    confirmacion: true,
    color: 'violet',
  },
  confirmar_entrega: {
    endpoint: 'confirmarEntrega',
    label: 'Confirmar Entrega',
    estadosPermitidos: ['surtida'],
    estadoResultante: 'entregada',
    rolesPermitidos: ['medico', 'centro', 'admin', 'farmacia'],
    requiereLugarEntrega: true,
    confirmacion: true,
    color: 'green',
  },
  devolver: {
    endpoint: 'devolver',
    label: 'Devolver al Centro',
    estadosPermitidos: ['pendiente_admin', 'pendiente_director', 'en_revision'],
    estadoResultante: 'devuelta',
    rolesPermitidos: ['administrador_centro', 'director_centro', 'farmacia', 'admin'],
    requiereMotivo: true,
    confirmacion: true,
    color: 'amber',
  },
  reenviar: {
    endpoint: 'reenviar',
    label: 'Reenviar',
    estadosPermitidos: ['devuelta'],
    estadoResultante: 'pendiente_admin',
    rolesPermitidos: ['medico', 'centro', 'admin'],
    confirmacion: true,
    color: 'blue',
  },
  rechazar: {
    endpoint: 'rechazar',
    label: 'Rechazar',
    estadosPermitidos: ['pendiente_admin', 'pendiente_director', 'enviada', 'en_revision'],
    estadoResultante: 'rechazada',
    rolesPermitidos: ['administrador_centro', 'director_centro', 'farmacia', 'admin'],
    requiereMotivo: true,
    confirmacion: true,
    color: 'red',
  },
  cancelar: {
    endpoint: 'cancelar',
    label: 'Cancelar',
    estadosPermitidos: ['borrador', 'devuelta', 'autorizada', 'en_surtido'],
    estadoResultante: 'cancelada',
    rolesPermitidos: ['medico', 'centro', 'farmacia', 'admin'],
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
  
  const rolUsuario = useMemo(() => {
    const rol = user?.rol?.toLowerCase() || getRolPrincipal()?.toLowerCase() || '';
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
   * Verifica si el usuario puede ejecutar una acción
   */
  const puedeEjecutarAccion = useCallback((accionKey, estadoActual) => {
    if (esSuperuser) return true;
    
    const accion = ACCIONES_FLUJO[accionKey];
    if (!accion) return false;
    
    // Verificar estado
    if (!accion.estadosPermitidos.includes(estadoActual)) {
      return false;
    }
    
    // Verificar rol
    if (!accion.rolesPermitidos.includes(rolUsuario)) {
      // También verificar roles legacy
      const rolesLegacy = {
        'admin_sistema': 'admin',
        'superusuario': 'admin',
        'admin_farmacia': 'farmacia',
        'usuario_normal': 'centro',
      };
      const rolNormalizado = rolesLegacy[rolUsuario] || rolUsuario;
      if (!accion.rolesPermitidos.includes(rolNormalizado)) {
        return false;
      }
    }
    
    // Verificar transición
    return esTransicionValida(estadoActual, accion.estadoResultante);
  }, [rolUsuario, esSuperuser, esTransicionValida]);
  
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
