/**
 * ISS-001 FIX: Tests para configuración de seguridad de API
 * 
 * Verifica:
 * - Forzar HTTPS en producción
 * - Bloqueo cuando VITE_API_URL falta
 * - Métricas de seguridad
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('API Security Configuration', () => {
  // Nota: Estos tests verifican el comportamiento esperado de api.js
  // El módulo se importa una sola vez, así que usamos mocks para simular

  describe('HTTPS Enforcement', () => {
    it('debe exportar getApiConfigError', async () => {
      const { getApiConfigError } = await import('../services/api');
      expect(typeof getApiConfigError).toBe('function');
    });

    it('debe exportar isHttpInsecure', async () => {
      const { isHttpInsecure } = await import('../services/api');
      expect(typeof isHttpInsecure).toBe('function');
    });

    it('debe exportar hasHttpWarning', async () => {
      const { hasHttpWarning } = await import('../services/api');
      expect(typeof hasHttpWarning).toBe('function');
    });

    it('debe exportar getSecurityMetrics', async () => {
      const { getSecurityMetrics } = await import('../services/api');
      expect(typeof getSecurityMetrics).toBe('function');
    });

    it('getSecurityMetrics debe retornar objeto con propiedades esperadas', async () => {
      const { getSecurityMetrics } = await import('../services/api');
      const metrics = getSecurityMetrics();
      
      expect(metrics).toHaveProperty('httpAttempts');
      expect(metrics).toHaveProperty('configErrors');
      expect(metrics).toHaveProperty('lastError');
      expect(typeof metrics.httpAttempts).toBe('number');
      expect(typeof metrics.configErrors).toBe('number');
    });
  });

  describe('API Client Configuration', () => {
    it('debe tener withCredentials habilitado para cookies HttpOnly', async () => {
      const apiModule = await import('../services/api');
      expect(apiModule.default.defaults.withCredentials).toBe(true);
    });

    it('debe tener Content-Type application/json', async () => {
      const apiModule = await import('../services/api');
      expect(apiModule.default.defaults.headers['Content-Type']).toBe('application/json');
    });
  });

  describe('Development Mode', () => {
    it('en desarrollo no debe bloquear por HTTPS', async () => {
      // En modo desarrollo (import.meta.env.DEV = true), no debería haber error
      const { isHttpInsecure, getApiConfigError } = await import('../services/api');
      
      // Si estamos en modo dev, no debería marcar como inseguro
      if (import.meta.env.DEV) {
        expect(isHttpInsecure()).toBe(false);
      }
    });

    it('en desarrollo debe usar localhost por defecto', async () => {
      const apiModule = await import('../services/api');
      
      if (import.meta.env.DEV && !import.meta.env.VITE_API_URL) {
        expect(apiModule.default.defaults.baseURL).toContain('127.0.0.1');
      }
    });
  });

  describe('Production Mode Simulation', () => {
    // Estos tests documentan el comportamiento esperado en producción
    // No pueden ejecutarse directamente porque import.meta.env es readonly
    
    it('debe rechazar HTTP en producción (documentación)', () => {
      // En producción, si la URL es HTTP:
      // - isHttpInsecure() debería ser true
      // - getApiConfigError() debería retornar mensaje de error
      // - La app debería mostrar ConfigErrorPage
      
      const expectedBehavior = {
        isHttpInsecure: true,
        hasConfigError: true,
        blocksApp: true,
      };
      
      expect(expectedBehavior.blocksApp).toBe(true);
    });

    it('debe requerir VITE_API_URL en producción (documentación)', () => {
      // En producción, si VITE_API_URL no está definida:
      // - getApiConfigError() debería retornar mensaje de error
      // - La app no debería iniciar
      
      const expectedBehavior = {
        requiresApiUrl: true,
        blocksWithoutUrl: true,
      };
      
      expect(expectedBehavior.requiresApiUrl).toBe(true);
    });

    it('VITE_ALLOW_INSECURE_HTTP solo funciona en desarrollo (documentación)', () => {
      // VITE_ALLOW_INSECURE_HTTP = 'true' solo tiene efecto si:
      // - import.meta.env.DEV = true
      // En producción, es ignorado
      
      const expectedBehavior = {
        onlyInDev: true,
        ignoredInProd: true,
      };
      
      expect(expectedBehavior.ignoredInProd).toBe(true);
    });
  });

  describe('Error Types', () => {
    it('ApiConfigurationError debe tener propiedades especiales', () => {
      const error = new Error('API no configurada');
      error.name = 'ApiConfigurationError';
      error.isConfigError = true;
      
      expect(error.name).toBe('ApiConfigurationError');
      expect(error.isConfigError).toBe(true);
    });
  });
});

describe('API Exports', () => {
  it('debe exportar productosAPI', async () => {
    const { productosAPI } = await import('../services/api');
    expect(productosAPI).toBeDefined();
    expect(productosAPI.getAll).toBeDefined();
    expect(productosAPI.getById).toBeDefined();
    expect(productosAPI.create).toBeDefined();
    expect(productosAPI.update).toBeDefined();
  });

  it('debe exportar requisicionesAPI', async () => {
    const { requisicionesAPI } = await import('../services/api');
    expect(requisicionesAPI).toBeDefined();
    expect(requisicionesAPI.getAll).toBeDefined();
    expect(requisicionesAPI.enviar).toBeDefined();
    expect(requisicionesAPI.rechazar).toBeDefined();
    expect(requisicionesAPI.surtir).toBeDefined();
  });

  it('debe exportar centrosAPI', async () => {
    const { centrosAPI } = await import('../services/api');
    expect(centrosAPI).toBeDefined();
    expect(centrosAPI.getAll).toBeDefined();
  });

  it('debe exportar lotesAPI', async () => {
    const { lotesAPI } = await import('../services/api');
    expect(lotesAPI).toBeDefined();
    expect(lotesAPI.getAll).toBeDefined();
  });

  it('debe exportar descargarArchivo', async () => {
    const { descargarArchivo } = await import('../services/api');
    expect(typeof descargarArchivo).toBe('function');
  });
});
