/**
 * PageHeader - Command Center Style
 * Encabezado moderno tipo SaaS con dos filas:
 * Row 1: Icono + Título + Métrica | Acciones
 * Row 2: Filtros y controles (opcional)
 * Usa variables CSS para colores dinámicos del tema
 */
import PropTypes from 'prop-types';

const PageHeader = ({ icon: Icon, title, subtitle, badge, actions, filters }) => {
  const renderBadge = () => {
    if (!badge) return null;
    if (typeof badge === 'string') {
      return (
        <span 
          className="px-3 py-1 rounded-full text-xs font-semibold"
          style={{
            background: 'rgba(147, 32, 67, 0.08)',
            color: 'var(--color-primary, #932043)',
          }}
        >
          {badge}
        </span>
      );
    }
    return badge;
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200/80 shadow-sm overflow-hidden">
      {/* Row 1: Título + Acciones */}
      <div className="px-5 py-4 flex flex-wrap items-center gap-4">
        {/* Left: Icon + Title + Metric */}
        <div className="flex items-center gap-3 min-w-0 flex-1">
          {Icon && (
            <div 
              className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{
                background: 'linear-gradient(135deg, var(--color-primary, #932043) 0%, var(--color-primary-hover, #632842) 100%)',
              }}
            >
              <Icon size={18} className="text-white" />
            </div>
          )}
          <div className="min-w-0">
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-lg font-bold text-gray-900 leading-tight">{title}</h1>
              {renderBadge()}
            </div>
            {subtitle && (
              <p className="text-xs text-gray-500 mt-0.5 truncate">{subtitle}</p>
            )}
          </div>
        </div>

        {/* Right: Actions */}
        {actions && (
          <div className="flex flex-wrap items-center gap-2">
            {actions}
          </div>
        )}
      </div>

      {/* Row 2: Filtros (opcional) */}
      {filters && (
        <div 
          className="px-5 py-3 flex flex-wrap items-center gap-2"
          style={{
            borderTop: '1px solid rgba(0,0,0,0.06)',
            background: 'rgba(249, 250, 251, 0.7)',
          }}
        >
          {filters}
        </div>
      )}
    </div>
  );
};

// FRONT-004: PropTypes para validación de props
PageHeader.propTypes = {
  icon: PropTypes.elementType,
  title: PropTypes.string.isRequired,
  subtitle: PropTypes.string,
  badge: PropTypes.oneOfType([PropTypes.string, PropTypes.node]),
  actions: PropTypes.node,
  filters: PropTypes.node,
};

export default PageHeader;
