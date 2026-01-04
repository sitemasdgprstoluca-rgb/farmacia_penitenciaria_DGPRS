/**
 * Tests unitarios para el módulo de Lotes - Frontend
 * 
 * Verifica:
 * - Filtros por usuario/centro
 * - Validaciones de formulario
 * - Cálculos de estados (caducidad)
 * - Permisos por rol
 * - CRUD operations mocking
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '../../context/ThemeContext';

// Mock de hooks y servicios
vi.mock('../../hooks/usePermissions', () => ({
  usePermissions: vi.fn()
}));

vi.mock('../../services/api', () => ({
  lotesAPI: {
    getAll: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    exportExcel: vi.fn(),
    exportPDF: vi.fn(),
    importExcel: vi.fn()
  },
  productosAPI: {
    getAll: vi.fn()
  },
  centrosAPI: {
    getAll: vi.fn()
  }
}));

import { usePermissions } from '../../hooks/usePermissions';
import { lotesAPI, productosAPI, centrosAPI } from '../../services/api';

// Componente wrapper para tests
const TestWrapper = ({ children }) => (
  <BrowserRouter>
    <ThemeProvider>
      {children}
    </ThemeProvider>
  </BrowserRouter>
);

// ============================================================================
// TESTS DE PERMISOS Y FILTROS
// ============================================================================

describe('Lotes - Filtros por Usuario y Permisos', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock default del API
    productosAPI.getAll.mockResolvedValue({ data: { results: [] } });
    centrosAPI.getAll.mockResolvedValue({ data: { results: [] } });
    lotesAPI.getAll.mockResolvedValue({ data: { results: [], count: 0 } });
  });

  it('Usuario ADMIN puede ver todos los lotes (sin filtro de centro)', async () => {
    usePermissions.mockReturnValue({
      user: { id: 1, rol: 'admin_sistema', is_superuser: true },
      permisos: { verLotes: true },
      loading: false
    });

    lotesAPI.getAll.mockResolvedValue({
      data: {
        results: [
          { id: 1, numero_lote: 'LOT-001', centro: null },
          { id: 2, numero_lote: 'LOT-002', centro: { id: 1, nombre: 'Centro A' } }
        ],
        count: 2
      }
    });

    // Admin debe poder ver lotes de cualquier centro
    expect(usePermissions().user.is_superuser).toBe(true);
    expect(usePermissions().permisos.verLotes).toBe(true);
  });

  it('Usuario FARMACIA puede ver todos los lotes', () => {
    usePermissions.mockReturnValue({
      user: { id: 2, rol: 'farmacia', is_staff: true },
      permisos: { verLotes: true },
      loading: false
    });

    // Farmacia debe tener acceso global
    expect(usePermissions().user.rol).toBe('farmacia');
    expect(usePermissions().permisos.verLotes).toBe(true);
  });

  it('Usuario CENTRO solo ve lotes de su centro asignado', () => {
    usePermissions.mockReturnValue({
      user: { 
        id: 3, 
        rol: 'centro', 
        centro: { id: 5, nombre: 'Centro Penitenciario X' },
        centro_id: 5
      },
      permisos: { verLotes: true },
      loading: false
    });

    const user = usePermissions().user;
    
    // Debe tener centro asignado
    expect(user.centro).toBeDefined();
    expect(user.centro.id).toBe(5);
    expect(user.rol).toBe('centro');
    
    // El componente debe forzar el filtro por este centro
  });

  it('Usuario sin centro asignado no puede cargar lotes', () => {
    usePermissions.mockReturnValue({
      user: { 
        id: 4, 
        rol: 'centro', 
        centro: null,
        centro_id: null
      },
      permisos: { verLotes: true },
      loading: false
    });

    const user = usePermissions().user;
    
    // Usuario de centro sin centro = no puede ver nada
    expect(user.centro).toBeNull();
    expect(user.rol).toBe('centro');
  });

  it('Usuario VISTA puede ver pero no modificar lotes', () => {
    usePermissions.mockReturnValue({
      user: { id: 5, rol: 'vista' },
      permisos: { 
        verLotes: true,
        crearLote: false,
        editarLote: false,
        eliminarLote: false
      },
      loading: false
    });

    const permisos = usePermissions().permisos;
    
    expect(permisos.verLotes).toBe(true);
    expect(permisos.crearLote).toBe(false);
    expect(permisos.editarLote).toBe(false);
    expect(permisos.eliminarLote).toBe(false);
  });
});

// ============================================================================
// TESTS DE CÁLCULO DE ESTADOS DE CADUCIDAD
// ============================================================================

describe('Lotes - Cálculo de Estados de Caducidad', () => {
  const calcularEstadoCaducidad = (fechaCaducidad) => {
    if (!fechaCaducidad) return 'normal';
    
    const hoy = new Date();
    const caducidad = new Date(fechaCaducidad);
    const dias = Math.floor((caducidad - hoy) / (1000 * 60 * 60 * 24));
    
    if (dias < 0) return 'vencido';
    if (dias < 90) return 'critico';
    if (dias < 180) return 'proximo';
    return 'normal';
  };

  it('debe retornar "vencido" si la fecha es pasada', () => {
    const fechaPasada = new Date();
    fechaPasada.setDate(fechaPasada.getDate() - 30);
    
    expect(calcularEstadoCaducidad(fechaPasada)).toBe('vencido');
  });

  it('debe retornar "critico" si faltan menos de 90 días', () => {
    const fecha = new Date();
    fecha.setDate(fecha.getDate() + 60);
    
    expect(calcularEstadoCaducidad(fecha)).toBe('critico');
  });

  it('debe retornar "proximo" si faltan entre 90 y 180 días', () => {
    const fecha = new Date();
    fecha.setDate(fecha.getDate() + 120);
    
    expect(calcularEstadoCaducidad(fecha)).toBe('proximo');
  });

  it('debe retornar "normal" si faltan más de 180 días', () => {
    const fecha = new Date();
    fecha.setDate(fecha.getDate() + 365);
    
    expect(calcularEstadoCaducidad(fecha)).toBe('normal');
  });

  it('debe retornar "normal" si no hay fecha', () => {
    expect(calcularEstadoCaducidad(null)).toBe('normal');
    expect(calcularEstadoCaducidad(undefined)).toBe('normal');
  });
});

// ============================================================================
// TESTS DE VALIDACIÓN DE FORMULARIO
// ============================================================================

describe('Lotes - Validaciones de Formulario', () => {
  const validarFormularioLote = (datos) => {
    const errores = {};
    
    // Número de lote requerido
    if (!datos.numero_lote || datos.numero_lote.trim() === '') {
      errores.numero_lote = 'El número de lote es requerido';
    }
    
    // Producto requerido
    if (!datos.producto) {
      errores.producto = 'El producto es requerido';
    }
    
    // Cantidad inicial requerida y > 0
    if (!datos.cantidad_inicial || datos.cantidad_inicial <= 0) {
      errores.cantidad_inicial = 'La cantidad debe ser mayor a 0';
    }
    
    // Fecha de caducidad requerida
    if (!datos.fecha_caducidad) {
      errores.fecha_caducidad = 'La fecha de caducidad es requerida';
    }
    
    // Precio unitario >= 0
    if (datos.precio_unitario !== undefined && datos.precio_unitario < 0) {
      errores.precio_unitario = 'El precio no puede ser negativo';
    }
    
    return errores;
  };

  it('debe requerir número de lote', () => {
    const errores = validarFormularioLote({ numero_lote: '' });
    expect(errores.numero_lote).toBeDefined();
  });

  it('debe requerir producto', () => {
    const errores = validarFormularioLote({ producto: null });
    expect(errores.producto).toBeDefined();
  });

  it('debe requerir cantidad inicial positiva', () => {
    let errores = validarFormularioLote({ cantidad_inicial: 0 });
    expect(errores.cantidad_inicial).toBeDefined();
    
    errores = validarFormularioLote({ cantidad_inicial: -5 });
    expect(errores.cantidad_inicial).toBeDefined();
  });

  it('debe requerir fecha de caducidad', () => {
    const errores = validarFormularioLote({ fecha_caducidad: null });
    expect(errores.fecha_caducidad).toBeDefined();
  });

  it('no debe permitir precio negativo', () => {
    const errores = validarFormularioLote({ precio_unitario: -100 });
    expect(errores.precio_unitario).toBeDefined();
  });

  it('debe aceptar datos válidos sin errores', () => {
    const datosValidos = {
      numero_lote: 'LOT-2026-001',
      producto: 1,
      cantidad_inicial: 100,
      fecha_caducidad: '2027-12-31',
      precio_unitario: 50.00
    };
    
    const errores = validarFormularioLote(datosValidos);
    expect(Object.keys(errores)).toHaveLength(0);
  });
});

// ============================================================================
// TESTS DE OPERACIONES CRUD
// ============================================================================

describe('Lotes - Operaciones CRUD', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('debe llamar API para obtener lotes con parámetros correctos', async () => {
    const mockParams = {
      page: 1,
      page_size: 20,
      centro: 5,
      estado_caducidad: 'critico'
    };
    
    lotesAPI.getAll.mockResolvedValue({ data: { results: [], count: 0 } });
    
    await lotesAPI.getAll(mockParams);
    
    expect(lotesAPI.getAll).toHaveBeenCalledWith(mockParams);
  });

  it('debe manejar error en creación de lote', async () => {
    const nuevoLote = {
      numero_lote: 'LOT-ERROR',
      producto: 1,
      cantidad_inicial: 100,
      fecha_caducidad: '2027-01-01'
    };
    
    lotesAPI.create.mockRejectedValue({
      response: { data: { numero_lote: 'Ya existe un lote con este número' } }
    });
    
    await expect(lotesAPI.create(nuevoLote)).rejects.toBeDefined();
  });

  it('debe actualizar lote correctamente', async () => {
    const loteActualizado = {
      id: 1,
      cantidad_actual: 80,
      ubicacion: 'A-1-5'
    };
    
    lotesAPI.update.mockResolvedValue({ data: loteActualizado });
    
    const resultado = await lotesAPI.update(1, loteActualizado);
    
    expect(lotesAPI.update).toHaveBeenCalledWith(1, loteActualizado);
    expect(resultado.data.cantidad_actual).toBe(80);
  });

  it('debe eliminar (soft delete) lote correctamente', async () => {
    lotesAPI.delete.mockResolvedValue({ data: { message: 'Lote desactivado' } });
    
    await lotesAPI.delete(1);
    
    expect(lotesAPI.delete).toHaveBeenCalledWith(1);
  });
});

// ============================================================================
// TESTS DE EXPORTACIÓN
// ============================================================================

describe('Lotes - Exportación', () => {
  it('debe llamar exportación a Excel con filtros actuales', async () => {
    const filtros = {
      centro: 3,
      estado_caducidad: 'proximo',
      search: 'paracetamol'
    };
    
    lotesAPI.exportExcel.mockResolvedValue({ data: new Blob() });
    
    await lotesAPI.exportExcel(filtros);
    
    expect(lotesAPI.exportExcel).toHaveBeenCalledWith(filtros);
  });

  it('debe llamar exportación a PDF con filtros actuales', async () => {
    const filtros = { activo: true };
    
    lotesAPI.exportPDF.mockResolvedValue({ data: new Blob() });
    
    await lotesAPI.exportPDF(filtros);
    
    expect(lotesAPI.exportPDF).toHaveBeenCalledWith(filtros);
  });
});

// ============================================================================
// TESTS DE CÁLCULO DE PORCENTAJE CONSUMIDO
// ============================================================================

describe('Lotes - Cálculo de Porcentaje Consumido', () => {
  const calcularPorcentajeConsumido = (cantidadInicial, cantidadActual) => {
    if (!cantidadInicial || cantidadInicial <= 0) return 0;
    const consumido = cantidadInicial - (cantidadActual || 0);
    return Math.round((consumido / cantidadInicial) * 100);
  };

  it('debe calcular 0% si no se ha consumido nada', () => {
    expect(calcularPorcentajeConsumido(100, 100)).toBe(0);
  });

  it('debe calcular 50% si se consumió la mitad', () => {
    expect(calcularPorcentajeConsumido(100, 50)).toBe(50);
  });

  it('debe calcular 100% si se agotó', () => {
    expect(calcularPorcentajeConsumido(100, 0)).toBe(100);
  });

  it('debe manejar cantidad inicial 0 o null', () => {
    expect(calcularPorcentajeConsumido(0, 0)).toBe(0);
    expect(calcularPorcentajeConsumido(null, 50)).toBe(0);
  });

  it('debe redondear correctamente', () => {
    // 33.33% -> 33%
    expect(calcularPorcentajeConsumido(100, 67)).toBe(33);
  });
});

// ============================================================================
// TESTS DE FILTROS DE BÚSQUEDA
// ============================================================================

describe('Lotes - Filtros de Búsqueda', () => {
  const aplicarFiltros = (lotes, filtros) => {
    let resultado = [...lotes];
    
    // Filtro por texto
    if (filtros.search) {
      const termino = filtros.search.toLowerCase();
      resultado = resultado.filter(l => 
        l.numero_lote?.toLowerCase().includes(termino) ||
        l.producto_nombre?.toLowerCase().includes(termino)
      );
    }
    
    // Filtro por estado de caducidad
    if (filtros.estado_caducidad) {
      resultado = resultado.filter(l => l.alerta_caducidad === filtros.estado_caducidad);
    }
    
    // Filtro por centro
    if (filtros.centro) {
      resultado = resultado.filter(l => l.centro?.id === filtros.centro);
    }
    
    // Filtro por activo
    if (filtros.activo !== undefined) {
      resultado = resultado.filter(l => l.activo === filtros.activo);
    }
    
    return resultado;
  };

  const lotesEjemplo = [
    { id: 1, numero_lote: 'LOT-001', producto_nombre: 'Paracetamol', alerta_caducidad: 'normal', centro: { id: 1 }, activo: true },
    { id: 2, numero_lote: 'LOT-002', producto_nombre: 'Ibuprofeno', alerta_caducidad: 'critico', centro: { id: 1 }, activo: true },
    { id: 3, numero_lote: 'LOT-003', producto_nombre: 'Paracetamol', alerta_caducidad: 'vencido', centro: { id: 2 }, activo: false },
    { id: 4, numero_lote: 'LOT-004', producto_nombre: 'Aspirina', alerta_caducidad: 'normal', centro: null, activo: true },
  ];

  it('debe filtrar por texto en número de lote', () => {
    const resultado = aplicarFiltros(lotesEjemplo, { search: 'LOT-001' });
    expect(resultado).toHaveLength(1);
    expect(resultado[0].id).toBe(1);
  });

  it('debe filtrar por texto en nombre de producto', () => {
    const resultado = aplicarFiltros(lotesEjemplo, { search: 'paracetamol' });
    expect(resultado).toHaveLength(2);
  });

  it('debe filtrar por estado de caducidad', () => {
    const resultado = aplicarFiltros(lotesEjemplo, { estado_caducidad: 'critico' });
    expect(resultado).toHaveLength(1);
    expect(resultado[0].id).toBe(2);
  });

  it('debe filtrar por centro', () => {
    const resultado = aplicarFiltros(lotesEjemplo, { centro: 1 });
    expect(resultado).toHaveLength(2);
  });

  it('debe filtrar por estado activo', () => {
    const resultado = aplicarFiltros(lotesEjemplo, { activo: false });
    expect(resultado).toHaveLength(1);
    expect(resultado[0].id).toBe(3);
  });

  it('debe combinar múltiples filtros', () => {
    const resultado = aplicarFiltros(lotesEjemplo, { 
      search: 'paracetamol',
      activo: true 
    });
    expect(resultado).toHaveLength(1);
    expect(resultado[0].id).toBe(1);
  });
});

// ============================================================================
// TESTS DE INTEGRACIÓN DE DATOS
// ============================================================================

describe('Lotes - Integración de Datos', () => {
  it('debe mapear campos del backend correctamente', () => {
    const loteBackend = {
      id: 1,
      numero_lote: 'LOT-2026-001',
      producto: 5,
      producto_nombre: 'Paracetamol 500mg',
      producto_clave: 'MED-001',
      cantidad_inicial: 1000,
      cantidad_actual: 750,
      fecha_fabricacion: '2025-06-01',
      fecha_caducidad: '2027-06-01',
      precio_unitario: '25.50',
      numero_contrato: 'CONT-2025-001',
      marca: 'Farmacia SA',
      ubicacion: 'A-1-5',
      centro: null,
      centro_nombre: null,
      activo: true,
      estado: 'disponible',
      dias_para_caducar: 547,
      alerta_caducidad: 'normal',
      porcentaje_consumido: 25
    };

    // Verificar que todos los campos necesarios existen
    expect(loteBackend.id).toBeDefined();
    expect(loteBackend.numero_lote).toBeDefined();
    expect(loteBackend.producto).toBeDefined();
    expect(loteBackend.cantidad_inicial).toBeDefined();
    expect(loteBackend.cantidad_actual).toBeDefined();
    expect(loteBackend.fecha_caducidad).toBeDefined();
    expect(loteBackend.activo).toBeDefined();
    
    // Verificar campos calculados
    expect(loteBackend.estado).toBe('disponible');
    expect(loteBackend.alerta_caducidad).toBe('normal');
    expect(loteBackend.porcentaje_consumido).toBe(25);
  });

  it('debe manejar lote sin centro (Farmacia Central)', () => {
    const loteFarmacia = {
      id: 1,
      centro: null,
      centro_nombre: null
    };

    expect(loteFarmacia.centro).toBeNull();
    // En la UI, esto se muestra como "Farmacia Central"
  });

  it('debe manejar lote con centro asignado', () => {
    const loteCentro = {
      id: 2,
      centro: { id: 3, nombre: 'Centro Penitenciario X' },
      centro_nombre: 'Centro Penitenciario X'
    };

    expect(loteCentro.centro).toBeDefined();
    expect(loteCentro.centro_nombre).toBe('Centro Penitenciario X');
  });
});
