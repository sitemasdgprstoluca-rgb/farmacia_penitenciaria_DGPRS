/**
 * src/lib/supabase.js
 * ───────────────────
 * Cliente de Supabase exclusivamente para Realtime (no para auth ni queries).
 *
 * Configuración:
 *   VITE_SUPABASE_URL   = https://<project_ref>.supabase.co
 *   VITE_SUPABASE_ANON_KEY = eyJ...  (anon/public key — seguro exponerlo)
 *
 * Degradación graceful:
 *   Si las variables no están configuradas, `supabase` es null y
 *   `isRealtimeAvailable` es false. useRealtimeSync detecta esto y
 *   simplemente no suscribe (sin errores, sin logs molestos).
 *
 * Seguridad:
 *   - La anon key es pública por diseño (Supabase la recomienda en frontend).
 *   - El acceso a filas sensibles está protegido por RLS en cada tabla.
 *   - La tabla `realtime_events` solo contiene metadatos (event_type, entity,
 *     entity_id, scope_id) — ningún dato clínico o de inventario.
 */
import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL      = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = (SUPABASE_URL && SUPABASE_ANON_KEY)
  ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      realtime: {
        params: { eventsPerSecond: 10 },
      },
      // No inicializar auth — solo lo usamos para Realtime
      auth: {
        persistSession: false,
        autoRefreshToken: false,
        detectSessionInUrl: false,
      },
    })
  : null;

/**
 * `true` si Supabase Realtime está disponible (env vars configuradas).
 * Usar en UIs para mostrar indicador de "sincronización en tiempo real".
 */
export const isRealtimeAvailable = Boolean(supabase);
