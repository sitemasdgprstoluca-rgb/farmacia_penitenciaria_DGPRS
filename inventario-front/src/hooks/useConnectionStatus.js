/**
 * Hook para monitorear el estado de conexión con el servidor
 * y proporcionar reconexión automática silenciosa
 * 
 * Diseñado para manejar:
 * - Cold starts de Render (servidor dormido)
 * - Desconexiones temporales de red
 * - Errores intermitentes del servidor
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { checkApiHealth } from '../services/api';

// Configuración de reconexión
const CONFIG = {
  // Intervalo entre verificaciones cuando todo está bien (5 minutos)
  HEALTH_CHECK_INTERVAL: 5 * 60 * 1000,
  // Intervalo cuando hay problemas (30 segundos)
  RECONNECT_INTERVAL: 30 * 1000,
  // ISS-FIX: Intervalo más largo durante cold starts para evitar spam (15 segundos)
  FAST_RECONNECT_INTERVAL: 15 * 1000,
  // Máximo de reintentos antes de mostrar error persistente
  MAX_SILENT_RETRIES: 3,
  // Tiempo antes de considerar que la conexión es estable (2 minutos sin errores)
  STABILITY_THRESHOLD: 2 * 60 * 1000,
};

// Estados posibles de la conexión
export const ConnectionState = {
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  DISCONNECTED: 'disconnected',
  SERVER_STARTING: 'server_starting',
  UNKNOWN: 'unknown',
};

/**
 * Hook para monitorear y manejar el estado de conexión
 * @param {Object} options - Opciones de configuración
 * @param {boolean} options.enabled - Si el monitoreo está habilitado (default: true)
 * @param {boolean} options.showNotifications - Si mostrar notificaciones al usuario (default: false para ser silencioso)
 */
export function useConnectionStatus(options = {}) {
  const { 
    enabled = true, 
    showNotifications = false,
  } = options;

  const [state, setState] = useState(ConnectionState.UNKNOWN);
  const [lastError, setLastError] = useState(null);
  const [isServerStarting, setIsServerStarting] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [lastSuccessfulConnection, setLastSuccessfulConnection] = useState(null);
  
  const checkIntervalRef = useRef(null);
  const mountedRef = useRef(true);
  const consecutiveFailuresRef = useRef(0);

  /**
   * Verifica la conexión con el servidor
   * @param {boolean} silent - Si es true, no actualiza el estado visible durante la verificación
   */
  const checkConnection = useCallback(async (silent = true) => {
    if (!enabled || !mountedRef.current) return;

    try {
      const result = await checkApiHealth({ retries: 1 });
      
      if (!mountedRef.current) return;

      if (result.healthy) {
        // Conexión exitosa
        consecutiveFailuresRef.current = 0;
        setLastSuccessfulConnection(Date.now());
        setLastError(null);
        setIsServerStarting(false);
        setRetryCount(0);
        
        // Solo actualizar estado si cambió (evitar re-renders innecesarios)
        setState(prev => prev !== ConnectionState.CONNECTED ? ConnectionState.CONNECTED : prev);
        
        return true;
      } else if (result.isServerStarting) {
        // Servidor está despertando
        setIsServerStarting(true);
        setState(ConnectionState.SERVER_STARTING);
        setLastError('El servidor está iniciando...');
        return false;
      } else {
        // Otros errores
        throw new Error(result.error || 'Error de conexión');
      }
    } catch (error) {
      if (!mountedRef.current) return;
      
      consecutiveFailuresRef.current++;
      setLastError(error.message);
      setRetryCount(prev => prev + 1);
      
      // Determinar el estado basado en el error
      if (error.message?.includes('iniciando') || error.code === 'ECONNABORTED') {
        setIsServerStarting(true);
        setState(ConnectionState.SERVER_STARTING);
      } else if (consecutiveFailuresRef.current <= CONFIG.MAX_SILENT_RETRIES) {
        // Aún en modo silencioso de reconexión
        setState(ConnectionState.RECONNECTING);
      } else {
        // Demasiados fallos, marcar como desconectado
        setState(ConnectionState.DISCONNECTED);
      }
      
      return false;
    }
  }, [enabled]);

  /**
   * Forzar una reconexión manual
   */
  const forceReconnect = useCallback(async () => {
    setState(ConnectionState.RECONNECTING);
    consecutiveFailuresRef.current = 0;
    setRetryCount(0);
    
    const success = await checkConnection(false);
    
    if (!success) {
      // Programar reintentos más frecuentes
      if (checkIntervalRef.current) {
        clearInterval(checkIntervalRef.current);
      }
      checkIntervalRef.current = setInterval(
        () => checkConnection(true),
        CONFIG.FAST_RECONNECT_INTERVAL
      );
    }
    
    return success;
  }, [checkConnection]);

  /**
   * Resetear el estado de error (para casos donde el usuario quiere ignorar)
   */
  const dismissError = useCallback(() => {
    setLastError(null);
    if (state === ConnectionState.DISCONNECTED) {
      setState(ConnectionState.RECONNECTING);
    }
  }, [state]);

  // Efecto principal: configurar el monitoreo
  useEffect(() => {
    if (!enabled) return;
    
    mountedRef.current = true;
    
    // Verificación inicial
    checkConnection(false);
    
    // Configurar intervalo de verificación
    checkIntervalRef.current = setInterval(
      () => checkConnection(true),
      CONFIG.HEALTH_CHECK_INTERVAL
    );
    
    return () => {
      mountedRef.current = false;
      if (checkIntervalRef.current) {
        clearInterval(checkIntervalRef.current);
      }
    };
  }, [enabled, checkConnection]);

  // Efecto: ajustar intervalo basado en el estado
  useEffect(() => {
    if (!enabled || !mountedRef.current) return;
    
    // Si estamos reconectando o desconectados, verificar más seguido
    if (state === ConnectionState.RECONNECTING || 
        state === ConnectionState.DISCONNECTED ||
        state === ConnectionState.SERVER_STARTING) {
      
      if (checkIntervalRef.current) {
        clearInterval(checkIntervalRef.current);
      }
      
      const interval = state === ConnectionState.SERVER_STARTING 
        ? CONFIG.FAST_RECONNECT_INTERVAL 
        : CONFIG.RECONNECT_INTERVAL;
      
      checkIntervalRef.current = setInterval(
        () => checkConnection(true),
        interval
      );
    } else if (state === ConnectionState.CONNECTED) {
      // Volver al intervalo normal cuando se reconecta
      if (checkIntervalRef.current) {
        clearInterval(checkIntervalRef.current);
      }
      checkIntervalRef.current = setInterval(
        () => checkConnection(true),
        CONFIG.HEALTH_CHECK_INTERVAL
      );
    }
  }, [state, enabled, checkConnection]);

  // Escuchar eventos de red del navegador
  useEffect(() => {
    if (!enabled) return;

    const handleOnline = () => {
      // ISS-FIX: Silencioso - solo en desarrollo
      if (import.meta.env.DEV) {
        console.debug('[Connection] Navegador reporta conexión online');
      }
      forceReconnect();
    };

    const handleOffline = () => {
      // ISS-FIX: Silencioso - solo en desarrollo
      if (import.meta.env.DEV) {
        console.debug('[Connection] Navegador reporta conexión offline');
      }
      setState(ConnectionState.DISCONNECTED);
      setLastError('Sin conexión a internet');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [enabled, forceReconnect]);

  return {
    // Estado actual de la conexión
    state,
    isConnected: state === ConnectionState.CONNECTED,
    isReconnecting: state === ConnectionState.RECONNECTING,
    isDisconnected: state === ConnectionState.DISCONNECTED,
    isServerStarting: state === ConnectionState.SERVER_STARTING || isServerStarting,
    
    // Información adicional
    lastError,
    retryCount,
    lastSuccessfulConnection,
    
    // Acciones
    forceReconnect,
    dismissError,
    checkConnection,
  };
}

export default useConnectionStatus;
