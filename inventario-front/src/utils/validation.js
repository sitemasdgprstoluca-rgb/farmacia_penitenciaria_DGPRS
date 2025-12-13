/**
 * Utilidades de validación para formularios del frontend.
 * 
 * Proporciona funciones de validación reutilizables y mensajes de error
 * estandarizados en español.
 */

// ============================================
// VALIDADORES BÁSICOS
// ============================================

/**
 * Valida que un campo no esté vacío
 */
export const required = (value, fieldName = 'Este campo') => {
  if (value === null || value === undefined || value === '') {
    return `${fieldName} es requerido`;
  }
  if (typeof value === 'string' && value.trim() === '') {
    return `${fieldName} es requerido`;
  }
  return null;
};

/**
 * Valida longitud mínima
 */
export const minLength = (min) => (value, fieldName = 'Este campo') => {
  if (!value) return null; // Si está vacío, usar required
  if (String(value).length < min) {
    return `${fieldName} debe tener al menos ${min} caracteres`;
  }
  return null;
};

/**
 * Valida longitud máxima
 */
export const maxLength = (max) => (value, fieldName = 'Este campo') => {
  if (!value) return null;
  if (String(value).length > max) {
    return `${fieldName} no puede exceder ${max} caracteres`;
  }
  return null;
};

/**
 * Valida formato de email
 */
export const email = (value, fieldName = 'Email') => {
  if (!value) return null;
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(value)) {
    return `${fieldName} no tiene un formato válido`;
  }
  return null;
};

/**
 * Valida que sea un número
 */
export const isNumber = (value, fieldName = 'Este campo') => {
  if (value === null || value === undefined || value === '') return null;
  if (isNaN(Number(value))) {
    return `${fieldName} debe ser un número`;
  }
  return null;
};

/**
 * Valida número mínimo
 */
export const min = (minValue) => (value, fieldName = 'Este campo') => {
  if (value === null || value === undefined || value === '') return null;
  if (Number(value) < minValue) {
    return `${fieldName} debe ser al menos ${minValue}`;
  }
  return null;
};

/**
 * Valida número máximo
 */
export const max = (maxValue) => (value, fieldName = 'Este campo') => {
  if (value === null || value === undefined || value === '') return null;
  if (Number(value) > maxValue) {
    return `${fieldName} no puede ser mayor a ${maxValue}`;
  }
  return null;
};

/**
 * Valida número positivo
 */
export const positive = (value, fieldName = 'Este campo') => {
  if (value === null || value === undefined || value === '') return null;
  if (Number(value) <= 0) {
    return `${fieldName} debe ser mayor a 0`;
  }
  return null;
};

/**
 * Valida número entero
 */
export const integer = (value, fieldName = 'Este campo') => {
  if (value === null || value === undefined || value === '') return null;
  if (!Number.isInteger(Number(value))) {
    return `${fieldName} debe ser un número entero`;
  }
  return null;
};

/**
 * Valida formato de teléfono mexicano
 */
export const phone = (value, fieldName = 'Teléfono') => {
  if (!value) return null;
  const phoneRegex = /^[0-9]{10}$/;
  const cleanValue = String(value).replace(/\D/g, '');
  if (!phoneRegex.test(cleanValue)) {
    return `${fieldName} debe tener 10 dígitos`;
  }
  return null;
};

/**
 * Valida formato de fecha
 */
export const date = (value, fieldName = 'Fecha') => {
  if (!value) return null;
  const dateObj = new Date(value);
  if (isNaN(dateObj.getTime())) {
    return `${fieldName} no es una fecha válida`;
  }
  return null;
};

/**
 * Valida fecha futura
 */
export const futureDate = (value, fieldName = 'Fecha') => {
  if (!value) return null;
  const dateObj = new Date(value);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  if (dateObj < today) {
    return `${fieldName} debe ser una fecha futura`;
  }
  return null;
};

/**
 * Valida fecha pasada
 */
export const pastDate = (value, fieldName = 'Fecha') => {
  if (!value) return null;
  const dateObj = new Date(value);
  const today = new Date();
  today.setHours(23, 59, 59, 999);
  if (dateObj > today) {
    return `${fieldName} debe ser una fecha pasada o actual`;
  }
  return null;
};

// ============================================
// VALIDADORES DE CONTRASEÑA
// ============================================

/**
 * Valida complejidad de contraseña
 */
export const password = (value, fieldName = 'Contraseña') => {
  if (!value) return null;
  
  const errors = [];
  
  if (value.length < 8) {
    errors.push('al menos 8 caracteres');
  }
  if (!/[A-Z]/.test(value)) {
    errors.push('al menos una mayúscula');
  }
  if (!/[a-z]/.test(value)) {
    errors.push('al menos una minúscula');
  }
  if (!/[0-9]/.test(value)) {
    errors.push('al menos un número');
  }
  
  if (errors.length > 0) {
    return `${fieldName} debe tener: ${errors.join(', ')}`;
  }
  return null;
};

/**
 * Valida que dos campos coincidan (para confirmación de contraseña)
 */
export const matches = (otherValue, otherFieldName = 'campo') => (value, fieldName = 'Este campo') => {
  if (!value && !otherValue) return null;
  if (value !== otherValue) {
    return `${fieldName} debe coincidir con ${otherFieldName}`;
  }
  return null;
};

// ============================================
// VALIDADORES DE NEGOCIO
// ============================================

/**
 * Valida formato de clave de producto
 */
export const productKey = (value, fieldName = 'Clave') => {
  if (!value) return null;
  const keyRegex = /^[A-Za-z0-9\-_]+$/;
  if (!keyRegex.test(value)) {
    return `${fieldName} solo puede contener letras, números, guiones y guiones bajos`;
  }
  if (value.length < 3) {
    return `${fieldName} debe tener al menos 3 caracteres`;
  }
  return null;
};

/**
 * Valida formato de número de lote
 */
export const loteNumber = (value, fieldName = 'Número de lote') => {
  if (!value) return null;
  const loteRegex = /^[A-Za-z0-9-]+$/;
  if (!loteRegex.test(value)) {
    return `${fieldName} solo puede contener letras, números y guiones`;
  }
  if (value.length < 3) {
    return `${fieldName} debe tener al menos 3 caracteres`;
  }
  return null;
};

/**
 * Valida cantidad de stock
 */
export const stockQuantity = (value, fieldName = 'Cantidad') => {
  const errors = [];
  
  const numError = isNumber(value, fieldName);
  if (numError) errors.push(numError);
  
  const intError = integer(value, fieldName);
  if (intError) errors.push(intError);
  
  const minError = min(0)(value, fieldName);
  if (minError) errors.push(minError);
  
  return errors.length > 0 ? errors[0] : null;
};

// ============================================
// UTILIDADES DE VALIDACIÓN
// ============================================

/**
 * Combina múltiples validadores
 * 
 * @example
 * const validateName = combine(required, minLength(3), maxLength(50));
 * const error = validateName(value, 'Nombre');
 */
export const combine = (...validators) => (value, fieldName) => {
  for (const validator of validators) {
    const error = validator(value, fieldName);
    if (error) return error;
  }
  return null;
};

/**
 * Valida un objeto completo con un esquema de validación
 * 
 * @example
 * const schema = {
 *   clave: combine(required, productKey),
 *   descripcion: combine(required, minLength(5)),
 *   precio: combine(required, positive),
 * };
 * 
 * const errors = validateSchema(formData, schema);
 * // { clave: null, descripcion: 'Descripción debe tener al menos 5 caracteres', precio: null }
 */
export const validateSchema = (data, schema, fieldLabels = {}) => {
  const errors = {};
  
  for (const [field, validator] of Object.entries(schema)) {
    const value = data[field];
    const label = fieldLabels[field] || field.charAt(0).toUpperCase() + field.slice(1).replace(/_/g, ' ');
    errors[field] = validator(value, label);
  }
  
  return errors;
};

/**
 * Verifica si hay errores en un objeto de errores
 */
export const hasErrors = (errors) => {
  return Object.values(errors).some(error => error !== null && error !== undefined);
};

/**
 * Obtiene el primer error de un objeto de errores
 */
export const getFirstError = (errors) => {
  for (const error of Object.values(errors)) {
    if (error) return error;
  }
  return null;
};

// ============================================
// ESQUEMAS PREDEFINIDOS
// ============================================

export const schemas = {
  producto: {
    clave: combine(required, productKey),
    descripcion: combine(required, minLength(5), maxLength(500)),
    unidad_medida: required,
    precio_unitario: combine(required, positive),
    stock_minimo: combine(required, integer, min(0)),
  },
  
  lote: {
    numero_lote: combine(required, loteNumber),
    fecha_caducidad: combine(required, date, futureDate),
    cantidad_inicial: combine(required, integer, positive),
    producto: required,
  },
  
  requisicion: {
    centro: required,
    observaciones: maxLength(500),
  },
  
  usuario: {
    username: combine(required, minLength(3), maxLength(30)),
    email: combine(required, email),
    password: password,
  },
  
  changePassword: {
    old_password: required,
    new_password: password,
    confirm_password: required,
  },
  
  centro: {
    clave: combine(required, minLength(2), maxLength(20)),
    nombre: combine(required, minLength(3), maxLength(200)),
    telefono: phone,
  },
};

export default {
  // Validadores básicos
  required,
  minLength,
  maxLength,
  email,
  isNumber,
  min,
  max,
  positive,
  integer,
  phone,
  date,
  futureDate,
  pastDate,
  
  // Validadores de contraseña
  password,
  matches,
  
  // Validadores de negocio
  productKey,
  loteNumber,
  stockQuantity,
  
  // Utilidades
  combine,
  validateSchema,
  hasErrors,
  getFirstError,
  
  // Esquemas
  schemas,
};

// ============================================
// EXPORTACIONES ADICIONALES PARA COMPATIBILIDAD
// ============================================

/**
 * Objeto con todos los validadores para importación conveniente
 * @example import { validators } from '@/utils/validation';
 */
export const validators = {
  required,
  minLength,
  maxLength,
  email,
  isNumber,
  numeric: isNumber,
  min,
  max,
  positive,
  positiveNumber: positive,
  integer,
  phone,
  date,
  futureDate,
  pastDate,
  password,
  matches,
  matchField: matches,
  productKey,
  codigoBarras: productKey,
  loteNumber,
  stockQuantity,
  combine,
};

// ============================================
// ISS-003 FIX: VALIDADORES DE DTO PRODUCTO
// Alineados con el backend (backend/inventario/serializers.py)
// ============================================

/**
 * Campos obligatorios para crear/editar producto
 * Basado en el modelo Producto del backend
 */
export const PRODUCTO_CAMPOS_OBLIGATORIOS = ['clave', 'descripcion', 'unidad_medida', 'presentacion'];

/**
 * Valida un producto antes de enviarlo al backend
 * @param {Object} producto - Datos del producto
 * @param {boolean} esEdicion - Si es edición (algunos campos opcionales)
 * @returns {Object} { valido: boolean, errores: Object, primerError: string|null }
 */
export const validarProducto = (producto, esEdicion = false) => {
  const errores = {};
  
  // Campos obligatorios
  if (!producto.clave?.trim()) {
    errores.clave = 'La clave del producto es obligatoria';
  } else if (producto.clave.length < 3) {
    errores.clave = 'La clave debe tener al menos 3 caracteres';
  } else if (!/^[A-Za-z0-9\-_]+$/.test(producto.clave)) {
    errores.clave = 'La clave solo puede contener letras, números, guiones y guiones bajos';
  }
  
  if (!producto.descripcion?.trim() && !producto.nombre?.trim()) {
    errores.descripcion = 'La descripción/nombre del producto es obligatoria';
  } else if ((producto.descripcion || producto.nombre || '').length < 3) {
    errores.descripcion = 'La descripción debe tener al menos 3 caracteres';
  }
  
  if (!producto.unidad_medida?.trim()) {
    errores.unidad_medida = 'La unidad de medida es obligatoria';
  }
  
  if (!producto.presentacion?.trim() && !esEdicion) {
    errores.presentacion = 'La presentación es obligatoria';
  }
  
  // Validar stock_minimo si se proporciona (debe ser >= 0)
  if (producto.stock_minimo !== undefined && producto.stock_minimo !== null && producto.stock_minimo !== '') {
    const minimo = Number(producto.stock_minimo);
    if (isNaN(minimo)) {
      errores.stock_minimo = 'El stock mínimo debe ser un número';
    } else if (minimo < 0) {
      errores.stock_minimo = 'El stock mínimo no puede ser negativo';
    } else if (!Number.isInteger(minimo)) {
      errores.stock_minimo = 'El stock mínimo debe ser un número entero';
    }
  }
  
  // Validar categoría si se proporciona
  const categoriasValidas = ['medicamento', 'material_curacion', 'insumo', 'equipo', 'otro'];
  if (producto.categoria && !categoriasValidas.includes(producto.categoria)) {
    errores.categoria = `Categoría inválida. Opciones: ${categoriasValidas.join(', ')}`;
  }
  
  const valido = Object.keys(errores).length === 0;
  return {
    valido,
    errores,
    primerError: valido ? null : Object.values(errores)[0],
  };
};

/**
 * Normaliza los datos de un producto del backend
 * ISS-003: Asegura tipos correctos y campos consistentes
 * @param {Object} producto - Datos del backend
 * @returns {Object} Producto normalizado
 */
export const normalizarProducto = (producto) => {
  if (!producto) return null;
  
  return {
    ...producto,
    id: producto.id,
    clave: String(producto.clave || ''),
    descripcion: String(producto.descripcion || producto.nombre || ''),
    nombre: String(producto.nombre || producto.descripcion || ''),
    unidad_medida: String(producto.unidad_medida || 'PIEZA'),
    presentacion: String(producto.presentacion || ''),
    categoria: String(producto.categoria || 'medicamento'),
    // Normalizar números
    stock_minimo: Number(producto.stock_minimo) || 0,
    stock_actual: Number(producto.stock_actual ?? producto.stock_total ?? producto.inventario_total ?? 0),
    precio_unitario: Number(producto.precio_unitario) || 0,
    // Booleanos
    activo: producto.activo !== false,
    requiere_receta: producto.requiere_receta === true,
    es_controlado: producto.es_controlado === true,
  };
};

// ============================================
// ISS-004 FIX: VALIDADORES DE REQUISICIÓN
// Validación de stock y transiciones
// ============================================

/**
 * Estados de requisición y transiciones permitidas
 * Basado en backend/core/constants.py
 */
export const ESTADOS_REQUISICION = {
  BORRADOR: 'borrador',
  ENVIADA: 'enviada',
  RECHAZADA: 'rechazada',
  ACEPTADA_PARCIAL: 'aceptada_parcial',
  AUTORIZADA: 'autorizada',
  SURTIDA_PARCIAL: 'surtida_parcial',
  SURTIDA: 'surtida',
  ENTREGADA: 'entregada',
  CANCELADA: 'cancelada',
};

/**
 * Transiciones permitidas por estado
 * ISS-TRANSICIONES FIX: Alineado con FLUJO_REQUISICIONES_V2.md especificación
 * y backend/core/constants.py TRANSICIONES_REQUISICION
 */
export const TRANSICIONES_REQUISICION = {
  // Centro Penitenciario
  borrador: ['pendiente_admin', 'cancelada'],
  pendiente_admin: ['pendiente_director', 'rechazada', 'devuelta'],  // Sin cancelada (spec)
  pendiente_director: ['enviada', 'rechazada', 'devuelta'],  // Sin cancelada (spec)
  
  // Farmacia Central
  enviada: ['en_revision', 'autorizada', 'rechazada'],  // ISS-FIX: Agregar autorizada, quitar cancelada
  en_revision: ['autorizada', 'rechazada', 'devuelta'],  // Sin cancelada (spec)
  autorizada: ['en_surtido', 'surtida', 'cancelada'],  // ISS-FIX: Agregar surtida
  en_surtido: ['surtida', 'cancelada'],  // Sin parcial (spec)
  
  surtida: ['entregada', 'vencida'],  // ISS-002 FIX: NO puede cancelarse
  devuelta: ['pendiente_admin', 'cancelada'],  // ISS-FIX: Regresa a pendiente_admin (spec)
  
  // Estados finales
  entregada: [],
  rechazada: [],
  vencida: [],
  cancelada: [],
};

// Estado interno de surtido parcial (manejado internamente, no expuesto)
export const TRANSICIONES_SURTIDO_INTERNO = {
  parcial: ['en_surtido', 'surtida', 'cancelada'],
};

/**
 * Verifica si una transición de estado es válida
 * @param {string} estadoActual - Estado actual de la requisición
 * @param {string} nuevoEstado - Estado al que se quiere transicionar
 * @returns {boolean}
 */
export const esTransicionValida = (estadoActual, nuevoEstado) => {
  const transicionesPermitidas = TRANSICIONES_REQUISICION[estadoActual?.toLowerCase()];
  if (!transicionesPermitidas) return false;
  return transicionesPermitidas.includes(nuevoEstado?.toLowerCase());
};

/**
 * Obtiene las acciones disponibles para una requisición según su estado y rol
 * @param {string} estado - Estado actual de la requisición
 * @param {string} rol - Rol del usuario (ADMIN, FARMACIA, CENTRO, VISTA)
 * @returns {Array} Lista de acciones permitidas
 */
export const getAccionesPermitidas = (estado, rol) => {
  const estadoLower = estado?.toLowerCase();
  const rolUpper = rol?.toUpperCase();
  
  const acciones = [];
  
  // Acciones por estado y rol
  if (estadoLower === 'borrador') {
    if (['ADMIN', 'FARMACIA', 'CENTRO'].includes(rolUpper)) {
      acciones.push('enviar', 'editar', 'eliminar');
    }
  } else if (estadoLower === 'enviada') {
    if (['ADMIN', 'FARMACIA'].includes(rolUpper)) {
      acciones.push('aceptar', 'rechazar');
    }
  } else if (estadoLower === 'aceptada_parcial') {
    if (['ADMIN', 'FARMACIA'].includes(rolUpper)) {
      acciones.push('autorizar', 'rechazar');
    }
  } else if (estadoLower === 'autorizada') {
    if (['ADMIN', 'FARMACIA'].includes(rolUpper)) {
      acciones.push('surtir', 'rechazar');
    }
  } else if (estadoLower === 'surtida_parcial') {
    if (['ADMIN', 'FARMACIA'].includes(rolUpper)) {
      acciones.push('surtir', 'cancelar');
    }
  } else if (estadoLower === 'surtida') {
    if (['ADMIN', 'FARMACIA', 'CENTRO'].includes(rolUpper)) {
      acciones.push('confirmar_entrega');
    }
  }
  
  // Ver siempre está disponible
  acciones.push('ver');
  
  return acciones;
};

/**
 * Valida un item de requisición contra stock disponible
 * @param {Object} item - { lote_id, cantidad, ... }
 * @param {Object} lote - Datos del lote con stock actual
 * @returns {Object} { valido: boolean, error: string|null }
 */
export const validarItemContraStock = (item, lote) => {
  if (!item || !lote) {
    return { valido: false, error: 'Datos incompletos' };
  }
  
  const cantidad = Number(item.cantidad);
  const stockDisponible = Number(lote.stock_actual ?? lote.cantidad_disponible ?? lote.cantidad ?? 0);
  
  if (isNaN(cantidad) || cantidad <= 0) {
    return { valido: false, error: 'La cantidad debe ser un número mayor a 0' };
  }
  
  if (!Number.isInteger(cantidad)) {
    return { valido: false, error: 'La cantidad debe ser un número entero' };
  }
  
  if (cantidad > stockDisponible) {
    return { 
      valido: false, 
      error: `Stock insuficiente. Disponible: ${stockDisponible}, Solicitado: ${cantidad}` 
    };
  }
  
  // Validar caducidad
  if (lote.fecha_caducidad) {
    const fechaCaducidad = new Date(lote.fecha_caducidad);
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    
    if (fechaCaducidad < hoy) {
      return { valido: false, error: 'El lote ya caducó' };
    }
    
    // Advertencia si caduca pronto (30 días)
    const diasRestantes = Math.ceil((fechaCaducidad - hoy) / (1000 * 60 * 60 * 24));
    if (diasRestantes <= 30) {
      return { 
        valido: true, 
        advertencia: `El lote caduca en ${diasRestantes} días` 
      };
    }
  }
  
  return { valido: true, error: null };
};

/**
 * Valida todos los items de una requisición
 * @param {Array} items - Lista de items
 * @param {Object} lotesMap - Mapa de lote_id -> lote con stock
 * @returns {Object} { valido: boolean, errores: Array, advertencias: Array }
 */
export const validarItemsRequisicion = (items, lotesMap = {}) => {
  const errores = [];
  const advertencias = [];
  
  if (!items || items.length === 0) {
    return { valido: false, errores: ['La requisición debe tener al menos un item'], advertencias };
  }
  
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const lote = lotesMap[item.lote_id] || lotesMap[item.lote] || item.lote_data;
    
    if (!lote) {
      errores.push(`Item ${i + 1}: No se encontró información del lote`);
      continue;
    }
    
    const resultado = validarItemContraStock(item, lote);
    if (!resultado.valido) {
      errores.push(`Item ${i + 1} (${lote.producto_nombre || lote.numero_lote || 'sin nombre'}): ${resultado.error}`);
    }
    if (resultado.advertencia) {
      advertencias.push(`Item ${i + 1}: ${resultado.advertencia}`);
    }
  }
  
  return {
    valido: errores.length === 0,
    errores,
    advertencias,
  };
};

/**
 * Alias para schemas como validationSchemas
 */
export const validationSchemas = schemas;

/**
 * Valida un campo individual con múltiples reglas
 */
export const validateField = (value, rules, fieldName = 'Campo') => {
  for (const rule of rules) {
    const error = rule(value, fieldName);
    if (error) return error;
  }
  return null;
};

/**
 * Valida un formulario completo con reglas por campo
 */
export const validateForm = (values, rules) => {
  const errors = {};
  for (const [fieldName, fieldRules] of Object.entries(rules)) {
    const error = validateField(values[fieldName], fieldRules, fieldName);
    if (error) {
      errors[fieldName] = error;
    }
  }
  return errors;
};

/**
 * Sanitiza input eliminando espacios extra y caracteres peligrosos
 */
export const sanitizeInput = (value) => {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\s+/g, ' ')
    .trim();
};

/**
 * Obtiene el error de un campo específico
 */
export const getFieldError = (errors, fieldName) => {
  return errors[fieldName];
};

/**
 * Combina múltiples validadores en uno solo
 */
export const combineValidators = (...validators) => (value, fieldName) => {
  for (const validator of validators) {
    const error = validator(value, fieldName);
    if (error) return error;
  }
  return null;
};
