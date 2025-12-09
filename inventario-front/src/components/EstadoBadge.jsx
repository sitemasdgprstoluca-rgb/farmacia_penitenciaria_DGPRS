/**
 * FLUJO V2: Badge de estado para requisiciones
 * 
 * Muestra el estado con colores e íconos apropiados
 */

import { REQUISICION_ESTADOS } from '../constants/strings';

/**
 * Mapeo de colores de Tailwind por nombre
 */
const COLORES_TAILWIND = {
  gray: {
    bg: 'bg-gray-100',
    text: 'text-gray-800',
    border: 'border-gray-300',
    dot: 'bg-gray-500',
  },
  yellow: {
    bg: 'bg-yellow-100',
    text: 'text-yellow-800',
    border: 'border-yellow-300',
    dot: 'bg-yellow-500',
  },
  orange: {
    bg: 'bg-orange-100',
    text: 'text-orange-800',
    border: 'border-orange-300',
    dot: 'bg-orange-500',
  },
  amber: {
    bg: 'bg-amber-100',
    text: 'text-amber-800',
    border: 'border-amber-300',
    dot: 'bg-amber-500',
  },
  blue: {
    bg: 'bg-blue-100',
    text: 'text-blue-800',
    border: 'border-blue-300',
    dot: 'bg-blue-500',
  },
  cyan: {
    bg: 'bg-cyan-100',
    text: 'text-cyan-800',
    border: 'border-cyan-300',
    dot: 'bg-cyan-500',
  },
  indigo: {
    bg: 'bg-indigo-100',
    text: 'text-indigo-800',
    border: 'border-indigo-300',
    dot: 'bg-indigo-500',
  },
  violet: {
    bg: 'bg-violet-100',
    text: 'text-violet-800',
    border: 'border-violet-300',
    dot: 'bg-violet-500',
  },
  purple: {
    bg: 'bg-purple-100',
    text: 'text-purple-800',
    border: 'border-purple-300',
    dot: 'bg-purple-500',
  },
  teal: {
    bg: 'bg-teal-100',
    text: 'text-teal-800',
    border: 'border-teal-300',
    dot: 'bg-teal-500',
  },
  green: {
    bg: 'bg-green-100',
    text: 'text-green-800',
    border: 'border-green-300',
    dot: 'bg-green-500',
  },
  red: {
    bg: 'bg-red-100',
    text: 'text-red-800',
    border: 'border-red-300',
    dot: 'bg-red-500',
  },
};

/**
 * Obtiene la configuración de un estado
 */
export const getEstadoConfig = (estado) => {
  const estadoLower = estado?.toLowerCase();
  return Object.values(REQUISICION_ESTADOS).find(
    e => e.value === estadoLower
  ) || {
    value: estadoLower,
    label: estado,
    color: 'gray',
    icon: '❓'
  };
};

/**
 * Helper: Obtiene el label de un estado (para compatibilidad)
 */
export const getEstadoLabel = (estado) => {
  const config = getEstadoConfig(estado);
  return config.label?.toUpperCase() || estado?.toUpperCase();
};

/**
 * Helper: Obtiene las clases CSS de badge para un estado
 * Compatible con el formato anterior de getEstadoBadge
 */
export const getEstadoBadgeClasses = (estado) => {
  const config = getEstadoConfig(estado);
  const colores = COLORES_TAILWIND[config.color] || COLORES_TAILWIND.gray;
  return `${colores.bg} ${colores.text} border ${colores.border}`;
};

/**
 * Componente Badge de Estado
 */
export function EstadoBadge({ 
  estado, 
  size = 'md',
  showIcon = true,
  showDot = false,
  className = ''
}) {
  const config = getEstadoConfig(estado);
  const colores = COLORES_TAILWIND[config.color] || COLORES_TAILWIND.gray;
  
  const sizeClasses = {
    sm: 'px-1.5 py-0.5 text-xs',
    md: 'px-2 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm',
  };
  
  return (
    <span
      className={`
        inline-flex items-center gap-1 font-medium rounded-full
        border ${colores.bg} ${colores.text} ${colores.border}
        ${sizeClasses[size]} ${className}
      `}
    >
      {showDot && (
        <span className={`w-1.5 h-1.5 rounded-full ${colores.dot}`} />
      )}
      {showIcon && config.icon && (
        <span className="text-xs">{config.icon}</span>
      )}
      {config.label}
    </span>
  );
}

/**
 * Componente para mostrar la transición de estados
 */
export function TransicionEstado({ 
  estadoAnterior, 
  estadoNuevo,
  showArrow = true 
}) {
  return (
    <div className="inline-flex items-center gap-2">
      {estadoAnterior && (
        <>
          <EstadoBadge estado={estadoAnterior} size="sm" />
          {showArrow && (
            <span className="text-gray-400">→</span>
          )}
        </>
      )}
      <EstadoBadge estado={estadoNuevo} size="sm" />
    </div>
  );
}

/**
 * Indicador de estado compacto (solo punto de color)
 */
export function EstadoIndicador({ estado, className = '' }) {
  const config = getEstadoConfig(estado);
  const colores = COLORES_TAILWIND[config.color] || COLORES_TAILWIND.gray;
  
  return (
    <span
      className={`w-3 h-3 rounded-full ${colores.dot} ${className}`}
      title={config.label}
    />
  );
}

/**
 * Lista de estados para filtros/selectores
 */
export function EstadoSelect({ 
  value, 
  onChange, 
  includeAll = true,
  className = '' 
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`
        px-3 py-2 border border-gray-300 rounded-md
        focus:ring-2 focus:ring-blue-500 focus:border-blue-500
        ${className}
      `}
    >
      {includeAll && (
        <option value="">Todos los estados</option>
      )}
      {Object.values(REQUISICION_ESTADOS).map((estado) => (
        <option key={estado.value} value={estado.value}>
          {estado.icon} {estado.label}
        </option>
      ))}
    </select>
  );
}

export default EstadoBadge;
