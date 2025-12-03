import { useEffect, useState, useCallback } from 'react';
import { PermissionContext } from './contexts';
import apiClient, { authAPI } from '../services/api';
import { setAccessToken, hasAccessToken, migrateFromLocalStorage } from '../services/tokenManager';

/**
 * Roles soportados por el front:
 * ADMIN (admin_sistema / superusuario)
 * FARMACIA (farmacia / admin_farmacia / grupo FARMACIA_ADMIN)
 * CENTRO (centro / usuario_normal / grupo CENTRO_USER)
 * VISTA (vista / usuario_vista / grupo VISTA_USER)
 * 
 * Los permisos vienen del backend calculados (rol + personalizados)
 */
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
    verUsuarios: true,
    verReportes: true,
    verTrazabilidad: true,
    verAuditoria: false,  // Solo admin/superuser
    verNotificaciones: true,
    verPerfil: true,
    verMovimientos: true,
    esSuperusuario: false,
    configurarTema: true, // Farmacia puede personalizar tema
    // Permisos granulares de requisiciones
    crearRequisicion: true,
    editarRequisicion: true,
    eliminarRequisicion: true,
    enviarRequisicion: true,
    autorizarRequisicion: true,
    rechazarRequisicion: true,
    surtirRequisicion: true,
    cancelarRequisicion: true,
    confirmarRecepcion: true,  // Farmacia puede confirmar recepción
    descargarHojaRecoleccion: true,
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
  CENTRO: {
    verDashboard: true,
    verProductos: false,
    verLotes: false,
    verRequisiciones: true,
    verCentros: false,
    verUsuarios: false,
    verReportes: true,
    verTrazabilidad: false,
    verAuditoria: false,
    verNotificaciones: true,
    verPerfil: true,
    verMovimientos: false,
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
    // Permisos de gestión de usuarios
    gestionUsuarios: false,
    // Permisos granulares de lotes - Centro no tiene acceso
    crearLote: false,
    editarLote: false,
    eliminarLote: false,
    exportarLotes: false,
    importarLotes: false,
    // Permisos granulares de movimientos - Centro no tiene acceso
    crearMovimiento: false,
    exportarMovimientos: false,
    // Permisos granulares de productos - Centro no tiene acceso
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
    verReportes: true,
    verTrazabilidad: false,  // Restringido: solo farmacia/admin pueden ver trazabilidad
    verAuditoria: false,  // Restringido: solo farmacia/admin pueden ver auditoría
    verNotificaciones: true,
    verPerfil: true,
    verMovimientos: true,
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

const getRolFromUser = (userData, userGroups) => {
  if (!userData) return 'SIN_ROL';
  const isSuperuser = Boolean(userData.is_superuser);
  const isStaff = Boolean(userData.is_staff);
  const rol = (userData.rol || '').toLowerCase();
  const groupNames = userGroups.map((g) => (g.name || g).toUpperCase());

  // Admin: superusuario o rol admin/admin_sistema/superusuario
  if (isSuperuser || rol === 'admin' || rol === 'admin_sistema' || rol === 'superusuario') return 'ADMIN';
  // Farmacia: rol farmacia o grupo FARMACIA_ADMIN, o staff sin rol específico
  if (rol === 'farmacia' || rol === 'admin_farmacia' || groupNames.includes('FARMACIA_ADMIN')) return 'FARMACIA';
  if (rol === 'centro' || rol === 'usuario_normal' || groupNames.includes('CENTRO_USER')) return 'CENTRO';
  if (rol === 'vista' || rol === 'usuario_vista' || groupNames.includes('VISTA_USER')) return 'VISTA';
  // Staff sin rol específico = FARMACIA
  if (isStaff) return 'FARMACIA';
  return 'SIN_ROL';
};

const calcularPermisos = (userData, userGroups) => {
  const role = getRolFromUser(userData, userGroups);
  const isSuperuser = Boolean(userData?.is_superuser);
  const groupNames = userGroups.map((g) => (g.name || g).toUpperCase());
  const isAdmin = role === 'ADMIN';
  const isFarmaciaAdmin = role === 'FARMACIA' || role === 'ADMIN';
  const isCentroUser = role === 'CENTRO';
  const isVistaUser = role === 'VISTA';

  // Obtener permisos base del rol
  const basePerms = PERMISOS_POR_ROL[role] || PERMISOS_POR_ROL.SIN_ROL;

  // Flags derivados que siempre se calculan
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
    // Permisos especiales que dependen del rol, no del backend
    configurarTema: isAdmin || isFarmaciaAdmin, // Solo ADMIN y FARMACIA pueden configurar tema
  };

  // Si el backend envía permisos calculados, mezclarlos con los base y flags
  // Los permisos del backend tienen prioridad sobre los base (excepto flags derivados)
  if (userData?.permisos && typeof userData.permisos === 'object') {
    return {
      ...basePerms,           // Permisos base del rol (fallback)
      ...userData.permisos,   // Permisos del backend (override)
      ...flagsDerivados,      // Flags derivados (siempre calculados)
    };
  }

  // Fallback: usar permisos por rol si el backend no envió permisos
  return {
    ...basePerms,
    ...flagsDerivados,
  };
};

export function PermissionProvider({ children }) {
  const [user, setUser] = useState(null);
  const [grupos, setGrupos] = useState([]);
  const [permisos, setPermisos] = useState({});
  const [loading, setLoading] = useState(true);

  const hydrateFromUser = useCallback((userData) => {
    if (!userData) return;
    setUser(userData);
    try {
      localStorage.setItem('user', JSON.stringify(userData));
    } catch (_) {
      // Ignorar almacenamiento local fallido
    }
    const baseGroups = userData.groups || (userData.grupos || []).map((name) => ({ name }));
    setGrupos(baseGroups);
    // SIEMPRE usar calcularPermisos para incluir flags derivados (role, isAdmin, isFarmaciaAdmin, etc.)
    // calcularPermisos ya mezcla userData.permisos del backend con los flags calculados
    setPermisos(calcularPermisos(userData, baseGroups));
  }, []);

  const cargarUsuario = useCallback(async (forceRefresh = false) => {
    try {
      // Primero intentar migrar tokens viejos de localStorage
      migrateFromLocalStorage();
      
      // Si no hay token en memoria Y hay evidencia de sesión previa, intentar refresh
      if (!hasAccessToken()) {
        // Solo intentar refresh si hay usuario guardado o se fuerza
        const storedUser = localStorage.getItem('user');
        if (!storedUser && !forceRefresh) {
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
            // Refresh falló, limpiar datos de usuario
            localStorage.removeItem('user');
            setLoading(false);
            return;
          }
        } catch (refreshError) {
          // No hay sesión válida, limpiar datos
          localStorage.removeItem('user');
          setLoading(false);
          return;
        }
      }

      // Cargar datos del usuario (el interceptor añade el token automáticamente)
      const response = await apiClient.get('/usuarios/me/');
      hydrateFromUser(response.data);
    } catch (error) {
      console.error('Error al cargar usuario:', error);
      // Limpiar datos de sesión inválida
      localStorage.removeItem('user');
    } finally {
      setLoading(false);
    }
  }, [hydrateFromUser]);

  useEffect(() => {
    // Hidratación inmediata desde localStorage para evitar flash
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        hydrateFromUser(JSON.parse(storedUser));
      } catch (error) {
        localStorage.removeItem('user');
      }
    }

    // SIEMPRE cargar usuario fresco del servidor para tener datos actualizados
    cargarUsuario();
  }, [cargarUsuario, hydrateFromUser]);

  const verificarPermiso = (permiso) => permisos[permiso] || false;

  const getRolPrincipal = () => {
    if (!user) return 'SIN_ROL';
    
    const rol = (user.rol || '').toLowerCase();
    const isSuperuser = user.is_superuser === true;
    
    // Primero verificar superusuario
    if (isSuperuser) return 'ADMIN';
    
    // Luego verificar por rol específico
    if (rol === 'admin_sistema' || rol === 'superusuario' || rol === 'admin') return 'ADMIN';
    if (rol === 'farmacia' || rol === 'admin_farmacia' || grupos.some((g) => g.name === 'FARMACIA_ADMIN')) return 'FARMACIA';
    if (rol === 'centro' || rol === 'usuario_normal' || grupos.some((g) => g.name === 'CENTRO_USER')) return 'CENTRO';
    if (rol === 'vista' || rol === 'usuario_vista' || grupos.some((g) => g.name === 'VISTA_USER')) return 'VISTA';
    
    // Si el usuario está autenticado pero sin rol específico, verificar permisos de staff
    if (user.is_staff) return 'FARMACIA';
    
    return 'SIN_ROL';
  };

  return (
    <PermissionContext.Provider value={{ user, grupos, permisos, loading, verificarPermiso, getRolPrincipal, recargarUsuario: cargarUsuario }}>
      {children}
    </PermissionContext.Provider>
  );
}

