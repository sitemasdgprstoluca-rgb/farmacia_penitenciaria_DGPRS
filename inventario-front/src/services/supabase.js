/**
 * Cliente de Supabase para persistencia del tema
 * Sistema de Inventario de Farmacia Penitenciaria
 */

import { createClient } from '@supabase/supabase-js';

// Configuración de Supabase
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

// Verificar configuración
const isConfigured = supabaseUrl && supabaseAnonKey;

if (!isConfigured) {
  console.warn(
    '⚠️ Supabase no configurado. Agrega VITE_SUPABASE_URL y VITE_SUPABASE_ANON_KEY en .env'
  );
}

// Cliente de Supabase
export const supabase = isConfigured
  ? createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        persistSession: false,
        autoRefreshToken: false,
      },
    })
  : null;

/**
 * Verifica si Supabase está disponible
 */
export const isSupabaseAvailable = () => supabase !== null;

/**
 * API del tema usando Supabase
 */
export const supabaseThemeAPI = {
  /**
   * Obtiene el tema activo desde Supabase (público, sin auth)
   */
  async getActiveTheme() {
    if (!supabase) return null;

    try {
      // Usar la función RPC pública
      const { data, error } = await supabase.rpc('get_active_theme');

      if (error) {
        console.error('Error RPC get_active_theme:', error);
        // Fallback a query directa
        const { data: queryData, error: queryError } = await supabase
          .from('theme_settings')
          .select('*')
          .eq('activo', true)
          .single();

        if (queryError) {
          console.error('Error query directa:', queryError);
          return null;
        }
        return queryData;
      }

      return data;
    } catch (err) {
      console.error('Error conexión Supabase:', err);
      return null;
    }
  },

  /**
   * Actualiza el tema en Supabase
   */
  async updateTheme(themeData) {
    if (!supabase) {
      console.warn('Supabase no disponible');
      return null;
    }

    try {
      // Intentar con RPC
      const { data, error } = await supabase.rpc('update_theme', {
        theme_data: themeData
      });

      if (error) {
        console.error('Error RPC update_theme:', error);
        
        // Fallback: update directo
        const { data: current } = await supabase
          .from('theme_settings')
          .select('id')
          .eq('activo', true)
          .single();

        if (current?.id) {
          const { data: updated, error: updateError } = await supabase
            .from('theme_settings')
            .update({
              ...themeData,
              updated_at: new Date().toISOString()
            })
            .eq('id', current.id)
            .select()
            .single();

          if (updateError) {
            console.error('Error update directo:', updateError);
            return null;
          }
          return updated;
        }
        return null;
      }

      return data;
    } catch (err) {
      console.error('Error actualizando tema:', err);
      return null;
    }
  },

  /**
   * Sube un logo a Supabase Storage
   */
  async uploadLogo(file, tipo) {
    if (!supabase) return null;

    try {
      const timestamp = Date.now();
      const ext = file.name.split('.').pop();
      const fileName = `${tipo}_${timestamp}.${ext}`;
      const filePath = `logos/${fileName}`;

      const { error } = await supabase.storage
        .from('theme-assets')
        .upload(filePath, file, {
          cacheControl: '3600',
          upsert: true
        });

      if (error) {
        console.error('Error subiendo logo:', error);
        return null;
      }

      const { data: urlData } = supabase.storage
        .from('theme-assets')
        .getPublicUrl(filePath);

      return urlData?.publicUrl || null;
    } catch (err) {
      console.error('Error upload logo:', err);
      return null;
    }
  },

  /**
   * Elimina un logo de Storage
   */
  async deleteLogo(url) {
    if (!supabase || !url) return false;

    try {
      const urlObj = new URL(url);
      const match = urlObj.pathname.match(/\/theme-assets\/(.+)$/);
      if (!match) return false;

      const { error } = await supabase.storage
        .from('theme-assets')
        .remove([match[1]]);

      return !error;
    } catch (err) {
      console.error('Error eliminando logo:', err);
      return false;
    }
  }
};

export default supabase;
