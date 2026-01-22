/**
 * ISS-003 FIX: Tests de contratos DTO y flujos críticos
 * Verifica que los contratos frontend-backend se cumplan
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getStockProducto,
  normalizarProducto,
  formatStock,
  normalizarLote,
  normalizarRequisicion,
  normalizarDetalleRequisicion,
  normalizarMovimiento,
  validarContrato,
  validarRespuestaPaginada,
  ESTADOS_REQUISICION,
  TIPOS_MOVIMIENTO,
  CAMPOS_REQUERIDOS,
  // ISS-001 FIX: Importar métricas de contrato
  getContractMetrics,
  resetContractMetrics,
} from '../utils/dtoContracts';

describe('dtoContracts', () => {
  // ISS-001 FIX: Limpiar métricas antes de cada test
  beforeEach(() => {
    resetContractMetrics();
  });

  describe('getStockProducto', () => {
    it('obtiene stock_actual como campo canónico', () => {
      const producto = { id: 1, stock_actual: 100 };
      expect(getStockProducto(producto)).toBe(100);
    });

    it('usa campos legacy como fallback', () => {
      const producto = { id: 1, stock_total: 50 };
      expect(getStockProducto(producto, { logWarnings: false })).toBe(50);
    });

    it('parsea strings numéricos', () => {
      const producto = { id: 1, stock_actual: '75' };
      expect(getStockProducto(producto, { logWarnings: false })).toBe(75);
    });

    it('retorna 0 para producto sin stock', () => {
      const producto = { id: 1, nombre: 'Test' };
      expect(getStockProducto(producto)).toBe(0);
    });

    it('retorna 0 para producto null', () => {
      expect(getStockProducto(null)).toBe(0);
      expect(getStockProducto(undefined)).toBe(0);
    });

    it('lanza error en modo strict sin stock', () => {
      const producto = { id: 1 };
      // ISS-003 FIX: En modo strict, lanza error si falta el campo canónico
      expect(() => getStockProducto(producto, { strict: true })).toThrow('[CONTRACT ERROR]');
    });

    it('prioriza stock_actual sobre campos legacy', () => {
      const producto = { 
        id: 1, 
        stock_actual: 100,
        stock_total: 200,
        inventario: 300 
      };
      expect(getStockProducto(producto)).toBe(100);
    });

    it('maneja NaN correctamente', () => {
      const producto = { id: 1, stock_actual: NaN, stock_total: 50 };
      expect(getStockProducto(producto, { logWarnings: false })).toBe(50);
    });
  });

  describe('normalizarProducto', () => {
    it('normaliza producto completo', () => {
      const raw = {
        id: 1,
        clave: 'MED-001',
        nombre: 'Paracetamol',
        descripcion: 'Analgésico',
        unidad_medida: 'pieza',
        categoria: 'medicamento',
        stock_minimo: 10,
        stock_actual: 50,
        requiere_receta: true,
        es_controlado: false,
        activo: true,
      };

      const resultado = normalizarProducto(raw);

      expect(resultado.id).toBe(1);
      expect(resultado.clave).toBe('MED-001');
      expect(resultado.nombre).toBe('Paracetamol');
      expect(resultado.unidad_medida).toBe('PIEZA'); // uppercase
      expect(resultado.stock_actual).toBe(50);
      expect(resultado.requiere_receta).toBe(true);
    });

    it('usa valores por defecto para campos faltantes', () => {
      const raw = { id: 2, nombre: 'Test' };
      const resultado = normalizarProducto(raw);

      expect(resultado.clave).toBe('');
      expect(resultado.unidad_medida).toBe('PIEZA');
      expect(resultado.categoria).toBe('medicamento');
      expect(resultado.stock_minimo).toBe(0);
      expect(resultado.activo).toBe(true);
    });

    it('mapea codigo_barras a clave', () => {
      const raw = { id: 3, codigo_barras: 'COD-123', nombre: 'Test' };
      const resultado = normalizarProducto(raw);
      expect(resultado.clave).toBe('COD-123');
    });

    it('lanza error para input inválido', () => {
      expect(() => normalizarProducto(null)).toThrow();
      expect(() => normalizarProducto('string')).toThrow();
    });
  });

  describe('formatStock', () => {
    it('formatea stock con separador de miles', () => {
      const producto = { stock_actual: 1234567 };
      const formatted = formatStock(producto);
      expect(formatted).toContain('1');
      expect(formatted.length).toBeGreaterThan(7); // tiene separadores
    });

    it('maneja stock 0', () => {
      const producto = { stock_actual: 0 };
      expect(formatStock(producto)).toBe('0');
    });
  });

  describe('normalizarLote', () => {
    it('normaliza lote completo', () => {
      const raw = {
        id: 1,
        producto_id: 10,
        numero_lote: 'L2024-001',
        cantidad_inicial: 100,
        cantidad_actual: 75,
        fecha_caducidad: '2025-12-31',
        activo: true,
      };

      const resultado = normalizarLote(raw);

      expect(resultado.id).toBe(1);
      expect(resultado.numero_lote).toBe('L2024-001');
      expect(resultado.cantidad_inicial).toBe(100);
      expect(resultado.cantidad_actual).toBe(75);
    });

    it('retorna null para input null', () => {
      expect(normalizarLote(null)).toBeNull();
    });

    it('calcula estado vencido', () => {
      const raw = {
        id: 1,
        numero_lote: 'L-OLD',
        cantidad_actual: 10,
        fecha_caducidad: '2020-01-01',
        activo: true,
      };
      const resultado = normalizarLote(raw);
      expect(resultado.estado).toBe('vencido');
    });

    it('calcula estado agotado', () => {
      const raw = {
        id: 1,
        numero_lote: 'L-EMPTY',
        cantidad_actual: 0,
        activo: true,
      };
      const resultado = normalizarLote(raw);
      expect(resultado.estado).toBe('agotado');
    });
  });

  describe('normalizarRequisicion', () => {
    it('normaliza requisición completa', () => {
      const raw = {
        id: 1,
        folio: 'REQ-2024-001',
        estado: 'pendiente',
        fecha_creacion: '2024-01-15T10:00:00Z',
        solicitante: { id: 5, username: 'usuario1' },
        detalles: [
          { id: 1, producto_id: 10, cantidad_solicitada: 5 }
        ],
      };

      const resultado = normalizarRequisicion(raw);

      expect(resultado.id).toBe(1);
      expect(resultado.folio).toBe('REQ-2024-001');
      expect(resultado.estado).toBe('pendiente');
      expect(resultado.solicitante_id).toBe(5);
      expect(resultado.solicitante_nombre).toBe('usuario1');
      expect(resultado.detalles).toHaveLength(1);
    });

    it('usa estado borrador por defecto', () => {
      const raw = { id: 2, folio: 'REQ-002' };
      const resultado = normalizarRequisicion(raw);
      expect(resultado.estado).toBe(ESTADOS_REQUISICION.BORRADOR);
    });

    it('retorna null para input null', () => {
      expect(normalizarRequisicion(null)).toBeNull();
    });
  });

  describe('normalizarDetalleRequisicion', () => {
    it('normaliza detalle con producto anidado', () => {
      const raw = {
        id: 1,
        producto: { id: 10, clave: 'MED-001', nombre: 'Paracetamol' },
        cantidad_solicitada: 50,
        cantidad_surtida: 25,
      };

      const resultado = normalizarDetalleRequisicion(raw);

      expect(resultado.producto_id).toBe(10);
      expect(resultado.producto_clave).toBe('MED-001');
      expect(resultado.cantidad_solicitada).toBe(50);
      expect(resultado.cantidad_surtida).toBe(25);
    });

    it('maneja campos planos', () => {
      const raw = {
        id: 2,
        producto_id: 15,
        producto_clave: 'INS-002',
        cantidad_solicitada: '100',
      };

      const resultado = normalizarDetalleRequisicion(raw);

      expect(resultado.producto_id).toBe(15);
      expect(resultado.cantidad_solicitada).toBe(100);
    });
  });

  describe('normalizarMovimiento', () => {
    it('normaliza movimiento completo', () => {
      const raw = {
        id: 1,
        tipo: 'entrada',
        cantidad: 100,
        lote_id: 5,
        producto_id: 10,
        fecha: '2024-01-15T10:00:00Z',
        referencia: 'FAC-001',
      };

      const resultado = normalizarMovimiento(raw);

      expect(resultado.tipo).toBe('entrada');
      expect(resultado.cantidad).toBe(100);
      expect(resultado.lote_id).toBe(5);
      expect(resultado.referencia).toBe('FAC-001');
    });

    it('usa tipo entrada por defecto', () => {
      const raw = { id: 2, cantidad: 50 };
      const resultado = normalizarMovimiento(raw);
      expect(resultado.tipo).toBe(TIPOS_MOVIMIENTO.ENTRADA);
    });
  });

  describe('validarContrato', () => {
    it('valida objeto con campos requeridos', () => {
      const obj = { id: 1, clave: 'TEST', nombre: 'Test' };
      const { valido, errores } = validarContrato(obj, CAMPOS_REQUERIDOS.producto, 'Producto');
      expect(valido).toBe(true);
      expect(errores).toHaveLength(0);
    });

    it('detecta campos faltantes', () => {
      const obj = { id: 1 };
      const { valido, errores } = validarContrato(obj, CAMPOS_REQUERIDOS.producto, 'Producto');
      expect(valido).toBe(false);
      expect(errores).toContain("Producto: campo 'clave' es requerido");
      expect(errores).toContain("Producto: campo 'nombre' es requerido");
    });

    it('rechaza objeto null', () => {
      const { valido, errores } = validarContrato(null, ['id'], 'Test');
      expect(valido).toBe(false);
      expect(errores).toContain('Test debe ser un objeto');
    });
  });

  describe('validarRespuestaPaginada', () => {
    it('valida respuesta DRF paginada', () => {
      const response = {
        results: [{ id: 1 }, { id: 2 }],
        count: 10,
        next: 'http://api/?page=2',
        previous: null,
      };

      const resultado = validarRespuestaPaginada(response);

      expect(resultado.valido).toBe(true);
      expect(resultado.data).toHaveLength(2);
      expect(resultado.count).toBe(10);
    });

    it('valida array directo', () => {
      const response = [{ id: 1 }, { id: 2 }, { id: 3 }];

      const resultado = validarRespuestaPaginada(response);

      expect(resultado.valido).toBe(true);
      expect(resultado.data).toHaveLength(3);
      expect(resultado.count).toBe(3);
    });

    it('valida respuesta con data array', () => {
      const response = { data: [{ id: 1 }], total: 5 };

      const resultado = validarRespuestaPaginada(response);

      expect(resultado.valido).toBe(true);
      expect(resultado.count).toBe(5);
    });

    it('rechaza formato desconocido', () => {
      const response = { algo: 'otro' };

      const resultado = validarRespuestaPaginada(response);

      expect(resultado.valido).toBe(false);
      expect(resultado.error).toBeDefined();
    });
  });

  describe('Constantes de estado', () => {
    it('ESTADOS_REQUISICION tiene todos los estados', () => {
      expect(ESTADOS_REQUISICION.BORRADOR).toBe('borrador');
      expect(ESTADOS_REQUISICION.PENDIENTE).toBe('pendiente');
      expect(ESTADOS_REQUISICION.APROBADA).toBe('aprobada');
      expect(ESTADOS_REQUISICION.SURTIDA).toBe('surtida');
      expect(ESTADOS_REQUISICION.RECHAZADA).toBe('rechazada');
      expect(ESTADOS_REQUISICION.CANCELADA).toBe('cancelada');
    });

    it('TIPOS_MOVIMIENTO tiene todos los tipos', () => {
      expect(TIPOS_MOVIMIENTO.ENTRADA).toBe('entrada');
      expect(TIPOS_MOVIMIENTO.SALIDA).toBe('salida');
      expect(TIPOS_MOVIMIENTO.AJUSTE).toBe('ajuste');
      expect(TIPOS_MOVIMIENTO.TRANSFERENCIA).toBe('transferencia');
    });
  });

  // ISS-001 FIX: Tests de métricas de contrato
  describe('Contract Metrics - ISS-001', () => {
    it('registra uso de campos legacy', () => {
      // Usar campo legacy debería registrar violación
      const producto = { id: 1, stock_total: 50 };
      getStockProducto(producto, { logWarnings: false, endpoint: 'test' });

      const metrics = getContractMetrics();
      expect(metrics.totalViolations).toBeGreaterThan(0);
      expect(Object.keys(metrics.legacyFieldUsage).length).toBeGreaterThan(0);
    });

    it('registra violaciones de paginación', () => {
      // Array plano debería registrar discrepancia
      validarRespuestaPaginada([{ id: 1 }], { endpoint: 'test' });

      const metrics = getContractMetrics();
      expect(metrics.paginationDiscrepancies).toBeGreaterThan(0);
    });

    it('resetea métricas correctamente', () => {
      // Generar algunas violaciones
      getStockProducto({ id: 1, stock_total: 10 }, { logWarnings: false });
      validarRespuestaPaginada([{ id: 1 }], { endpoint: 'test' });

      resetContractMetrics();
      const metrics = getContractMetrics();

      expect(metrics.totalViolations).toBe(0);
      expect(metrics.paginationDiscrepancies).toBe(0);
    });

    it('no registra violación cuando se usa campo canónico', () => {
      resetContractMetrics();
      
      // Usar campo canónico NO debe registrar violación
      const producto = { id: 1, stock_actual: 100 };
      getStockProducto(producto, { logWarnings: false });

      const metrics = getContractMetrics();
      expect(metrics.totalViolations).toBe(0);
    });
  });

  // ISS-003 FIX: Tests de modo estricto de paginación
  describe('validarRespuestaPaginada - modo estricto ISS-003', () => {
    it('rechaza array plano en modo estricto', () => {
      const response = [{ id: 1 }, { id: 2 }];
      const resultado = validarRespuestaPaginada(response, { strict: true, endpoint: 'test' });

      expect(resultado.valido).toBe(false);
      expect(resultado.format).toBe('array_plain');
    });

    it('rechaza formato {data} en modo estricto', () => {
      const response = { data: [{ id: 1 }], total: 5 };
      const resultado = validarRespuestaPaginada(response, { strict: true, endpoint: 'test' });

      expect(resultado.valido).toBe(false);
      expect(resultado.format).toBe('data_wrapper');
    });

    it('acepta formato canónico DRF en modo estricto', () => {
      const response = { results: [{ id: 1 }], count: 1 };
      const resultado = validarRespuestaPaginada(response, { strict: true, endpoint: 'test' });

      expect(resultado.valido).toBe(true);
      expect(resultado.format).toBe('canonical');
    });

    it('incluye warning para formatos no canónicos', () => {
      const response = [{ id: 1 }];
      const resultado = validarRespuestaPaginada(response, { strict: false });

      expect(resultado.valido).toBe(true);
      expect(resultado.warning).toBeDefined();
    });
  });

  // =========================================================================
  // ISS-003 FIX (audit32): Tests de modo estricto de producción
  // =========================================================================
  describe('Modo estricto producción - ISS-003 audit32', () => {
    it('getStockProducto rechaza campos legacy en modo estricto', () => {
      const producto = { id: 1, stock_total: 50 }; // Campo legacy
      
      // En modo estricto, debe lanzar error por usar campo legacy
      expect(() => getStockProducto(producto, { 
        strict: true, 
        endpoint: 'productos' 
      })).toThrow('CONTRACT ERROR');
    });

    it('getStockProducto rechaza falta de campo canónico en modo estricto', () => {
      const producto = { id: 1, nombre: 'Test' }; // Sin stock_actual
      
      expect(() => getStockProducto(producto, { 
        strict: true, 
        endpoint: 'productos' 
      })).toThrow('falta campo canónico');
    });

    it('getStockProducto acepta campo canónico en modo estricto', () => {
      const producto = { id: 1, stock_actual: 100 };
      
      // No debe lanzar error
      const stock = getStockProducto(producto, { strict: true, endpoint: 'productos' });
      expect(stock).toBe(100);
    });

    it('registra violación como crítica cuando falta campo canónico', () => {
      resetContractMetrics();
      
      const producto = { id: 1, nombre: 'Test' };
      
      // Capturamos el error pero verificamos las métricas
      try {
        getStockProducto(producto, { strict: true, endpoint: 'productos' });
      } catch (e) {
        // Esperado
      }
      
      const metrics = getContractMetrics();
      expect(metrics.criticalViolations).toBeGreaterThan(0);
    });

    it('validarRespuestaPaginada rechaza formato no canónico en strict', () => {
      const response = { data: [{ id: 1 }], total: 5 };
      
      const resultado = validarRespuestaPaginada(response, { 
        strict: true, 
        endpoint: 'productos' 
      });
      
      expect(resultado.valido).toBe(false);
      expect(resultado.error).toContain('no canónico');
    });

    it('getStockProducto rechaza stock como string en modo estricto', () => {
      const producto = { id: 1, stock_actual: '100' }; // String en lugar de number
      
      expect(() => getStockProducto(producto, { 
        strict: true, 
        endpoint: 'productos' 
      })).toThrow('CONTRACT ERROR');
    });
  });

  // =========================================================================
  // ISS-003 FIX (audit32): Tests de bloqueo por violaciones críticas
  // =========================================================================
  describe('Bloqueo de contrato - ISS-003 audit32', () => {
    beforeEach(() => {
      resetContractMetrics();
    });

    it('contractMetrics expone métodos de bloqueo', () => {
      const metrics = getContractMetrics();
      expect(typeof metrics.isBlocked).toBe('function');
      expect(typeof metrics.block).toBe('function');
      expect(typeof metrics.unblock).toBe('function');
    });

    it('contractMetrics registra violaciones críticas', () => {
      // Simulamos una violación crítica
      const producto = { id: 1 }; // Sin stock
      
      try {
        getStockProducto(producto, { strict: true, endpoint: 'productos' });
      } catch (e) {
        // Esperado
      }
      
      const metrics = getContractMetrics();
      expect(metrics.criticalViolations).toBeGreaterThanOrEqual(1);
    });

    it('contractMetrics puede ser bloqueado y desbloqueado', () => {
      const metrics = getContractMetrics();
      
      expect(metrics.isBlocked()).toBe(false);
      
      metrics.block('test-reason');
      expect(metrics.isBlocked()).toBe(true);
      
      metrics.unblock();
      expect(metrics.isBlocked()).toBe(false);
    });
  });
});
