/**
 * @fileoverview Tests para TwoStepConfirmModal (ISS-SEC)
 * Verifica el componente de modal de confirmación en 2 pasos
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TwoStepConfirmModal from '../components/TwoStepConfirmModal';

describe('TwoStepConfirmModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: jest.fn(),
    onConfirm: jest.fn(),
    title: 'Confirmar Acción',
    message: '¿Está seguro de realizar esta acción?'
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Renderizado básico', () => {
    it('no debe renderizar cuando isOpen es false', () => {
      render(<TwoStepConfirmModal {...defaultProps} isOpen={false} />);
      
      expect(screen.queryByText('Confirmar Acción')).not.toBeInTheDocument();
    });

    it('debe renderizar cuando isOpen es true', () => {
      render(<TwoStepConfirmModal {...defaultProps} />);
      
      expect(screen.getByText('Confirmar Acción')).toBeInTheDocument();
      expect(screen.getByText('¿Está seguro de realizar esta acción?')).toBeInTheDocument();
    });

    it('debe mostrar botones de confirmar y cancelar', () => {
      render(<TwoStepConfirmModal {...defaultProps} />);
      
      expect(screen.getByText('Confirmar')).toBeInTheDocument();
      expect(screen.getByText('Cancelar')).toBeInTheDocument();
    });
  });

  describe('Información del item', () => {
    it('debe mostrar itemInfo cuando se proporciona', () => {
      const itemInfo = {
        'Nombre': 'Producto Test',
        'ID': '123',
        'Estado': 'Activo'
      };

      render(<TwoStepConfirmModal {...defaultProps} itemInfo={itemInfo} />);
      
      expect(screen.getByText('Nombre:')).toBeInTheDocument();
      expect(screen.getByText('Producto Test')).toBeInTheDocument();
      expect(screen.getByText('ID:')).toBeInTheDocument();
      expect(screen.getByText('123')).toBeInTheDocument();
    });
  });

  describe('Textos personalizados', () => {
    it('debe usar confirmText personalizado', () => {
      render(<TwoStepConfirmModal {...defaultProps} confirmText="Eliminar definitivamente" />);
      
      expect(screen.getByText('Eliminar definitivamente')).toBeInTheDocument();
    });

    it('debe usar cancelText personalizado', () => {
      render(<TwoStepConfirmModal {...defaultProps} cancelText="No, mantener" />);
      
      expect(screen.getByText('No, mantener')).toBeInTheDocument();
    });
  });

  describe('Modo crítico con frase de confirmación', () => {
    const criticalProps = {
      ...defaultProps,
      isCritical: true,
      confirmPhrase: 'ELIMINAR',
      message: 'Esta acción es irreversible'
    };

    it('debe mostrar input de confirmación en modo crítico', () => {
      render(<TwoStepConfirmModal {...criticalProps} />);
      
      expect(screen.getByPlaceholderText(/escriba ELIMINAR/i)).toBeInTheDocument();
    });

    it('debe deshabilitar botón confirmar si la frase no coincide', () => {
      render(<TwoStepConfirmModal {...criticalProps} />);
      
      const confirmButton = screen.getByRole('button', { name: /confirmar/i });
      expect(confirmButton).toBeDisabled();
    });

    it('debe habilitar botón cuando la frase coincide exactamente', async () => {
      const user = userEvent.setup();
      render(<TwoStepConfirmModal {...criticalProps} />);
      
      const input = screen.getByPlaceholderText(/escriba ELIMINAR/i);
      await user.type(input, 'ELIMINAR');
      
      const confirmButton = screen.getByRole('button', { name: /confirmar/i });
      expect(confirmButton).not.toBeDisabled();
    });

    it('debe mantener deshabilitado si la frase es incorrecta', async () => {
      const user = userEvent.setup();
      render(<TwoStepConfirmModal {...criticalProps} />);
      
      const input = screen.getByPlaceholderText(/escriba ELIMINAR/i);
      await user.type(input, 'eliminar'); // minúsculas
      
      const confirmButton = screen.getByRole('button', { name: /confirmar/i });
      expect(confirmButton).toBeDisabled();
    });

    it('debe mostrar advertencia visual en modo crítico', () => {
      render(<TwoStepConfirmModal {...criticalProps} />);
      
      // Verificar que hay indicadores de peligro (icono, color rojo, etc.)
      const warningElement = document.querySelector('.text-red-600, .bg-red-50, [class*="red"]');
      expect(warningElement).toBeInTheDocument();
    });
  });

  describe('Interacciones', () => {
    it('debe llamar onClose al hacer clic en Cancelar', async () => {
      const user = userEvent.setup();
      const onClose = jest.fn();
      
      render(<TwoStepConfirmModal {...defaultProps} onClose={onClose} />);
      
      await user.click(screen.getByText('Cancelar'));
      
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('debe llamar onConfirm al hacer clic en Confirmar', async () => {
      const user = userEvent.setup();
      const onConfirm = jest.fn();
      
      render(<TwoStepConfirmModal {...defaultProps} onConfirm={onConfirm} />);
      
      await user.click(screen.getByText('Confirmar'));
      
      expect(onConfirm).toHaveBeenCalledTimes(1);
    });

    it('debe llamar onClose al hacer clic fuera del modal', async () => {
      const user = userEvent.setup();
      const onClose = jest.fn();
      
      render(<TwoStepConfirmModal {...defaultProps} onClose={onClose} />);
      
      // Clic en el backdrop (el overlay)
      const backdrop = document.querySelector('.fixed.inset-0');
      if (backdrop) {
        await user.click(backdrop);
        expect(onClose).toHaveBeenCalled();
      }
    });
  });

  describe('Estado de carga', () => {
    it('debe mostrar indicador de carga cuando isLoading es true', () => {
      render(<TwoStepConfirmModal {...defaultProps} isLoading={true} />);
      
      // Verificar que hay un spinner o texto de cargando
      const loadingIndicator = screen.queryByText(/procesando|cargando/i) || 
                               document.querySelector('.animate-spin');
      expect(loadingIndicator).toBeInTheDocument();
    });

    it('debe deshabilitar botones durante la carga', () => {
      render(<TwoStepConfirmModal {...defaultProps} isLoading={true} />);
      
      const confirmButton = screen.getByRole('button', { name: /confirmar|procesando/i });
      const cancelButton = screen.getByRole('button', { name: /cancelar/i });
      
      expect(confirmButton).toBeDisabled();
      expect(cancelButton).toBeDisabled();
    });
  });

  describe('actionType', () => {
    it('debe mostrar estilos de eliminar para actionType="delete"', () => {
      render(<TwoStepConfirmModal {...defaultProps} actionType="delete" />);
      
      // Los botones de eliminar suelen tener clases rojas
      const confirmButton = screen.getByRole('button', { name: /confirmar|eliminar/i });
      expect(confirmButton.className).toMatch(/red|danger/i);
    });

    it('debe mostrar estilos de guardar para actionType="save"', () => {
      render(<TwoStepConfirmModal {...defaultProps} actionType="save" confirmText="Guardar" />);
      
      // Los botones de guardar suelen tener clases verdes o azules
      const confirmButton = screen.getByRole('button', { name: /guardar/i });
      expect(confirmButton.className).toMatch(/green|blue|primary/i);
    });
  });

  describe('Accesibilidad', () => {
    it('debe tener role="dialog"', () => {
      render(<TwoStepConfirmModal {...defaultProps} />);
      
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('debe enfocar el modal al abrirse', () => {
      render(<TwoStepConfirmModal {...defaultProps} />);
      
      const modal = screen.getByRole('dialog');
      expect(document.activeElement).toBe(modal) || 
        expect(modal.contains(document.activeElement)).toBe(true);
    });

    it('debe cerrar con tecla Escape', async () => {
      const user = userEvent.setup();
      const onClose = jest.fn();
      
      render(<TwoStepConfirmModal {...defaultProps} onClose={onClose} />);
      
      await user.keyboard('{Escape}');
      
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('summaryTitle', () => {
    it('debe mostrar summaryTitle cuando se proporciona', () => {
      render(
        <TwoStepConfirmModal 
          {...defaultProps} 
          summaryTitle="Resumen de la operación"
          itemInfo={{ campo: 'valor' }}
        />
      );
      
      expect(screen.getByText('Resumen de la operación')).toBeInTheDocument();
    });
  });

  describe('warnings', () => {
    it('debe mostrar advertencias cuando se proporcionan', () => {
      const warnings = [
        'Esta acción no se puede deshacer',
        'Los datos se perderán permanentemente'
      ];

      render(<TwoStepConfirmModal {...defaultProps} warnings={warnings} />);
      
      warnings.forEach(warning => {
        expect(screen.getByText(warning)).toBeInTheDocument();
      });
    });
  });
});
