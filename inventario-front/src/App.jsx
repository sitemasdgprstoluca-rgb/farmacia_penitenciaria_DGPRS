// filepath: inventario-front/src/App.jsx
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { Suspense, lazy, useEffect, useState, createContext, useContext } from 'react';
import { PermissionProvider } from './context/PermissionContext';
import { ThemeProvider } from './context/ThemeContext';
import { ModalStackProvider } from './contexts/ModalStackContext';
import { usePermissions } from './hooks/usePermissions';
import { useInactivityLogout } from './hooks/useInactivityLogout';
import PermissionsGuard from './components/PermissionsGuard';
import ErrorBoundary from './components/ErrorBoundary';
import { 
  getApiConfigError, 
  hasHttpWarning, 
  wasHealthCheckSkipped, 
  checkApiHealth, 
  isApiHealthy,
  hasEnvErrors,
  getEnvErrors,
  getEnvWarnings,
} from './services/api';

// ═══════════════════════════════════════════════════════════════════════════════
// ISS-001 FIX (audit32): Contexto de estado de salud para bloquear navegación
// ═══════════════════════════════════════════════════════════════════════════════
const HealthContext = createContext({
  healthy: true,
  checked: false,
  error: null,
});

// Rutas críticas que requieren API saludable para operar
const RUTAS_CRITICAS = [
  '/productos',
  '/lotes', 
  '/requisiciones',
  '/movimientos',
  '/donaciones',
  '/pacientes',
  '/dispensaciones',
];

// Rutas permitidas aunque el API no esté saludable
const RUTAS_PERMITIDAS_DEGRADADO = [
  '/dashboard',
  '/perfil',
  '/configuracion-tema',
  '/notificaciones',
];

// ═══════════════════════════════════════════════════════════════════════════════
// LAZY LOADING - Mejora el tiempo de carga inicial dividiendo el bundle
// ═══════════════════════════════════════════════════════════════════════════════
// Componentes críticos (cargan inmediatamente)
import Layout from './components/Layout';
import Login from './pages/Login';

// Componentes diferidos (cargan bajo demanda)
const RecuperarPassword = lazy(() => import('./pages/RecuperarPassword'));
const RestablecerPassword = lazy(() => import('./pages/RestablecerPassword'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Productos = lazy(() => import('./pages/Productos'));
const Lotes = lazy(() => import('./pages/Lotes'));
const Requisiciones = lazy(() => import('./pages/Requisiciones'));
const RequisicionDetalle = lazy(() => import('./pages/RequisicionDetalle'));
const Centros = lazy(() => import('./pages/Centros'));
const Usuarios = lazy(() => import('./pages/Usuarios'));
const Reportes = lazy(() => import('./pages/Reportes'));
const Trazabilidad = lazy(() => import('./pages/Trazabilidad'));
const Movimientos = lazy(() => import('./pages/Movimientos'));
const Notificaciones = lazy(() => import('./pages/Notificaciones'));
const Perfil = lazy(() => import('./pages/Perfil'));
const ConfiguracionTema = lazy(() => import('./pages/ConfiguracionTema'));
const Donaciones = lazy(() => import('./pages/Donaciones'));
const Pacientes = lazy(() => import('./pages/Pacientes'));
const Dispensaciones = lazy(() => import('./pages/Dispensaciones'));
const ComprasCajaChica = lazy(() => import('./pages/ComprasCajaChica'));
const InventarioCajaChica = lazy(() => import('./pages/InventarioCajaChica'));
const Auditoria = lazy(() => import('./pages/Auditoria'));
const NotFound = lazy(() => import('./pages/NotFound'));
const ServerError = lazy(() => import('./pages/ServerError'));

// Componente de carga para Suspense - usa variable CSS del tema para fondo
const PageLoader = () => (
  <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--color-background, #F5F5F5)' }}>
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-4 spinner-institucional mx-auto"></div>
      <p className="mt-4 text-gray-600">Cargando...</p>
    </div>
  </div>
);

// ISS-002/ISS-004: Banner de advertencia para HTTP inseguro en staging/testing
const HttpWarningBanner = () => (
  <div className="fixed top-0 left-0 right-0 z-50 bg-yellow-500 text-yellow-900 px-4 py-2 text-center text-sm font-medium shadow-lg">
    <span className="inline-flex items-center gap-2">
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      ⚠️ CONEXIÓN NO SEGURA: Esta sesión usa HTTP sin cifrado. Los datos pueden estar expuestos. Solo para entornos de prueba.
    </span>
  </div>
);

/**
 * ISS-005 FIX: Banner de healthcheck omitido o degradado
 * Muestra advertencia sutil cuando no se verificó compatibilidad con backend
 * Ahora es más discreto - aparece como un pequeño indicador en esquina
 */
const HealthCheckWarningBanner = ({ reason, onDismiss, onRetry }) => (
  <div className="fixed bottom-4 left-4 z-40 max-w-xs bg-amber-50 border border-amber-200 rounded-lg shadow-lg overflow-hidden">
    <div className="p-3">
      <div className="flex items-start gap-2">
        <span className="text-lg flex-shrink-0">🔌</span>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-amber-800">
            Modo degradado
          </p>
          <p className="text-xs text-amber-700 mt-0.5">
            {reason || 'Verificación de servidor omitida'}
          </p>
        </div>
        <button
          onClick={onDismiss}
          className="flex-shrink-0 text-amber-400 hover:text-amber-600"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div className="mt-2 flex gap-2">
        <button
          onClick={onRetry}
          className="flex-1 px-2 py-1 text-xs font-medium rounded bg-amber-200 text-amber-800 hover:bg-amber-300 transition-colors"
        >
          Verificar
        </button>
        <button
          onClick={onDismiss}
          className="flex-1 px-2 py-1 text-xs font-medium rounded bg-gray-200 text-gray-600 hover:bg-gray-300 transition-colors"
        >
          Ignorar
        </button>
      </div>
    </div>
  </div>
);

/**
 * ISS-005 FIX: Banner de API no saludable
 * Muestra error cuando el healthcheck falló
 * ISS-FIX: Mejorado para mostrar mensaje amigable en cold starts
 * Ahora incluye barra de progreso animada y es más discreto
 */
const ApiUnhealthyBanner = ({ error, onRetry, isServerStarting, onDismiss }) => {
  const [progress, setProgress] = useState(0);
  const [dismissed, setDismissed] = useState(false);

  // Animar progreso cuando el servidor está iniciando
  useEffect(() => {
    if (isServerStarting) {
      const interval = setInterval(() => {
        setProgress(prev => Math.min(prev + Math.random() * 10, 95));
      }, 1000);
      return () => clearInterval(interval);
    } else {
      setProgress(0);
    }
  }, [isServerStarting]);

  if (dismissed) return null;

  return (
    <div className={`fixed bottom-4 right-4 z-40 max-w-sm rounded-lg shadow-xl overflow-hidden 
      ${isServerStarting ? 'bg-amber-50 border border-amber-200' : 'bg-red-50 border border-red-200'}`}
    >
      <div className="p-4">
        <div className="flex items-start gap-3">
          <span className="text-xl flex-shrink-0">{isServerStarting ? '⏳' : '⚠️'}</span>
          <div className="flex-1 min-w-0">
            <p className={`text-sm font-medium ${isServerStarting ? 'text-amber-800' : 'text-red-800'}`}>
              {isServerStarting ? 'Servidor iniciando...' : 'Conexión inestable'}
            </p>
            <p className={`text-xs mt-1 ${isServerStarting ? 'text-amber-700' : 'text-red-700'}`}>
              {isServerStarting 
                ? 'El servidor gratuito está despertando. Esto puede tomar hasta 60 segundos.'
                : error || 'Verificando conexión con el servidor...'}
            </p>
          </div>
          <button
            onClick={() => { setDismissed(true); onDismiss?.(); }}
            className="flex-shrink-0 text-gray-400 hover:text-gray-600"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        {/* Barra de progreso para servidor iniciando */}
        {isServerStarting && (
          <div className="mt-3 w-full bg-amber-200 rounded-full h-1.5 overflow-hidden">
            <div 
              className="bg-amber-500 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
        
        <button
          onClick={onRetry}
          className={`mt-3 w-full py-2 text-xs font-medium rounded-lg transition-colors flex items-center justify-center gap-2
            ${isServerStarting 
              ? 'bg-amber-200 text-amber-800 hover:bg-amber-300' 
              : 'bg-red-200 text-red-800 hover:bg-red-300'}`}
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Reintentar conexión
        </button>
      </div>
    </div>
  );
};

// Componente de error de configuración (ISS-001)
// ISS-001 FIX (audit33): Bloquea render completo con instrucciones claras y enlace a documentación
const ConfigErrorPage = ({ error, errors = [], warnings = [] }) => (
  <div className="min-h-screen flex items-center justify-center bg-gray-100">
    <div className="max-w-lg w-full mx-4 bg-white rounded-lg shadow-xl p-8 text-center">
      <div className="mx-auto w-16 h-16 flex items-center justify-center rounded-full bg-red-100 mb-4">
        <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Error de Configuración</h1>
      <p className="text-gray-600 mb-4">{error}</p>
      
      {/* ISS-001: Mostrar errores detallados con acciones */}
      {errors.length > 0 && (
        <div className="bg-red-50 rounded-lg p-4 mb-4 text-left">
          <p className="font-medium text-red-800 mb-2">Errores de configuración:</p>
          {errors.map((err, idx) => (
            <div key={idx} className="mb-2 text-sm">
              <code className="bg-red-200 px-1 rounded text-red-900">{err.variable}</code>
              <p className="text-red-700 ml-2">{err.mensaje}</p>
              <p className="text-red-600 ml-2 text-xs italic">→ {err.accion}</p>
            </div>
          ))}
        </div>
      )}
      
      {/* ISS-001: Mostrar advertencias */}
      {warnings.length > 0 && (
        <div className="bg-yellow-50 rounded-lg p-4 mb-4 text-left">
          <p className="font-medium text-yellow-800 mb-2">Advertencias:</p>
          {warnings.map((warn, idx) => (
            <div key={idx} className="mb-2 text-sm">
              <code className="bg-yellow-200 px-1 rounded text-yellow-900">{warn.variable}</code>
              <p className="text-yellow-700 ml-2">{warn.mensaje}</p>
            </div>
          ))}
        </div>
      )}
      
      <div className="bg-gray-50 rounded p-4 text-left text-sm">
        <p className="font-medium text-gray-700 mb-2">Para resolver este problema:</p>
        <ol className="list-decimal list-inside text-gray-600 space-y-1">
          <li>Verifique que el archivo <code className="bg-gray-200 px-1 rounded">.env</code> existe</li>
          <li>Asegúrese de que <code className="bg-gray-200 px-1 rounded">VITE_API_URL</code> está configurado</li>
          <li>Reconstruya la aplicación después de los cambios</li>
        </ol>
      </div>
      
      {/* ISS-001: Enlace a documentación de despliegue */}
      <div className="mt-4 text-sm">
        <a 
          href="https://github.com/zaragozaalexander124-uzumaki/farmacia_penitenciaria#configuracion"
          target="_blank"
          rel="noopener noreferrer"
          className="text-guinda-600 hover:text-guinda-800 underline"
        >
          📖 Ver documentación de configuración
        </a>
      </div>
      
      <p className="text-xs text-gray-400 mt-4">SIFP - Sistema de Inventario de Farmacia Penitenciaria</p>
    </div>
  </div>
);

function SessionManager() {
  useInactivityLogout();
  return null;
}

/**
 * ISS-001 FIX (audit32): Componente de bloqueo cuando API no está saludable
 * Muestra mensaje explicativo y opciones de acción
 */
const ApiBlockedPage = ({ error, onRetry }) => {
  const location = useLocation();
  
  return (
    <div className="min-h-[80vh] flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-xl p-8 text-center border border-red-200">
        <div className="mx-auto w-16 h-16 flex items-center justify-center rounded-full bg-red-100 mb-4">
          <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636l-12.728 12.728M5.636 5.636l12.728 12.728" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">
          Módulo No Disponible
        </h2>
        <p className="text-gray-600 mb-4 text-sm">
          La conexión con el servidor no está estable. Por seguridad, el acceso a 
          <strong className="text-red-700"> {location.pathname}</strong> está temporalmente bloqueado 
          para evitar inconsistencias de datos.
        </p>
        {error && (
          <div className="bg-red-50 rounded-lg p-3 mb-4 text-left">
            <p className="text-xs text-red-700 font-mono">{error}</p>
          </div>
        )}
        <div className="flex flex-col gap-2">
          <button
            onClick={onRetry}
            className="w-full px-4 py-2 bg-guinda-600 text-white rounded-lg hover:bg-guinda-700 transition-colors font-medium"
          >
            🔄 Reintentar conexión
          </button>
          <button
            onClick={() => window.location.href = '/dashboard'}
            className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
          >
            Ir al Dashboard
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-4">
          Si el problema persiste, contacte al administrador del sistema.
        </p>
      </div>
    </div>
  );
};

/**
 * ISS-002 FIX + ISS-001 FIX (audit32): ProtectedRoute mejorado
 * ISS-002 FIX (audit33): Timeout de carga, manejo de errores, sincronización con refresh
 * - Bloquea render hasta que el estado de autenticación esté resuelto
 * - ISS-001: Bloquea acceso a rutas críticas cuando API no está saludable
 * - ISS-002: Timeout de carga para evitar spinner infinito
 */
const PERMISSION_LOAD_TIMEOUT = 15000; // 15 segundos máximo

function ProtectedRoute({ children }) {
  const { user, loading, error, recargarUsuario } = usePermissions();
  const healthState = useContext(HealthContext);
  const location = useLocation();
  const [isReady, setIsReady] = useState(false);
  const [loadTimeout, setLoadTimeout] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  // ISS-002 (audit33): Timeout para evitar spinner infinito
  useEffect(() => {
    if (loading) {
      const timeoutId = setTimeout(() => {
        console.warn('[ProtectedRoute] Timeout cargando permisos');
        setLoadTimeout(true);
      }, PERMISSION_LOAD_TIMEOUT);
      
      return () => clearTimeout(timeoutId);
    } else {
      setLoadTimeout(false);
    }
  }, [loading]);

  // ISS-002: Esperar hasta que loading termine para evitar race conditions
  useEffect(() => {
    if (!loading) {
      // Pequeño delay para asegurar que el estado se ha propagado
      const timer = setTimeout(() => setIsReady(true), 50);
      return () => clearTimeout(timer);
    }
  }, [loading]);

  // ISS-002 (audit33): Manejar timeout con opción de reintento
  if (loadTimeout && loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="max-w-md w-full mx-4 bg-white rounded-lg shadow-lg p-8 text-center">
          <div className="mx-auto w-16 h-16 flex items-center justify-center rounded-full bg-yellow-100 mb-4">
            <svg className="w-8 h-8 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Carga lenta</h2>
          <p className="text-gray-600 mb-4 text-sm">
            La verificación de permisos está tardando más de lo esperado. 
            Esto puede deberse a problemas de conexión.
          </p>
          <div className="flex gap-2 justify-center">
            <button
              onClick={() => {
                setLoadTimeout(false);
                setRetryCount(prev => prev + 1);
                if (typeof recargarUsuario === 'function') {
                  recargarUsuario();
                }
              }}
              className="px-4 py-2 bg-guinda-600 text-white rounded-lg hover:bg-guinda-700 transition-colors"
            >
              🔄 Reintentar
            </button>
            <button
              onClick={() => window.location.href = '/login'}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Ir al Login
            </button>
          </div>
          {retryCount > 0 && (
            <p className="text-xs text-gray-400 mt-4">Reintentos: {retryCount}</p>
          )}
        </div>
      </div>
    );
  }

  // ISS-002 (audit33): Manejar estado de error de permisos
  if (error && !loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="max-w-md w-full mx-4 bg-white rounded-lg shadow-lg p-8 text-center">
          <div className="mx-auto w-16 h-16 flex items-center justify-center rounded-full bg-red-100 mb-4">
            <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Error de permisos</h2>
          <p className="text-gray-600 mb-4 text-sm">{error || 'No se pudieron cargar los permisos.'}</p>
          <div className="flex gap-2 justify-center">
            <button
              onClick={() => {
                if (typeof recargarUsuario === 'function') {
                  recargarUsuario();
                } else {
                  window.location.reload();
                }
              }}
              className="px-4 py-2 bg-guinda-600 text-white rounded-lg hover:bg-guinda-700 transition-colors"
            >
              🔄 Reintentar
            </button>
            <button
              onClick={() => window.location.href = '/login'}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Iniciar sesión
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Mostrar spinner mientras carga o aún no está listo
  if (loading || !isReady) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--color-background, #F5F5F5)' }}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 spinner-institucional mx-auto"></div>
          <p className="mt-4 text-gray-500 text-sm">Verificando permisos...</p>
        </div>
      </div>
    );
  }

  // Si no hay usuario, redirigir al login
  if (!user) return <Navigate to="/login" replace />;

  // ISS-002: Envolver en ErrorBoundary para capturar errores de componentes hijos
  return <ErrorBoundary>{children}</ErrorBoundary>;
}

/**
 * ISS-001 FIX (audit32): Guardia de rutas críticas por estado de salud
 * Bloquea acceso a módulos que manipulan datos cuando API no está saludable
 */
function CriticalRouteGuard({ children }) {
  const healthState = useContext(HealthContext);
  const location = useLocation();
  
  // Verificar si la ruta actual es crítica
  const esRutaCritica = RUTAS_CRITICAS.some(ruta => 
    location.pathname.startsWith(ruta)
  );
  
  // Si el healthcheck no se ha completado, permitir (se bloqueará después si falla)
  if (!healthState.checked) {
    return children;
  }
  
  // ISS-001: Si el API no está saludable y es ruta crítica, bloquear
  if (!healthState.healthy && esRutaCritica) {
    return (
      <ApiBlockedPage 
        error={healthState.error}
        onRetry={healthState.onRetry}
      />
    );
  }
  
  return children;
}

function App() {
  // ISS-001 FIX (audit33): Verificar TODAS las configuraciones de API antes de renderizar
  // BLOQUEO COMPLETO: Si hay errores de configuración, NO montar el router
  const configError = getApiConfigError();
  const envErrors = getEnvErrors();
  const envWarnings = getEnvWarnings();
  
  if (configError || hasEnvErrors()) {
    // ISS-001: Bloquear render completo, incluyendo router
    return (
      <ConfigErrorPage 
        error={configError || 'Hay errores de configuración que impiden iniciar la aplicación'} 
        errors={envErrors}
        warnings={envWarnings}
      />
    );
  }

  // ISS-002/ISS-004: Verificar si hay advertencia de HTTP inseguro
  const showHttpWarning = hasHttpWarning();
  
  // ISS-005 FIX: Estado para healthcheck
  const [healthState, setHealthState] = useState({
    checked: false,
    healthy: null,
    skipped: false,
    error: null,
    reason: null,
    dismissed: false,
    isServerStarting: false,
  });
  
  // ISS-005: Verificar healthcheck al montar
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const result = await checkApiHealth();
        setHealthState({
          checked: true,
          healthy: result.healthy,
          skipped: result.skipped || false,
          error: result.error || null,
          reason: result.mode === 'auth-only' 
            ? 'Modo de autenticación únicamente - verificación de compatibilidad deshabilitada'
            : result.mode === 'degraded'
              ? 'El servidor no tiene endpoint de salud - funcionando en modo degradado'
              : null,
          dismissed: false,
          isServerStarting: result.isServerStarting || false,
        });
      } catch (err) {
        setHealthState({
          checked: true,
          healthy: false,
          skipped: false,
          error: err.message || 'Error desconocido al verificar conexión',
          reason: null,
          dismissed: false,
          isServerStarting: false,
        });
      }
    };
    
    checkHealth();
  }, []);
  
  // ISS-005: Handler para reintentar healthcheck
  const handleRetryHealthCheck = async () => {
    setHealthState(prev => ({ ...prev, checked: false, isServerStarting: false }));
    try {
      const result = await checkApiHealth({ force: true });
      setHealthState({
        checked: true,
        healthy: result.healthy,
        skipped: result.skipped || false,
        error: result.error || null,
        reason: result.reason || null,
        dismissed: false,
        isServerStarting: result.isServerStarting || false,
      });
    } catch (err) {
      setHealthState(prev => ({
        ...prev,
        checked: true,
        healthy: false,
        error: err.message,
        isServerStarting: false,
      }));
    }
  };
  
  // ISS-005: Handler para descartar advertencia
  const handleDismissHealthWarning = () => {
    setHealthState(prev => ({ ...prev, dismissed: true }));
  };
  
  // Determinar qué banner de health mostrar
  const showHealthSkippedBanner = healthState.checked && healthState.skipped && !healthState.dismissed;
  const showHealthErrorBanner = healthState.checked && !healthState.healthy && !healthState.skipped;

  // ISS-001 FIX (audit32): Valor del contexto de health para rutas críticas
  const healthContextValue = {
    ...healthState,
    onRetry: handleRetryHealthCheck,
  };

  return (
    <Router>
      <ModalStackProvider>
        <HealthContext.Provider value={healthContextValue}>
        <PermissionProvider>
          <ThemeProvider>
          {showHttpWarning && <HttpWarningBanner />}
          {/* ISS-005 FIX: Banners de healthcheck */}
          {showHealthSkippedBanner && (
            <HealthCheckWarningBanner 
              reason={healthState.reason}
              onDismiss={handleDismissHealthWarning}
              onRetry={handleRetryHealthCheck}
            />
          )}
          {showHealthErrorBanner && (
            <ApiUnhealthyBanner 
              error={healthState.error}
              onRetry={handleRetryHealthCheck}
              isServerStarting={healthState.isServerStarting}
            />
          )}
          <SessionManager />
          <Toaster 
            position="top-center"
            containerStyle={{
              top: 80, // Debajo del header (h-16 = 64px + margen)
            }}
            toastOptions={{
              // Estilos base para todos los toasts
              style: {
                maxWidth: '400px',
              },
              // Los toasts con duration: Infinity mostrarán botón de cerrar
              success: {
                duration: 4000,
              },
              error: {
                duration: 5000,
              },
            }}
          />
        
          <Suspense fallback={<PageLoader />}>
          <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/recuperar-password" element={<RecuperarPassword />} />
          <Route path="/restablecer-password" element={<RestablecerPassword />} />
          {/* Alias para compatibilidad con enlaces antiguos */}
          <Route path="/reset-password" element={<RestablecerPassword />} />
          
          <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={
              <PermissionsGuard requiredPermission="verDashboard">
                <Dashboard />
              </PermissionsGuard>
            } />
            {/* ISS-001 FIX (audit32): Rutas críticas protegidas por CriticalRouteGuard */}
            <Route path="productos" element={
              <CriticalRouteGuard>
              <PermissionsGuard requiredPermission="verProductos">
                <Productos />
              </PermissionsGuard>
              </CriticalRouteGuard>
            } />
            <Route path="lotes" element={
              <CriticalRouteGuard>
              <PermissionsGuard requiredPermission="verLotes">
                <Lotes />
              </PermissionsGuard>
              </CriticalRouteGuard>
            } />
            <Route path="requisiciones" element={
              <CriticalRouteGuard>
              <PermissionsGuard requiredPermission="verRequisiciones">
                <Requisiciones />
              </PermissionsGuard>
              </CriticalRouteGuard>
            } />
            <Route path="requisiciones/:id" element={
              <CriticalRouteGuard>
              <PermissionsGuard requiredPermission="verRequisiciones">
                <RequisicionDetalle />
              </PermissionsGuard>
              </CriticalRouteGuard>
            } />
            <Route path="movimientos" element={
              <CriticalRouteGuard>
              <PermissionsGuard requiredPermission="verMovimientos">
                <Movimientos />
              </PermissionsGuard>
              </CriticalRouteGuard>
            } />
            <Route path="donaciones" element={
              <CriticalRouteGuard>
              <PermissionsGuard requiredPermission="verDonaciones">
                <Donaciones />
              </PermissionsGuard>
              </CriticalRouteGuard>
            } />
            <Route path="pacientes" element={
              <CriticalRouteGuard>
              <PermissionsGuard requiredPermission="verPacientes">
                <Pacientes />
              </PermissionsGuard>
              </CriticalRouteGuard>
            } />
            <Route path="dispensaciones" element={
              <CriticalRouteGuard>
              <PermissionsGuard requiredPermission="verDispensaciones">
                <Dispensaciones />
              </PermissionsGuard>
              </CriticalRouteGuard>
            } />
            {/* Módulo Compras Caja Chica del Centro */}
            <Route path="compras-caja-chica" element={
              <CriticalRouteGuard>
              <PermissionsGuard requiredPermission="verComprasCajaChica">
                <ComprasCajaChica />
              </PermissionsGuard>
              </CriticalRouteGuard>
            } />
            <Route path="inventario-caja-chica" element={
              <CriticalRouteGuard>
              <PermissionsGuard requiredPermission="verComprasCajaChica">
                <InventarioCajaChica />
              </PermissionsGuard>
              </CriticalRouteGuard>
            } />
            {/* Rutas no críticas - permitidas en modo degradado */}
            <Route path="centros" element={
              <PermissionsGuard requiredPermission="verCentros">
                <Centros />
              </PermissionsGuard>
            } />
            <Route path="usuarios" element={
              <PermissionsGuard requiredPermission="verUsuarios">
                <Usuarios />
              </PermissionsGuard>
            } />
            <Route path="reportes" element={
              <PermissionsGuard requiredPermission="verReportes">
                <Reportes />
              </PermissionsGuard>
            } />
            <Route path="trazabilidad" element={
              <PermissionsGuard requiredPermission="verTrazabilidad">
                <Trazabilidad />
              </PermissionsGuard>
            } />
            <Route path="notificaciones" element={
              <PermissionsGuard requiredPermission="verNotificaciones">
                <Notificaciones />
              </PermissionsGuard>
            } />
            <Route path="perfil" element={
              <PermissionsGuard requiredPermission="verPerfil">
                <Perfil />
              </PermissionsGuard>
            } />
            <Route path="configuracion-tema" element={
              <PermissionsGuard requiredPermission="configurarTema">
                <ConfiguracionTema />
              </PermissionsGuard>
            } />
            {/* Panel de Auditoría - Solo SUPER ADMIN */}
            <Route path="auditoria" element={<Auditoria />} />
          </Route>
          
          {/* Páginas de error */}
          <Route path="/error" element={<ServerError />} />
          <Route path="*" element={<NotFound />} />
          </Routes>
          </Suspense>
        </ThemeProvider>
      </PermissionProvider>
      </HealthContext.Provider>
      </ModalStackProvider>
    </Router>
  );
}

export default App;
