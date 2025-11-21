import { useEffect, useState, useCallback } from 'react';
import { PermissionContext } from './contexts';
import apiClient from '../services/api';

const calcularPermisos = (userData, userGroups) => {
  const isSuperuser = Boolean(userData.is_superuser);
  const rol = (userData.rol || '').toLowerCase();
  const groupNames = userGroups.map((g) => (g.name || g).toUpperCase());

  const isAdmin =
    isSuperuser ||
    rol === 'admin_sistema' ||
    rol === 'superusuario' ||
    groupNames.includes('FARMACIA_ADMIN');
  const isFarmaciaAdmin =
    isAdmin ||
    rol === 'farmacia' ||
    rol === 'admin_farmacia' ||
    groupNames.includes('FARMACIA_ADMIN');
  const isCentroUser =
    rol === 'centro' ||
    rol === 'usuario_normal' ||
    groupNames.includes('CENTRO_USER');
  const isVistaUser =
    rol === 'vista' ||
    rol === 'usuario_vista' ||
    groupNames.includes('VISTA_USER');

  return {
    isSuperuser: isAdmin,
    isFarmaciaAdmin,
    isCentroUser,
    isVistaUser,

    verProductos: true,
    crearProducto: isFarmaciaAdmin,
    editarProducto: isFarmaciaAdmin,
    eliminarProducto: isFarmaciaAdmin,
    importarProductos: isFarmaciaAdmin,
    exportarProductos: isFarmaciaAdmin || isVistaUser,

    verLotes: true,
    crearLote: isFarmaciaAdmin,
    editarLote: isFarmaciaAdmin,
    eliminarLote: isFarmaciaAdmin,

    verRequisiciones: true,
    crearRequisicion: isCentroUser || isFarmaciaAdmin,
    editarRequisicion: isCentroUser || isFarmaciaAdmin,
    autorizarRequisicion: isFarmaciaAdmin,
    rechazarRequisicion: isFarmaciaAdmin,
    surtirRequisicion: isFarmaciaAdmin,
    descargarHojaRecoleccion: isCentroUser || isFarmaciaAdmin,

    verCentros: true,
    crearCentro: isFarmaciaAdmin,
    editarCentro: isFarmaciaAdmin,

    verUsuarios: isSuperuser,
    crearUsuario: isSuperuser,

    verReportes: isFarmaciaAdmin || isVistaUser || isCentroUser,
    verTrazabilidad: true,
    verAuditoria: isFarmaciaAdmin,
    verDashboard: true,
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
    const baseGroups = userData.groups || (userData.grupos || []).map((name) => ({ name }));
    setGrupos(baseGroups);
    setPermisos(calcularPermisos(userData, baseGroups));
  }, []);

  const cargarUsuario = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setLoading(false);
        return;
      }

      const response = await apiClient.get('/me/', {
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

