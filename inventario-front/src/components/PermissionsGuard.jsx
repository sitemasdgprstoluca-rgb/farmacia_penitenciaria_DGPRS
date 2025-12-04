import { Navigate } from "react-router-dom";
import { usePermissions } from "../hooks/usePermissions";

/**
 * Wrapper para proteger rutas o secciones por permiso/rol.
 * Muestra loader mientras carga permisos, redirige a login si no hay usuario,
 * y permite definir un fallback visual cuando falta permiso.
 */
function PermissionsGuard({ children, requiredPermission, fallback = null, redirectTo = "/login" }) {
  const { user, loading, verificarPermiso } = usePermissions();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-4 border-t-transparent spinner-institucional" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to={redirectTo} replace />;
  }

  if (requiredPermission && !verificarPermiso(requiredPermission)) {
    return fallback || (
      <div className="min-h-[60vh] flex flex-col items-center justify-center text-center">
        <p className="text-3xl font-bold text-red-600 mb-2">Acceso denegado</p>
        <p className="text-gray-600">No tienes permisos para ver esta sección.</p>
      </div>
    );
  }

  return children;
}

export default PermissionsGuard;
