/**
 * Cliente de Supabase para persistencia del tema
 * Sistema de Inventario de Farmacia Penitenciaria
 * 
 * NOTA: La conexión directa a Supabase desde el frontend está DESHABILITADA.
 * Todo el acceso a datos pasa por la API de Django en el backend.
 * Las variables VITE_SUPABASE_* no están configuradas intencionalmente.
 */

// Supabase está deshabilitado - todo pasa por API Django
const isConfigured = false;

// Cliente nulo - no se usa conexión directa
export const supabase = null;

/**
 * Verifica si Supabase está disponible (siempre false)
 */
export const isSupabaseAvailable = () => false;

/**
 * API del tema - stub que siempre retorna null
 * El tema se obtiene desde /api/tema/activo/ via Django
 */
export const supabaseThemeAPI = {
  async getActiveTheme() {
    return null;
  },

  async updateTheme(themeData) {
    return null;
  },

  async uploadLogo(file, tipo) {
    return null;
  },

  async deleteLogo(url) {
    return false;
  }
};

export default supabase;
