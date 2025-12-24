/**
 * Componente de indicador de estado de conexión
 * Se muestra discretamente cuando hay problemas de conexión con el servidor
 * 
 * Características:
 * - Aparece solo cuando hay problemas reales (después de reintentos silenciosos)
 * - Se oculta automáticamente cuando se recupera la conexión
 * - No es intrusivo - aparece en una esquina con animación suave
 * - Permite al usuario forzar una reconexión
 */

import { useState, useEffect, useCallback } from 'react';
import { FaWifi, FaExclamationTriangle, FaServer, FaSync, FaTimes } from 'react-icons/fa';
import { checkApiHealth } from '../services/api';

// Estados de conexión
const ConnectionState = {
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  DISCONNECTED: 'disconnected',
  SERVER_STARTING: 'server_starting',
};

function ConnectionIndicator() {
  const [state, setState] = useState(ConnectionState.CONNECTED);
  const [visible, setVisible] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);

  // Función para verificar la conexión
  const checkConnection = useCallback(async () => {
    setIsRetrying(true);
    try {
      const result = await checkApiHealth({ retries: 1 });
      if (result.healthy) {
        setState(ConnectionState.CONNECTED);
        setVisible(false);
        setDismissed(false);
        setRetryCount(0);
      } else if (result.isServerStarting) {
        setState(ConnectionState.SERVER_STARTING);
        setVisible(true);
      } else {
        setState(ConnectionState.DISCONNECTED);
        setVisible(true);
      }
    } catch {
      setState(ConnectionState.DISCONNECTED);
      setVisible(true);
    } finally {
      setIsRetrying(false);
    }
  }, []);

  // Escuchar eventos del interceptor de API
  useEffect(() => {
    const handleReconnecting = (event) => {
      setState(ConnectionState.RECONNECTING);
      setRetryCount(event.detail?.retryCount || 0);
      setVisible(true);
      setDismissed(false);
    };

    const handleConnectionLost = () => {
      setState(ConnectionState.DISCONNECTED);
      setVisible(true);
      setDismissed(false);
    };

    const handleConnectionRestored = () => {
      setState(ConnectionState.CONNECTED);
      // Mantener visible brevemente para mostrar que se reconectó
      setTimeout(() => {
        setVisible(false);
        setDismissed(false);
      }, 2000);
    };

    window.addEventListener('api-reconnecting', handleReconnecting);
    window.addEventListener('api-connection-lost', handleConnectionLost);
    window.addEventListener('api-connection-restored', handleConnectionRestored);

    return () => {
      window.removeEventListener('api-reconnecting', handleReconnecting);
      window.removeEventListener('api-connection-lost', handleConnectionLost);
      window.removeEventListener('api-connection-restored', handleConnectionRestored);
    };
  }, []);

  // Auto-retry cuando hay problemas
  useEffect(() => {
    if (state === ConnectionState.DISCONNECTED || state === ConnectionState.SERVER_STARTING) {
      const interval = setInterval(() => {
        if (!isRetrying) {
          checkConnection();
        }
      }, 30000); // Reintentar cada 30 segundos

      return () => clearInterval(interval);
    }
  }, [state, isRetrying, checkConnection]);

  // Escuchar eventos de red del navegador
  useEffect(() => {
    const handleOnline = () => {
      checkConnection();
    };

    const handleOffline = () => {
      setState(ConnectionState.DISCONNECTED);
      setVisible(true);
      setDismissed(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [checkConnection]);

  // No mostrar si está conectado, fue descartado, o no es visible
  if (!visible || dismissed || state === ConnectionState.CONNECTED) {
    return null;
  }

  // Configuración según el estado
  const config = {
    [ConnectionState.RECONNECTING]: {
      bgColor: 'bg-amber-500',
      icon: FaSync,
      iconClass: 'animate-spin',
      title: 'Reconectando...',
      message: retryCount > 0 ? `Intento ${retryCount}` : 'Estableciendo conexión',
      showRetry: false,
    },
    [ConnectionState.DISCONNECTED]: {
      bgColor: 'bg-red-500',
      icon: FaWifi,
      iconClass: '',
      title: 'Sin conexión',
      message: 'No se puede conectar al servidor',
      showRetry: true,
    },
    [ConnectionState.SERVER_STARTING]: {
      bgColor: 'bg-amber-500',
      icon: FaServer,
      iconClass: 'animate-pulse',
      title: 'Servidor iniciando',
      message: 'Esto puede tomar hasta 60 segundos',
      showRetry: true,
    },
  };

  const currentConfig = config[state] || config[ConnectionState.DISCONNECTED];
  const Icon = currentConfig.icon;

  return (
    <div 
      className={`fixed bottom-4 right-4 z-50 ${currentConfig.bgColor} text-white rounded-lg shadow-lg 
        transform transition-all duration-300 ease-out
        ${visible ? 'translate-y-0 opacity-100' : 'translate-y-full opacity-0'}`}
      style={{ maxWidth: '320px' }}
    >
      <div className="p-3">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-0.5">
            <Icon className={`text-lg ${currentConfig.iconClass}`} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-sm">{currentConfig.title}</p>
            <p className="text-xs opacity-90">{currentConfig.message}</p>
          </div>
          <button
            onClick={() => setDismissed(true)}
            className="flex-shrink-0 opacity-70 hover:opacity-100 transition-opacity"
            title="Cerrar"
          >
            <FaTimes className="text-sm" />
          </button>
        </div>
        
        {currentConfig.showRetry && (
          <button
            onClick={checkConnection}
            disabled={isRetrying}
            className="mt-2 w-full py-1.5 px-3 bg-white/20 hover:bg-white/30 rounded text-xs font-medium 
              transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <FaSync className={isRetrying ? 'animate-spin' : ''} />
            {isRetrying ? 'Verificando...' : 'Reintentar ahora'}
          </button>
        )}
      </div>
    </div>
  );
}

export default ConnectionIndicator;
