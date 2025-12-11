import { Navigate } from "react-router-dom";
import { usePermissions } from "../hooks/usePermissions";

/**
 * ISS-004 FIX (audit32): Wrapper para proteger rutas o secciones por permiso/rol.
 * 
 * CAMBIOS ISS-004:
 * - Ahora espera a que `permisosValidados` sea true antes de evaluar permisos
 * - Los permisos NO se hidratan desde storage local, siempre vienen del backend
 * - Muestra loader mientras permisos se validan con el servidor
 * 
 * Muestra loader mientras carga permisos, redirige a login si no hay usuario,
 * y permite definir un fallback visual cuando falta permiso.
 */
function PermissionsGuard({ children, requiredPermission, fallback = null, redirectTo = "/login" }) {
  const { user, loading, verificarPermiso, permisosValidados, permisos } = usePermissions();

  // ISS-004 FIX: Mostrar loader mientras carga O mientras permisos no están validados
  // Esto previene que se muestren secciones basándose en permisos locales no validados
  const esperandoValidacion = loading || (!permisosValidados && permisos?._source === 'pending_validation');
  
  if (esperandoValidacion) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-t-transparent spinner-institucional mx-auto" />
          <p className="mt-3 text-sm text-gray-500">Validando permisos...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to={redirectTo} replace />;
  }

  // ISS-004 FIX: Solo evaluar permisos después de validación con backend
  if (requiredPermission && !verificarPermiso(requiredPermission)) {
    // Log para debugging cuando acceso es denegado
    if (import.meta.env.DEV) {
      console.warn(
        `[PermissionsGuard] Acceso denegado a '${requiredPermission}'. ` +
        `Permisos validados: ${permisosValidados}. Fuente: ${permisos?._source}`
      );
    }
    
    return fallback || (
      <div className="min-h-[60vh] flex flex-col items-center justify-center text-center">
        <p className="text-3xl font-bold text-red-600 mb-2">Acceso denegado</p>
        <p className="text-gray-600">No tienes permisos para ver esta sección.</p>
        {import.meta.env.DEV && (
          <p className="mt-2 text-xs text-gray-400">
            Permiso requerido: {requiredPermission} | Fuente: {permisos?._source}
          </p>
        )}
      </div>
    );
  }

  return children;
}

export default PermissionsGuard;
