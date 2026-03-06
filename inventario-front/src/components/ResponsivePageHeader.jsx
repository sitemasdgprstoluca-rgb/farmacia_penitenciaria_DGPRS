/**
 * ResponsivePageHeader - Header de página con acciones responsivas
 * 
 * Features:
 * - Título y subtítulo responsivos
 * - Botones de acción que se adaptan a móvil
 * - Breadcrumbs opcionales
 */

import { useIsMobile } from './ResponsiveTable';

/**
 * ResponsivePageHeader Component
 * 
 * @param {String} title - Título principal
 * @param {String} subtitle - Subtítulo opcional
 * @param {React.ReactNode} actions - Botones de acción
 * @param {React.ReactNode} breadcrumbs - Breadcrumbs opcionales
 * @param {React.ReactNode} icon - Ícono del título
 */
const ResponsivePageHeader = ({
  title,
  subtitle,
  actions,
  breadcrumbs,
  icon: Icon,
  className = '',
}) => {
  const isMobile = useIsMobile();

  return (
    <div className={`mb-6 ${className}`}>
      {/* Breadcrumbs */}
      {breadcrumbs && (
        <div className="mb-2 text-sm text-gray-500 flex items-center gap-2 flex-wrap">
          {breadcrumbs}
        </div>
      )}

      {/* Header principal */}
      <div 
        className={`
          flex gap-4
          ${isMobile ? 'flex-col' : 'items-center justify-between'}
        `}
      >
        {/* Título */}
        <div className="flex items-center gap-3 min-w-0">
          {Icon && (
            <div 
              className="flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 rounded-xl flex-shrink-0"
              style={{
                background: 'linear-gradient(135deg, var(--color-primary, #932043) 0%, var(--color-primary-hover, #632842) 100%)',
                boxShadow: '0 4px 12px rgba(147, 32, 67, 0.25)',
              }}
            >
              <Icon className="text-white" size={isMobile ? 18 : 22} />
            </div>
          )}
          <div className="min-w-0">
            <h1 
              className="text-xl sm:text-2xl font-bold truncate"
              style={{ color: 'var(--color-primary-hover, #632842)' }}
            >
              {title}
            </h1>
            {subtitle && (
              <p className="text-sm text-gray-500 truncate mt-0.5">
                {subtitle}
              </p>
            )}
          </div>
        </div>

        {/* Acciones */}
        {actions && (
          <div 
            className={`
              flex gap-2 flex-shrink-0
              ${isMobile ? 'flex-wrap w-full' : ''}
            `}
          >
            {/* Envolver acciones para hacer responsivos */}
            <ResponsiveActions isMobile={isMobile}>
              {actions}
            </ResponsiveActions>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Wrapper para hacer los botones de acción responsivos
 */
const ResponsiveActions = ({ children, isMobile }) => {
  // Si es móvil, aplicar estilos a los children
  if (isMobile) {
    return (
      <div className="flex flex-wrap gap-2 w-full">
        {children}
      </div>
    );
  }

  return <>{children}</>;
};

/**
 * Botón de acción responsivo para usar dentro del header
 * Se hace full width en móvil automáticamente
 */
export const ActionButton = ({
  children,
  variant = 'primary',
  onClick,
  disabled = false,
  icon: Icon,
  className = '',
  ...props
}) => {
  const isMobile = useIsMobile();

  const variantStyles = {
    primary: {
      background: 'linear-gradient(135deg, var(--color-primary, #932043) 0%, var(--color-primary-hover, #632842) 100%)',
      color: 'white',
      border: 'none',
    },
    secondary: {
      background: 'white',
      color: 'var(--color-primary, #932043)',
      border: '2px solid var(--color-primary, #932043)',
    },
    success: {
      background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
      color: 'white',
      border: 'none',
    },
    danger: {
      background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
      color: 'white',
      border: 'none',
    },
    ghost: {
      background: 'transparent',
      color: 'var(--color-text-secondary, #757575)',
      border: 'none',
    },
  };

  const styles = variantStyles[variant] || variantStyles.primary;

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        flex items-center justify-center gap-2 
        px-4 py-2.5 rounded-xl text-sm font-semibold
        transition-all duration-200
        disabled:opacity-50 disabled:cursor-not-allowed
        hover:shadow-lg hover:-translate-y-0.5
        ${isMobile ? 'flex-1 min-w-[calc(50%-0.25rem)]' : ''}
        ${className}
      `}
      style={{
        ...styles,
        minHeight: '44px', // Touch target
      }}
      {...props}
    >
      {Icon && <Icon size={16} />}
      {children}
    </button>
  );
};

export default ResponsivePageHeader;
