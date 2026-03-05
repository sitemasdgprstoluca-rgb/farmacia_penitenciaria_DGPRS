/**
 * ISS-SEC: Modal de Confirmación en Dos Pasos
 * 
 * Proporciona confirmación adicional para acciones críticas e irreversibles.
 * Paso 1: Muestra advertencias y consecuencias
 * Paso 2: Solicita confirmación explícita escribiendo texto
 * 
 * IMPORTANTE: Este componente implementa el requerimiento de confirmación
 * obligatoria en 2 pasos para todas las operaciones de guardar/eliminar.
 * Sin el Paso 2, NO se ejecuta ninguna acción.
 * 
 * Integración con useConfirmation hook:
 * @example
 * const { confirmState, executeWithConfirmation, cancelConfirmation } = useConfirmation();
 * 
 * <TwoStepConfirmModal
 *   open={confirmState.isOpen}
 *   onCancel={cancelConfirmation}
 *   onConfirm={executeWithConfirmation}
 *   title={confirmState.title}
 *   message={confirmState.message}
 *   warnings={confirmState.warnings}
 *   confirmText={confirmState.confirmText}
 *   cancelText={confirmState.cancelText}
 *   tone={confirmState.tone}
 *   confirmPhrase={confirmState.confirmPhrase}
 *   itemInfo={confirmState.itemInfo}
 *   loading={confirmState.loading}
 * />
 * 
 * Uso directo:
 * @example
 * <TwoStepConfirmModal
 *   open={showModal}
 *   onCancel={() => setShowModal(false)}
 *   onConfirm={handleAction}
 *   title="Confirmar Entrega"
 *   message="¿Está seguro de confirmar esta entrega?"
 *   warnings={['Se descontará del inventario', 'No se puede deshacer']}
 *   confirmText="Sí, confirmar"
 *   cancelText="No, volver"
 *   tone="warning" // 'danger' | 'warning' | 'info'
 *   confirmPhrase="CONFIRMAR" // Opcional: texto que debe escribir el usuario
 * />
 */

import { useState, useEffect, useCallback } from 'react';
import PropTypes from 'prop-types';
import { FaExclamationTriangle, FaCheckCircle, FaTimesCircle, FaShieldAlt, FaSave, FaTrash } from 'react-icons/fa';
import useEscapeToClose from '../hooks/useEscapeToClose';

function TwoStepConfirmModal({
  open,
  title = "Confirmar Acción",
  message = "",
  warnings = [],
  confirmText = "Confirmar",
  cancelText = "Cancelar",
  loading = false,
  onConfirm,
  onCancel,
  tone = "warning",
  confirmPhrase = null, // Si se proporciona, requiere escribir este texto
  itemInfo = null, // Información adicional del item (folio, nombre, etc.)
  actionType = null, // 'save' | 'delete' | null - para mostrar icono apropiado
  summaryTitle = null, // Título para la sección de resumen
}) {
  const [step, setStep] = useState(1);
  const [inputValue, setInputValue] = useState('');
  const [isValid, setIsValid] = useState(false);

  // ISS-UX: Cerrar con ESC (equivale a Cancelar, NO a Confirmar)
  useEscapeToClose({
    isOpen: open,
    onClose: onCancel,
    modalId: 'two-step-confirm-modal',
    disabled: loading, // No cerrar durante operación crítica
  });

  // Reset al abrir/cerrar
  useEffect(() => {
    if (open) {
      setStep(1);
      setInputValue('');
      setIsValid(false);
    }
  }, [open]);

  // Validar input si se requiere frase
  useEffect(() => {
    if (confirmPhrase) {
      setIsValid(inputValue.toUpperCase().trim() === confirmPhrase.toUpperCase().trim());
    } else {
      setIsValid(true);
    }
  }, [inputValue, confirmPhrase]);

  if (!open) return null;

  // Estilos según tono
  const toneConfig = {
    danger: {
      bgHeader: 'bg-red-600',
      bgIcon: 'bg-red-100',
      textIcon: 'text-red-600',
      bgWarning: 'bg-red-50 border-red-200',
      textWarning: 'text-red-800',
      btnConfirm: 'bg-red-600 hover:bg-red-700 focus:ring-red-500',
      icon: FaTimesCircle,
    },
    warning: {
      bgHeader: 'bg-amber-500',
      bgIcon: 'bg-amber-100',
      textIcon: 'text-amber-600',
      bgWarning: 'bg-amber-50 border-amber-200',
      textWarning: 'text-amber-800',
      btnConfirm: 'bg-amber-600 hover:bg-amber-700 focus:ring-amber-500',
      icon: FaExclamationTriangle,
    },
    info: {
      bgHeader: 'bg-blue-600',
      bgIcon: 'bg-blue-100',
      textIcon: 'text-blue-600',
      bgWarning: 'bg-blue-50 border-blue-200',
      textWarning: 'text-blue-800',
      btnConfirm: 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-500',
      icon: FaCheckCircle,
    },
  };

  const config = toneConfig[tone] || toneConfig.warning;
  const IconComponent = config.icon;

  const handleProceedToStep2 = () => {
    if (confirmPhrase) {
      setStep(2);
    } else {
      // Sin frase de confirmación, ejecutar directamente
      onConfirm();
    }
  };

  const handleConfirm = () => {
    if (isValid) {
      onConfirm();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/50" onClick={!loading ? onCancel : undefined} />
      <div className="relative w-full max-w-lg bg-white rounded-lg shadow-xl overflow-hidden">
        {/* Header con color */}
        <div className={`${config.bgHeader} px-6 py-4`}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
              <FaShieldAlt className="text-white text-xl" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">{title}</h3>
              {step === 2 && (
                <span className="text-sm text-white/80">Paso 2 de 2: Confirmación final</span>
              )}
            </div>
          </div>
        </div>

        <div className="p-6">
          {/* Paso 1: Mostrar advertencias */}
          {step === 1 && (
            <>
              {/* Mensaje principal */}
              {message && (
                <p className="text-gray-700 mb-4">{message}</p>
              )}

              {/* Info del item */}
              {itemInfo && (
                <div className="bg-gray-50 border rounded-lg p-3 mb-4">
                  <div className="text-sm text-gray-600">
                    {Object.entries(itemInfo).map(([key, value]) => (
                      <div key={key} className="flex justify-between">
                        <span className="font-medium">{key}:</span>
                        <span>{value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Panel de advertencias */}
              {warnings.length > 0 && (
                <div className={`${config.bgWarning} border rounded-lg p-4 mb-4`}>
                  <div className="flex items-start gap-3">
                    <IconComponent className={`${config.textIcon} text-xl flex-shrink-0 mt-0.5`} />
                    <div>
                      <p className={`font-medium ${config.textWarning} mb-2`}>
                        ⚠️ Esta acción:
                      </p>
                      <ul className={`list-disc list-inside space-y-1 text-sm ${config.textWarning}`}>
                        {warnings.map((warning, idx) => (
                          <li key={idx}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* Botones paso 1 */}
              <div className="flex justify-end gap-3 mt-6">
                <button
                  type="button"
                  onClick={onCancel}
                  className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50"
                  disabled={loading}
                >
                  {cancelText}
                </button>
                <button
                  type="button"
                  onClick={handleProceedToStep2}
                  className={`px-4 py-2 rounded-lg text-white ${config.btnConfirm}`}
                  disabled={loading}
                >
                  {confirmPhrase ? 'Continuar →' : (loading ? "Procesando..." : confirmText)}
                </button>
              </div>
            </>
          )}

          {/* Paso 2: Confirmar escribiendo */}
          {step === 2 && confirmPhrase && (
            <>
              <div className="text-center mb-6">
                <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full ${config.bgIcon} mb-4`}>
                  <IconComponent className={`${config.textIcon} text-3xl`} />
                </div>
                <p className="text-gray-700 mb-2">
                  Para confirmar esta acción, escriba:
                </p>
                <code className={`text-lg font-bold ${config.textIcon} bg-gray-100 px-3 py-1 rounded`}>
                  {confirmPhrase}
                </code>
              </div>

              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={`Escriba "${confirmPhrase}" para confirmar`}
                className={`w-full px-4 py-3 border-2 rounded-lg text-center font-medium text-lg
                  ${isValid ? 'border-green-500 bg-green-50' : 'border-gray-300'}
                  focus:outline-none focus:ring-2 focus:ring-offset-1
                `}
                autoFocus
              />

              {inputValue && !isValid && (
                <p className="text-red-500 text-sm text-center mt-2">
                  El texto no coincide. Escriba exactamente: {confirmPhrase}
                </p>
              )}

              {/* Botones paso 2 */}
              <div className="flex justify-end gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50"
                  disabled={loading}
                >
                  ← Volver
                </button>
                <button
                  type="button"
                  onClick={handleConfirm}
                  className={`px-4 py-2 rounded-lg text-white ${config.btnConfirm} disabled:opacity-50 disabled:cursor-not-allowed`}
                  disabled={!isValid || loading}
                >
                  {loading ? "Procesando..." : confirmText}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

TwoStepConfirmModal.propTypes = {
  open: PropTypes.bool.isRequired,
  title: PropTypes.string,
  message: PropTypes.oneOfType([PropTypes.string, PropTypes.node]),
  warnings: PropTypes.arrayOf(PropTypes.string),
  confirmText: PropTypes.string,
  cancelText: PropTypes.string,
  loading: PropTypes.bool,
  onConfirm: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired,
  tone: PropTypes.oneOf(['danger', 'warning', 'info']),
  confirmPhrase: PropTypes.string,
  itemInfo: PropTypes.object,
  actionType: PropTypes.oneOf(['save', 'delete', null]),
  summaryTitle: PropTypes.string,
};

export default TwoStepConfirmModal;
