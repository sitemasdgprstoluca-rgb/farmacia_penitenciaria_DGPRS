/**
 * src/hooks/useRealtimeSync.js
 * ─────────────────────────────
 * Hook universal para sincronización multi-usuario en tiempo real.
 *
 * Arquitectura (segura):
 *   1. Suscribe a INSERTs en la tabla `realtime_events` de Supabase.
 *   2. El evento solo contiene metadatos (event_type, entity, entity_id, scope_id).
 *   3. Al recibir un evento relevante, llama a `onRefresh` (con debounce).
 *   4. `onRefresh` es la función normal de carga de la página (p.ej. cargarMovimientos).
 *      Esa función llama a la API DRF que aplica permisos completos.
 *   → Ningún usuario recibe datos que no le corresponden.
 *
 * Uso:
 *   const { isLive } = useRealtimeSync(
 *     ['movimiento', 'salida_masiva'],   // entidades a escuchar
 *     cargarMovimientos,                  // callback de recarga
 *     { debounceMs: 500, enabled: !modal } // opciones
 *   );
 *
 * Degradación graceful:
 *   - Si VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY no están → no hace nada, sin errores.
 *   - Si la tabla realtime_events no existe → canal en error, log warning silencioso.
 *
 * Reconexión:
 *   - Supabase JS maneja reconexión automática con backoff exponencial.
 *   - Al reconectar, isLive vuelve a true; el componente no necesita hacer nada extra.
 *
 * @param {string|string[]} entity   Tipo(s) de entidad: 'movimiento', 'requisicion', ...
 * @param {Function}        onRefresh Callback a llamar al recibir evento relevante
 * @param {Object}          options
 * @param {number}   [options.debounceMs=500]  Debounce en ms para coalescer eventos rápidos
 * @param {number[]} [options.scopeIds=[]]      Filtrar por scope_id ([] = aceptar todos)
 * @param {boolean}  [options.enabled=true]     Desactivar temporalmente (p.ej. modal abierto)
 * @returns {{ isLive: boolean }}  true cuando la suscripción está activa
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { supabase } from '../lib/supabase';

export const useRealtimeSync = (
  entity,
  onRefresh,
  { debounceMs = 500, scopeIds = [], enabled = true } = {}
) => {
  const [isLive, setIsLive]     = useState(false);
  const debounceTimer           = useRef(null);
  const seenEvents              = useRef(new Set());
  const onRefreshRef            = useRef(onRefresh);
  const scopeIdsRef             = useRef(scopeIds);

  // Mantener refs sincronizados sin disparar re-suscripción
  useEffect(() => { onRefreshRef.current  = onRefresh; },  [onRefresh]);
  useEffect(() => { scopeIdsRef.current   = scopeIds;  },  [scopeIds]);  // eslint-disable-line react-hooks/exhaustive-deps

  // ── Función de disparo con debounce + deduplicación ─────────────────────
  const triggerRefresh = useCallback((eventKey) => {
    // Deduplicar: ignorar si ya procesamos este evento
    if (seenEvents.current.has(eventKey)) return;
    seenEvents.current.add(eventKey);

    // Acotar el conjunto visto para evitar crecimiento indefinido
    if (seenEvents.current.size > 400) {
      const arr = [...seenEvents.current];
      seenEvents.current = new Set(arr.slice(-150));
    }

    // Debounce — coalescer múltiples eventos en una sola recarga
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      onRefreshRef.current?.();
    }, debounceMs);
  }, [debounceMs]);

  // ── Suscripción Supabase Realtime ────────────────────────────────────────
  useEffect(() => {
    // Sin cliente (env vars no configuradas) → no-op silencioso
    if (!supabase || !enabled) return;

    const entities = Array.isArray(entity) ? entity : [entity];

    // Nombre único de canal para evitar colisiones entre instancias del hook
    const channelName = `rt:${entities.join('+')}:${crypto.randomUUID?.() ?? Math.random().toString(36).slice(2)}`;

    const channel = supabase
      .channel(channelName)
      .on(
        'postgres_changes',
        {
          event:  'INSERT',
          schema: 'public',
          table:  'realtime_events',
        },
        (payload) => {
          const row = payload.new;
          if (!row) return;

          const { id, entity: evEntity, entity_id, scope_id } = row;

          // 1. Filtrar por tipo de entidad
          if (!entities.includes(evEntity)) return;

          // 2. Filtrar por scope si se especificaron scopes de interés
          const scopes = scopeIdsRef.current;
          if (
            scopes.length > 0 &&
            scope_id !== null &&
            scope_id !== undefined &&
            !scopes.includes(scope_id)
          ) return;

          // 3. Disparar recarga (debounced + deduped)
          triggerRefresh(`${evEntity}:${entity_id}:${id}`);
        }
      )
      .subscribe((status) => {
        switch (status) {
          case 'SUBSCRIBED':
            setIsLive(true);
            break;
          case 'CHANNEL_ERROR':
          case 'TIMED_OUT':
            setIsLive(false);
            console.warn(`[useRealtimeSync] canal ${entities.join('+')} — estado: ${status}`);
            break;
          case 'CLOSED':
            setIsLive(false);
            break;
          default:
            break;
        }
      });

    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
      setIsLive(false);
      supabase.removeChannel(channel);
    };
  }, [
    // eslint-disable-next-line react-hooks/exhaustive-deps
    Array.isArray(entity) ? entity.join(',') : entity,
    enabled,
    triggerRefresh,
  ]);

  return { isLive };
};
