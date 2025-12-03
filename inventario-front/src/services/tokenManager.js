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

// ISS-003: Flag para bloquear refresh después de logout iniciado
// Esto previene que el interceptor intente refresh con una cookie que puede existir
// pero que el usuario ya intentó invalidar
let logoutInProgress = false;

// Callbacks para notificar cambios de sesión
let onSessionChangeCallbacks = [];

/**
 * Almacena el access token en memoria
 * @param {string} token - El access token JWT
 */
export const setAccessToken = (token) => {
  accessToken = token;
  // Si recibimos un token válido, resetear el flag de logout
  if (token) {
    logoutInProgress = false;
  }
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
 * ISS-003: Marca que el logout está en progreso
 * Esto bloquea intentos de refresh automático
 */
export const setLogoutInProgress = (inProgress) => {
  logoutInProgress = inProgress;
};

/**
 * ISS-003: Verifica si el logout está en progreso
 * @returns {boolean} true si hay logout en progreso
 */
export const isLogoutInProgress = () => {
  return logoutInProgress;
};

/**
 * Limpia todos los tokens (logout)
 */
export const clearTokens = () => {
  accessToken = null;
  logoutInProgress = true; // Bloquear refresh hasta nuevo login
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
 * Decodifica un JWT sin verificar firma (solo para leer payload)
 * @param {string} token - Token JWT
 * @returns {Object|null} Payload decodificado o null si inválido
 */
const decodeJWT = (token) => {
  try {
    if (!token || typeof token !== 'string') return null;
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    
    const payload = parts[1];
    // Decodificar base64url
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (e) {
    console.warn('Error decodificando JWT:', e);
    return null;
  }
};

/**
 * Verifica si un token JWT está expirado
 * @param {string} token - Token JWT
 * @returns {boolean} true si está expirado o es inválido
 */
const isTokenExpired = (token) => {
  const payload = decodeJWT(token);
  if (!payload || !payload.exp) return true;
  
  // Agregar margen de 30 segundos para evitar race conditions
  const now = Math.floor(Date.now() / 1000);
  return payload.exp < (now + 30);
};

/**
 * Migración desde localStorage (para usuarios existentes)
 * Solo debe ejecutarse una vez al cargar la app
 * 
 * SEGURIDAD (ISS-004): Valida el token antes de usarlo
 * - Verifica estructura JWT válida
 * - Verifica que no esté expirado
 * - Descarta tokens inválidos
 */
export const migrateFromLocalStorage = () => {
  const oldToken = localStorage.getItem('token');
  if (oldToken) {
    // Limpiar localStorage primero por seguridad
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    
    // Validar token antes de usarlo (ISS-004)
    const payload = decodeJWT(oldToken);
    
    if (!payload) {
      console.warn('Token migrado inválido (no es JWT válido), descartado');
      return false;
    }
    
    if (isTokenExpired(oldToken)) {
      console.warn('Token migrado expirado, descartado');
      return false;
    }
    
    // Token válido y no expirado, usar temporalmente
    accessToken = oldToken;
    console.info('Token migrado y validado desde localStorage a memoria');
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
  setLogoutInProgress,
  isLogoutInProgress,
};
