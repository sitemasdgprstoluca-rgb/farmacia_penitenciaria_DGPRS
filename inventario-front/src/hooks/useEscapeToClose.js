/**
 * useEscapeToClose Hook
 * 
 * PROPÓSITO:
 * Hook centralizado para implementar cierre con tecla ESC en overlays/modales.
 * 
 * COMPORTAMIENTO:
 * 1. Solo cierra el modal superior (top de la pila)
 * 2. Respeta estados de loading (no cierra durante operaciones críticas)
 * 3. En modales de confirmación, ESC = Cancelar (onCancel, no onConfirm)
 * 4. Limpia listeners correctamente (no memory leaks)
 * 5. Compatible con inputs (foco puede estar en un campo)
 * 
 * INTEGRACIÓN:
 * @example
 * const MyModal = ({ open, onClose }) => {
 *   useEscapeToClose({
 *     isOpen: open,
 *     onClose: onClose,
 *     modalId: 'my-modal',
 *     disabled: false, // Opcional: deshabilitar ESC temporalmente
 *   });
 *   
 *   if (!open) return null;
 *   return <div>...</div>;
 * };
 * 
 * @module hooks/useEscapeToClose
 */

import { useEffect, useRef } from 'react';
import { useModalStack } from '../contexts/ModalStackContext';

/**
 * Hook para implementar cierre con ESC
 * 
 * @param {Object} options - Configuración del hook
 * @param {boolean} options.isOpen - Si el modal está abierto
 * @param {Function} options.onClose - Callback para cerrar (equivale a Cancelar)
 * @param {string} options.modalId - ID único del modal (para pila)
 * @param {boolean} [options.disabled=false] - Si true, ESC no cierra (útil durante loading)
 * @param {boolean} [options.ignoreStack=false] - Si true, no usa la pila (para casos legacy)
 */
const useEscapeToClose = ({
  isOpen,
  onClose,
  modalId,
  disabled = false,
  ignoreStack = false,
}) => {
  const { registerModal, unregisterModal, isTopModal } = useModalStack();
  const listenerAttached = useRef(false);

  // Registrar/desregistrar del stack cuando abre/cierra
  useEffect(() => {
    if (isOpen && !ignoreStack) {
      registerModal(modalId);
      return () => {
        unregisterModal(modalId);
      };
    }
  }, [isOpen, modalId, registerModal, unregisterModal, ignoreStack]);

  // Listener de teclado
  useEffect(() => {
    if (!isOpen) {
      listenerAttached.current = false;
      return;
    }

    const handleEscape = (event) => {
      // Solo procesar si es tecla Escape
      if (event.key !== 'Escape') return;

      // Verificar si ESC está deshabilitado (ej. durante loading)
      if (disabled) {
        // Opcional: mostrar feedback visual que no se puede cerrar
        console.debug(`[useEscapeToClose] ESC deshabilitado en ${modalId}`);
        return;
      }

      // Si no ignoramos el stack, verificar que somos el modal superior
      if (!ignoreStack && !isTopModal(modalId)) {
        console.debug(`[useEscapeToClose] ${modalId} no es top modal, ignorando ESC`);
        return;
      }

      // Prevenir comportamiento por defecto del navegador
      event.preventDefault();
      event.stopPropagation();

      // IMPORTANTE: onClose equivale a CANCELAR (no confirmar)
      // En modales de confirmación, esto NO ejecuta la acción
      onClose();
    };

    // Usar keydown (no keyup) para mejor UX
    document.addEventListener('keydown', handleEscape, true);
    listenerAttached.current = true;

    // Cleanup para evitar memory leaks
    return () => {
      document.removeEventListener('keydown', handleEscape, true);
      listenerAttached.current = false;
    };
  }, [isOpen, onClose, disabled, modalId, isTopModal, ignoreStack]);

  // Retornar estado actual (útil para debugging)
  return {
    isRegistered: isOpen && !ignoreStack,
    isListening: listenerAttached.current,
    modalId,
  };
};

export default useEscapeToClose;
