// filepath: inventario-front/src/App.jsx
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { PermissionProvider } from './context/PermissionContext';
import { usePermissions } from './hooks/usePermissions';
import { useInactivityLogout } from './hooks/useInactivityLogout';
import PermissionsGuard from './components/PermissionsGuard';

function SessionManager() {
  useInactivityLogout();
  return null;
}

import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Productos from './pages/Productos';
import Lotes from './pages/Lotes';
import Requisiciones from './pages/Requisiciones';
import Centros from './pages/Centros';
import Usuarios from './pages/Usuarios';
import Reportes from './pages/Reportes';
import Trazabilidad from './pages/Trazabilidad';
import Auditoria from './pages/Auditoria';
import Movimientos from './pages/Movimientos';
import Notificaciones from './pages/Notificaciones';
import Perfil from './pages/Perfil';

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
        <SessionManager />
        <Toaster position="top-right" />
        
        <Routes>
          <Route path="/login" element={<Login />} />
          
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
              <PermissionsGuard requiredPermission="verLotes">
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
          </Route>
        </Routes>
      </PermissionProvider>
    </Router>
  );
}

export default App;
