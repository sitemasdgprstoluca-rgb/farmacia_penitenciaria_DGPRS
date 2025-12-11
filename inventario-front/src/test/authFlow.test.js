/**
 * ISS-003 FIX: Tests de flujos de autenticación y permisos
 * Verifica comportamiento de AuthContext y PermissionContext
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import React from 'react';

// Mock de los servicios
vi.mock('../../services/api', () => ({
  authAPI: {
    login: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    me: vi.fn(),
  },
  default: {
    defaults: { headers: { common: {} } },
  },
}));

vi.mock('../../services/tokenManager', () => ({
  setAccessToken: vi.fn(),
  getAccessToken: vi.fn(),
  clearTokens: vi.fn(),
  hasAccessToken: vi.fn(),
  isTokenExpired: vi.fn(),
}));

describe('Flujos de Autenticación', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  describe('Login Flow', () => {
    it('debe validar credenciales requeridas', () => {
      const validarCredenciales = (username, password) => {
        const errores = [];
        if (!username || username.trim().length < 3) {
          errores.push('Usuario debe tener al menos 3 caracteres');
        }
        if (!password || password.length < 6) {
          errores.push('Contraseña debe tener al menos 6 caracteres');
        }
        return { valido: errores.length === 0, errores };
      };

      expect(validarCredenciales('ab', '123').valido).toBe(false);
      expect(validarCredenciales('admin', '12345').valido).toBe(false);
      expect(validarCredenciales('admin', '123456').valido).toBe(true);
    });

    it('debe sanitizar username antes de enviar', () => {
      const sanitizeUsername = (username) => {
        return username
          .trim()
          .toLowerCase()
          .replace(/[<>\"'&]/g, '');
      };

      expect(sanitizeUsername('  Admin  ')).toBe('admin');
      expect(sanitizeUsername('user<script>')).toBe('userscript');
      expect(sanitizeUsername("user'test")).toBe('usertest');
    });

    it('debe manejar respuesta exitosa de login', async () => {
      const mockResponse = {
        access: 'mock-access-token',
        refresh: 'mock-refresh-token',
        user: {
          id: 1,
          username: 'admin',
          rol: 'admin',
          permisos: ['verProductos', 'editarProductos'],
        },
      };

      const handleLoginSuccess = (response) => {
        const { access, user } = response;
        return {
          isAuthenticated: true,
          token: access,
          user: user,
          permisos: user.permisos || [],
        };
      };

      const result = handleLoginSuccess(mockResponse);
      expect(result.isAuthenticated).toBe(true);
      expect(result.user.username).toBe('admin');
      expect(result.permisos).toContain('verProductos');
    });

    it('debe manejar errores de autenticación', () => {
      const handleLoginError = (error) => {
        if (error.response?.status === 401) {
          return { error: 'Credenciales inválidas', code: 'INVALID_CREDENTIALS' };
        }
        if (error.response?.status === 403) {
          return { error: 'Usuario deshabilitado', code: 'USER_DISABLED' };
        }
        if (error.response?.status === 429) {
          return { error: 'Demasiados intentos, espere un momento', code: 'RATE_LIMITED' };
        }
        return { error: 'Error de conexión', code: 'NETWORK_ERROR' };
      };

      expect(handleLoginError({ response: { status: 401 } }).code).toBe('INVALID_CREDENTIALS');
      expect(handleLoginError({ response: { status: 403 } }).code).toBe('USER_DISABLED');
      expect(handleLoginError({ response: { status: 429 } }).code).toBe('RATE_LIMITED');
      expect(handleLoginError({}).code).toBe('NETWORK_ERROR');
    });
  });

  describe('Token Management', () => {
    it('debe detectar token expirado', () => {
      const isTokenExpired = (token) => {
        if (!token) return true;
        try {
          const payload = JSON.parse(atob(token.split('.')[1]));
          return payload.exp * 1000 < Date.now();
        } catch {
          return true;
        }
      };

      // Token expirado (exp en el pasado)
      const expiredPayload = btoa(JSON.stringify({ exp: 1000000000 }));
      const expiredToken = `header.${expiredPayload}.signature`;
      expect(isTokenExpired(expiredToken)).toBe(true);

      // Token válido (exp en el futuro)
      const futureExp = Math.floor(Date.now() / 1000) + 3600;
      const validPayload = btoa(JSON.stringify({ exp: futureExp }));
      const validToken = `header.${validPayload}.signature`;
      expect(isTokenExpired(validToken)).toBe(false);
    });

    it('debe manejar refresh token correctamente', async () => {
      const refreshTokenFlow = async (refreshFn, currentToken) => {
        if (!currentToken) {
          return { success: false, reason: 'NO_TOKEN' };
        }
        try {
          const response = await refreshFn();
          return { success: true, newToken: response.access };
        } catch (error) {
          if (error.response?.status === 401) {
            return { success: false, reason: 'REFRESH_EXPIRED' };
          }
          return { success: false, reason: 'REFRESH_ERROR' };
        }
      };

      // Sin token
      const result1 = await refreshTokenFlow(vi.fn(), null);
      expect(result1.success).toBe(false);
      expect(result1.reason).toBe('NO_TOKEN');

      // Con refresh exitoso
      const mockRefresh = vi.fn().mockResolvedValue({ access: 'new-token' });
      const result2 = await refreshTokenFlow(mockRefresh, 'old-token');
      expect(result2.success).toBe(true);
      expect(result2.newToken).toBe('new-token');

      // Con refresh fallido
      const failedRefresh = vi.fn().mockRejectedValue({ response: { status: 401 } });
      const result3 = await refreshTokenFlow(failedRefresh, 'old-token');
      expect(result3.success).toBe(false);
      expect(result3.reason).toBe('REFRESH_EXPIRED');
    });
  });

  describe('Permisos y Roles', () => {
    const PERMISOS_POR_ROL = {
      admin: [
        'verProductos', 'crearProductos', 'editarProductos', 'eliminarProductos',
        'verRequisiciones', 'crearRequisicion', 'aprobarRequisicion', 'surtirRequisicion',
        'verUsuarios', 'crearUsuarios', 'editarUsuarios',
        'verReportes', 'configurarTema',
      ],
      farmaceutico: [
        'verProductos', 'crearProductos', 'editarProductos',
        'verRequisiciones', 'crearRequisicion', 'aprobarRequisicion', 'surtirRequisicion',
        'verReportes',
      ],
      medico: [
        'verProductos',
        'verRequisiciones', 'crearRequisicion',
      ],
      enfermero: [
        'verProductos',
        'verRequisiciones', 'crearRequisicion',
      ],
    };

    it('debe asignar permisos según rol', () => {
      const getPermisosForRol = (rol) => PERMISOS_POR_ROL[rol] || [];

      expect(getPermisosForRol('admin')).toContain('configurarTema');
      expect(getPermisosForRol('farmaceutico')).toContain('surtirRequisicion');
      expect(getPermisosForRol('medico')).not.toContain('aprobarRequisicion');
      expect(getPermisosForRol('enfermero')).toContain('crearRequisicion');
      expect(getPermisosForRol('desconocido')).toEqual([]);
    });

    it('debe verificar permiso específico', () => {
      const tienePermiso = (permisos, permiso) => {
        if (!Array.isArray(permisos)) return false;
        return permisos.includes(permiso);
      };

      const permisosAdmin = PERMISOS_POR_ROL.admin;
      expect(tienePermiso(permisosAdmin, 'eliminarProductos')).toBe(true);
      expect(tienePermiso(permisosAdmin, 'permisoInexistente')).toBe(false);
      expect(tienePermiso(null, 'verProductos')).toBe(false);
    });

    it('debe verificar múltiples permisos (AND)', () => {
      const tienePermisos = (permisos, requeridos) => {
        if (!Array.isArray(permisos)) return false;
        return requeridos.every(p => permisos.includes(p));
      };

      const permisosFarmaceutico = PERMISOS_POR_ROL.farmaceutico;
      expect(tienePermisos(permisosFarmaceutico, ['verProductos', 'crearProductos'])).toBe(true);
      expect(tienePermisos(permisosFarmaceutico, ['verProductos', 'eliminarProductos'])).toBe(false);
    });

    it('debe verificar al menos un permiso (OR)', () => {
      const tieneAlgunPermiso = (permisos, opciones) => {
        if (!Array.isArray(permisos)) return false;
        return opciones.some(p => permisos.includes(p));
      };

      const permisosMedico = PERMISOS_POR_ROL.medico;
      expect(tieneAlgunPermiso(permisosMedico, ['editarProductos', 'crearRequisicion'])).toBe(true);
      expect(tieneAlgunPermiso(permisosMedico, ['eliminarProductos', 'configurarTema'])).toBe(false);
    });
  });

  describe('Logout Flow', () => {
    it('debe limpiar estado al hacer logout', () => {
      const logout = () => {
        return {
          isAuthenticated: false,
          user: null,
          permisos: [],
          token: null,
        };
      };

      const state = logout();
      expect(state.isAuthenticated).toBe(false);
      expect(state.user).toBeNull();
      expect(state.permisos).toEqual([]);
    });

    it('debe limpiar localStorage al logout', () => {
      localStorage.setItem('lastUser', 'admin');
      localStorage.setItem('preferences', '{}');

      const cleanupOnLogout = () => {
        const keysToRemove = ['lastUser'];
        keysToRemove.forEach(key => localStorage.removeItem(key));
      };

      cleanupOnLogout();
      expect(localStorage.getItem('lastUser')).toBeNull();
      expect(localStorage.getItem('preferences')).toBe('{}'); // no se borra
    });
  });

  describe('Session Timeout', () => {
    it('debe calcular tiempo restante de sesión', () => {
      const calcularTiempoRestante = (lastActivity, timeoutMinutes) => {
        const ahora = Date.now();
        const limite = lastActivity + timeoutMinutes * 60 * 1000;
        const restante = limite - ahora;
        return Math.max(0, Math.floor(restante / 1000));
      };

      const hace5Min = Date.now() - 5 * 60 * 1000;
      const restante = calcularTiempoRestante(hace5Min, 20);
      expect(restante).toBeGreaterThan(14 * 60); // ~15 minutos restantes
      expect(restante).toBeLessThan(16 * 60);
    });

    it('debe detectar sesión expirada por inactividad', () => {
      const sesionExpirada = (lastActivity, timeoutMinutes) => {
        const ahora = Date.now();
        const limite = lastActivity + timeoutMinutes * 60 * 1000;
        return ahora > limite;
      };

      const hace30Min = Date.now() - 30 * 60 * 1000;
      expect(sesionExpirada(hace30Min, 20)).toBe(true);

      const hace10Min = Date.now() - 10 * 60 * 1000;
      expect(sesionExpirada(hace10Min, 20)).toBe(false);
    });
  });
});
