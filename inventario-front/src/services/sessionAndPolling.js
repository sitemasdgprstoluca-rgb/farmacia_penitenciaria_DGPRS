/**
 * ISS-010: Manejo de sesión expirada.
 * ISS-022: Sistema de actualización de estado en tiempo real.
 * 
 * Componentes y hooks para:
 * - Detectar y manejar sesiones expiradas
 * - Polling inteligente para actualizaciones
 * - Notificaciones de cambios de estado
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { toast } from 'react-hot-toast';
import { clearTokens, hasAccessToken } from './tokenManager';

// =============================================================================
// ISS-010: Manejador de Sesión Expirada
// =============================================================================

/**
 * ISS-010: Clase para manejar sesiones expiradas.
 * 
 * Características:
 * - Detecta expiración por respuesta 401
 * - Muestra modal de reautenticación
 * - Permite continuar o cerrar sesión
 */
class SessionManager {
  constructor() {
    this.isExpired = false;
    this.expirationCallbacks = new Set();
    this.warningShown = false;
    this.redirectTimeout = null;
    
    // Escuchar evento de sesión expirada
    if (typeof window !== 'undefined') {
      window.addEventListener('session-expired', this.handleExpiration.bind(this));
    }
  }
  
  /**
   * Registra callback para cuando expire la sesión
   */
  onExpiration(callback) {
    this.expirationCallbacks.add(callback);
    return () => this.expirationCallbacks.delete(callback);
  }
  
  /**
   * ISS-010: Maneja la expiración de sesión
   */
  handleExpiration() {
    if (this.isExpired) return;
    
    this.isExpired = true;
    
    // Notificar a todos los listeners
    this.expirationCallbacks.forEach(cb => {
      try {
        cb();
      } catch (e) {
        console.error('Error en callback de expiracion:', e);
      }
    });
    
    // Mostrar aviso (solo una vez)
    if (!this.warningShown) {
      this.warningShown = true;
      toast.error('Tu sesion ha expirado. Por favor, inicia sesion nuevamente.', {
        duration: 5000,
        id: 'session-expired'
      });
    }
  }
  
  /**
   * Resetea el estado de sesion (despues de nuevo login)
   */
  reset() {
    this.isExpired = false;
    this.warningShown = false;
    if (this.redirectTimeout) {
      clearTimeout(this.redirectTimeout);
      this.redirectTimeout = null;
    }
  }
  
  /**
   * Verifica si la sesión está activa
   */
  isSessionActive() {
    return !this.isExpired && hasAccessToken();
  }
}

// Singleton del manejador de sesión
export const sessionManager = new SessionManager();


// =============================================================================
// ISS-010: Hook de sesión expirada
// =============================================================================

/**
 * ISS-010: Hook para manejar sesiones expiradas en componentes.
 * 
 * @returns {Object} Estado y métodos de sesión
 */
export function useSessionExpiration() {
  const [isExpired, setIsExpired] = useState(false);
  
  useEffect(() => {
    const unsubscribe = sessionManager.onExpiration(() => {
      setIsExpired(true);
    });
    
    return unsubscribe;
  }, []);
  
  const redirectToLogin = useCallback(() => {
    clearTokens();
    window.location.href = '/login';
  }, []);
  
  return {
    isExpired,
    redirectToLogin,
    isSessionActive: sessionManager.isSessionActive()
  };
}


// =============================================================================
// ISS-022: Sistema de Polling para Actualizaciones en Tiempo Real
// =============================================================================

/**
 * ISS-022: Configuración de polling por tipo de recurso.
 * ISS-DB-002: Estados alineados con BD Supabase
 * BD permite: borrador, enviada, autorizada, rechazada, en_surtido, surtida, parcial, cancelada, entregada
 */
const POLLING_CONFIG = {
  requisiciones: {
    interval: 30000,      // 30 segundos
    // ISS-DB-002: Estados activos que requieren polling
    enabledStates: ['enviada', 'autorizada', 'en_surtido', 'parcial', 'surtida'],
  },
  notificaciones: {
    interval: 60000,      // 1 minuto
    enabledStates: null,  // Siempre activo
  },
  inventario: {
    interval: 120000,     // 2 minutos
    enabledStates: null,
  },
};


/**
 * ISS-022: Hook de polling inteligente.
 * 
 * Características:
 * - Pausa cuando la pestaña no está visible
 * - Ajusta intervalo según actividad
 * - Cancela polling en cleanup
 * 
 * @param {Function} fetchFn - Función para obtener datos
 * @param {Object} options - Opciones de configuración
 * @returns {Object} Estado y control del polling
 */
export function usePolling(fetchFn, options = {}) {
  const {
    interval = 30000,
    enabled = true,
    pauseWhenHidden = true,
    onUpdate = null,
    dependencies = [],
  } = options;
  
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  
  const intervalRef = useRef(null);
  const isActiveRef = useRef(enabled);
  const mountedRef = useRef(true);
  
  // Función de fetch con manejo de errores
  const doFetch = useCallback(async () => {
    if (!isActiveRef.current || !mountedRef.current) return;
    if (!sessionManager.isSessionActive()) return;
    
    try {
      setLoading(true);
      const result = await fetchFn();
      
      if (!mountedRef.current) return;
      
      setData(result);
      setLastUpdate(new Date());
      setError(null);
      
      if (onUpdate) {
        onUpdate(result);
      }
    } catch (err) {
      if (!mountedRef.current) return;
      
      // No reportar error si es por sesión expirada
      if (err?.response?.status !== 401) {
        setError(err);
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [fetchFn, onUpdate]);
  
  // Iniciar/detener polling
  const startPolling = useCallback(() => {
    if (intervalRef.current) return;
    
    intervalRef.current = setInterval(doFetch, interval);
  }, [doFetch, interval]);
  
  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);
  
  // Forzar actualización inmediata
  const refresh = useCallback(() => {
    doFetch();
  }, [doFetch]);
  
  // Manejar visibilidad de la página
  useEffect(() => {
    if (!pauseWhenHidden) return;
    
    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopPolling();
      } else if (isActiveRef.current) {
        doFetch(); // Fetch inmediato al volver
        startPolling();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [pauseWhenHidden, doFetch, startPolling, stopPolling]);
  
  // Iniciar polling al montar
  useEffect(() => {
    mountedRef.current = true;
    isActiveRef.current = enabled;
    
    if (enabled) {
      doFetch(); // Fetch inicial
      startPolling();
    }
    
    return () => {
      mountedRef.current = false;
      stopPolling();
    };
  }, [enabled, ...dependencies]);
  
  return {
    data,
    loading,
    error,
    lastUpdate,
    refresh,
    startPolling,
    stopPolling,
    isActive: isActiveRef.current,
  };
}


// =============================================================================
// ISS-022: Hook específico para estado de requisiciones
// =============================================================================

/**
 * ISS-022: Hook para monitorear cambios de estado en requisiciones.
 * 
 * @param {number} requisicionId - ID de la requisición a monitorear
 * @param {string} estadoActual - Estado actual de la requisición
 * @param {Function} onEstadoCambio - Callback cuando cambia el estado
 */
export function useRequisicionStatePolling(requisicionId, estadoActual, onEstadoCambio) {
  const config = POLLING_CONFIG.requisiciones;
  
  // Solo habilitar polling para ciertos estados
  const shouldPoll = config.enabledStates 
    ? config.enabledStates.includes(estadoActual)
    : true;
  
  const { data, refresh, lastUpdate } = usePolling(
    async () => {
      const { requisicionesAPI } = await import('./api');
      const response = await requisicionesAPI.getById(requisicionId);
      return response.data;
    },
    {
      interval: config.interval,
      enabled: shouldPoll && requisicionId != null,
      pauseWhenHidden: true,
      onUpdate: (requisicion) => {
        if (requisicion && requisicion.estado !== estadoActual) {
          onEstadoCambio?.(requisicion.estado, requisicion);
          
          // Notificar cambio
          toast.success(
            `Requisición ${requisicion.folio}: Estado actualizado a "${requisicion.estado}"`,
            { duration: 4000 }
          );
        }
      },
      dependencies: [requisicionId, estadoActual],
    }
  );
  
  return { requisicion: data, refresh, lastUpdate };
}


// =============================================================================
// ISS-022: Hook para notificaciones en tiempo real
// =============================================================================

/**
 * ISS-022: Hook para polling de notificaciones.
 */
export function useNotificacionesPolling(onNewNotification) {
  const config = POLLING_CONFIG.notificaciones;
  const [unreadCount, setUnreadCount] = useState(0);
  
  const { data, refresh, lastUpdate } = usePolling(
    async () => {
      const { notificacionesAPI } = await import('./api');
      const response = await notificacionesAPI.getAll({ leida: false, page_size: 10 });
      return response.data;
    },
    {
      interval: config.interval,
      enabled: true,
      pauseWhenHidden: true,
      onUpdate: (result) => {
        const count = result?.count || result?.length || 0;
        
        // Si hay más notificaciones que antes, notificar
        if (count > unreadCount && unreadCount > 0) {
          onNewNotification?.(result);
        }
        
        setUnreadCount(count);
      },
    }
  );
  
  return { 
    notificaciones: data?.results || data || [], 
    unreadCount, 
    refresh, 
    lastUpdate 
  };
}


// =============================================================================
// ISS-006: Validador de cantidad para frontend
// =============================================================================

/**
 * ISS-006: Valida cantidad de movimiento en el frontend.
 * 
 * @param {string} tipo - Tipo de movimiento ('entrada', 'salida', 'ajuste')
 * @param {number} cantidad - Cantidad a validar
 * @param {number} stockDisponible - Stock disponible (para salidas)
 * @returns {Object} Resultado de validación
 */
export function validarCantidadMovimiento(tipo, cantidad, stockDisponible = null) {
  const resultado = {
    valido: true,
    errores: [],
    advertencias: [],
  };
  
  // Convertir a número
  const cantidadNum = parseFloat(cantidad);
  
  if (isNaN(cantidadNum)) {
    resultado.valido = false;
    resultado.errores.push('La cantidad debe ser un número válido');
    return resultado;
  }
  
  if (cantidadNum === 0) {
    resultado.valido = false;
    resultado.errores.push('La cantidad no puede ser 0');
    return resultado;
  }
  
  switch (tipo) {
    case 'entrada':
      if (cantidadNum <= 0) {
        resultado.valido = false;
        resultado.errores.push('Las entradas deben tener cantidad positiva');
      }
      break;
      
    case 'salida':
      if (cantidadNum >= 0) {
        resultado.valido = false;
        resultado.errores.push('Las salidas deben tener cantidad negativa');
      }
      if (stockDisponible !== null && Math.abs(cantidadNum) > stockDisponible) {
        resultado.valido = false;
        resultado.errores.push(`Stock insuficiente. Disponible: ${stockDisponible}`);
      }
      break;
      
    case 'ajuste':
      if (stockDisponible !== null && cantidadNum < 0 && Math.abs(cantidadNum) > stockDisponible) {
        resultado.valido = false;
        resultado.errores.push(`Ajuste negativo excede stock. Disponible: ${stockDisponible}`);
      }
      break;
      
    default:
      resultado.advertencias.push(`Tipo de movimiento no reconocido: ${tipo}`);
  }
  
  return resultado;
}


/**
 * ISS-006: Hook para validación de cantidad con debounce.
 */
export function useValidarCantidad(tipo, stockDisponible = null) {
  const [cantidad, setCantidad] = useState('');
  const [validacion, setValidacion] = useState({ valido: true, errores: [], advertencias: [] });
  const timeoutRef = useRef(null);
  
  const validar = useCallback((valor) => {
    // Limpiar timeout anterior
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    
    // Debounce de 300ms
    timeoutRef.current = setTimeout(() => {
      if (valor === '' || valor === null) {
        setValidacion({ valido: true, errores: [], advertencias: [] });
        return;
      }
      
      const resultado = validarCantidadMovimiento(tipo, valor, stockDisponible);
      setValidacion(resultado);
    }, 300);
  }, [tipo, stockDisponible]);
  
  const handleChange = useCallback((valor) => {
    setCantidad(valor);
    validar(valor);
  }, [validar]);
  
  return {
    cantidad,
    setCantidad: handleChange,
    validacion,
    esValido: validacion.valido,
    errores: validacion.errores,
    advertencias: validacion.advertencias,
  };
}


export default {
  sessionManager,
  useSessionExpiration,
  usePolling,
  useRequisicionStatePolling,
  useNotificacionesPolling,
  validarCantidadMovimiento,
  useValidarCantidad,
};
