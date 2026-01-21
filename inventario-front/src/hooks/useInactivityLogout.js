import { useCallback, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { setApiActivityHandler } from '../services/api';
import { hasAccessToken, clearTokens, isRefreshInProgress, isLogoutInProgress } from '../services/tokenManager';

const parseMinutes = (value, fallback) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
};

// Claves de sessionStorage que deben limpiarse en logout por inactividad
const SESSION_KEYS_TO_CLEAR = ['session_uid', 'session_role', 'session_hash'];

/**
 * ISS-002 FIX (audit33): Hook de logout por inactividad
 * Mejorado para coordinarse con el refresh de tokens y evitar race conditions
 * SEGURIDAD: Ahora limpia TODOS los datos de sesión (memoria, localStorage, sessionStorage)
 */
export const useInactivityLogout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const timerRef = useRef(null);
  const timeoutMinutes = parseMinutes(import.meta.env.VITE_INACTIVITY_MINUTES, 20);
  const timeoutMs = timeoutMinutes * 60 * 1000;

  const clearSession = useCallback(() => {
    // SEGURIDAD: Limpiar tokens en memoria (access + refresh)
    clearTokens();
    // Limpiar localStorage
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    // SEGURIDAD: Limpiar sessionStorage para prevenir rehidratación/refresh
    SESSION_KEYS_TO_CLEAR.forEach(key => {
      try {
        sessionStorage.removeItem(key);
      } catch (e) {
        // Ignorar errores de storage
      }
    });
  }, []);

  const logout = useCallback(() => {
    // ISS-002 FIX (audit33): No hacer logout si hay refresh en progreso
    if (isRefreshInProgress?.() || isLogoutInProgress?.()) {
      console.info('[useInactivityLogout] Postergando logout: refresh/logout en progreso');
      // Reprogramar logout para cuando termine el refresh
      timerRef.current = setTimeout(logout, 2000);
      return;
    }
    
    clearTimeout(timerRef.current);
    clearSession();
    toast.error('Tu sesión ha expirado por inactividad');
    navigate('/login');
  }, [clearSession, navigate]);

  const resetTimer = useCallback(() => {
    // ISS-002 FIX (audit33): No resetear timer si hay refresh en progreso
    if (isRefreshInProgress?.()) {
      return;
    }
    
    // SEGURIDAD: Verificar sesión usando token en memoria Y sessionStorage
    // Ambos deben existir para considerar la sesión válida
    const hasTokenInMemory = hasAccessToken();
    const hasSessionData = Boolean(sessionStorage.getItem('session_uid'));
    const hasSession = hasTokenInMemory || (hasSessionData && Boolean(localStorage.getItem('user')));

    if (!hasSession) {
      clearTimeout(timerRef.current);
      return;
    }

    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(logout, timeoutMs);
  }, [logout, timeoutMs]);

  useEffect(() => {
    const activityEvents = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];

    activityEvents.forEach((eventName) => {
      window.addEventListener(eventName, resetTimer);
    });

    setApiActivityHandler(() => resetTimer());
    resetTimer();

    return () => {
      activityEvents.forEach((eventName) => {
        window.removeEventListener(eventName, resetTimer);
      });
      setApiActivityHandler(null);
      clearTimeout(timerRef.current);
    };
  }, [resetTimer, location.pathname]);
};
