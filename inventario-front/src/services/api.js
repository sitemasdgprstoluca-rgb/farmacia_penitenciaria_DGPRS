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
  isLogoutInProgress
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
const HEALTH_TIMEOUT = parseInt(import.meta.env.VITE_HEALTHCHECK_TIMEOUT || '5000', 10);
const AUTH_ONLY_MODE = import.meta.env.VITE_AUTH_ONLY_MODE === 'true'; // Modo sin healthcheck

let apiHealthy = null; // null = no verificado, true = ok, false = fallo
let healthCheckSkipped = false; // Si se saltó por configuración

/**
 * ISS-001 FIX: Verificar conectividad y compatibilidad con el backend
 * Parametrizable via VITE_HEALTH_ENDPOINT y VITE_ENABLE_HEALTHCHECK
 * Degrada elegantemente si el endpoint no existe (404)
 * 
 * @param {Object} options - Opciones de configuración
 * @param {boolean} options.force - Forzar verificación aunque AUTH_ONLY_MODE esté activo
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
  
  try {
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
      details: data, // Incluir respuesta completa para debugging
    };
  } catch (error) {
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
    
    // Otros errores sí indican problemas
    apiHealthy = false;
    const errorMsg = status === 503
      ? 'Backend en mantenimiento (503)'
      : error.code === 'ECONNREFUSED' || error.code === 'ERR_NETWORK'
        ? 'No se puede conectar al servidor'
        : error.message || 'Error de conexión';
    
    console.warn('[API] Health check falló:', errorMsg, status ? `(${status})` : '');
    
    return {
      healthy: false,
      skipped: false,
      error: errorMsg,
      status: status,
      version: null,
    };
  }
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

      // El refresh token está en una cookie HttpOnly, no necesitamos enviarlo
      // El servidor lo lee automáticamente de la cookie
      try {
        // POST vacío - el servidor lee el refresh token de la cookie HttpOnly
        const response = await axios.post(
          `${apiBaseUrl}/token/refresh/`, 
          {}, // No enviamos refresh token en el body
          { withCredentials: true } // IMPORTANTE: incluir cookies
        );

        const newAccessToken = response.data.access;
        // Guardar nuevo access token en memoria
        setAccessToken(newAccessToken);
        
        // Actualizar headers del request original
        originalRequest.headers['Authorization'] = 'Bearer ' + newAccessToken;
        
        // Procesar cola de peticiones pendientes
        processQueue(null, newAccessToken);
        isRefreshing = false;
        
        // Reintentar request original
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        isRefreshing = false;
        
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
    if (status === 403) {
      toastDebounce.error('No tienes permisos para esta acción.');
    } else if (status >= 400 && status < 500) {
      if (detail) toastDebounce.error(detail);
    } else if (!error.response) {
      toastDebounce.error('Error al conectar con el servidor.');
    } else if (status >= 500) {
      toastDebounce.error('Error interno del servidor.');
    }
    return Promise.reject(error);
  }
);

/**
 * Descarga un blob como archivo local.
 * @param {Blob} blob
 * @param {string} nombreArchivo
 */
export const descargarArchivo = (blob, nombreArchivo) => {
  const contenido = blob && blob.data ? blob.data : blob;
  const url = window.URL.createObjectURL(contenido);
  const enlace = document.createElement('a');
  enlace.href = url;
  enlace.download = nombreArchivo;
  document.body.appendChild(enlace);
  enlace.click();
  document.body.removeChild(enlace);
  window.URL.revokeObjectURL(url);
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
};

// Lotes
export const lotesAPI = {
  getAll: (params) => apiClient.get('/lotes/', { params }),
  getById: (id) => apiClient.get(`/lotes/${id}/`),
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
export const authAPI = {
  // Login: recibe access token, refresh token va en cookie HttpOnly
  login: (credentials) => apiClient.post('/token/', credentials),
  // Refresh: el servidor lee el refresh token de la cookie HttpOnly
  refresh: () => apiClient.post('/token/refresh/', {}),
  // Logout: invalida la cookie del refresh token
  logout: (data = {}) => apiClient.post('/logout/', data),
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
  create: (data) => apiClient.post('/movimientos/', data),
  exportarExcel: (params) => apiClient.get('/movimientos/exportar-excel/', { params, responseType: 'blob' }),
  exportarPdf: (params) => apiClient.get('/movimientos/exportar-pdf/', { params, responseType: 'blob' }),
};

// Trazabilidad -  NUEVO
export const trazabilidadAPI = {
  producto: (clave, params = {}) => apiClient.get(`/trazabilidad/producto/${clave}/`, { params }),
  lote: (numeroLote, params = {}) => apiClient.get(`/trazabilidad/lote/${numeroLote}/`, { params }),
  exportarPdf: (clave) => apiClient.get(`/movimientos/trazabilidad-pdf/`, { 
    params: { producto_clave: clave }, 
    responseType: 'blob' 
  }),
  exportarLotePdf: (numeroLote) => apiClient.get(`/movimientos/trazabilidad-lote-pdf/`, { 
    params: { numero_lote: numeroLote }, 
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
  // Exportar
  exportar: (params) => apiClient.get('/donaciones/exportar/', { 
    params, 
    responseType: 'blob' 
  }),
};

// Detalles de Donación
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
};

// Salidas de Donaciones - Control de entregas del almacén de donaciones
export const salidasDonacionesAPI = {
  getAll: (params) => apiClient.get('/salidas-donaciones/', { params }),
  getById: (id) => apiClient.get(`/salidas-donaciones/${id}/`),
  create: (data) => apiClient.post('/salidas-donaciones/', data),
  // Solo lectura - no permite editar ni eliminar entregas
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

// ISS-001 FIX: Health check API
export const healthAPI = {
  check: () => publicApiClient.get('/health/', { timeout: 5000 }),
  detailed: () => apiClient.get('/health/detailed/'),
};

export default apiClient;
