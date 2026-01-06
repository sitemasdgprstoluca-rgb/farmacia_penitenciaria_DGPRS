/**
 * API Client con gestión segura de tokens
 * 
 * SEGURIDAD:
 * - Access Token: En memoria (tokenManager)
 * - Refresh Token: En cookie HttpOnly (manejado por el servidor)
 * - Refresh automático transparente
 */

import axios from 'axios';
import { toast } from 'react-hot-toast';
import { 
  getAccessToken, 
  setAccessToken, 
  clearTokens,
  isLogoutInProgress,
  setRefreshInProgress,
} from './tokenManager';

// === CONFIGURACIÓN DE BASE URL CON VALIDACIÓN DE SEGURIDAD (ISS-001, ISS-005) ===
const configuredUrl = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL;
const isDev = import.meta.env.DEV || import.meta.env.MODE === 'development';
// ISS-001 FIX: En producción, HTTPS es OBLIGATORIO sin bypass
// VITE_ALLOW_INSECURE_HTTP solo está disponible en desarrollo para testing local
const allowInsecureHttp = isDev && import.meta.env.VITE_ALLOW_INSECURE_HTTP === 'true';

// Flag para detectar configuración inválida
let apiConfigError = null;
let httpInsecureError = false;
let httpInsecureWarning = false;

// ISS-001 FIX (audit33): Validación centralizada de TODAS las variables críticas
const validateEnvConfig = () => {
  const errors = [];
  const warnings = [];
  
  // Variables críticas obligatorias en producción
  if (!isDev) {
    if (!configuredUrl) {
      errors.push({
        variable: 'VITE_API_URL',
        mensaje: 'La URL de la API no está configurada',
        accion: 'Configure VITE_API_URL en el archivo .env o en las variables de entorno del servidor',
      });
    } else if (!configuredUrl.startsWith('https://')) {
      errors.push({
        variable: 'VITE_API_URL',
        mensaje: 'La API debe usar HTTPS en producción',
        accion: 'Configure VITE_API_URL con una URL que comience con https://',
      });
    }
  }
  
  // Validar consistencia de variables opcionales
  const apiVersion = import.meta.env.VITE_API_VERSION;
  if (apiVersion && !/^v?\d+(\.\d+)?$/.test(apiVersion)) {
    warnings.push({
      variable: 'VITE_API_VERSION',
      mensaje: `Formato de versión inusual: "${apiVersion}"`,
      accion: 'Use un formato como "v1" o "1.0"',
    });
  }
  
  const healthTimeout = import.meta.env.VITE_HEALTHCHECK_TIMEOUT;
  if (healthTimeout && (isNaN(parseInt(healthTimeout)) || parseInt(healthTimeout) < 1000)) {
    warnings.push({
      variable: 'VITE_HEALTHCHECK_TIMEOUT',
      mensaje: 'Timeout de healthcheck muy bajo o inválido',
      accion: 'Configure un valor en milisegundos >= 1000 (ej: 5000)',
    });
  }
  
  return { errors, warnings };
};

// ISS-001: Ejecutar validación al cargar
const envValidation = validateEnvConfig();
export const getEnvValidation = () => envValidation;
export const hasEnvErrors = () => envValidation.errors.length > 0;
export const getEnvErrors = () => envValidation.errors;
export const getEnvWarnings = () => envValidation.warnings;

// ISS-001 FIX: Métricas de configuración insegura (solo en desarrollo)
const securityMetrics = {
  httpAttempts: 0,
  configErrors: 0,
  lastError: null,
  
  recordHttpAttempt() {
    this.httpAttempts++;
    this.lastError = new Date().toISOString();
    if (isDev) {
      console.warn(`[SECURITY METRIC] HTTP attempt #${this.httpAttempts}`);
    }
  },
  
  recordConfigError(error) {
    this.configErrors++;
    this.lastError = new Date().toISOString();
    console.error(`[SECURITY METRIC] Config error #${this.configErrors}: ${error}`);
  },
  
  getMetrics() {
    return { ...this };
  }
};

// Determinar baseURL
let apiBaseUrl;
if (configuredUrl) {
  apiBaseUrl = configuredUrl.replace(/\/+$/, '');
} else if (isDev) {
  // Solo permitir HTTP localhost en desarrollo
  apiBaseUrl = 'http://127.0.0.1:8000/api';
  console.info('[API] Modo desarrollo: usando', apiBaseUrl);
} else {
  // ISS-001 FIX: En producción, ABORTAR si VITE_API_URL falta
  apiConfigError = 'ERROR DE CONFIGURACIÓN: La variable VITE_API_URL no está definida. ' +
    'La aplicación no puede iniciar sin una URL de API válida.';
  securityMetrics.recordConfigError('VITE_API_URL no definida en producción');
  console.error(
    '[API] ⛔ ABORTO CRÍTICO: VITE_API_URL no está configurada en producción. ' +
    'Configure la variable de entorno VITE_API_URL con una URL HTTPS válida.'
  );
  // Usar placeholder que fallará de forma evidente
  apiBaseUrl = 'https://api-no-configurada.error';
}

// ISS-001 FIX: HTTPS OBLIGATORIO en producción - SIN BYPASS
if (!isDev && apiBaseUrl && !apiBaseUrl.startsWith('https://')) {
  // Bloquear HTTP en producción SIEMPRE
  httpInsecureError = true;
  apiConfigError = 'ERROR DE SEGURIDAD: La API debe usar HTTPS en producción. ' +
    'Los datos y credenciales no están protegidos. Contacte al administrador.';
  securityMetrics.recordHttpAttempt();
  console.error(
    '[API] ⛔ BLOQUEADO: Intento de usar HTTP en producción. ' +
    'Esto expone tokens y datos sensibles. URL actual:', apiBaseUrl
  );
} else if (isDev && allowInsecureHttp && apiBaseUrl && !apiBaseUrl.startsWith('https://')) {
  // Solo en desarrollo: permitir HTTP con advertencia visible
  httpInsecureWarning = true;
  securityMetrics.recordHttpAttempt();
  console.warn(
    '[API] ⚠️ ADVERTENCIA DEV: Usando HTTP sin cifrado. ' +
    'Esto está permitido SOLO en desarrollo.'
  );
}

// Exportar métricas de seguridad para monitoreo
export const getSecurityMetrics = () => securityMetrics.getMetrics();

// ISS-001 FIX: Configuración de healthcheck parametrizable
const API_VERSION = import.meta.env.VITE_API_VERSION || 'v1';
const HEALTH_ENDPOINT = import.meta.env.VITE_HEALTH_ENDPOINT || '/health/';
const HEALTH_CHECK_ENABLED = import.meta.env.VITE_ENABLE_HEALTHCHECK !== 'false';
// ISS-FIX: Aumentar timeout default a 60s para cold starts de Render (free tier tarda ~50s)
const HEALTH_TIMEOUT = parseInt(import.meta.env.VITE_HEALTHCHECK_TIMEOUT || '60000', 10);
const AUTH_ONLY_MODE = import.meta.env.VITE_AUTH_ONLY_MODE === 'true'; // Modo sin healthcheck
// ISS-FIX: Configuración de reintentos para cold starts - aumentado a 5 reintentos
const HEALTH_RETRIES = parseInt(import.meta.env.VITE_HEALTHCHECK_RETRIES || '5', 10);
const HEALTH_RETRY_DELAY = parseInt(import.meta.env.VITE_HEALTHCHECK_RETRY_DELAY || '3000', 10);

// ISS-003 FIX (audit33): Configuración parametrizable de rutas de autenticación
const AUTH_CONFIG = {
  tokenEndpoint: import.meta.env.VITE_TOKEN_ENDPOINT || '/token/',
  refreshEndpoint: import.meta.env.VITE_REFRESH_ENDPOINT || '/token/refresh/',
  logoutEndpoint: import.meta.env.VITE_LOGOUT_ENDPOINT || '/logout/',
  // ISS-003: Campo de access token en respuesta (puede variar por backend)
  accessTokenField: import.meta.env.VITE_ACCESS_TOKEN_FIELD || 'access',
  refreshTokenField: import.meta.env.VITE_REFRESH_TOKEN_FIELD || 'refresh',
  // ISS-003: Modo de envío del refresh token
  refreshInCookie: import.meta.env.VITE_REFRESH_IN_COOKIE !== 'false', // Default: cookie HttpOnly
  refreshInBody: import.meta.env.VITE_REFRESH_IN_BODY === 'true', // Alternativo: body
};

// ISS-003: Exportar configuración para debugging
export const getAuthConfig = () => ({ ...AUTH_CONFIG });

let apiHealthy = null; // null = no verificado, true = ok, false = fallo
let healthCheckSkipped = false; // Si se saltó por configuración

/**
 * ISS-FIX: Helper para esperar con delay (usado en reintentos)
 */
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * ISS-001 FIX: Verificar conectividad y compatibilidad con el backend
 * Parametrizable via VITE_HEALTH_ENDPOINT y VITE_ENABLE_HEALTHCHECK
 * Degrada elegantemente si el endpoint no existe (404)
 * ISS-FIX: Añadido soporte para reintentos automáticos (cold starts de Render)
 * 
 * @param {Object} options - Opciones de configuración
 * @param {boolean} options.force - Forzar verificación aunque AUTH_ONLY_MODE esté activo
 * @param {number} options.retries - Número de reintentos (default: HEALTH_RETRIES)
 * @returns {Promise<Object>} Estado del backend
 */
export const checkApiHealth = async (options = {}) => {
  // Si hay error de configuración, retornar inmediatamente
  if (apiConfigError) {
    return { healthy: false, error: apiConfigError, version: null, skipped: false };
  }
  
  // ISS-001: Modo solo autenticación - saltar healthcheck
  if ((AUTH_ONLY_MODE || !HEALTH_CHECK_ENABLED) && !options.force) {
    healthCheckSkipped = true;
    apiHealthy = true; // Asumir saludable en modo auth-only
    if (isDev) {
      console.info('[API] Health check deshabilitado (AUTH_ONLY_MODE o ENABLE_HEALTHCHECK=false)');
    }
    return {
      healthy: true,
      skipped: true,
      mode: 'auth-only',
      version: API_VERSION,
      timestamp: new Date().toISOString(),
    };
  }
  
  const maxRetries = options.retries ?? HEALTH_RETRIES;
  let lastError = null;
  
  // ISS-FIX: Intentar con reintentos para manejar cold starts
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      if (attempt > 0) {
        // Silenciado para no confundir usuarios - solo en desarrollo
        if (isDev) console.debug(`[API] Health check reintento ${attempt}/${maxRetries}...`);
        await sleep(HEALTH_RETRY_DELAY * attempt); // Backoff exponencial simple
      }
      
      // ISS-001: Usar endpoint parametrizable
      const response = await publicApiClient.get(HEALTH_ENDPOINT, { timeout: HEALTH_TIMEOUT });
      const data = response.data;
      
      apiHealthy = true;
      
      return {
        healthy: true,
        skipped: false,
        version: data?.version || data?.api_version || API_VERSION,
        database: data?.database ?? data?.db_status ?? 'unknown',
        timestamp: data?.timestamp || new Date().toISOString(),
        details: data,
        attempts: attempt + 1,
      };
    } catch (error) {
      lastError = error;
      const status = error.response?.status;
      
      // ISS-001: Degradación elegante - 404 no es fatal
      if (status === 404) {
        apiHealthy = true; // Backend funciona, solo no tiene /health/
        healthCheckSkipped = true;
        if (isDev) {
          console.info(`[API] Health endpoint ${HEALTH_ENDPOINT} no disponible (404), degradando a modo auth-only`);
        }
        return {
          healthy: true,
          skipped: true,
          mode: 'degraded',
          reason: 'Health endpoint no implementado en backend',
          version: API_VERSION,
          timestamp: new Date().toISOString(),
        };
      }
      
      // ISS-FIX: Si es timeout y quedan reintentos, continuar
      const isTimeout = error.code === 'ECONNABORTED' || error.message?.includes('timeout');
      const isNetworkError = error.code === 'ECONNREFUSED' || error.code === 'ERR_NETWORK';
      
      if ((isTimeout || isNetworkError) && attempt < maxRetries) {
        // Silenciado para no confundir usuarios - solo en desarrollo
        if (isDev) console.debug(`[API] Health check timeout/error en intento ${attempt + 1}, reintentando...`);
        continue;
      }
      
      // Sin más reintentos o error no recuperable
      break;
    }
  }
  
  // Todos los reintentos fallaron
  apiHealthy = false;
  const status = lastError?.response?.status;
  const isTimeout = lastError?.code === 'ECONNABORTED' || lastError?.message?.includes('timeout');
  
  const errorMsg = status === 503
    ? 'Backend en mantenimiento (503)'
    : isTimeout
      ? 'El servidor está iniciando, por favor espere unos segundos'
      : lastError?.code === 'ECONNREFUSED' || lastError?.code === 'ERR_NETWORK'
        ? 'No se puede conectar al servidor'
        : lastError?.message || 'Error de conexión';
  
  // Silenciado para no confundir usuarios - solo en desarrollo
  if (isDev) console.debug('[API] Health check falló después de reintentos:', errorMsg, status ? `(${status})` : '');
  
  return {
    healthy: false,
    skipped: false,
    error: errorMsg,
    status: status,
    version: null,
    isServerStarting: isTimeout,
  };
};

/**
 * ISS-001 FIX: Estado de salud de la API
 */
export const isApiHealthy = () => apiHealthy;
export const wasHealthCheckSkipped = () => healthCheckSkipped;
export const getApiVersion = () => API_VERSION;
export const getHealthConfig = () => ({
  endpoint: HEALTH_ENDPOINT,
  enabled: HEALTH_CHECK_ENABLED,
  timeout: HEALTH_TIMEOUT,
  authOnlyMode: AUTH_ONLY_MODE,
});

// Exportar función para verificar estado de configuración (ISS-001, ISS-003, ISS-005)
export const getApiConfigError = () => apiConfigError;
export const isApiConfigured = () => !apiConfigError;
export const isHttpInsecure = () => httpInsecureError;
export const hasHttpWarning = () => httpInsecureWarning;

// ISS-003 FIX: Fail-fast helper - lanzar error inmediatamente si API no está configurada
const assertApiConfigured = () => {
  if (apiConfigError) {
    const error = new Error(apiConfigError);
    error.name = 'ApiConfigurationError';
    error.isConfigError = true;
    console.error('[API] Fail-fast: intento de usar API sin configuración válida');
    throw error;
  }
};

// ISS-003: Ejecutar validación fail-fast al cargar el módulo en producción
if (!isDev && apiConfigError) {
  console.error('[API] ⛔ FAIL-FAST: La API no está configurada correctamente.');
  console.error('[API] Error:', apiConfigError);
  // No lanzar error aquí para permitir que App.jsx muestre el error
}

const apiClient = axios.create({
  baseURL: `${apiBaseUrl}/`,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // IMPORTANTE: Enviar cookies en cada request
  timeout: 60000, // ISS-FIX: 60 segundos de timeout para cold starts de Render
});

// Cliente público para endpoints que NO requieren autenticación
// Usado para cargar tema antes del login, health checks, etc.
const publicApiClient = axios.create({
  baseURL: `${apiBaseUrl}/`,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false, // No enviar cookies/tokens
});

let activityCallback = null;
let redirectingToLogin = false;
let isRefreshing = false;
let failedQueue = [];

// ISS-005 FIX (audit32): Configuración de reintentos para cold starts de Render
const RETRY_CONFIG = {
  maxRetries: 5,              // Máximo 5 reintentos para cold starts (~50s de espera total)
  retryDelay: 2000,           // Delay base entre reintentos (ms) - aumentado
  retryableStatusCodes: [0, 408, 429, 500, 502, 503, 504], // 0 = error de red, 500 para cold starts
  exponentialBackoff: true,   // Usar backoff exponencial
};

// ISS-005 FIX (audit32): Mapa de errores específicos por código de estado
const ERROR_HANDLERS = {
  // 409 Conflict: Estado del recurso ha cambiado (común en flujos de requisiciones)
  409: {
    message: 'El recurso ha sido modificado por otro usuario. Recarga la página.',
    action: 'reload',
    logLevel: 'warn',
  },
  // 422 Unprocessable Entity: Datos válidos pero no procesables por reglas de negocio
  422: {
    message: 'Los datos enviados no cumplen las reglas de validación.',
    action: 'none', // Manejar en el componente
    logLevel: 'warn',
  },
  // 429 Too Many Requests: Rate limiting
  429: {
    message: 'Demasiadas solicitudes. Espera un momento antes de continuar.',
    action: 'none',
    logLevel: 'warn',
  },
  // 423 Locked: Recurso bloqueado (e.g. requisición en proceso)
  423: {
    message: 'Este recurso está bloqueado temporalmente. Intenta más tarde.',
    action: 'none',
    logLevel: 'info',
  },
};

// ISS-011: Sistema de debounce para evitar toasts duplicados
const toastDebounce = {
  lastToasts: new Map(), // Map<message, timestamp>
  debounceMs: 3000,      // Mínimo 3 segundos entre toasts iguales
  
  shouldShow(message) {
    const now = Date.now();
    const lastTime = this.lastToasts.get(message);
    if (lastTime && (now - lastTime) < this.debounceMs) {
      return false; // Toast duplicado, no mostrar
    }
    this.lastToasts.set(message, now);
    // Limpiar entradas antiguas (>10 segundos)
    for (const [msg, time] of this.lastToasts.entries()) {
      if (now - time > 10000) this.lastToasts.delete(msg);
    }
    return true;
  },
  
  error(message) {
    if (this.shouldShow(message)) {
      toast.error(message);
    }
  }
};

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

export const setApiActivityHandler = (callback) => {
  activityCallback = callback;
};

const redirectToLogin = () => {
  if (redirectingToLogin) return;
  redirectingToLogin = true;
  // Limpiar tokens de memoria
  clearTokens();
  // Limpiar cualquier dato de usuario del localStorage (no tokens)
  localStorage.removeItem('user');
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
};

// Interceptor para añadir token desde memoria
apiClient.interceptors.request.use(
  (config) => {
    // ISS-003 FIX: Fail-fast si la API no está configurada correctamente
    assertApiConfigured();
    
    if (activityCallback) {
      activityCallback();
    }
    // Obtener token desde memoria (no localStorage)
    const token = getAccessToken();
    if (config.url?.startsWith('/')) {
      config.url = config.url.slice(1);
    }
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // ISS-005 FIX (audit32): Inicializar contador de reintentos si no existe
    if (typeof config._retryCount === 'undefined') {
      config._retryCount = 0;
    }
    
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;
    const detail = error.response?.data?.detail || error.response?.data?.error;
    const currentPath = window.location?.pathname || '';
    const now = Date.now();
    
    // ISS-FIX: Detectar si es un error de red/timeout (servidor no responde - cold start)
    const isNetworkError = !error.response && (
      error.code === 'ECONNABORTED' || 
      error.code === 'ERR_NETWORK' || 
      error.code === 'ECONNREFUSED' ||
      error.message?.includes('timeout') ||
      error.message?.includes('Network Error')
    );
    
    // ISS-005 FIX (audit32): Verificar límite de reintentos para errores de red/timeout
    const isRetryableError = isNetworkError || !status || RETRY_CONFIG.retryableStatusCodes.includes(status);
    const retryCount = originalRequest._retryCount || 0;
    
    if (isRetryableError && retryCount < RETRY_CONFIG.maxRetries && !originalRequest._noRetry) {
      originalRequest._retryCount = retryCount + 1;
      
      // Calcular delay con backoff exponencial si está habilitado
      const delay = RETRY_CONFIG.exponentialBackoff 
        ? RETRY_CONFIG.retryDelay * Math.pow(2, retryCount)
        : RETRY_CONFIG.retryDelay;
      
      // Silenciado para no confundir usuarios - solo en desarrollo
      if (retryCount === 0 && isNetworkError && isDev) {
        console.debug('[API] El servidor está iniciando, esperando respuesta...');
      }
      
      // HALLAZGO #5: Solo loguear en desarrollo para evitar fuga de información
      if (isDev) {
        console.log(
          `[API] Reintento ${originalRequest._retryCount}/${RETRY_CONFIG.maxRetries} ` +
          `para ${originalRequest.url} (delay: ${delay}ms, status: ${status || 'network/timeout'})`
        );
      }
      
      await new Promise(resolve => setTimeout(resolve, delay));
      return apiClient(originalRequest);
    }
    
    // ISS-FIX: Si todos los reintentos fallaron por error de red, NO redirigir al login
    // Solo mostrar mensaje de error de conexión
    if (isNetworkError && retryCount >= RETRY_CONFIG.maxRetries) {
      toastDebounce.error('El servidor no responde. Por favor, espera un momento e intenta de nuevo.');
      return Promise.reject(error);
    }
    
    // Intentar refresh automático en caso de 401
    // ISS-003: No intentar refresh si el logout está en progreso
    if (status === 401 && !originalRequest._retry && !isLogoutInProgress()) {
      if (isRefreshing) {
        // Si ya se está refrescando, encolar la petición
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(token => {
            originalRequest.headers['Authorization'] = 'Bearer ' + token;
            return apiClient(originalRequest);
          })
          .catch(err => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;
      // ISS-002 FIX (audit33): Notificar al tokenManager que hay refresh en progreso
      setRefreshInProgress(true);

      // ISS-003 FIX (audit33): Refresh parametrizable según configuración del backend
      try {
        // ISS-003: Construir payload según modo configurado
        const refreshPayload = {};
        const axiosConfig = { withCredentials: AUTH_CONFIG.refreshInCookie };
        
        // ISS-003: Si el backend espera refresh en body (no en cookie)
        // obtener el refresh token del tokenManager (si está disponible)
        if (AUTH_CONFIG.refreshInBody) {
          const storedRefresh = localStorage.getItem('_rt'); // Solo si no es HttpOnly
          if (storedRefresh) {
            refreshPayload[AUTH_CONFIG.refreshTokenField] = storedRefresh;
          }
        }
        
        const response = await axios.post(
          `${apiBaseUrl}${AUTH_CONFIG.refreshEndpoint}`, 
          refreshPayload,
          axiosConfig
        );

        // ISS-003 FIX: Buscar access token con campo parametrizado y fallbacks
        const newAccessToken = response.data?.[AUTH_CONFIG.accessTokenField] 
          || response.data?.access 
          || response.data?.access_token
          || response.data?.token;
        
        // ISS-003: Validar que obtuvimos un token válido
        if (!newAccessToken || typeof newAccessToken !== 'string') {
          console.error('[API] Refresh exitoso pero sin token válido en respuesta:', {
            expectedField: AUTH_CONFIG.accessTokenField,
            receivedKeys: Object.keys(response.data || {}),
          });
          throw new Error('Respuesta de refresh inválida: token no encontrado');
        }
        
        // Guardar nuevo access token en memoria
        setAccessToken(newAccessToken);
        
        // Actualizar headers del request original
        originalRequest.headers['Authorization'] = 'Bearer ' + newAccessToken;
        
        // Procesar cola de peticiones pendientes
        processQueue(null, newAccessToken);
        isRefreshing = false;
        setRefreshInProgress(false); // ISS-002 FIX (audit33)
        
        // Reintentar request original
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        isRefreshing = false;
        setRefreshInProgress(false); // ISS-002 FIX (audit33)
        
        // Cancelar timers activos
        if (window.notificationInterval) {
          clearInterval(window.notificationInterval);
          window.notificationInterval = null;
        }
        window.dispatchEvent(new Event('session-expired'));
        toastDebounce.error('Sesión expirada. Inicia sesión nuevamente.');
        redirectToLogin();
        return Promise.reject(refreshError);
      }
    }
    
    // ISS-011: Usar toastDebounce para evitar toasts duplicados
    // ISS-005 FIX (audit32): Manejo específico por código de estado
    // ISS-FIX: Definir serverMessage a nivel de scope para evitar ReferenceError
    const serverMessage = error.response?.data?.detail || error.response?.data?.error;
    
    if (status === 403) {
      toastDebounce.error('No tienes permisos para esta acción.');
    } else if (ERROR_HANDLERS[status]) {
      // ISS-005 FIX: Manejar códigos específicos con configuración
      const handler = ERROR_HANDLERS[status];
      
      // Loguear según nivel configurado
      if (handler.logLevel === 'error') {
        console.error(`[API ${status}]`, serverMessage || handler.message);
      } else if (handler.logLevel === 'warn') {
        console.warn(`[API ${status}]`, serverMessage || handler.message);
      }
      
      // Mostrar toast con mensaje del servidor si existe, sino el genérico
      toastDebounce.error(serverMessage || handler.message);
      
      // ISS-005: Ejecutar acción configurada
      if (handler.action === 'reload') {
        // Dar tiempo al usuario para leer el mensaje antes de recargar
        setTimeout(() => {
          window.location.reload();
        }, 2000);
      }
    } else if (status >= 400 && status < 500) {
      if (detail) toastDebounce.error(detail);
    } else if (!error.response) {
      toastDebounce.error('Error al conectar con el servidor.');
    } else if (status >= 500) {
      // ISS-FIX: No mostrar errores 500 al usuario, solo loguear en consola
      console.error('[API] Error interno del servidor:', status, serverMessage || error.message);
    }
    return Promise.reject(error);
  }
);

/**
 * ISS-005 FIX (audit33): Descarga un blob como archivo local con validación de tipo
 * @param {Blob|Response} blob - El blob o respuesta de axios
 * @param {string} nombreArchivo - Nombre del archivo a descargar
 * @returns {boolean} true si la descarga fue exitosa, false si hubo error
 */
export const descargarArchivo = (blob, nombreArchivo) => {
  try {
    // ISS-005: Obtener el contenido del blob correctamente
    const contenido = blob?.data ?? blob;
    
    // ISS-005: Validar que tenemos un blob válido
    if (!contenido) {
      console.error('[descargarArchivo] No se recibió contenido');
      toast.error('Error: No se recibió el archivo del servidor');
      return false;
    }
    
    // ISS-005: Verificar si es un error JSON en lugar de un blob
    // Algunos backends devuelven JSON con error incluso para peticiones de blob
    if (contenido instanceof Blob && contenido.type === 'application/json') {
      // Intentar leer el error del JSON
      contenido.text().then(text => {
        try {
          const error = JSON.parse(text);
          const mensaje = error.detail || error.error || error.message || 'Error al generar el archivo';
          console.error('[descargarArchivo] Error del servidor:', error);
          toast.error(mensaje);
        } catch {
          toast.error('Error inesperado al descargar el archivo');
        }
      });
      return false;
    }
    
    // ISS-005: Validar tamaño mínimo (un archivo vacío no es válido)
    if (contenido.size !== undefined && contenido.size === 0) {
      console.warn('[descargarArchivo] Archivo vacío recibido');
      toast.error('El archivo generado está vacío. Verifica los filtros.');
      return false;
    }
    
    const url = window.URL.createObjectURL(contenido);
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = nombreArchivo;
    document.body.appendChild(enlace);
    enlace.click();
    document.body.removeChild(enlace);
    window.URL.revokeObjectURL(url);
    
    return true;
  } catch (error) {
    console.error('[descargarArchivo] Error:', error);
    toast.error('Error al descargar el archivo');
    return false;
  }
};

/**
 * ISS-005 FIX (audit33): Wrapper para peticiones de exportación con manejo de errores
 * @param {Promise} peticion - Promesa de axios con responseType: 'blob'
 * @param {string} nombreArchivo - Nombre del archivo a descargar
 * @param {Object} options - Opciones adicionales
 * @returns {Promise<boolean>} true si exitoso, false si hubo error
 */
export const exportarConManejo = async (peticion, nombreArchivo, options = {}) => {
  const { 
    mensajeExito = 'Archivo descargado correctamente',
    mensajeVacio = 'No hay datos para exportar con los filtros seleccionados',
    mostrarExito = false,
  } = options;
  
  try {
    const response = await peticion;
    
    // ISS-005: Verificar código 204 (No Content)
    if (response.status === 204) {
      toast.error(mensajeVacio);
      return false;
    }
    
    const exito = descargarArchivo(response, nombreArchivo);
    
    if (exito && mostrarExito) {
      toast.success(mensajeExito);
    }
    
    return exito;
  } catch (error) {
    const status = error.response?.status;
    
    // ISS-005: Manejar códigos específicos
    if (status === 204 || status === 404) {
      toast.error(mensajeVacio);
    } else if (status === 400) {
      // Intentar extraer mensaje del servidor
      const data = error.response?.data;
      if (data instanceof Blob) {
        try {
          const text = await data.text();
          const json = JSON.parse(text);
          toast.error(json.detail || json.error || 'Parámetros de exportación inválidos');
        } catch {
          toast.error('Parámetros de exportación inválidos');
        }
      } else {
        toast.error(data?.detail || 'Parámetros de exportación inválidos');
      }
    } else if (status === 403) {
      toast.error('No tienes permiso para exportar este reporte');
    } else {
      // Error genérico manejado por el interceptor
      console.error('[exportarConManejo] Error:', error);
    }
    
    return false;
  }
};

// Productos
export const productosAPI = {
  getAll: (params) => apiClient.get('/productos/', { params }),
  getById: (id) => apiClient.get(`/productos/${id}/`),
  create: (data, isFormData = false) => {
    const config = isFormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : {};
    return apiClient.post('/productos/', data, config);
  },
  update: (id, data, isFormData = false) => {
    const config = isFormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : {};
    return apiClient.put(`/productos/${id}/`, data, config);
  },
  patch: (id, data, isFormData = false) => {
    const config = isFormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : {};
    return apiClient.patch(`/productos/${id}/`, data, config);
  },
  delete: (id) => apiClient.delete(`/productos/${id}/`),
  toggleActivo: (id) => apiClient.post(`/productos/${id}/toggle-activo/`),
  nuevos: (dias = 7) => apiClient.get(`/productos/nuevos/?dias=${dias}`),
  bajoStock: () => apiClient.get('/productos/bajo-stock/'),
  estadisticas: () => apiClient.get('/productos/estadisticas/'),
  exportar: (params) => apiClient.get('/productos/exportar-excel/', { 
    params, 
    responseType: 'blob' 
  }),
  importar: (formData) => apiClient.post('/productos/importar-excel/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  plantilla: () => apiClient.get('/productos/plantilla/', { responseType: 'blob' }),
  auditoria: (id) => apiClient.get(`/productos/${id}/auditoria/`),
  // ISS-FIX: Obtener lotes de un producto específico con semáforo de caducidad
  lotes: (id) => apiClient.get(`/productos/${id}/lotes/`),
};

// Lotes
// ISS-006 FIX (audit33): getAll acepta config adicional para AbortController
export const lotesAPI = {
  getAll: (params, config = {}) => apiClient.get('/lotes/', { params, ...config }),
  // ISS-FIX: getById acepta params opcionales (ej: para_requisicion=true)
  getById: (id, params = {}) => apiClient.get(`/lotes/${id}/`, { params }),
  create: (data) => apiClient.post('/lotes/', data),
  update: (id, data) => apiClient.put(`/lotes/${id}/`, data),
  delete: (id) => apiClient.delete(`/lotes/${id}/`),
  porCaducar: (dias = 90) => apiClient.get(`/lotes/por-caducar/?dias=${dias}`),
  vencidos: () => apiClient.get('/lotes/vencidos/'),
  ajustarStock: (id, data) => apiClient.post(`/lotes/${id}/ajustar-stock/`, data),
  trazabilidad: (id) => apiClient.get(`/lotes/${id}/trazabilidad/`),
  // Documentos de lote (facturas, contratos, remisiones)
  listarDocumentos: (id) => apiClient.get(`/lotes/${id}/documentos/`),
  subirDocumento: (id, formData) => apiClient.post(`/lotes/${id}/subir-documento/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  eliminarDocumento: (loteId, docId) => apiClient.delete(`/lotes/${loteId}/eliminar-documento/${docId}/`),
  // Exportaciones
  exportar: (params) => apiClient.get('/lotes/exportar-excel/', { 
    params, 
    responseType: 'blob' 
  }),
  exportarPdf: (params) => apiClient.get('/lotes/exportar-pdf/', { 
    params, 
    responseType: 'blob' 
  }),
  importar: (formData) => apiClient.post('/lotes/importar-excel/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  plantilla: () => apiClient.get('/lotes/plantilla/', { responseType: 'blob' }),
};

// Centros
export const centrosAPI = {
  getAll: (params) => apiClient.get('/centros/', { params }),
  getById: (id) => apiClient.get(`/centros/${id}/`),
  create: (data) => apiClient.post('/centros/', data),
  update: (id, data) => apiClient.put(`/centros/${id}/`, data),
  delete: (id) => apiClient.delete(`/centros/${id}/`),
  toggleActivo: (id) => apiClient.post(`/centros/${id}/toggle-activo/`),
  plantilla: () => apiClient.get('/centros/plantilla/', { responseType: 'blob' }),
  exportar: (params) => apiClient.get('/centros/exportar-excel/', { params, responseType: 'blob' }),
  importar: (formData) => apiClient.post('/centros/importar/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  inventario: (id) => apiClient.get(`/centros/${id}/inventario/`),
};

// Usuarios -  COMPLETO
export const usuariosAPI = {
  getAll: (params) => apiClient.get('/usuarios/', { params }),
  getById: (id) => apiClient.get(`/usuarios/${id}/`),
  create: (data) => apiClient.post('/usuarios/', data),
  update: (id, data) => apiClient.put(`/usuarios/${id}/`, data),
  delete: (id) => apiClient.delete(`/usuarios/${id}/`),
  cambiarPassword: (id, data) => apiClient.post(`/usuarios/${id}/cambiar-password/`, data),
  me: () => apiClient.get('/usuarios/me/'),
  actualizarPerfil: (data) => apiClient.patch('/usuarios/me/', data),
  cambiarPasswordPropio: (data) => apiClient.post('/usuarios/me/change-password/', data),
  exportar: (params = {}) => apiClient.get('/usuarios/exportar-excel/', { params, responseType: 'blob' }),
  importar: (formData) => apiClient.post('/usuarios/importar-excel/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  plantilla: () => apiClient.get('/usuarios/plantilla/', { responseType: 'blob' }),
};

// ========== ISS-002 FIX: VALIDACIÓN DE ESTADOS DE REQUISICIONES ==========
/**
 * Mapa de transiciones válidas V2 (estado_actual -> [acciones_permitidas])
 * Esto previene acciones incoherentes antes de enviar al backend
 */
const TRANSICIONES_V2 = {
  'BORRADOR': ['enviar', 'enviarAdmin', 'delete'],
  'ENVIADA': ['autorizar', 'rechazar', 'cancelar'],
  'ENVIADA_ADMIN': ['autorizarAdmin', 'rechazar', 'cancelar', 'devolver'],
  'AUTORIZADA_ADMIN': ['autorizarDirector', 'rechazar', 'cancelar', 'devolver'],
  'AUTORIZADA_DIRECTOR': ['recibirFarmacia', 'rechazar', 'cancelar'],
  'RECIBIDA_FARMACIA': ['autorizarFarmacia', 'rechazar', 'devolver'],
  'AUTORIZADA_FARMACIA': ['surtir', 'cancelar'],
  'AUTORIZADA': ['surtir', 'rechazar', 'cancelar'], // Legacy
  'SURTIDA': ['confirmarEntrega', 'marcarRecibida'],
  'EN_TRANSITO': ['confirmarEntrega', 'marcarRecibida'],
  'ENTREGADA': [], // Estado final
  'RECIBIDA': [], // Estado final
  'RECHAZADA': ['reenviar'],
  'DEVUELTA': ['reenviar'],
  'CANCELADA': [], // Estado final
  'VENCIDA': [], // Estado final
};

/**
 * ISS-002: Validar si una transición es permitida desde el estado actual
 * @param {string} estadoActual - Estado actual de la requisición
 * @param {string} accion - Acción que se quiere ejecutar
 * @returns {boolean} - True si la transición es válida
 */
const esTransicionValida = (estadoActual, accion) => {
  if (!estadoActual) return true; // Si no hay estado, dejar que backend valide
  const estadoNorm = estadoActual.toUpperCase().replace(/ /g, '_');
  const permitidas = TRANSICIONES_V2[estadoNorm] || [];
  return permitidas.length === 0 || permitidas.includes(accion);
};

/**
 * ISS-002: Crear error de transición inválida
 */
const crearErrorTransicion = (estadoActual, accion) => {
  const error = new Error(
    `Transición inválida: No se puede ejecutar "${accion}" desde estado "${estadoActual}". ` +
    `Acciones permitidas: ${(TRANSICIONES_V2[estadoActual?.toUpperCase()] || ['ninguna']).join(', ')}`
  );
  error.name = 'TransicionInvalidaError';
  error.code = 'INVALID_TRANSITION';
  error.estadoActual = estadoActual;
  error.accionIntentada = accion;
  return error;
};

/**
 * ISS-002: Wrapper para validar estado antes de ejecutar acción
 * @param {string} accion - Nombre de la acción
 * @param {Function} fn - Función que ejecuta la acción
 * @param {string} estadoActual - Estado actual de la requisición (opcional)
 */
const conValidacionEstado = (accion, fn, estadoActual = null) => {
  return async (...args) => {
    // Si tenemos el estado actual, validar antes de llamar
    if (estadoActual && !esTransicionValida(estadoActual, accion)) {
      return Promise.reject(crearErrorTransicion(estadoActual, accion));
    }
    return fn(...args);
  };
};

// Exportar utilidades de validación para uso en componentes
export const requisicionesValidacion = {
  TRANSICIONES_V2,
  esTransicionValida,
  getAccionesPermitidas: (estado) => TRANSICIONES_V2[estado?.toUpperCase()?.replace(/ /g, '_')] || [],
};

// Requisiciones -  COMPLETO CON FLUJO V2
export const requisicionesAPI = {
  getAll: (params) => apiClient.get('/requisiciones/', { params }),
  getById: (id) => apiClient.get(`/requisiciones/${id}/`),
  create: (data) => apiClient.post('/requisiciones/', data),
  update: (id, data) => apiClient.put(`/requisiciones/${id}/`, data),
  delete: (id) => apiClient.delete(`/requisiciones/${id}/`),
  
  // ISS-002: Flujo de estados (legacy - compatibilidad, usar V2 preferentemente)
  enviar: (id) => apiClient.post(`/requisiciones/${id}/enviar/`),
  autorizar: (id, data) => apiClient.post(`/requisiciones/${id}/autorizar/`, data),
  rechazar: (id, data) => apiClient.post(`/requisiciones/${id}/rechazar/`, data),
  surtir: (id, formData = null) => {
    // Soporta subir foto de firma al surtir
    if (formData instanceof FormData) {
      return apiClient.post(`/requisiciones/${id}/surtir/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    }
    return apiClient.post(`/requisiciones/${id}/surtir/`);
  },
  marcarRecibida: (id, data) => {
    // Soporta subir foto de firma al recibir
    if (data instanceof FormData) {
      return apiClient.post(`/requisiciones/${id}/marcar-recibida/`, data, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    }
    return apiClient.post(`/requisiciones/${id}/marcar-recibida/`, data);
  },
  cancelar: (id, data = {}) => apiClient.post(`/requisiciones/${id}/cancelar/`, data),
  resumenEstados: (params = {}) => apiClient.get('/requisiciones/resumen_estados/', { params }),
  
  // ========== FLUJO V2: TRANSICIONES JERÁRQUICAS ==========
  
  // Flujo Centro Penitenciario
  enviarAdmin: (id, data = {}) => apiClient.post(`/requisiciones/${id}/enviar-admin/`, data),
  autorizarAdmin: (id, data = {}) => apiClient.post(`/requisiciones/${id}/autorizar-admin/`, data),
  autorizarDirector: (id, data = {}) => apiClient.post(`/requisiciones/${id}/autorizar-director/`, data),
  
  // Flujo Farmacia Central
  recibirFarmacia: (id, data = {}) => apiClient.post(`/requisiciones/${id}/recibir-farmacia/`, data),
  autorizarFarmacia: (id, data) => apiClient.post(`/requisiciones/${id}/autorizar-farmacia/`, data),
  
  // Acciones especiales
  devolver: (id, data) => apiClient.post(`/requisiciones/${id}/devolver/`, data),
  reenviar: (id, data = {}) => apiClient.post(`/requisiciones/${id}/reenviar/`, data),
  confirmarEntrega: (id, data) => {
    if (data instanceof FormData) {
      return apiClient.post(`/requisiciones/${id}/confirmar-entrega/`, data, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    }
    return apiClient.post(`/requisiciones/${id}/confirmar-entrega/`, data);
  },
  marcarVencida: (id, data = {}) => apiClient.post(`/requisiciones/${id}/marcar-vencida/`, data),
  
  // Historial y transiciones
  getHistorial: (id) => apiClient.get(`/requisiciones/${id}/historial/`),
  verificarVencidas: () => apiClient.post('/requisiciones/verificar-vencidas/'),
  getTransicionesDisponibles: () => apiClient.get('/requisiciones/transiciones-disponibles/'),
  
  // Subir fotos de firma
  subirFirmaSurtido: (id, formData) => apiClient.post(`/requisiciones/${id}/subir-firma-surtido/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  subirFirmaRecepcion: (id, formData) => apiClient.post(`/requisiciones/${id}/subir-firma-recepcion/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  
  // Descarga de PDFs
  downloadPDFAceptacion: (id) => apiClient.get(`/requisiciones/${id}/hoja-recoleccion/`, {
    responseType: 'blob'
  }),
  downloadPDFRechazo: (id) => apiClient.get(`/requisiciones/${id}/pdf-rechazo/`, {
    responseType: 'blob'
  }),
  // ISS-HOJA-V2: Hoja de consulta para centro (con sello SURTIDA, sin firmas)
  downloadHojaConsulta: (id) => apiClient.get(`/requisiciones/${id}/hoja-consulta/`, {
    responseType: 'blob'
  }),

  // Compatibilidad hacia atras
  getHojaRecoleccion: (id) => apiClient.get(`/requisiciones/${id}/hoja-recoleccion/`, {
    responseType: 'blob'
  }),
};

// Auditora -  NUEVO
export const auditoriaAPI = {
  getAll: (params) => apiClient.get('/auditoria/', { params }),
  exportar: (params) => apiClient.get('/auditoria/exportar/', { 
    params, 
    responseType: 'blob' 
  }),
  exportarPdf: (params) => apiClient.get('/auditoria/exportar-pdf/', { 
    params, 
    responseType: 'blob' 
  }),
};

// Auth -  SEGURO CON COOKIES HttpOnly
// ISS-003 FIX (audit33): Configuración parametrizable de endpoints
export const authAPI = {
  // ISS-003: Login con validación de respuesta
  login: async (credentials) => {
    const response = await apiClient.post(AUTH_CONFIG.tokenEndpoint, credentials);
    
    // ISS-003: Validar que la respuesta contiene el token esperado
    const accessToken = response.data?.[AUTH_CONFIG.accessTokenField]
      || response.data?.access
      || response.data?.access_token
      || response.data?.token;
    
    if (!accessToken && response.status === 200) {
      console.warn('[API] Login exitoso pero sin access token en respuesta esperada:', {
        expectedField: AUTH_CONFIG.accessTokenField,
        receivedKeys: Object.keys(response.data || {}),
      });
    }
    
    // Normalizar respuesta para consumidores
    return {
      ...response,
      data: {
        ...response.data,
        access: accessToken, // Siempre disponible como 'access'
      }
    };
  },
  // ISS-003: Refresh usa configuración de AUTH_CONFIG
  refresh: () => apiClient.post(AUTH_CONFIG.refreshEndpoint, {}),
  // ISS-003: Logout con endpoint parametrizable
  logout: (data = {}) => apiClient.post(AUTH_CONFIG.logoutEndpoint, data),
  // Dev login (solo desarrollo)
  devLogin: (data = {}) => apiClient.post('/dev-autologin/', data),
  // Perfil del usuario autenticado
  me: () => apiClient.get('/usuarios/me/'),
};

// Password Reset - Recuperación de contraseña
export const passwordResetAPI = {
  // Solicitar email de recuperación
  request: (email) => apiClient.post('/password-reset/request/', { email }),
  // Confirmar nueva contraseña con token
  confirm: (data) => apiClient.post('/password-reset/confirm/', data),
  // Validar si un token es válido
  validate: (token) => apiClient.post('/password-reset/validate/', { token }),
};

// Movimientos
export const movimientosAPI = {
  getAll: (params) => apiClient.get('/movimientos/', { params }),
  // ISS-FIX: Endpoint para vista agrupada - agrupa en backend antes de paginar
  getAgrupados: (params) => apiClient.get('/movimientos/agrupados/', { params }),
  create: (data) => apiClient.post('/movimientos/', data),
  exportarExcel: (params) => apiClient.get('/movimientos/exportar-excel/', { params, responseType: 'blob' }),
  exportarPdf: (params) => apiClient.get('/movimientos/exportar-pdf/', { params, responseType: 'blob' }),
  // Recibo de salida con campos de firma (PDF)
  // Si finalizado=true, genera comprobante con sello ENTREGADO en lugar de firmas
  getReciboSalida: (movimientoId, finalizado = false) => apiClient.get(`/movimientos/${movimientoId}/recibo-salida/`, { 
    params: finalizado ? { finalizado: 'true' } : {},
    responseType: 'blob' 
  }),
  // Confirmar entrega física de un movimiento individual
  confirmarEntrega: (movimientoId) => apiClient.post(`/movimientos/${movimientoId}/confirmar-entrega/`),
};

// Salida Masiva (solo Farmacia)
export const salidaMasivaAPI = {
  // Procesar salida masiva a un centro
  procesar: (data) => apiClient.post('/salida-masiva/', data),
  // Obtener lotes disponibles en Farmacia Central
  lotesDisponibles: (params) => apiClient.get('/salida-masiva/lotes-disponibles/', { params }),
  // Descargar hoja de entrega PDF (finalizado=true para comprobante con sello ENTREGADO)
  hojaEntregaPdf: (grupoSalida, finalizado = false) => apiClient.get(
    `/salida-masiva/hoja-entrega/${grupoSalida}/`, 
    { 
      params: finalizado ? { finalizado: 'true' } : {},
      responseType: 'blob' 
    }
  ),
  // Confirmar entrega física
  confirmarEntrega: (grupoSalida) => apiClient.post(`/salida-masiva/confirmar-entrega/${grupoSalida}/`),
  // Cancelar salida NO confirmada (devuelve stock al inventario)
  cancelar: (grupoSalida) => apiClient.delete(`/salida-masiva/cancelar/${grupoSalida}/`),
  // Consultar estado de entrega
  estadoEntrega: (grupoSalida) => apiClient.get(`/salida-masiva/estado-entrega/${grupoSalida}/`),
};

// Trazabilidad -  NUEVO
export const trazabilidadAPI = {
  // Búsqueda unificada (detecta si es lote o producto)
  buscar: (termino, params = {}) => apiClient.get('/trazabilidad/buscar/', { params: { q: termino, ...params } }),
  // Autocompletado unificado
  autocomplete: (search, params = {}) => apiClient.get('/trazabilidad/autocomplete/', { params: { search, ...params } }),
  // Endpoints específicos
  producto: (clave, params = {}) => apiClient.get(`/trazabilidad/producto/${clave}/`, { params }),
  lote: (numeroLote, params = {}) => apiClient.get(`/trazabilidad/lote/${numeroLote}/`, { params }),
  
  // Trazabilidad global (todos los lotes)
  global: (params = {}) => apiClient.get('/trazabilidad/global/', { params }),
  
  // Exportar PDF de producto (con filtros de fecha)
  exportarPdf: (clave, params = {}) => apiClient.get(`/trazabilidad/producto/${clave}/exportar/`, { 
    params: { ...params, formato: 'pdf' }, 
    responseType: 'blob' 
  }),
  // Exportar Excel de producto (con filtros de fecha)
  exportarExcel: (clave, params = {}) => apiClient.get(`/trazabilidad/producto/${clave}/exportar/`, { 
    params: { ...params, formato: 'excel' }, 
    responseType: 'blob' 
  }),
  
  // Exportar PDF de lote (con filtros de fecha)
  exportarLotePdf: (numeroLote, loteId = null, params = {}) => {
    const queryParams = { ...params, formato: 'pdf' };
    if (loteId) queryParams.lote_id = loteId;
    return apiClient.get(`/trazabilidad/lote/${numeroLote}/exportar/`, { 
      params: queryParams, 
      responseType: 'blob' 
    });
  },
  // Exportar Excel de lote (con filtros de fecha)
  exportarLoteExcel: (numeroLote, loteId = null, params = {}) => {
    const queryParams = { ...params, formato: 'excel' };
    if (loteId) queryParams.lote_id = loteId;
    return apiClient.get(`/trazabilidad/lote/${numeroLote}/exportar/`, { 
      params: queryParams, 
      responseType: 'blob' 
    });
  },
  
  // Exportar global PDF (todos los lotes con filtros)
  exportarGlobalPdf: (params = {}) => apiClient.get('/trazabilidad/global/', { 
    params: { ...params, formato: 'pdf' }, 
    responseType: 'blob' 
  }),
  // Exportar global Excel (todos los lotes con filtros)
  exportarGlobalExcel: (params = {}) => apiClient.get('/trazabilidad/global/', { 
    params: { ...params, formato: 'excel' }, 
    responseType: 'blob' 
  }),
  
  // Exportar Control de Inventarios (formato licitación)
  exportarControlInventarios: () => apiClient.get('/trazabilidad/exportar-control-inventarios/', { 
    responseType: 'blob' 
  }),
};

// Dashboard
export const dashboardAPI = {
  getResumen: (params) => apiClient.get('/dashboard/', { params }),
  getGraficas: (params) => apiClient.get('/dashboard/graficas/', { params }),
};

// Reportes -  COMPLETO
export const reportesAPI = {
  // Reportes generales
  medicamentosPorCaducar: (params) => apiClient.get('/reportes/medicamentos-por-caducar/', { params }),
  bajoStock: () => apiClient.get('/reportes/bajo-stock/'),
  consumo: (params) => apiClient.get('/reportes/consumo/', { params }),

  // Reportes JSON
  inventario: (params) => apiClient.get('/reportes/inventario/', { params }),
  caducidades: (params) => apiClient.get('/reportes/caducidades/', { params }),
  requisiciones: (params) => apiClient.get('/reportes/requisiciones/', { params }),
  movimientos: (params) => apiClient.get('/reportes/movimientos/', { params: { ...params, formato: 'json' } }),

  // Descargas Excel
  exportarInventarioExcel: (params) => apiClient.get('/reportes/inventario/', {
    params: { ...params, formato: 'excel' },
    responseType: 'blob'
  }),
  exportarCaducidadesExcel: (params) => apiClient.get('/reportes/caducidades/', {
    params: { ...params, formato: 'excel' },
    responseType: 'blob'
  }),
  exportarRequisicionesExcel: (params) => apiClient.get('/reportes/requisiciones/', {
    params: { ...params, formato: 'excel' },
    responseType: 'blob'
  }),
  exportarMovimientosExcel: (params) => apiClient.get('/reportes/movimientos/', {
    params: { ...params, formato: 'excel' },
    responseType: 'blob'
  }),

  // Descargas PDF (con fondo oficial)
  exportarInventarioPDF: (params) => apiClient.get('/reportes/inventario/', {
    params: { ...params, formato: 'pdf' },
    responseType: 'blob'
  }),
  exportarCaducidadesPDF: (params) => apiClient.get('/reportes/caducidades/', {
    params: { ...params, formato: 'pdf' },
    responseType: 'blob'
  }),
  exportarRequisicionesPDF: (params) => apiClient.get('/reportes/requisiciones/', {
    params: { ...params, formato: 'pdf' },
    responseType: 'blob'
  }),
  exportarMovimientosPDF: (params) => apiClient.get('/reportes/movimientos/', {
    params: { ...params, formato: 'pdf' },
    responseType: 'blob'
  }),

  // Precarga de datos
  precarga: () => apiClient.get('/reportes/precarga/'),
};

// Notificaciones
export const notificacionesAPI = {
  getAll: (params) => apiClient.get('/notificaciones/', { params }),
  marcarLeida: (id) => apiClient.post(`/notificaciones/${id}/marcar-leida/`),
  // Pasar filtros para respetar el contexto actual (tipo, desde, hasta, leida)
  marcarTodasLeidas: (params) => apiClient.post('/notificaciones/marcar-todas-leidas/', null, { params }),
  delete: (id) => apiClient.delete(`/notificaciones/${id}/`),
  noLeidasCount: () => apiClient.get('/notificaciones/no-leidas-count/'),
};

// Configuración del Sistema (tema/colores)
export const configuracionAPI = {
  // Obtener configuración actual (público)
  getTema: () => apiClient.get('/configuracion/tema/'),
  // Actualizar configuración (solo superusuario)
  updateTema: (data) => apiClient.put('/configuracion/tema/', data),
  // Aplicar tema predefinido (solo superusuario)
  aplicarTema: (tema) => apiClient.post('/configuracion/tema/aplicar-tema/', { tema }),
  // Restablecer a valores por defecto (solo superusuario)
  restablecer: () => apiClient.post('/configuracion/tema/restablecer/'),
  // Subir logo del header
  subirLogoHeader: (formData) => apiClient.post('/configuracion/tema/subir-logo-header/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  // Subir logo para PDFs
  subirLogoPdf: (formData) => apiClient.post('/configuracion/tema/subir-logo-pdf/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  // Eliminar logo del header
  eliminarLogoHeader: () => apiClient.delete('/configuracion/tema/eliminar-logo-header/'),
  // Eliminar logo para PDFs
  eliminarLogoPdf: () => apiClient.delete('/configuracion/tema/eliminar-logo-pdf/'),
};

// API de Tema Global (personalización completa)
export const temaGlobalAPI = {
  // Obtener tema activo (PÚBLICO - usa cliente sin auth para funcionar antes del login)
  getTemaActivo: () => publicApiClient.get('/tema/activo/'),
  // Obtener tema completo para administración (autenticado)
  getTema: () => apiClient.get('/tema/'),
  // Actualizar tema global (solo superusuario)
  updateTema: (data) => apiClient.put('/tema/', data),
  // Restablecer a tema institucional (solo superusuario)
  restablecerInstitucional: () => apiClient.post('/tema/restablecer/'),
  // Subir logo específico (tipos: header, login, reportes, favicon, fondo_login, fondo_reportes)
  subirLogo: (tipo, formData) => apiClient.post(`/tema/subir-logo/${tipo}/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  // Eliminar logo específico
  eliminarLogo: (tipo) => apiClient.delete(`/tema/eliminar-logo/${tipo}/`),
};

// Hojas de Recolección - Sistema de seguridad para entregas
export const hojasRecoleccionAPI = {
  // Listar hojas (filtrable por estado, centro, folio)
  getAll: (params) => apiClient.get('/hojas-recoleccion/', { params }),
  // Obtener detalle de una hoja
  getById: (id) => apiClient.get(`/hojas-recoleccion/${id}/`),
  // Descargar PDF de la hoja
  descargarPDF: (id) => apiClient.get(`/hojas-recoleccion/${id}/pdf/`, { responseType: 'blob' }),
  // Farmacia verifica que la hoja coincide con lo impreso
  verificar: (id) => apiClient.post(`/hojas-recoleccion/${id}/verificar/`),
  // Verificar integridad (hash)
  verificarIntegridad: (id) => apiClient.get(`/hojas-recoleccion/${id}/verificar-integridad/`),
  // Registrar que se imprimió
  registrarImpresion: (id) => apiClient.post(`/hojas-recoleccion/${id}/registrar-impresion/`),
  // Estadísticas (solo farmacia)
  estadisticas: () => apiClient.get('/hojas-recoleccion/estadisticas/'),
  // Obtener hoja por requisición
  porRequisicion: (requisicionId) => apiClient.get(`/hojas-recoleccion/por-requisicion/${requisicionId}/`),
};

// Donaciones - Módulo de gestión de donaciones
export const donacionesAPI = {
  // CRUD básico
  getAll: (params) => apiClient.get('/donaciones/', { params }),
  getById: (id) => apiClient.get(`/donaciones/${id}/`),
  create: (data) => apiClient.post('/donaciones/', data),
  update: (id, data) => apiClient.put(`/donaciones/${id}/`, data),
  delete: (id) => apiClient.delete(`/donaciones/${id}/`),
  // Recibir donación (pendiente → recibida)
  recibir: (id) => apiClient.post(`/donaciones/${id}/recibir/`),
  // Procesar donación (genera movimientos de entrada)
  procesar: (id) => apiClient.post(`/donaciones/${id}/procesar/`),
  // Rechazar donación
  rechazar: (id, data) => apiClient.post(`/donaciones/${id}/rechazar/`, data),
  // Obtener siguiente número de donación
  getSiguienteNumero: () => apiClient.get('/donaciones/siguiente-numero/'),
  // Exportar (legacy)
  exportar: (params) => apiClient.get('/donaciones/exportar/', { 
    params, 
    responseType: 'blob' 
  }),
  // Exportación e importación Excel
  exportarExcel: (params) => apiClient.get('/donaciones/exportar-excel/', { 
    params, 
    responseType: 'blob' 
  }),
  plantillaExcel: () => apiClient.get('/donaciones/plantilla-excel/', { 
    responseType: 'blob' 
  }),
  importarExcel: (formData) => apiClient.post('/donaciones/importar-excel/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
};

// ===========================================================================
// CATÁLOGO INDEPENDIENTE DE PRODUCTOS DE DONACIONES
// Este catálogo es COMPLETAMENTE SEPARADO del catálogo principal de productos.
// Las donaciones pueden tener productos con claves y nombres diferentes.
// ===========================================================================
export const productosDonacionAPI = {
  // CRUD básico
  getAll: (params) => apiClient.get('/productos-donacion/', { params }),
  getById: (id) => apiClient.get(`/productos-donacion/${id}/`),
  create: (data) => apiClient.post('/productos-donacion/', data),
  update: (id, data) => apiClient.put(`/productos-donacion/${id}/`, data),
  delete: (id) => apiClient.delete(`/productos-donacion/${id}/`),
  // Búsqueda rápida
  buscar: (q) => apiClient.get('/productos-donacion/buscar/', { params: { q } }),
  // Importación/Exportación
  descargarPlantilla: () => apiClient.get('/productos-donacion/plantilla-excel/', { responseType: 'blob' }),
  exportarExcel: () => apiClient.get('/productos-donacion/exportar-excel/', { responseType: 'blob' }),
  importarExcel: (formData) => apiClient.post('/productos-donacion/importar-excel/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
};

// Detalles de Donación (Inventario de Donaciones)
export const detallesDonacionAPI = {
  getAll: (params) => apiClient.get('/detalle-donaciones/', { params }),
  getById: (id) => apiClient.get(`/detalle-donaciones/${id}/`),
  create: (data) => apiClient.post('/detalle-donaciones/', data),
  update: (id, data) => apiClient.put(`/detalle-donaciones/${id}/`, data),
  delete: (id) => apiClient.delete(`/detalle-donaciones/${id}/`),
  // Obtener solo con stock disponible
  conStock: (params) => apiClient.get('/detalle-donaciones/', { 
    params: { ...params, disponible: 'true' } 
  }),
  // Exportar inventario a Excel con formato trazabilidad (respeta filtros)
  exportarExcel: (params) => apiClient.get('/detalle-donaciones/exportar-excel/', { 
    params, 
    responseType: 'blob' 
  }),
  // Exportar inventario a PDF con formato profesional (respeta filtros)
  exportarPdf: (params) => apiClient.get('/detalle-donaciones/exportar-pdf/', { 
    params, 
    responseType: 'blob' 
  }),
};

// Salidas de Donaciones - Control de entregas del almacén de donaciones
export const salidasDonacionesAPI = {
  getAll: (params) => apiClient.get('/salidas-donaciones/', { params }),
  getById: (id) => apiClient.get(`/salidas-donaciones/${id}/`),
  create: (data) => apiClient.post('/salidas-donaciones/', data),
  // Eliminar entrega NO finalizada (devuelve stock al inventario)
  delete: (id) => apiClient.delete(`/salidas-donaciones/${id}/`),
  // Finalizar entrega (marcar como entregado)
  finalizar: (id) => apiClient.post(`/salidas-donaciones/${id}/finalizar/`),
  // Descargar recibo PDF
  getReciboPdf: (id, finalizado = false) => apiClient.get(`/salidas-donaciones/${id}/recibo-pdf/`, { 
    params: { finalizado: finalizado ? 'true' : 'false' },
    responseType: 'blob' 
  }),
  // Exportación e importación Excel
  exportarExcel: (params) => apiClient.get('/salidas-donaciones/exportar-excel/', { 
    params, 
    responseType: 'blob' 
  }),
  plantillaExcel: () => apiClient.get('/salidas-donaciones/plantilla-excel/', { 
    responseType: 'blob' 
  }),
  importarExcel: (formData) => apiClient.post('/salidas-donaciones/importar-excel/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
};

// Imágenes de Productos - Múltiples fotos por producto
export const productosImagenesAPI = {
  getAll: (params) => apiClient.get('/productos-imagenes/', { params }),
  getById: (id) => apiClient.get(`/productos-imagenes/${id}/`),
  create: (formData) => apiClient.post('/productos-imagenes/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  update: (id, data) => apiClient.put(`/productos-imagenes/${id}/`, data),
  delete: (id) => apiClient.delete(`/productos-imagenes/${id}/`),
  // Establecer imagen como principal
  setPrincipal: (id) => apiClient.post(`/productos-imagenes/${id}/set_principal/`),
  // Obtener imágenes por producto
  porProducto: (productoId) => apiClient.get('/productos-imagenes/', { 
    params: { producto: productoId } 
  }),
};

// Documentos de Lotes - Facturas y contratos por lote
export const lotesDocumentosAPI = {
  getAll: (params) => apiClient.get('/lotes-documentos/', { params }),
  getById: (id) => apiClient.get(`/lotes-documentos/${id}/`),
  create: (formData) => apiClient.post('/lotes-documentos/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  update: (id, data) => apiClient.put(`/lotes-documentos/${id}/`, data),
  delete: (id) => apiClient.delete(`/lotes-documentos/${id}/`),
  // Obtener documentos por lote
  porLote: (loteId) => apiClient.get('/lotes-documentos/', { 
    params: { lote: loteId } 
  }),
};

// ISS-002 FIX: API de Catálogos - Sincronizar enums con backend
export const catalogosAPI = {
  // Obtener todos los catálogos en una sola llamada
  getAll: () => apiClient.get('/catalogos/'),
  // Catálogos específicos
  unidadesMedida: () => apiClient.get('/catalogos/unidades-medida/'),
  categorias: () => apiClient.get('/catalogos/categorias/'),
  viasAdministracion: () => apiClient.get('/catalogos/vias-administracion/'),
  estadosRequisicion: () => apiClient.get('/catalogos/estados-requisicion/'),
  tiposMovimiento: () => apiClient.get('/catalogos/tipos-movimiento/'),
  roles: () => apiClient.get('/catalogos/roles/'),
};

// ADMIN: Limpieza de datos del sistema
export const adminAPI = {
  // Obtener estadísticas de lo que se eliminaría por categoría
  getLimpiarDatosStats: () => apiClient.get('/admin/limpiar-datos/'),
  // Ejecutar limpieza selectiva (requiere {"confirmar": true, "categoria": "productos|lotes|requisiciones|movimientos|todos"})
  limpiarDatos: (confirmar = false, categoria = 'todos') => 
    apiClient.post('/admin/limpiar-datos/', { confirmar, categoria }),
};

// ISS-001 FIX: Health check API
// ISS-003 FIX (audit33): Validación flexible de respuesta
export const healthAPI = {
  check: async () => {
    const response = await publicApiClient.get(HEALTH_ENDPOINT, { timeout: HEALTH_TIMEOUT });
    
    // ISS-003: Normalizar respuesta de healthcheck
    // Diferentes backends pueden usar version/api_version/v, db_status/database/db
    const data = response.data || {};
    return {
      ...response,
      data: {
        ...data,
        version: data.version || data.api_version || data.v || API_VERSION,
        database: data.database ?? data.db_status ?? data.db ?? 'unknown',
        healthy: data.healthy ?? data.status === 'ok' ?? response.status === 200,
        timestamp: data.timestamp || new Date().toISOString(),
      }
    };
  },
  detailed: () => apiClient.get('/health/detailed/'),
};

export default apiClient;
