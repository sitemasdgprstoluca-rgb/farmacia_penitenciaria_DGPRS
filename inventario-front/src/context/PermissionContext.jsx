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
    // Permisos granulares de requisiciones
    crearRequisicion: true,
    editarRequisicion: true,
    eliminarRequisicion: true,
    enviarRequisicion: true,
    autorizarRequisicion: true,
    rechazarRequisicion: true,
    surtirRequisicion: true,
    cancelarRequisicion: true,
    descargarHojaRecoleccion: true,
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
    // Permisos granulares de requisiciones
    crearRequisicion: true,
    editarRequisicion: true,
    eliminarRequisicion: true,
    enviarRequisicion: true,
    autorizarRequisicion: true,
    rechazarRequisicion: true,
    surtirRequisicion: true,
    cancelarRequisicion: true,
    descargarHojaRecoleccion: true,
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
    // Permisos granulares de requisiciones - Centro solo crea y envía
    crearRequisicion: true,
    editarRequisicion: true,  // Solo sus propios borradores
    eliminarRequisicion: true,  // Solo sus propios borradores
    enviarRequisicion: true,
    autorizarRequisicion: false,  // No puede autorizar
    rechazarRequisicion: false,  // No puede rechazar
    surtirRequisicion: false,  // No puede surtir
    cancelarRequisicion: true,  // Puede cancelar las suyas
    descargarHojaRecoleccion: true,  // Puede descargar para recoger
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
    // Vista no puede modificar requisiciones
    crearRequisicion: false,
    editarRequisicion: false,
    eliminarRequisicion: false,
    enviarRequisicion: false,
    autorizarRequisicion: false,
    rechazarRequisicion: false,
    surtirRequisicion: false,
    cancelarRequisicion: false,
    descargarHojaRecoleccion: true,  // Puede descargar para consulta
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
    crearRequisicion: false,
    editarRequisicion: false,
    eliminarRequisicion: false,
    enviarRequisicion: false,
    autorizarRequisicion: false,
    rechazarRequisicion: false,
    surtirRequisicion: false,
    cancelarRequisicion: false,
    descargarHojaRecoleccion: false,
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

  // Si el backend envía permisos calculados, usarlos directamente
  // Esto incluye los permisos personalizados por el admin
  if (userData?.permisos && typeof userData.permisos === 'object') {
    return {
      role,
      isSuperuser,
      isAdmin,
      isFarmaciaAdmin,
      isCentroUser,
      isVistaUser,
      groupNames,
      ...userData.permisos,
      verPerfil: true, // Siempre puede ver su perfil
      esSuperusuario: isSuperuser, // Siempre calcular desde is_superuser
    };
  }

  // Fallback: usar permisos por rol si el backend no envió permisos
  const basePerms = PERMISOS_POR_ROL[role] || PERMISOS_POR_ROL.SIN_ROL;

  return {
    role,
    isSuperuser,
    isAdmin,
    isFarmaciaAdmin,
    isCentroUser,
    isVistaUser,
    groupNames,
    ...basePerms,
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
    if (userData.permisos && typeof userData.permisos === 'object') {
      setPermisos(userData.permisos);
    } else {
      setPermisos(calcularPermisos(userData, baseGroups));
    }
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

