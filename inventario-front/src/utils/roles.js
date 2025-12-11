/**
 * FRONT-006 FIX: Lógica de roles centralizada
 * 
 * Este módulo centraliza todas las verificaciones de roles y permisos
 * para evitar duplicación de lógica en múltiples componentes.
 * 
 * ROLES SOPORTADOS:
 * - ADMIN: admin, admin_sistema, superusuario
 * - FARMACIA: farmacia, admin_farmacia
 * - CENTRO: centro, medico, administrador_centro, director_centro, usuario_normal
 * - VISTA: vista, usuario_vista
 * 
 * FLUJO V2: Los roles específicos del centro (medico, administrador_centro, 
 * director_centro) mapean a CENTRO para navegación pero mantienen su rol
 * específico para acciones de autorización.
 */

// Roles que tienen privilegios de administrador
export const ADMIN_ROLES = ['admin', 'admin_sistema', 'superusuario'];

// Roles que tienen privilegios de farmacia
export const FARMACIA_ROLES = ['farmacia', 'admin_farmacia'];

// Roles del centro penitenciario (FLUJO V2)
export const CENTRO_ROLES = ['centro', 'medico', 'administrador_centro', 'director_centro', 'usuario_normal', 'usuario_centro'];

// Roles de solo vista
export const VISTA_ROLES = ['vista', 'usuario_vista'];

// Roles con acceso a gestión de farmacia (ADMIN + FARMACIA)
export const FARMACIA_ADMIN_ROLES = [...ADMIN_ROLES, ...FARMACIA_ROLES];

/**
 * Normaliza el rol a su forma canónica
 * @param {string} rol - Rol del usuario
 * @returns {string} - Rol normalizado (lowercase)
 */
export const normalizarRol = (rol) => (rol || '').toLowerCase().trim();

/**
 * Verifica si el usuario es administrador del sistema
 * @param {Object} user - Usuario o permisos
 * @returns {boolean}
 */
export const esAdmin = (user) => {
  if (!user) return false;
  if (user.is_superuser === true || user.isSuperuser === true) return true;
  const rol = normalizarRol(user.rol);
  return ADMIN_ROLES.includes(rol);
};

/**
 * Verifica si el usuario es personal de farmacia
 * @param {Object} user - Usuario o permisos
 * @returns {boolean}
 */
export const esFarmacia = (user) => {
  if (!user) return false;
  const rol = normalizarRol(user.rol);
  return FARMACIA_ROLES.includes(rol);
};

/**
 * Verifica si el usuario es de farmacia o admin
 * @param {Object} user - Usuario o permisos
 * @returns {boolean}
 */
export const esFarmaciaAdmin = (user) => {
  if (!user) return false;
  if (user.is_superuser === true || user.isSuperuser === true) return true;
  const rol = normalizarRol(user.rol);
  return FARMACIA_ADMIN_ROLES.includes(rol);
};

/**
 * Verifica si el usuario es del centro penitenciario
 * @param {Object} user - Usuario o permisos
 * @returns {boolean}
 */
export const esCentro = (user) => {
  if (!user) return false;
  const rol = normalizarRol(user.rol);
  return CENTRO_ROLES.includes(rol);
};

/**
 * Verifica si el usuario es solo vista
 * @param {Object} user - Usuario o permisos
 * @returns {boolean}
 */
export const esVista = (user) => {
  if (!user) return false;
  const rol = normalizarRol(user.rol);
  return VISTA_ROLES.includes(rol);
};

/**
 * Verifica si el usuario puede ver datos globales (no solo de su centro)
 * @param {Object} user - Usuario o permisos
 * @param {Object} permisos - Permisos calculados (opcional)
 * @returns {boolean}
 */
export const puedeVerGlobal = (user, permisos = null) => {
  if (!user) return false;
  if (permisos?.isSuperuser === true || user.is_superuser === true) return true;
  return esAdmin(user) || esFarmacia(user) || esVista(user);
};

/**
 * Obtiene el rol principal normalizado para navegación
 * @param {Object} user - Usuario
 * @param {Array} grupos - Grupos del usuario
 * @returns {string} - 'ADMIN' | 'FARMACIA' | 'CENTRO' | 'VISTA' | 'SIN_ROL'
 */
export const getRolPrincipal = (user, grupos = []) => {
  if (!user) return 'SIN_ROL';
  
  const isSuperuser = user.is_superuser === true;
  const rol = normalizarRol(user.rol);
  const groupNames = (grupos || []).map((g) => ((g.name || g) + '').toUpperCase());
  
  // Primero verificar superusuario
  if (isSuperuser) return 'ADMIN';
  
  // Luego verificar por rol específico
  if (ADMIN_ROLES.includes(rol)) return 'ADMIN';
  if (FARMACIA_ROLES.includes(rol) || groupNames.includes('FARMACIA_ADMIN')) return 'FARMACIA';
  if (CENTRO_ROLES.includes(rol) || groupNames.includes('CENTRO_USER')) return 'CENTRO';
  if (VISTA_ROLES.includes(rol) || groupNames.includes('VISTA_USER')) return 'VISTA';
  
  // Si el usuario está autenticado pero sin rol específico, verificar permisos de staff
  if (user.is_staff) return 'FARMACIA';
  
  return 'SIN_ROL';
};

/**
 * Verifica si un rol tiene acceso a un módulo específico
 * @param {string} rolPrincipal - Rol normalizado (ADMIN, FARMACIA, CENTRO, VISTA)
 * @param {string} modulo - Nombre del módulo
 * @param {Object} permisos - Permisos del usuario (opcional)
 * @returns {boolean}
 */
export const tieneAccesoModulo = (rolPrincipal, modulo, permisos = null) => {
  // Si tiene el permiso específico del módulo, usarlo
  const permisoKey = `ver${modulo.charAt(0).toUpperCase() + modulo.slice(1)}`;
  if (permisos && typeof permisos[permisoKey] === 'boolean') {
    return permisos[permisoKey];
  }
  
  // Fallback por rol
  const ACCESO_POR_ROL = {
    ADMIN: true, // Admin ve todo
    FARMACIA: ['dashboard', 'productos', 'lotes', 'requisiciones', 'centros', 'usuarios', 'reportes', 'trazabilidad', 'movimientos', 'donaciones', 'notificaciones', 'perfil'].includes(modulo.toLowerCase()),
    CENTRO: ['dashboard', 'productos', 'lotes', 'requisiciones', 'movimientos', 'notificaciones', 'perfil'].includes(modulo.toLowerCase()),
    VISTA: ['dashboard', 'productos', 'lotes', 'requisiciones', 'centros', 'usuarios', 'reportes', 'movimientos', 'donaciones', 'notificaciones', 'perfil'].includes(modulo.toLowerCase()),
    SIN_ROL: false,
  };
  
  return ACCESO_POR_ROL[rolPrincipal] || false;
};

/**
 * FLUJO V2: Verifica si el usuario puede ejecutar una acción del flujo
 * @param {Object} user - Usuario
 * @param {string} accion - Acción del flujo (enviar_admin, autorizar_admin, etc.)
 * @returns {boolean}
 */
export const puedeEjecutarAccionFlujo = (user, accion) => {
  if (!user) return false;
  if (user.is_superuser === true) return true;
  
  const rol = normalizarRol(user.rol);
  
  const ACCIONES_POR_ROL = {
    enviar_admin: ['medico', ...ADMIN_ROLES, ...FARMACIA_ROLES],
    autorizar_admin: ['administrador_centro', ...ADMIN_ROLES],
    autorizar_director: ['director_centro', ...ADMIN_ROLES],
    recibir_farmacia: [...FARMACIA_ROLES, ...ADMIN_ROLES],
    autorizar_farmacia: [...FARMACIA_ROLES, ...ADMIN_ROLES],
    surtir: [...FARMACIA_ROLES, ...ADMIN_ROLES],
    confirmar_entrega: ['medico', 'centro', ...ADMIN_ROLES, ...FARMACIA_ROLES],
    devolver: ['administrador_centro', 'director_centro', ...FARMACIA_ROLES, ...ADMIN_ROLES],
    reenviar: ['medico', 'centro', ...ADMIN_ROLES],
    rechazar: ['administrador_centro', 'director_centro', ...FARMACIA_ROLES, ...ADMIN_ROLES],
    cancelar: ['medico', 'centro', ...FARMACIA_ROLES, ...ADMIN_ROLES],
  };
  
  const rolesPermitidos = ACCIONES_POR_ROL[accion] || [];
  return rolesPermitidos.includes(rol);
};

// Exportar todo para uso flexible
export default {
  ADMIN_ROLES,
  FARMACIA_ROLES,
  CENTRO_ROLES,
  VISTA_ROLES,
  FARMACIA_ADMIN_ROLES,
  normalizarRol,
  esAdmin,
  esFarmacia,
  esFarmaciaAdmin,
  esCentro,
  esVista,
  puedeVerGlobal,
  getRolPrincipal,
  tieneAccesoModulo,
  puedeEjecutarAccionFlujo,
};
