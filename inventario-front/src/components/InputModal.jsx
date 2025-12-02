import { useState, useEffect, useRef } from 'react';

/**
 * Modal con campo de entrada de texto.
 * Útil para solicitar motivos de rechazo, cancelación, etc.
 */
function InputModal({
  open,
  title = "Ingrese información",
  message = "",
  placeholder = "Escriba aquí...",
  confirmText = "Confirmar",
  cancelText = "Cancelar",
  loading = false,
  minLength = 0,
  maxLength = 500,
  multiline = true,
  onConfirm,
  onCancel,
  tone = "danger",
}) {
  const [inputValue, setInputValue] = useState('');
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  // Limpiar al abrir/cerrar
  useEffect(() => {
    if (open) {
      setInputValue('');
      setError('');
      // Focus en el input al abrir
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open]);

  if (!open) return null;

  const toneClasses = tone === "danger"
    ? "bg-red-600 hover:bg-red-700 focus:ring-red-500"
    : "bg-blue-600 hover:bg-blue-700 focus:ring-blue-500";

  const iconClasses = tone === "danger" 
    ? "mt-1 w-10 h-10 rounded-full flex items-center justify-center text-white font-bold bg-red-600"
    : "mt-1 w-10 h-10 rounded-full flex items-center justify-center text-white font-bold bg-blue-600";

  const handleConfirm = () => {
    const trimmed = inputValue.trim();
    
    if (minLength > 0 && trimmed.length < minLength) {
      setError(`Debe ingresar al menos ${minLength} caracteres`);
      return;
    }
    
    setError('');
    onConfirm(trimmed);
  };

  const handleKeyDown = (e) => {
    // Enter sin shift confirma en single-line
    if (e.key === 'Enter' && !multiline && !e.shiftKey) {
      e.preventDefault();
      handleConfirm();
    }
    // Escape cancela
    if (e.key === 'Escape') {
      onCancel();
    }
  };

  const InputComponent = multiline ? 'textarea' : 'input';

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
        
        <div className="mt-4">
          <InputComponent
            ref={inputRef}
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              if (error) setError('');
            }}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            maxLength={maxLength}
            rows={multiline ? 3 : undefined}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:outline-none ${
              error 
                ? 'border-red-500 focus:ring-red-200' 
                : 'border-gray-300 focus:ring-blue-200 focus:border-blue-500'
            }`}
          />
          {error && (
            <p className="mt-1 text-sm text-red-600">{error}</p>
          )}
          <p className="mt-1 text-xs text-gray-400 text-right">
            {inputValue.length}/{maxLength} caracteres
            {minLength > 0 && ` (mín. ${minLength})`}
          </p>
        </div>

        <div className="mt-4 flex justify-end gap-3">
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
            onClick={handleConfirm}
            className={`px-4 py-2 rounded text-white ${toneClasses} disabled:opacity-60`}
            disabled={loading || (minLength > 0 && inputValue.trim().length < minLength)}
          >
            {loading ? "Procesando..." : confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

export default InputModal;
