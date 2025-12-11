/**
 * ISS-006 FIX: Tests de flujos críticos y validadores
 * Cubre: validación de productos, requisiciones, stock y transiciones
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  validarProductoCreacion,
  validarProductoEdicion,
  validarRequisicionEnvio,
  validarTransicionRequisicion,
  validarSurtidoRequisicion,
  validarLoteCreacion,
  getValidationMetrics,
  resetValidationMetrics,
  PRODUCTO_RULES,
  ESTADOS_FLUJO_V2,
  ACCIONES_POR_ROL,
} from '../utils/flowValidators';

// Mock de api.js para esTransicionValidaV2
vi.mock('../services/api', () => ({
  esTransicionValida: vi.fn((actual, nuevo) => {
    const transiciones = {
      borrador: ['enviada', 'pendiente_admin', 'cancelada'],
      pendiente_admin: ['autorizada', 'rechazada', 'devuelta'],
      enviada: ['autorizada', 'rechazada', 'devuelta'],
      autorizada: ['en_surtido', 'cancelada'],
      en_surtido: ['surtida', 'cancelada'],
      surtida: ['entregada'],
    };
    return transiciones[actual]?.includes(nuevo) || false;
  }),
  TRANSICIONES_V2: {},
}));

describe('flowValidators - ISS-006', () => {
  beforeEach(() => {
    resetValidationMetrics();
  });

  // =========================================================================
  // VALIDACIÓN DE PRODUCTOS
  // =========================================================================
  describe('validarProductoCreacion', () => {
    it('valida producto completo correctamente', () => {
      const producto = {
        clave: 'MED-001',
        nombre: 'Paracetamol 500mg',
        unidad_medida: 'TABLETA',
        categoria: 'medicamento',
        stock_minimo: 10,
        descripcion: 'Analgésico',
        presentacion: 'Tabletas',
      };

      const result = validarProductoCreacion(producto);

      expect(result.valido).toBe(true);
      expect(result.errores).toEqual({});
    });

    it('rechaza producto sin clave', () => {
      const producto = {
        nombre: 'Paracetamol',
        unidad_medida: 'TABLETA',
        categoria: 'medicamento',
        stock_minimo: 10,
      };

      const result = validarProductoCreacion(producto);

      expect(result.valido).toBe(false);
      expect(result.errores.clave).toBeTruthy();
    });

    it('rechaza clave con caracteres inválidos', () => {
      const producto = {
        clave: 'MED@001!',
        nombre: 'Paracetamol',
        unidad_medida: 'TABLETA',
        categoria: 'medicamento',
        stock_minimo: 10,
      };

      const result = validarProductoCreacion(producto);

      expect(result.valido).toBe(false);
      expect(result.errores.clave).toContain('letras, números');
    });

    it('rechaza clave muy corta', () => {
      const producto = {
        clave: 'AB',
        nombre: 'Paracetamol',
        unidad_medida: 'TABLETA',
        categoria: 'medicamento',
        stock_minimo: 10,
      };

      const result = validarProductoCreacion(producto);

      expect(result.valido).toBe(false);
      expect(result.errores.clave).toContain('al menos 3');
    });

    it('rechaza producto sin nombre', () => {
      const producto = {
        clave: 'MED-001',
        unidad_medida: 'TABLETA',
        categoria: 'medicamento',
        stock_minimo: 10,
      };

      const result = validarProductoCreacion(producto);

      expect(result.valido).toBe(false);
      expect(result.errores.nombre).toBeTruthy();
    });

    it('rechaza stock_minimo negativo', () => {
      const producto = {
        clave: 'MED-001',
        nombre: 'Paracetamol',
        unidad_medida: 'TABLETA',
        categoria: 'medicamento',
        stock_minimo: -5,
      };

      const result = validarProductoCreacion(producto);

      expect(result.valido).toBe(false);
      expect(result.errores.stock_minimo).toBeTruthy();
    });

    it('rechaza categoría inválida', () => {
      const producto = {
        clave: 'MED-001',
        nombre: 'Paracetamol',
        unidad_medida: 'TABLETA',
        categoria: 'categoria_inexistente',
        stock_minimo: 10,
      };

      const result = validarProductoCreacion(producto);

      expect(result.valido).toBe(false);
      expect(result.errores.categoria).toContain('no válida');
    });

    it('valida contra catálogo de unidades si se proporciona', () => {
      const producto = {
        clave: 'MED-001',
        nombre: 'Paracetamol',
        unidad_medida: 'UNIDAD_INVENTADA',
        categoria: 'medicamento',
        stock_minimo: 10,
      };

      const result = validarProductoCreacion(producto, {
        unidadesValidas: ['TABLETA', 'CAJA', 'FRASCO'],
      });

      expect(result.valido).toBe(false);
      expect(result.errores.unidad_medida).toContain('no válida');
    });

    it('genera warnings para campos opcionales faltantes', () => {
      const producto = {
        clave: 'MED-001',
        nombre: 'Paracetamol',
        unidad_medida: 'TABLETA',
        categoria: 'medicamento',
        stock_minimo: 10,
      };

      const result = validarProductoCreacion(producto);

      expect(result.valido).toBe(true);
      expect(result.warnings.length).toBeGreaterThan(0);
      expect(result.warnings.some(w => w.includes('descripción'))).toBe(true);
    });
  });

  describe('validarProductoEdicion', () => {
    const productoOriginal = {
      id: 1,
      clave: 'MED-001',
      nombre: 'Paracetamol 500mg',
      unidad_medida: 'TABLETA',
      categoria: 'medicamento',
      stock_minimo: 10,
      stock_actual: 50,
      activo: true,
    };

    it('permite edición parcial válida', () => {
      const productoEditado = {
        ...productoOriginal,
        nombre: 'Paracetamol 500mg - Actualizado',
      };

      const result = validarProductoEdicion(productoEditado, productoOriginal);

      expect(result.valido).toBe(true);
      expect(result.camposModificados).toContain('nombre');
    });

    it('rechaza vaciar nombre', () => {
      const productoEditado = {
        ...productoOriginal,
        nombre: '',
      };

      const result = validarProductoEdicion(productoEditado, productoOriginal);

      expect(result.valido).toBe(false);
      expect(result.errores.nombre).toBeTruthy();
    });

    it('advierte al desactivar producto con stock', () => {
      const productoEditado = {
        ...productoOriginal,
        activo: false,
      };

      const result = validarProductoEdicion(productoEditado, productoOriginal);

      expect(result.valido).toBe(true);
      expect(result.warnings.some(w => w.includes('stock'))).toBe(true);
    });

    it('no genera errores si no hay cambios', () => {
      const result = validarProductoEdicion(productoOriginal, productoOriginal);

      expect(result.valido).toBe(true);
      expect(result.camposModificados).toHaveLength(0);
    });
  });

  // =========================================================================
  // VALIDACIÓN DE REQUISICIONES
  // =========================================================================
  describe('validarRequisicionEnvio', () => {
    it('valida requisición completa correctamente', () => {
      const requisicion = {
        lugar_entrega: 'Almacén Central',
        detalles: [
          { producto_id: 1, cantidad_solicitada: 10 },
          { producto_id: 2, cantidad_solicitada: 5 },
        ],
      };

      const result = validarRequisicionEnvio(requisicion);

      expect(result.valido).toBe(true);
      expect(result.errores).toEqual({});
    });

    it('rechaza requisición sin detalles', () => {
      const requisicion = {
        lugar_entrega: 'Almacén',
        detalles: [],
      };

      const result = validarRequisicionEnvio(requisicion);

      expect(result.valido).toBe(false);
      expect(result.errores.detalles).toBeTruthy();
    });

    it('rechaza detalle sin producto', () => {
      const requisicion = {
        lugar_entrega: 'Almacén',
        detalles: [
          { cantidad_solicitada: 10 }, // Sin producto_id
        ],
      };

      const result = validarRequisicionEnvio(requisicion);

      expect(result.valido).toBe(false);
      expect(Object.keys(result.errores).some(k => k.includes('producto'))).toBe(true);
    });

    it('rechaza cantidad cero o negativa', () => {
      const requisicion = {
        lugar_entrega: 'Almacén',
        detalles: [
          { producto_id: 1, cantidad_solicitada: 0 },
        ],
      };

      const result = validarRequisicionEnvio(requisicion);

      expect(result.valido).toBe(false);
      expect(Object.keys(result.errores).some(k => k.includes('cantidad'))).toBe(true);
    });

    it('rechaza productos duplicados', () => {
      const requisicion = {
        lugar_entrega: 'Almacén',
        detalles: [
          { producto_id: 1, cantidad_solicitada: 10 },
          { producto_id: 1, cantidad_solicitada: 5 }, // Duplicado
        ],
      };

      const result = validarRequisicionEnvio(requisicion);

      expect(result.valido).toBe(false);
      expect(result.errores.duplicados).toBeTruthy();
    });

    it('rechaza sin lugar de entrega', () => {
      const requisicion = {
        detalles: [{ producto_id: 1, cantidad_solicitada: 10 }],
      };

      const result = validarRequisicionEnvio(requisicion);

      expect(result.valido).toBe(false);
      expect(result.errores.lugar_entrega).toBeTruthy();
    });

    it('genera warning cuando stock es insuficiente', () => {
      const productos = [
        { id: 1, clave: 'MED-001', nombre: 'Paracetamol', stock_actual: 5 },
      ];
      const requisicion = {
        lugar_entrega: 'Almacén',
        detalles: [
          { producto_id: 1, cantidad_solicitada: 20 }, // Mayor que stock
        ],
      };

      const result = validarRequisicionEnvio(requisicion, {
        verificarStock: true,
        productos,
      });

      expect(result.valido).toBe(true); // Stock bajo no bloquea, solo advierte
      expect(result.warnings.some(w => w.includes('Stock'))).toBe(true);
    });
  });

  // =========================================================================
  // VALIDACIÓN DE TRANSICIONES
  // =========================================================================
  describe('validarTransicionRequisicion', () => {
    it('permite transición válida borrador -> enviada para ADMIN', () => {
      const result = validarTransicionRequisicion('borrador', 'enviada', 'ADMIN');

      expect(result.valido).toBe(true);
      expect(result.error).toBeNull();
    });

    it('permite transición válida autorizada -> en_surtido para FARMACIA', () => {
      const result = validarTransicionRequisicion('autorizada', 'en_surtido', 'FARMACIA');

      expect(result.valido).toBe(true);
    });

    it('rechaza transición inválida borrador -> surtida', () => {
      const result = validarTransicionRequisicion('borrador', 'surtida', 'ADMIN');

      expect(result.valido).toBe(false);
      expect(result.error).toContain('No se puede cambiar');
    });

    it('rechaza transición para rol sin permisos', () => {
      const result = validarTransicionRequisicion('borrador', 'enviada', 'VISTA');

      // VISTA no puede enviar, pero la transición sería válida para otros roles
      expect(result.valido).toBe(false);
    });
  });

  // =========================================================================
  // VALIDACIÓN DE SURTIDO
  // =========================================================================
  describe('validarSurtidoRequisicion', () => {
    const requisicion = {
      id: 1,
      estado: 'autorizada',
      detalles: [
        { id: 1, producto_id: 10, producto_nombre: 'Paracetamol', cantidad_solicitada: 20, cantidad_aprobada: 20, cantidad_surtida: 0 },
        { id: 2, producto_id: 11, producto_nombre: 'Ibuprofeno', cantidad_solicitada: 10, cantidad_aprobada: 10, cantidad_surtida: 0 },
      ],
    };

    const lotes = [
      { id: 100, producto_id: 10, numero_lote: 'LOT-001', cantidad_actual: 50, fecha_caducidad: '2026-12-31' },
      { id: 101, producto_id: 11, numero_lote: 'LOT-002', cantidad_actual: 15, fecha_caducidad: '2025-06-30' },
    ];

    it('valida surtido completo correctamente', () => {
      const surtido = [
        { detalle_id: 1, cantidad: 20, lote_id: 100 },
        { detalle_id: 2, cantidad: 10, lote_id: 101 },
      ];

      const result = validarSurtidoRequisicion(requisicion, surtido, lotes);

      expect(result.valido).toBe(true);
      expect(result.detallesSurtido).toHaveLength(2);
    });

    it('rechaza cantidad mayor a pendiente', () => {
      const surtido = [
        { detalle_id: 1, cantidad: 30, lote_id: 100 }, // 30 > 20 aprobada
      ];

      const result = validarSurtidoRequisicion(requisicion, surtido, lotes);

      expect(result.valido).toBe(false);
      expect(result.errores.some(e => e.includes('excede'))).toBe(true);
    });

    it('rechaza cuando lote tiene stock insuficiente', () => {
      const lotesConPocoStock = [
        { id: 100, producto_id: 10, numero_lote: 'LOT-001', cantidad_actual: 5, fecha_caducidad: '2026-12-31' },
      ];
      const surtido = [
        { detalle_id: 1, cantidad: 20, lote_id: 100 }, // Lote solo tiene 5
      ];

      const result = validarSurtidoRequisicion(requisicion, surtido, lotesConPocoStock);

      expect(result.valido).toBe(false);
      expect(result.errores.some(e => e.includes('insuficiente'))).toBe(true);
    });

    it('rechaza lote vencido', () => {
      const lotesVencidos = [
        { id: 100, producto_id: 10, numero_lote: 'LOT-001', cantidad_actual: 50, fecha_caducidad: '2020-01-01' },
      ];
      const surtido = [
        { detalle_id: 1, cantidad: 10, lote_id: 100 },
      ];

      const result = validarSurtidoRequisicion(requisicion, surtido, lotesVencidos);

      expect(result.valido).toBe(false);
      expect(result.errores.some(e => e.includes('vencido'))).toBe(true);
    });
  });

  // =========================================================================
  // VALIDACIÓN DE LOTES
  // =========================================================================
  describe('validarLoteCreacion', () => {
    it('valida lote completo correctamente', () => {
      const lote = {
        numero_lote: 'LOT-2024-001',
        producto_id: 1,
        cantidad_inicial: 100,
        fecha_caducidad: '2026-12-31',
      };

      const result = validarLoteCreacion(lote);

      expect(result.valido).toBe(true);
    });

    it('rechaza lote sin número', () => {
      const lote = {
        producto_id: 1,
        cantidad_inicial: 100,
        fecha_caducidad: '2026-12-31',
      };

      const result = validarLoteCreacion(lote);

      expect(result.valido).toBe(false);
      expect(result.errores.numero_lote).toBeTruthy();
    });

    it('rechaza cantidad inicial cero', () => {
      const lote = {
        numero_lote: 'LOT-001',
        producto_id: 1,
        cantidad_inicial: 0,
        fecha_caducidad: '2026-12-31',
      };

      const result = validarLoteCreacion(lote);

      expect(result.valido).toBe(false);
      expect(result.errores.cantidad_inicial).toBeTruthy();
    });

    it('rechaza fecha de caducidad pasada', () => {
      const lote = {
        numero_lote: 'LOT-001',
        producto_id: 1,
        cantidad_inicial: 100,
        fecha_caducidad: '2020-01-01',
      };

      const result = validarLoteCreacion(lote);

      expect(result.valido).toBe(false);
      expect(result.errores.fecha_caducidad).toContain('pasada');
    });
  });

  // =========================================================================
  // MÉTRICAS DE VALIDACIÓN
  // =========================================================================
  describe('Métricas de validación', () => {
    it('registra validaciones exitosas y fallidas', () => {
      // Validación exitosa
      validarProductoCreacion({
        clave: 'MED-001',
        nombre: 'Test',
        unidad_medida: 'TABLETA',
        categoria: 'medicamento',
        stock_minimo: 10,
      });

      // Validación fallida
      validarProductoCreacion({
        clave: '', // Inválido
        nombre: 'Test',
      });

      const metrics = getValidationMetrics();

      expect(metrics.validations).toBe(2);
      expect(metrics.failures).toBe(1);
      expect(parseFloat(metrics.successRate)).toBe(50.0);
    });

    it('resetea métricas correctamente', () => {
      validarProductoCreacion({ clave: '' }); // Generar una falla

      resetValidationMetrics();
      const metrics = getValidationMetrics();

      expect(metrics.validations).toBe(0);
      expect(metrics.failures).toBe(0);
    });
  });

  // =========================================================================
  // CONSTANTES Y REGLAS
  // =========================================================================
  describe('Constantes y reglas', () => {
    it('PRODUCTO_RULES tiene todas las reglas necesarias', () => {
      expect(PRODUCTO_RULES.clave).toBeDefined();
      expect(PRODUCTO_RULES.nombre).toBeDefined();
      expect(PRODUCTO_RULES.unidad_medida).toBeDefined();
      expect(PRODUCTO_RULES.categoria).toBeDefined();
      expect(PRODUCTO_RULES.stock_minimo).toBeDefined();
    });

    it('ESTADOS_FLUJO_V2 tiene todos los estados', () => {
      expect(ESTADOS_FLUJO_V2.BORRADOR).toBe('borrador');
      expect(ESTADOS_FLUJO_V2.AUTORIZADA).toBe('autorizada');
      expect(ESTADOS_FLUJO_V2.SURTIDA).toBe('surtida');
      expect(ESTADOS_FLUJO_V2.ENTREGADA).toBe('entregada');
    });

    it('ACCIONES_POR_ROL define acciones para todos los roles principales', () => {
      expect(ACCIONES_POR_ROL.ADMIN).toBeDefined();
      expect(ACCIONES_POR_ROL.FARMACIA).toBeDefined();
      expect(ACCIONES_POR_ROL.CENTRO).toBeDefined();
      expect(ACCIONES_POR_ROL.VISTA).toBeDefined();
    });
  });
});
