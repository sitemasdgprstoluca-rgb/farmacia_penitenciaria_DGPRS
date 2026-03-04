/**
 * useSafeAction — Hook transversal anti-doble-submit para todas las acciones de escritura.
 *
 * Características:
 *  • Bloqueo sincrónico via useRef → captura el 2º click ANTES del siguiente render
 *  • Throttle de 800ms → aunque useRef fuera burlado (Enter repetido), el throttle bloquea
 *  • client_request_id (UUID v4) único por operación → idempotencia end-to-end con backend
 *  • resetRequestId() → genera nuevo ID después de operación exitosa
 *  • isLoading → estado React para UI (disabled, spinner)
 *
 * Uso básico:
 *   const { isLoading, guard, getRequestId, resetRequestId } = useSafeAction();
 *   const handleSave = () => guard(async () => {
 *     await api.create({ ...data, client_request_id: getRequestId() });
 *     resetRequestId(); // ← generar nuevo ID para la próxima operación
 *   });
 *
 * Uso con SafeButton:
 *   <SafeButton loading={isLoading} onClick={handleSave}>Guardar</SafeButton>
 */
import { useState, useRef, useCallback } from 'react';

// Genera UUID v4 — crypto.randomUUID() nativo (Chrome 92+, Firefox 95+, Node 16.7+)
// Fallback manual para entornos sin crypto.randomUUID
const generateRequestId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  // Fallback: RFC 4122 UUID v4 manual
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
};

// Throttle mínimo entre invocaciones permitidas (ms)
const THROTTLE_MS = 800;

export const useSafeAction = () => {
  // Bloqueo sincrónico — no depende de re-renders de React
  const isInflightRef = useRef(false);
  // Timestamp del último inicio permitido (para throttle)
  const lastStartRef = useRef(0);
  // Identificador único de operación — enviado al backend para idempotencia
  const requestIdRef = useRef(generateRequestId());

  // Estado React — solo para UI (disabled, spinner)
  const [isLoading, setIsLoading] = useState(false);

  /** Ejecuta `fn` con protección anti-doble-submit + throttle */
  const guard = useCallback(async (fn) => {
    const now = Date.now();

    // 1. Bloqueo sincrónico (captura doble click en el mismo frame)
    if (isInflightRef.current) return;

    // 2. Throttle: mínimo THROTTLE_MS entre operaciones
    if (now - lastStartRef.current < THROTTLE_MS) return;

    isInflightRef.current = true;
    lastStartRef.current = now;
    setIsLoading(true);

    try {
      return await fn();
    } finally {
      isInflightRef.current = false;
      setIsLoading(false);
    }
  }, []);

  /** Devuelve el client_request_id actual */
  const getRequestId = useCallback(() => requestIdRef.current, []);

  /**
   * Renueva el client_request_id.
   * Llamar después de una operación exitosa para que el siguiente intento
   * use un ID diferente (no reutilizar el ID de una operación completada).
   */
  const resetRequestId = useCallback(() => {
    requestIdRef.current = generateRequestId();
  }, []);

  return { isLoading, guard, getRequestId, resetRequestId };
};

export default useSafeAction;
