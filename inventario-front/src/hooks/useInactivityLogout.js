import { useCallback, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { setApiActivityHandler } from '../services/api';

const parseMinutes = (value, fallback) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
};

export const useInactivityLogout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const timerRef = useRef(null);
  const timeoutMinutes = parseMinutes(import.meta.env.VITE_INACTIVITY_MINUTES, 20);
  const timeoutMs = timeoutMinutes * 60 * 1000;

  const clearSession = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  }, []);

  const logout = useCallback(() => {
    clearTimeout(timerRef.current);
    clearSession();
    toast.error('Tu sesión ha expirado por inactividad');
    navigate('/login');
  }, [clearSession, navigate]);

  const resetTimer = useCallback(() => {
    const hasSession = Boolean(localStorage.getItem('token') || localStorage.getItem('user'));

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
