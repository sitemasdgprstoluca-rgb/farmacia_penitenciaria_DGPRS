/**
 * useSubmitGuard — Previene double-submit / spam-clic en operaciones de escritura.
 *
 * PROBLEMA que resuelve:
 *   setState (setProcesando/setLoading) es ASÍNCRONO en React: si el usuario
 *   hace clic varias veces muy rápido, múltiples llamadas inician antes de que
 *   el estado actualice y deshabilite el botón.
 *
 * SOLUCIÓN:
 *   useRef es SINCRÓNICO. El flag isSubmittingRef.current se actualiza
 *   inmediatamente en el mismo tick de JS, bloqueando cualquier clic posterior
 *   antes de que React tenga tiempo de re-renderizar.
 *
 * BONUS — client_request_id:
 *   Genera un UUID por operación y lo mantiene estable entre re-renders.
 *   Enviarlo al backend permite idempotencia: si el mismo request llega 2 veces
 *   (red lenta + reintento), el backend devuelve el resultado ya creado en lugar
 *   de duplicar el movimiento.
 *   Se regenera automáticamente con resetRequestId() después de éxito o al
 *   descartar/resetear el formulario.
 *
 * USO:
 *   const { submitting, guard, getRequestId, resetRequestId } = useSubmitGuard();
 *
 *   const handleSubmit = () => guard(async () => {
 *     const payload = { ...data, client_request_id: getRequestId() };
 *     await api.post(payload);
 *     resetRequestId(); // Para la siguiente operación
 *   });
 *
 *   <button disabled={submitting} onClick={handleSubmit}>
 *     {submitting ? 'Procesando…' : 'Guardar'}
 *   </button>
 */
import { useRef, useState, useCallback } from 'react';

/**
 * Genera un ID único tipo UUID usando crypto.randomUUID() si está disponible,
 * con fallback para entornos/navegadores antiguos.
 */
const generateRequestId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  // Fallback manual (insecure pero suficiente para idempotencia de UI)
  return `${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 10).toUpperCase()}`;
};

/**
 * @returns {{
 *   submitting: boolean,
 *   guard: (fn: () => Promise<any>) => Promise<any>,
 *   getRequestId: () => string,
 *   resetRequestId: () => void,
 * }}
 */
export const useSubmitGuard = () => {
  // Ref sincrónico: bloqueo inmediato, no espera re-render
  const isSubmittingRef = useRef(false);
  // State: controla UI (disabled, spinner)
  const [submitting, setSubmitting] = useState(false);

  // requestId estable por operación — se reutiliza en reintentos, se regenera en reset
  const requestIdRef = useRef(generateRequestId());

  /** Devuelve el client_request_id actual */
  const getRequestId = useCallback(() => requestIdRef.current, []);

  /**
   * Regenera el client_request_id.
   * Llamar después de éxito o al descartar/limpiar el formulario.
   */
  const resetRequestId = useCallback(() => {
    requestIdRef.current = generateRequestId();
  }, []);

  /**
   * Envuelve la función asíncrona con el guard anti-doble-submit.
   * Si ya hay una operación en curso, ignora el clic silenciosamente.
   *
   * @param {() => Promise<any>} fn - Función async a ejecutar
   * @returns {Promise<any>}
   */
  const guard = useCallback(async (fn) => {
    // Verificación SINCRÓNICA - bloquea inmediatamente, antes de cualquier await
    if (isSubmittingRef.current) return;

    isSubmittingRef.current = true;
    setSubmitting(true);

    try {
      return await fn();
    } finally {
      isSubmittingRef.current = false;
      setSubmitting(false);
    }
  }, []);

  return { submitting, guard, getRequestId, resetRequestId };
};

export default useSubmitGuard;
