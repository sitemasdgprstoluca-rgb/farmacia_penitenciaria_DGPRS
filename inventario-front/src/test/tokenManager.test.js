/**
 * Tests para tokenManager - Gestión segura de tokens JWT
 * 
 * ISS-005: Tests unitarios para servicios críticos
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  setAccessToken,
  getAccessToken,
  hasAccessToken,
  clearTokens,
  onSessionChange,
  migrateFromLocalStorage,
  getTokenStatus
} from '../services/tokenManager';

describe('tokenManager', () => {
  beforeEach(() => {
    // Limpiar tokens antes de cada test
    clearTokens();
  });

  describe('setAccessToken / getAccessToken', () => {
    it('debe almacenar y recuperar un token', () => {
      const token = 'test-access-token-123';
      setAccessToken(token);
      expect(getAccessToken()).toBe(token);
    });

    it('debe devolver null si no hay token', () => {
      expect(getAccessToken()).toBeNull();
    });

    it('debe sobrescribir token existente', () => {
      setAccessToken('token-1');
      setAccessToken('token-2');
      expect(getAccessToken()).toBe('token-2');
    });
  });

  describe('hasAccessToken', () => {
    it('debe devolver false si no hay token', () => {
      expect(hasAccessToken()).toBe(false);
    });

    it('debe devolver true si hay token', () => {
      setAccessToken('some-token');
      expect(hasAccessToken()).toBe(true);
    });
  });

  describe('clearTokens', () => {
    it('debe limpiar el token almacenado', () => {
      setAccessToken('token-to-clear');
      expect(hasAccessToken()).toBe(true);
      clearTokens();
      expect(hasAccessToken()).toBe(false);
      expect(getAccessToken()).toBeNull();
    });
  });

  describe('onSessionChange', () => {
    it('debe notificar cuando se establece un token', () => {
      const callback = vi.fn();
      const unsubscribe = onSessionChange(callback);
      
      setAccessToken('new-token');
      
      expect(callback).toHaveBeenCalledWith(true);
      unsubscribe();
    });

    it('debe notificar cuando se limpia el token', () => {
      const callback = vi.fn();
      setAccessToken('token');
      
      const unsubscribe = onSessionChange(callback);
      clearTokens();
      
      expect(callback).toHaveBeenCalledWith(false);
      unsubscribe();
    });

    it('debe permitir desuscribirse', () => {
      const callback = vi.fn();
      const unsubscribe = onSessionChange(callback);
      
      unsubscribe();
      setAccessToken('token');
      
      // No debe llamar al callback después de desuscribirse
      expect(callback).not.toHaveBeenCalled();
    });

    it('debe manejar errores en callbacks sin afectar otros', () => {
      const errorCallback = vi.fn(() => { throw new Error('Test error'); });
      const goodCallback = vi.fn();
      
      const unsubscribe1 = onSessionChange(errorCallback);
      const unsubscribe2 = onSessionChange(goodCallback);
      
      // No debe lanzar excepción y debe llamar al segundo callback
      expect(() => setAccessToken('token')).not.toThrow();
      expect(goodCallback).toHaveBeenCalledWith(true);
      
      unsubscribe1();
      unsubscribe2();
    });
  });

  describe('migrateFromLocalStorage', () => {
    it('debe retornar false si no hay token en localStorage', () => {
      expect(migrateFromLocalStorage()).toBe(false);
    });

    it('debe descartar tokens inválidos', () => {
      localStorage.setItem('token', 'invalid-not-jwt');
      expect(migrateFromLocalStorage()).toBe(false);
      expect(localStorage.getItem('token')).toBeNull();
    });
  });

  describe('getTokenStatus', () => {
    it('debe retornar estado sin token', () => {
      const status = getTokenStatus();
      expect(status.hasAccessToken).toBe(false);
      expect(status.accessTokenLength).toBe(0);
    });

    it('debe retornar estado con token', () => {
      setAccessToken('test-token-12345');
      const status = getTokenStatus();
      expect(status.hasAccessToken).toBe(true);
      expect(status.accessTokenLength).toBe(16);
    });
  });
});
