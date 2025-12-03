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
  setLogoutInProgress
} from '../services/tokenManager';

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
        // Intentar refresh (la cookie HttpOnly puede existir)
        try {
          const refreshResponse = await authAPI.refresh();
          if (refreshResponse.data.access) {
            setAccessToken(refreshResponse.data.access);
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
    const { access, user: userData } = response.data;
    
    // Guardar access token en memoria (NO en localStorage)
    setAccessToken(access);
    
    // El refresh token viene como cookie HttpOnly del servidor
    // No necesitamos manejarlo en el frontend
    
    // Obtener perfil completo si no viene en la respuesta
    if (userData) {
      setUser(userData);
      return userData;
    } else {
      const profile = await authAPI.me();
      setUser(profile.data);
      return profile.data;
    }
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
      console.warn('Error en logout (limpieza local realizada):', error);
    }
    
    // Limpiar tokens de memoria (esto mantiene logoutInProgress=true)
    clearTokens();
    // Limpiar datos de usuario
    localStorage.removeItem('user');
    setUser(null);
  };

  // ISS-002: Roles are lowercase from backend (admin_sistema, farmacia, centro, vista)
  // Also support legacy roles: superusuario, admin_farmacia, usuario_normal, usuario_vista
  const ADMIN_ROLES = ['admin_sistema', 'superusuario', 'admin_farmacia'];
  
  const hasRole = (role) => {
    if (!user) return false;
    // Normalize both to lowercase for comparison
    const userRole = (user.rol || '').toLowerCase();
    const targetRole = role.toLowerCase();
    // Admin roles have access to everything
    if (ADMIN_ROLES.includes(userRole)) return true;
    return userRole === targetRole;
  };

  const hasAnyRole = (roles) => {
    if (!user) return false;
    const userRole = (user.rol || '').toLowerCase();
    // Admin roles have access to everything
    if (ADMIN_ROLES.includes(userRole)) return true;
    return roles.some(r => r.toLowerCase() === userRole);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, checkAuth, hasRole, hasAnyRole }}>
      {children}
    </AuthContext.Provider>
  );
}
