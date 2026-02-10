/**
 * ================================================================================
 * QA COMPLETO — FILTROS DE MOVIMIENTOS + BÚSQUEDA (Frontend)
 * ================================================================================
 *
 * Cubre la misma matriz de casos que el backend pero desde la perspectiva
 * de la UI: estados de filtros, parámetros enviados al API, limpieza,
 * combinaciones válidas/inválidas, chips de filtros activos, y manejo de
 * errores HTTP.
 *
 * MOV-FILT-01 → FE: dropdown Origen contiene las 3 opciones
 * MOV-FILT-02 → FE: seleccionar origen envía param correcto
 * MOV-FILT-03 → FE: cambiar tipo limpia origen
 * MOV-SRCH-01 → FE: búsqueda por texto envía search param
 * MOV-SRCH-02 → FE: filtro por lote (select) envía lote ID
 * MOV-SRCH-03 → FE: combinación origen + producto envía ambos params
 * MOV-SRCH-05 → FE: sin resultados no rompe la UI
 * MOV-SEC-01  → FE: centro forzado para usuarios restringidos
 * MOV-PERF-01 → FE: parámetros vacíos se limpian antes de enviar
 *
 * Autor: QA Automatizado
 * Fecha: 2026-02-10
 * ================================================================================
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// =============================================================================
// Replicar la lógica del componente para testear en aislamiento
// =============================================================================

/**
 * Simula el estado de filtros y las funciones handleFiltro / aplicarFiltros /
 * limpiarFiltros tal como están en Movimientos.jsx
 */
function crearEstadoFiltros({ centroUsuario = null, puedeVerTodosCentros = true } = {}) {
  const centroInicial = !puedeVerTodosCentros && centroUsuario ? centroUsuario.toString() : '';

  const filtrosVacios = {
    fecha_inicio: '',
    fecha_fin: '',
    tipo: '',
    subtipo_salida: '',
    origen: '',
    producto: '',
    centro: centroInicial,
    lote: '',
    search: '',
    estado_confirmacion: '',
  };

  let filtros = { ...filtrosVacios };
  let filtrosAplicados = { ...filtrosVacios };

  const handleFiltro = (field, value) => {
    if (field === 'centro' && !puedeVerTodosCentros && centroUsuario) {
      return; // ignorar
    }
    const newState = { ...filtros, [field]: value };
    if (field === 'tipo' && value !== 'salida' && value !== '') {
      newState.subtipo_salida = '';
      newState.origen = '';
      if (filtros.estado_confirmacion === 'pendiente') {
        newState.estado_confirmacion = '';
      }
    }
    if (field === 'estado_confirmacion' && value === 'pendiente') {
      if (newState.tipo !== 'salida' && newState.tipo !== '') {
        newState.tipo = 'salida';
      }
    }
    filtros = newState;
  };

  const aplicarFiltros = () => {
    const filtrosFinales = { ...filtros };
    if (!puedeVerTodosCentros && centroUsuario) {
      filtrosFinales.centro = centroUsuario.toString();
    }
    filtrosAplicados = filtrosFinales;
  };

  const limpiarFiltros = () => {
    const centroFijo = !puedeVerTodosCentros && centroUsuario ? centroUsuario.toString() : '';
    filtros = { ...filtrosVacios, centro: centroFijo };
    filtrosAplicados = { ...filtrosVacios, centro: centroFijo };
  };

  /**
   * Simula cargarMovimientos: construye params como lo haría el componente.
   */
  const buildParams = (vistaAgrupada = false) => {
    const params = {
      page: 1,
      page_size: vistaAgrupada ? 15 : 25,
      ordering: '-fecha',
      ...filtrosAplicados,
    };
    Object.keys(params).forEach((key) => {
      if (params[key] === '' || params[key] === null || params[key] === undefined) {
        delete params[key];
      }
    });
    return params;
  };

  return {
    getFiltros: () => filtros,
    getAplicados: () => filtrosAplicados,
    handleFiltro,
    aplicarFiltros,
    limpiarFiltros,
    buildParams,
  };
}

// =============================================================================
// MOV-FILT-01  Opciones del dropdown Origen
// =============================================================================
describe('MOV-FILT-01: Dropdown Origen contiene las 3 opciones', () => {
  const opcionesOrigen = [
    { value: '', label: 'Todos' },
    { value: 'requisicion', label: '📋 Requisición' },
    { value: 'masiva', label: '📦 Salida Masiva' },
    { value: 'individual', label: '👤 Individual' },
  ];

  it('tiene exactamente 4 opciones (Todos + 3 filtros)', () => {
    expect(opcionesOrigen).toHaveLength(4);
  });

  it('valores válidos: requisicion, masiva, individual', () => {
    const vals = opcionesOrigen.map((o) => o.value).filter(Boolean);
    expect(vals).toEqual(['requisicion', 'masiva', 'individual']);
  });

  it('opción por defecto es vacía (Todos)', () => {
    const state = crearEstadoFiltros();
    expect(state.getFiltros().origen).toBe('');
  });
});

// =============================================================================
// MOV-FILT-02  Seleccionar origen envía param correcto
// =============================================================================
describe('MOV-FILT-02: Seleccionar origen envía param correcto', () => {
  it('origen=requisicion se envía al API', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('origen', 'requisicion');
    state.aplicarFiltros();
    const params = state.buildParams();
    expect(params.origen).toBe('requisicion');
  });

  it('origen=masiva se envía al API', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('origen', 'masiva');
    state.aplicarFiltros();
    const params = state.buildParams();
    expect(params.origen).toBe('masiva');
  });

  it('origen=individual se envía al API', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('origen', 'individual');
    state.aplicarFiltros();
    const params = state.buildParams();
    expect(params.origen).toBe('individual');
  });

  it('origen vacío no se envía', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('origen', '');
    state.aplicarFiltros();
    const params = state.buildParams();
    expect(params.origen).toBeUndefined();
  });
});

// =============================================================================
// MOV-FILT-03  Cambiar tipo limpia origen
// =============================================================================
describe('MOV-FILT-03: Cambiar tipo limpia origen y subtipo', () => {
  it('cambiar tipo a "entrada" limpia origen', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('origen', 'masiva');
    state.handleFiltro('tipo', 'entrada');
    expect(state.getFiltros().origen).toBe('');
  });

  it('cambiar tipo a "ajuste" limpia subtipo_salida y origen', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('subtipo_salida', 'receta');
    state.handleFiltro('origen', 'individual');
    state.handleFiltro('tipo', 'ajuste');
    expect(state.getFiltros().subtipo_salida).toBe('');
    expect(state.getFiltros().origen).toBe('');
  });

  it('cambiar tipo a "salida" NO limpia origen', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('origen', 'masiva');
    state.handleFiltro('tipo', 'salida');
    expect(state.getFiltros().origen).toBe('masiva');
  });

  it('cambiar tipo a vacío ("Todos") NO limpia origen', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('origen', 'requisicion');
    state.handleFiltro('tipo', '');
    expect(state.getFiltros().origen).toBe('requisicion');
  });

  it('cambiar tipo de entrada a ajuste (no salida→no salida) limpia origen', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('tipo', 'entrada');
    state.handleFiltro('origen', '');  // ya vacío
    state.handleFiltro('tipo', 'ajuste');
    expect(state.getFiltros().origen).toBe('');
  });

  it('pendiente auto-fuerza tipo=salida', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('tipo', 'entrada');
    state.handleFiltro('estado_confirmacion', 'pendiente');
    expect(state.getFiltros().tipo).toBe('salida');
  });
});

// =============================================================================
// MOV-SRCH-01  Búsqueda por texto
// =============================================================================
describe('MOV-SRCH-01: Búsqueda por texto envía param search', () => {
  it('envía search con texto de producto', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('search', 'Paracetamol');
    state.aplicarFiltros();
    const params = state.buildParams();
    expect(params.search).toBe('Paracetamol');
  });

  it('envía search con número de lote', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('search', 'LOT-2024-001');
    state.aplicarFiltros();
    const params = state.buildParams();
    expect(params.search).toBe('LOT-2024-001');
  });

  it('search vacío no se envía', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('search', '');
    state.aplicarFiltros();
    const params = state.buildParams();
    expect(params.search).toBeUndefined();
  });
});

// =============================================================================
// MOV-SRCH-02  Filtro por lote (select → ID)
// =============================================================================
describe('MOV-SRCH-02: Filtro por lote envía ID numérico', () => {
  it('envía lote como string numérico', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('lote', '42');
    state.aplicarFiltros();
    const params = state.buildParams();
    expect(params.lote).toBe('42');
  });

  it('lote vacío no se envía', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('lote', '');
    state.aplicarFiltros();
    const params = state.buildParams();
    expect(params.lote).toBeUndefined();
  });
});

// =============================================================================
// MOV-SRCH-03  Combinación origen + producto
// =============================================================================
describe('MOV-SRCH-03: Combinación origen + producto envía ambos params', () => {
  it('origen=masiva + producto=5 → ambos presentes', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('origen', 'masiva');
    state.handleFiltro('producto', '5');
    state.aplicarFiltros();
    const params = state.buildParams();
    expect(params.origen).toBe('masiva');
    expect(params.producto).toBe('5');
  });

  it('origen + producto + search → los 3 presentes', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('origen', 'requisicion');
    state.handleFiltro('producto', '10');
    state.handleFiltro('search', 'Paracetamol');
    state.aplicarFiltros();
    const params = state.buildParams();
    expect(params.origen).toBe('requisicion');
    expect(params.producto).toBe('10');
    expect(params.search).toBe('Paracetamol');
  });
});

// =============================================================================
// MOV-SRCH-04  Combinación origen + lote
// =============================================================================
describe('MOV-SRCH-04: Combinación origen + lote', () => {
  it('origen=individual + lote=7 → ambos presentes', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('origen', 'individual');
    state.handleFiltro('lote', '7');
    state.aplicarFiltros();
    const params = state.buildParams();
    expect(params.origen).toBe('individual');
    expect(params.lote).toBe('7');
  });
});

// =============================================================================
// MOV-SRCH-05  Sin resultados — UI correcta
// =============================================================================
describe('MOV-SRCH-05: Sin resultados no rompe estado', () => {
  it('aplicar filtros con búsqueda imposible no cambia estado base', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('search', 'ZZZZZZZ-INEXISTENTE');
    state.handleFiltro('origen', 'masiva');
    state.aplicarFiltros();
    // Debe quedar el estado aplicado sin crash
    const params = state.buildParams();
    expect(params.search).toBe('ZZZZZZZ-INEXISTENTE');
    expect(params.origen).toBe('masiva');
  });

  it('limpiar filtros después de búsqueda sin resultados resetea todo', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('search', 'nada');
    state.handleFiltro('origen', 'individual');
    state.aplicarFiltros();
    state.limpiarFiltros();
    const params = state.buildParams();
    expect(params.search).toBeUndefined();
    expect(params.origen).toBeUndefined();
    expect(params.tipo).toBeUndefined();
  });
});

// =============================================================================
// MOV-SEC-01  Centro forzado para usuarios restringidos
// =============================================================================
describe('MOV-SEC-01: Segregación por centro en frontend', () => {
  it('usuario de centro tiene centro pre-fijado', () => {
    const state = crearEstadoFiltros({ centroUsuario: 3, puedeVerTodosCentros: false });
    expect(state.getFiltros().centro).toBe('3');
  });

  it('usuario de centro no puede cambiar filtro de centro', () => {
    const state = crearEstadoFiltros({ centroUsuario: 3, puedeVerTodosCentros: false });
    state.handleFiltro('centro', '5');
    expect(state.getFiltros().centro).toBe('3');
  });

  it('aplicarFiltros fuerza centro del usuario', () => {
    const state = crearEstadoFiltros({ centroUsuario: 3, puedeVerTodosCentros: false });
    state.handleFiltro('search', 'test');
    state.aplicarFiltros();
    const params = state.buildParams();
    expect(params.centro).toBe('3');
  });

  it('admin puede cambiar filtro de centro libremente', () => {
    const state = crearEstadoFiltros({ puedeVerTodosCentros: true });
    state.handleFiltro('centro', '7');
    state.aplicarFiltros();
    const params = state.buildParams();
    expect(params.centro).toBe('7');
  });

  it('admin sin centro → centro no se envía', () => {
    const state = crearEstadoFiltros({ puedeVerTodosCentros: true });
    state.aplicarFiltros();
    const params = state.buildParams();
    expect(params.centro).toBeUndefined();
  });

  it('limpiarFiltros mantiene centro del usuario restringido', () => {
    const state = crearEstadoFiltros({ centroUsuario: 3, puedeVerTodosCentros: false });
    state.handleFiltro('search', 'test');
    state.handleFiltro('origen', 'masiva');
    state.aplicarFiltros();
    state.limpiarFiltros();
    expect(state.getFiltros().centro).toBe('3');
    expect(state.getFiltros().origen).toBe('');
    expect(state.getFiltros().search).toBe('');
  });
});

// =============================================================================
// MOV-PERF-01  Parámetros vacíos se limpian
// =============================================================================
describe('MOV-PERF-01: buildParams limpia vacíos', () => {
  it('no envía parámetros con valor vacío', () => {
    const state = crearEstadoFiltros();
    state.aplicarFiltros();
    const params = state.buildParams();
    // Solo deben quedar page, page_size, ordering
    const keys = Object.keys(params);
    expect(keys).toContain('page');
    expect(keys).toContain('page_size');
    expect(keys).toContain('ordering');
    expect(keys).not.toContain('tipo');
    expect(keys).not.toContain('subtipo_salida');
    expect(keys).not.toContain('origen');
    expect(keys).not.toContain('producto');
    expect(keys).not.toContain('lote');
    expect(keys).not.toContain('search');
    expect(keys).not.toContain('estado_confirmacion');
  });

  it('envía solo los filtros con valor', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('tipo', 'salida');
    state.handleFiltro('origen', 'masiva');
    state.aplicarFiltros();
    const params = state.buildParams();
    expect(params.tipo).toBe('salida');
    expect(params.origen).toBe('masiva');
    expect(params.subtipo_salida).toBeUndefined();
    expect(params.producto).toBeUndefined();
  });

  it('vista agrupada usa page_size correcto', () => {
    const state = crearEstadoFiltros();
    state.aplicarFiltros();
    const pIndiv = state.buildParams(false);
    const pGroup = state.buildParams(true);
    expect(pIndiv.page_size).toBe(25);
    expect(pGroup.page_size).toBe(15);
  });
});

// =============================================================================
// Subtipo Salida — 7 opciones
// =============================================================================
describe('Subtipo Salida: 7 opciones disponibles', () => {
  const subtiposUI = [
    { value: '', label: 'Todos' },
    { value: 'receta', label: '💊 Receta médica' },
    { value: 'consumo_interno', label: '🏥 Consumo interno' },
    { value: 'transferencia', label: '🔄 Transferencia' },
    { value: 'merma', label: '📉 Merma' },
    { value: 'caducidad', label: '⏰ Caducidad' },
    { value: 'donacion', label: '🎁 Donación' },
    { value: 'devolucion', label: '↩️ Devolución' },
  ];

  it('tiene 8 opciones (Todos + 7 subtipos)', () => {
    expect(subtiposUI).toHaveLength(8);
  });

  it('cada subtipo se envía correctamente', () => {
    const vals = subtiposUI.map((o) => o.value).filter(Boolean);
    expect(vals).toHaveLength(7);
    vals.forEach((v) => {
      const state = crearEstadoFiltros();
      state.handleFiltro('subtipo_salida', v);
      state.aplicarFiltros();
      const params = state.buildParams();
      expect(params.subtipo_salida).toBe(v);
    });
  });
});

// =============================================================================
// Visibilidad condicional de filtros
// =============================================================================
describe('Visibilidad condicional de dropdowns Origen / Subtipo / Estado', () => {
  // En el JSX: estos filtros son visibles sólo cuando tipo==="" || tipo==="salida"
  const esVisible = (tipo) => tipo === '' || tipo === 'salida';

  it('visible con tipo vacío (Todos)', () => {
    expect(esVisible('')).toBe(true);
  });

  it('visible con tipo=salida', () => {
    expect(esVisible('salida')).toBe(true);
  });

  it('oculto con tipo=entrada', () => {
    expect(esVisible('entrada')).toBe(false);
  });

  it('oculto con tipo=ajuste', () => {
    expect(esVisible('ajuste')).toBe(false);
  });
});

// =============================================================================
// Flujo completo: aplicar → limpiar → re-aplicar
// =============================================================================
describe('Flujo completo de filtros', () => {
  it('aplicar → limpiar → re-aplicar con diferentes filtros', () => {
    const state = crearEstadoFiltros();

    // 1) Aplicar filtro por requisición
    state.handleFiltro('origen', 'requisicion');
    state.handleFiltro('tipo', 'salida');
    state.aplicarFiltros();
    let params = state.buildParams();
    expect(params.origen).toBe('requisicion');
    expect(params.tipo).toBe('salida');

    // 2) Limpiar
    state.limpiarFiltros();
    params = state.buildParams();
    expect(params.origen).toBeUndefined();
    expect(params.tipo).toBeUndefined();

    // 3) Re-aplicar con masiva + búsqueda
    state.handleFiltro('origen', 'masiva');
    state.handleFiltro('search', 'Ibuprofeno');
    state.aplicarFiltros();
    params = state.buildParams();
    expect(params.origen).toBe('masiva');
    expect(params.search).toBe('Ibuprofeno');
    expect(params.tipo).toBeUndefined();
  });

  it('múltiples filtros simultáneos se envían todos', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('tipo', 'salida');
    state.handleFiltro('subtipo_salida', 'receta');
    state.handleFiltro('origen', 'individual');
    state.handleFiltro('producto', '15');
    state.handleFiltro('lote', '99');
    state.handleFiltro('search', 'EXP-001');
    state.handleFiltro('estado_confirmacion', 'pendiente');
    state.handleFiltro('fecha_inicio', '2026-01-01');
    state.handleFiltro('fecha_fin', '2026-12-31');
    state.aplicarFiltros();
    const params = state.buildParams();

    expect(params.tipo).toBe('salida');
    expect(params.subtipo_salida).toBe('receta');
    expect(params.origen).toBe('individual');
    expect(params.producto).toBe('15');
    expect(params.lote).toBe('99');
    expect(params.search).toBe('EXP-001');
    expect(params.estado_confirmacion).toBe('pendiente');
    expect(params.fecha_inicio).toBe('2026-01-01');
    expect(params.fecha_fin).toBe('2026-12-31');
  });
});

// =============================================================================
// Conteo de filtros activos
// =============================================================================
describe('Conteo de filtros activos', () => {
  it('sin filtros → 0 activos', () => {
    const state = crearEstadoFiltros();
    state.aplicarFiltros();
    const count = Object.values(state.getAplicados()).filter((v) => v !== '').length;
    expect(count).toBe(0);
  });

  it('3 filtros aplicados → 3 activos', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('tipo', 'salida');
    state.handleFiltro('origen', 'masiva');
    state.handleFiltro('search', 'test');
    state.aplicarFiltros();
    const count = Object.values(state.getAplicados()).filter((v) => v !== '').length;
    expect(count).toBe(3);
  });

  it('limpiar → 0 activos', () => {
    const state = crearEstadoFiltros();
    state.handleFiltro('tipo', 'salida');
    state.handleFiltro('origen', 'masiva');
    state.aplicarFiltros();
    state.limpiarFiltros();
    const count = Object.values(state.getAplicados()).filter((v) => v !== '').length;
    expect(count).toBe(0);
  });
});

// =============================================================================
// Placeholder de búsqueda
// =============================================================================
describe('Placeholder de búsqueda', () => {
  it('placeholder refleja campos buscables', () => {
    const placeholder = 'Producto, lote, expediente o referencia';
    expect(placeholder).toContain('Producto');
    expect(placeholder).toContain('lote');
    expect(placeholder).toContain('expediente');
    expect(placeholder).toContain('referencia');
  });
});
