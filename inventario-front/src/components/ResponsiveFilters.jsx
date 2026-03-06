/**
 * ResponsiveFilters - Filtros colapsables en móvil
 * 
 * Features:
 * - En desktop: filtros visibles en fila/grid
 * - En móvil: filtros colapsables con botón toggle
 * - Animación suave de expansión
 */

import { useState, useEffect } from 'react';
import { FaFilter, FaChevronDown, FaTimes } from 'react-icons/fa';

const useIsMobile = (breakpoint = 768) => {
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

/**
 * ResponsiveFilters Component
 * 
 * @param {React.ReactNode} children - Los filtros (inputs, selects, etc)
 * @param {Function} onClear - Callback para limpiar filtros
 * @param {Number} activeCount - Número de filtros activos
 * @param {String} title - Título del panel de filtros
 */
const ResponsiveFilters = ({ 
  children, 
  onClear, 
  activeCount = 0, 
  title = 'Filtros',
  className = '' 
}) => {
  const isMobile = useIsMobile();
  const [isExpanded, setIsExpanded] = useState(false);

  // En desktop siempre expandido
  useEffect(() => {
    if (!isMobile) {
      setIsExpanded(true);
    }
  }, [isMobile]);

  // Vista móvil
  if (isMobile) {
    return (
      <div className={`mb-4 ${className}`}>
        {/* Botón toggle */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center justify-between px-4 py-3 rounded-xl font-semibold text-sm transition-all"
          style={{
            background: isExpanded 
              ? 'linear-gradient(135deg, var(--color-primary, #932043) 0%, var(--color-primary-hover, #632842) 100%)'
              : 'white',
            color: isExpanded ? 'white' : 'var(--color-primary, #932043)',
            border: isExpanded ? 'none' : '2px solid var(--color-primary, #932043)',
            boxShadow: isExpanded ? '0 4px 12px rgba(147, 32, 67, 0.25)' : 'none',
          }}
        >
          <div className="flex items-center gap-2">
            <FaFilter size={14} />
            <span>{title}</span>
            {activeCount > 0 && (
              <span 
                className="flex items-center justify-center min-w-[20px] h-5 px-1.5 text-xs font-bold rounded-full"
                style={{
                  backgroundColor: isExpanded ? 'white' : 'var(--color-primary, #932043)',
                  color: isExpanded ? 'var(--color-primary, #932043)' : 'white',
                }}
              >
                {activeCount}
              </span>
            )}
          </div>
          <FaChevronDown 
            className={`transform transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
            size={14}
          />
        </button>

        {/* Panel de filtros */}
        <div 
          className={`overflow-hidden transition-all duration-300 ease-in-out ${
            isExpanded ? 'mt-3 opacity-100' : 'mt-0 opacity-0'
          }`}
          style={{
            maxHeight: isExpanded ? '1000px' : '0',
          }}
        >
          <div 
            className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm"
          >
            {/* Grid de filtros en móvil - 1 columna */}
            <div className="flex flex-col gap-3">
              {children}
            </div>

            {/* Acciones */}
            {onClear && (
              <div className="mt-4 pt-3 border-t border-gray-200 flex gap-2">
                <button
                  onClick={onClear}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors"
                  style={{
                    color: 'var(--color-text-secondary, #757575)',
                    border: '1px solid var(--color-border, #e7e5e4)',
                  }}
                >
                  <FaTimes size={12} />
                  Limpiar filtros
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Vista desktop - Filtros en línea
  return (
    <div className={`mb-4 ${className}`}>
      <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
        <div className="flex flex-wrap items-end gap-4">
          {children}
          
          {onClear && activeCount > 0 && (
            <button
              onClick={onClear}
              className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-700 transition-colors"
            >
              <FaTimes size={12} />
              Limpiar
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ResponsiveFilters;
