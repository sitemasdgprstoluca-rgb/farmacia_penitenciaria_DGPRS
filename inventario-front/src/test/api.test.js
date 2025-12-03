/**
 * Tests para api.js - Cliente API con gestión segura
 * 
 * ISS-005: Tests unitarios para servicios críticos
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock de import.meta.env antes de importar api.js
const mockEnv = {
  VITE_API_URL: '',
  VITE_API_BASE_URL: '',
  DEV: true,
  MODE: 'development',
  VITE_ALLOW_INSECURE_HTTP: 'false'
};

vi.mock('../services/tokenManager', () => ({
  getAccessToken: vi.fn(() => 'mock-access-token'),
  setAccessToken: vi.fn(),
  clearTokens: vi.fn()
}));

describe('api.js configuration', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  describe('getApiConfigError', () => {
    it('debe devolver null en modo desarrollo sin URL configurada', async () => {
      // En desarrollo sin URL, debe usar localhost
      vi.stubGlobal('import.meta', { env: { ...mockEnv, DEV: true } });
      
      const { getApiConfigError, isApiConfigured } = await import('../services/api.js');
      
      expect(getApiConfigError()).toBeNull();
      expect(isApiConfigured()).toBe(true);
    });
  });

  describe('isHttpInsecure', () => {
    it('debe devolver false en modo desarrollo', async () => {
      vi.stubGlobal('import.meta', { env: { ...mockEnv, DEV: true } });
      
      const { isHttpInsecure } = await import('../services/api.js');
      
      expect(isHttpInsecure()).toBe(false);
    });
  });

  describe('hasHttpWarning', () => {
    it('debe exportar hasHttpWarning function', async () => {
      const { hasHttpWarning } = await import('../services/api.js');
      expect(typeof hasHttpWarning).toBe('function');
    });
  });
});

describe('API Client Functions', () => {
  let apiModule;

  beforeEach(async () => {
    vi.resetModules();
    apiModule = await import('../services/api.js');
  });

  describe('apiClient', () => {
    it('debe exportar apiClient como default', () => {
      expect(apiModule.default).toBeDefined();
    });

    it('debe tener withCredentials habilitado', () => {
      expect(apiModule.default.defaults.withCredentials).toBe(true);
    });

    it('debe tener Content-Type application/json', () => {
      expect(apiModule.default.defaults.headers['Content-Type']).toBe('application/json');
    });
  });

  describe('authAPI', () => {
    it('debe exportar objeto authAPI', () => {
      expect(apiModule.authAPI).toBeDefined();
      expect(typeof apiModule.authAPI).toBe('object');
    });

    it('debe tener métodos de autenticación', () => {
      expect(typeof apiModule.authAPI.login).toBe('function');
      expect(typeof apiModule.authAPI.logout).toBe('function');
      expect(typeof apiModule.authAPI.getProfile).toBe('function');
    });
  });

  describe('inventarioAPI', () => {
    it('debe exportar objeto inventarioAPI', () => {
      expect(apiModule.inventarioAPI).toBeDefined();
      expect(typeof apiModule.inventarioAPI).toBe('object');
    });
  });
});

describe('Error Handling', () => {
  it('debe exportar función para descargar archivos', async () => {
    const { downloadFile } = await import('../services/api.js');
    expect(typeof downloadFile).toBe('function');
  });

  it('debe exportar función registerActivityCallback', async () => {
    const { registerActivityCallback } = await import('../services/api.js');
    expect(typeof registerActivityCallback).toBe('function');
  });
});
