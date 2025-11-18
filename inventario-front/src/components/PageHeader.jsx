import { PRIMARY_GRADIENT } from '../constants/theme';

const PageHeader = ({ icon: Icon, title, subtitle, badge, actions }) => {
  const renderBadge = () => {
    if (!badge) return null;
    if (typeof badge === 'string') {
      return (
        <span className="bg-white/20 px-4 py-1 rounded-full text-sm font-semibold">
          {badge}
        </span>
      );
    }
    return badge;
  };

  return (
    <div
      className="rounded-2xl p-6 text-white shadow-lg"
      style={{ background: PRIMARY_GRADIENT }}
    >
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-4">
          {Icon && (
            <div className="bg-white/20 p-3 rounded-full">
              <Icon size={24} />
            </div>
          )}
          <div>
            <h1 className="text-2xl font-bold">{title}</h1>
            {subtitle && (
              <p className="text-white/80 text-sm">
                {subtitle}
              </p>
            )}
          </div>
        </div>
        {(badge || actions) && (
          <div className="flex flex-wrap items-center gap-3 ml-auto">
            {renderBadge()}
            {actions && (
              <div className="flex flex-wrap gap-3">
                {actions}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PageHeader;
