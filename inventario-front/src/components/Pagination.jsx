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
    // En móvil mostrar menos botones
    const maxButtons = isMobile ? 3 : 5;
    const halfWindow = Math.floor(maxButtons / 2);
    
    let start = Math.max(1, page - halfWindow);
    let end = Math.min(totalPages, start + maxButtons - 1);
    
    // Ajustar si estamos cerca del final
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
            min-w-[40px] h-10 rounded-lg border text-sm font-medium
            transition-all duration-200
            ${p === page 
              ? 'text-white shadow-md' 
              : 'bg-white text-gray-700 border-gray-200 hover:border-gray-300'
            }
          `}
          style={p === page 
            ? { 
                backgroundColor: 'var(--color-primary, #932043)', 
                borderColor: 'var(--color-primary, #932043)' 
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

  // Vista móvil compacta
  if (isMobile) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {/* Info arriba */}
        <div className="px-4 py-2 text-center border-b border-gray-100">
          <p className="text-xs text-gray-500">
            {totalItems > 0
              ? `${Math.min((page - 1) * (pageSize || 1) + 1, totalItems)}-${Math.min(page * (pageSize || 1), totalItems)} de ${totalItems}`
              : 'Sin registros'}
          </p>
        </div>
        
        {/* Controles */}
        <div className="flex items-center justify-between p-2 gap-2">
          {/* Anterior */}
          <button
            type="button"
            onClick={() => goTo(page - 1)}
            disabled={page <= 1}
            className="flex items-center justify-center w-10 h-10 rounded-lg text-white disabled:opacity-40 transition-all"
            style={{ background: 'linear-gradient(135deg, var(--color-primary, #932043), var(--color-primary-hover, #632842))' }}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          
          {/* Páginas */}
          <div className="flex items-center gap-1 flex-1 justify-center">
            {renderPages()}
          </div>
          
          {/* Siguiente */}
          <button
            type="button"
            onClick={() => goTo(page + 1)}
            disabled={page >= totalPages}
            className="flex items-center justify-center w-10 h-10 rounded-lg text-white disabled:opacity-40 transition-all"
            style={{ background: 'linear-gradient(135deg, var(--color-primary, #932043), var(--color-primary-hover, #632842))' }}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
        
        {/* Selector de página (opcional en móvil) */}
        {onPageSizeChange && (
          <div className="px-4 py-2 border-t border-gray-100">
            <select
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 bg-gray-50"
            >
              {[10, 25, 50, 100].map((size) => (
                <option key={size} value={size}>
                  {size} por página
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
    );
  }

  // Vista desktop
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-gray-200 bg-white px-4 py-3 shadow-sm">
      <p className="text-sm text-gray-600">
        {totalItems > 0
          ? `Mostrando ${Math.min((page - 1) * (pageSize || 1) + 1, totalItems)}-${Math.min(page * (pageSize || 1), totalItems)} de ${totalItems} registros`
          : 'No hay registros'}
      </p>
      <div className="flex items-center gap-2">
        {onPageSizeChange && (
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 min-h-[40px]"
          >
            {[10, 25, 50, 100].map((size) => (
              <option key={size} value={size}>
                {size} por página
              </option>
            ))}
          </select>
        )}
        <button
          type="button"
          onClick={() => goTo(page - 1)}
          disabled={page <= 1}
          className="rounded-lg px-4 py-2 text-white disabled:opacity-40 min-h-[40px] transition-all hover:shadow-md"
          style={{ background: 'linear-gradient(135deg, var(--color-primary, #932043), var(--color-primary-hover, #632842))' }}
        >
          Anterior
        </button>
        <div className="flex items-center gap-1">
          {renderPages()}
        </div>
        <button
          type="button"
          onClick={() => goTo(page + 1)}
          disabled={page >= totalPages}
          className="rounded-lg px-4 py-2 text-white disabled:opacity-40 min-h-[40px] transition-all hover:shadow-md"
          style={{ background: 'linear-gradient(135deg, var(--color-primary, #932043), var(--color-primary-hover, #632842))' }}
        >
          Siguiente
        </button>
      </div>
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
