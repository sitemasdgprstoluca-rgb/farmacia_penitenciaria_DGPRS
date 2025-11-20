// filepath: inventario-front/src/App.jsx
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { PermissionProvider } from './context/PermissionContext';
import { usePermissions } from './hooks/usePermissions';
import { useInactivityLogout } from './hooks/useInactivityLogout';

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

function ProtectedRoute({ children, requiredPermission }) {
  const { user, loading, verificarPermiso } = usePermissions();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }
  
  if (!user) return <Navigate to="/login" replace />;
  
  if (requiredPermission && !verificarPermiso(requiredPermission)) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-red-600 mb-4">Acceso Denegado</h1>
          <p className="text-gray-600">No tiene permisos para acceder a esta pgina</p>
        </div>
      </div>
    );
  }
  
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
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="productos" element={<Productos />} />
            <Route path="lotes" element={<Lotes />} />
            <Route path="requisiciones" element={<Requisiciones />} />
            <Route path="centros" element={<Centros />} />
            <Route path="usuarios" element={
              <ProtectedRoute requiredPermission="verUsuarios">
                <Usuarios />
              </ProtectedRoute>
            } />
            <Route path="reportes" element={
              <ProtectedRoute requiredPermission="verReportes">
                <Reportes />
              </ProtectedRoute>
            } />
            <Route path="trazabilidad" element={<Trazabilidad />} />
            <Route path="auditoria" element={
              <ProtectedRoute requiredPermission="verAuditoria">
                <Auditoria />
              </ProtectedRoute>
            } />
          </Route>
        </Routes>
      </PermissionProvider>
    </Router>
  );
}

export default App;
