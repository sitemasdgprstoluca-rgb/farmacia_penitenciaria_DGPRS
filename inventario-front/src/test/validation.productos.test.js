/**
 * ISS-005 FIX: Tests para validadores de productos y requisiciones
 * 
 * Cubre:
 * - Validación de productos alineada con backend (ISS-003)
 * - Validación de transiciones de requisiciones (ISS-004)
 * - Validación de stock contra lotes (ISS-004)
 * - Normalización de datos
 */

import { describe, it, expect } from 'vitest';
import {
  validarProducto,
  normalizarProducto,
  validarItemContraStock,
  validarItemsRequisicion,
  esTransicionValida,
  getAccionesPermitidas,
  TRANSICIONES_REQUISICION,
  ESTADOS_REQUISICION,
} from '../validation';

// ============================================
// TESTS DE VALIDACIÓN DE PRODUCTOS (ISS-003)
// ============================================

describe('validarProducto', () => {
  describe('campos obligatorios', () => {
    it('debe rechazar producto sin clave', () => {
      const producto = { nombre: 'Test', unidad_medida: 'PIEZA', presentacion: 'Caja x 10' };
      const { valido, errores } = validarProducto(producto);
      
      expect(valido).toBe(false);
      expect(errores.clave).toBeDefined();
    });

    it('debe rechazar producto sin nombre', () => {
      const producto = { clave: 'TEST-001', unidad_medida: 'PIEZA', presentacion: 'Caja x 10' };
      const { valido, errores } = validarProducto(producto);
      
      expect(valido).toBe(false);
      expect(errores.nombre).toBeDefined();
    });

    it('debe rechazar producto sin unidad_medida', () => {
      const producto = { clave: 'TEST-001', nombre: 'Producto Test', presentacion: 'Caja x 10' };
      const { valido, errores } = validarProducto(producto);
      
      expect(valido).toBe(false);
      expect(errores.unidad_medida).toBeDefined();
    });

    it('debe rechazar producto sin presentación en creación', () => {
      const producto = { clave: 'TEST-001', nombre: 'Producto Test', unidad_medida: 'PIEZA' };
      const { valido, errores } = validarProducto(producto, false);
      
      expect(valido).toBe(false);
      expect(errores.presentacion).toBeDefined();
    });

    it('debe rechazar producto sin presentación en edición (ahora es obligatoria)', () => {
      const producto = { clave: 'TEST-001', nombre: 'Producto Test', unidad_medida: 'PIEZA' };
      const { valido, errores } = validarProducto(producto, true);
      
      expect(valido).toBe(false);
      expect(errores.presentacion).toBeDefined();
    });
  });

  describe('validación de clave', () => {
    it('debe rechazar clave muy corta', () => {
      const producto = { clave: 'AB', nombre: 'Test', unidad_medida: 'PIEZA', presentacion: 'Caja' };
      const { valido, errores } = validarProducto(producto);
      
      expect(valido).toBe(false);
      expect(errores.clave).toContain('al menos 3');
    });

    it('debe rechazar clave con caracteres inválidos', () => {
      const producto = { clave: 'TEST@#$', nombre: 'Test', unidad_medida: 'PIEZA', presentacion: 'Caja' };
      const { valido, errores } = validarProducto(producto);
      
      expect(valido).toBe(false);
      expect(errores.clave).toContain('letras');
    });

    it('debe aceptar clave válida con guiones', () => {
      const producto = { clave: 'MED-001_A', nombre: 'Test', unidad_medida: 'PIEZA', presentacion: 'Caja' };
      const { valido, errores } = validarProducto(producto);
      
      expect(valido).toBe(true);
      expect(errores.clave).toBeUndefined();
    });
  });

  describe('validación de stock_minimo', () => {
    it('debe rechazar stock_minimo negativo', () => {
      const producto = { 
        clave: 'TEST-001', nombre: 'Test', unidad_medida: 'PIEZA', 
        presentacion: 'Caja', stock_minimo: -5 
      };
      const { valido, errores } = validarProducto(producto);
      
      expect(valido).toBe(false);
      expect(errores.stock_minimo).toBeDefined();
    });

    it('debe rechazar stock_minimo no entero', () => {
      const producto = { 
        clave: 'TEST-001', nombre: 'Test', unidad_medida: 'PIEZA', 
        presentacion: 'Caja', stock_minimo: 5.5 
      };
      const { valido, errores } = validarProducto(producto);
      
      expect(valido).toBe(false);
      expect(errores.stock_minimo).toContain('entero');
    });

    it('debe aceptar stock_minimo cero', () => {
      const producto = { 
        clave: 'TEST-001', nombre: 'Test', unidad_medida: 'PIEZA', 
        presentacion: 'Caja', stock_minimo: 0 
      };
      const { valido } = validarProducto(producto);
      
      expect(valido).toBe(true);
    });
  });

  describe('validación de categoría', () => {
    it('debe rechazar categoría inválida', () => {
      const producto = { 
        clave: 'TEST-001', nombre: 'Test', unidad_medida: 'PIEZA', 
        presentacion: 'Caja', categoria: 'invalid_category' 
      };
      const { valido, errores } = validarProducto(producto);
      
      expect(valido).toBe(false);
      expect(errores.categoria).toBeDefined();
    });

    it('debe aceptar categorías válidas', () => {
      const categorias = ['medicamento', 'material_curacion', 'insumo', 'equipo', 'otro'];
      
      for (const cat of categorias) {
        const producto = { 
          clave: 'TEST-001', nombre: 'Test', unidad_medida: 'PIEZA', 
          presentacion: 'Caja', categoria: cat 
        };
        const { valido } = validarProducto(producto);
        expect(valido).toBe(true);
      }
    });
  });

  describe('producto completo', () => {
    it('debe validar producto completo', () => {
      const producto = {
        clave: 'MED-001',
        nombre: 'Paracetamol 500mg',
        unidad_medida: 'TABLETA',
        presentacion: 'Caja x 20',
        categoria: 'medicamento',
        stock_minimo: 10,
      };
      const { valido, errores, primerError } = validarProducto(producto);
      
      expect(valido).toBe(true);
      expect(Object.keys(errores)).toHaveLength(0);
      expect(primerError).toBeNull();
    });

    it('debe aceptar descripcion como campo opcional', () => {
      const producto = {
        clave: 'MED-001',
        nombre: 'Paracetamol 500mg',
        descripcion: 'Analgésico y antipirético',
        unidad_medida: 'TABLETA',
        presentacion: 'Caja x 20',
        categoria: 'medicamento',
      };
      const { valido } = validarProducto(producto);
      
      expect(valido).toBe(true);
    });
  });
});

describe('normalizarProducto', () => {
  it('debe normalizar producto null', () => {
    expect(normalizarProducto(null)).toBeNull();
  });

  it('debe normalizar tipos numéricos', () => {
    const producto = {
      id: 1,
      clave: 'TEST',
      stock_minimo: '10', // String del backend
      stock_actual: '50',
      precio_unitario: '25.50',
    };
    const normalizado = normalizarProducto(producto);
    
    expect(typeof normalizado.stock_minimo).toBe('number');
    expect(typeof normalizado.stock_actual).toBe('number');
    expect(typeof normalizado.precio_unitario).toBe('number');
    expect(normalizado.stock_minimo).toBe(10);
  });

  it('debe normalizar booleanos', () => {
    const producto = {
      id: 1,
      clave: 'TEST',
      activo: undefined,
      requiere_receta: 1,
      es_controlado: 'true',
    };
    const normalizado = normalizarProducto(producto);
    
    expect(normalizado.activo).toBe(true); // Default true
    expect(typeof normalizado.requiere_receta).toBe('boolean');
    expect(typeof normalizado.es_controlado).toBe('boolean');
  });

  it('debe preservar campos opcionales', () => {
    const producto = {
      id: 1,
      clave: 'TEST',
      descripcion: 'Descripción',
      nombre: 'Nombre',
      unidad_medida: 'CAJA',
    };
    const normalizado = normalizarProducto(producto);
    
    expect(normalizado.descripcion).toBe('Descripción');
    expect(normalizado.nombre).toBe('Nombre');
  });
});

// ============================================
// TESTS DE VALIDACIÓN DE REQUISICIONES (ISS-004)
// ============================================

describe('esTransicionValida', () => {
  it('debe permitir transiciones válidas desde borrador', () => {
    expect(esTransicionValida('borrador', 'enviada')).toBe(true);
    expect(esTransicionValida('borrador', 'cancelada')).toBe(true);
  });

  it('debe rechazar transiciones inválidas desde borrador', () => {
    expect(esTransicionValida('borrador', 'surtida')).toBe(false);
    expect(esTransicionValida('borrador', 'entregada')).toBe(false);
    expect(esTransicionValida('borrador', 'autorizada')).toBe(false);
  });

  it('debe permitir transiciones válidas desde enviada', () => {
    expect(esTransicionValida('enviada', 'aceptada_parcial')).toBe(true);
    expect(esTransicionValida('enviada', 'autorizada')).toBe(true);
    expect(esTransicionValida('enviada', 'rechazada')).toBe(true);
  });

  it('debe permitir transiciones válidas desde autorizada', () => {
    expect(esTransicionValida('autorizada', 'surtida')).toBe(true);
    expect(esTransicionValida('autorizada', 'surtida_parcial')).toBe(true);
    expect(esTransicionValida('autorizada', 'rechazada')).toBe(true);
  });

  it('debe bloquear transiciones desde estados finales', () => {
    expect(esTransicionValida('entregada', 'borrador')).toBe(false);
    expect(esTransicionValida('rechazada', 'enviada')).toBe(false);
    expect(esTransicionValida('cancelada', 'autorizada')).toBe(false);
  });

  it('debe manejar estados null/undefined', () => {
    expect(esTransicionValida(null, 'enviada')).toBe(false);
    expect(esTransicionValida('borrador', null)).toBe(false);
    expect(esTransicionValida(undefined, undefined)).toBe(false);
  });

  it('debe ser case-insensitive', () => {
    expect(esTransicionValida('BORRADOR', 'ENVIADA')).toBe(true);
    expect(esTransicionValida('Borrador', 'Enviada')).toBe(true);
  });
});

describe('getAccionesPermitidas', () => {
  it('debe retornar acciones para estado borrador', () => {
    const acciones = getAccionesPermitidas('borrador', 'ADMIN');
    
    expect(acciones).toContain('enviar');
    expect(acciones).toContain('editar');
    expect(acciones).toContain('eliminar');
    expect(acciones).toContain('ver');
  });

  it('debe retornar acciones limitadas para rol VISTA', () => {
    const acciones = getAccionesPermitidas('borrador', 'VISTA');
    
    expect(acciones).not.toContain('enviar');
    expect(acciones).not.toContain('editar');
    expect(acciones).toContain('ver'); // Vista siempre puede ver
  });

  it('debe retornar acciones de surtido para FARMACIA en estado autorizada', () => {
    const acciones = getAccionesPermitidas('autorizada', 'FARMACIA');
    
    expect(acciones).toContain('surtir');
    expect(acciones).toContain('rechazar');
  });

  it('debe retornar solo ver para estados finales', () => {
    const accionesEntregada = getAccionesPermitidas('entregada', 'ADMIN');
    const accionesRechazada = getAccionesPermitidas('rechazada', 'ADMIN');
    
    expect(accionesEntregada).toEqual(['ver']);
    expect(accionesRechazada).toEqual(['ver']);
  });
});

describe('validarItemContraStock', () => {
  const loteMock = {
    id: 1,
    stock_actual: 100,
    fecha_caducidad: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(), // 1 año
  };

  it('debe validar item con stock suficiente', () => {
    const item = { lote_id: 1, cantidad: 50 };
    const resultado = validarItemContraStock(item, loteMock);
    
    expect(resultado.valido).toBe(true);
    expect(resultado.error).toBeNull();
  });

  it('debe rechazar cantidad mayor al stock', () => {
    const item = { lote_id: 1, cantidad: 150 };
    const resultado = validarItemContraStock(item, loteMock);
    
    expect(resultado.valido).toBe(false);
    expect(resultado.error).toContain('insuficiente');
  });

  it('debe rechazar cantidad cero o negativa', () => {
    expect(validarItemContraStock({ cantidad: 0 }, loteMock).valido).toBe(false);
    expect(validarItemContraStock({ cantidad: -1 }, loteMock).valido).toBe(false);
  });

  it('debe rechazar cantidad no entera', () => {
    const item = { lote_id: 1, cantidad: 5.5 };
    const resultado = validarItemContraStock(item, loteMock);
    
    expect(resultado.valido).toBe(false);
    expect(resultado.error).toContain('entero');
  });

  it('debe rechazar lote caducado', () => {
    const loteCaducado = {
      ...loteMock,
      fecha_caducidad: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), // Ayer
    };
    const item = { lote_id: 1, cantidad: 10 };
    const resultado = validarItemContraStock(item, loteCaducado);
    
    expect(resultado.valido).toBe(false);
    expect(resultado.error).toContain('caducó');
  });

  it('debe advertir si lote caduca pronto', () => {
    const lotePorCaducar = {
      ...loteMock,
      fecha_caducidad: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000).toISOString(), // 15 días
    };
    const item = { lote_id: 1, cantidad: 10 };
    const resultado = validarItemContraStock(item, lotePorCaducar);
    
    expect(resultado.valido).toBe(true);
    expect(resultado.advertencia).toContain('caduca');
  });

  it('debe manejar datos incompletos', () => {
    expect(validarItemContraStock(null, loteMock).valido).toBe(false);
    expect(validarItemContraStock({ cantidad: 10 }, null).valido).toBe(false);
  });
});

describe('validarItemsRequisicion', () => {
  const lotesMap = {
    1: { id: 1, stock_actual: 100, fecha_caducidad: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(), producto_nombre: 'Producto A' },
    2: { id: 2, stock_actual: 50, fecha_caducidad: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(), producto_nombre: 'Producto B' },
  };

  it('debe rechazar requisición sin items', () => {
    const { valido, errores } = validarItemsRequisicion([]);
    
    expect(valido).toBe(false);
    expect(errores).toContain('al menos un item');
  });

  it('debe validar requisición con items válidos', () => {
    const items = [
      { lote_id: 1, cantidad: 10 },
      { lote_id: 2, cantidad: 20 },
    ];
    const { valido, errores, advertencias } = validarItemsRequisicion(items, lotesMap);
    
    expect(valido).toBe(true);
    expect(errores).toHaveLength(0);
  });

  it('debe acumular errores de múltiples items', () => {
    const items = [
      { lote_id: 1, cantidad: 200 }, // Excede stock
      { lote_id: 2, cantidad: 100 }, // Excede stock
    ];
    const { valido, errores } = validarItemsRequisicion(items, lotesMap);
    
    expect(valido).toBe(false);
    expect(errores.length).toBe(2);
  });

  it('debe acumular advertencias', () => {
    const lotesConProximaCaducidad = {
      1: { ...lotesMap[1], fecha_caducidad: new Date(Date.now() + 20 * 24 * 60 * 60 * 1000).toISOString() },
    };
    const items = [{ lote_id: 1, cantidad: 10 }];
    const { valido, advertencias } = validarItemsRequisicion(items, lotesConProximaCaducidad);
    
    expect(valido).toBe(true);
    expect(advertencias.length).toBeGreaterThan(0);
  });
});

describe('TRANSICIONES_REQUISICION constante', () => {
  it('debe tener todos los estados FLUJO V2 definidos', () => {
    // ISS-001: Estados alineados con backend/core/constants.py
    const estadosEsperados = [
      'borrador', 'pendiente_admin', 'pendiente_director',
      'enviada', 'en_revision', 'autorizada', 'en_surtido',
      'parcial', 'surtida', 'devuelta', 
      'entregada', 'rechazada', 'vencida', 'cancelada'
    ];
    
    for (const estado of estadosEsperados) {
      expect(TRANSICIONES_REQUISICION).toHaveProperty(estado);
    }
  });

  it('los estados finales deben tener array vacío', () => {
    expect(TRANSICIONES_REQUISICION.entregada).toEqual([]);
    expect(TRANSICIONES_REQUISICION.rechazada).toEqual([]);
    expect(TRANSICIONES_REQUISICION.cancelada).toEqual([]);
    expect(TRANSICIONES_REQUISICION.vencida).toEqual([]);
  });
});
