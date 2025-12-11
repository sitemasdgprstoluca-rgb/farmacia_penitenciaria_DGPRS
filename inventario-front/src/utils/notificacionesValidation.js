/**
 * ISS-005 FIX: Validación de shape para respuestas de notificaciones
 * Asegura que la respuesta del servidor tenga la estructura esperada
 */

/**
 * Shape esperado de una notificación individual
 * @typedef {Object} Notificacion
 * @property {number} id - ID único
 * @property {string} tipo - Tipo de notificación
 * @property {string} mensaje - Mensaje de la notificación
 * @property {boolean} leida - Si fue leída
 * @property {string} created_at - Fecha de creación
 */

/**
 * Shape esperado de la respuesta de lista de notificaciones
 * @typedef {Object} NotificacionesListResponse
 * @property {Notificacion[]} results - Lista de notificaciones
 * @property {number} count - Total de notificaciones
 * @property {string|null} next - URL de siguiente página
 * @property {string|null} previous - URL de página anterior
 */

/**
 * Shape esperado de la respuesta de conteo de no leídas
 * @typedef {Object} NotificacionesCountResponse
 * @property {number} no_leidas - Cantidad de notificaciones no leídas
 */

/**
 * Valida que un objeto sea una notificación válida
 * @param {*} obj - Objeto a validar
 * @returns {{ valido: boolean, errores: string[] }}
 */
export const validarNotificacion = (obj) => {
  const errores = [];
  
  if (!obj || typeof obj !== 'object') {
    return { valido: false, errores: ['La notificación debe ser un objeto'] };
  }

  if (typeof obj.id !== 'number' && typeof obj.id !== 'string') {
    errores.push('id debe ser un número o string');
  }

  if (typeof obj.tipo !== 'string' && obj.tipo !== undefined) {
    errores.push('tipo debe ser una cadena');
  }

  if (typeof obj.mensaje !== 'string' && obj.message !== 'string') {
    errores.push('mensaje debe ser una cadena');
  }

  if (typeof obj.leida !== 'boolean' && obj.leida !== undefined) {
    errores.push('leida debe ser un booleano');
  }

  return { valido: errores.length === 0, errores };
};

/**
 * Valida la respuesta de lista de notificaciones
 * @param {*} response - Respuesta del servidor
 * @returns {{ valido: boolean, data: NotificacionesListResponse|null, errores: string[] }}
 */
export const validarNotificacionesListResponse = (response) => {
  const errores = [];
  
  if (!response || typeof response !== 'object') {
    return { valido: false, data: null, errores: ['Respuesta inválida'] };
  }

  // Puede ser un array directo o un objeto paginado
  if (Array.isArray(response)) {
    // Respuesta es un array directo de notificaciones
    return {
      valido: true,
      data: {
        results: response,
        count: response.length,
        next: null,
        previous: null,
      },
      errores: [],
    };
  }

  // Respuesta paginada estándar de DRF
  if (Array.isArray(response.results)) {
    return {
      valido: true,
      data: {
        results: response.results,
        count: response.count ?? response.results.length,
        next: response.next ?? null,
        previous: response.previous ?? null,
      },
      errores: [],
    };
  }

  // Otros formatos posibles
  if (Array.isArray(response.data)) {
    return {
      valido: true,
      data: {
        results: response.data,
        count: response.total ?? response.count ?? response.data.length,
        next: null,
        previous: null,
      },
      errores: [],
    };
  }

  errores.push('Formato de respuesta no reconocido');
  return { valido: false, data: null, errores };
};

/**
 * Valida la respuesta de conteo de notificaciones no leídas
 * @param {*} response - Respuesta del servidor
 * @returns {{ valido: boolean, count: number, errores: string[] }}
 */
export const validarNotificacionesCountResponse = (response) => {
  const errores = [];
  
  if (!response || typeof response !== 'object') {
    return { valido: false, count: 0, errores: ['Respuesta inválida'] };
  }

  // Intentar extraer el conteo de varias posibles propiedades
  const count = 
    response.no_leidas ?? 
    response.unread ?? 
    response.unread_count ??
    response.total ?? 
    response.count ?? 
    0;

  if (typeof count !== 'number' || count < 0) {
    errores.push('Conteo inválido');
    return { valido: false, count: 0, errores };
  }

  return { valido: true, count, errores: [] };
};

/**
 * Normaliza una notificación a un formato estándar
 * @param {Object} raw - Notificación cruda del servidor
 * @returns {Notificacion}
 */
export const normalizarNotificacion = (raw) => {
  return {
    id: raw.id,
    tipo: raw.tipo || raw.type || 'info',
    mensaje: raw.mensaje || raw.message || raw.titulo || '',
    titulo: raw.titulo || raw.title || '',
    leida: raw.leida ?? raw.read ?? false,
    created_at: raw.created_at || raw.createdAt || raw.fecha || new Date().toISOString(),
    data: raw.data || raw.extra || {},
    // Campos adicionales que puedan existir
    prioridad: raw.prioridad || raw.priority || 'normal',
    enlace: raw.enlace || raw.link || null,
  };
};

export default {
  validarNotificacion,
  validarNotificacionesListResponse,
  validarNotificacionesCountResponse,
  normalizarNotificacion,
};
