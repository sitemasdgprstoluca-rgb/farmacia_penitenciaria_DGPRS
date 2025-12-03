/**
 * Constantes de tema - Usar variables CSS dinámicas para compatibilidad con TemaGlobal
 * Los valores hardcoded son fallback para compatibilidad
 */
export const COLORS = {
  vino: '#9F2241',
  guinda: '#6B1839',
  vinoLight: 'rgba(159, 34, 65, 0.15)',
  grisSuave: '#F3F4F6',
  texto: '#1F2937',
  success: '#10B981',
  danger: '#EF4444',
  warning: '#F59E0B',
  info: '#0284C7'
};

// Gradientes que usan variables CSS del tema - se actualizan dinámicamente
export const PRIMARY_GRADIENT = 'var(--color-sidebar-bg, linear-gradient(135deg, #9F2241 0%, #6B1839 100%))';
export const SECONDARY_GRADIENT = 'var(--color-sidebar-bg, linear-gradient(135deg, #6B1839 0%, #9F2241 100%))';

// Helper para obtener gradiente con colores específicos (cuando se necesita)
export const getGradient = (colorStart, colorEnd) => 
  `linear-gradient(135deg, ${colorStart} 0%, ${colorEnd} 100%)`;
