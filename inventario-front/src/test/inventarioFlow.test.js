/**
 * ISS-003 FIX: Tests de flujos de inventario
 * Verifica operaciones de entrada, salida, ajuste y transferencia
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('Flujos de Inventario', () => {
  describe('Validación de Movimientos', () => {
    const validarMovimiento = (movimiento) => {
      const errores = [];

      if (!movimiento.tipo) {
        errores.push('Tipo de movimiento es requerido');
      }

      if (!movimiento.cantidad || movimiento.cantidad <= 0) {
        errores.push('Cantidad debe ser mayor a 0');
      }

      if (!Number.isInteger(movimiento.cantidad)) {
        errores.push('Cantidad debe ser un número entero');
      }

      if (!movimiento.lote_id && !movimiento.producto_id) {
        errores.push('Debe especificar lote o producto');
      }

      if (movimiento.tipo === 'salida' && !movimiento.lote_id) {
        errores.push('Las salidas requieren especificar lote');
      }

      return { valido: errores.length === 0, errores };
    };

    it('valida movimiento de entrada correcto', () => {
      const mov = { tipo: 'entrada', cantidad: 100, lote_id: 1 };
      const { valido } = validarMovimiento(mov);
      expect(valido).toBe(true);
    });

    it('rechaza cantidad negativa', () => {
      const mov = { tipo: 'entrada', cantidad: -50, lote_id: 1 };
      const { valido, errores } = validarMovimiento(mov);
      expect(valido).toBe(false);
      expect(errores).toContain('Cantidad debe ser mayor a 0');
    });

    it('rechaza cantidad decimal', () => {
      const mov = { tipo: 'entrada', cantidad: 10.5, lote_id: 1 };
      const { valido, errores } = validarMovimiento(mov);
      expect(valido).toBe(false);
      expect(errores).toContain('Cantidad debe ser un número entero');
    });

    it('requiere lote para salidas', () => {
      const mov = { tipo: 'salida', cantidad: 10, producto_id: 1 };
      const { valido, errores } = validarMovimiento(mov);
      expect(valido).toBe(false);
      expect(errores).toContain('Las salidas requieren especificar lote');
    });
  });

  describe('Validación de Stock', () => {
    const verificarStockSuficiente = (lote, cantidadSolicitada) => {
      if (!lote || lote.cantidad_actual === undefined) {
        return { suficiente: false, error: 'Lote inválido' };
      }

      if (cantidadSolicitada > lote.cantidad_actual) {
        return {
          suficiente: false,
          error: `Stock insuficiente. Disponible: ${lote.cantidad_actual}, Solicitado: ${cantidadSolicitada}`,
          disponible: lote.cantidad_actual,
          faltante: cantidadSolicitada - lote.cantidad_actual,
        };
      }

      return { suficiente: true, disponible: lote.cantidad_actual };
    };

    it('permite salida con stock suficiente', () => {
      const lote = { id: 1, cantidad_actual: 100 };
      const result = verificarStockSuficiente(lote, 50);
      expect(result.suficiente).toBe(true);
    });

    it('rechaza salida con stock insuficiente', () => {
      const lote = { id: 1, cantidad_actual: 30 };
      const result = verificarStockSuficiente(lote, 50);
      expect(result.suficiente).toBe(false);
      expect(result.faltante).toBe(20);
    });

    it('rechaza lote inválido', () => {
      const result = verificarStockSuficiente(null, 10);
      expect(result.suficiente).toBe(false);
      expect(result.error).toBe('Lote inválido');
    });

    it('permite salida exacta del stock disponible', () => {
      const lote = { id: 1, cantidad_actual: 50 };
      const result = verificarStockSuficiente(lote, 50);
      expect(result.suficiente).toBe(true);
    });
  });

  describe('Validación de Lotes', () => {
    const validarLote = (lote) => {
      const errores = [];
      const hoy = new Date();

      if (!lote.numero_lote || lote.numero_lote.trim().length < 3) {
        errores.push('Número de lote debe tener al menos 3 caracteres');
      }

      if (!lote.cantidad_inicial || lote.cantidad_inicial <= 0) {
        errores.push('Cantidad inicial debe ser mayor a 0');
      }

      if (lote.fecha_caducidad) {
        const caducidad = new Date(lote.fecha_caducidad);
        if (caducidad <= hoy) {
          errores.push('Fecha de caducidad debe ser futura');
        }
      }

      if (lote.fecha_fabricacion && lote.fecha_caducidad) {
        const recepcion = new Date(lote.fecha_fabricacion);
        const caducidad = new Date(lote.fecha_caducidad);
        if (recepcion >= caducidad) {
          errores.push('Fecha de entrega debe ser anterior a caducidad');
        }
      }

      return { valido: errores.length === 0, errores };
    };

    it('valida lote correcto', () => {
      const lote = {
        numero_lote: 'L2025-001',
        cantidad_inicial: 100,
        fecha_caducidad: '2026-12-31',
        fecha_fabricacion: '2024-01-01',
      };
      const { valido } = validarLote(lote);
      expect(valido).toBe(true);
    });

    it('rechaza lote con número corto', () => {
      const lote = { numero_lote: 'L1', cantidad_inicial: 100 };
      const { valido, errores } = validarLote(lote);
      expect(valido).toBe(false);
      expect(errores).toContain('Número de lote debe tener al menos 3 caracteres');
    });

    it('rechaza lote ya vencido', () => {
      const lote = {
        numero_lote: 'L-VIEJO',
        cantidad_inicial: 100,
        fecha_caducidad: '2020-01-01',
      };
      const { valido, errores } = validarLote(lote);
      expect(valido).toBe(false);
      expect(errores).toContain('Fecha de caducidad debe ser futura');
    });

    it('rechaza fechas inconsistentes', () => {
      const lote = {
        numero_lote: 'L-BAD',
        cantidad_inicial: 100,
        fecha_fabricacion: '2025-01-01',
        fecha_caducidad: '2024-01-01',
      };
      const { valido, errores } = validarLote(lote);
      expect(valido).toBe(false);
      expect(errores).toContain('Fecha de entrega debe ser anterior a caducidad');
    });
  });

  describe('Cálculo de Nivel de Stock', () => {
    const calcularNivelStock = (stockActual, stockMinimo) => {
      if (stockActual <= 0) return 'sin_stock';
      
      if (stockMinimo <= 0) {
        // Sin mínimo definido, usar umbrales absolutos
        if (stockActual < 25) return 'bajo';
        if (stockActual < 100) return 'normal';
        return 'alto';
      }

      const ratio = stockActual / stockMinimo;
      if (ratio < 0.5) return 'critico';
      if (ratio < 1) return 'bajo';
      if (ratio <= 2) return 'normal';
      return 'alto';
    };

    it('detecta sin stock', () => {
      expect(calcularNivelStock(0, 10)).toBe('sin_stock');
      expect(calcularNivelStock(-5, 10)).toBe('sin_stock');
    });

    it('detecta nivel crítico', () => {
      expect(calcularNivelStock(4, 10)).toBe('critico'); // 40% del mínimo
    });

    it('detecta nivel bajo', () => {
      expect(calcularNivelStock(7, 10)).toBe('bajo'); // 70% del mínimo
    });

    it('detecta nivel normal', () => {
      expect(calcularNivelStock(15, 10)).toBe('normal'); // 150% del mínimo
    });

    it('detecta nivel alto', () => {
      expect(calcularNivelStock(30, 10)).toBe('alto'); // 300% del mínimo
    });

    it('maneja stock sin mínimo definido', () => {
      expect(calcularNivelStock(10, 0)).toBe('bajo');
      expect(calcularNivelStock(50, 0)).toBe('normal');
      expect(calcularNivelStock(200, 0)).toBe('alto');
    });
  });

  describe('Transferencias entre Centros', () => {
    const validarTransferencia = (transferencia) => {
      const errores = [];

      if (!transferencia.centro_origen_id) {
        errores.push('Centro de origen es requerido');
      }

      if (!transferencia.centro_destino_id) {
        errores.push('Centro de destino es requerido');
      }

      if (transferencia.centro_origen_id === transferencia.centro_destino_id) {
        errores.push('Centro de origen y destino deben ser diferentes');
      }

      if (!transferencia.detalles || transferencia.detalles.length === 0) {
        errores.push('Debe incluir al menos un producto a transferir');
      }

      if (transferencia.detalles) {
        transferencia.detalles.forEach((detalle, idx) => {
          if (!detalle.lote_id) {
            errores.push(`Detalle ${idx + 1}: Lote es requerido`);
          }
          if (!detalle.cantidad || detalle.cantidad <= 0) {
            errores.push(`Detalle ${idx + 1}: Cantidad debe ser mayor a 0`);
          }
        });
      }

      return { valido: errores.length === 0, errores };
    };

    it('valida transferencia correcta', () => {
      const transfer = {
        centro_origen_id: 1,
        centro_destino_id: 2,
        detalles: [
          { lote_id: 10, cantidad: 50 },
          { lote_id: 11, cantidad: 30 },
        ],
      };
      const { valido } = validarTransferencia(transfer);
      expect(valido).toBe(true);
    });

    it('rechaza transferencia al mismo centro', () => {
      const transfer = {
        centro_origen_id: 1,
        centro_destino_id: 1,
        detalles: [{ lote_id: 10, cantidad: 50 }],
      };
      const { valido, errores } = validarTransferencia(transfer);
      expect(valido).toBe(false);
      expect(errores).toContain('Centro de origen y destino deben ser diferentes');
    });

    it('rechaza transferencia sin detalles', () => {
      const transfer = {
        centro_origen_id: 1,
        centro_destino_id: 2,
        detalles: [],
      };
      const { valido, errores } = validarTransferencia(transfer);
      expect(valido).toBe(false);
      expect(errores).toContain('Debe incluir al menos un producto a transferir');
    });
  });

  describe('Ajustes de Inventario', () => {
    const validarAjuste = (ajuste) => {
      const errores = [];
      const motivosValidos = ['inventario_fisico', 'merma', 'robo', 'error_sistema', 'otro'];

      if (!ajuste.motivo || !motivosValidos.includes(ajuste.motivo)) {
        errores.push('Motivo de ajuste no válido');
      }

      if (!ajuste.justificacion || ajuste.justificacion.trim().length < 10) {
        errores.push('Justificación debe tener al menos 10 caracteres');
      }

      if (ajuste.cantidad === 0) {
        errores.push('Cantidad de ajuste no puede ser 0');
      }

      if (ajuste.diferencia !== undefined) {
        // Verificar que la diferencia sea la correcta
        const diferenciaCalculada = ajuste.cantidad_nueva - ajuste.cantidad_anterior;
        if (diferenciaCalculada !== ajuste.diferencia) {
          errores.push('Diferencia no coincide con cantidades');
        }
      }

      return { valido: errores.length === 0, errores };
    };

    it('valida ajuste correcto', () => {
      const ajuste = {
        lote_id: 1,
        motivo: 'inventario_fisico',
        justificacion: 'Ajuste por conteo físico mensual',
        cantidad: -5,
        cantidad_anterior: 100,
        cantidad_nueva: 95,
        diferencia: -5,
      };
      const { valido } = validarAjuste(ajuste);
      expect(valido).toBe(true);
    });

    it('rechaza motivo inválido', () => {
      const ajuste = {
        motivo: 'motivo_inventado',
        justificacion: 'Justificación válida aquí',
        cantidad: -5,
      };
      const { valido, errores } = validarAjuste(ajuste);
      expect(valido).toBe(false);
      expect(errores).toContain('Motivo de ajuste no válido');
    });

    it('rechaza justificación corta', () => {
      const ajuste = {
        motivo: 'merma',
        justificacion: 'Corta',
        cantidad: -5,
      };
      const { valido, errores } = validarAjuste(ajuste);
      expect(valido).toBe(false);
      expect(errores).toContain('Justificación debe tener al menos 10 caracteres');
    });

    it('rechaza ajuste de cantidad 0', () => {
      const ajuste = {
        motivo: 'inventario_fisico',
        justificacion: 'Verificación sin cambios necesarios',
        cantidad: 0,
      };
      const { valido, errores } = validarAjuste(ajuste);
      expect(valido).toBe(false);
      expect(errores).toContain('Cantidad de ajuste no puede ser 0');
    });
  });
});
