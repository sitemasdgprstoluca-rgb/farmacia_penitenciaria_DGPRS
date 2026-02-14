/**
 * ISS-SEC: Hook para gestión de confirmación en 2 pasos
 * 
 * Proporciona un flujo de confirmación obligatorio para operaciones
 * de guardar y eliminar, cumpliendo con los requerimientos de seguridad.
 * 
 * Características:
 * - Confirmación en 2 pasos para todas las operaciones destructivas
 * - Soporte para confirmación con frase escrita (ej: "ELIMINAR")
 * - Integración con API que valida el flag 'confirmed'
 * - Prevención de acciones accidentales
 * 
 * @example
 * const {
 *   confirmState,
 *   requestSaveConfirmation,
 *   requestDeleteConfirmation,
 *   executeWithConfirmation,
 *   cancelConfirmation,
 *   isConfirming,
 * } = useConfirmation();
 */

import { useState, useCallback } from 'react';

/**
 * Tipos de operación que requieren confirmación
 */
export const CONFIRMATION_TYPES = {
  SAVE: 'save',
  DELETE: 'delete',
  DELETE_CRITICAL: 'delete_critical', // Requiere escribir frase
};

/**
 * Configuración por defecto para cada tipo de confirmación
 */
const DEFAULT_CONFIGS = {
  [CONFIRMATION_TYPES.SAVE]: {
    title: 'Confirmar Cambios',
    tone: 'info',
    confirmPhrase: null,
    confirmText: 'Guardar',
    cancelText: 'Cancelar',
    warnings: [],
  },
  [CONFIRMATION_TYPES.DELETE]: {
    title: 'Confirmar Eliminación',
    tone: 'danger',
    confirmPhrase: null,
    confirmText: 'Eliminar',
    cancelText: 'Cancelar',
    warnings: ['Esta acción no se puede deshacer fácilmente'],
  },
  [CONFIRMATION_TYPES.DELETE_CRITICAL]: {
    title: 'Confirmar Eliminación Permanente',
    tone: 'danger',
    confirmPhrase: 'ELIMINAR',
    confirmText: 'Eliminar Permanentemente',
    cancelText: 'Cancelar',
    warnings: [
      'Esta acción es IRREVERSIBLE',
      'Se eliminarán todos los datos asociados',
      'No se podrá recuperar la información',
    ],
  },
};

/**
 * Estado inicial del modal de confirmación
 */
const INITIAL_STATE = {
  isOpen: false,
  type: null,
  title: '',
  message: '',
  warnings: [],
  confirmText: '',
  cancelText: '',
  tone: 'warning',
  confirmPhrase: null,
  itemInfo: null,
  loading: false,
  pendingAction: null,
  actionData: null,
};

/**
 * Hook para gestionar confirmación en 2 pasos
 * 
 * @returns {Object} Estado y funciones para gestionar confirmaciones
 */
export function useConfirmation() {
  const [confirmState, setConfirmState] = useState(INITIAL_STATE);

  /**
   * Solicita confirmación para guardar cambios
   * 
   * @param {Object} options - Opciones de configuración
   * @param {string} options.message - Mensaje de confirmación
   * @param {string} options.title - Título del modal (opcional)
   * @param {Array<string>} options.warnings - Lista de advertencias (opcional)
   * @param {Object} options.itemInfo - Info del item a mostrar (opcional)
   * @param {Object} options.changes - Resumen de cambios (opcional)
   * @param {Function} options.onConfirm - Función a ejecutar al confirmar
   * @param {*} options.actionData - Datos adicionales para la acción
   */
  const requestSaveConfirmation = useCallback((options) => {
    const config = DEFAULT_CONFIGS[CONFIRMATION_TYPES.SAVE];
    
    // Generar mensaje de cambios si se proporcionan
    let message = options.message || '¿Deseas guardar estos cambios?';
    if (options.changes && typeof options.changes === 'object') {
      const changesList = Object.entries(options.changes)
        .map(([key, value]) => `• ${key}: ${value}`)
        .join('\n');
      message = `${message}\n\nCambios a aplicar:\n${changesList}`;
    }
    
    setConfirmState({
      isOpen: true,
      type: CONFIRMATION_TYPES.SAVE,
      title: options.title || config.title,
      message,
      warnings: options.warnings || config.warnings,
      confirmText: options.confirmText || config.confirmText,
      cancelText: options.cancelText || config.cancelText,
      tone: options.tone || config.tone,
      confirmPhrase: options.requirePhrase ? 'GUARDAR' : null,
      itemInfo: options.itemInfo || null,
      loading: false,
      pendingAction: options.onConfirm,
      actionData: options.actionData || null,
    });
  }, []);

  /**
   * Solicita confirmación para eliminar
   * 
   * @param {Object} options - Opciones de configuración
   * @param {string} options.message - Mensaje de confirmación
   * @param {string} options.title - Título del modal (opcional)
   * @param {Array<string>} options.warnings - Lista de advertencias (opcional)
   * @param {Object} options.itemInfo - Info del item a eliminar (opcional)
   * @param {boolean} options.isCritical - Si es eliminación crítica/irreversible
   * @param {string} options.confirmPhrase - Frase que debe escribir el usuario (opcional)
   * @param {Function} options.onConfirm - Función a ejecutar al confirmar
   * @param {*} options.actionData - Datos adicionales para la acción
   */
  const requestDeleteConfirmation = useCallback((options) => {
    const isCritical = options.isCritical === true;
    const baseConfig = isCritical 
      ? DEFAULT_CONFIGS[CONFIRMATION_TYPES.DELETE_CRITICAL]
      : DEFAULT_CONFIGS[CONFIRMATION_TYPES.DELETE];
    
    setConfirmState({
      isOpen: true,
      type: isCritical ? CONFIRMATION_TYPES.DELETE_CRITICAL : CONFIRMATION_TYPES.DELETE,
      title: options.title || baseConfig.title,
      message: options.message || '¿Está seguro de eliminar este elemento?',
      warnings: options.warnings || baseConfig.warnings,
      confirmText: options.confirmText || baseConfig.confirmText,
      cancelText: options.cancelText || baseConfig.cancelText,
      tone: options.tone || baseConfig.tone,
      confirmPhrase: options.confirmPhrase || baseConfig.confirmPhrase,
      itemInfo: options.itemInfo || null,
      loading: false,
      pendingAction: options.onConfirm,
      actionData: options.actionData || null,
    });
  }, []);

  /**
   * Ejecuta la acción pendiente con el flag de confirmación
   */
  const executeWithConfirmation = useCallback(async () => {
    if (!confirmState.pendingAction) {
      console.error('[useConfirmation] No hay acción pendiente para ejecutar');
      return;
    }

    setConfirmState(prev => ({ ...prev, loading: true }));

    try {
      // Ejecutar la acción con el flag de confirmación
      await confirmState.pendingAction({
        confirmed: true,
        actionData: confirmState.actionData,
      });
      
      // Cerrar modal después de éxito
      setConfirmState(INITIAL_STATE);
    } catch (error) {
      // En caso de error, mantener modal abierto pero quitar loading
      setConfirmState(prev => ({ ...prev, loading: false }));
      // Re-lanzar error para que el componente lo maneje
      throw error;
    }
  }, [confirmState.pendingAction, confirmState.actionData]);

  /**
   * Cancela la confirmación y cierra el modal
   */
  const cancelConfirmation = useCallback(() => {
    setConfirmState(INITIAL_STATE);
  }, []);

  /**
   * Resetea el estado de loading (útil si hay error)
   */
  const resetLoading = useCallback(() => {
    setConfirmState(prev => ({ ...prev, loading: false }));
  }, []);

  return {
    // Estado del modal
    confirmState,
    isConfirming: confirmState.isOpen,
    isLoading: confirmState.loading,
    
    // Funciones para solicitar confirmación
    requestSaveConfirmation,
    requestDeleteConfirmation,
    
    // Funciones para ejecutar/cancelar
    executeWithConfirmation,
    cancelConfirmation,
    resetLoading,
    
    // Tipos exportados para uso externo
    CONFIRMATION_TYPES,
  };
}

export default useConfirmation;
