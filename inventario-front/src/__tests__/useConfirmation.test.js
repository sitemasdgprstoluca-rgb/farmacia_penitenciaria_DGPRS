/**
 * @fileoverview Tests para el hook useConfirmation (ISS-SEC)
 * Verifica el funcionamiento del flujo de confirmación en 2 pasos
 */

import { renderHook, act } from '@testing-library/react';
import { useConfirmation, CONFIRMATION_TYPES } from '../hooks/useConfirmation';

describe('useConfirmation Hook', () => {
  describe('Estado inicial', () => {
    it('debe iniciar con el modal cerrado', () => {
      const { result } = renderHook(() => useConfirmation());
      
      expect(result.current.confirmState.isOpen).toBe(false);
      expect(result.current.confirmState.isLoading).toBe(false);
    });

    it('debe tener valores por defecto correctos', () => {
      const { result } = renderHook(() => useConfirmation());
      
      expect(result.current.confirmState.title).toBe('');
      expect(result.current.confirmState.message).toBe('');
      expect(result.current.confirmState.isCritical).toBe(false);
      expect(result.current.confirmState.confirmPhrase).toBe(null);
    });
  });

  describe('requestDeleteConfirmation', () => {
    it('debe abrir el modal con los datos correctos', () => {
      const { result } = renderHook(() => useConfirmation());
      const mockOnConfirm = jest.fn();

      act(() => {
        result.current.requestDeleteConfirmation({
          title: 'Eliminar Item',
          message: '¿Está seguro?',
          itemInfo: { nombre: 'Test' },
          onConfirm: mockOnConfirm
        });
      });

      expect(result.current.confirmState.isOpen).toBe(true);
      expect(result.current.confirmState.title).toBe('Eliminar Item');
      expect(result.current.confirmState.message).toBe('¿Está seguro?');
      expect(result.current.confirmState.itemInfo).toEqual({ nombre: 'Test' });
      expect(result.current.confirmState.actionType).toBe(CONFIRMATION_TYPES.DELETE);
    });

    it('debe configurar confirmación crítica correctamente', () => {
      const { result } = renderHook(() => useConfirmation());
      const mockOnConfirm = jest.fn();

      act(() => {
        result.current.requestDeleteConfirmation({
          title: 'Eliminar Usuario',
          message: 'Esta acción es permanente',
          onConfirm: mockOnConfirm,
          isCritical: true,
          confirmPhrase: 'ELIMINAR'
        });
      });

      expect(result.current.confirmState.isCritical).toBe(true);
      expect(result.current.confirmState.confirmPhrase).toBe('ELIMINAR');
      expect(result.current.confirmState.actionType).toBe(CONFIRMATION_TYPES.DELETE_CRITICAL);
    });

    it('debe pasar actionData a la función onConfirm', () => {
      const { result } = renderHook(() => useConfirmation());
      const mockOnConfirm = jest.fn();

      act(() => {
        result.current.requestDeleteConfirmation({
          title: 'Test',
          message: 'Test message',
          onConfirm: mockOnConfirm,
          actionData: { id: 123, name: 'test' }
        });
      });

      expect(result.current.confirmState.actionData).toEqual({ id: 123, name: 'test' });
    });
  });

  describe('requestSaveConfirmation', () => {
    it('debe configurar tipo SAVE', () => {
      const { result } = renderHook(() => useConfirmation());
      const mockOnConfirm = jest.fn();

      act(() => {
        result.current.requestSaveConfirmation({
          title: 'Guardar Cambios',
          message: '¿Confirma los cambios?',
          onConfirm: mockOnConfirm
        });
      });

      expect(result.current.confirmState.isOpen).toBe(true);
      expect(result.current.confirmState.actionType).toBe(CONFIRMATION_TYPES.SAVE);
      expect(result.current.confirmState.confirmText).toBe('Guardar');
    });
  });

  describe('cancelConfirmation', () => {
    it('debe cerrar el modal y resetear el estado', () => {
      const { result } = renderHook(() => useConfirmation());
      const mockOnConfirm = jest.fn();

      // Primero abrir
      act(() => {
        result.current.requestDeleteConfirmation({
          title: 'Test',
          message: 'Test',
          onConfirm: mockOnConfirm
        });
      });

      expect(result.current.confirmState.isOpen).toBe(true);

      // Luego cancelar
      act(() => {
        result.current.cancelConfirmation();
      });

      expect(result.current.confirmState.isOpen).toBe(false);
      expect(result.current.confirmState.title).toBe('');
      expect(result.current.confirmState.onConfirm).toBe(null);
    });
  });

  describe('executeWithConfirmation', () => {
    it('debe ejecutar la función onConfirm y cerrar el modal', async () => {
      const { result } = renderHook(() => useConfirmation());
      const mockOnConfirm = jest.fn().mockResolvedValue();

      // Abrir modal
      act(() => {
        result.current.requestDeleteConfirmation({
          title: 'Test',
          message: 'Test',
          onConfirm: mockOnConfirm,
          actionData: { id: 1 }
        });
      });

      // Ejecutar confirmación
      await act(async () => {
        await result.current.executeWithConfirmation(mockOnConfirm);
      });

      expect(mockOnConfirm).toHaveBeenCalled();
      expect(result.current.confirmState.isOpen).toBe(false);
    });

    it('debe establecer isLoading durante la ejecución', async () => {
      const { result } = renderHook(() => useConfirmation());
      
      let resolvePromise;
      const mockOnConfirm = jest.fn().mockImplementation(() => {
        return new Promise(resolve => {
          resolvePromise = resolve;
        });
      });

      act(() => {
        result.current.requestDeleteConfirmation({
          title: 'Test',
          message: 'Test',
          onConfirm: mockOnConfirm
        });
      });

      // Iniciar ejecución (no esperar)
      let executePromise;
      act(() => {
        executePromise = result.current.executeWithConfirmation(mockOnConfirm);
      });

      // Durante la ejecución, isLoading debe ser true
      expect(result.current.confirmState.isLoading).toBe(true);

      // Resolver la promesa
      await act(async () => {
        resolvePromise();
        await executePromise;
      });

      expect(result.current.confirmState.isLoading).toBe(false);
    });

    it('debe manejar errores sin cerrar el modal', async () => {
      const { result } = renderHook(() => useConfirmation());
      const mockOnConfirm = jest.fn().mockRejectedValue(new Error('Test error'));

      act(() => {
        result.current.requestDeleteConfirmation({
          title: 'Test',
          message: 'Test',
          onConfirm: mockOnConfirm
        });
      });

      // Ejecutar confirmación que falla
      await act(async () => {
        try {
          await result.current.executeWithConfirmation(mockOnConfirm);
        } catch (e) {
          // Error esperado
        }
      });

      // El modal debe permanecer abierto para reintentar
      expect(result.current.confirmState.isOpen).toBe(true);
      expect(result.current.confirmState.isLoading).toBe(false);
    });

    it('debe pasar confirmed: true y actionData a la función', async () => {
      const { result } = renderHook(() => useConfirmation());
      const mockOnConfirm = jest.fn().mockResolvedValue();

      act(() => {
        result.current.requestDeleteConfirmation({
          title: 'Test',
          message: 'Test',
          onConfirm: mockOnConfirm,
          actionData: { itemId: 42 }
        });
      });

      await act(async () => {
        await result.current.executeWithConfirmation(result.current.confirmState.onConfirm);
      });

      expect(mockOnConfirm).toHaveBeenCalledWith(expect.objectContaining({
        confirmed: true,
        actionData: { itemId: 42 }
      }));
    });
  });

  describe('Textos personalizados', () => {
    it('debe permitir confirmText personalizado', () => {
      const { result } = renderHook(() => useConfirmation());

      act(() => {
        result.current.requestDeleteConfirmation({
          title: 'Restablecer',
          message: 'Test',
          onConfirm: jest.fn(),
          confirmText: 'Restablecer todo'
        });
      });

      expect(result.current.confirmState.confirmText).toBe('Restablecer todo');
    });

    it('debe permitir cancelText personalizado', () => {
      const { result } = renderHook(() => useConfirmation());

      act(() => {
        result.current.requestDeleteConfirmation({
          title: 'Test',
          message: 'Test',
          onConfirm: jest.fn(),
          cancelText: 'No, mantener'
        });
      });

      expect(result.current.confirmState.cancelText).toBe('No, mantener');
    });
  });
});

describe('CONFIRMATION_TYPES', () => {
  it('debe tener los tipos esperados', () => {
    expect(CONFIRMATION_TYPES.SAVE).toBe('save');
    expect(CONFIRMATION_TYPES.DELETE).toBe('delete');
    expect(CONFIRMATION_TYPES.DELETE_CRITICAL).toBe('delete_critical');
  });
});
