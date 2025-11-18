// filepath: inventario-front/src/context/AuthContext.jsx
import { useState, useEffect } from 'react';
import { authAPI } from '../services/api';
import { DEV_CONFIG, devLog } from '../config/dev';
import { AuthContext } from './contexts';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (DEV_CONFIG.ENABLED) {
      devLog('Modo desarrollo activado - Usuario automtico cargado');
      setUser(DEV_CONFIG.AUTO_USER);
      setLoading(false);
    } else {
      checkAuth();
    }
  }, []);

  const checkAuth = async () => {
    try {
      const response = await authAPI.me();
      setUser(response.data);
    } catch (error) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (credentials) => {
    if (DEV_CONFIG.ENABLED) {
      devLog('Login simulado en modo desarrollo', credentials);
      setUser(DEV_CONFIG.AUTO_USER);
      return { user: DEV_CONFIG.AUTO_USER };
    }

    const response = await authAPI.login(credentials);
    const { access, refresh } = response.data;
    localStorage.setItem('token', access);
    if (refresh) {
      localStorage.setItem('refresh_token', refresh);
    }
    const profile = await authAPI.me();
    setUser(profile.data);
    return profile.data;
  };

  const logout = async () => {
    if (DEV_CONFIG.ENABLED) {
      devLog('Logout simulado en modo desarrollo');
      // En modo desarrollo, redirigir al login pero no borrar sesin
      setUser(null);
      setTimeout(() => {
        setUser(DEV_CONFIG.AUTO_USER);
      }, 100);
      return;
    }

    await authAPI.logout();
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
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
