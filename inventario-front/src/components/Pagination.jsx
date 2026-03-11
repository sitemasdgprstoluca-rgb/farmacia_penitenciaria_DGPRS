import PropTypes from 'prop-types';
import { useState, useEffect } from 'react';

// Hook para detectar móvil
const useIsMobile = (breakpoint = 640) => {
  const [isMobile, setIsMobile] = useState(
    typeof window !== 'undefined' ? window.innerWidth < breakpoint : false
  );

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < breakpoint);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [breakpoint]);

  return isMobile;
};

function Pagination({
  page = 1,
  totalPages = 1,
  totalItems = 0,
  pageSize,
  onPageChange,
  onPageSizeChange,
}) {
  const isMobile = useIsMobile();

  const goTo = (nextPage) => {
    if (!onPageChange) return;
    const target = Math.max(1, Math.min(totalPages || 1, nextPage));
    onPageChange(target);
  };

  const renderPages = () => {
    const pages = [];
    const maxButtons = isMobile ? 3 : 5;
    const halfWindow = Math.floor(maxButtons / 2);

    let start = Math.max(1, page - halfWindow);
    let end = Math.min(totalPages, start + maxButtons - 1);

    if (end - start < maxButtons - 1) {
      start = Math.max(1, end - maxButtons + 1);
    }

    for (let p = start; p <= end; p += 1) {
      pages.push(
        <button
          type="button"
          key={p}
          onClick={() => goTo(p)}
          className={`
            min-w-[36px] h-9 rounded-md text-sm font-semibold transition-all duration-200
            ${p === page
              ? 'text-white shadow-sm'
              : 'bg-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }
          `}
          style={p === page
            ? {
                backgroundColor: 'var(--color-primary, #932043)',
              }
            : {}
          }
          disabled={p === page}
        >
          {p}
        </button>
      );
    }
    return pages;
  };

  const infoText = totalItems > 0
    ? `Mostrando ${Math.min((page - 1) * (pageSize || 1) + 1, totalItems)}-${Math.min(page * (pageSize || 1), totalItems)} de ${totalItems} registros`
    : 'No hay registros';

  // Vista móvil compacta
  if (isMobile) {
    return (
      <div className="flex flex-col items-center gap-2 mt-4">
        <div className="inline-flex items-center bg-white rounded-full shadow-md px-2 py-1.5 gap-1">
          {/* Anterior */}
          <button
            type="button"
            onClick={() => goTo(page - 1)}
            disabled={page <= 1}
            className="flex items-center gap-1 rounded-full px-3 py-1.5 text-sm font-medium transition-all disabled:opacity-30"
            style={{ color: 'var(--color-primary, #932043)' }}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span>Anterior</span>
          </button>

          <div className="flex items-center gap-0.5">
            {renderPages()}
          </div>

          {/* Siguiente */}
          <button
            type="button"
            onClick={() => goTo(page + 1)}
            disabled={page >= totalPages}
            className="flex items-center gap-1 rounded-full px-3 py-1.5 text-sm font-medium text-white transition-all disabled:opacity-30"
            style={{ backgroundColor: 'var(--color-primary, #932043)' }}
          >
            <span>Siguiente</span>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        <p className="text-xs text-gray-500">{infoText}</p>
      </div>
    );
  }

  // Vista desktop — Elevated Minimal Pagination
  return (
    <div className="flex flex-col items-center gap-2 mt-4">
      <div className="inline-flex items-center bg-white rounded-full shadow-md px-2 py-1.5 gap-1">
        {/* Anterior — estilo outlined */}
        <button
          type="button"
          onClick={() => goTo(page - 1)}
          disabled={page <= 1}
          className="flex items-center gap-1 rounded-full px-4 py-1.5 text-sm font-medium border transition-all disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-50"
          style={{
            color: 'var(--color-primary, #932043)',
            borderColor: 'var(--color-primary, #932043)',
          }}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span>Anterior</span>
        </button>

        {/* Números de página */}
        <div className="flex items-center gap-0.5 mx-1">
          {renderPages()}
        </div>

        {/* Siguiente — estilo filled */}
        <button
          type="button"
          onClick={() => goTo(page + 1)}
          disabled={page >= totalPages}
          className="flex items-center gap-1 rounded-full px-4 py-1.5 text-sm font-medium text-white border transition-all disabled:opacity-30 disabled:cursor-not-allowed hover:opacity-90"
          style={{
            backgroundColor: 'var(--color-primary, #932043)',
            borderColor: 'var(--color-primary, #932043)',
          }}
        >
          <span>Siguiente</span>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      <p className="text-sm text-gray-500">{infoText}</p>

      {onPageSizeChange && (
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-600 bg-white hover:border-gray-300 transition-colors"
        >
          {[10, 25, 50, 100].map((size) => (
            <option key={size} value={size}>
              {size} por página
            </option>
          ))}
        </select>
      )}
    </div>
  );
}

// FRONT-004: PropTypes para validación de props
Pagination.propTypes = {
  page: PropTypes.number,
  totalPages: PropTypes.number,
  totalItems: PropTypes.number,
  pageSize: PropTypes.number,
  onPageChange: PropTypes.func.isRequired,
  onPageSizeChange: PropTypes.func,
};

export default Pagination;
