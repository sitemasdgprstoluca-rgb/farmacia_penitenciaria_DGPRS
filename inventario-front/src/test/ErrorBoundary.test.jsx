/**
 * ISS-002 FIX: Tests para ErrorBoundary mejorado
 * 
 * Verifica:
 * - Captura de errores de renderizado
 * - Clasificación de tipos de error (config, auth, network, render)
 * - UI apropiada para cada tipo de error
 * - HOC withErrorBoundary
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

// Mock de api.js para las funciones de configuración
vi.mock('../services/api', () => ({
  getApiConfigError: vi.fn(() => null),
  isHttpInsecure: vi.fn(() => false),
}));

import ErrorBoundary, { withErrorBoundary } from '../components/ErrorBoundary';
import { getApiConfigError, isHttpInsecure } from '../services/api';

// Componente que lanza error para testing
const ThrowError = ({ error }) => {
  throw error;
};

// Componente normal para testing
const NormalComponent = () => <div data-testid="normal">Contenido normal</div>;

describe('ErrorBoundary', () => {
  // Suprimir errores de consola durante tests
  const originalError = console.error;
  beforeEach(() => {
    console.error = vi.fn();
  });
  afterEach(() => {
    console.error = originalError;
    vi.clearAllMocks();
  });

  describe('renderizado normal', () => {
    it('debe renderizar hijos cuando no hay error', () => {
      render(
        <ErrorBoundary>
          <NormalComponent />
        </ErrorBoundary>
      );
      
      expect(screen.getByTestId('normal')).toBeInTheDocument();
      expect(screen.getByText('Contenido normal')).toBeInTheDocument();
    });
  });

  describe('captura de errores', () => {
    it('debe capturar error de renderizado y mostrar UI de error', () => {
      const error = new Error('Error de prueba');
      
      render(
        <ErrorBoundary>
          <ThrowError error={error} />
        </ErrorBoundary>
      );
      
      expect(screen.getByText('¡Algo salió mal!')).toBeInTheDocument();
    });

    it('debe mostrar detalles técnicos solo en desarrollo', () => {
      const originalDev = import.meta.env.DEV;
      const error = new Error('Error detallado');
      
      render(
        <ErrorBoundary>
          <ThrowError error={error} />
        </ErrorBoundary>
      );
      
      // En desarrollo debería haber un botón para ver detalles
      if (import.meta.env.DEV) {
        expect(screen.getByText('Ver detalles técnicos')).toBeInTheDocument();
      }
    });
  });

  describe('clasificación de errores', () => {
    it('debe clasificar error de configuración correctamente', () => {
      const configError = new Error('Config error');
      configError.name = 'ApiConfigurationError';
      configError.isConfigError = true;
      
      getApiConfigError.mockReturnValue('Error de configuración mock');
      
      render(
        <ErrorBoundary>
          <ThrowError error={configError} />
        </ErrorBoundary>
      );
      
      expect(screen.getByText('Error de Configuración')).toBeInTheDocument();
    });

    it('debe clasificar error de autenticación correctamente', () => {
      const authError = new Error('Unauthorized');
      authError.response = { status: 401 };
      
      render(
        <ErrorBoundary>
          <ThrowError error={authError} />
        </ErrorBoundary>
      );
      
      expect(screen.getByText('Sesión Expirada')).toBeInTheDocument();
    });

    it('debe clasificar error de red correctamente', () => {
      const networkError = new Error('Network Error');
      networkError.code = 'ERR_NETWORK';
      
      render(
        <ErrorBoundary>
          <ThrowError error={networkError} />
        </ErrorBoundary>
      );
      
      expect(screen.getByText('Error de Conexión')).toBeInTheDocument();
    });
  });

  describe('botones de acción', () => {
    it('debe tener botón de recargar', () => {
      const error = new Error('Error');
      
      render(
        <ErrorBoundary>
          <ThrowError error={error} />
        </ErrorBoundary>
      );
      
      expect(screen.getByText('Recargar página')).toBeInTheDocument();
    });

    it('debe tener botón de ir al inicio', () => {
      const error = new Error('Error');
      
      render(
        <ErrorBoundary>
          <ThrowError error={error} />
        </ErrorBoundary>
      );
      
      expect(screen.getByText('Ir al inicio')).toBeInTheDocument();
    });
  });

  describe('error de seguridad HTTPS', () => {
    it('debe mostrar error de seguridad cuando isHttpInsecure es true', () => {
      const configError = new Error('HTTPS required');
      configError.isConfigError = true;
      
      isHttpInsecure.mockReturnValue(true);
      getApiConfigError.mockReturnValue('HTTPS requerido');
      
      render(
        <ErrorBoundary>
          <ThrowError error={configError} />
        </ErrorBoundary>
      );
      
      expect(screen.getByText('Error de Seguridad')).toBeInTheDocument();
    });
  });
});

describe('withErrorBoundary HOC', () => {
  const originalError = console.error;
  beforeEach(() => {
    console.error = vi.fn();
  });
  afterEach(() => {
    console.error = originalError;
  });

  it('debe envolver componente con ErrorBoundary', () => {
    const WrappedComponent = withErrorBoundary(NormalComponent);
    
    render(<WrappedComponent />);
    
    expect(screen.getByTestId('normal')).toBeInTheDocument();
  });

  it('debe capturar errores del componente envuelto', () => {
    const ErrorComponent = () => {
      throw new Error('Error en componente');
    };
    const WrappedComponent = withErrorBoundary(ErrorComponent);
    
    render(<WrappedComponent />);
    
    expect(screen.getByText('¡Algo salió mal!')).toBeInTheDocument();
  });

  it('debe establecer displayName correcto', () => {
    const TestComponent = () => <div>Test</div>;
    TestComponent.displayName = 'TestComponent';
    
    const WrappedComponent = withErrorBoundary(TestComponent);
    
    expect(WrappedComponent.displayName).toBe('WithErrorBoundary(TestComponent)');
  });

  it('debe usar nombre de función si no hay displayName', () => {
    function MyComponent() {
      return <div>Test</div>;
    }
    
    const WrappedComponent = withErrorBoundary(MyComponent);
    
    expect(WrappedComponent.displayName).toBe('WithErrorBoundary(MyComponent)');
  });
});

describe('ErrorBoundary recovery', () => {
  const originalError = console.error;
  beforeEach(() => {
    console.error = vi.fn();
  });
  afterEach(() => {
    console.error = originalError;
  });

  it('debe permitir recuperación después de error', async () => {
    // Mock de location.reload
    const reloadMock = vi.fn();
    Object.defineProperty(window, 'location', {
      value: { reload: reloadMock, href: '' },
      writable: true,
    });

    const error = new Error('Error recuperable');
    
    render(
      <ErrorBoundary>
        <ThrowError error={error} />
      </ErrorBoundary>
    );
    
    const reloadButton = screen.getByText('Recargar página');
    fireEvent.click(reloadButton);
    
    expect(reloadMock).toHaveBeenCalled();
  });
});
