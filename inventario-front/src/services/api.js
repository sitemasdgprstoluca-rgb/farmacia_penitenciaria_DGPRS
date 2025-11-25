import axios from 'axios';
import { toast } from 'react-hot-toast';

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
  withCredentials: true,
});

let activityCallback = null;
let lastForbiddenToast = { path: '', ts: 0 };
let redirectingToLogin = false;
export const setApiActivityHandler = (callback) => {
  activityCallback = callback;
};

const redirectToLogin = () => {
  if (redirectingToLogin) return;
  redirectingToLogin = true;
  localStorage.removeItem('token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
};

// Interceptor para añadir token
apiClient.interceptors.request.use(
  (config) => {
    if (activityCallback) {
      activityCallback();
    }
    const token = localStorage.getItem('token');
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
  (error) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail || error.response?.data?.error;
    const currentPath = window.location?.pathname || '';
    const now = Date.now();
    if (status === 401) {
      // Cancelar timers activos (polling de notificaciones)
      if (window.notificationInterval) {
        clearInterval(window.notificationInterval);
        window.notificationInterval = null;
      }
      // Emitir evento global para componentes que necesiten limpiar recursos
      window.dispatchEvent(new Event('session-expired'));
      toast.error('Sesion expirada. Inicia sesion nuevamente.');
      redirectToLogin();
    } else if (status === 403) {
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
  bajoStock: () => apiClient.get('/productos/bajo_stock/'),
  estadisticas: () => apiClient.get('/productos/estadisticas/'),
  exportar: (params) => apiClient.get('/productos/exportar_excel/', { 
    params, 
    responseType: 'blob' 
  }),
  importar: async (formData) => {
    try {
      return await apiClient.post('/productos/importar_excel/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    } catch (error) {
      if (error.response?.status === 405) {
        return await apiClient.post('/productos/importar-excel/', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      }
      throw error;
    }
  },
  auditoria: (id) => apiClient.get(`/productos/${id}/auditoria/`),
};

// Lotes
export const lotesAPI = {
  getAll: (params) => apiClient.get('/lotes/', { params }),
  getById: (id) => apiClient.get(`/lotes/${id}/`),
  create: (data) => apiClient.post('/lotes/', data),
  update: (id, data) => apiClient.put(`/lotes/${id}/`, data),
  delete: (id) => apiClient.delete(`/lotes/${id}/`),
  porCaducar: (dias = 90) => apiClient.get(`/lotes/por_caducar/?dias=${dias}`),
  vencidos: () => apiClient.get('/lotes/vencidos/'),
  ajustarStock: (id, data) => apiClient.post(`/lotes/${id}/ajustar_stock/`, data),
  exportar: (params) => apiClient.get('/lotes/exportar_excel/', { 
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
  exportar: (params) => apiClient.get('/centros/exportar/', { params, responseType: 'blob' }),
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
  cambiarPassword: (id, data) => apiClient.post(`/usuarios/${id}/cambiar_password/`, data),
  me: () => apiClient.get('/usuarios/me/'),
  actualizarPerfil: (data) => apiClient.patch('/usuarios/me/', data),
  cambiarPasswordPropio: (data) => apiClient.post('/usuarios/me/change-password/', data),
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
  cancelar: (id) => apiClient.post(`/requisiciones/${id}/cancelar/`),
  resumenEstados: () => apiClient.get('/requisiciones/resumen_estados/'),
  
  // Descarga de PDFs
  downloadPDFAceptacion: (id) => apiClient.get(`/requisiciones/${id}/hoja-recoleccion/`, {
    responseType: 'blob'
  }),
  downloadPDFRechazo: (id) => apiClient.get(`/requisiciones/${id}/pdf_rechazo/`, {
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
};

// Auth -  COMPLETO
export const authAPI = {
  login: (credentials) => apiClient.post('/token/', credentials),
  devLogin: (data = {}) => apiClient.post('/dev-autologin/', data),
  logout: (data = {}) => apiClient.post('/logout/', data),
  me: () => apiClient.get('/usuarios/me/'),
};

// Movimientos
export const movimientosAPI = {
  getAll: (params) => apiClient.get('/movimientos/', { params }),
  create: (data) => apiClient.post('/movimientos/', data),
  registrarPorCodigo: (data) => apiClient.post('/movimientos/registrar_por_codigo_barras/', data),
};

// Trazabilidad -  NUEVO
export const trazabilidadAPI = {
  producto: (clave) => apiClient.get(`/trazabilidad/producto/${clave}/`),
  lote: (numeroLote) => apiClient.get(`/trazabilidad/lote/${numeroLote}/`),
};

// Dashboard
export const dashboardAPI = {
  getResumen: () => apiClient.get('/dashboard/'),
};

// Reportes -  COMPLETO
export const reportesAPI = {
  // Reportes generales
  medicamentosPorCaducar: (params) => apiClient.get('/reportes/medicamentos_por_caducar/', { params }),
  bajoStock: () => apiClient.get('/reportes/bajo_stock/'),
  consumo: (params) => apiClient.get('/reportes/consumo/', { params }),

  // Reportes JSON
  inventario: (params) => apiClient.get('/reportes/inventario/', { params }),
  caducidades: (params) => apiClient.get('/reportes/caducidades/', { params }),
  requisiciones: (params) => apiClient.get('/reportes/requisiciones/', { params }),

  // Descargas
  exportarInventarioExcel: (params) => apiClient.get('/reportes/inventario/', {
    params: { ...params, formato: 'excel' },
    responseType: 'blob'
  }),

  // Precarga de datos
  precarga: () => apiClient.get('/reportes/precarga/'),
};

// Notificaciones
export const notificacionesAPI = {
  getAll: (params) => apiClient.get('/notificaciones/', { params }),
  marcarLeida: (id) => apiClient.post(`/notificaciones/${id}/marcar_leida/`),
  delete: (id) => apiClient.delete(`/notificaciones/${id}/`),
  noLeidasCount: () => apiClient.get('/notificaciones/no_leidas_count/'),
};

export default apiClient;
