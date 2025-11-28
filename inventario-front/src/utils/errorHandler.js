/**
 * Utilidades para manejo global de errores en el frontend.
 * 
 * Proporciona funciones para:
 * - Parsear errores de API
 * - Mostrar errores de forma amigable
 * - Logging de errores
 */

import { toast } from 'react-hot-toast';

// ============================================
// TIPOS DE ERROR
// ============================================

export const ERROR_TYPES = {
  NETWORK: 'NETWORK',
  AUTHENTICATION: 'AUTHENTICATION',
  AUTHORIZATION: 'AUTHORIZATION',
  VALIDATION: 'VALIDATION',
  NOT_FOUND: 'NOT_FOUND',
  SERVER: 'SERVER',
  UNKNOWN: 'UNKNOWN',
};

// ============================================
// MENSAJES DE ERROR PREDEFINIDOS
// ============================================

const ERROR_MESSAGES = {
  [ERROR_TYPES.NETWORK]: 'Error de conexión. Verifica tu conexión a internet.',
  [ERROR_TYPES.AUTHENTICATION]: 'Sesión expirada. Por favor, inicia sesión nuevamente.',
  [ERROR_TYPES.AUTHORIZATION]: 'No tienes permisos para realizar esta acción.',
  [ERROR_TYPES.VALIDATION]: 'Por favor, verifica los datos ingresados.',
  [ERROR_TYPES.NOT_FOUND]: 'El recurso solicitado no fue encontrado.',
  [ERROR_TYPES.SERVER]: 'Error en el servidor. Por favor, intenta más tarde.',
  [ERROR_TYPES.UNKNOWN]: 'Ocurrió un error inesperado.',
};

// ============================================
// FUNCIONES DE PARSING
// ============================================

/**
 * Determina el tipo de error basado en la respuesta
 */
export const getErrorType = (error) => {
  if (!error.response) {
    return ERROR_TYPES.NETWORK;
  }
  
  const status = error.response.status;
  
  if (status === 401) return ERROR_TYPES.AUTHENTICATION;
  if (status === 403) return ERROR_TYPES.AUTHORIZATION;
  if (status === 404) return ERROR_TYPES.NOT_FOUND;
  if (status === 400 || status === 422) return ERROR_TYPES.VALIDATION;
  if (status >= 500) return ERROR_TYPES.SERVER;
  
  return ERROR_TYPES.UNKNOWN;
};

/**
 * Extrae el mensaje de error de una respuesta de API
 */
export const parseApiError = (error) => {
  // Error de red (sin respuesta)
  if (!error.response) {
    return {
      type: ERROR_TYPES.NETWORK,
      message: ERROR_MESSAGES[ERROR_TYPES.NETWORK],
      details: error.message,
    };
  }
  
  const { status, data } = error.response;
  const type = getErrorType(error);
  
  // Intentar extraer mensaje de diferentes formatos de respuesta
  let message = ERROR_MESSAGES[type];
  let details = null;
  let fieldErrors = null;
  
  if (data) {
    // Formato: { message: "..." } o { error: "..." } o { detail: "..." }
    if (typeof data === 'string') {
      message = data;
    } else if (data.message) {
      message = data.message;
    } else if (data.error) {
      message = data.error;
    } else if (data.detail) {
      message = data.detail;
    } else if (data.non_field_errors) {
      message = Array.isArray(data.non_field_errors) 
        ? data.non_field_errors.join('. ')
        : data.non_field_errors;
    }
    
    // Errores de validación por campo (DRF)
    if (type === ERROR_TYPES.VALIDATION && typeof data === 'object') {
      fieldErrors = {};
      for (const [key, value] of Object.entries(data)) {
        if (key !== 'message' && key !== 'error' && key !== 'detail') {
          fieldErrors[key] = Array.isArray(value) ? value.join('. ') : value;
        }
      }
      if (Object.keys(fieldErrors).length === 0) {
        fieldErrors = null;
      }
    }
    
    // Detalles adicionales
    if (data.details || data.detalles) {
      details = data.details || data.detalles;
    }
  }
  
  return {
    type,
    status,
    message,
    details,
    fieldErrors,
    originalError: error,
  };
};

// ============================================
// FUNCIONES DE DISPLAY
// ============================================

/**
 * Muestra un error con toast
 * @param {Error|Object} error - Error de axios o error parseado
 * @param {Object} options - Opciones adicionales
 */
export const showError = (error, options = {}) => {
  const {
    defaultMessage = null,
    showFieldErrors = true,
    duration = 4000,
  } = options;
  
  // Si ya es un error parseado, usarlo directamente
  const parsedError = error.type ? error : parseApiError(error);
  
  // Usar mensaje por defecto si se proporciona
  const message = defaultMessage || parsedError.message;
  
  // No mostrar errores de autenticación (se manejan globalmente)
  if (parsedError.type === ERROR_TYPES.AUTHENTICATION) {
    return;
  }
  
  // Mostrar toast principal
  toast.error(message, { duration });
  
  // Mostrar errores de campo si es validación
  if (showFieldErrors && parsedError.fieldErrors) {
    const fieldMessages = Object.entries(parsedError.fieldErrors)
      .map(([field, msg]) => `${formatFieldName(field)}: ${msg}`)
      .slice(0, 3); // Máximo 3 errores de campo
    
    if (fieldMessages.length > 0) {
      setTimeout(() => {
        toast(fieldMessages.join('\n'), {
          duration: duration + 1000,
          icon: '⚠️',
        });
      }, 500);
    }
  }
  
  return parsedError;
};

/**
 * Muestra un mensaje de éxito
 */
export const showSuccess = (message, options = {}) => {
  const { duration = 3000 } = options;
  toast.success(message, { duration });
};

/**
 * Muestra un mensaje informativo
 */
export const showInfo = (message, options = {}) => {
  const { duration = 3000 } = options;
  toast(message, { duration, icon: 'ℹ️' });
};

/**
 * Muestra un mensaje de advertencia
 */
export const showWarning = (message, options = {}) => {
  const { duration = 4000 } = options;
  toast(message, { duration, icon: '⚠️' });
};

// ============================================
// UTILIDADES
// ============================================

/**
 * Formatea un nombre de campo para mostrar
 */
export const formatFieldName = (fieldName) => {
  const fieldLabels = {
    clave: 'Clave',
    descripcion: 'Descripción',
    precio_unitario: 'Precio unitario',
    stock_minimo: 'Inventario mínimo',
    numero_lote: 'Número de lote',
    fecha_caducidad: 'Fecha de caducidad',
    cantidad_inicial: 'Cantidad inicial',
    cantidad_actual: 'Cantidad actual',
    cantidad_solicitada: 'Cantidad solicitada',
    cantidad_autorizada: 'Cantidad autorizada',
    unidad_medida: 'Unidad de medida',
    old_password: 'Contraseña actual',
    new_password: 'Nueva contraseña',
    confirm_password: 'Confirmar contraseña',
    username: 'Usuario',
    email: 'Correo electrónico',
    first_name: 'Nombre',
    last_name: 'Apellidos',
    telefono: 'Teléfono',
    direccion: 'Dirección',
    responsable: 'Responsable',
    centro: 'Centro',
    producto: 'Producto',
    lote: 'Lote',
    non_field_errors: 'Error general',
  };
  
  return fieldLabels[fieldName] || fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

/**
 * Wrapper para llamadas API con manejo de errores automático
 * 
 * @example
 * const result = await handleApiCall(
 *   () => productosAPI.create(data),
 *   {
 *     successMessage: 'Producto creado exitosamente',
 *     errorMessage: 'Error al crear producto',
 *   }
 * );
 * if (result.success) {
 *   // ...
 * }
 */
export const handleApiCall = async (apiCall, options = {}) => {
  const {
    successMessage = null,
    errorMessage = null,
    showSuccessToast = true,
    showErrorToast = true,
    onSuccess = null,
    onError = null,
  } = options;
  
  try {
    const response = await apiCall();
    
    if (showSuccessToast && successMessage) {
      showSuccess(successMessage);
    }
    
    if (onSuccess) {
      onSuccess(response);
    }
    
    return {
      success: true,
      data: response.data,
      response,
    };
  } catch (error) {
    const parsedError = parseApiError(error);
    
    if (showErrorToast) {
      showError(parsedError, { defaultMessage: errorMessage });
    }
    
    if (onError) {
      onError(parsedError);
    }
    
    // Log para debugging
    console.error('API Error:', {
      type: parsedError.type,
      message: parsedError.message,
      details: parsedError.details,
      fieldErrors: parsedError.fieldErrors,
    });
    
    return {
      success: false,
      error: parsedError,
    };
  }
};

/**
 * Hook-friendly error state management
 */
export const createErrorState = () => {
  return {
    error: null,
    fieldErrors: {},
    
    setError: function(error) {
      const parsed = error.type ? error : parseApiError(error);
      this.error = parsed.message;
      this.fieldErrors = parsed.fieldErrors || {};
      return parsed;
    },
    
    clearError: function() {
      this.error = null;
      this.fieldErrors = {};
    },
    
    getFieldError: function(field) {
      return this.fieldErrors[field] || null;
    },
    
    hasErrors: function() {
      return this.error !== null || Object.keys(this.fieldErrors).length > 0;
    },
  };
};

export default {
  ERROR_TYPES,
  getErrorType,
  parseApiError,
  showError,
  showSuccess,
  showInfo,
  showWarning,
  formatFieldName,
  handleApiCall,
  createErrorState,
};
