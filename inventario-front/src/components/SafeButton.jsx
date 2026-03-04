/**
 * SafeButton — Botón transversal anti-doble-submit para todas las acciones de escritura.
 *
 * Características:
 *  • Se deshabilita automáticamente mientras `loading` es true
 *  • Muestra spinner + texto "Procesando…" (o `loadingText` custom)
 *  • Bloquea Enter repetido en formularios (onKeyDown guard)
 *  • Previene submit duplicado con debounce local (complementa useSafeAction)
 *  • Accesible: aria-busy, aria-disabled, foco no perdido durante carga
 *  • 100% compatible con botones de tipo "submit" dentro de <form>
 *
 * Props:
 *  @param {boolean}  loading       - Si true, deshabilita y muestra spinner
 *  @param {boolean}  disabled      - Deshabilita adicional (permiso, validación, etc.)
 *  @param {Function} onClick       - Handler de click (puede ser async)
 *  @param {string}   loadingText   - Texto mientras loading (default: "Procesando...")
 *  @param {string}   type          - "button" | "submit" | "reset" (default: "button")
 *  @param {string}   className     - Clases Tailwind adicionales
 *  @param {node}     children      - Contenido del botón (ícono + texto)
 *  @param {...any}   rest          - Cualquier otro prop HTML válido para <button>
 *
 * Uso:
 *   <SafeButton
 *     loading={isLoading}
 *     onClick={handleGuardar}
 *     loadingText="Guardando..."
 *     className="btn-primary"
 *   >
 *     <FaSave /> Guardar
 *   </SafeButton>
 */
import React, { useRef, useCallback } from 'react';
import { FaSpinner } from 'react-icons/fa';

const DEBOUNCE_MS = 300; // Protección adicional interna (junto con useSafeAction)

const SafeButton = ({
  loading = false,
  disabled = false,
  onClick,
  loadingText = 'Procesando...',
  type = 'button',
  className = '',
  children,
  ...rest
}) => {
  const lastClickRef = useRef(0);

  const handleClick = useCallback((e) => {
    if (loading || disabled) {
      e.preventDefault();
      return;
    }
    // Debounce interno: ignora clicks < DEBOUNCE_MS
    const now = Date.now();
    if (now - lastClickRef.current < DEBOUNCE_MS) {
      e.preventDefault();
      return;
    }
    lastClickRef.current = now;
    onClick?.(e);
  }, [loading, disabled, onClick]);

  const handleKeyDown = useCallback((e) => {
    // Bloquear Enter repetido (autorepeat cuando se mantiene presionado)
    if (e.key === 'Enter' && e.repeat) {
      e.preventDefault();
    }
    // Bloquear si ya está en vuelo
    if ((e.key === 'Enter' || e.key === ' ') && (loading || disabled)) {
      e.preventDefault();
    }
  }, [loading, disabled]);

  const isDisabled = loading || disabled;

  return (
    <button
      type={type}
      disabled={isDisabled}
      aria-busy={loading}
      aria-disabled={isDisabled}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={`inline-flex items-center gap-2 transition-opacity ${
        isDisabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'
      } ${className}`}
      {...rest}
    >
      {loading ? (
        <>
          <FaSpinner className="animate-spin flex-shrink-0" aria-hidden="true" />
          <span>{loadingText}</span>
        </>
      ) : (
        children
      )}
    </button>
  );
};

export default SafeButton;
