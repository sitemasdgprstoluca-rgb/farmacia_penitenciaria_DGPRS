import { useEffect, useState, useCallback } from 'react';
import { PermissionContext } from './contexts';
import apiClient from '../services/api';

/**
 * Roles soportados por el front:
 * ADMIN (admin_sistema / superusuario)
 * FARMACIA (farmacia / admin_farmacia / grupo FARMACIA_ADMIN)
 * CENTRO (centro / usuario_normal / grupo CENTRO_USER)
 * VISTA (vista / usuario_vista / grupo VISTA_USER)
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
  },
  FARMACIA: {
    verDashboard: true,
    verProductos: true,
    verLotes: true,
    verRequisiciones: true,
    verCentros: true,
    verUsuarios: false,
    verReportes: true,
    verTrazabilidad: true,
    verAuditoria: true,
    verNotificaciones: true,
    verPerfil: true,
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
  },
  VISTA: {
    verDashboard: true,
    verProductos: false,
    verLotes: false,
    verRequisiciones: false,
    verCentros: false,
    verUsuarios: false,
    verReportes: true,
    verTrazabilidad: false,
    verAuditoria: false,
    verNotificaciones: true,
    verPerfil: true,
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
  },
};

const getRolFromUser = (userData, userGroups) => {
  if (!userData) return 'SIN_ROL';
  const isSuperuser = Boolean(userData.is_superuser);
  const rol = (userData.rol || '').toLowerCase();
  const groupNames = userGroups.map((g) => (g.name || g).toUpperCase());

  if (isSuperuser || rol === 'admin_sistema' || rol === 'superusuario') return 'ADMIN';
  if (rol === 'farmacia' || rol === 'admin_farmacia' || groupNames.includes('FARMACIA_ADMIN')) return 'FARMACIA';
  if (rol === 'centro' || rol === 'usuario_normal' || groupNames.includes('CENTRO_USER')) return 'CENTRO';
  if (rol === 'vista' || rol === 'usuario_vista' || groupNames.includes('VISTA_USER')) return 'VISTA';
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

  const basePerms = PERMISOS_POR_ROL[role] || PERMISOS_POR_ROL.SIN_ROL;

  return {
    role,
    isSuperuser,
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

  const cargarUsuario = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setLoading(false);
        return;
      }

      const response = await apiClient.get('/usuarios/me/', {
        headers: { Authorization: `Bearer ${token}` }
      });

      hydrateFromUser(response.data);
    } catch (error) {
      console.error('Error al cargar usuario:', error);
      localStorage.removeItem('token');
    } finally {
      setLoading(false);
    }
  }, [hydrateFromUser]);

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        hydrateFromUser(JSON.parse(storedUser));
        setLoading(false);
        return;
      } catch (error) {
        localStorage.removeItem('user');
      }
    }

    cargarUsuario();
  }, [cargarUsuario, hydrateFromUser]);

  const verificarPermiso = (permiso) => permisos[permiso] || false;

  const getRolPrincipal = () => {
    const rol = (user?.rol || '').toLowerCase();
    if (user?.is_superuser || rol === 'admin_sistema' || rol === 'superusuario') return 'ADMIN';
    if (rol === 'farmacia' || rol === 'admin_farmacia' || grupos.some((g) => g.name === 'FARMACIA_ADMIN')) return 'FARMACIA';
    if (rol === 'centro' || rol === 'usuario_normal' || grupos.some((g) => g.name === 'CENTRO_USER')) return 'CENTRO';
    if (rol === 'vista' || rol === 'usuario_vista' || grupos.some((g) => g.name === 'VISTA_USER')) return 'VISTA';
    return 'SIN_ROL';
  };

  return (
    <PermissionContext.Provider value={{ user, grupos, permisos, loading, verificarPermiso, getRolPrincipal, recargarUsuario: cargarUsuario }}>
      {children}
    </PermissionContext.Provider>
  );
}

