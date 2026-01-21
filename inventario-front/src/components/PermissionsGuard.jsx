import { Navigate } from "react-router-dom";
import { usePermissions } from "../hooks/usePermissions";

/**
 * ISS-004 FIX (audit32): Wrapper para proteger rutas o secciones por permiso/rol.
 * ISS-MEDICO FIX: Bloquea acceso si permisos vienen de fallback para roles específicos.
 * ISS-SEC FIX: Maneja estado de error de carga de permisos para evitar spinner infinito.
 * 
 * CAMBIOS ISS-004:
 * - Ahora espera a que `permisosValidados` sea true antes de evaluar permisos
 * - Los permisos NO se hidratan desde storage local, siempre vienen del backend
 * - Muestra loader mientras permisos se validan con el servidor
 * 
 * CAMBIOS ISS-MEDICO:
 * - Roles específicos (MEDICO, ADMINISTRADOR_CENTRO, DIRECTOR_CENTRO) NO pueden
 *   acceder a rutas protegidas si los permisos no vienen del backend
 * - Esto evita que manipulación de sessionStorage otorgue permisos indebidos
 * 
 * CAMBIOS ISS-SEC:
 * - Si hay error de carga de permisos, muestra mensaje de error con opción de reintento
 * - Evita spinner infinito cuando API está caída o sesión es inválida
 * 
 * Muestra loader mientras carga permisos, redirige a login si no hay usuario,
 * y permite definir un fallback visual cuando falta permiso.
 */
function PermissionsGuard({ children, requiredPermission, fallback = null, redirectTo = "/login" }) {
  const { user, loading, verificarPermiso, permisosValidados, permisos, recargarUsuario } = usePermissions();

  // ISS-SEC FIX: Detectar estado de error en carga de permisos
  const tieneErrorCarga = permisos?._loadError === true;
  
  // ISS-004 FIX: Mostrar loader mientras carga O mientras permisos no están validados
  // ISS-SEC FIX: NO mostrar loader si hay error de carga
  const esperandoValidacion = !tieneErrorCarga && (loading || (!permisosValidados && permisos?._source === 'pending_validation'));
  
  // ISS-SEC FIX: Si hay error de carga, mostrar pantalla de error con opción de reintento
  if (tieneErrorCarga) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="w-16 h-16 mx-auto rounded-full bg-red-100 flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-800 mb-2">
            {permisos?._errorMessage || 'Error al cargar permisos'}
          </h3>
          <p className="text-sm text-gray-600 mb-4">
            No se pudo validar tu sesión. Esto puede deberse a problemas de conexión o una sesión expirada.
          </p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => recargarUsuario?.(true)}
              className="px-4 py-2 rounded-lg text-white text-sm font-semibold transition-colors"
              style={{ backgroundColor: 'var(--color-primary, #9F2241)' }}
            >
              Reintentar
            </button>
            <button
              onClick={() => window.location.href = redirectTo}
              className="px-4 py-2 rounded-lg bg-gray-100 text-gray-700 text-sm font-semibold hover:bg-gray-200 transition-colors"
            >
              Ir al login
            </button>
          </div>
        </div>
      </div>
    );
  }
  
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

  // ISS-MEDICO FIX: Roles específicos NO pueden usar rutas si permisos no vienen del backend
  // Esto bloquea acceso cuando hay fallback y el rol es específico
  if (permisos?._requiresBackendValidation && permisos?._source !== 'backend') {
    if (import.meta.env.DEV) {
      console.warn(
        `[PermissionsGuard] ISS-MEDICO: Rol específico '${permisos?.role}' requiere permisos del backend. ` +
        `Fuente actual: ${permisos?._source}. Acceso denegado.`
      );
    }
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center text-center">
        <p className="text-3xl font-bold text-amber-600 mb-2">Verificando permisos</p>
        <p className="text-gray-600">Tu rol requiere validación del servidor.</p>
        <p className="text-gray-500 text-sm mt-2">Por favor, cierra sesión e inicia de nuevo.</p>
        {import.meta.env.DEV && (
          <p className="mt-2 text-xs text-gray-400">
            Rol: {permisos?.role} | Fuente: {permisos?._source}
          </p>
        )}
      </div>
    );
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
