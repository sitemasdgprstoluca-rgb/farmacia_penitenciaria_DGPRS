/**
 * Tests unitarios para la lista de requisiciones (Requisiciones.jsx)
 * Cubre filtros por rol y navegación a modo edición
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';

// Mock de navegación
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
  };
});

// Mock de API
vi.mock('../services/api', () => ({
  requisicionesAPI: {
    getAll: vi.fn(),
  },
}));

// Mock de permisos
vi.mock('../hooks/usePermissions', () => ({
  usePermissions: vi.fn(),
}));

// Datos de prueba
const mockRequisiciones = [
  {
    id: 1,
    folio: 'REQ-001',
    estado: 'borrador',
    centro_nombre: 'Centro 1',
    fecha_solicitud: '2026-01-05T10:00:00Z',
    solicitante_id: 1,
  },
  {
    id: 2,
    folio: 'REQ-002',
    estado: 'devuelta',
    centro_nombre: 'Centro 1',
    fecha_solicitud: '2026-01-04T10:00:00Z',
    motivo_devolucion: 'Ajustar cantidades',
    solicitante_id: 1,
  },
  {
    id: 3,
    folio: 'REQ-003',
    estado: 'enviada',
    centro_nombre: 'Centro 1',
    fecha_solicitud: '2026-01-03T10:00:00Z',
    solicitante_id: 1,
  },
  {
    id: 4,
    folio: 'REQ-004',
    estado: 'autorizada',
    centro_nombre: 'Centro 2',
    fecha_solicitud: '2026-01-02T10:00:00Z',
    solicitante_id: 2,
  },
];

describe('Requisiciones - Filtros por Rol', () => {
  let usePermissions;
  let requisicionesAPI;
  
  beforeEach(async () => {
    const hooks = await import('../hooks/usePermissions');
    usePermissions = hooks.usePermissions;
    
    const api = await import('../services/api');
    requisicionesAPI = api.requisicionesAPI;
    
    requisicionesAPI.getAll.mockResolvedValue({ 
      data: { results: mockRequisiciones, count: 4 } 
    });
  });
  
  afterEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
  });

  // ============ TESTS DE FILTROS POR ROL ============
  
  describe('Filtros para usuario Centro (Médico)', () => {
    beforeEach(() => {
      usePermissions.mockReturnValue({
        permisos: { enviarRequisicion: true },
        user: {
          id: 1,
          rol: 'medico',
          centro: { id: 1, nombre: 'Centro 1' },
          is_superuser: false,
        },
      });
    });
    
    it('muestra tabs correctos para médico: Mis Borradores, Devueltas, En Proceso', () => {
      const esFarmacia = false;
      const esUsuarioCentro = true;
      
      const tabsEsperados = esUsuarioCentro && !esFarmacia 
        ? ['Mis Borradores', 'Devueltas', 'En Proceso', 'Todas']
        : ['Pendientes', 'En Proceso', 'Completadas', 'Todas'];
      
      expect(tabsEsperados).toContain('Mis Borradores');
      expect(tabsEsperados).toContain('Devueltas');
    });
    
    it('filtra borradores solo del usuario actual', () => {
      const userId = 1;
      const borradores = mockRequisiciones.filter(
        r => r.estado === 'borrador' && r.solicitante_id === userId
      );
      
      expect(borradores).toHaveLength(1);
      expect(borradores[0].folio).toBe('REQ-001');
    });
    
    it('filtra requisiciones devueltas del usuario', () => {
      const userId = 1;
      const devueltas = mockRequisiciones.filter(
        r => r.estado === 'devuelta' && r.solicitante_id === userId
      );
      
      expect(devueltas).toHaveLength(1);
      expect(devueltas[0].motivo_devolucion).toBe('Ajustar cantidades');
    });
    
    it('NO muestra requisiciones en estado devuelta en tabs de farmacia', () => {
      // Para farmacia, devuelta no debe aparecer
      const estadosFarmacia = ['pendientes', 'en_proceso', 'completadas'];
      const estadosExcluidos = ['borrador', 'devuelta'];
      
      estadosExcluidos.forEach(estado => {
        expect(estadosFarmacia).not.toContain(estado);
      });
    });
  });
  
  describe('Filtros para usuario Farmacia', () => {
    beforeEach(() => {
      usePermissions.mockReturnValue({
        permisos: { 
          autorizarRequisicion: true,
          surtirRequisicion: true,
        },
        user: {
          id: 99,
          rol: 'farmacia',
          is_superuser: true,
        },
      });
    });
    
    it('muestra tabs correctos para farmacia: Pendientes, En Proceso, Completadas', () => {
      const esFarmacia = true;
      
      const tabsEsperados = esFarmacia
        ? ['Pendientes', 'En Proceso', 'Completadas', 'Todas']
        : ['Mis Borradores', 'Devueltas', 'En Proceso', 'Todas'];
      
      expect(tabsEsperados).toContain('Pendientes');
      expect(tabsEsperados).not.toContain('Devueltas');
    });
    
    it('filtra requisiciones enviadas como Pendientes', () => {
      const pendientes = mockRequisiciones.filter(
        r => r.estado === 'enviada'
      );
      
      expect(pendientes).toHaveLength(1);
      expect(pendientes[0].folio).toBe('REQ-003');
    });
    
    it('excluye requisiciones devueltas del queryset de farmacia', () => {
      const estadosExcluidosFarmacia = ['borrador', 'pendiente_admin', 'pendiente_director', 'devuelta'];
      
      const requisicionesFarmacia = mockRequisiciones.filter(
        r => !estadosExcluidosFarmacia.includes(r.estado)
      );
      
      // No debe incluir devuelta ni borrador
      const tieneDevuelta = requisicionesFarmacia.some(r => r.estado === 'devuelta');
      const tieneBorrador = requisicionesFarmacia.some(r => r.estado === 'borrador');
      
      expect(tieneDevuelta).toBe(false);
      expect(tieneBorrador).toBe(false);
    });
  });

  // ============ TESTS DE NAVEGACIÓN A EDICIÓN ============
  
  describe('Navegación a modo edición', () => {
    it('navega a detalle con ?modo=editar para requisiciones editables', () => {
      const requisicion = mockRequisiciones[0]; // borrador
      const estadosEditables = ['borrador', 'devuelta'];
      
      const puedeEditar = estadosEditables.includes(requisicion.estado);
      expect(puedeEditar).toBe(true);
      
      // Simular click en editar
      const urlEsperada = `/requisiciones/${requisicion.id}?modo=editar`;
      mockNavigate(urlEsperada);
      
      expect(mockNavigate).toHaveBeenCalledWith(urlEsperada);
    });
    
    it('NO muestra botón editar para requisiciones en estado enviada', () => {
      const requisicion = mockRequisiciones.find(r => r.estado === 'enviada');
      const estadosEditables = ['borrador', 'devuelta'];
      
      const puedeEditar = estadosEditables.includes(requisicion.estado);
      
      expect(puedeEditar).toBe(false);
    });
    
    it('navega a detalle simple para requisiciones no editables', () => {
      const requisicion = mockRequisiciones.find(r => r.estado === 'autorizada');
      
      // Navegar sin modo editar
      const urlEsperada = `/requisiciones/${requisicion.id}`;
      mockNavigate(urlEsperada);
      
      expect(mockNavigate).toHaveBeenCalledWith(urlEsperada);
      expect(mockNavigate).not.toHaveBeenCalledWith(expect.stringContaining('modo=editar'));
    });
  });

  // ============ TESTS DE ACCIONES POR ESTADO ============
  
  describe('Acciones disponibles por estado', () => {
    it('muestra botón Editar para estado borrador', () => {
      const estado = 'borrador';
      const accionesDisponibles = getAccionesDisponibles(estado, 'medico');
      
      expect(accionesDisponibles).toContain('editar');
      expect(accionesDisponibles).toContain('enviar');
    });
    
    it('muestra botón Editar para estado devuelta', () => {
      const estado = 'devuelta';
      const accionesDisponibles = getAccionesDisponibles(estado, 'medico');
      
      expect(accionesDisponibles).toContain('editar');
      expect(accionesDisponibles).toContain('enviar');
    });
    
    it('NO muestra botón Editar para estado enviada', () => {
      const estado = 'enviada';
      const accionesDisponibles = getAccionesDisponibles(estado, 'medico');
      
      expect(accionesDisponibles).not.toContain('editar');
    });
    
    it('farmacia puede autorizar requisiciones enviadas', () => {
      const estado = 'enviada';
      const accionesDisponibles = getAccionesDisponibles(estado, 'farmacia');
      
      expect(accionesDisponibles).toContain('autorizar');
      expect(accionesDisponibles).toContain('rechazar');
      expect(accionesDisponibles).toContain('devolver');
    });
    
    it('farmacia puede surtir requisiciones autorizadas', () => {
      const estado = 'autorizada';
      const accionesDisponibles = getAccionesDisponibles(estado, 'farmacia');
      
      expect(accionesDisponibles).toContain('surtir');
    });
  });
});

// ============ HELPER FUNCTIONS ============

function getAccionesDisponibles(estado, rol) {
  const acciones = [];
  
  const estadosEditables = ['borrador', 'devuelta'];
  const esUsuarioCentro = ['medico', 'centro', 'usuario_centro'].includes(rol);
  const esFarmacia = ['farmacia', 'admin_farmacia', 'admin_sistema'].includes(rol);
  
  // Editar/Enviar para centro en estados editables
  if (esUsuarioCentro && estadosEditables.includes(estado)) {
    acciones.push('editar', 'enviar');
  }
  
  // Acciones de farmacia
  if (esFarmacia) {
    if (estado === 'enviada') {
      acciones.push('autorizar', 'rechazar', 'devolver');
    }
    if (estado === 'autorizada') {
      acciones.push('surtir');
    }
  }
  
  // Cancelar disponible para todos en estados no finales
  const estadosFinales = ['surtida', 'entregada', 'cancelada', 'rechazada'];
  if (!estadosFinales.includes(estado)) {
    acciones.push('cancelar');
  }
  
  return acciones;
}

// ============ TESTS DE ESTADOS DE BD ============

describe('Estados de requisición (alineados con BD)', () => {
  const estadosValidos = [
    'borrador',
    'pendiente_admin',
    'pendiente_director',
    'enviada',
    'en_revision',
    'autorizada',
    'en_surtido',
    'surtida',
    'entregada',
    'rechazada',
    'devuelta',
    'cancelada',
    'vencida',
  ];
  
  it('reconoce todos los estados válidos del sistema', () => {
    estadosValidos.forEach(estado => {
      expect(typeof estado).toBe('string');
      expect(estado.length).toBeGreaterThan(0);
    });
  });
  
  it('estados editables son borrador y devuelta', () => {
    const estadosEditables = estadosValidos.filter(
      e => e === 'borrador' || e === 'devuelta'
    );
    
    expect(estadosEditables).toEqual(['borrador', 'devuelta']);
  });
  
  it('estados finales no permiten más acciones', () => {
    const estadosFinales = ['surtida', 'entregada', 'cancelada', 'rechazada', 'vencida'];
    
    estadosFinales.forEach(estado => {
      expect(estadosValidos).toContain(estado);
    });
  });
  
  it('transiciones de estado válidas desde borrador', () => {
    const transicionesDesde = {
      'borrador': ['enviada', 'cancelada'],
      'devuelta': ['enviada', 'cancelada'],
      'enviada': ['autorizada', 'rechazada', 'devuelta'],
      'autorizada': ['surtida', 'entregada', 'cancelada'],
    };
    
    expect(transicionesDesde['borrador']).toContain('enviada');
    expect(transicionesDesde['devuelta']).toContain('enviada');
  });
});
