import { useState, useEffect, useCallback } from 'react';
import { ThemeContext } from './contexts';
import { configuracionAPI } from '../services/api';

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
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Carga la configuración del tema desde el backend
   */
  const cargarTema = useCallback(async () => {
    try {
      setCargando(true);
      setError(null);
      const response = await configuracionAPI.getTema();
      const config = response.data;
      
      if (config && config.css_variables) {
        setConfiguracion(config);
        aplicarCSSVariables(config.css_variables);
        
        // Actualizar el título del documento
        if (config.nombre_sistema) {
          document.title = config.nombre_sistema;
        }
      } else {
        // Respuesta inválida, usar tema por defecto
        aplicarCSSVariables(temaDefault.css_variables);
      }
    } catch (err) {
      // Silenciar error - usar tema por defecto sin bloquear la app
      console.warn('Tema: usando valores por defecto');
      aplicarCSSVariables(temaDefault.css_variables);
    } finally {
      setCargando(false);
    }
  }, []);

  /**
   * Actualiza la configuración del tema
   */
  const actualizarTema = async (nuevaConfig) => {
    try {
      const response = await configuracionAPI.updateTema(nuevaConfig);
      const config = response.data;
      
      setConfiguracion(config);
      // Aplicar CSS variables - usar las del backend o generarlas si no vienen
      const cssVars = config.css_variables || generarCSSVariablesDesdeConfig(config);
      aplicarCSSVariables(cssVars);
      
      // Actualizar título del documento si cambió
      actualizarTituloDocumento(config.nombre_sistema);
      
      return { success: true, data: config };
    } catch (err) {
      console.error('Error al actualizar el tema:', err);
      return { 
        success: false, 
        error: err.response?.data?.error || 'Error al actualizar el tema' 
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
      aplicarCSSVariables(config.css_variables);
      
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
      aplicarCSSVariables(config.css_variables);
      
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

  const value = {
    configuracion,
    cargando,
    error,
    cargarTema,
    actualizarTema,
    aplicarTemaPredefinido,
    restablecerTema,
    subirLogoHeader,
    subirLogoPdf,
    eliminarLogoHeader,
    eliminarLogoPdf,
    aplicarCSSVariablesLocalmente, // Para preview en tiempo real
    temaActivo: configuracion.tema_activo,
    nombreSistema: configuracion.nombre_sistema,
    temasDisponibles: configuracion.temas_disponibles || temaDefault.temas_disponibles,
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};
