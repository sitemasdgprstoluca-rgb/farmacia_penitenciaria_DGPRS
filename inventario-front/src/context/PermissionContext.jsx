import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { DEV_CONFIG, devLog } from '../config/dev';
import { PermissionContext } from './contexts';

const calcularPermisos = (userData, userGroups) => {
  const isSuperuser = userData.is_superuser;
  const groupNames = userGroups.map((g) => g.name);

  const isFarmaciaAdmin = groupNames.includes('FARMACIA_ADMIN') || isSuperuser;
  const isCentroUser = groupNames.includes('CENTRO_USER');
  const isVistaUser = groupNames.includes('VISTA_USER');

  return {
    isSuperuser,
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

    verReportes: isFarmaciaAdmin || isVistaUser,
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

      const response = await axios.get('http://localhost:8000/api/me/', {
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

    if (DEV_CONFIG.ENABLED) {
      devLog('PermissionContext: modo desarrollo activo, usando usuario simulado');
      const mockUser = DEV_CONFIG.AUTO_USER;
      hydrateFromUser(mockUser);
      setLoading(false);
      return;
    }
    cargarUsuario();
  }, [cargarUsuario, hydrateFromUser]);

  const verificarPermiso = (permiso) => permisos[permiso] || false;

  const getRolPrincipal = () => {
    if (user?.is_superuser) return 'SUPERUSUARIO';
    if (grupos.some(g => g.name === 'FARMACIA_ADMIN')) return 'FARMACIA_ADMIN';
    if (grupos.some(g => g.name === 'CENTRO_USER')) return 'CENTRO_USER';
    if (grupos.some(g => g.name === 'VISTA_USER')) return 'VISTA_USER';
    return 'SIN_ROL';
  };

  return (
    <PermissionContext.Provider value={{ user, grupos, permisos, loading, verificarPermiso, getRolPrincipal, recargarUsuario: cargarUsuario }}>
      {children}
    </PermissionContext.Provider>
  );
}

