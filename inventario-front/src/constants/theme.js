/**
 * Constantes de tema - Usar variables CSS dinámicas para compatibilidad con TemaGlobal
 * 
 * IMPORTANTE: COLORS ahora usa getComputedStyle para obtener los valores CSS
 * del tema activo. Si necesitas un color en un style={}, usa las clases CSS
 * o las variables directamente: var(--color-primary)
 */

// Función helper para obtener el valor actual de una variable CSS
const getCSSVar = (varName, fallback) => {
  if (typeof window !== 'undefined' && document.documentElement) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
    return value || fallback;
  }
  return fallback;
};

// COLORS con valores por defecto - usar getCSSVar() en runtime para valores dinámicos
export const COLORS = {
  // Colores principales del tema - se actualizan via CSS variables
  get vino() { return getCSSVar('--color-primary', '#9F2241'); },
  get primary() { return getCSSVar('--color-primary', '#9F2241'); }, // Alias de vino para compatibilidad
  get guinda() { return getCSSVar('--color-primary-hover', '#6B1839'); },
  get vinoOscuro() { return getCSSVar('--color-primary-hover', '#6B1839'); },
  get vinoLight() { return `color-mix(in srgb, ${getCSSVar('--color-primary', '#9F2241')} 15%, transparent)`; },
  
  // Colores de fondo del tema
  get sidebarBg() { return getCSSVar('--color-sidebar-bg', '#9F2241'); },
  get headerBg() { return getCSSVar('--color-header-bg', '#9F2241'); },
  get cardBg() { return getCSSVar('--color-card-bg', '#FFFFFF'); },
  get background() { return getCSSVar('--color-background', '#F5F5F5'); },
  
  // Colores de texto del tema
  get texto() { return getCSSVar('--color-text', '#1F2937'); },
  get textoSecundario() { return getCSSVar('--color-text-secondary', '#757575'); },
  
  // Colores de estado (estos son fijos para consistencia semántica)
  grisSuave: '#F3F4F6',
  success: '#10B981',
  danger: '#EF4444',
  warning: '#F59E0B',
  info: '#0284C7'
};

// Gradientes que usan variables CSS del tema - se actualizan dinámicamente
export const PRIMARY_GRADIENT = 'var(--color-sidebar-bg, linear-gradient(135deg, #9F2241 0%, #6B1839 100%))';
export const SECONDARY_GRADIENT = 'var(--color-sidebar-bg, linear-gradient(135deg, #6B1839 0%, #9F2241 100%))';

// Helper para obtener gradiente dinámico del tema
export const getThemeGradient = () => 
  `linear-gradient(135deg, ${COLORS.vino} 0%, ${COLORS.guinda} 100%)`;

// Helper para obtener gradiente con colores específicos (cuando se necesita)
export const getGradient = (colorStart, colorEnd) => 
  `linear-gradient(135deg, ${colorStart} 0%, ${colorEnd} 100%)`;
