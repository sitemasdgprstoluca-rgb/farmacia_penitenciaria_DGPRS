import { useState, useEffect, useCallback } from 'react';
import { ThemeContext } from './contexts';
import { configuracionAPI, temaGlobalAPI } from '../services/api';

/**
 * Aplica las variables CSS al documento
 */
const aplicarCSSVariables = (cssVariables) => {
  if (!cssVariables) return;
  
  const root = document.documentElement;
  Object.entries(cssVariables).forEach(([variable, valor]) => {
    root.style.setProperty(variable, valor);
  });
};

/**
 * Genera CSS variables a partir de la configuración de colores
 * Útil cuando el backend no devuelve css_variables en la respuesta
 */
const generarCSSVariablesDesdeConfig = (config) => {
  if (!config) return null;
  return {
    '--color-primary': config.color_primario,
    '--color-primary-hover': config.color_primario_hover,
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
  const [temaGlobal, setTemaGlobal] = useState(null); // Nuevo: tema global completo
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Carga la configuración del tema desde el backend (TemaGlobal)
   */
  const cargarTema = useCallback(async () => {
    try {
      setCargando(true);
      setError(null);
      
      // Intentar cargar desde TemaGlobal primero (nuevo sistema)
      try {
        const response = await temaGlobalAPI.getTemaActivo();
        const tema = response.data;
        
        if (tema && tema.css_variables) {
          setTemaGlobal(tema);
          // Aplicar CSS variables del nuevo sistema
          aplicarCSSVariables(tema.css_variables);
          
          // Actualizar favicon si está definido
          if (tema.favicon_url) {
            const link = document.querySelector("link[rel*='icon']") || document.createElement('link');
            link.type = 'image/x-icon';
            link.rel = 'shortcut icon';
            link.href = tema.favicon_url;
            document.getElementsByTagName('head')[0].appendChild(link);
          }
          
          // Actualizar título con nombre del tema si no hay nombre_sistema
          if (tema.reporte_titulo_institucion) {
            document.title = tema.reporte_titulo_institucion;
          }
          return;
        }
      } catch (temaErr) {
        console.warn('TemaGlobal no disponible, usando configuración legacy');
      }
      
      // Fallback a sistema legacy
      const response = await configuracionAPI.getTema();
      const config = response.data;
      
      if (config) {
        setConfiguracion(config);
        const cssVars = config.css_variables || generarCSSVariablesDesdeConfig(config);
        aplicarCSSVariables(cssVars);
        actualizarTituloDocumento(config.nombre_sistema);
      } else {
        aplicarCSSVariables(temaDefault.css_variables);
      }
    } catch (err) {
      console.warn('Tema: usando valores por defecto');
      aplicarCSSVariables(temaDefault.css_variables);
    } finally {
      setCargando(false);
    }
  }, []);

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
   * Actualiza el TemaGlobal completo (nuevo sistema)
   */
  const actualizarTemaGlobal = async (nuevoTema) => {
    try {
      const response = await temaGlobalAPI.updateTema(nuevoTema);
      const resultado = response.data;
      const tema = resultado.tema || resultado;
      
      setTemaGlobal(tema);
      if (tema.css_variables) {
        aplicarCSSVariables(tema.css_variables);
      }
      
      return { success: true, data: tema };
    } catch (err) {
      console.error('Error al actualizar tema global:', err);
      return { 
        success: false, 
        error: err.response?.data?.error || 'Error al actualizar el tema' 
      };
    }
  };

  /**
   * Sube un logo al TemaGlobal
   * @param {string} tipo - header, login, reportes, favicon, fondo_login, fondo_reportes
   * @param {File} file - archivo a subir
   */
  const subirLogoTema = async (tipo, file) => {
    try {
      const formData = new FormData();
      formData.append('archivo', file);
      
      const response = await temaGlobalAPI.subirLogo(tipo, formData);
      const resultado = response.data;
      const tema = resultado.tema || resultado;
      
      setTemaGlobal(tema);
      if (tema.css_variables) {
        aplicarCSSVariables(tema.css_variables);
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
