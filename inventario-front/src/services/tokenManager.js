/**
 * Módulo de gestión segura de tokens JWT
 * 
 * SEGURIDAD:
 * - Access Token: Almacenado SOLO en memoria (variable de módulo)
 * - Refresh Token: Almacenado en cookie HttpOnly por el servidor
 * - NO se usa localStorage para tokens (vulnerable a XSS)
 * 
 * Este módulo proporciona funciones para:
 * - Almacenar/recuperar access token en memoria
 * - Limpiar tokens en logout
 * - Verificar si hay sesión activa
 */

// Access token almacenado SOLO en memoria (no persiste entre pestañas ni recargas)
let accessToken = null;

// Callbacks para notificar cambios de sesión
let onSessionChangeCallbacks = [];

/**
 * Almacena el access token en memoria
 * @param {string} token - El access token JWT
 */
export const setAccessToken = (token) => {
  accessToken = token;
  notifySessionChange(!!token);
};

/**
 * Obtiene el access token desde memoria
 * @returns {string|null} El access token o null si no existe
 */
export const getAccessToken = () => {
  return accessToken;
};

/**
 * Verifica si hay un access token almacenado
 * @returns {boolean} true si hay token, false si no
 */
export const hasAccessToken = () => {
  return !!accessToken;
};

/**
 * Limpia todos los tokens (logout)
 */
export const clearTokens = () => {
  accessToken = null;
  notifySessionChange(false);
};

/**
 * Registra un callback para cambios de sesión
 * @param {Function} callback - Función a llamar cuando cambie el estado de sesión
 * @returns {Function} Función para desregistrar el callback
 */
export const onSessionChange = (callback) => {
  onSessionChangeCallbacks.push(callback);
  return () => {
    onSessionChangeCallbacks = onSessionChangeCallbacks.filter(cb => cb !== callback);
  };
};

/**
 * Notifica a todos los callbacks registrados sobre un cambio de sesión
 * @param {boolean} isAuthenticated - Estado de autenticación
 */
const notifySessionChange = (isAuthenticated) => {
  onSessionChangeCallbacks.forEach(callback => {
    try {
      callback(isAuthenticated);
    } catch (error) {
      console.error('Error en callback de sesión:', error);
    }
  });
};

/**
 * Migración desde localStorage (para usuarios existentes)
 * Solo debe ejecutarse una vez al cargar la app
 */
export const migrateFromLocalStorage = () => {
  const oldToken = localStorage.getItem('token');
  if (oldToken) {
    // Intentar usar el token existente
    accessToken = oldToken;
    // Limpiar localStorage por seguridad
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    console.info('Tokens migrados desde localStorage a memoria');
    return true;
  }
  return false;
};

/**
 * Debug: obtiene el estado actual de los tokens (sin valores sensibles)
 * @returns {Object} Estado de los tokens
 */
export const getTokenStatus = () => {
  return {
    hasAccessToken: !!accessToken,
    accessTokenLength: accessToken?.length || 0,
  };
};

export default {
  setAccessToken,
  getAccessToken,
  hasAccessToken,
  clearTokens,
  onSessionChange,
  migrateFromLocalStorage,
  getTokenStatus,
};
