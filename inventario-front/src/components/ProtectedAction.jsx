import { FaLock } from 'react-icons/fa';
import { usePermissions } from '../hooks/usePermissions';

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
  const { verificarPermiso } = usePermissions();
  const tienePermiso = verificarPermiso(permission);

  if (!tienePermiso) {
    return (
      <button
        type="button"
        disabled
        title={tooltip ? 'No tiene permisos para esta acción' : ''}
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
  const { verificarPermiso } = usePermissions();
  const tienePermiso = verificarPermiso(permission);

  if (!tienePermiso) {
    return fallback;
  }

  return <>{children}</>;
}
