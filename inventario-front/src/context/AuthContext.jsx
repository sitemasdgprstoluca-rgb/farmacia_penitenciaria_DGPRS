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
  migrateFromLocalStorage 
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
    try {
      await authAPI.logout();
    } catch (error) {
      // Ignorar errores de logout, limpiar de todos modos
      console.warn('Error en logout:', error);
    }
    
    // Limpiar tokens de memoria
    clearTokens();
    // Limpiar datos de usuario
    localStorage.removeItem('user');
    setUser(null);
  };

  const hasRole = (role) => {
    if (!user) return false;
    if (user.rol === 'SUPERUSER') return true;
    return user.rol === role;
  };

  const hasAnyRole = (roles) => {
    if (!user) return false;
    if (user.rol === 'SUPERUSER') return true;
    return roles.includes(user.rol);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, checkAuth, hasRole, hasAnyRole }}>
      {children}
    </AuthContext.Provider>
  );
}
