import { FaLock } from 'react-icons/fa';
import { useContext } from 'react';
import { PermissionContext } from '../context/contexts';

/**
 * Hook seguro que no lanza error si el contexto no está montado.
 * Retorna permisos vacíos en lugar de romper la UI.
 * También indica si el contexto está disponible para mostrar mensajes apropiados.
 */
function useSafePermissions() {
  const context = useContext(PermissionContext);
  // Si no hay contexto, retornar un objeto seguro con permisos vacíos
  if (!context) {
    return {
      permisos: {},
      verificarPermiso: () => false,
      user: null,
      contextDisponible: false, // Flag para indicar que el contexto no está montado
    };
  }
  return { ...context, contextDisponible: true };
}

/**
 * Botn protegido por permisos: se deshabilita cuando el usuario no cuenta con ellos.
 */
export function ProtectedButton({
  permission,
  onClick,
  children,
  className = '',
  disabledClassName = 'opacity-50 cursor-not-allowed',
  showIcon = true,
  tooltip = true,
  ...props
}) {
  const { verificarPermiso, contextDisponible } = useSafePermissions();
  const tienePermiso = verificarPermiso(permission);

  // Determinar el mensaje de tooltip según el estado
  const getTooltipMessage = () => {
    if (!tooltip) return '';
    if (!contextDisponible) return 'Cargando permisos... Por favor espera';
    return 'No tiene permisos para esta acción';
  };

  if (!tienePermiso) {
    return (
      <button
        type="button"
        disabled
        title={getTooltipMessage()}
        className={`${className} ${disabledClassName}`}
        {...props}
      >
        {showIcon && <FaLock className="inline mr-1" />}
        {children}
      </button>
    );
  }

  return (
    <button type="button" onClick={onClick} className={className} {...props}>
      {children}
    </button>
  );
}

/**
 * Envuelve contenido que solo debe mostrarse cuando se tiene el permiso indicado.
 */
export function ProtectedComponent({ permission, children, fallback = null }) {
  const { verificarPermiso } = useSafePermissions();
  const tienePermiso = verificarPermiso(permission);

  if (!tienePermiso) {
    return fallback;
  }

  return <>{children}</>;
}
