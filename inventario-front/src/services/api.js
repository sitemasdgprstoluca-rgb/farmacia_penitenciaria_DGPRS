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
  clearTokens
} from './tokenManager';

const apiBaseUrl = (
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  'http://127.0.0.1:8000/api/'
).replace(/\/+$/, '');

const apiClient = axios.create({
  baseURL: `${apiBaseUrl}/`,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // IMPORTANTE: Enviar cookies en cada request
});

let activityCallback = null;
let lastForbiddenToast = { path: '', ts: 0 };
let redirectingToLogin = false;
let isRefreshing = false;
let failedQueue = [];

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
    if (status === 401 && !originalRequest._retry) {
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
        toast.error('Sesion expirada. Inicia sesion nuevamente.');
        redirectToLogin();
        return Promise.reject(refreshError);
      }
    }
    
    if (status === 403) {
      const shouldToast = currentPath !== lastForbiddenToast.path || (now - lastForbiddenToast.ts) > 4000;
      if (shouldToast) {
        toast.error('No tienes permisos para esta accion.');
        lastForbiddenToast = { path: currentPath, ts: now };
      }
    } else if (status >= 400 && status < 500) {
      if (detail) toast.error(detail);
    } else if (!error.response) {
      toast.error('Error al conectar con el servidor.');
    } else if (status >= 500) {
      toast.error('Error interno del servidor.');
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
  create: (data) => apiClient.post('/productos/', data),
  update: (id, data) => apiClient.put(`/productos/${id}/`, data),
  delete: (id) => apiClient.delete(`/productos/${id}/`),
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
  subirDocumento: (id, formData) => apiClient.post(`/lotes/${id}/subir-documento/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  eliminarDocumento: (id) => apiClient.delete(`/lotes/${id}/eliminar-documento/`),
  exportar: (params) => apiClient.get('/lotes/exportar-excel/', { 
    params, 
    responseType: 'blob' 
  }),
  importar: (formData) => apiClient.post('/lotes/importar-excel/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
};

// Centros
export const centrosAPI = {
  getAll: (params) => apiClient.get('/centros/', { params }),
  getById: (id) => apiClient.get(`/centros/${id}/`),
  create: (data) => apiClient.post('/centros/', data),
  update: (id, data) => apiClient.put(`/centros/${id}/`, data),
  delete: (id) => apiClient.delete(`/centros/${id}/`),
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
  exportar: () => apiClient.get('/usuarios/exportar-excel/', { responseType: 'blob' }),
  importar: (formData) => apiClient.post('/usuarios/importar-excel/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
};

// Requisiciones -  COMPLETO CON FLUJO
export const requisicionesAPI = {
  getAll: (params) => apiClient.get('/requisiciones/', { params }),
  getById: (id) => apiClient.get(`/requisiciones/${id}/`),
  create: (data) => apiClient.post('/requisiciones/', data),
  update: (id, data) => apiClient.put(`/requisiciones/${id}/`, data),
  delete: (id) => apiClient.delete(`/requisiciones/${id}/`),
  
  // Flujo de estados
  enviar: (id) => apiClient.post(`/requisiciones/${id}/enviar/`),
  autorizar: (id, data) => apiClient.post(`/requisiciones/${id}/autorizar/`, data),
  rechazar: (id, data) => apiClient.post(`/requisiciones/${id}/rechazar/`, data),
  surtir: (id) => apiClient.post(`/requisiciones/${id}/surtir/`),
  marcarRecibida: (id, data) => apiClient.post(`/requisiciones/${id}/marcar-recibida/`, data),
  cancelar: (id) => apiClient.post(`/requisiciones/${id}/cancelar/`),
  resumenEstados: () => apiClient.get('/requisiciones/resumen_estados/'),
  
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
  producto: (clave) => apiClient.get(`/trazabilidad/producto/${clave}/`),
  lote: (numeroLote) => apiClient.get(`/trazabilidad/lote/${numeroLote}/`),
  exportarPdf: (clave) => apiClient.get(`/movimientos/trazabilidad-pdf/`, { 
    params: { producto_clave: clave }, 
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
  marcarTodasLeidas: () => apiClient.post('/notificaciones/marcar-todas-leidas/'),
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

export default apiClient;
