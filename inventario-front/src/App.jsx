// filepath: inventario-front/src/App.jsx
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { Suspense, lazy } from 'react';
import { PermissionProvider } from './context/PermissionContext';
import { ThemeProvider } from './context/ThemeContext';
import { usePermissions } from './hooks/usePermissions';
import { useInactivityLogout } from './hooks/useInactivityLogout';
import PermissionsGuard from './components/PermissionsGuard';

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
const Auditoria = lazy(() => import('./pages/Auditoria'));
const Movimientos = lazy(() => import('./pages/Movimientos'));
const Notificaciones = lazy(() => import('./pages/Notificaciones'));
const Perfil = lazy(() => import('./pages/Perfil'));
const ConfiguracionTema = lazy(() => import('./pages/ConfiguracionTema'));
const NotFound = lazy(() => import('./pages/NotFound'));
const ServerError = lazy(() => import('./pages/ServerError'));

// Componente de carga para Suspense
const PageLoader = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
      <p className="mt-4 text-gray-600">Cargando...</p>
    </div>
  </div>
);

function SessionManager() {
  useInactivityLogout();
  return null;
}

function ProtectedRoute({ children }) {
  const { user, loading } = usePermissions();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  return children;
}

function App() {
  return (
    <Router>
      <PermissionProvider>
        <ThemeProvider>
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
            <Route path="auditoria" element={
              <PermissionsGuard requiredPermission="verAuditoria">
                <Auditoria />
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
              <PermissionsGuard requiredPermission="esSuperusuario">
                <ConfiguracionTema />
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
