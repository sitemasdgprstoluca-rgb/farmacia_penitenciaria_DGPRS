/**
 * Constantes centralizadas del sistema - Farmacia Penitenciaria
 * 
 * Este archivo centraliza todas las constantes utilizadas en el frontend
 * para mantener consistencia con el backend y facilitar el mantenimiento.
 * 
 * @module config/constants
 */

// ============================================
// ROLES DE USUARIO
// ============================================

/**
 * Roles disponibles en el sistema
 * Sincronizado con backend/core/constants.py
 */
export const ROLES = {
    ADMIN: 'ADMIN',
    FARMACEUTICO: 'FARMACEUTICO',
    ALMACENISTA: 'ALMACENISTA',
    MEDICO: 'MEDICO',
    CONSULTA: 'CONSULTA',
};

export const ROLES_LABELS = {
    [ROLES.ADMIN]: 'Administrador',
    [ROLES.FARMACEUTICO]: 'Farmacéutico',
    [ROLES.ALMACENISTA]: 'Almacenista',
    [ROLES.MEDICO]: 'Médico',
    [ROLES.CONSULTA]: 'Solo Consulta',
};

export const ROLES_LIST = Object.entries(ROLES_LABELS).map(([value, label]) => ({
    value,
    label,
}));

// ============================================
// TIPOS DE MOVIMIENTO
// ============================================

export const TIPO_MOVIMIENTO = {
    ENTRADA: 'ENTRADA',
    SALIDA: 'SALIDA',
    AJUSTE: 'AJUSTE',
    TRANSFERENCIA: 'TRANSFERENCIA',
    DEVOLUCION: 'DEVOLUCION',
    MERMA: 'MERMA',
    CADUCIDAD: 'CADUCIDAD',
};

export const TIPO_MOVIMIENTO_LABELS = {
    [TIPO_MOVIMIENTO.ENTRADA]: 'Entrada',
    [TIPO_MOVIMIENTO.SALIDA]: 'Salida',
    [TIPO_MOVIMIENTO.AJUSTE]: 'Ajuste de Inventario',
    [TIPO_MOVIMIENTO.TRANSFERENCIA]: 'Transferencia',
    [TIPO_MOVIMIENTO.DEVOLUCION]: 'Devolución',
    [TIPO_MOVIMIENTO.MERMA]: 'Merma',
    [TIPO_MOVIMIENTO.CADUCIDAD]: 'Caducidad',
};

export const TIPO_MOVIMIENTO_LIST = Object.entries(TIPO_MOVIMIENTO_LABELS).map(([value, label]) => ({
    value,
    label,
}));

// Colores para badges de movimientos
export const TIPO_MOVIMIENTO_COLORS = {
    [TIPO_MOVIMIENTO.ENTRADA]: 'bg-green-100 text-green-800',
    [TIPO_MOVIMIENTO.SALIDA]: 'bg-red-100 text-red-800',
    [TIPO_MOVIMIENTO.AJUSTE]: 'bg-yellow-100 text-yellow-800',
    [TIPO_MOVIMIENTO.TRANSFERENCIA]: 'bg-blue-100 text-blue-800',
    [TIPO_MOVIMIENTO.DEVOLUCION]: 'bg-purple-100 text-purple-800',
    [TIPO_MOVIMIENTO.MERMA]: 'bg-orange-100 text-orange-800',
    [TIPO_MOVIMIENTO.CADUCIDAD]: 'bg-gray-100 text-gray-800',
};

// ============================================
// CATEGORÍAS DE PRODUCTOS
// ============================================

export const CATEGORIA_PRODUCTO = {
    ANALGESICO: 'ANALGESICO',
    ANTIBIOTICO: 'ANTIBIOTICO',
    ANTIINFLAMATORIO: 'ANTIINFLAMATORIO',
    ANTIHIPERTENSIVO: 'ANTIHIPERTENSIVO',
    ANTIDIABETICO: 'ANTIDIABETICO',
    PSICOFARMACOS: 'PSICOFARMACOS',
    VITAMINAS: 'VITAMINAS',
    MATERIAL_CURACION: 'MATERIAL_CURACION',
    OTROS: 'OTROS',
};

export const CATEGORIA_PRODUCTO_LABELS = {
    [CATEGORIA_PRODUCTO.ANALGESICO]: 'Analgésico',
    [CATEGORIA_PRODUCTO.ANTIBIOTICO]: 'Antibiótico',
    [CATEGORIA_PRODUCTO.ANTIINFLAMATORIO]: 'Antiinflamatorio',
    [CATEGORIA_PRODUCTO.ANTIHIPERTENSIVO]: 'Antihipertensivo',
    [CATEGORIA_PRODUCTO.ANTIDIABETICO]: 'Antidiabético',
    [CATEGORIA_PRODUCTO.PSICOFARMACOS]: 'Psicofármacos',
    [CATEGORIA_PRODUCTO.VITAMINAS]: 'Vitaminas y Suplementos',
    [CATEGORIA_PRODUCTO.MATERIAL_CURACION]: 'Material de Curación',
    [CATEGORIA_PRODUCTO.OTROS]: 'Otros',
};

export const CATEGORIA_PRODUCTO_LIST = Object.entries(CATEGORIA_PRODUCTO_LABELS).map(([value, label]) => ({
    value,
    label,
}));

// ============================================
// TIPOS DE PRODUCTO
// ============================================

export const TIPO_PRODUCTO = {
    MEDICAMENTO: 'MEDICAMENTO',
    MATERIAL_CURACION: 'MATERIAL_CURACION',
    EQUIPO_MEDICO: 'EQUIPO_MEDICO',
    INSUMO: 'INSUMO',
};

export const TIPO_PRODUCTO_LABELS = {
    [TIPO_PRODUCTO.MEDICAMENTO]: 'Medicamento',
    [TIPO_PRODUCTO.MATERIAL_CURACION]: 'Material de Curación',
    [TIPO_PRODUCTO.EQUIPO_MEDICO]: 'Equipo Médico',
    [TIPO_PRODUCTO.INSUMO]: 'Insumo General',
};

export const TIPO_PRODUCTO_LIST = Object.entries(TIPO_PRODUCTO_LABELS).map(([value, label]) => ({
    value,
    label,
}));

// ============================================
// ESTADOS
// ============================================

export const ESTADO_LOTE = {
    ACTIVO: 'ACTIVO',
    AGOTADO: 'AGOTADO',
    CADUCADO: 'CADUCADO',
    BLOQUEADO: 'BLOQUEADO',
};

export const ESTADO_LOTE_LABELS = {
    [ESTADO_LOTE.ACTIVO]: 'Activo',
    [ESTADO_LOTE.AGOTADO]: 'Agotado',
    [ESTADO_LOTE.CADUCADO]: 'Caducado',
    [ESTADO_LOTE.BLOQUEADO]: 'Bloqueado',
};

export const ESTADO_LOTE_COLORS = {
    [ESTADO_LOTE.ACTIVO]: 'bg-green-100 text-green-800',
    [ESTADO_LOTE.AGOTADO]: 'bg-gray-100 text-gray-800',
    [ESTADO_LOTE.CADUCADO]: 'bg-red-100 text-red-800',
    [ESTADO_LOTE.BLOQUEADO]: 'bg-yellow-100 text-yellow-800',
};

// ============================================
// PRESENTACIONES
// ============================================

export const PRESENTACION = {
    TABLETA: 'TABLETA',
    CAPSULA: 'CAPSULA',
    JARABE: 'JARABE',
    AMPOLLA: 'AMPOLLA',
    CREMA: 'CREMA',
    GEL: 'GEL',
    SOLUCION: 'SOLUCION',
    SUSPENSION: 'SUSPENSION',
    INYECTABLE: 'INYECTABLE',
    SUPOSITORIO: 'SUPOSITORIO',
    PARCHE: 'PARCHE',
    SOBRE: 'SOBRE',
    SPRAY: 'SPRAY',
    GOTAS: 'GOTAS',
    OTRO: 'OTRO',
};

export const PRESENTACION_LABELS = {
    [PRESENTACION.TABLETA]: 'Tableta',
    [PRESENTACION.CAPSULA]: 'Cápsula',
    [PRESENTACION.JARABE]: 'Jarabe',
    [PRESENTACION.AMPOLLA]: 'Ampolla',
    [PRESENTACION.CREMA]: 'Crema',
    [PRESENTACION.GEL]: 'Gel',
    [PRESENTACION.SOLUCION]: 'Solución',
    [PRESENTACION.SUSPENSION]: 'Suspensión',
    [PRESENTACION.INYECTABLE]: 'Inyectable',
    [PRESENTACION.SUPOSITORIO]: 'Supositorio',
    [PRESENTACION.PARCHE]: 'Parche',
    [PRESENTACION.SOBRE]: 'Sobre',
    [PRESENTACION.SPRAY]: 'Spray',
    [PRESENTACION.GOTAS]: 'Gotas',
    [PRESENTACION.OTRO]: 'Otro',
};

export const PRESENTACION_LIST = Object.entries(PRESENTACION_LABELS).map(([value, label]) => ({
    value,
    label,
}));

// ============================================
// CONFIGURACIÓN DE API
// ============================================

export const API_CONFIG = {
    BASE_URL: import.meta.env.VITE_API_URL || '/api',
    TIMEOUT: 30000, // 30 segundos
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 1000, // 1 segundo
};

// ============================================
// PAGINACIÓN
// ============================================

export const PAGINATION = {
    DEFAULT_PAGE_SIZE: 20,
    PAGE_SIZE_OPTIONS: [10, 20, 50, 100],
    MAX_PAGE_SIZE: 100,
};

// ============================================
// ALERTAS DE INVENTARIO
// ============================================

export const ALERTAS = {
    DIAS_CADUCIDAD_PROXIMA: 90, // Alertar 90 días antes de caducidad
    DIAS_CADUCIDAD_CRITICA: 30, // Alerta crítica 30 días antes
    INVENTARIO_CRITICO_PORCENTAJE: 0.25, // 25% del inventario mínimo
};

// ============================================
// FORMATOS
// ============================================

export const FORMATOS = {
    FECHA: 'dd/MM/yyyy',
    FECHA_HORA: 'dd/MM/yyyy HH:mm',
    FECHA_ISO: 'yyyy-MM-dd',
    MONEDA: {
        locale: 'es-MX',
        currency: 'MXN',
    },
};

// ============================================
// MENSAJES COMUNES
// ============================================

export const MENSAJES = {
    EXITO: {
        CREAR: 'Registro creado exitosamente',
        ACTUALIZAR: 'Registro actualizado exitosamente',
        ELIMINAR: 'Registro eliminado exitosamente',
        GUARDAR: 'Cambios guardados exitosamente',
    },
    ERROR: {
        GENERAL: 'Ocurrió un error. Por favor intente nuevamente.',
        RED: 'Error de conexión. Verifique su conexión a internet.',
        SESION: 'Su sesión ha expirado. Por favor inicie sesión nuevamente.',
        PERMISOS: 'No tiene permisos para realizar esta acción.',
        VALIDACION: 'Por favor verifique los datos ingresados.',
    },
    CONFIRMACION: {
        ELIMINAR: '¿Está seguro de que desea eliminar este registro?',
        CANCELAR: '¿Está seguro de que desea cancelar? Los cambios no guardados se perderán.',
        SALIR: '¿Está seguro de que desea salir?',
    },
};

// ============================================
// PERMISOS POR ROL
// ============================================

export const PERMISOS_POR_ROL = {
    [ROLES.ADMIN]: {
        productos: { ver: true, crear: true, editar: true, eliminar: true },
        lotes: { ver: true, crear: true, editar: true, eliminar: true },
        movimientos: { ver: true, crear: true, editar: true, eliminar: true },
        usuarios: { ver: true, crear: true, editar: true, eliminar: true },
        reportes: { ver: true, exportar: true },
        configuracion: { ver: true, editar: true },
    },
    [ROLES.FARMACEUTICO]: {
        productos: { ver: true, crear: true, editar: true, eliminar: false },
        lotes: { ver: true, crear: true, editar: true, eliminar: false },
        movimientos: { ver: true, crear: true, editar: false, eliminar: false },
        usuarios: { ver: false, crear: false, editar: false, eliminar: false },
        reportes: { ver: true, exportar: true },
        configuracion: { ver: false, editar: false },
    },
    [ROLES.ALMACENISTA]: {
        productos: { ver: true, crear: false, editar: false, eliminar: false },
        lotes: { ver: true, crear: true, editar: true, eliminar: false },
        movimientos: { ver: true, crear: true, editar: false, eliminar: false },
        usuarios: { ver: false, crear: false, editar: false, eliminar: false },
        reportes: { ver: true, exportar: false },
        configuracion: { ver: false, editar: false },
    },
    [ROLES.MEDICO]: {
        productos: { ver: true, crear: false, editar: false, eliminar: false },
        lotes: { ver: true, crear: false, editar: false, eliminar: false },
        movimientos: { ver: true, crear: false, editar: false, eliminar: false },
        usuarios: { ver: false, crear: false, editar: false, eliminar: false },
        reportes: { ver: true, exportar: false },
        configuracion: { ver: false, editar: false },
    },
    [ROLES.CONSULTA]: {
        productos: { ver: true, crear: false, editar: false, eliminar: false },
        lotes: { ver: true, crear: false, editar: false, eliminar: false },
        movimientos: { ver: true, crear: false, editar: false, eliminar: false },
        usuarios: { ver: false, crear: false, editar: false, eliminar: false },
        reportes: { ver: true, exportar: false },
        configuracion: { ver: false, editar: false },
    },
};

// ============================================
// COLORES DEL TEMA
// ============================================

export const THEME_COLORS = {
    primary: '#9F2241',
    secondary: '#6B1839',
    accent: '#EED5DD',
    success: '#10B981',
    warning: '#F59E0B',
    error: '#EF4444',
    info: '#3B82F6',
};

// ============================================
// RUTAS DE NAVEGACIÓN
// ============================================

export const ROUTES = {
    HOME: '/',
    LOGIN: '/login',
    DASHBOARD: '/dashboard',
    PRODUCTOS: '/productos',
    PRODUCTO_NUEVO: '/productos/nuevo',
    PRODUCTO_EDITAR: '/productos/:id/editar',
    LOTES: '/lotes',
    LOTE_NUEVO: '/lotes/nuevo',
    MOVIMIENTOS: '/movimientos',
    MOVIMIENTO_NUEVO: '/movimientos/nuevo',
    REQUISICIONES: '/requisiciones',
    REQUISICION_NUEVA: '/requisiciones/nueva',
    USUARIOS: '/usuarios',
    USUARIO_NUEVO: '/usuarios/nuevo',
    REPORTES: '/reportes',
    CONFIGURACION: '/configuracion',
    PERFIL: '/perfil',
};

// ============================================
// HELPERS
// ============================================

/**
 * Obtiene el label de un valor de constante
 * @param {Object} labelsMap - Mapa de valor -> label
 * @param {string} value - Valor a buscar
 * @param {string} defaultLabel - Label por defecto si no se encuentra
 * @returns {string} Label correspondiente
 */
export const getLabel = (labelsMap, value, defaultLabel = 'Desconocido') => {
    return labelsMap[value] || defaultLabel;
};

/**
 * Obtiene el color de un valor de constante
 * @param {Object} colorsMap - Mapa de valor -> clases CSS
 * @param {string} value - Valor a buscar
 * @param {string} defaultColor - Color por defecto
 * @returns {string} Clases CSS correspondientes
 */
export const getColor = (colorsMap, value, defaultColor = 'bg-gray-100 text-gray-800') => {
    return colorsMap[value] || defaultColor;
};

/**
 * Verifica si un rol tiene un permiso específico
 * @param {string} rol - Rol del usuario
 * @param {string} modulo - Módulo a verificar (ej: 'productos')
 * @param {string} accion - Acción a verificar (ej: 'crear')
 * @returns {boolean} true si tiene permiso
 */
export const tienePermiso = (rol, modulo, accion) => {
    const permisos = PERMISOS_POR_ROL[rol];
    if (!permisos) return false;
    const permisosModulo = permisos[modulo];
    if (!permisosModulo) return false;
    return permisosModulo[accion] === true;
};

export default {
    ROLES,
    ROLES_LABELS,
    ROLES_LIST,
    TIPO_MOVIMIENTO,
    TIPO_MOVIMIENTO_LABELS,
    TIPO_MOVIMIENTO_LIST,
    TIPO_MOVIMIENTO_COLORS,
    CATEGORIA_PRODUCTO,
    CATEGORIA_PRODUCTO_LABELS,
    CATEGORIA_PRODUCTO_LIST,
    TIPO_PRODUCTO,
    TIPO_PRODUCTO_LABELS,
    TIPO_PRODUCTO_LIST,
    ESTADO_LOTE,
    ESTADO_LOTE_LABELS,
    ESTADO_LOTE_COLORS,
    PRESENTACION,
    PRESENTACION_LABELS,
    PRESENTACION_LIST,
    API_CONFIG,
    PAGINATION,
    ALERTAS,
    FORMATOS,
    MENSAJES,
    PERMISOS_POR_ROL,
    THEME_COLORS,
    ROUTES,
    getLabel,
    getColor,
    tienePermiso,
};
