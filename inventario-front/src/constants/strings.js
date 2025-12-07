/**
 * ISS-009: Constantes de texto centralizadas
 * 
 * Este archivo centraliza todos los textos de la UI para:
 * - Facilitar correcciones y actualizaciones
 * - Preparar el sistema para internacionalización (i18n)
 * - Mantener consistencia en mensajes de error y etiquetas
 */

// ========================================
// MENSAJES DE ERROR COMUNES
// ========================================
export const ERRORS = {
  // Autenticación
  LOGIN_FAILED: 'Credenciales inválidas',
  SESSION_EXPIRED: 'Tu sesión ha expirado. Por favor, inicia sesión nuevamente.',
  UNAUTHORIZED: 'No tienes permisos para realizar esta acción',
  
  // Operaciones CRUD
  CREATE_FAILED: 'Error al crear el registro',
  UPDATE_FAILED: 'Error al actualizar el registro',
  DELETE_FAILED: 'Error al eliminar el registro',
  LOAD_FAILED: 'Error al cargar los datos',
  
  // Validación
  REQUIRED_FIELD: 'Este campo es obligatorio',
  INVALID_FORMAT: 'Formato inválido',
  MIN_LENGTH: (min) => `Mínimo ${min} caracteres`,
  MAX_LENGTH: (max) => `Máximo ${max} caracteres`,
  MIN_VALUE: (min) => `El valor mínimo es ${min}`,
  MAX_VALUE: (max) => `El valor máximo es ${max}`,
  
  // Stock
  STOCK_INSUFFICIENT: 'Stock insuficiente',
  STOCK_NEGATIVE: 'La cantidad no puede ser negativa',
  STOCK_EXCEEDED: 'La cantidad excede el stock disponible',
  
  // Requisiciones
  REQUISICION_EMPTY: 'Agrega al menos un producto',
  REQUISICION_NO_LOTE: 'Selecciona el lote para cada producto',
  REQUISICION_NO_CENTRO: 'Debes seleccionar un centro',
  
  // Genéricos
  SERVER_ERROR: 'Error del servidor. Intenta más tarde.',
  NETWORK_ERROR: 'Error de conexión. Verifica tu internet.',
  UNKNOWN_ERROR: 'Ocurrió un error inesperado',
};

// ========================================
// MENSAJES DE ÉXITO
// ========================================
export const SUCCESS = {
  // CRUD
  CREATED: 'Registro creado exitosamente',
  UPDATED: 'Registro actualizado exitosamente',
  DELETED: 'Registro eliminado exitosamente',
  SAVED: 'Cambios guardados',
  
  // Autenticación
  LOGIN_SUCCESS: 'Inicio de sesión exitoso',
  LOGOUT_SUCCESS: 'Sesión cerrada correctamente',
  PASSWORD_CHANGED: 'Contraseña actualizada correctamente',
  PASSWORD_RESET_SENT: 'Se ha enviado un correo con las instrucciones',
  
  // Requisiciones
  REQUISICION_CREATED: 'Requisición creada exitosamente',
  REQUISICION_UPDATED: 'Requisición actualizada',
  REQUISICION_SENT: 'Requisición enviada correctamente',
  REQUISICION_AUTHORIZED: 'Requisición autorizada',
  REQUISICION_REJECTED: 'Requisición rechazada',
  REQUISICION_FILLED: 'Requisición surtida correctamente',
  REQUISICION_RECEIVED: 'Recepción confirmada',
  
  // Movimientos
  MOVEMENT_REGISTERED: 'Movimiento registrado',
  STOCK_ADJUSTED: 'Stock ajustado correctamente',
  
  // Exportación
  EXPORT_SUCCESS: 'Archivo exportado correctamente',
};

// ========================================
// CONFIRMACIONES
// ========================================
export const CONFIRM = {
  DELETE: '¿Estás seguro de que deseas eliminar este registro?',
  DELETE_WITH_NAME: (name) => `¿Estás seguro de que deseas eliminar "${name}"?`,
  CANCEL_CHANGES: '¿Descartar los cambios sin guardar?',
  LOGOUT: '¿Cerrar sesión?',
  
  // Requisiciones
  SEND_REQUISICION: (folio) => `¿Enviar la requisición ${folio}?`,
  AUTHORIZE_REQUISICION: (folio) => `¿Autorizar la requisición ${folio}?`,
  REJECT_REQUISICION: (folio) => `¿Rechazar la requisición ${folio}?`,
  FILL_REQUISICION: (folio) => `¿Surtir la requisición ${folio}?`,
  CANCEL_REQUISICION: (folio) => `¿Cancelar la requisición ${folio}?`,
  CONFIRM_RECEPTION: (folio) => `¿Confirmar recepción de la requisición ${folio}?`,
};

// ========================================
// ETIQUETAS DE UI
// ========================================
export const LABELS = {
  // Botones comunes
  SAVE: 'Guardar',
  CANCEL: 'Cancelar',
  DELETE: 'Eliminar',
  EDIT: 'Editar',
  CREATE: 'Crear',
  SEARCH: 'Buscar',
  FILTER: 'Filtrar',
  CLEAR_FILTERS: 'Limpiar filtros',
  EXPORT: 'Exportar',
  IMPORT: 'Importar',
  CLOSE: 'Cerrar',
  CONFIRM: 'Confirmar',
  BACK: 'Volver',
  NEXT: 'Siguiente',
  PREVIOUS: 'Anterior',
  LOADING: 'Cargando...',
  PROCESSING: 'Procesando...',
  
  // Autenticación
  LOGIN: 'Iniciar sesión',
  LOGOUT: 'Cerrar sesión',
  EMAIL: 'Correo electrónico',
  PASSWORD: 'Contraseña',
  USERNAME: 'Usuario',
  REMEMBER_ME: 'Recordarme',
  FORGOT_PASSWORD: '¿Olvidaste tu contraseña?',
  
  // Navegación
  DASHBOARD: 'Dashboard',
  PRODUCTS: 'Productos',
  LOTS: 'Lotes',
  MOVEMENTS: 'Movimientos',
  REQUISITIONS: 'Requisiciones',
  USERS: 'Usuarios',
  CENTERS: 'Centros',
  REPORTS: 'Reportes',
  AUDIT: 'Auditoría',
  SETTINGS: 'Configuración',
  
  // Estados
  ACTIVE: 'Activo',
  INACTIVE: 'Inactivo',
  PENDING: 'Pendiente',
  APPROVED: 'Aprobado',
  REJECTED: 'Rechazado',
  CANCELLED: 'Cancelado',
  COMPLETED: 'Completado',
  
  // Requisiciones - ISS-DB-002: Alineados con BD Supabase
  DRAFT: 'Borrador',
  SENT: 'Enviada',            // BD: 'enviada'
  AUTHORIZED: 'Autorizada',
  IN_SURTIDO: 'En Surtido',   // BD: 'en_surtido'
  PARTIAL: 'Parcial',         // BD: 'parcial'
  FILLED: 'Surtida',
  DELIVERED: 'Entregada',     // BD: 'entregada'
  RECEIVED: 'Entregada',      // Alias para compatibilidad
  IN_TRANSIT: 'En tránsito',
  
  // Tabla
  ACTIONS: 'Acciones',
  NO_RESULTS: 'Sin resultados',
  SHOWING: (from, to, total) => `Mostrando ${from}-${to} de ${total}`,
  ROWS_PER_PAGE: 'Filas por página',
};

// ========================================
// PLACEHOLDERS
// ========================================
export const PLACEHOLDERS = {
  SEARCH: 'Buscar...',
  SEARCH_PRODUCTS: 'Buscar productos...',
  SELECT_OPTION: 'Selecciona una opción',
  SELECT_CENTER: 'Selecciona un centro',
  SELECT_DATE: 'Selecciona una fecha',
  ENTER_QUANTITY: 'Ingresa cantidad',
  WRITE_OBSERVATION: 'Escribe una observación...',
  WRITE_REASON: 'Escribe el motivo...',
};

// ========================================
// ROLES Y PERMISOS
// ========================================
export const ROLES = {
  ADMIN: 'Administrador',
  FARMACIA: 'Farmacia',
  CENTRO: 'Centro',
  VISTA: 'Solo Vista',
  SIN_ROL: 'Sin Rol',
};

// ========================================
// TIPOS DE MOVIMIENTO - ISS-DB-001: Alineados con BD Supabase
// ========================================
export const MOVEMENT_TYPES = {
  ENTRADA: 'Entrada',
  SALIDA: 'Salida',
  TRANSFERENCIA: 'Transferencia',
  AJUSTE_POSITIVO: 'Ajuste Positivo',
  AJUSTE_NEGATIVO: 'Ajuste Negativo',
  DEVOLUCION: 'Devolución',
  MERMA: 'Merma',
  CADUCIDAD: 'Caducidad',
};

// Valores para selectores (keys son los valores que espera la BD)
export const MOVEMENT_TYPES_OPTIONS = [
  { value: 'entrada', label: 'Entrada' },
  { value: 'salida', label: 'Salida' },
  { value: 'transferencia', label: 'Transferencia' },
  { value: 'ajuste_positivo', label: 'Ajuste Positivo' },
  { value: 'ajuste_negativo', label: 'Ajuste Negativo' },
  { value: 'devolucion', label: 'Devolución' },
  { value: 'merma', label: 'Merma' },
  { value: 'caducidad', label: 'Caducidad' },
];

// ISS-DB-002: Estados de requisición alineados con BD Supabase
// BD permite: borrador, enviada, autorizada, rechazada, en_surtido, surtida, parcial, cancelada, entregada
export const REQUISICION_ESTADOS = {
  BORRADOR: { value: 'borrador', label: 'Borrador', color: 'gray' },
  ENVIADA: { value: 'enviada', label: 'Enviada', color: 'yellow' },
  AUTORIZADA: { value: 'autorizada', label: 'Autorizada', color: 'blue' },
  EN_SURTIDO: { value: 'en_surtido', label: 'En Surtido', color: 'orange' },
  PARCIAL: { value: 'parcial', label: 'Parcialmente Surtida', color: 'purple' },
  RECHAZADA: { value: 'rechazada', label: 'Rechazada', color: 'red' },
  SURTIDA: { value: 'surtida', label: 'Surtida', color: 'indigo' },
  ENTREGADA: { value: 'entregada', label: 'Entregada', color: 'green' },
  CANCELADA: { value: 'cancelada', label: 'Cancelada', color: 'gray' },
};

// Lista para selectores de estado
export const REQUISICION_ESTADOS_OPTIONS = Object.values(REQUISICION_ESTADOS);

// ========================================
// SUBTIPOS DE SALIDA (MEJORA FLUJO 5)
// ========================================
export const SUBTIPOS_SALIDA = {
  RECETA: { value: 'receta', label: 'Receta Médica', requiresExpediente: true },
  CONSUMO_INTERNO: { value: 'consumo_interno', label: 'Consumo Interno', requiresExpediente: false },
  MERMA: { value: 'merma', label: 'Merma', requiresExpediente: false },
  CADUCIDAD: { value: 'caducidad', label: 'Caducidad', requiresExpediente: false },
  TRANSFERENCIA: { value: 'transferencia', label: 'Transferencia', requiresExpediente: false },
  OTRO: { value: 'otro', label: 'Otro', requiresExpediente: false },
};

// Lista para selectores
export const SUBTIPOS_SALIDA_OPTIONS = Object.values(SUBTIPOS_SALIDA);

// ========================================
// MOTIVOS DE AJUSTE SUGERIDOS (MEJORA FLUJO 3)
// ========================================
export const MOTIVOS_AJUSTE_SUGERIDOS = [
  'Stock insuficiente en almacén',
  'Cantidad solicitada excede el promedio mensual',
  'Producto próximo a caducar - se reduce cantidad',
  'Ajuste por inventario físico',
  'Prioridad de abastecimiento a otro centro',
  'Otro (especificar)',
];

// ========================================
// HELPERS PARA FORMATEO
// ========================================
export const formatters = {
  /**
   * Formatea un número como moneda
   * @param {number} value - Valor a formatear
   * @param {string} currency - Código de moneda (MXN, USD)
   */
  currency: (value, currency = 'MXN') => {
    return new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency,
    }).format(value || 0);
  },
  
  /**
   * Formatea una fecha
   * @param {string|Date} date - Fecha a formatear
   * @param {object} options - Opciones de Intl.DateTimeFormat
   */
  date: (date, options = {}) => {
    if (!date) return '-';
    const defaultOptions = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Intl.DateTimeFormat('es-MX', { ...defaultOptions, ...options })
      .format(new Date(date));
  },
  
  /**
   * Formatea fecha y hora
   * @param {string|Date} date - Fecha a formatear
   */
  datetime: (date) => {
    if (!date) return '-';
    return new Intl.DateTimeFormat('es-MX', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(date));
  },
  
  /**
   * Formatea un número con separadores de miles
   * @param {number} value - Valor a formatear
   */
  number: (value) => {
    return new Intl.NumberFormat('es-MX').format(value || 0);
  },
};

// ========================================
// EXPORT POR DEFECTO
// ========================================
export default {
  ERRORS,
  SUCCESS,
  CONFIRM,
  LABELS,
  PLACEHOLDERS,
  ROLES,
  MOVEMENT_TYPES,
  formatters,
};
