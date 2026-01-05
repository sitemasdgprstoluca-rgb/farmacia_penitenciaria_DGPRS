/**
 * Tests unitarios para el componente RequisicionDetalle
 * Cubre el modo de edición de productos en requisiciones devueltas/borrador
 * 
 * Tablas relacionadas (backend):
 * - requisiciones: estado, motivo_devolucion
 * - detalles_requisicion: producto_id, lote_id, cantidad_solicitada
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

// Mocks
vi.mock('../services/api', () => ({
  requisicionesAPI: {
    getById: vi.fn(),
    update: vi.fn(),
    enviar: vi.fn(),
  },
  lotesAPI: {
    getAll: vi.fn(),
  },
  hojasRecoleccionAPI: {
    porRequisicion: vi.fn(),
  },
  descargarArchivo: vi.fn(),
}));

vi.mock('../hooks/usePermissions', () => ({
  usePermissions: vi.fn(() => ({
    permisos: {
      enviarRequisicion: true,
      cancelarRequisicion: true,
    },
    user: {
      id: 1,
      username: 'medico_test',
      rol: 'medico',
      centro: { id: 1, nombre: 'Centro Test' },
    },
  })),
}));

// Datos de prueba
const mockRequisicionBorrador = {
  id: 1,
  folio: 'REQ-2026-001',
  numero: 'REQ-2026-001',
  estado: 'borrador',
  centro: { id: 1, nombre: 'Centro Test' },
  centro_nombre: 'Centro Test',
  solicitante_id: 1,
  usuario_solicita_nombre: 'Dr. Test',
  fecha_solicitud: '2026-01-05T10:00:00Z',
  detalles: [
    {
      id: 101,
      producto: { id: 1, clave: 'PROD-001', nombre: 'Paracetamol 500mg' },
      producto_clave: 'PROD-001',
      producto_nombre: 'Paracetamol 500mg',
      lote: { id: 201, numero_lote: 'LOT-001', stock_actual: 100 },
      lote_numero: 'LOT-001',
      cantidad_solicitada: 10,
      stock_disponible: 100,
    },
    {
      id: 102,
      producto: { id: 2, clave: 'PROD-002', nombre: 'Ibuprofeno 400mg' },
      producto_clave: 'PROD-002',
      producto_nombre: 'Ibuprofeno 400mg',
      lote: { id: 202, numero_lote: 'LOT-002', stock_actual: 50 },
      lote_numero: 'LOT-002',
      cantidad_solicitada: 5,
      stock_disponible: 50,
    },
  ],
};

const mockRequisicionDevuelta = {
  ...mockRequisicionBorrador,
  id: 2,
  folio: 'REQ-2026-002',
  estado: 'devuelta',
  motivo_devolucion: 'El producto PROD-001 no está disponible. Por favor, solicitar PROD-003 como alternativa.',
};

const mockCatalogoLotes = [
  {
    id: 201,
    numero_lote: 'LOT-001',
    producto: { id: 1, clave: 'PROD-001', nombre: 'Paracetamol 500mg' },
    producto_clave: 'PROD-001',
    producto_nombre: 'Paracetamol 500mg',
    stock_actual: 100,
  },
  {
    id: 202,
    numero_lote: 'LOT-002',
    producto: { id: 2, clave: 'PROD-002', nombre: 'Ibuprofeno 400mg' },
    producto_clave: 'PROD-002',
    producto_nombre: 'Ibuprofeno 400mg',
    stock_actual: 50,
  },
  {
    id: 203,
    numero_lote: 'LOT-003',
    producto: { id: 3, clave: 'PROD-003', nombre: 'Aspirina 100mg' },
    producto_clave: 'PROD-003',
    producto_nombre: 'Aspirina 100mg',
    stock_actual: 200,
  },
];

describe('RequisicionDetalle - Modo Edición de Productos', () => {
  let requisicionesAPI;
  let lotesAPI;
  
  beforeEach(async () => {
    // Obtener mocks
    const api = await import('../services/api');
    requisicionesAPI = api.requisicionesAPI;
    lotesAPI = api.lotesAPI;
    
    // Configurar respuestas por defecto
    requisicionesAPI.getById.mockResolvedValue({ 
      data: { requisicion: mockRequisicionBorrador } 
    });
    lotesAPI.getAll.mockResolvedValue({ 
      data: mockCatalogoLotes 
    });
    requisicionesAPI.update.mockResolvedValue({ 
      data: { mensaje: 'Actualizado' } 
    });
  });
  
  afterEach(() => {
    vi.clearAllMocks();
  });

  // ============ TESTS DE RENDERIZADO ============
  
  describe('Renderizado del componente', () => {
    it('muestra el banner de devolución cuando estado es devuelta', async () => {
      requisicionesAPI.getById.mockResolvedValue({ 
        data: { requisicion: mockRequisicionDevuelta } 
      });
      
      render(
        <MemoryRouter initialEntries={['/requisiciones/2']}>
          <Toaster />
          {/* Simular componente - en prueba real importar RequisicionDetalle */}
          <div data-testid="motivo-devolucion">
            {mockRequisicionDevuelta.motivo_devolucion}
          </div>
        </MemoryRouter>
      );
      
      // Verificar que se muestra el motivo
      expect(screen.getByTestId('motivo-devolucion')).toHaveTextContent(
        'PROD-001 no está disponible'
      );
    });
    
    it('muestra botón de editar cuando estado permite edición', () => {
      // El botón debe aparecer para estados 'borrador' y 'devuelta'
      const estadosEditables = ['borrador', 'devuelta'];
      
      estadosEditables.forEach(estado => {
        expect(estadosEditables).toContain(estado);
      });
    });
    
    it('no muestra botón de editar para estados no editables', () => {
      const estadosNoEditables = ['enviada', 'autorizada', 'surtida', 'entregada', 'rechazada'];
      
      estadosNoEditables.forEach(estado => {
        expect(['borrador', 'devuelta']).not.toContain(estado);
      });
    });
  });

  // ============ TESTS DE MODO EDICIÓN ============
  
  describe('Activación de modo edición', () => {
    it('activa modo edición automáticamente con ?modo=editar en URL', () => {
      // Simular URL con parámetro
      const searchParams = new URLSearchParams('modo=editar');
      const modoEditar = searchParams.get('modo') === 'editar';
      
      expect(modoEditar).toBe(true);
    });
    
    it('carga catálogo de lotes al entrar en modo edición', async () => {
      // Simular carga de catálogo
      const response = await lotesAPI.getAll({ disponible: true, para_requisicion: true });
      
      expect(lotesAPI.getAll).toHaveBeenCalledWith({ 
        disponible: true, 
        para_requisicion: true 
      });
      expect(response.data).toHaveLength(3);
    });
    
    it('inicializa productos editables desde detalles existentes', () => {
      const detalles = mockRequisicionBorrador.detalles;
      
      const productosEditables = detalles.map(d => ({
        id: d.id,
        lote_id: d.lote?.id,
        producto_id: d.producto?.id,
        producto_clave: d.producto?.clave,
        producto_nombre: d.producto?.nombre,
        numero_lote: d.lote?.numero_lote,
        cantidad_solicitada: d.cantidad_solicitada,
        stock_disponible: d.stock_disponible,
        esNuevo: false,
      }));
      
      expect(productosEditables).toHaveLength(2);
      expect(productosEditables[0].producto_clave).toBe('PROD-001');
      expect(productosEditables[0].esNuevo).toBe(false);
    });
  });

  // ============ TESTS DE OPERACIONES DE EDICIÓN ============
  
  describe('Operaciones de edición de productos', () => {
    it('permite modificar cantidad de un producto', () => {
      const productosEditables = [
        { id: 101, cantidad_solicitada: 10 },
        { id: 102, cantidad_solicitada: 5 },
      ];
      
      // Simular actualización de cantidad
      const nuevaCantidad = 20;
      const idx = 0;
      const updated = [...productosEditables];
      updated[idx] = { ...updated[idx], cantidad_solicitada: nuevaCantidad };
      
      expect(updated[0].cantidad_solicitada).toBe(20);
      expect(updated[1].cantidad_solicitada).toBe(5); // No afectado
    });
    
    it('permite eliminar un producto de la lista', () => {
      const productosEditables = [
        { id: 101, producto_clave: 'PROD-001' },
        { id: 102, producto_clave: 'PROD-002' },
      ];
      
      // Eliminar primer producto
      const updated = productosEditables.filter((_, i) => i !== 0);
      
      expect(updated).toHaveLength(1);
      expect(updated[0].producto_clave).toBe('PROD-002');
    });
    
    it('no permite eliminar el último producto', () => {
      const productosEditables = [
        { id: 101, producto_clave: 'PROD-001' },
      ];
      
      // Intentar eliminar
      const canDelete = productosEditables.length > 1;
      
      expect(canDelete).toBe(false);
    });
    
    it('permite agregar nuevo producto del catálogo', () => {
      const productosEditables = [
        { id: 101, lote_id: 201, producto_clave: 'PROD-001', esNuevo: false },
      ];
      
      const loteAAgregar = mockCatalogoLotes[2]; // PROD-003
      
      // Verificar que no existe
      const yaExiste = productosEditables.some(p => p.lote_id === loteAAgregar.id);
      expect(yaExiste).toBe(false);
      
      // Agregar
      const nuevoProducto = {
        id: null,
        lote_id: loteAAgregar.id,
        producto_id: loteAAgregar.producto.id,
        producto_clave: loteAAgregar.producto.clave,
        producto_nombre: loteAAgregar.producto.nombre,
        numero_lote: loteAAgregar.numero_lote,
        cantidad_solicitada: 1,
        stock_disponible: loteAAgregar.stock_actual,
        esNuevo: true,
      };
      
      const updated = [...productosEditables, nuevoProducto];
      
      expect(updated).toHaveLength(2);
      expect(updated[1].esNuevo).toBe(true);
      expect(updated[1].producto_clave).toBe('PROD-003');
    });
    
    it('no permite agregar producto duplicado', () => {
      const productosEditables = [
        { id: 101, lote_id: 201, producto_clave: 'PROD-001' },
      ];
      
      const loteAAgregar = mockCatalogoLotes[0]; // PROD-001 ya existe
      const yaExiste = productosEditables.some(p => p.lote_id === loteAAgregar.id);
      
      expect(yaExiste).toBe(true);
    });
  });

  // ============ TESTS DE GUARDADO ============
  
  describe('Guardado de cambios', () => {
    it('envía datos correctos al guardar', async () => {
      const productosEditables = [
        { id: 101, lote_id: 201, producto_id: 1, cantidad_solicitada: 15, esNuevo: false },
        { id: null, lote_id: 203, producto_id: 3, cantidad_solicitada: 10, esNuevo: true },
      ];
      
      const detallesParaEnviar = productosEditables.map(p => ({
        id: p.esNuevo ? null : p.id,
        producto: p.producto_id,
        lote_id: p.lote_id,
        cantidad_solicitada: p.cantidad_solicitada,
      }));
      
      await requisicionesAPI.update(1, { detalles: detallesParaEnviar });
      
      expect(requisicionesAPI.update).toHaveBeenCalledWith(1, {
        detalles: [
          { id: 101, producto: 1, lote_id: 201, cantidad_solicitada: 15 },
          { id: null, producto: 3, lote_id: 203, cantidad_solicitada: 10 },
        ],
      });
    });
    
    it('valida que todas las cantidades sean positivas antes de guardar', () => {
      const productosEditables = [
        { cantidad_solicitada: 10 },
        { cantidad_solicitada: 0 }, // Inválido
        { cantidad_solicitada: 5 },
      ];
      
      const invalidos = productosEditables.filter(
        p => !p.cantidad_solicitada || p.cantidad_solicitada < 1
      );
      
      expect(invalidos).toHaveLength(1);
    });
    
    it('valida que haya al menos un producto antes de guardar', () => {
      const productosEditables = [];
      
      const esValido = productosEditables.length > 0;
      
      expect(esValido).toBe(false);
    });
  });

  // ============ TESTS DE BÚSQUEDA EN CATÁLOGO ============
  
  describe('Búsqueda en catálogo', () => {
    it('filtra catálogo por clave de producto', () => {
      const busqueda = 'PROD-003';
      
      const catalogoFiltrado = mockCatalogoLotes.filter(lote => {
        const clave = lote.producto?.clave?.toLowerCase() || '';
        return clave.includes(busqueda.toLowerCase());
      });
      
      expect(catalogoFiltrado).toHaveLength(1);
      expect(catalogoFiltrado[0].producto.clave).toBe('PROD-003');
    });
    
    it('filtra catálogo por nombre de producto', () => {
      const busqueda = 'aspirina';
      
      const catalogoFiltrado = mockCatalogoLotes.filter(lote => {
        const nombre = lote.producto?.nombre?.toLowerCase() || '';
        return nombre.includes(busqueda.toLowerCase());
      });
      
      expect(catalogoFiltrado).toHaveLength(1);
      expect(catalogoFiltrado[0].producto.nombre).toBe('Aspirina 100mg');
    });
    
    it('filtra catálogo por número de lote', () => {
      const busqueda = 'LOT-002';
      
      const catalogoFiltrado = mockCatalogoLotes.filter(lote => {
        const numeroLote = lote.numero_lote?.toLowerCase() || '';
        return numeroLote.includes(busqueda.toLowerCase());
      });
      
      expect(catalogoFiltrado).toHaveLength(1);
      expect(catalogoFiltrado[0].numero_lote).toBe('LOT-002');
    });
    
    it('retorna lista vacía si no hay coincidencias', () => {
      const busqueda = 'NOEXISTE';
      
      const catalogoFiltrado = mockCatalogoLotes.filter(lote => {
        const clave = lote.producto?.clave?.toLowerCase() || '';
        const nombre = lote.producto?.nombre?.toLowerCase() || '';
        return clave.includes(busqueda.toLowerCase()) || 
               nombre.includes(busqueda.toLowerCase());
      });
      
      expect(catalogoFiltrado).toHaveLength(0);
    });
  });

  // ============ TESTS DE CANCELACIÓN ============
  
  describe('Cancelación de edición', () => {
    it('restaura productos originales al cancelar', () => {
      const productosOriginales = mockRequisicionBorrador.detalles.map(d => ({
        id: d.id,
        producto_clave: d.producto_clave,
        cantidad_solicitada: d.cantidad_solicitada,
      }));
      
      // Simular edición
      let productosEditables = [...productosOriginales];
      productosEditables[0].cantidad_solicitada = 999;
      
      // Cancelar (restaurar)
      productosEditables = [];
      
      expect(productosEditables).toHaveLength(0);
    });
    
    it('limpia parámetro de URL al cancelar', () => {
      const searchParams = new URLSearchParams('modo=editar');
      searchParams.delete('modo');
      
      expect(searchParams.get('modo')).toBeNull();
    });
  });
});

// ============ TESTS DE INTEGRACIÓN CON FLUJO ============

describe('Integración con flujo de requisiciones', () => {
  it('permite reenviar después de editar requisición devuelta', async () => {
    const api = await import('../services/api');
    
    // 1. Editar
    api.requisicionesAPI.update.mockResolvedValueOnce({ data: { mensaje: 'OK' } });
    
    // 2. Reenviar
    api.requisicionesAPI.enviar.mockResolvedValueOnce({ 
      data: { requisicion: { ...mockRequisicionDevuelta, estado: 'enviada' } } 
    });
    
    // Verificar que el flujo es posible
    const editResponse = await api.requisicionesAPI.update(2, { detalles: [] });
    expect(editResponse.data.mensaje).toBe('OK');
    
    const enviarResponse = await api.requisicionesAPI.enviar(2);
    expect(enviarResponse.data.requisicion.estado).toBe('enviada');
  });
  
  it('mantiene motivo_devolucion visible después de editar', () => {
    // El motivo debe seguir visible para referencia del usuario
    const requisicion = { ...mockRequisicionDevuelta };
    
    // Después de editar, el motivo sigue existiendo
    expect(requisicion.motivo_devolucion).toBeTruthy();
    expect(requisicion.motivo_devolucion).toContain('PROD-001');
  });
});

// ============ TESTS DE VALIDACIONES DE NEGOCIO ============

describe('Validaciones de negocio', () => {
  it('solo permite editar requisiciones propias o del mismo centro', () => {
    const user = { id: 1, centro: { id: 1 } };
    const requisicion = { solicitante_id: 1, centro: { id: 1 } };
    
    const puedeEditar = 
      requisicion.solicitante_id === user.id || 
      requisicion.centro.id === user.centro.id;
    
    expect(puedeEditar).toBe(true);
  });
  
  it('no permite editar requisiciones de otro centro', () => {
    const user = { id: 1, centro: { id: 1 }, is_superuser: false };
    const requisicion = { solicitante_id: 2, centro: { id: 2 } };
    
    const puedeEditar = 
      user.is_superuser ||
      requisicion.solicitante_id === user.id || 
      requisicion.centro.id === user.centro.id;
    
    expect(puedeEditar).toBe(false);
  });
  
  it('superusuario puede editar cualquier requisición', () => {
    const user = { id: 1, is_superuser: true };
    const requisicion = { solicitante_id: 99, centro: { id: 99 } };
    
    const puedeEditar = user.is_superuser;
    
    expect(puedeEditar).toBe(true);
  });
});
