import React from "react";
import { getApiConfigError, isHttpInsecure } from '../services/api';

/**
 * ISS-002 FIX: Error Boundary mejorado para capturar errores de renderizado en React
 * 
 * Proporciona manejo de errores a nivel de ruta con:
 * - Captura de errores de renderizado
 * - Manejo de errores de configuración de API
 * - Detección de pérdida de sesión (401)
 * - UI amigable con opción de reintentar
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null, 
      errorInfo: null,
      errorType: 'unknown' // 'config' | 'auth' | 'network' | 'render' | 'unknown'
    };
  }

  static getDerivedStateFromError(error) {
    // Clasificar el tipo de error
    let errorType = 'render';
    
    if (error.name === 'ApiConfigurationError' || error.isConfigError) {
      errorType = 'config';
    } else if (error.response?.status === 401 || error.message?.includes('401') || error.message?.includes('Unauthorized')) {
      errorType = 'auth';
    } else if (error.message?.includes('Network') || error.message?.includes('fetch') || error.code === 'ERR_NETWORK') {
      errorType = 'network';
    }
    
    return { hasError: true, errorType };
  }

  componentDidCatch(error, errorInfo) {
    // Log del error para debugging
    console.error("[ErrorBoundary] Error capturado:", error, errorInfo);
    console.error("[ErrorBoundary] Tipo:", this.state.errorType);
    this.setState({
      error: error,
      errorInfo: errorInfo,
    });

    // Aquí podrías enviar el error a un servicio de monitoreo
    // como Sentry, LogRocket, etc.
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null, errorInfo: null, errorType: 'unknown' });
    window.location.reload();
  };

  handleGoHome = () => {
    this.setState({ hasError: false, error: null, errorInfo: null, errorType: 'unknown' });
    window.location.href = "/dashboard";
  };

  handleLogout = () => {
    // Limpiar tokens y redirigir al login
    localStorage.removeItem('user');
    window.location.href = '/login';
  };

  renderConfigError() {
    const configError = getApiConfigError();
    const isInsecure = isHttpInsecure();
    
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl p-8 max-w-lg w-full text-center">
          <div className="mx-auto w-16 h-16 flex items-center justify-center rounded-full bg-red-100 mb-4">
            <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">
            {isInsecure ? 'Error de Seguridad' : 'Error de Configuración'}
          </h1>
          <p className="text-gray-600 mb-4">{configError || this.state.error?.message}</p>
          <div className="bg-gray-50 rounded p-4 text-left text-sm mb-4">
            <p className="font-medium text-gray-700 mb-2">Información técnica:</p>
            <ul className="list-disc list-inside text-gray-600 space-y-1">
              <li>Código: {isInsecure ? 'HTTPS_REQUIRED' : 'CONFIG_MISSING'}</li>
              <li>Verifique las variables de entorno</li>
              <li>Contacte al administrador del sistema</li>
            </ul>
          </div>
          <button
            onClick={this.handleReload}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  renderAuthError() {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full text-center">
          <div className="mx-auto w-16 h-16 flex items-center justify-center rounded-full bg-yellow-100 mb-4">
            <svg className="w-8 h-8 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">Sesión Expirada</h1>
          <p className="text-gray-600 mb-6">
            Tu sesión ha expirado o no tienes permisos para acceder a este recurso.
            Por favor, inicia sesión nuevamente.
          </p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={this.handleLogout}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium"
            >
              Iniciar Sesión
            </button>
            <button
              onClick={this.handleGoHome}
              className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition font-medium"
            >
              Ir al Inicio
            </button>
          </div>
        </div>
      </div>
    );
  }

  renderNetworkError() {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full text-center">
          <div className="mx-auto w-16 h-16 flex items-center justify-center rounded-full bg-orange-100 mb-4">
            <svg className="w-8 h-8 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">Error de Conexión</h1>
          <p className="text-gray-600 mb-6">
            No se pudo conectar con el servidor. Verifica tu conexión a internet
            o intenta nuevamente en unos momentos.
          </p>
          <button
            onClick={this.handleReload}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  };

  render() {
    if (this.state.hasError) {
      // Renderizar UI según tipo de error
      switch (this.state.errorType) {
        case 'config':
          return this.renderConfigError();
        case 'auth':
          return this.renderAuthError();
        case 'network':
          return this.renderNetworkError();
        default:
          // UI de fallback genérica
          return (
            <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
              <div className="bg-white rounded-lg shadow-xl p-8 max-w-lg w-full text-center">
                <div className="mb-6">
                  <svg
                    className="mx-auto h-16 w-16 text-red-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </div>

                <h1 className="text-2xl font-bold text-gray-800 mb-2">
                  ¡Algo salió mal!
                </h1>

                <p className="text-gray-600 mb-6">
                  Ha ocurrido un error inesperado. El equipo técnico ha sido
                  notificado.
                </p>

                {/* Mostrar detalles solo en desarrollo */}
                {import.meta.env.DEV && this.state.error && (
                  <details className="mb-6 text-left">
                    <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-700">
                      Ver detalles técnicos
                    </summary>
                    <div className="mt-2 p-3 bg-gray-100 rounded text-xs font-mono overflow-auto max-h-40">
                      <p className="text-red-600 font-semibold">
                        {this.state.error.toString()}
                      </p>
                      <pre className="mt-2 text-gray-600 whitespace-pre-wrap">
                        {this.state.errorInfo?.componentStack}
                      </pre>
                    </div>
                  </details>
                )}

                <div className="flex gap-3 justify-center">
                  <button
                    onClick={this.handleReload}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium"
                  >
                    Recargar página
                  </button>
                  <button
                    onClick={this.handleGoHome}
                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition font-medium"
                  >
                    Ir al inicio
                  </button>
                </div>

                <p className="mt-6 text-xs text-gray-400">
                  Si el problema persiste, contacta a soporte técnico.
                </p>
              </div>
            </div>
          );
      }
    }

    return this.props.children;
  }
}

/**
 * HOC para envolver componentes con Error Boundary
 * @param {React.Component} WrappedComponent - Componente a envolver
 * @param {React.ReactNode} fallback - UI alternativa opcional
 */
export const withErrorBoundary = (WrappedComponent, fallback = null) => {
  const WithErrorBoundary = (props) => (
    <ErrorBoundary fallback={fallback}>
      <WrappedComponent {...props} />
    </ErrorBoundary>
  );
  
  WithErrorBoundary.displayName = `WithErrorBoundary(${WrappedComponent.displayName || WrappedComponent.name || 'Component'})`;
  
  return WithErrorBoundary;
};

export default ErrorBoundary;
