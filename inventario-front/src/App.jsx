// filepath: inventario-front/src/App.jsx
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { Suspense, lazy, useEffect, useState } from 'react';
import { PermissionProvider } from './context/PermissionContext';
import { ThemeProvider } from './context/ThemeContext';
import { usePermissions } from './hooks/usePermissions';
import { useInactivityLogout } from './hooks/useInactivityLogout';
import PermissionsGuard from './components/PermissionsGuard';
import ErrorBoundary from './components/ErrorBoundary';
import { getApiConfigError, hasHttpWarning, wasHealthCheckSkipped, checkApiHealth, isApiHealthy } from './services/api';

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
 * Muestra advertencia persistente cuando no se verificó compatibilidad con backend
 */
const HealthCheckWarningBanner = ({ reason, onDismiss, onRetry }) => (
  <div className="fixed bottom-0 left-0 right-0 z-40 bg-amber-100 border-t border-amber-300 px-4 py-3 shadow-lg">
    <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <span className="text-xl">🔌</span>
        <div>
          <p className="text-sm font-medium text-amber-800">
            Verificación de API omitida
          </p>
          <p className="text-xs text-amber-700">
            {reason || 'No se pudo verificar la compatibilidad con el servidor. Algunas funciones podrían no estar disponibles.'}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={onRetry}
          className="px-3 py-1.5 text-sm font-medium rounded-lg bg-amber-200 text-amber-800 hover:bg-amber-300 transition-colors"
        >
          🔄 Verificar ahora
        </button>
        <button
          onClick={onDismiss}
          className="px-3 py-1.5 text-sm font-medium rounded-lg bg-gray-200 text-gray-700 hover:bg-gray-300 transition-colors"
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
 */
const ApiUnhealthyBanner = ({ error, onRetry }) => (
  <div className="fixed bottom-0 left-0 right-0 z-40 bg-red-100 border-t border-red-300 px-4 py-3 shadow-lg">
    <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <span className="text-xl">⚠️</span>
        <div>
          <p className="text-sm font-medium text-red-800">
            Conexión con servidor inestable
          </p>
          <p className="text-xs text-red-700">
            {error || 'No se pudo conectar al servidor. Las operaciones podrían fallar.'}
          </p>
        </div>
      </div>
      <button
        onClick={onRetry}
        className="px-3 py-1.5 text-sm font-medium rounded-lg bg-red-200 text-red-800 hover:bg-red-300 transition-colors"
      >
        🔄 Reintentar conexión
      </button>
    </div>
  </div>
);

// Componente de error de configuración (ISS-001)
const ConfigErrorPage = ({ error }) => (
  <div className="min-h-screen flex items-center justify-center bg-gray-100">
    <div className="max-w-lg w-full mx-4 bg-white rounded-lg shadow-xl p-8 text-center">
      <div className="mx-auto w-16 h-16 flex items-center justify-center rounded-full bg-red-100 mb-4">
        <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Error de Configuración</h1>
      <p className="text-gray-600 mb-4">{error}</p>
      <div className="bg-gray-50 rounded p-4 text-left text-sm">
        <p className="font-medium text-gray-700 mb-2">Para resolver este problema:</p>
        <ol className="list-decimal list-inside text-gray-600 space-y-1">
          <li>Verifique que el archivo <code className="bg-gray-200 px-1 rounded">.env</code> existe</li>
          <li>Asegúrese de que <code className="bg-gray-200 px-1 rounded">VITE_API_URL</code> está configurado</li>
          <li>Reconstruya la aplicación después de los cambios</li>
        </ol>
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
 * ISS-002 FIX: ProtectedRoute mejorado con bloqueo hasta confirmación de permisos
 * Bloquea render hasta que el estado de autenticación esté resuelto
 */
function ProtectedRoute({ children }) {
  const { user, loading, error } = usePermissions();
  const [isReady, setIsReady] = useState(false);

  // ISS-002: Esperar hasta que loading termine para evitar race conditions
  useEffect(() => {
    if (!loading) {
      // Pequeño delay para asegurar que el estado se ha propagado
      const timer = setTimeout(() => setIsReady(true), 50);
      return () => clearTimeout(timer);
    }
  }, [loading]);

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

function App() {
  // ISS-001: Verificar configuración de API antes de renderizar
  const configError = getApiConfigError();
  if (configError) {
    return <ConfigErrorPage error={configError} />;
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
        });
      } catch (err) {
        setHealthState({
          checked: true,
          healthy: false,
          skipped: false,
          error: err.message || 'Error desconocido al verificar conexión',
          reason: null,
          dismissed: false,
        });
      }
    };
    
    checkHealth();
  }, []);
  
  // ISS-005: Handler para reintentar healthcheck
  const handleRetryHealthCheck = async () => {
    setHealthState(prev => ({ ...prev, checked: false }));
    try {
      const result = await checkApiHealth({ force: true });
      setHealthState({
        checked: true,
        healthy: result.healthy,
        skipped: result.skipped || false,
        error: result.error || null,
        reason: result.reason || null,
        dismissed: false,
      });
    } catch (err) {
      setHealthState(prev => ({
        ...prev,
        checked: true,
        healthy: false,
        error: err.message,
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

  return (
    <Router>
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
            />
          )}
          <SessionManager />
          <Toaster position="top-right" />
        
          <Suspense fallback={<PageLoader />}>
          <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/recuperar-password" element={<RecuperarPassword />} />
          <Route path="/restablecer-password" element={<RestablecerPassword />} />
          
          <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={
              <PermissionsGuard requiredPermission="verDashboard">
                <Dashboard />
              </PermissionsGuard>
            } />
            <Route path="productos" element={
              <PermissionsGuard requiredPermission="verProductos">
                <Productos />
              </PermissionsGuard>
            } />
            <Route path="lotes" element={
              <PermissionsGuard requiredPermission="verLotes">
                <Lotes />
              </PermissionsGuard>
            } />
            <Route path="requisiciones" element={
              <PermissionsGuard requiredPermission="verRequisiciones">
                <Requisiciones />
              </PermissionsGuard>
            } />
            <Route path="requisiciones/:id" element={
              <PermissionsGuard requiredPermission="verRequisiciones">
                <RequisicionDetalle />
              </PermissionsGuard>
            } />
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
            <Route path="movimientos" element={
              <PermissionsGuard requiredPermission="verMovimientos">
                <Movimientos />
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
            <Route path="donaciones" element={
              <PermissionsGuard requiredPermission="verDonaciones">
                <Donaciones />
              </PermissionsGuard>
            } />
          </Route>
          
          {/* Páginas de error */}
          <Route path="/error" element={<ServerError />} />
          <Route path="*" element={<NotFound />} />
          </Routes>
          </Suspense>
        </ThemeProvider>
      </PermissionProvider>
    </Router>
  );
}

export default App;
