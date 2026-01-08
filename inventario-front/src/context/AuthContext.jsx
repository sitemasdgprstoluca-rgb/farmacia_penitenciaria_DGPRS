// filepath: inventario-front/src/context/AuthContext.jsx
/**
 * Context de Autenticación con manejo seguro de tokens
 * 
 * SEGURIDAD:
 * - Access Token: Almacenado en memoria (tokenManager)
 * - Refresh Token: Cookie HttpOnly manejada por el servidor
 * - NO se usa localStorage para tokens (vulnerable a XSS)
 */
import { useState, useEffect } from 'react';
import { authAPI } from '../services/api';
import { AuthContext } from './contexts';
import { 
  setAccessToken, 
  clearTokens, 
  getAccessToken,
  migrateFromLocalStorage,
  setLogoutInProgress,
  setRefreshToken,
  getRefreshToken
} from '../services/tokenManager';
import { devWarn } from '../config/dev';
import { ADMIN_ROLES } from '../utils/roles';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Migrar tokens existentes de localStorage (una sola vez)
    migrateFromLocalStorage();
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      // Si hay token en memoria, intentar obtener perfil
      if (getAccessToken()) {
        const response = await authAPI.me();
        setUser(response.data);
      } else {
        // Intentar refresh (la cookie HttpOnly o el token en memoria)
        try {
          const refreshResponse = await authAPI.refresh();
          if (refreshResponse.data.access) {
            setAccessToken(refreshResponse.data.access);
            // ISS-FIX: Guardar nuevo refresh si viene en la respuesta
            if (refreshResponse.data.refresh) {
              setRefreshToken(refreshResponse.data.refresh);
            }
            const profileResponse = await authAPI.me();
            setUser(profileResponse.data);
          }
        } catch {
          // No hay sesión válida
          setUser(null);
        }
      }
    } catch (error) {
      // Token expirado o inválido
      clearTokens();
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (credentials) => {
    const response = await authAPI.login(credentials);
    const { access, refresh, user: userData } = response.data;
    
    // Guardar access token en memoria (NO en localStorage)
    setAccessToken(access);
    
    // ISS-FIX: Guardar refresh token en memoria para cross-origin
    if (refresh) {
      setRefreshToken(refresh);
    }
    
    // Obtener perfil completo si no viene en la respuesta
    let finalUser;
    if (userData) {
      setUser(userData);
      finalUser = userData;
    } else {
      const profile = await authAPI.me();
      setUser(profile.data);
      finalUser = profile.data;
    }
    
    // Disparar evento para que ThemeContext recargue el tema con autenticación
    // Esto resuelve el problema de temas que requieren auth para cargar
    window.dispatchEvent(new Event('auth-login-success'));
    
    return finalUser;
  };

  const logout = async () => {
    // ISS-003: Marcar logout en progreso ANTES de llamar a la API
    // Esto bloquea cualquier intento de refresh automático
    setLogoutInProgress(true);
    
    try {
      await authAPI.logout();
    } catch (error) {
      // ISS-003: Incluso si el logout falla (servidor inalcanzable, etc.),
      // limpiar el estado local. El flag logoutInProgress evita que el
      // interceptor intente refresh con una cookie potencialmente válida.
      devWarn('Error en logout (limpieza local realizada):', error);
    }
    
    // Limpiar tokens de memoria (esto mantiene logoutInProgress=true)
    clearTokens();
    // Limpiar datos de usuario
    localStorage.removeItem('user');
    setUser(null);
  };

  // FRONT-006 FIX: Usando ADMIN_ROLES importado al inicio
  // ISS-002: Roles are lowercase from backend (admin_sistema, farmacia, centro, vista)
  // Also support legacy roles: superusuario, admin_farmacia, usuario_normal, usuario_vista
  
  const hasRole = (role) => {
    if (!user) return false;
    // ISS-DIRECTOR FIX: Usar rol_efectivo del backend que incluye inferencia de rol
    const userRole = (user.rol_efectivo || user.rol || '').toLowerCase();
    const targetRole = role.toLowerCase();
    // Admin roles have access to everything
    if (ADMIN_ROLES.includes(userRole)) return true;
    return userRole === targetRole;
  };

  const hasAnyRole = (roles) => {
    if (!user) return false;
    // ISS-DIRECTOR FIX: Usar rol_efectivo del backend que incluye inferencia de rol
    const userRole = (user.rol_efectivo || user.rol || '').toLowerCase();
    // Admin roles have access to everything
    if (ADMIN_ROLES.includes(userRole)) return true;
    return roles.some(r => r.toLowerCase() === userRole);
  };

  /**
   * Verifica si el usuario tiene acceso a un módulo específico.
   * Usa los permisos booleanos del backend: perm_dashboard, perm_productos, etc.
   * 
   * @param {string} modulo - Nombre del módulo (dashboard, productos, lotes, etc.)
   * @returns {boolean} - true si tiene permiso
   */
  const canAccess = (modulo) => {
    if (!user) return false;
    // Superusuarios tienen acceso a todo
    if (user.is_superuser) return true;
    
    // Mapear nombre de módulo a campo perm_*
    const permisoField = `perm_${modulo.toLowerCase()}`;
    
    // Si el campo existe y es explícitamente true/false, usar ese valor
    if (permisoField in user && user[permisoField] !== null) {
      return user[permisoField] === true;
    }
    
    // Si hay permisos calculados del backend, usar esos
    if (user.permisos && typeof user.permisos === 'object') {
      const permisoKey = `ver${modulo.charAt(0).toUpperCase() + modulo.slice(1).toLowerCase()}`;
      if (permisoKey in user.permisos) {
        return user.permisos[permisoKey] === true;
      }
    }
    
    // Fallback: admins tienen acceso a todo
    // ISS-DIRECTOR FIX: Usar rol_efectivo del backend que incluye inferencia de rol
    const userRole = (user.rol_efectivo || user.rol || '').toLowerCase();
    if (ADMIN_ROLES.includes(userRole)) return true;
    
    return false;
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, checkAuth, hasRole, hasAnyRole, canAccess }}>
      {children}
    </AuthContext.Provider>
  );
}
