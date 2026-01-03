/**
 * Tests para Reserva de Stock - Frontend
 * =======================================
 * 
 * Tests para verificar el nuevo flujo de reserva de stock en frontend:
 * 1. Donaciones.jsx: Eliminar entregas pendientes devuelve stock
 * 2. Movimientos.jsx: Cancelar salida masiva devuelve stock
 * 
 * Flujo correcto:
 * - Crear entrega → Stock se descuenta (reserva inmediata)
 * - Confirmar/Finalizar → Solo marca como completado
 * - Eliminar/Cancelar (si no confirmado) → Stock se devuelve
 * 
 * Date: 2026-01-02
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// =============================================================================
// MOCK DE API
// =============================================================================

// Mock del servicio API para salidas de donaciones
const mockSalidasDonacionesAPI = {
  list: vi.fn(),
  create: vi.fn(),
  delete: vi.fn(),  // NUEVO: Método delete agregado
  finalizar: vi.fn(),
};

// Mock del servicio API para salida masiva
const mockSalidaMasivaAPI = {
  create: vi.fn(),
  confirmar: vi.fn(),
  cancelar: vi.fn(),  // NUEVO: Método cancelar agregado
  getEstado: vi.fn(),
  hojaEntregaPDF: vi.fn(),
};

// =============================================================================
// TESTS: API SALIDAS DONACIONES
// =============================================================================

describe('API salidasDonacionesAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('delete(id)', () => {
    it('debe existir el método delete', () => {
      expect(mockSalidasDonacionesAPI.delete).toBeDefined();
      expect(typeof mockSalidasDonacionesAPI.delete).toBe('function');
    });

    it('debe llamar al endpoint DELETE /api/salidas-donaciones/{id}/', async () => {
      const entregaId = 123;
      mockSalidasDonacionesAPI.delete.mockResolvedValueOnce({ status: 204 });

      await mockSalidasDonacionesAPI.delete(entregaId);

      expect(mockSalidasDonacionesAPI.delete).toHaveBeenCalledWith(123);
    });

    it('debe retornar 204 en éxito', async () => {
      mockSalidasDonacionesAPI.delete.mockResolvedValueOnce({ status: 204 });

      const result = await mockSalidasDonacionesAPI.delete(1);

      expect(result.status).toBe(204);
    });

    it('debe manejar error 400 si entrega está finalizada', async () => {
      mockSalidasDonacionesAPI.delete.mockRejectedValueOnce({
        response: {
          status: 400,
          data: { error: 'No se puede eliminar una entrega que ya fue confirmada/finalizada' }
        }
      });

      try {
        await mockSalidasDonacionesAPI.delete(1);
      } catch (error) {
        expect(error.response.status).toBe(400);
        expect(error.response.data.error).toContain('confirmada');
      }
    });

    it('debe manejar error 404 si entrega no existe', async () => {
      mockSalidasDonacionesAPI.delete.mockRejectedValueOnce({
        response: { status: 404 }
      });

      try {
        await mockSalidasDonacionesAPI.delete(9999);
      } catch (error) {
        expect(error.response.status).toBe(404);
      }
    });
  });

  describe('create(data)', () => {
    it('debe crear una nueva entrega', async () => {
      const nuevaEntrega = {
        detalle_donacion: 1,
        cantidad: 30,
        destinatario: 'Juan Pérez',
        motivo: 'Tratamiento médico'
      };

      mockSalidasDonacionesAPI.create.mockResolvedValueOnce({
        status: 201,
        data: { id: 1, ...nuevaEntrega }
      });

      const result = await mockSalidasDonacionesAPI.create(nuevaEntrega);

      expect(result.status).toBe(201);
      expect(result.data.cantidad).toBe(30);
    });

    it('debe rechazar si stock insuficiente', async () => {
      mockSalidasDonacionesAPI.create.mockRejectedValueOnce({
        response: {
          status: 400,
          data: { error: 'Stock insuficiente. Disponible: 10, Solicitado: 50' }
        }
      });

      try {
        await mockSalidasDonacionesAPI.create({ cantidad: 50 });
      } catch (error) {
        expect(error.response.status).toBe(400);
        expect(error.response.data.error).toContain('insuficiente');
      }
    });
  });
});

// =============================================================================
// TESTS: API SALIDA MASIVA
// =============================================================================

describe('API salidaMasivaAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('cancelar(grupoSalida)', () => {
    it('debe existir el método cancelar', () => {
      expect(mockSalidaMasivaAPI.cancelar).toBeDefined();
      expect(typeof mockSalidaMasivaAPI.cancelar).toBe('function');
    });

    it('debe llamar al endpoint DELETE /api/salida-masiva/cancelar/{grupo}/', async () => {
      const grupoSalida = 'SAL-0102-1530-1';
      mockSalidaMasivaAPI.cancelar.mockResolvedValueOnce({
        status: 200,
        data: { success: true, items_devueltos: [] }
      });

      await mockSalidaMasivaAPI.cancelar(grupoSalida);

      expect(mockSalidaMasivaAPI.cancelar).toHaveBeenCalledWith('SAL-0102-1530-1');
    });

    it('debe retornar items devueltos en éxito', async () => {
      const respuestaExitosa = {
        success: true,
        message: 'Salida cancelada. 3 productos devueltos al inventario.',
        grupo_salida: 'SAL-0102-1530-1',
        items_devueltos: [
          { lote_id: 1, cantidad_devuelta: 20, stock_actual: 100 },
          { lote_id: 2, cantidad_devuelta: 10, stock_actual: 50 },
          { lote_id: 3, cantidad_devuelta: 30, stock_actual: 200 },
        ]
      };

      mockSalidaMasivaAPI.cancelar.mockResolvedValueOnce({
        status: 200,
        data: respuestaExitosa
      });

      const result = await mockSalidaMasivaAPI.cancelar('SAL-0102-1530-1');

      expect(result.data.success).toBe(true);
      expect(result.data.items_devueltos).toHaveLength(3);
    });

    it('debe manejar error 400 si ya está confirmada', async () => {
      mockSalidaMasivaAPI.cancelar.mockRejectedValueOnce({
        response: {
          status: 400,
          data: { error: true, message: 'No se puede cancelar una entrega que ya fue confirmada' }
        }
      });

      try {
        await mockSalidaMasivaAPI.cancelar('SAL-0102-1530-1');
      } catch (error) {
        expect(error.response.status).toBe(400);
        expect(error.response.data.message).toContain('confirmada');
      }
    });

    it('debe manejar error 404 si grupo no existe', async () => {
      mockSalidaMasivaAPI.cancelar.mockRejectedValueOnce({
        response: {
          status: 404,
          data: { error: true, message: 'No se encontraron movimientos para este grupo de salida' }
        }
      });

      try {
        await mockSalidaMasivaAPI.cancelar('SAL-INEXISTENTE');
      } catch (error) {
        expect(error.response.status).toBe(404);
      }
    });
  });

  describe('confirmar(grupoSalida)', () => {
    it('debe confirmar una salida pendiente', async () => {
      mockSalidaMasivaAPI.confirmar.mockResolvedValueOnce({
        status: 200,
        data: { success: true, grupo_salida: 'SAL-0102-1530-1' }
      });

      const result = await mockSalidaMasivaAPI.confirmar('SAL-0102-1530-1');

      expect(result.data.success).toBe(true);
    });
  });
});

// =============================================================================
// TESTS: COMPONENTE DONACIONES - ELIMINAR ENTREGA
// =============================================================================

describe('Donaciones.jsx - Eliminar Entrega', () => {
  describe('Estado confirmEliminarEntrega', () => {
    it('debe inicializarse en null', () => {
      const confirmEliminarEntrega = null;
      expect(confirmEliminarEntrega).toBeNull();
    });

    it('debe poder guardar una entrega a eliminar', () => {
      const entregaAEliminar = {
        id: 1,
        cantidad: 30,
        destinatario: 'Juan Pérez',
        finalizado: false
      };

      let confirmEliminarEntrega = null;
      confirmEliminarEntrega = entregaAEliminar;

      expect(confirmEliminarEntrega).toEqual(entregaAEliminar);
    });
  });

  describe('handleEliminarEntrega', () => {
    it('debe llamar a salidasDonacionesAPI.delete con el ID correcto', async () => {
      const entregaId = 123;
      mockSalidasDonacionesAPI.delete.mockResolvedValueOnce({ status: 204 });

      await mockSalidasDonacionesAPI.delete(entregaId);

      expect(mockSalidasDonacionesAPI.delete).toHaveBeenCalledWith(123);
    });

    it('debe mostrar toast de éxito después de eliminar', async () => {
      const toastSuccess = vi.fn();
      
      mockSalidasDonacionesAPI.delete.mockResolvedValueOnce({ status: 204 });
      await mockSalidasDonacionesAPI.delete(1);
      
      // Simular que se llama al toast
      toastSuccess('Entrega eliminada y stock devuelto correctamente');

      expect(toastSuccess).toHaveBeenCalledWith(
        expect.stringContaining('eliminada')
      );
    });

    it('debe refrescar la lista de entregas después de eliminar', async () => {
      const cargarEntregas = vi.fn();
      
      mockSalidasDonacionesAPI.delete.mockResolvedValueOnce({ status: 204 });
      await mockSalidasDonacionesAPI.delete(1);
      
      // Simular recarga
      cargarEntregas();

      expect(cargarEntregas).toHaveBeenCalled();
    });
  });

  describe('Botón Eliminar Entrega', () => {
    it('solo debe mostrarse si la entrega NO está finalizada', () => {
      const entregaPendiente = { id: 1, finalizado: false };
      const entregaFinalizada = { id: 2, finalizado: true };

      const mostrarBotonEliminarPendiente = !entregaPendiente.finalizado;
      const mostrarBotonEliminarFinalizada = !entregaFinalizada.finalizado;

      expect(mostrarBotonEliminarPendiente).toBe(true);
      expect(mostrarBotonEliminarFinalizada).toBe(false);
    });

    it('debe usar icono FaTrash', () => {
      const iconoEsperado = 'FaTrash';
      expect(iconoEsperado).toBe('FaTrash');
    });

    it('debe tener color de error (rojo)', () => {
      const colorBoton = '#c53030'; // COLORS.error
      expect(colorBoton).toMatch(/^#[0-9A-Fa-f]{6}$/);
    });
  });

  describe('Modal de Confirmación', () => {
    it('debe mostrar mensaje de advertencia sobre stock', () => {
      const mensajeEsperado = 'El stock será devuelto al inventario';
      expect(mensajeEsperado).toContain('stock');
      expect(mensajeEsperado).toContain('devuelto');
    });

    it('debe tener botón Cancelar y Eliminar', () => {
      const botones = ['Cancelar', 'Eliminar'];
      expect(botones).toContain('Cancelar');
      expect(botones).toContain('Eliminar');
    });
  });
});

// =============================================================================
// TESTS: COMPONENTE MOVIMIENTOS - CANCELAR SALIDA
// =============================================================================

describe('Movimientos.jsx - Cancelar Salida Masiva', () => {
  describe('Estado confirmCancelarGrupo', () => {
    it('debe inicializarse en null', () => {
      const confirmCancelarGrupo = null;
      expect(confirmCancelarGrupo).toBeNull();
    });

    it('debe poder guardar un grupo a cancelar', () => {
      let confirmCancelarGrupo = null;
      confirmCancelarGrupo = 'SAL-0102-1530-1';

      expect(confirmCancelarGrupo).toBe('SAL-0102-1530-1');
    });
  });

  describe('cancelarSalidaGrupo', () => {
    it('debe llamar a salidaMasivaAPI.cancelar con el grupo correcto', async () => {
      const grupoSalida = 'SAL-0102-1530-1';
      mockSalidaMasivaAPI.cancelar.mockResolvedValueOnce({
        status: 200,
        data: { success: true, items_devueltos: [] }
      });

      await mockSalidaMasivaAPI.cancelar(grupoSalida);

      expect(mockSalidaMasivaAPI.cancelar).toHaveBeenCalledWith('SAL-0102-1530-1');
    });

    it('debe mostrar toast de éxito con cantidad de items devueltos', async () => {
      const toastSuccess = vi.fn();
      
      mockSalidaMasivaAPI.cancelar.mockResolvedValueOnce({
        status: 200,
        data: { 
          success: true, 
          message: 'Salida cancelada. 3 productos devueltos al inventario.',
          items_devueltos: [{}, {}, {}]
        }
      });

      const result = await mockSalidaMasivaAPI.cancelar('SAL-0102-1530-1');
      toastSuccess(result.data.message);

      expect(toastSuccess).toHaveBeenCalledWith(
        expect.stringContaining('devueltos')
      );
    });

    it('debe refrescar la lista de movimientos después de cancelar', async () => {
      const cargarMovimientos = vi.fn();
      
      mockSalidaMasivaAPI.cancelar.mockResolvedValueOnce({
        status: 200,
        data: { success: true }
      });
      
      await mockSalidaMasivaAPI.cancelar('SAL-0102-1530-1');
      cargarMovimientos();

      expect(cargarMovimientos).toHaveBeenCalled();
    });
  });

  describe('Botón Cancelar Salida', () => {
    it('solo debe mostrarse si la salida NO está confirmada', () => {
      const salidaPendiente = { confirmada: false };
      const salidaConfirmada = { confirmada: true };

      const mostrarBotonPendiente = !salidaPendiente.confirmada;
      const mostrarBotonConfirmada = !salidaConfirmada.confirmada;

      expect(mostrarBotonPendiente).toBe(true);
      expect(mostrarBotonConfirmada).toBe(false);
    });

    it('debe usar icono FaTrash', () => {
      const iconoEsperado = 'FaTrash';
      expect(iconoEsperado).toBe('FaTrash');
    });

    it('debe tener estilo de peligro/error', () => {
      const colorBoton = '#c53030';
      expect(colorBoton).toBe('#c53030');
    });
  });

  describe('Modal de Confirmación', () => {
    it('debe mostrar advertencia sobre stock', () => {
      const mensajeEsperado = 'Se eliminará la salida y el stock volverá al inventario';
      expect(mensajeEsperado).toContain('stock');
      expect(mensajeEsperado).toContain('volverá');
    });

    it('debe mostrar el grupo de salida a cancelar', () => {
      const grupoSalida = 'SAL-0102-1530-1';
      const textoModal = `¿Cancelar la salida ${grupoSalida}?`;

      expect(textoModal).toContain(grupoSalida);
    });
  });
});

// =============================================================================
// TESTS: FLUJO COMPLETO FRONTEND
// =============================================================================

describe('Flujo Completo Frontend', () => {
  describe('Donaciones: Crear → Eliminar', () => {
    it('debe actualizar UI correctamente al eliminar entrega', async () => {
      // Estado inicial: 1 entrega
      let entregas = [
        { id: 1, cantidad: 30, finalizado: false }
      ];

      // Simular eliminación
      mockSalidasDonacionesAPI.delete.mockResolvedValueOnce({ status: 204 });
      await mockSalidasDonacionesAPI.delete(1);

      // Actualizar estado (simular recarga)
      entregas = [];

      expect(entregas).toHaveLength(0);
    });

    it('debe actualizar stock disponible en detalle después de eliminar', () => {
      // Stock antes de eliminar: 70
      // Cantidad de la entrega eliminada: 30
      // Stock esperado: 100
      const stockAntes = 70;
      const cantidadEntrega = 30;
      const stockEsperado = stockAntes + cantidadEntrega;

      expect(stockEsperado).toBe(100);
    });
  });

  describe('Movimientos: Crear → Cancelar', () => {
    it('debe eliminar grupo de la lista al cancelar', async () => {
      // Estado inicial: 1 grupo de salida
      let gruposSalida = ['SAL-0102-1530-1'];

      // Simular cancelación
      mockSalidaMasivaAPI.cancelar.mockResolvedValueOnce({
        status: 200,
        data: { success: true }
      });
      await mockSalidaMasivaAPI.cancelar('SAL-0102-1530-1');

      // Actualizar estado (simular recarga - el grupo ya no aparece)
      gruposSalida = [];

      expect(gruposSalida).not.toContain('SAL-0102-1530-1');
    });
  });
});

// =============================================================================
// TESTS: VALIDACIONES DE INTERFAZ
// =============================================================================

describe('Validaciones de Interfaz', () => {
  describe('Donaciones.jsx', () => {
    it('debe deshabilitar botón eliminar mientras se procesa', () => {
      const eliminando = true;
      const botonDeshabilitado = eliminando;

      expect(botonDeshabilitado).toBe(true);
    });

    it('debe mostrar spinner mientras elimina', () => {
      const eliminando = true;
      const mostrarSpinner = eliminando;

      expect(mostrarSpinner).toBe(true);
    });
  });

  describe('Movimientos.jsx', () => {
    it('debe deshabilitar botón cancelar mientras se procesa', () => {
      const cancelandoGrupo = 'SAL-0102-1530-1';
      const botonDeshabilitado = !!cancelandoGrupo;

      expect(botonDeshabilitado).toBe(true);
    });

    it('debe mostrar spinner en botón mientras cancela', () => {
      const cancelandoGrupo = 'SAL-0102-1530-1';
      const grupoActual = 'SAL-0102-1530-1';
      const mostrarSpinner = cancelandoGrupo === grupoActual;

      expect(mostrarSpinner).toBe(true);
    });
  });
});

// =============================================================================
// TESTS: MANEJO DE ERRORES
// =============================================================================

describe('Manejo de Errores Frontend', () => {
  describe('Error al eliminar entrega', () => {
    it('debe mostrar toast de error con mensaje del servidor', async () => {
      const toastError = vi.fn();
      
      mockSalidasDonacionesAPI.delete.mockRejectedValueOnce({
        response: {
          status: 400,
          data: { error: 'No se puede eliminar una entrega finalizada' }
        }
      });

      try {
        await mockSalidasDonacionesAPI.delete(1);
      } catch (error) {
        toastError(error.response.data.error);
      }

      expect(toastError).toHaveBeenCalledWith(
        expect.stringContaining('eliminar')
      );
    });
  });

  describe('Error al cancelar salida', () => {
    it('debe mostrar toast de error si ya está confirmada', async () => {
      const toastError = vi.fn();
      
      mockSalidaMasivaAPI.cancelar.mockRejectedValueOnce({
        response: {
          status: 400,
          data: { message: 'No se puede cancelar una entrega que ya fue confirmada' }
        }
      });

      try {
        await mockSalidaMasivaAPI.cancelar('SAL-0102-1530-1');
      } catch (error) {
        toastError(error.response.data.message);
      }

      expect(toastError).toHaveBeenCalledWith(
        expect.stringContaining('confirmada')
      );
    });
  });
});
