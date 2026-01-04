/**
 * Tests para RequisicionHistorial - Formato amigable de detalles adicionales
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import RequisicionHistorial from '../RequisicionHistorial';
import { requisicionesAPI } from '../../services/api';

// Mock del API
vi.mock('../../services/api', () => ({
  requisicionesAPI: {
    getHistorial: vi.fn()
  }
}));

describe('RequisicionHistorial', () => {
  const mockHistorial = {
    folio: 'TEST-001',
    estado_actual: 'pendiente_admin',
    total_cambios: 2,
    historial: [
      {
        id: 1,
        estado_anterior: 'borrador',
        estado_nuevo: 'pendiente_admin',
        accion_display: 'Enviar a Administrador',
        usuario: 'Juan Pérez',
        fecha_cambio: '2026-01-02T10:00:00Z',
        motivo: null,
        observaciones: null,
        datos_adicionales: {
          estado_nuevo: 'pendiente_admin',
          estado_anterior: 'borrador',
          updated_at: '2026-01-02T10:00:00+00:00',
          ip_address: '192.168.1.1',
          hash_verificacion: 'abc123xyz'
        }
      },
      {
        id: 2,
        estado_anterior: 'pendiente_admin',
        estado_nuevo: 'autorizada_admin',
        accion_display: 'Autorizar Admin',
        usuario: 'María García',
        fecha_cambio: '2026-01-03T14:30:00Z',
        motivo: 'Aprobado sin observaciones',
        observaciones: null,
        datos_adicionales: {
          cantidad_autorizada: 10,
          cantidad_solicitada: 15,
          total_autorizado: 50,
          fecha_recoleccion_limite: '2026-01-10T12:00:00+00:00'
        }
      }
    ]
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('debe renderizar el historial correctamente', async () => {
    requisicionesAPI.getHistorial.mockResolvedValue({ data: mockHistorial });

    render(<RequisicionHistorial requisicionId={1} isModal={false} />);

    await waitFor(() => {
      expect(screen.getByText('Historial de Cambios')).toBeInTheDocument();
    });

    expect(screen.getByText('(2 cambios)')).toBeInTheDocument();
  });

  it('debe mostrar el estado actual', async () => {
    requisicionesAPI.getHistorial.mockResolvedValue({ data: mockHistorial });

    render(<RequisicionHistorial requisicionId={1} isModal={false} />);

    await waitFor(() => {
      expect(screen.getByText('TEST-001')).toBeInTheDocument();
    });
  });

  it('debe mostrar detalles adicionales con formato amigable', async () => {
    requisicionesAPI.getHistorial.mockResolvedValue({ data: mockHistorial });

    render(<RequisicionHistorial requisicionId={1} isModal={false} />);

    await waitFor(() => {
      expect(screen.getByText('Historial de Cambios')).toBeInTheDocument();
    });

    // Buscar el botón de detalles adicionales y hacer clic
    const detallesButtons = screen.getAllByText('Ver detalles adicionales');
    expect(detallesButtons.length).toBeGreaterThan(0);

    // Expandir el primer detalle
    fireEvent.click(detallesButtons[0]);

    // Debe mostrar etiquetas amigables, no el JSON crudo
    await waitFor(() => {
      // Verifica que no se muestre JSON crudo
      expect(screen.queryByText('"updated_at"')).not.toBeInTheDocument();
      expect(screen.queryByText('"ip_address"')).not.toBeInTheDocument();
    });
  });

  it('debe excluir campos técnicos internos', async () => {
    requisicionesAPI.getHistorial.mockResolvedValue({ data: mockHistorial });

    render(<RequisicionHistorial requisicionId={1} isModal={false} />);

    await waitFor(() => {
      expect(screen.getByText('Historial de Cambios')).toBeInTheDocument();
    });

    const detallesButtons = screen.getAllByText('Ver detalles adicionales');
    fireEvent.click(detallesButtons[0]);

    // Campos técnicos NO deben aparecer
    expect(screen.queryByText('hash_verificacion')).not.toBeInTheDocument();
    expect(screen.queryByText('ip_address')).not.toBeInTheDocument();
    expect(screen.queryByText('user_agent')).not.toBeInTheDocument();
  });

  it('debe mostrar cantidades con etiquetas amigables', async () => {
    requisicionesAPI.getHistorial.mockResolvedValue({ data: mockHistorial });

    render(<RequisicionHistorial requisicionId={1} isModal={false} />);

    await waitFor(() => {
      expect(screen.getByText('Historial de Cambios')).toBeInTheDocument();
    });

    // Expandir el segundo evento que tiene cantidades
    const detallesButtons = screen.getAllByText('Ver detalles adicionales');
    if (detallesButtons.length > 1) {
      fireEvent.click(detallesButtons[1]);

      await waitFor(() => {
        // Debe mostrar etiquetas amigables para cantidades
        expect(screen.getByText('Cantidad autorizada:')).toBeInTheDocument();
        expect(screen.getByText('10')).toBeInTheDocument();
      });
    }
  });

  it('debe formatear fechas ISO correctamente', async () => {
    requisicionesAPI.getHistorial.mockResolvedValue({ data: mockHistorial });

    render(<RequisicionHistorial requisicionId={1} isModal={false} />);

    await waitFor(() => {
      expect(screen.getByText('Historial de Cambios')).toBeInTheDocument();
    });

    const detallesButtons = screen.getAllByText('Ver detalles adicionales');
    if (detallesButtons.length > 1) {
      fireEvent.click(detallesButtons[1]);

      await waitFor(() => {
        // Debe mostrar etiqueta amigable para fecha
        expect(screen.getByText('Fecha límite recolección:')).toBeInTheDocument();
        // La fecha debe estar formateada (no en formato ISO crudo)
        expect(screen.queryByText('2026-01-10T12:00:00+00:00')).not.toBeInTheDocument();
      });
    }
  });

  it('debe mostrar loading mientras carga', () => {
    requisicionesAPI.getHistorial.mockImplementation(() => new Promise(() => {}));

    render(<RequisicionHistorial requisicionId={1} isModal={false} />);

    // Debe mostrar spinner de carga (buscando por clase animate-spin)
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeTruthy();
  });

  it('debe mostrar error si falla la carga', async () => {
    requisicionesAPI.getHistorial.mockRejectedValue({
      response: { data: { error: 'Error de prueba' } }
    });

    render(<RequisicionHistorial requisicionId={1} isModal={false} />);

    await waitFor(() => {
      expect(screen.getByText('Error de prueba')).toBeInTheDocument();
    });
  });

  it('debe mostrar mensaje cuando no hay historial', async () => {
    requisicionesAPI.getHistorial.mockResolvedValue({
      data: {
        folio: 'TEST-002',
        estado_actual: 'borrador',
        total_cambios: 0,
        historial: []
      }
    });

    render(<RequisicionHistorial requisicionId={2} isModal={false} />);

    await waitFor(() => {
      expect(screen.getByText('No hay cambios registrados')).toBeInTheDocument();
    });
  });

  it('debe renderizar como modal cuando isModal=true', async () => {
    requisicionesAPI.getHistorial.mockResolvedValue({ data: mockHistorial });
    const mockOnClose = vi.fn();

    render(<RequisicionHistorial requisicionId={1} isModal={true} onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Historial de Cambios')).toBeInTheDocument();
    });

    // Debe tener el overlay del modal
    const overlay = document.querySelector('.fixed.inset-0');
    expect(overlay).toBeInTheDocument();
  });
});
