import axios from 'axios';

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

// Interceptor para aÃ±adir token
apiClient.interceptors.request.use(
  (config) => {
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
};

// Usuarios -  COMPLETO
export const usuariosAPI = {
  getAll: (params) => apiClient.get('/usuarios/', { params }),
  getById: (id) => apiClient.get(`/usuarios/${id}/`),
  create: (data) => apiClient.post('/usuarios/', data),
  update: (id, data) => apiClient.put(`/usuarios/${id}/`, data),
  delete: (id) => apiClient.delete(`/usuarios/${id}/`),
  cambiarPassword: (id, data) => apiClient.post(`/usuarios/${id}/cambiar_password/`, data),
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
  
  // Hoja de recoleccin
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
  logout: () => apiClient.post('/auth/logout/'),
  me: () => apiClient.get('/me/'),
  register: (data) => apiClient.post('/auth/register/', data),
};

// Movimientos
export const movimientosAPI = {
  getAll: (params) => apiClient.get('/movimientos/', { params }),
  create: (data) => apiClient.post('/movimientos/', data),
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
  
  // Nuevos reportes implementados
  inventario: (params) => apiClient.get('/reportes/inventario/', { 
    params, 
    responseType: 'blob' 
  }),
  movimientos: (params) => apiClient.get('/reportes/movimientos/', { 
    params, 
    responseType: 'blob' 
  }),
  caducidades: (params) => apiClient.get('/reportes/caducidades/', { 
    params, 
    responseType: 'blob' 
  }),
  
  // Precarga de datos
  precarga: () => apiClient.get('/reportes/precarga/'),
};

export default apiClient;
