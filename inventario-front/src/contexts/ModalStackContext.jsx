/**
 * ModalStackContext - Gestor de Pila de Modales
 * 
 * PROPÓSITO:
 * Mantiene una pila (stack) de todos los overlays/modales abiertos
 * para implementar correctamente el comportamiento de ESC:
 * - Solo cierra el modal "más arriba" (último en abrir)
 * - Respeta jerarquías y modales anidados
 * - LIFO (Last In, First Out)
 * 
 * INTEGRACIÓN:
 * 1. Envolver la app con <ModalStackProvider>
 * 2. Cada modal registra su ID al abrirse con registerModal()
 * 3. Al cerrarse, se desregistra con unregisterModal()
 * 4. useEscapeToClose consulta isTopModal() antes de cerrar
 * 
 * @module contexts/ModalStackContext
 */

import { createContext, useContext, useState, useCallback, useRef } from 'react';
import PropTypes from 'prop-types';

const ModalStackContext = createContext(null);

export const useModalStack = () => {
  const context = useContext(ModalStackContext);
  if (!context) {
    throw new Error('useModalStack debe usarse dentro de ModalStackProvider');
  }
  return context;
};

export const ModalStackProvider = ({ children }) => {
  // Stack de IDs de modales (array de strings)
  const [stack, setStack] = useState([]);
  const stackRef = useRef([]);

  /**
   * Registra un modal al abrirse
   * @param {string} modalId - ID único del modal
   */
  const registerModal = useCallback((modalId) => {
    setStack((current) => {
      // Evitar duplicados (por si acaso)
      if (current.includes(modalId)) {
        console.warn(`[ModalStack] Modal ${modalId} ya registrado`);
        return current;
      }
      const newStack = [...current, modalId];
      stackRef.current = newStack;
      return newStack;
    });
  }, []);

  /**
   * Desregistra un modal al cerrarse
   * @param {string} modalId - ID único del modal
   */
  const unregisterModal = useCallback((modalId) => {
    setStack((current) => {
      const newStack = current.filter((id) => id !== modalId);
      stackRef.current = newStack;
      return newStack;
    });
  }, []);

  /**
   * Verifica si un modal es el más alto de la pila (top)
   * @param {string} modalId - ID del modal a verificar
   * @returns {boolean} true si es el top modal
   */
  const isTopModal = useCallback((modalId) => {
    const currentStack = stackRef.current;
    return currentStack.length > 0 && currentStack[currentStack.length - 1] === modalId;
  }, []);

  /**
   * Obtiene el ID del modal superior actual
   * @returns {string|null} ID del modal top o null si no hay modales
   */
  const getTopModal = useCallback(() => {
    const currentStack = stackRef.current;
    return currentStack.length > 0 ? currentStack[currentStack.length - 1] : null;
  }, []);

  /**
   * Limpia la pila (emergencia - normalmente no se usa)
   */
  const clearStack = useCallback(() => {
    setStack([]);
    stackRef.current = [];
  }, []);

  const value = {
    stack,
    registerModal,
    unregisterModal,
    isTopModal,
    getTopModal,
    clearStack,
  };

  return (
    <ModalStackContext.Provider value={value}>
      {children}
    </ModalStackContext.Provider>
  );
};

ModalStackProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export default ModalStackContext;
