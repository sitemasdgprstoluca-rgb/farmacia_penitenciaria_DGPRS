/**
 * Tests unitarios para normalización de datos de Trazabilidad.
 * 
 * Problema detectado: Cuando se busca por clave/nombre, los campos
 * nombre y descripción no se mapeaban correctamente porque estaban
 * en data.producto, no en data directamente.
 */
import { describe, it, expect } from 'vitest';

// ============ Normalizadores (replicados del componente) ============

const getCentroNombre = (centro) => {
  if (!centro) return 'Sin centro';
  if (typeof centro === 'string') return centro;
  if (typeof centro === 'object') {
    return centro.nombre || centro.name || `Centro ${centro.id || ''}`;
  }
  return String(centro);
};

const mapMovimiento = (mov = {}) => ({
  id: mov.id,
  fecha: mov.fecha || mov.fecha_movimiento || mov.fecha_mov || null,
  tipo: (mov.tipo || mov.tipo_movimiento || '').toString().toUpperCase(),
  cantidad: mov.cantidad,
  centro: getCentroNombre(mov.centro || mov.centro_nombre),
  usuario: mov.usuario || mov.usuario_nombre || '',
  lote: mov.lote || mov.lote_numero || '',
  observaciones: mov.observaciones || '',
  saldo: mov.saldo,
});

const mapLote = (lote = {}) => ({
  numero_lote: lote.numero_lote,
  fecha_caducidad: lote.fecha_caducidad,
  cantidad_actual: lote.cantidad_actual,
  cantidad_inicial: lote.cantidad_inicial ?? lote.cantidad_actual,
  estado: (lote.estado || lote.estado_caducidad || '').toString().toUpperCase(),
  centro: getCentroNombre(lote.centro),
  numero_contrato: lote.numero_contrato || '',
  marca: lote.marca || '',
});

/**
 * Normalizador CORREGIDO - prioriza data.producto para obtener nombre/descripción
 */
const normalizeProductoResponse = (data) => {
  if (!data) return null;

  const lotes = Array.isArray(data.lotes) ? data.lotes.map(mapLote) : [];
  const movimientos = Array.isArray(data.movimientos) ? data.movimientos.map(mapMovimiento) : [];

  // ISS-FIX: El backend devuelve data.codigo + data.producto con los detalles
  // Priorizar data.producto para obtener nombre/descripción
  if (data.producto) {
    const producto = data.producto;
    return {
      codigo: data.codigo || producto.clave || producto.codigo,
      nombre: producto.nombre || producto.descripcion || '',
      descripcion: producto.descripcion || producto.nombre || '',
      presentacion: producto.presentacion || '',
      unidad_medida: producto.unidad_medida || 'PIEZA',
      precio_unitario: producto.precio_unitario || producto.precio || 0,
      stock_actual: data.estadisticas?.stock_total ?? producto.stock_actual ?? 0,
      stock_minimo: producto.stock_minimo ?? data.estadisticas?.stock_minimo ?? null,
      lotes,
      movimientos,
      alertas: data.alertas || [],
      estadisticas: data.estadisticas || {},
    };
  }

  // Fallback: estructura donde los datos vienen directamente en data
  if (data.codigo) {
    return {
      codigo: data.codigo,
      nombre: data.nombre || data.descripcion || '',
      descripcion: data.descripcion || data.nombre || '',
      presentacion: data.presentacion || '',
      unidad_medida: data.unidad_medida || 'PIEZA',
      precio_unitario: data.precio_unitario || data.precio || 0,
      stock_actual: data.stock_actual ?? data.estadisticas?.stock_total ?? 0,
      stock_minimo: data.stock_minimo ?? data.estadisticas?.stock_minimo ?? null,
      lotes,
      movimientos,
      alertas: data.alertas || [],
      estadisticas: data.estadisticas || {},
    };
  }

  return data;
};

// ============ Tests de normalización ============

describe('Normalización de respuesta de trazabilidad de producto', () => {
  describe('Búsqueda por clave (ej: "615")', () => {
    // Este es el formato REAL que devuelve el backend cuando buscas por clave
    const respuestaBackendPorClave = {
      codigo: '615',
      producto: {
        id: 615,
        clave: '615',
        nombre: 'KETOCONAZOL/CLINDAMICINA',
        descripcion: 'KETOCONAZOL/CLINDAMICINA',
        unidad_medida: 'PIEZA',
        stock_minimo: 1,
        precio_unitario: null,
        activo: true,
      },
      estadisticas: {
        stock_total: 292,
        total_lotes: 3,
        lotes_activos: 3,
        total_entradas: 2,
        total_salidas: 9,
        diferencia: -7,
        lotes_proximos_vencer: 0,
        lotes_vencidos: 0,
        bajo_minimo: false,
      },
      lotes: [
        {
          id: 1,
          numero_lote: 'LOT-615-001',
          fecha_caducidad: '2027-12-31',
          cantidad_actual: 100,
          cantidad_inicial: 100,
        },
      ],
      movimientos: [],
      total_movimientos: 11,
      alertas: [],
    };

    it('debe extraer el nombre del producto de data.producto', () => {
      const normalizado = normalizeProductoResponse(respuestaBackendPorClave);
      
      expect(normalizado.nombre).toBe('KETOCONAZOL/CLINDAMICINA');
      expect(normalizado.nombre).not.toBe('');
      expect(normalizado.nombre).not.toBeUndefined();
    });

    it('debe extraer la clave/codigo correctamente', () => {
      const normalizado = normalizeProductoResponse(respuestaBackendPorClave);
      
      expect(normalizado.codigo).toBe('615');
    });

    it('debe extraer la descripción del producto', () => {
      const normalizado = normalizeProductoResponse(respuestaBackendPorClave);
      
      expect(normalizado.descripcion).toBe('KETOCONAZOL/CLINDAMICINA');
    });

    it('debe extraer la unidad de medida', () => {
      const normalizado = normalizeProductoResponse(respuestaBackendPorClave);
      
      expect(normalizado.unidad_medida).toBe('PIEZA');
    });

    it('debe extraer el stock actual de estadisticas', () => {
      const normalizado = normalizeProductoResponse(respuestaBackendPorClave);
      
      expect(normalizado.stock_actual).toBe(292);
    });

    it('debe extraer el stock mínimo de producto', () => {
      const normalizado = normalizeProductoResponse(respuestaBackendPorClave);
      
      expect(normalizado.stock_minimo).toBe(1);
    });

    it('debe mapear los lotes correctamente', () => {
      const normalizado = normalizeProductoResponse(respuestaBackendPorClave);
      
      expect(normalizado.lotes).toHaveLength(1);
      expect(normalizado.lotes[0].numero_lote).toBe('LOT-615-001');
    });

    it('debe incluir las estadísticas', () => {
      const normalizado = normalizeProductoResponse(respuestaBackendPorClave);
      
      expect(normalizado.estadisticas.total_lotes).toBe(3);
      expect(normalizado.estadisticas.total_entradas).toBe(2);
      expect(normalizado.estadisticas.total_salidas).toBe(9);
    });
  });

  describe('Búsqueda por nombre de producto', () => {
    const respuestaBackendPorNombre = {
      codigo: 'PARA-500',
      producto: {
        id: 1,
        clave: 'PARA-500',
        nombre: 'Paracetamol 500mg',
        descripcion: 'Tabletas de paracetamol 500mg',
        unidad_medida: 'TABLETA',
        stock_minimo: 100,
        activo: true,
      },
      estadisticas: {
        stock_total: 500,
        total_lotes: 2,
      },
      lotes: [],
      movimientos: [],
      alertas: [],
    };

    it('debe extraer nombre cuando se busca por texto', () => {
      const normalizado = normalizeProductoResponse(respuestaBackendPorNombre);
      
      expect(normalizado.nombre).toBe('Paracetamol 500mg');
      expect(normalizado.descripcion).toBe('Tabletas de paracetamol 500mg');
    });

    it('debe usar descripción como fallback si no hay nombre', () => {
      const respuestaSinNombre = {
        ...respuestaBackendPorNombre,
        producto: {
          ...respuestaBackendPorNombre.producto,
          nombre: '',
          descripcion: 'Solo descripción disponible',
        },
      };
      
      const normalizado = normalizeProductoResponse(respuestaSinNombre);
      
      expect(normalizado.nombre).toBe('Solo descripción disponible');
    });
  });

  describe('Fallback para estructura legacy', () => {
    // Estructura antigua donde los datos vienen directamente en data
    const respuestaLegacy = {
      codigo: 'MED-001',
      nombre: 'Medicamento Legacy',
      descripcion: 'Descripción legacy',
      unidad_medida: 'CAJA',
      stock_actual: 50,
      lotes: [],
      movimientos: [],
      alertas: [],
    };

    it('debe funcionar con estructura legacy (sin data.producto)', () => {
      const normalizado = normalizeProductoResponse(respuestaLegacy);
      
      expect(normalizado.codigo).toBe('MED-001');
      expect(normalizado.nombre).toBe('Medicamento Legacy');
    });
  });

  describe('Manejo de datos nulos/vacíos', () => {
    it('debe retornar null para data null', () => {
      const normalizado = normalizeProductoResponse(null);
      expect(normalizado).toBeNull();
    });

    it('debe retornar null para data undefined', () => {
      const normalizado = normalizeProductoResponse(undefined);
      expect(normalizado).toBeNull();
    });

    it('debe manejar producto con campos vacíos', () => {
      const respuestaVacia = {
        codigo: '999',
        producto: {
          clave: '999',
          nombre: '',
          descripcion: '',
        },
        estadisticas: {},
        lotes: [],
        movimientos: [],
        alertas: [],
      };

      const normalizado = normalizeProductoResponse(respuestaVacia);
      
      expect(normalizado.codigo).toBe('999');
      expect(normalizado.nombre).toBe('');
      expect(normalizado.unidad_medida).toBe('PIEZA'); // Default
    });
  });
});

// ============ Tests de mapeo de lotes ============

describe('Mapeo de lotes', () => {
  it('debe mapear todos los campos del lote', () => {
    const loteBackend = {
      numero_lote: 'LOT-2026-001',
      fecha_caducidad: '2027-06-30',
      cantidad_actual: 150,
      cantidad_inicial: 200,
      estado_caducidad: 'NORMAL',
      centro: { id: 1, nombre: 'Centro Santiaguito' },
      numero_contrato: 'CONT-2026-001',
      marca: 'Laboratorio XYZ',
    };

    const mapeado = mapLote(loteBackend);

    expect(mapeado.numero_lote).toBe('LOT-2026-001');
    expect(mapeado.fecha_caducidad).toBe('2027-06-30');
    expect(mapeado.cantidad_actual).toBe(150);
    expect(mapeado.cantidad_inicial).toBe(200);
    expect(mapeado.estado).toBe('NORMAL');
    expect(mapeado.centro).toBe('Centro Santiaguito');
    expect(mapeado.numero_contrato).toBe('CONT-2026-001');
    expect(mapeado.marca).toBe('Laboratorio XYZ');
  });

  it('debe usar cantidad_actual como fallback de cantidad_inicial', () => {
    const lote = {
      numero_lote: 'LOT-001',
      cantidad_actual: 100,
      // Sin cantidad_inicial
    };

    const mapeado = mapLote(lote);
    
    expect(mapeado.cantidad_inicial).toBe(100);
  });
});

// ============ Tests de mapeo de movimientos ============

describe('Mapeo de movimientos', () => {
  it('debe mapear campos de movimiento correctamente', () => {
    const movBackend = {
      id: 1,
      fecha: '2026-01-05T10:30:00',
      tipo: 'salida',
      cantidad: 10,
      centro_nombre: 'Centro Santiaguito',
      usuario_nombre: 'Dr. García',
      lote_numero: 'LOT-001',
      observaciones: 'Dispensación por receta',
    };

    const mapeado = mapMovimiento(movBackend);

    expect(mapeado.id).toBe(1);
    expect(mapeado.tipo).toBe('SALIDA');
    expect(mapeado.cantidad).toBe(10);
    expect(mapeado.centro).toBe('Centro Santiaguito');
    expect(mapeado.usuario).toBe('Dr. García');
    expect(mapeado.lote).toBe('LOT-001');
  });

  it('debe manejar campos alternativos', () => {
    const movAlt = {
      id: 2,
      fecha_movimiento: '2026-01-05',
      tipo_movimiento: 'entrada',
      cantidad: 50,
      centro: { nombre: 'Farmacia Central' },
    };

    const mapeado = mapMovimiento(movAlt);

    expect(mapeado.fecha).toBe('2026-01-05');
    expect(mapeado.tipo).toBe('ENTRADA');
    expect(mapeado.centro).toBe('Farmacia Central');
  });
});

// ============ Tests de getCentroNombre ============

describe('getCentroNombre helper', () => {
  it('retorna string directamente', () => {
    expect(getCentroNombre('Farmacia Central')).toBe('Farmacia Central');
  });

  it('extrae nombre de objeto', () => {
    expect(getCentroNombre({ id: 1, nombre: 'Centro Test' })).toBe('Centro Test');
  });

  it('usa name como fallback', () => {
    expect(getCentroNombre({ id: 1, name: 'Centro English' })).toBe('Centro English');
  });

  it('retorna "Sin centro" para null/undefined', () => {
    expect(getCentroNombre(null)).toBe('Sin centro');
    expect(getCentroNombre(undefined)).toBe('Sin centro');
  });

  it('genera nombre con ID si no hay nombre', () => {
    expect(getCentroNombre({ id: 5 })).toBe('Centro 5');
  });
});
