/**
 * FLUJO V2: Modal para asignar fecha límite de recolección
 * 
 * Cuando farmacia autoriza una requisición, debe asignar
 * una fecha límite para que el centro recoja los productos.
 * Si pasa esta fecha sin recolección, la requisición se marca como vencida.
 */

import { useState } from 'react';
import { FaCalendarAlt, FaTimes, FaExclamationTriangle } from 'react-icons/fa';

/**
 * Calcula la fecha mínima (mañana)
 */
const getFechaMinima = () => {
  const manana = new Date();
  manana.setDate(manana.getDate() + 1);
  return manana.toISOString().split('T')[0];
};

/**
 * Calcula la fecha máxima (30 días desde hoy)
 */
const getFechaMaxima = () => {
  const max = new Date();
  max.setDate(max.getDate() + 30);
  return max.toISOString().split('T')[0];
};

/**
 * Modal para seleccionar fecha límite de recolección
 */
export function FechaRecoleccionModal({
  isOpen,
  onClose,
  onConfirm,
  folio,
  loading = false,
}) {
  const [fechaLimite, setFechaLimite] = useState('');
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    if (!fechaLimite) {
      setError('La fecha límite es obligatoria');
      return;
    }

    const fecha = new Date(fechaLimite);
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);

    if (fecha <= hoy) {
      setError('La fecha debe ser posterior a hoy');
      return;
    }

    const maxFecha = new Date();
    maxFecha.setDate(maxFecha.getDate() + 30);
    if (fecha > maxFecha) {
      setError('La fecha no puede ser mayor a 30 días');
      return;
    }

    onConfirm(fechaLimite);
  };

  const handleClose = () => {
    setFechaLimite('');
    setError('');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <FaCalendarAlt className="text-blue-600 text-xl" />
            <h3 className="text-lg font-semibold text-gray-900">
              Fecha Límite de Recolección
            </h3>
          </div>
          <button
            type="button"
            onClick={handleClose}
            disabled={loading}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <FaTimes size={20} />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-4">
          {folio && (
            <p className="text-sm text-gray-600 mb-4">
              Requisición: <span className="font-semibold">{folio}</span>
            </p>
          )}

          <div className="mb-4">
            <label 
              htmlFor="fechaLimite" 
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Fecha límite para recoger los productos
            </label>
            <input
              type="date"
              id="fechaLimite"
              value={fechaLimite}
              onChange={(e) => {
                setFechaLimite(e.target.value);
                setError('');
              }}
              min={getFechaMinima()}
              max={getFechaMaxima()}
              disabled={loading}
              className={`
                w-full px-3 py-2 border rounded-lg
                focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                disabled:bg-gray-100 disabled:cursor-not-allowed
                ${error ? 'border-red-300' : 'border-gray-300'}
              `}
            />
            {error && (
              <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                <FaExclamationTriangle size={12} />
                {error}
              </p>
            )}
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
            <p className="text-sm text-amber-800">
              <FaExclamationTriangle className="inline mr-1" />
              <strong>Importante:</strong> Si la requisición no es recogida 
              antes de esta fecha, será marcada automáticamente como <strong>vencida</strong>.
            </p>
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              disabled={loading}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading || !fechaLimite}
              className="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {loading ? (
                <>
                  <span className="animate-spin">⏳</span>
                  Procesando...
                </>
              ) : (
                <>
                  <FaCalendarAlt />
                  Confirmar Fecha
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default FechaRecoleccionModal;
