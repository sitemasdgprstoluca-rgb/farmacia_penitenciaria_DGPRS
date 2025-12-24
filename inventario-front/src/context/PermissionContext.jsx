import { useEffect, useState, useCallback, useRef } from 'react';
import { PermissionContext } from './contexts';
import apiClient, { authAPI } from '../services/api';
import { setAccessToken, hasAccessToken, migrateFromLocalStorage, isLogoutInProgress } from '../services/tokenManager';
// ISS-009 FIX: Usar lógica de roles centralizada
// ISS-AUDIT FIX: getRolPrincipal importado como getRolPrincipalUtil, función local getRolPrincipal para navegación
import { 
  getRolPrincipal as getRolPrincipalUtil, 
  esAdmin, 
  esFarmacia, 
  esFarmaciaAdmin as esFarmaciaAdminUtil, 
  esCentro, 
  esVista,
  puedeEjecutarAccionFlujo,
} from '../utils/roles';

/**
 * ISS-001 FIX (audit28): Permisos del backend tienen prioridad
 * ISS-002 FIX (audit28): Validar sesión ANTES de hidratar UI
 * ISS-005 FIX (audit28): Minimizar datos en localStorage
 * ISS-009 FIX (audit30): Lógica de roles centralizada en utils/roles.js
 * 
 * Roles soportados por el front:
 * ADMIN (admin_sistema / superusuario)
 * FARMACIA (farmacia / admin_farmacia / grupo FARMACIA_ADMIN)
 * CENTRO (centro / usuario_normal / grupo CENTRO_USER)
 * VISTA (vista / usuario_vista / grupo VISTA_USER)
 * 
 * Los permisos vienen del backend calculados (rol + personalizados)
 */

// ISS-005 FIX: Claves mínimas para sessionStorage (más seguro que localStorage)
const SESSION_KEYS = {
  USER_ID: 'session_uid',
  USER_ROLE: 'session_role',
  SESSION_HASH: 'session_hash',
};

// ISS-005 FIX: Generar hash simple para detectar manipulación
const generateSessionHash = (userId, role) => {
  const data = `${userId}:${role}:${Date.now()}`;
  let hash = 0;
  for (let i = 0; i < data.length; i++) {
    const char = data.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return hash.toString(36);
};

// ISS-001 FIX: Permisos por rol como FALLBACK SOLAMENTE
// El backend siempre tiene prioridad cuando envía permisos
const PERMISOS_POR_ROL = {
  ADMIN: {
    verDashboard: true,
    verProductos: true,
    verLotes: true,
    verRequisiciones: true,
    verCentros: true,
    verUsuarios: true,
    verReportes: true,
    verTrazabilidad: true,
    verAuditoria: true,
    verNotificaciones: true,
    verPerfil: true,
    verMovimientos: true,
    verDonaciones: true,  // Admin puede ver y gestionar todas las donaciones
    esSuperusuario: true,
    configurarTema: true, // Permite personalizar tema del sistema
    // Permisos granulares de requisiciones
    crearRequisicion: true,
    editarRequisicion: true,
    eliminarRequisicion: true,
    enviarRequisicion: true,
    autorizarRequisicion: true,
    rechazarRequisicion: true,
    surtirRequisicion: true,
    cancelarRequisicion: true,
    confirmarRecepcion: true,  // Admin puede confirmar recepción de cualquier centro
    descargarHojaRecoleccion: true,
    // FLUJO V2: Permisos jerárquicos
    autorizarAdmin: true,       // Puede autorizar como Administrador de Centro
    autorizarDirector: true,    // Puede autorizar como Director de Centro
    recibirFarmacia: true,      // Puede recibir requisiciones en Farmacia
    autorizarFarmacia: true,    // Puede autorizar en Farmacia
    // Permisos de gestión de usuarios
    gestionUsuarios: true,
    // Permisos granulares de lotes
    crearLote: true,
    editarLote: true,
    eliminarLote: true,
    exportarLotes: true,
    importarLotes: true,
    // Permisos granulares de movimientos
    crearMovimiento: true,
    exportarMovimientos: true,
    // Permisos granulares de productos
    crearProducto: true,
    editarProducto: true,
    eliminarProducto: true,
    exportarProductos: true,
    importarProductos: true,
    // Permisos de notificaciones
    gestionarNotificaciones: true,
  },
  FARMACIA: {
    verDashboard: true,
    verProductos: true,
    verLotes: true,
    verRequisiciones: true,
    verCentros: true,
    verUsuarios: false,  // ISS-FIX: Farmacia NO gestiona usuarios
    verReportes: true,
    verTrazabilidad: true,
    verAuditoria: false,  // Solo admin/superuser
    verNotificaciones: true,
    verPerfil: true,
    verMovimientos: true,
    verDonaciones: true,  // Farmacia puede gestionar donaciones
    esSuperusuario: false,
    configurarTema: false, // ISS-FIX: Solo admin puede personalizar tema
    // Permisos granulares de requisiciones
    crearRequisicion: false,  // Farmacia no crea requisiciones
    editarRequisicion: true,
    eliminarRequisicion: true,
    enviarRequisicion: false,
    autorizarRequisicion: true,
    rechazarRequisicion: true,
    surtirRequisicion: true,
    cancelarRequisicion: true,
    confirmarRecepcion: false,  // Farmacia no confirma recepción (lo hace el centro)
    descargarHojaRecoleccion: true,
    // FLUJO V2: Permisos jerárquicos
    autorizarAdmin: false,      // No es administrador de centro
    autorizarDirector: false,   // No es director de centro
    recibirFarmacia: true,      // Puede recibir requisiciones en Farmacia
    autorizarFarmacia: true,    // Puede autorizar en Farmacia
    // Permisos de gestión de usuarios
    gestionUsuarios: false,  // ISS-FIX: Farmacia NO gestiona usuarios
    // Permisos granulares de lotes
    crearLote: true,
    editarLote: true,
    eliminarLote: true,
    exportarLotes: true,
    importarLotes: true,
    // Permisos granulares de movimientos
    crearMovimiento: true,
    exportarMovimientos: true,
    // Permisos granulares de productos
    crearProducto: true,
    editarProducto: true,
    eliminarProducto: true,
    exportarProductos: true,
    importarProductos: true,
    // Permisos de notificaciones
    gestionarNotificaciones: true,
  },
  CENTRO: {
    verDashboard: true,
    verProductos: true,  // ISS-FIX: Centro DEBE ver productos para crear requisiciones (solo lectura)
    verLotes: true,  // ISS-FIX: Centro DEBE ver lotes para seleccionar en requisiciones (solo lectura)
    verRequisiciones: true,
    verCentros: false,
    verUsuarios: false,
    verReportes: false,  // Centro NO debe ver Reportes - solo admin/farmacia
    verTrazabilidad: false,  // Centro NO debe ver Trazabilidad
    verAuditoria: false,
    verNotificaciones: true,
    verPerfil: true,
    verMovimientos: true,  // ISS-FIX: Centro puede ver movimientos de SU centro
    verDonaciones: false,  // Centro NO puede ver/gestionar donaciones
    esSuperusuario: false,
    configurarTema: false, // Centro no puede personalizar tema
    // Permisos granulares de requisiciones - Centro solo crea y envía
    crearRequisicion: true,
    editarRequisicion: true,  // Solo sus propios borradores
    eliminarRequisicion: true,  // Solo sus propios borradores
    enviarRequisicion: true,
    autorizarRequisicion: false,  // No puede autorizar
    rechazarRequisicion: false,  // No puede rechazar
    surtirRequisicion: false,  // No puede surtir
    cancelarRequisicion: true,  // Puede cancelar las suyas
    confirmarRecepcion: true,  // Centro puede confirmar recepción de sus requisiciones
    descargarHojaRecoleccion: true,  // Puede descargar para recoger
    // FLUJO V2: Permisos jerárquicos - Centro médico solo crea
    autorizarAdmin: false,      // Médico no autoriza como admin
    autorizarDirector: false,   // Médico no autoriza como director
    recibirFarmacia: false,     // Centro no recibe en farmacia
    autorizarFarmacia: false,   // Centro no autoriza en farmacia
    // Permisos de gestión de usuarios
    gestionUsuarios: false,
    // Permisos granulares de lotes - Centro NO puede crear/editar (solo ver)
    crearLote: false,
    editarLote: false,
    eliminarLote: false,
    exportarLotes: false,
    importarLotes: false,
    // Permisos granulares de movimientos - Centro solo ver
    crearMovimiento: false,
    exportarMovimientos: false,
    // Permisos granulares de productos - Centro NO puede crear/editar (solo ver)
    crearProducto: false,
    editarProducto: false,
    eliminarProducto: false,
    exportarProductos: false,
    importarProductos: false,
    // Permisos de notificaciones - CENTRO solo puede ver y marcar SUS propias notificaciones
    // No tiene acceso a gestión masiva ni administrativa de notificaciones
    gestionarNotificaciones: false,
  },
  VISTA: {
    verDashboard: true,
    verProductos: true,
    verLotes: true,
    verRequisiciones: true,
    verCentros: true,
    verUsuarios: true,
    verReportes: false,  // Restringido: solo farmacia/admin pueden ver reportes
    verTrazabilidad: false,  // Restringido: solo farmacia/admin pueden ver trazabilidad
    verAuditoria: false,  // Restringido: solo farmacia/admin pueden ver auditoría
    verNotificaciones: true,
    verPerfil: true,
    verMovimientos: true,
    verDonaciones: true,  // Vista puede consultar donaciones (solo lectura)
    esSuperusuario: false,
    configurarTema: false, // Vista no puede personalizar tema
    // Vista no puede modificar requisiciones
    crearRequisicion: false,
    editarRequisicion: false,
    eliminarRequisicion: false,
    enviarRequisicion: false,
    autorizarRequisicion: false,
    rechazarRequisicion: false,
    surtirRequisicion: false,
    cancelarRequisicion: false,
    confirmarRecepcion: false,  // Vista no puede confirmar recepción
    descargarHojaRecoleccion: true,  // Puede descargar para consulta
    // FLUJO V2: Vista no tiene permisos de flujo
    autorizarAdmin: false,
    autorizarDirector: false,
    recibirFarmacia: false,
    autorizarFarmacia: false,
    // Permisos de gestión de usuarios
    gestionUsuarios: false,
    // Permisos granulares de lotes - Vista solo lectura
    crearLote: false,
    editarLote: false,
    eliminarLote: false,
    exportarLotes: true,  // Puede exportar para consulta
    importarLotes: false,
    // Permisos granulares de movimientos - Vista solo exportar
    crearMovimiento: false,
    exportarMovimientos: true,  // Puede exportar para consulta
    // Permisos granulares de productos - Vista solo exportar
    crearProducto: false,
    editarProducto: false,
    eliminarProducto: false,
    exportarProductos: true,  // Puede exportar para consulta
    importarProductos: false,
    // Permisos de notificaciones
    gestionarNotificaciones: false,
  },
  // ISS-AUDIT FIX: Roles específicos del centro penitenciario (FLUJO V2)
  // Estos roles tienen permisos diferentes entre sí para el flujo jerárquico
  MEDICO: {
    verDashboard: true,
    verProductos: true,  // Ve productos para crear requisiciones
    verLotes: false,     // Médico no gestiona lotes
    verRequisiciones: true,
    verCentros: false,
    verUsuarios: false,
    verReportes: false,  // ISS-AUDIT: Centro NO ve reportes
    verTrazabilidad: false,  // ISS-AUDIT: Centro NO ve trazabilidad
    verAuditoria: false,
    verNotificaciones: true,
    verPerfil: true,
    verMovimientos: true,  // ISS-FIX: Médico PUEDE ver movimientos de su centro (salidas/consumos)
    verDonaciones: false,
    esSuperusuario: false,
    configurarTema: false,
    // FLUJO V2: Médico CREA requisiciones y CONFIRMA entrega
    crearRequisicion: true,
    editarRequisicion: true,  // Solo borradores propios
    eliminarRequisicion: true,  // Solo borradores propios
    enviarRequisicion: true,  // Envía a Administrador de Centro
    autorizarRequisicion: false,
    rechazarRequisicion: false,
    surtirRequisicion: false,
    cancelarRequisicion: true,
    confirmarRecepcion: true,  // Médico confirma recepción
    descargarHojaRecoleccion: true,
    gestionUsuarios: false,
    // FLUJO V2: Permisos jerárquicos específicos
    autorizarAdmin: false,      // Médico NO autoriza como admin
    autorizarDirector: false,   // Médico NO autoriza como director
    recibirFarmacia: false,
    autorizarFarmacia: false,
    // Lotes - Solo lectura
    crearLote: false,
    editarLote: false,
    eliminarLote: false,
    exportarLotes: false,
    importarLotes: false,
    // Movimientos - ISS-FIX: Médico puede crear movimientos de salida en su centro
    crearMovimiento: true,
    exportarMovimientos: false,
    // Productos - Solo lectura
    crearProducto: false,
    editarProducto: false,
    eliminarProducto: false,
    exportarProductos: false,
    importarProductos: false,
    gestionarNotificaciones: false,
  },
  ADMINISTRADOR_CENTRO: {
    verDashboard: true,
    verProductos: true,
    verLotes: false,
    verRequisiciones: true,
    verCentros: false,
    verUsuarios: false,
    verReportes: false,  // ISS-AUDIT: Centro NO ve reportes
    verTrazabilidad: false,  // ISS-AUDIT: Centro NO ve trazabilidad
    verAuditoria: false,
    verNotificaciones: true,
    verPerfil: true,
    verMovimientos: true,  // ISS-FIX: Admin Centro puede VER movimientos de su centro
    verDonaciones: false,
    esSuperusuario: false,
    configurarTema: false,
    // FLUJO V2: Administrador AUTORIZA y CONFIRMA
    crearRequisicion: false,  // No crea, solo autoriza
    editarRequisicion: false,
    eliminarRequisicion: false,
    enviarRequisicion: false,
    autorizarRequisicion: false,
    rechazarRequisicion: true,  // Puede rechazar/devolver
    surtirRequisicion: false,
    cancelarRequisicion: false,
    confirmarRecepcion: true,
    descargarHojaRecoleccion: true,
    gestionUsuarios: false,
    // FLUJO V2: Admin de Centro AUTORIZA en su nivel
    autorizarAdmin: true,       // SÍ autoriza como admin de centro
    autorizarDirector: false,   // NO autoriza como director
    recibirFarmacia: false,
    autorizarFarmacia: false,
    // Sin acceso a lotes/movimientos/productos
    crearLote: false,
    editarLote: false,
    eliminarLote: false,
    exportarLotes: false,
    importarLotes: false,
    crearMovimiento: false,
    exportarMovimientos: false,
    crearProducto: false,
    editarProducto: false,
    eliminarProducto: false,
    exportarProductos: false,
    importarProductos: false,
    gestionarNotificaciones: false,
  },
  DIRECTOR_CENTRO: {
    verDashboard: true,
    verProductos: true,
    verLotes: false,
    verRequisiciones: true,
    verCentros: false,
    verUsuarios: false,
    verReportes: false,  // ISS-AUDIT: Centro NO ve reportes
    verTrazabilidad: false,  // ISS-AUDIT: Centro NO ve trazabilidad
    verAuditoria: false,
    verNotificaciones: true,
    verPerfil: true,
    verMovimientos: true,  // ISS-FIX: Director puede VER movimientos de su centro
    verDonaciones: false,
    esSuperusuario: false,
    configurarTema: false,
    // FLUJO V2: Director AUTORIZA final del centro
    crearRequisicion: false,
    editarRequisicion: false,
    eliminarRequisicion: false,
    enviarRequisicion: false,
    autorizarRequisicion: false,
    rechazarRequisicion: true,  // Puede rechazar/devolver
    surtirRequisicion: false,
    cancelarRequisicion: false,
    confirmarRecepcion: true,
    descargarHojaRecoleccion: true,
    gestionUsuarios: false,
    // FLUJO V2: Director AUTORIZA en su nivel
    autorizarAdmin: false,      // NO autoriza como admin
    autorizarDirector: true,    // SÍ autoriza como director
    recibirFarmacia: false,
    autorizarFarmacia: false,
    // Sin acceso a lotes/movimientos/productos
    crearLote: false,
    editarLote: false,
    eliminarLote: false,
    exportarLotes: false,
    importarLotes: false,
    crearMovimiento: false,
    exportarMovimientos: false,
    crearProducto: false,
    editarProducto: false,
    eliminarProducto: false,
    exportarProductos: false,
    importarProductos: false,
    gestionarNotificaciones: false,
  },
  SIN_ROL: {
    verDashboard: false,
    verProductos: false,
    verLotes: false,
    verRequisiciones: false,
    verCentros: false,
    verUsuarios: false,
    verReportes: false,
    verTrazabilidad: false,
    verAuditoria: false,
    verNotificaciones: false,
    verPerfil: false,
    verMovimientos: false,
    verDonaciones: false,
    esSuperusuario: false,
    configurarTema: false,
    crearRequisicion: false,
    editarRequisicion: false,
    eliminarRequisicion: false,
    enviarRequisicion: false,
    autorizarRequisicion: false,
    rechazarRequisicion: false,
    surtirRequisicion: false,
    cancelarRequisicion: false,
    confirmarRecepcion: false,
    descargarHojaRecoleccion: false,
    gestionUsuarios: false,
    // FLUJO V2: Sin permisos de flujo
    autorizarAdmin: false,
    autorizarDirector: false,
    recibirFarmacia: false,
    autorizarFarmacia: false,
    // Permisos granulares de lotes
    crearLote: false,
    editarLote: false,
    eliminarLote: false,
    exportarLotes: false,
    importarLotes: false,
    // Permisos granulares de movimientos
    crearMovimiento: false,
    exportarMovimientos: false,
    // Permisos granulares de productos
    crearProducto: false,
    editarProducto: false,
    eliminarProducto: false,
    exportarProductos: false,
    importarProductos: false,
    // Permisos de notificaciones
    gestionarNotificaciones: false,
  },
};

/**
 * ISS-AUDIT FIX: Obtiene el rol específico para mapeo de permisos.
 * 
 * A diferencia de getRolPrincipal (para navegación), esta función
 * devuelve el rol específico del centro (MEDICO, ADMINISTRADOR_CENTRO, 
 * DIRECTOR_CENTRO) para que calcularPermisos() use los permisos correctos.
 */
const getRolFromUser = (userData, userGroups) => {
  if (!userData) return 'SIN_ROL';
  
  const isSuperuser = userData.is_superuser === true;
  if (isSuperuser) return 'ADMIN';
  
  // ISS-AUDIT FIX: Usar rol_efectivo o rol del usuario directamente
  const rolRaw = (userData.rol_efectivo || userData.rol || '').toLowerCase();
  
  // Mapear roles específicos del centro a sus claves de permisos
  const rolMapping = {
    // Admin roles
    'admin': 'ADMIN',
    'admin_sistema': 'ADMIN',
    'superusuario': 'ADMIN',
    // Farmacia roles
    'farmacia': 'FARMACIA',
    'admin_farmacia': 'FARMACIA',
    'farmaceutico': 'FARMACIA',
    'usuario_farmacia': 'FARMACIA',
    // Roles específicos del centro (FLUJO V2) - Usar su propio mapeo
    'medico': 'MEDICO',
    'administrador_centro': 'ADMINISTRADOR_CENTRO',
    'director_centro': 'DIRECTOR_CENTRO',
    // Centro genérico
    'centro': 'CENTRO',
    'usuario_centro': 'CENTRO',
    'usuario_normal': 'CENTRO',
    'solicitante': 'CENTRO',
    // Vista
    'vista': 'VISTA',
    'usuario_vista': 'VISTA',
  };
  
  if (rolMapping[rolRaw]) {
    return rolMapping[rolRaw];
  }
  
  // Verificar por grupos
  const groupNames = (userGroups || []).map((g) => ((g.name || g) + '').toUpperCase());
  if (groupNames.includes('FARMACIA_ADMIN') || groupNames.includes('FARMACEUTICO')) return 'FARMACIA';
  if (groupNames.includes('CENTRO_USER') || groupNames.includes('SOLICITANTE')) return 'CENTRO';
  if (groupNames.includes('VISTA_USER')) return 'VISTA';
  
  // Si tiene centro asignado pero sin rol específico, es CENTRO genérico
  if (userData.centro || userData.centro_id) {
    return 'CENTRO';
  }
  
  // Default: VISTA (más seguro)
  return 'VISTA';
};

const calcularPermisos = (userData, userGroups) => {
  const role = getRolFromUser(userData, userGroups);
  const isSuperuser = Boolean(userData?.is_superuser);
  const groupNames = userGroups.map((g) => (g.name || g).toUpperCase());
  
  // ISS-009 FIX: Usar funciones centralizadas de roles.js
  const isAdmin = esAdmin(userData);
  const isFarmaciaAdmin = esFarmaciaAdminUtil(userData);
  const isCentroUser = esCentro(userData);
  const isVistaUser = esVista(userData);

  // ISS-MEDICO FIX: Detectar roles específicos que NO deben usar fallback permisivo
  const ROLES_ESPECIFICOS = ['MEDICO', 'ADMINISTRADOR_CENTRO', 'DIRECTOR_CENTRO'];
  const esRolEspecifico = ROLES_ESPECIFICOS.includes(role);

  // Obtener permisos base del rol (FALLBACK)
  const basePerms = PERMISOS_POR_ROL[role] || PERMISOS_POR_ROL.SIN_ROL;

  // Flags derivados que siempre se calculan (NO incluir permisos de módulos aquí)
  const flagsDerivados = {
    role,
    isSuperuser,
    isAdmin,
    isFarmaciaAdmin,
    isCentroUser,
    isVistaUser,
    groupNames,
    verPerfil: true, // Siempre puede ver su perfil
    esSuperusuario: isSuperuser, // Siempre calcular desde is_superuser
    // ISS-009 FIX: Exponer función de validación de acciones del flujo
    puedeEjecutarAccion: (accion) => puedeEjecutarAccionFlujo(userData, accion),
    // ISS-MEDICO FIX: Marcar si es rol específico
    _esRolEspecifico: esRolEspecifico,
    // configurarTema viene del basePerms del rol, NO lo sobrescribimos aquí
  };

  // ISS-001 FIX (audit28): Permisos del backend tienen PRIORIDAD ABSOLUTA
  // Los permisos base solo son fallback cuando el backend no envía permisos
  if (userData?.permisos && typeof userData.permisos === 'object' && Object.keys(userData.permisos).length > 0) {
    // Log de advertencia si hay discrepancias significativas
    const permisosBackend = userData.permisos;
    const discrepancias = [];
    
    // Verificar permisos críticos
    const permisosCriticos = ['crearRequisicion', 'autorizarRequisicion', 'surtirRequisicion', 'gestionUsuarios'];
    permisosCriticos.forEach(permiso => {
      if (basePerms[permiso] !== undefined && permisosBackend[permiso] !== undefined) {
        if (basePerms[permiso] !== permisosBackend[permiso]) {
          discrepancias.push(`${permiso}: fallback=${basePerms[permiso]}, backend=${permisosBackend[permiso]}`);
        }
      }
    });
    
    if (discrepancias.length > 0) {
      console.warn('[PermissionContext] ISS-001: Discrepancias detectadas (usando backend):', discrepancias);
    }
    
    return {
      ...basePerms,           // Permisos base del rol (fallback más bajo)
      ...userData.permisos,   // Permisos del backend (PRIORIDAD)
      ...flagsDerivados,      // Flags derivados (siempre calculados)
      _source: 'backend',     // Marcador de origen para debugging
    };
  }

  // ISS-MEDICO FIX: Para roles específicos SIN permisos del backend, 
  // NO usar fallback permisivo - usar los permisos restrictivos del rol específico
  if (esRolEspecifico) {
    console.warn(`[PermissionContext] ISS-MEDICO: Rol específico '${role}' sin permisos del backend. Usando permisos restrictivos del rol.`);
    return {
      ...basePerms,           // Permisos restrictivos del rol específico
      ...flagsDerivados,
      _source: 'rol_especifico_fallback',
      _requiresBackendValidation: true,  // Indicar que se requiere validación
    };
  }

  // ISS-001 FIX: Fallback SOLO si el backend no envió permisos
  console.warn('[PermissionContext] ISS-001: Usando permisos fallback (backend no envió permisos)');
  return {
    ...basePerms,
    ...flagsDerivados,
    _source: 'fallback',
  };
};

export function PermissionProvider({ children }) {
  const [user, setUser] = useState(null);
  const [grupos, setGrupos] = useState([]);
  const [permisos, setPermisos] = useState({});
  const [loading, setLoading] = useState(true);
  // ISS-002 FIX: Flag para indicar si los permisos están validados con el backend
  const [permisosValidados, setPermisosValidados] = useState(false);
  // ISS-002 FIX: Ref para evitar hidratación múltiple
  const hydrationRef = useRef(false);

  // ISS-005 FIX: Hidratar SOLO datos mínimos necesarios para UI básica
  // NO usar para permisos hasta validar con backend
  const hydrateFromUser = useCallback((userData, validated = false) => {
    if (!userData) return;
    setUser(userData);
    
    // ISS-005 FIX: Guardar SOLO datos mínimos en sessionStorage (no localStorage)
    try {
      sessionStorage.setItem(SESSION_KEYS.USER_ID, userData.id?.toString() || '');
      sessionStorage.setItem(SESSION_KEYS.USER_ROLE, userData.rol || '');
      sessionStorage.setItem(SESSION_KEYS.SESSION_HASH, generateSessionHash(userData.id, userData.rol));
      // Limpiar localStorage antiguo si existe
      localStorage.removeItem('user');
    } catch (_) {
      // Ignorar errores de almacenamiento
    }
    
    const baseGroups = userData.groups || (userData.grupos || []).map((name) => ({ name }));
    setGrupos(baseGroups);
    
    // ISS-002 FIX: Solo calcular permisos completos si datos están validados con backend
    if (validated) {
      const permisosCompletos = calcularPermisos(userData, baseGroups);
      // ISS-009 FIX: Marcar que permisos están validados y NO están en validación
      setPermisos({
        ...permisosCompletos,
        _isValidating: false,  // Crucial: desactivar flag de validación
      });
      setPermisosValidados(true);
    } else {
      // ISS-009 FIX: Permisos mínimos hasta validar - NO incluir rol
      setPermisos({
        verPerfil: true,
        _source: 'pending_validation',
        _isValidating: true,
      });
    }
  }, []);

  const cargarUsuario = useCallback(async (forceRefresh = false) => {
    try {
      // ISS-003 FIX: No intentar cargar usuario si hay logout en progreso
      if (isLogoutInProgress()) {
        setLoading(false);
        return;
      }
      
      // Primero intentar migrar tokens viejos de localStorage
      migrateFromLocalStorage();
      
      // Si no hay token en memoria Y hay evidencia de sesión previa, intentar refresh
      if (!hasAccessToken()) {
        // ISS-003 FIX: Doble verificación de logout en progreso
        if (isLogoutInProgress()) {
          setLoading(false);
          return;
        }
        
        // ISS-002/005 FIX: Verificar sessionStorage en lugar de localStorage
        const storedUserId = sessionStorage.getItem(SESSION_KEYS.USER_ID);
        if (!storedUserId && !forceRefresh) {
          // No hay sesión previa, no intentar refresh
          setLoading(false);
          return;
        }
        
        try {
          // El refresh token está en cookie HttpOnly, el servidor lo lee automáticamente
          const refreshResponse = await authAPI.refresh();
          if (refreshResponse.data?.access) {
            setAccessToken(refreshResponse.data.access);
          } else {
            // Refresh falló, limpiar datos de sesión
            sessionStorage.removeItem(SESSION_KEYS.USER_ID);
            sessionStorage.removeItem(SESSION_KEYS.USER_ROLE);
            sessionStorage.removeItem(SESSION_KEYS.SESSION_HASH);
            localStorage.removeItem('user'); // Limpiar legacy
            setLoading(false);
            return;
          }
        } catch (refreshError) {
          // No hay sesión válida, limpiar datos
          sessionStorage.removeItem(SESSION_KEYS.USER_ID);
          sessionStorage.removeItem(SESSION_KEYS.USER_ROLE);
          sessionStorage.removeItem(SESSION_KEYS.SESSION_HASH);
          localStorage.removeItem('user'); // Limpiar legacy
          setLoading(false);
          return;
        }
      }

      // ISS-002 FIX: Cargar datos del usuario Y VALIDAR permisos con backend
      // El interceptor añade el token automáticamente
      const response = await apiClient.get('/usuarios/me/');
      hydrateFromUser(response.data, true); // true = datos validados
    } catch (error) {
      console.error('Error al cargar usuario:', error);
      // ISS-002/005 FIX: Limpiar datos de sesión inválida
      sessionStorage.removeItem(SESSION_KEYS.USER_ID);
      sessionStorage.removeItem(SESSION_KEYS.USER_ROLE);
      sessionStorage.removeItem(SESSION_KEYS.SESSION_HASH);
      localStorage.removeItem('user'); // Limpiar legacy
      setPermisosValidados(false);
    } finally {
      setLoading(false);
    }
  }, [hydrateFromUser]);

  useEffect(() => {
    // ISS-002 FIX: NO hidratar permisos completos desde storage local
    // Solo mostrar UI mínima mientras validamos con backend
    if (hydrationRef.current) return;
    hydrationRef.current = true;
    
    // ISS-005 FIX: Verificar si hay sesión previa en sessionStorage
    const storedUserId = sessionStorage.getItem(SESSION_KEYS.USER_ID);
    const storedRole = sessionStorage.getItem(SESSION_KEYS.USER_ROLE);
    const storedHash = sessionStorage.getItem(SESSION_KEYS.SESSION_HASH);
    
    // Migrar de localStorage legacy si existe
    const legacyUser = localStorage.getItem('user');
    if (legacyUser && !storedUserId) {
      try {
        const parsed = JSON.parse(legacyUser);
        sessionStorage.setItem(SESSION_KEYS.USER_ID, parsed.id?.toString() || '');
        sessionStorage.setItem(SESSION_KEYS.USER_ROLE, parsed.rol || '');
        sessionStorage.setItem(SESSION_KEYS.SESSION_HASH, generateSessionHash(parsed.id, parsed.rol));
        localStorage.removeItem('user'); // Eliminar legacy
      } catch (e) {
        localStorage.removeItem('user');
      }
    }
    
    // ISS-009 FIX: NO asignar rol durante pending_validation para prevenir escalación de privilegios
    // Solo mostrar ID mínimo, sin permisos de UI hasta que backend valide
    if (storedUserId && storedHash) {
      // Solo ID para tracking, SIN rol ni permisos inferidos
      setUser({ id: storedUserId });
      setPermisos({
        // Solo permiso de perfil básico, NO módulos
        verPerfil: true,
        _source: 'pending_validation',
        _isValidating: true,  // Flag para ocultar menús hasta validación
      });
    }

    // SIEMPRE cargar usuario fresco del servidor para tener permisos actualizados
    cargarUsuario();
  }, [cargarUsuario]);

  const verificarPermiso = (permiso) => permisos[permiso] || false;

  const getRolPrincipal = () => {
    // ISS-009 FIX: NO retornar rol durante validación pendiente
    // Esto previene que UI muestre opciones basadas en rol manipulado en storage
    if (permisos?._isValidating || permisos?._source === 'pending_validation') {
      return 'VALIDANDO';
    }
    
    if (!user) return 'SIN_ROL';
    
    // ISS-PERMS FIX: Usar rol_efectivo del backend si está disponible
    const rol = (user.rol_efectivo || user.rol || '').toLowerCase();
    const isSuperuser = user.is_superuser === true;
    
    // Primero verificar superusuario
    if (isSuperuser) return 'ADMIN';
    
    // Luego verificar por rol específico
    if (rol === 'admin_sistema' || rol === 'superusuario' || rol === 'admin') return 'ADMIN';
    if (rol === 'farmacia' || rol === 'admin_farmacia' || grupos.some((g) => g.name === 'FARMACIA_ADMIN')) return 'FARMACIA';
    // FLUJO V2: Roles específicos del centro penitenciario mapean a CENTRO
    if (rol === 'medico' || rol === 'administrador_centro' || rol === 'director_centro' ||
        rol === 'centro' || rol === 'usuario_normal' || rol === 'usuario_centro' ||
        grupos.some((g) => g.name === 'CENTRO_USER')) return 'CENTRO';
    if (rol === 'vista' || rol === 'usuario_vista' || grupos.some((g) => g.name === 'VISTA_USER')) return 'VISTA';
    
    // ISS-PERMS FIX: Si tiene centro asignado, es usuario de centro
    if (user.centro || user.centro_id) return 'CENTRO';
    
    // Si el usuario está autenticado pero sin rol específico, verificar permisos de staff
    if (user.is_staff) return 'FARMACIA';
    
    // ISS-PERMS FIX: Default a VISTA en lugar de SIN_ROL
    return 'VISTA';
  };

  return (
    <PermissionContext.Provider value={{ 
      user, 
      grupos, 
      permisos, 
      loading, 
      permisosValidados, // ISS-002 FIX: Exponer si permisos están validados
      verificarPermiso, 
      getRolPrincipal, 
      recargarUsuario: cargarUsuario 
    }}>
      {children}
    </PermissionContext.Provider>
  );
}

