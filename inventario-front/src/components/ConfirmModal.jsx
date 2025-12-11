import PropTypes from 'prop-types';

function ConfirmModal({
  open,
  title = "¿Estás seguro?",
  message = "",
  confirmText = "Confirmar",
  cancelText = "Cancelar",
  loading = false,
  onConfirm,
  onCancel,
  tone = "danger",
}) {
  if (!open) return null;

  const toneClasses = tone === "danger"
    ? "bg-red-600 hover:bg-red-700 focus:ring-red-500"
    : "bg-blue-600 hover:bg-blue-700 focus:ring-blue-500";

  // Clases de icono fijas para evitar purge de Tailwind
  const iconClasses = tone === "danger" 
    ? "mt-1 w-10 h-10 rounded-full flex items-center justify-center text-white font-bold bg-red-600"
    : "mt-1 w-10 h-10 rounded-full flex items-center justify-center text-white font-bold bg-blue-600";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/50" onClick={onCancel} />
      <div className="relative w-full max-w-lg bg-white rounded-lg shadow-xl p-6">
        <div className="flex items-start gap-3">
          <div className={iconClasses}>
            !
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            {message && <p className="mt-2 text-gray-600 text-sm">{message}</p>}
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 rounded border border-gray-200 text-gray-700 hover:bg-gray-50"
            disabled={loading}
          >
            {cancelText}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className={`px-4 py-2 rounded text-white ${toneClasses} disabled:opacity-60`}
            disabled={loading}
          >
            {loading ? "Procesando..." : confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

// FRONT-004: PropTypes para validación de props
ConfirmModal.propTypes = {
  open: PropTypes.bool.isRequired,
  title: PropTypes.string,
  message: PropTypes.oneOfType([PropTypes.string, PropTypes.node]),
  confirmText: PropTypes.string,
  cancelText: PropTypes.string,
  loading: PropTypes.bool,
  onConfirm: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired,
  tone: PropTypes.oneOf(['danger', 'info']),
};

export default ConfirmModal;

