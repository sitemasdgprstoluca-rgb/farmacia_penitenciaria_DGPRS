/**
 * ResponsiveTable - Tabla que se convierte en tarjetas en móvil
 * 
 * Features:
 * - Vista de tabla en desktop (≥768px)
 * - Vista de tarjetas en móvil (<768px)
 * - Configuración flexible de columnas
 * - Soporte para acciones por fila
 * - Animaciones suaves en transición
 */

import { useState, useEffect, useMemo } from 'react';

/**
 * Hook para detectar si estamos en móvil
 */
const useIsMobile = (breakpoint = 768) => {
  const [isMobile, setIsMobile] = useState(
    typeof window !== 'undefined' ? window.innerWidth < breakpoint : false
  );

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < breakpoint);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [breakpoint]);

  return isMobile;
};

/**
 * Componente de tarjeta móvil individual
 */
const MobileCard = ({ item, columns, actions, titleField, titleRenderer, index }) => {
  // Determinar el título de la tarjeta
  const title = useMemo(() => {
    if (titleRenderer) {
      return titleRenderer(item, index);
    }
    if (titleField) {
      return item[titleField];
    }
    // Buscar un campo que parezca título
    const titleCol = columns.find(c => 
      c.key === 'nombre' || c.key === 'title' || c.key === 'id' || c.key === 'codigo'
    );
    return titleCol ? item[titleCol.key] : `#${index + 1}`;
  }, [item, columns, titleField, titleRenderer, index]);

  // Filtrar columnas que no sean el título
  const displayColumns = useMemo(() => {
    return columns.filter(col => col.key !== titleField && !col.hideOnMobile);
  }, [columns, titleField]);

  return (
    <div 
      className="bg-white rounded-xl shadow-md border border-gray-100 overflow-hidden transition-all duration-200 hover:shadow-lg"
      style={{ borderLeft: '4px solid var(--color-primary, #932043)' }}
    >
      {/* Header de la tarjeta */}
      <div 
        className="px-4 py-3 flex items-center justify-between gap-3"
        style={{ 
          background: 'linear-gradient(135deg, rgba(147, 32, 67, 0.03) 0%, rgba(99, 40, 66, 0.06) 100%)',
          borderBottom: '1px solid rgba(147, 32, 67, 0.1)',
        }}
      >
        <div className="flex-1 min-w-0">
          <span 
            className="font-bold text-sm truncate block"
            style={{ color: 'var(--color-primary, #932043)' }}
          >
            {title}
          </span>
        </div>
        {/* Badge o indicador opcional */}
        {item.status && (
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            item.status === 'activo' || item.status === 'aprobado' || item.status === 'completado'
              ? 'bg-green-100 text-green-700' 
              : item.status === 'pendiente' 
                ? 'bg-yellow-100 text-yellow-700'
                : item.status === 'rechazado' || item.status === 'cancelado'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-gray-100 text-gray-700'
          }`}>
            {item.status}
          </span>
        )}
      </div>

      {/* Cuerpo de la tarjeta - Grid de campos */}
      <div className="p-4">
        <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
          {displayColumns.map((col) => {
            const value = col.render ? col.render(item[col.key], item, index) : item[col.key];
            
            return (
              <div 
                key={col.key} 
                className={`flex flex-col ${col.fullWidth ? 'col-span-2' : ''}`}
              >
                <span 
                  className="text-[10px] uppercase tracking-wider font-semibold"
                  style={{ color: 'var(--color-text-secondary, #757575)' }}
                >
                  {col.label}
                </span>
                <span className="text-sm text-gray-900 mt-0.5 break-words">
                  {value ?? '-'}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Acciones */}
      {actions && (
        <div 
          className="px-4 py-3 flex flex-wrap gap-2"
          style={{ 
            borderTop: '1px solid var(--color-border, #e7e5e4)',
            background: 'rgba(0,0,0,0.02)',
          }}
        >
          {actions(item, index)}
        </div>
      )}
    </div>
  );
};

/**
 * Componente principal ResponsiveTable
 * 
 * @param {Array} data - Los datos a mostrar
 * @param {Array} columns - Configuración de columnas: { key, label, render?, hideOnMobile?, fullWidth? }
 * @param {Function} actions - Función que retorna JSX de acciones (item, index) => JSX
 * @param {String} titleField - Campo a usar como título en tarjetas
 * @param {Function} titleRenderer - Función para renderizar título custom: (item, index) => string/JSX
 * @param {String} emptyMessage - Mensaje cuando no hay datos
 * @param {Boolean} loading - Estado de carga
 * @param {String} className - Clases adicionales para el contenedor
 */
const ResponsiveTable = ({
  data = [],
  columns = [],
  actions,
  titleField,
  titleRenderer,
  emptyMessage = 'No hay datos para mostrar',
  loading = false,
  className = '',
  onRowClick,
}) => {
  const isMobile = useIsMobile();

  // Loading state
  if (loading) {
    return (
      <div className={`${className}`}>
        <div className="flex items-center justify-center py-12">
          <div 
            className="w-10 h-10 border-4 rounded-full animate-spin"
            style={{ 
              borderColor: 'rgba(147, 32, 67, 0.2)',
              borderTopColor: 'var(--color-primary, #932043)',
            }}
          />
        </div>
      </div>
    );
  }

  // Empty state
  if (!data || data.length === 0) {
    return (
      <div className={`${className}`}>
        <div 
          className="text-center py-12 px-4 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200"
        >
          <svg 
            className="w-12 h-12 mx-auto mb-3 text-gray-300" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={1.5} 
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" 
            />
          </svg>
          <p className="text-gray-500 font-medium">{emptyMessage}</p>
        </div>
      </div>
    );
  }

  // Vista móvil - Tarjetas
  if (isMobile) {
    return (
      <div className={`space-y-3 ${className}`}>
        {data.map((item, index) => (
          <div 
            key={item.id || index}
            onClick={onRowClick ? () => onRowClick(item, index) : undefined}
            className={onRowClick ? 'cursor-pointer' : ''}
          >
            <MobileCard
              item={item}
              columns={columns}
              actions={actions}
              titleField={titleField}
              titleRenderer={titleRenderer}
              index={index}
            />
          </div>
        ))}
      </div>
    );
  }

  // Vista desktop - Tabla
  return (
    <div className={`bg-white rounded-xl shadow-md border border-gray-100 overflow-hidden ${className}`}>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr 
              style={{ 
                background: 'linear-gradient(135deg, var(--color-primary, #932043) 0%, var(--color-primary-hover, #632842) 100%)',
              }}
            >
              {columns.filter(col => !col.hideOnDesktop).map((col) => (
                <th 
                  key={col.key}
                  className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-white whitespace-nowrap"
                >
                  {col.label}
                </th>
              ))}
              {actions && (
                <th className="px-4 py-3 text-center text-xs font-bold uppercase tracking-wider text-white">
                  Acciones
                </th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.map((item, index) => (
              <tr 
                key={item.id || index}
                className={`transition-colors hover:bg-gray-50 ${onRowClick ? 'cursor-pointer' : ''}`}
                onClick={onRowClick ? () => onRowClick(item, index) : undefined}
              >
                {columns.filter(col => !col.hideOnDesktop).map((col) => {
                  const value = col.render 
                    ? col.render(item[col.key], item, index) 
                    : item[col.key];
                  
                  return (
                    <td 
                      key={col.key}
                      className="px-4 py-3 text-sm text-gray-700 whitespace-nowrap"
                    >
                      {value ?? '-'}
                    </td>
                  );
                })}
                {actions && (
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      {actions(item, index)}
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ResponsiveTable;

/**
 * Hook exportado para usar en otros componentes
 */
export { useIsMobile };
