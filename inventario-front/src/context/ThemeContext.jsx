import { useState, useEffect, useCallback } from 'react';
import { ThemeContext } from './contexts';
import { configuracionAPI, temaGlobalAPI } from '../services/api';
import { supabaseThemeAPI, isSupabaseAvailable } from '../services/supabase';

// ============================================================================
// CONSTANTES Y CLAVES DE ALMACENAMIENTO
// ============================================================================
const STORAGE_KEY_TEMA = 'sifp_tema_cache';
const STORAGE_KEY_UPDATED = 'sifp_tema_updated_at';

/**
 * Aplica las variables CSS al documento
 */
const aplicarCSSVariables = (cssVariables) => {
  if (!cssVariables) {
    console.warn('ThemeContext: No hay CSS variables para aplicar');
    return;
  }
  
  const root = document.documentElement;
  Object.entries(cssVariables).forEach(([variable, valor]) => {
    if (valor) {
      root.style.setProperty(variable, valor);
    }
  });
  console.log('ThemeContext: Variables CSS aplicadas correctamente');
};

/**
 * Guarda el tema en localStorage para persistencia entre recargas
 */
const guardarTemaEnCache = (tema) => {
  try {
    if (!tema) return;
    const cacheData = {
      css_variables: tema.css_variables,
      reporte_titulo_institucion: tema.reporte_titulo_institucion,
      favicon_url: tema.favicon_url,
      logo_header_url: tema.logo_header_url,
      logo_login_url: tema.logo_login_url,
      logo_reportes_url: tema.logo_reportes_url,
      nombre: tema.nombre,
      updated_at: tema.updated_at || new Date().toISOString()
    };
    localStorage.setItem(STORAGE_KEY_TEMA, JSON.stringify(cacheData));
    localStorage.setItem(STORAGE_KEY_UPDATED, cacheData.updated_at);
    console.log('ThemeContext: Tema guardado en caché local');
  } catch (err) {
    console.warn('ThemeContext: No se pudo guardar tema en localStorage:', err);
  }
};

/**
 * Recupera el tema desde localStorage
 */
const obtenerTemaDeCache = () => {
  try {
    const cached = localStorage.getItem(STORAGE_KEY_TEMA);
    if (cached) {
      const tema = JSON.parse(cached);
      console.log('ThemeContext: Tema recuperado de caché local');
      return tema;
    }
  } catch (err) {
    console.warn('ThemeContext: Error leyendo caché local:', err);
  }
  return null;
};

/**
 * Invalida la caché local del tema
 */
const invalidarCacheTema = () => {
  try {
    localStorage.removeItem(STORAGE_KEY_TEMA);
    localStorage.removeItem(STORAGE_KEY_UPDATED);
  } catch (err) {
    // Ignorar errores de localStorage
  }
};

/**
 * Genera CSS variables a partir de la configuración de colores y tipografía
 * Útil cuando el backend no devuelve css_variables en la respuesta
 */
const generarCSSVariablesDesdeConfig = (config) => {
  if (!config) return null;
  return {
    // Colores
    '--color-primary': config.color_primario,
    '--color-primary-hover': config.color_primario_hover,
    '--color-primary-light': `rgba(${hexToRgb(config.color_primario)}, 0.2)`,
    '--color-secondary': config.color_secundario,
    '--color-accent': config.color_acento,
    '--color-background': config.color_fondo,
    '--color-sidebar-bg': config.color_fondo_sidebar,
    '--color-header-bg': config.color_fondo_header,
    '--color-card-bg': config.color_fondo_card,
    '--color-text': config.color_texto,
    '--color-text-secondary': config.color_texto_secundario,
    '--color-sidebar-text': config.color_texto_sidebar,
    '--color-header-text': config.color_texto_header,
    '--color-success': config.color_exito,
    '--color-warning': config.color_advertencia,
    '--color-error': config.color_error,
    '--color-info': config.color_info,
    // Tipografía
    '--font-family-principal': config.tipografia_principal || "'Montserrat', sans-serif",
    '--font-family-titulos': config.tipografia_titulos || "'Montserrat', sans-serif",
    '--font-size-titulo': config.tamano_titulo || '2rem',
    '--font-size-subtitulo': config.tamano_subtitulo || '1.5rem',
    '--font-size-cuerpo': config.tamano_cuerpo || '1rem',
    '--font-size-pequeño': config.tamano_pequeno || '0.875rem',
  };
};

/**
 * Convierte color hex a RGB para usar en rgba()
 */
const hexToRgb = (hex) => {
  if (!hex) return '159, 34, 65'; // default color
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result 
    ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`
    : '159, 34, 65';
};

/**
 * Normaliza los datos de Supabase al formato esperado por el frontend
 */
const normalizarTemaSupabase = (temaSupabase) => {
  if (!temaSupabase) return null;
  
  // Si ya tiene css_variables como objeto, usarlas directamente
  let cssVars = temaSupabase.css_variables;
  
  // Si css_variables es string JSON, parsearlo
  if (typeof cssVars === 'string') {
    try {
      cssVars = JSON.parse(cssVars);
    } catch (e) {
      cssVars = null;
    }
  }
  
  // Si no hay css_variables, generarlas desde los campos individuales
  if (!cssVars || Object.keys(cssVars).length === 0) {
    cssVars = {
      '--color-primary': temaSupabase.primary_color || '#0ea5e9',
      '--color-primary-hover': temaSupabase.primary_hover_color || '#0284c7',
      '--color-primary-light': temaSupabase.primary_light_color || '#e0f2fe',
      '--color-secondary': temaSupabase.secondary_color || '#64748b',
      '--color-accent': temaSupabase.accent_color || '#f59e0b',
      '--color-background': temaSupabase.background_color || '#f8fafc',
      '--color-sidebar-bg': temaSupabase.sidebar_bg || '#1e293b',
      '--color-sidebar-hover': temaSupabase.sidebar_hover || '#334155',
      '--color-header-bg': temaSupabase.header_bg || '#ffffff',
      '--color-card-bg': temaSupabase.card_bg || '#ffffff',
      '--color-text': temaSupabase.text_primary || '#1e293b',
      '--color-text-secondary': temaSupabase.text_secondary || '#64748b',
      '--color-text-muted': temaSupabase.text_muted || '#94a3b8',
      '--color-sidebar-text': temaSupabase.text_on_primary || '#ffffff',
      '--color-header-text': temaSupabase.text_on_primary || '#ffffff',
      '--color-success': temaSupabase.success_color || '#22c55e',
      '--color-warning': temaSupabase.warning_color || '#f59e0b',
      '--color-error': temaSupabase.error_color || '#ef4444',
      '--color-info': temaSupabase.info_color || '#3b82f6',
      '--color-border': temaSupabase.border_color || '#e2e8f0',
      '--border-radius': temaSupabase.border_radius || '0.5rem',
      '--font-family-principal': temaSupabase.font_family || '"Inter", sans-serif',
    };
  }
  
  return {
    id: temaSupabase.id,
    nombre: temaSupabase.nombre || 'Tema Personalizado',
    css_variables: cssVars,
    logo_header_url: temaSupabase.logo_header_url,
    logo_login_url: temaSupabase.logo_login_url,
    logo_reportes_url: temaSupabase.logo_reports_url,
    favicon_url: temaSupabase.favicon_url,
    reporte_titulo_institucion: temaSupabase.report_title || 'Sistema de Farmacia Penitenciaria',
    updated_at: temaSupabase.updated_at,
  };
};

/**
 * Actualiza el título del documento
 */
const actualizarTituloDocumento = (nombre) => {
  if (nombre) {
    document.title = nombre;
  }
};

/**
 * Valores por defecto del tema (colores institucionales - guinda/rojo)
 */
const temaDefault = {
  nombre_sistema: 'Sistema de Farmacia Penitenciaria',
  tema_activo: 'default',
  css_variables: {
    '--color-primary': '#9F2241',
    '--color-primary-hover': '#6B1839',
    '--color-primary-light': 'rgba(159, 34, 65, 0.2)',
    '--color-secondary': '#424242',
    '--color-accent': '#BC955C',
    '--color-background': '#F5F5F5',
    '--color-sidebar-bg': '#9F2241',
    '--color-header-bg': '#9F2241',
    '--color-card-bg': '#FFFFFF',
    '--color-text': '#212121',
    '--color-text-secondary': '#757575',
    '--color-sidebar-text': '#FFFFFF',
    '--color-header-text': '#FFFFFF',
    '--color-success': '#4CAF50',
    '--color-warning': '#FF9800',
    '--color-error': '#F44336',
    '--color-info': '#2196F3',
    '--font-family-principal': "'Montserrat', sans-serif",
    '--font-family-titulos': "'Montserrat', sans-serif",
    '--font-size-titulo': '2rem',
    '--font-size-subtitulo': '1.5rem',
    '--font-size-cuerpo': '1rem',
    '--font-size-pequeño': '0.875rem',
  },
  temas_disponibles: [
    { id: 'default', nombre: 'Por Defecto (Institucional)' },
    { id: 'dark', nombre: 'Oscuro' },
    { id: 'green', nombre: 'Verde Institucional' },
    { id: 'purple', nombre: 'Púrpura' },
    { id: 'custom', nombre: 'Personalizado' },
  ],
};

export const ThemeProvider = ({ children }) => {
  const [configuracion, setConfiguracion] = useState(temaDefault);
  const [temaGlobal, setTemaGlobal] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [temaAplicado, setTemaAplicado] = useState(false);

  /**
   * Aplica el tema (CSS variables, favicon, título)
   */
  const aplicarTemaCompleto = useCallback((tema) => {
    if (!tema) return;
    
    // Aplicar CSS variables
    if (tema.css_variables) {
      aplicarCSSVariables(tema.css_variables);
    }
    
    // Actualizar favicon si está definido
    if (tema.favicon_url) {
      const link = document.querySelector("link[rel*='icon']") || document.createElement('link');
      link.type = 'image/x-icon';
      link.rel = 'shortcut icon';
      link.href = tema.favicon_url;
      document.getElementsByTagName('head')[0].appendChild(link);
    }
    
    // Actualizar título
    if (tema.reporte_titulo_institucion) {
      document.title = tema.reporte_titulo_institucion;
    }
    
    setTemaAplicado(true);
  }, []);

  /**
   * Carga la configuración del tema
   * FLUJO MEJORADO (defensivo):
   * 1. Aplicar caché local SIEMPRE primero (rehidratación instantánea)
   * 2. Consultar SUPABASE (fuente de verdad pública)
   * 3. Si Supabase falla, intentar API Django (usa cliente público, no requiere auth)
   * 4. Si API falla, MANTENER la caché (no sobrescribir con default)
   * 5. Solo usar default si no hay absolutamente nada
   * 
   * @param {boolean} forzar - Si true, ignora la caché y fuerza recarga desde servidor
   */
  const cargarTema = useCallback(async (forzar = false) => {
    try {
      setCargando(true);
      setError(null);
      
      // PASO 1: Rehidratación rápida desde caché local (SIEMPRE primero)
      const temaCache = obtenerTemaDeCache();
      let temaAplicadoDesdeCache = false;
      
      if (temaCache && temaCache.css_variables && !forzar) {
        console.log('ThemeContext: Aplicando tema desde caché local (instantáneo)');
        setTemaGlobal(temaCache);
        aplicarTemaCompleto(temaCache);
        temaAplicadoDesdeCache = true;
      }
      
      // PASO 2: SUPABASE como fuente principal (público, no requiere auth)
      let temaObtenido = false;
      
      if (isSupabaseAvailable()) {
        try {
          console.log('ThemeContext: Consultando Supabase...');
          const temaSupabase = await supabaseThemeAPI.getActiveTheme();
          
          if (temaSupabase) {
            // Normalizar datos de Supabase al formato esperado
            const temaNormalizado = normalizarTemaSupabase(temaSupabase);
            
            if (temaNormalizado && temaNormalizado.css_variables) {
              setTemaGlobal(temaNormalizado);
              aplicarTemaCompleto(temaNormalizado);
              guardarTemaEnCache(temaNormalizado);
              console.log('ThemeContext: Tema cargado desde Supabase ✓');
              temaObtenido = true;
            }
          }
        } catch (supabaseErr) {
          console.warn('ThemeContext: Supabase no disponible:', supabaseErr.message);
          // NO retornar aquí - intentar API Django como fallback
        }
      } else {
        console.log('ThemeContext: Supabase no configurado, usando API Django');
      }
      
      // PASO 3: Fallback a API Django (usa cliente PÚBLICO, no requiere auth)
      if (!temaObtenido) {
        try {
          console.log('ThemeContext: Consultando API Django (público)...');
          const response = await temaGlobalAPI.getTemaActivo();
          const tema = response.data;
          
          if (tema && tema.css_variables) {
            setTemaGlobal(tema);
            aplicarTemaCompleto(tema);
            guardarTemaEnCache(tema);
            console.log('ThemeContext: Tema cargado desde API Django ✓');
            temaObtenido = true;
          }
        } catch (apiErr) {
          // Error esperado si el endpoint no existe o hay problema de red
          const status = apiErr.response?.status;
          console.warn(`ThemeContext: API Django no disponible (${status || 'red'})`);
          // NO sobrescribir caché con default si ya tenemos tema aplicado
        }
      }
      
      // PASO 4: Si tenemos caché y no pudimos obtener tema del servidor, MANTENER caché
      if (!temaObtenido && temaAplicadoDesdeCache) {
        console.log('ThemeContext: Manteniendo tema desde caché (servidor no disponible)');
        return; // NO aplicar default, ya tenemos caché aplicada
      }
      
      // PASO 5: Sistema legacy (solo si no hay tema aún)
      if (!temaObtenido && !temaAplicadoDesdeCache) {
        try {
          const response = await configuracionAPI.getTema();
          const config = response.data;
          
          if (config) {
            setConfiguracion(config);
            const cssVars = config.css_variables || generarCSSVariablesDesdeConfig(config);
            aplicarCSSVariables(cssVars);
            actualizarTituloDocumento(config.nombre_sistema);
            setTemaAplicado(true);
            console.log('ThemeContext: Tema cargado desde sistema legacy');
            return;
          }
        } catch (legacyErr) {
          // Legacy tampoco disponible
        }
        
        // PASO 6: Último recurso - tema por defecto (solo si no hay NADA)
        console.warn('ThemeContext: Sin datos de tema, usando valores por defecto');
        aplicarCSSVariables(temaDefault.css_variables);
        setTemaAplicado(true);
      }
    } catch (err) {
      console.error('ThemeContext: Error crítico cargando tema:', err);
      setError(err);
      // Solo aplicar default si no hay caché
      const temaCache = obtenerTemaDeCache();
      if (!temaCache) {
        aplicarCSSVariables(temaDefault.css_variables);
      }
      setTemaAplicado(true);
    } finally {
      setCargando(false);
    }
  }, [aplicarTemaCompleto]);

  /**
   * Actualiza la configuración del tema (TemaGlobal)
   */
  const actualizarTema = async (nuevaConfig) => {
    try {
      // Intentar actualizar con TemaGlobal primero
      try {
        const response = await temaGlobalAPI.updateTema(nuevaConfig);
        const resultado = response.data;
        const tema = resultado.tema || resultado;
        
        setTemaGlobal(tema);
        if (tema.css_variables) {
          aplicarCSSVariables(tema.css_variables);
          guardarTemaEnCache(tema);
        }
        
        return { success: true, data: tema };
      } catch (temaErr) {
        // Fallback a sistema legacy
        const response = await configuracionAPI.updateTema(nuevaConfig);
        const config = response.data;
        
        setConfiguracion(config);
        const cssVars = config.css_variables || generarCSSVariablesDesdeConfig(config);
        aplicarCSSVariables(cssVars);
        actualizarTituloDocumento(config.nombre_sistema);
        
        return { success: true, data: config };
      }
    } catch (err) {
      console.error('Error al actualizar el tema:', err);
      return { 
        success: false, 
        error: err.response?.data?.error || 'Error al actualizar el tema' 
      };
    }
  };

  /**
   * Actualiza el TemaGlobal completo
   * IMPORTANTE: Guarda en AMBOS Supabase Y API Django para mantener sincronización
   * Si uno falla, el otro sirve de respaldo
   */
  const actualizarTemaGlobal = async (nuevoTema) => {
    try {
      console.log('ThemeContext: Actualizando tema...');
      
      // Preparar datos para Supabase
      const datosSupabase = {
        primary_color: nuevoTema.color_primario || nuevoTema.primary_color,
        primary_hover_color: nuevoTema.color_primario_hover || nuevoTema.primary_hover_color,
        secondary_color: nuevoTema.color_secundario || nuevoTema.secondary_color,
        accent_color: nuevoTema.color_acento || nuevoTema.accent_color,
        background_color: nuevoTema.color_fondo || nuevoTema.background_color,
        sidebar_bg: nuevoTema.color_fondo_sidebar || nuevoTema.sidebar_bg,
        header_bg: nuevoTema.color_fondo_header || nuevoTema.header_bg,
        card_bg: nuevoTema.color_fondo_card || nuevoTema.card_bg,
        text_primary: nuevoTema.color_texto || nuevoTema.text_primary,
        text_secondary: nuevoTema.color_texto_secundario || nuevoTema.text_secondary,
        success_color: nuevoTema.color_exito || nuevoTema.success_color,
        warning_color: nuevoTema.color_advertencia || nuevoTema.warning_color,
        error_color: nuevoTema.color_error || nuevoTema.error_color,
        info_color: nuevoTema.color_info || nuevoTema.info_color,
        border_color: nuevoTema.color_borde || nuevoTema.border_color,
        logo_header_url: nuevoTema.logo_header_url,
        logo_login_url: nuevoTema.logo_login_url,
        logo_reports_url: nuevoTema.logo_reportes_url || nuevoTema.logo_reports_url,
        favicon_url: nuevoTema.favicon_url,
        report_title: nuevoTema.reporte_titulo_institucion || nuevoTema.report_title,
        css_variables: nuevoTema.css_variables,
      };
      
      let temaFinal = null;
      let supabaseOk = false;
      let djangoOk = false;
      
      // PASO 1: Guardar en Supabase (fuente de verdad pública)
      if (isSupabaseAvailable()) {
        try {
          const temaSupabase = await supabaseThemeAPI.updateTheme(datosSupabase);
          if (temaSupabase) {
            temaFinal = normalizarTemaSupabase(temaSupabase);
            supabaseOk = true;
            console.log('ThemeContext: Tema guardado en Supabase ✓');
          }
        } catch (supabaseErr) {
          console.warn('ThemeContext: Error guardando en Supabase:', supabaseErr.message);
          // Continuar con Django aunque Supabase falle
        }
      }
      
      // PASO 2: SIEMPRE intentar guardar en API Django (sincronización)
      // Esto mantiene ambos sistemas sincronizados como respaldo
      try {
        const response = await temaGlobalAPI.updateTema(nuevoTema);
        const resultado = response.data;
        const temaDjango = resultado.tema || resultado;
        
        // Si no obtuvimos tema de Supabase, usar el de Django
        if (!temaFinal && temaDjango) {
          temaFinal = temaDjango;
        }
        djangoOk = true;
        console.log('ThemeContext: Tema guardado en API Django ✓');
      } catch (djangoErr) {
        console.warn('ThemeContext: Error guardando en Django:', djangoErr.message);
        // Si Supabase funcionó, no es error crítico
      }
      
      // Si al menos uno funcionó, actualizar estado y caché
      if (temaFinal) {
        setTemaGlobal(temaFinal);
        if (temaFinal.css_variables) {
          aplicarCSSVariables(temaFinal.css_variables);
          guardarTemaEnCache(temaFinal);
        }
        
        const source = supabaseOk && djangoOk ? 'Supabase + Django' 
                     : supabaseOk ? 'Supabase' 
                     : 'Django';
        console.log(`ThemeContext: Tema actualizado (${source})`);
        
        return { success: true, data: temaFinal };
      }
      
      // Si ambos fallaron, es un error
      throw new Error('No se pudo guardar el tema en ningún servidor');
    } catch (err) {
      console.error('Error al actualizar tema global:', err);
      return { 
        success: false, 
        error: err.response?.data?.error || err.message || 'Error al actualizar el tema' 
      };
    }
  };

  /**
   * Sube un logo al TemaGlobal
   * Primero intenta Supabase Storage, luego API Django
   * @param {string} tipo - header, login, reportes, favicon, fondo_login, fondo_reportes
   * @param {File} file - archivo a subir
   */
  const subirLogoTema = async (tipo, file) => {
    try {
      // PASO 1: Intentar subir a Supabase Storage
      if (isSupabaseAvailable()) {
        try {
          const logoUrl = await supabaseThemeAPI.uploadLogo(file, tipo);
          if (logoUrl) {
            // Actualizar el tema con la nueva URL del logo
            const campoLogo = {
              'header': 'logo_header_url',
              'login': 'logo_login_url',
              'reportes': 'logo_reports_url',
              'favicon': 'favicon_url',
            }[tipo] || `logo_${tipo}_url`;
            
            const temaActualizado = await supabaseThemeAPI.updateTheme({
              [campoLogo]: logoUrl
            });
            
            if (temaActualizado) {
              const temaNormalizado = normalizarTemaSupabase(temaActualizado);
              setTemaGlobal(temaNormalizado);
              guardarTemaEnCache(temaNormalizado);
              console.log(`ThemeContext: Logo ${tipo} subido a Supabase ✓`);
              return { success: true, data: temaNormalizado };
            }
          }
        } catch (supabaseErr) {
          console.warn('ThemeContext: Error subiendo a Supabase:', supabaseErr);
        }
      }
      
      // PASO 2: Fallback a API Django
      const formData = new FormData();
      formData.append('archivo', file);
      
      const response = await temaGlobalAPI.subirLogo(tipo, formData);
      const resultado = response.data;
      const tema = resultado.tema || resultado;
      
      setTemaGlobal(tema);
      if (tema.css_variables) {
        aplicarCSSVariables(tema.css_variables);
        guardarTemaEnCache(tema);
      }
      
      return { success: true, data: tema };
    } catch (err) {
      console.error(`Error al subir logo ${tipo}:`, err);
      return { 
        success: false, 
        error: err.response?.data?.error || `Error al subir el logo ${tipo}` 
      };
    }
  };

  /**
   * Elimina un logo del TemaGlobal
   * @param {string} tipo - header, login, reportes, favicon, fondo_login, fondo_reportes
   */
  const eliminarLogoTema = async (tipo) => {
    try {
      const response = await temaGlobalAPI.eliminarLogo(tipo);
      const resultado = response.data;
      const tema = resultado.tema || resultado;
      
      setTemaGlobal(tema);
      if (tema.css_variables) {
        aplicarCSSVariables(tema.css_variables);
        guardarTemaEnCache(tema);
      }
      
      return { success: true, data: tema };
    } catch (err) {
      console.error(`Error al eliminar logo ${tipo}:`, err);
      return { 
        success: false, 
        error: err.response?.data?.error || `Error al eliminar el logo ${tipo}` 
      };
    }
  };

  /**
   * Restablece al tema institucional (TemaGlobal)
   */
  const restablecerTemaInstitucional = async () => {
    try {
      const response = await temaGlobalAPI.restablecerInstitucional();
      const resultado = response.data;
      const tema = resultado.tema || resultado;
      
      setTemaGlobal(tema);
      if (tema.css_variables) {
        aplicarCSSVariables(tema.css_variables);
        // Invalidar caché anterior y guardar el nuevo tema institucional
        invalidarCacheTema();
        guardarTemaEnCache(tema);
      }
      
      return { success: true, data: tema };
    } catch (err) {
      console.error('Error al restablecer tema institucional:', err);
      return { 
        success: false, 
        error: err.response?.data?.error || 'Error al restablecer el tema' 
      };
    }
  };

  /**
   * Aplica un tema predefinido
   */
  const aplicarTemaPredefinido = async (tema) => {
    try {
      const response = await configuracionAPI.aplicarTema(tema);
      const config = response.data.configuracion;
      
      setConfiguracion(config);
      // Aplicar CSS variables - usar las del backend o generarlas si no vienen
      const cssVars = config.css_variables || generarCSSVariablesDesdeConfig(config);
      aplicarCSSVariables(cssVars);
      
      // Actualizar título del documento
      actualizarTituloDocumento(config.nombre_sistema);
      
      return { success: true, data: config };
    } catch (err) {
      console.error('Error al aplicar el tema:', err);
      return { 
        success: false, 
        error: err.response?.data?.error || 'Error al aplicar el tema' 
      };
    }
  };

  /**
   * Restablece la configuración a valores por defecto
   */
  const restablecerTema = async () => {
    try {
      const response = await configuracionAPI.restablecer();
      const config = response.data.configuracion;
      
      setConfiguracion(config);
      // Aplicar CSS variables - usar las del backend o generarlas si no vienen
      const cssVars = config.css_variables || generarCSSVariablesDesdeConfig(config);
      aplicarCSSVariables(cssVars);
      
      // Actualizar título del documento
      actualizarTituloDocumento(config.nombre_sistema);
      
      return { success: true, data: config };
    } catch (err) {
      console.error('Error al restablecer el tema:', err);
      return { 
        success: false, 
        error: err.response?.data?.error || 'Error al restablecer el tema' 
      };
    }
  };

  /**
   * Sube un logo para el header
   */
  const subirLogoHeader = async (file) => {
    try {
      const formData = new FormData();
      formData.append('logo', file);
      
      const response = await configuracionAPI.subirLogoHeader(formData);
      const config = response.data.configuracion;
      
      setConfiguracion(config);
      // Re-aplicar CSS variables para mantener colores (backend puede no incluirlos)
      const cssVars = config.css_variables || generarCSSVariablesDesdeConfig(config);
      aplicarCSSVariables(cssVars);
      
      return { success: true, data: config };
    } catch (err) {
      console.error('Error al subir logo header:', err);
      return { 
        success: false, 
        error: err.response?.data?.error || 'Error al subir el logo' 
      };
    }
  };

  /**
   * Sube un logo para PDFs
   */
  const subirLogoPdf = async (file) => {
    try {
      const formData = new FormData();
      formData.append('logo', file);
      
      const response = await configuracionAPI.subirLogoPdf(formData);
      const config = response.data.configuracion;
      
      setConfiguracion(config);
      // Re-aplicar CSS variables para mantener colores (backend puede no incluirlos)
      const cssVars = config.css_variables || generarCSSVariablesDesdeConfig(config);
      aplicarCSSVariables(cssVars);
      
      return { success: true, data: config };
    } catch (err) {
      console.error('Error al subir logo PDF:', err);
      return { 
        success: false, 
        error: err.response?.data?.error || 'Error al subir el logo' 
      };
    }
  };

  /**
   * Elimina el logo del header
   */
  const eliminarLogoHeader = async () => {
    try {
      const response = await configuracionAPI.eliminarLogoHeader();
      const config = response.data.configuracion;
      
      setConfiguracion(config);
      // Re-aplicar CSS variables para mantener colores (backend puede no incluirlos)
      const cssVars = config.css_variables || generarCSSVariablesDesdeConfig(config);
      aplicarCSSVariables(cssVars);
      
      return { success: true, data: config };
    } catch (err) {
      console.error('Error al eliminar logo header:', err);
      return { 
        success: false, 
        error: err.response?.data?.error || 'Error al eliminar el logo' 
      };
    }
  };

  /**
   * Elimina el logo para PDFs
   */
  const eliminarLogoPdf = async () => {
    try {
      const response = await configuracionAPI.eliminarLogoPdf();
      const config = response.data.configuracion;
      
      setConfiguracion(config);
      // Re-aplicar CSS variables para mantener colores (backend puede no incluirlos)
      const cssVars = config.css_variables || generarCSSVariablesDesdeConfig(config);
      aplicarCSSVariables(cssVars);
      
      return { success: true, data: config };
    } catch (err) {
      console.error('Error al eliminar logo PDF:', err);
      return { 
        success: false, 
        error: err.response?.data?.error || 'Error al eliminar el logo' 
      };
    }
  };

  // Cargar tema al montar el componente
  useEffect(() => {
    cargarTema();
  }, [cargarTema]);

  // Escuchar evento de login exitoso para recargar tema con auth disponible
  // Esto resuelve el problema de que el tema inicial puede fallar sin token
  useEffect(() => {
    const handleLoginSuccess = () => {
      console.log('ThemeContext: Login detectado, recargando tema con autenticación...');
      // Forzar recarga desde servidor (ignorar caché) para obtener tema más actualizado
      cargarTema(true);
    };

    // Escuchar evento personalizado de login exitoso
    window.addEventListener('auth-login-success', handleLoginSuccess);
    
    return () => {
      window.removeEventListener('auth-login-success', handleLoginSuccess);
    };
  }, [cargarTema]);

  /**
   * Aplica variables CSS localmente para preview en tiempo real
   * No persiste en backend, solo actualiza la UI temporalmente
   */
  const aplicarCSSVariablesLocalmente = useCallback((colores) => {
    const cssVars = generarCSSVariablesDesdeConfig(colores);
    aplicarCSSVariables(cssVars);
  }, []);

  /**
   * Aplica CSS variables desde un objeto de tema (para preview)
   */
  const previewTema = useCallback((tema) => {
    if (tema?.css_variables) {
      aplicarCSSVariables(tema.css_variables);
    }
  }, []);

  const value = {
    // Estado
    configuracion,
    temaGlobal,
    cargando,
    error,
    
    // Funciones legacy
    cargarTema,
    actualizarTema,
    aplicarTemaPredefinido,
    restablecerTema,
    subirLogoHeader,
    subirLogoPdf,
    eliminarLogoHeader,
    eliminarLogoPdf,
    
    // Nuevas funciones TemaGlobal
    actualizarTemaGlobal,
    subirLogoTema,
    eliminarLogoTema,
    restablecerTemaInstitucional,
    previewTema,
    
    // Utilidades
    aplicarCSSVariablesLocalmente,
    
    // Computed
    temaActivo: temaGlobal?.nombre || configuracion.tema_activo,
    nombreSistema: temaGlobal?.reporte_titulo_institucion || configuracion.nombre_sistema,
    temasDisponibles: configuracion.temas_disponibles || temaDefault.temas_disponibles,
    
    // URLs de logos (TemaGlobal)
    logoHeaderUrl: temaGlobal?.logo_header_url || configuracion?.logo_header_url,
    logoLoginUrl: temaGlobal?.logo_login_url,
    logoReportesUrl: temaGlobal?.logo_reportes_url,
    faviconUrl: temaGlobal?.favicon_url,
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};
