/**
 * FRONT-003 FIX: Helpers extraídos de Productos.jsx
 * 
 * Este módulo contiene funciones utilitarias para el manejo de productos,
 * incluyendo cálculo de inventario, nivel de stock, y formateo.
 */

import { COLORS, SECONDARY_GRADIENT } from '../constants/theme';
import { DEV_CONFIG } from '../config/dev';
import { hasAccessToken } from '../services/tokenManager';

// Unidades de medida disponibles
export const UNIDADES = [
  { value: 'pieza', label: 'Pieza' },
  { value: 'caja', label: 'Caja' },
  { value: 'paquete', label: 'Paquete' },
  { value: 'frasco', label: 'Frasco' },
  { value: 'sobre', label: 'Sobre' },
  { value: 'ampolleta', label: 'Ampolleta' },
  { value: 'vial', label: 'Vial' },
  { value: 'tubo', label: 'Tubo' },
  { value: 'blister', label: 'Blíster' },
  { value: 'rollo', label: 'Rollo' },
  { value: 'bolsa', label: 'Bolsa' },
  { value: 'litro', label: 'Litro' },
  { value: 'mililitro', label: 'Mililitro' },
  { value: 'gramo', label: 'Gramo' },
  { value: 'kilogramo', label: 'Kilogramo' },
  { value: 'metro', label: 'Metro' },
];

// Categorías de productos
export const CATEGORIAS = ['medicamento', 'material_curacion', 'insumo', 'equipo', 'otro'];

// Vías de administración para medicamentos
export const VIAS_ADMINISTRACION = [
  'oral', 'intravenosa', 'intramuscular', 'subcutanea', 'topica', 
  'inhalatoria', 'rectal', 'oftalmico', 'otico', 'nasal', 'otra'
];

// Niveles de inventario para filtros
export const NIVELES_INVENTARIO = [
  { value: '', label: 'Todos' },
  { value: 'alto', label: 'Alto' },
  { value: 'normal', label: 'Normal' },
  { value: 'bajo', label: 'Bajo' },
  { value: 'critico', label: 'Crítico' },
  { value: 'sin_stock', label: 'Sin Stock' },
];

// Formulario por defecto para nuevo producto
export const DEFAULT_FORM = {
  clave: '',
  nombre: '',
  descripcion: '',
  unidad_medida: 'pieza',
  stock_minimo: 10,
  stock_maximo: 100,
  categoria: 'medicamento',
  tipo: '',
  via_administracion: 'oral',
  forma_farmaceutica: '',
  presentacion: '',
  concentracion: '',
  laboratorio: '',
  registro_sanitario: '',
  activo: true,
};

/**
 * Verifica si está en sesión de desarrollo
 */
export const isDevSession = () => {
  return DEV_CONFIG.MOCKS_ENABLED && !hasAccessToken();
};

/**
 * Normaliza texto para búsqueda (quita acentos, lowercase)
 */
export const normalizeText = (text) =>
  String(text || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');

/**
 * Obtiene el inventario disponible de un producto
 * Maneja múltiples nombres de campo del backend
 */
export const getInventarioDisponible = (producto) => {
  const numericCandidates = [
    producto.stock_actual,
    producto.stock_total,
    producto.inventario_total,
    producto.inventario,
    producto.existencias,
    producto.stock_disponible,
    producto.cantidad_disponible,
    producto.cantidad_total
  ];

  for (const candidate of numericCandidates) {
    if (typeof candidate === 'number' && !Number.isNaN(candidate)) {
      return candidate;
    }
  }

  if (typeof producto.stock === 'number') {
    return producto.stock;
  }

  const parsed = Number(producto.stock_actual ?? producto.stock_total ?? producto.stock);
  return Number.isNaN(parsed) ? 0 : parsed;
};

/**
 * Formatea el inventario para mostrar
 */
export const formatInventario = (producto) => {
  const valor = getInventarioDisponible(producto);
  if (typeof valor === 'number' && !Number.isNaN(valor)) {
    return valor.toLocaleString('es-MX');
  }
  return valor || '-';
};

/**
 * Calcula el nivel de stock de un producto
 * @returns 'sin_stock' | 'critico' | 'bajo' | 'normal' | 'alto'
 */
export const calcularNivelStock = (producto) => {
  const inventario = getInventarioDisponible(producto);
  const minimo = Number(producto.stock_minimo) || 0;
  
  if (inventario <= 0) return 'sin_stock';
  
  if (minimo <= 0) {
    if (inventario < 25) return 'bajo';
    if (inventario < 100) return 'normal';
    return 'alto';
  }
  
  const ratio = inventario / minimo;
  if (ratio < 0.5) return 'critico';
  if (ratio < 1) return 'bajo';
  if (ratio <= 2) return 'normal';
  return 'alto';
};

/**
 * Determina el estado de un producto para mostrar en badge
 */
export const determinarEstadoProducto = (producto) => {
  const inventario = getInventarioDisponible(producto);
  const minimo = Number(producto.stock_minimo) || 0;
  
  if (!producto.activo) {
    return { label: 'Inactivo', activo: false };
  }
  if (inventario <= 0) {
    return { label: 'Sin inventario', activo: false };
  }
  if (minimo > 0 && inventario < minimo) {
    return { label: 'Por surtir', activo: true };
  }
  return { label: 'Activo', activo: true };
};

/**
 * Obtiene los estilos para el badge de stock según nivel
 */
export const getStockBadgeStyles = (nivel) => {
  const estilos = {
    alto: {
      bg: 'bg-green-100',
      text: 'text-green-800',
      icon: '▲',
      label: 'Alto'
    },
    normal: {
      bg: 'bg-blue-100',
      text: 'text-blue-800',
      icon: '●',
      label: 'Normal'
    },
    bajo: {
      bg: 'bg-yellow-100',
      text: 'text-yellow-800',
      icon: '▼',
      label: 'Bajo'
    },
    critico: {
      bg: 'bg-red-100',
      text: 'text-red-800',
      icon: '⚠',
      label: 'Crítico'
    },
    sin_stock: {
      bg: 'bg-gray-100',
      text: 'text-gray-600',
      icon: '○',
      label: 'Sin Stock'
    },
  };
  return estilos[nivel] || estilos.normal;
};

/**
 * Obtiene los estilos para el badge de estado
 */
export const getEstadoBadgeStyles = (activo) => {
  return {
    bg: activo ? 'bg-green-100' : 'bg-gray-100',
    text: activo ? 'text-green-800' : 'text-gray-600',
  };
};

/**
 * Valida el formulario de producto
 */
export const validarFormularioProducto = (formData) => {
  const errors = {};
  
  if (!formData.clave?.trim()) {
    errors.clave = 'La clave es obligatoria';
  } else if (!/^[A-Za-z0-9-]+$/.test(formData.clave.trim())) {
    errors.clave = 'Solo letras, números y guiones';
  }
  
  if (!formData.nombre?.trim()) {
    errors.nombre = 'El nombre es obligatorio';
  }
  
  if (!formData.unidad_medida) {
    errors.unidad_medida = 'La unidad es obligatoria';
  }
  
  const stockMinimo = Number(formData.stock_minimo);
  if (isNaN(stockMinimo) || stockMinimo < 0) {
    errors.stock_minimo = 'Debe ser un número >= 0';
  }
  
  const stockMaximo = Number(formData.stock_maximo);
  if (isNaN(stockMaximo) || stockMaximo < 0) {
    errors.stock_maximo = 'Debe ser un número >= 0';
  }
  
  if (stockMaximo > 0 && stockMaximo < stockMinimo) {
    errors.stock_maximo = 'Debe ser >= stock mínimo';
  }
  
  return errors;
};

/**
 * Genera productos mock para desarrollo
 */
export const generarProductosMock = (cantidad = 124) => {
  return Array.from({ length: cantidad }).map((_, index) => {
    const id = index + 1;
    const stock = Math.floor(Math.random() * 500);
    const stockMinimo = Math.floor(Math.random() * 50) + 10;
    const activo = index % 9 !== 0;
    
    return {
      id,
      clave: `MED-${String(id).padStart(4, '0')}`,
      nombre: `Producto ${id} - ${['Paracetamol', 'Ibuprofeno', 'Amoxicilina', 'Metformina', 'Omeprazol'][index % 5]} ${index * 10}mg`,
      descripcion: `Descripción del producto ${id}`,
      unidad_medida: UNIDADES[index % UNIDADES.length].value,
      stock_minimo: stockMinimo,
      stock_maximo: stockMinimo * 3,
      stock_actual: stock,
      stock_total: stock,
      inventario_total: stock,
      activo,
      categoria: CATEGORIAS[index % CATEGORIAS.length],
      tipo: 'generico',
      via_administracion: VIAS_ADMINISTRACION[index % VIAS_ADMINISTRACION.length],
      forma_farmaceutica: ['tableta', 'cápsula', 'jarabe', 'inyectable', 'crema'][index % 5],
      presentacion: `${10 * ((index % 5) + 1)} ${UNIDADES[index % UNIDADES.length].label}s`,
      concentracion: `${index * 10}mg`,
      laboratorio: `Laboratorio ${(index % 10) + 1}`,
      registro_sanitario: `RS-${String(id).padStart(6, '0')}`,
      created_at: new Date(Date.now() - id * 86400000).toISOString(),
    };
  });
};

export default {
  UNIDADES,
  CATEGORIAS,
  VIAS_ADMINISTRACION,
  NIVELES_INVENTARIO,
  DEFAULT_FORM,
  isDevSession,
  normalizeText,
  getInventarioDisponible,
  formatInventario,
  calcularNivelStock,
  determinarEstadoProducto,
  getStockBadgeStyles,
  getEstadoBadgeStyles,
  validarFormularioProducto,
  generarProductosMock,
};
