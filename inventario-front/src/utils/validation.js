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
