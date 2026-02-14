/**
 * ConfiguracionTema - M├│dulo de personalizaci├│n del tema del sistema
 * @version 2.0.0 - ColorInput movido antes del componente principal (fix hoisting)
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { useTheme } from '../hooks/useTheme';
import { usePermissions } from '../hooks/usePermissions';
import { useConfirmation } from '../hooks/useConfirmation';
import TwoStepConfirmModal from '../components/TwoStepConfirmModal';
import { toast } from 'react-hot-toast';
import { 
  FaPalette, 
  FaImage, 
  FaUpload, 
  FaTrash, 
  FaSave, 
  FaUndo, 
  FaBuilding,
  FaFilePdf,
  FaDesktop,
  FaCheck,
  FaExclamationTriangle,
  FaLock,
  FaFont,
  FaFileAlt,
  FaGlobe,
  FaRedo,
  FaSpinner
} from 'react-icons/fa';
import './ConfiguracionTema.css';

/**
 * Expresi├│n regular para validar colores hex
 */
const HEX_COLOR_REGEX = /^#[0-9A-Fa-f]{6}$/;

/**
 * Valida si un string es un color hexadecimal v├ílido
 */
const esColorValido = (color) => {
  if (!color) return false;
  return HEX_COLOR_REGEX.test(color);
};

/**
 * Normaliza un color a formato hex v├ílido
 * Retorna el color si es v├ílido, o un fallback si no
 */
const normalizarColor = (color, fallback = '#000000') => {
  if (!color) return fallback;
  // Si ya es v├ílido, retornar
  if (esColorValido(color)) return color.toUpperCase();
  // Intentar agregar # si falta
  if (/^[0-9A-Fa-f]{6}$/.test(color)) return `#${color}`.toUpperCase();
  return fallback;
};

/**
 * Genera un color hover m├ís oscuro a partir de un color base
 * Oscurece el color un 15% aprox.
 */
const generarColorHover = (hexColor) => {
  if (!esColorValido(hexColor)) return hexColor;
  const hex = hexColor.replace('#', '');
  const r = Math.max(0, parseInt(hex.substring(0, 2), 16) - 30);
  const g = Math.max(0, parseInt(hex.substring(2, 4), 16) - 30);
  const b = Math.max(0, parseInt(hex.substring(4, 6), 16) - 30);
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`.toUpperCase();
};

/**
 * Componente de input de color mejorado con validaci├│n
 */
const ColorInput = ({ label, name, value, onChange, error, disabled }) => (
  <div>
    <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
    <div className="flex items-center gap-2">
      <input
        type="color"
        id={name}
        name={name}
        value={value && /^#[0-9A-Fa-f]{6}$/.test(value) ? value : '#000000'}
        onChange={onChange}
        disabled={disabled}
        className="w-10 h-10 rounded cursor-pointer border-0 disabled:opacity-50 disabled:cursor-not-allowed"
      />
      <input
        type="text"
        value={value || ''}
        onChange={onChange}
        name={name}
        placeholder="#000000"
        disabled={disabled}
        className={`flex-1 px-3 py-2 border rounded text-sm font-mono disabled:opacity-50 disabled:bg-gray-100 ${
          error ? 'border-red-500 bg-red-50' : 'border-gray-300'
        }`}
      />
    </div>
    {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
  </div>
);

/**
 * P├ígina de configuraci├│n del tema del sistema
 * Solo accesible por superusuarios
 * 
 * Funcionalidades:
 * - Selecci├│n de temas predefinidos
 * - Personalizaci├│n de colores
 * - Subida de logos (header e institucional para PDFs)
 * - Configuraci├│n de textos institucionales
 * - Vista previa en tiempo real
 */
const ConfiguracionTema = () => {
  const { user, permisos, loading: cargandoPermisos } = usePermissions();
  const { 
    configuracion, 
    temaGlobal,
    cargando: cargandoTema, 
    actualizarTema,
    actualizarTemaGlobal,
    aplicarTemaPredefinido, 
    restablecerTema,
    restablecerTemaInstitucional,
    subirLogoHeader,
    subirLogoPdf,
    subirLogoTema,
    eliminarLogoHeader,
    eliminarLogoPdf,
    eliminarLogoTema,
    temasDisponibles,
    aplicarCSSVariablesLocalmente, // Para preview en tiempo real
    cargarTema // Para recargar tema despu├®s de guardar
  } = useTheme();
  
  const [formData, setFormData] = useState({});
  const [temaSeleccionado, setTemaSeleccionado] = useState('');
  const [modoEdicion, setModoEdicion] = useState(false);
  const [activeTab, setActiveTab] = useState('temas');
  const [erroresColor, setErroresColor] = useState({});
  
  // Estados de carga separados para cada operaci├│n
  const [operacionEnCurso, setOperacionEnCurso] = useState({
    aplicandoTema: false,
    guardandoColores: false,
    guardandoIdentidad: false,
    guardandoReportes: false,
    restableciendo: false,
    restablecerInstitucional: false,
    subiendoLogoHeader: false,
    subiendoLogoPdf: false,
    subiendoLogoLogin: false,
    subiendoFavicon: false,
    subiendoFondoLogin: false,
    subiendoFondoReportes: false,
    eliminandoLogoHeader: false,
    eliminandoLogoPdf: false,
    eliminandoLogoLogin: false,
    eliminandoFavicon: false,
    eliminandoFondoLogin: false,
    eliminandoFondoReportes: false,
  });
  
  // Timeout de seguridad para operaciones bloqueadas (30 segundos)
  const TIMEOUT_OPERACION_MS = 30000;
  const timeoutRef = useRef(null);
  
  const logoHeaderRef = useRef(null);
  const logoPdfRef = useRef(null);
  const logoLoginRef = useRef(null);
  const faviconRef = useRef(null);
  const fondoLoginRef = useRef(null);
  const fondoReportesRef = useRef(null);

  // Verificar permisos usando el sistema de permisos coherente
  // Usa el permiso 'configurarTema' que incluye ADMIN y FARMACIA
  const tienePermisoTema = permisos?.configurarTema || user?.is_superuser || permisos?.esSuperusuario;
  const permisosResueltos = !cargandoPermisos && user !== undefined;
  
  // ISS-SEC: Hook de confirmaci├│n en dos pasos
  const {
    confirmState,
    requestDeleteConfirmation,
    executeWithConfirmation,
    cancelConfirmation
  } = useConfirmation();
  
  // Agrupar operaciones por tipo para permitir concurrencia entre grupos diferentes
  const operacionesBloqueantes = ['aplicandoTema', 'guardandoColores', 'restableciendo', 'restablecerInstitucional'];
  const operacionesLogos = [
    'subiendoLogoHeader', 'subiendoLogoPdf', 'subiendoLogoLogin', 'subiendoFavicon',
    'subiendoFondoLogin', 'subiendoFondoReportes',
    'eliminandoLogoHeader', 'eliminandoLogoPdf', 'eliminandoLogoLogin', 'eliminandoFavicon',
    'eliminandoFondoLogin', 'eliminandoFondoReportes'
  ];
  
  // Estado de operaciones por grupo (para bloqueo interno del grupo)
  const hayOperacionTemaEnCurso = operacionesBloqueantes.some(op => operacionEnCurso[op]);
  const hayOperacionLogoEnCurso = operacionesLogos.some(op => operacionEnCurso[op]);
  const hayOperacionIdentidadEnCurso = operacionEnCurso.guardandoIdentidad;
  const hayOperacionReportesEnCurso = operacionEnCurso.guardandoReportes;
  
  // Para deshabilitar UI global (indicador visual)
  const hayOperacionEnCurso = Object.values(operacionEnCurso).some(v => v);
  
  /**
   * Resetea todas las operaciones en curso (escape de seguridad)
   * ├Ütil cuando una operaci├│n queda bloqueada por error de red
   */
  const resetearOperaciones = useCallback(() => {
    setOperacionEnCurso({
      aplicandoTema: false,
      guardandoColores: false,
      guardandoIdentidad: false,
      guardandoReportes: false,
      restableciendo: false,
      restablecerInstitucional: false,
      subiendoLogoHeader: false,
      subiendoLogoPdf: false,
      subiendoLogoLogin: false,
      subiendoFavicon: false,
      subiendoFondoLogin: false,
      subiendoFondoReportes: false,
      eliminandoLogoHeader: false,
      eliminandoLogoPdf: false,
      eliminandoLogoLogin: false,
      eliminandoFavicon: false,
      eliminandoFondoLogin: false,
      eliminandoFondoReportes: false,
    });
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    toast.info('Operaciones desbloqueadas');
  }, []);

  // Inicializar formulario con datos actuales (preferir temaGlobal sobre configuracion legacy)
  useEffect(() => {
    const tema = temaGlobal || configuracion;
    if (tema) {
      // Mapear campos del TemaGlobal al formulario
      // Los campos vienen directamente del backend con los nombres de la BD
      
      setFormData({
        // Identidad (mapear desde nombres de BD)
        nombre_sistema: tema.titulo_sistema || tema.reporte_titulo_institucion || tema.nombre_sistema || '',
        nombre_institucion: tema.titulo_sistema || tema.nombre_institucion || '',
        subtitulo_institucion: tema.subtitulo_sistema || tema.subtitulo_institucion || '',
        
        // Colores principales (nombres directos de BD)
        color_primario: normalizarColor(tema.color_primario, '#9F2241'),
        color_primario_hover: normalizarColor(tema.color_primario_hover, '#6B1839'),
        color_secundario: normalizarColor(tema.color_secundario, '#424242'),
        color_acento: normalizarColor(tema.color_secundario, '#BC955C'), // Usar secundario como acento
        
        // Colores de fondo (nombres directos de BD)
        color_fondo: normalizarColor(tema.color_fondo_principal, '#F5F5F5'),
        color_fondo_sidebar: normalizarColor(tema.color_fondo_sidebar, '#9F2241'),
        color_fondo_header: normalizarColor(tema.color_fondo_header, '#9F2241'),
        color_fondo_card: normalizarColor(tema.color_fondo_principal, '#FFFFFF'), // Usar fondo principal
        
        // Colores de texto (nombres directos de BD)
        color_texto: normalizarColor(tema.color_texto_principal, '#212121'),
        color_texto_secundario: normalizarColor(tema.color_texto_principal, '#757575'),
        color_texto_sidebar: normalizarColor(tema.color_texto_sidebar, '#FFFFFF'),
        color_texto_header: normalizarColor(tema.color_texto_header, '#FFFFFF'),
        
        // Colores de estado (mapear color_alerta -> color_advertencia para UI)
        color_exito: normalizarColor(tema.color_exito, '#4CAF50'),
        color_advertencia: normalizarColor(tema.color_alerta, '#FF9800'),
        color_error: normalizarColor(tema.color_error, '#F44336'),
        color_info: normalizarColor(tema.color_info, '#2196F3'),
        
        // Tipograf├¡a (valores por defecto)
        fuente_principal: 'Montserrat',
        fuente_titulos: 'Montserrat',
        
        // Reportes (nombres directos de BD)
        reporte_color_encabezado: normalizarColor(tema.reporte_color_encabezado, '#9F2241'),
        reporte_color_texto_encabezado: normalizarColor(tema.reporte_color_texto, '#ffffff'),
        reporte_color_filas_alternas: '#f9fafb', // Valor por defecto, no existe en BD
        reporte_pie_pagina: '', // No existe en BD, valor por defecto
        reporte_ano_visible: true, // No existe en BD, valor por defecto
      });
      setTemaSeleccionado(tema.tema_activo || tema.nombre || 'default');
      setModoEdicion(false);
      setErroresColor({});
    }
  }, [temaGlobal, configuracion]);

  /**
   * Valida permisos antes de ejecutar una acci├│n
   */
  const validarPermisos = useCallback(() => {
    if (!tienePermisoTema) {
      toast.error('No tienes permisos para realizar esta acci├│n');
      return false;
    }
    return true;
  }, [tienePermisoTema]);

  /**
   * Handler gen├®rico para operaciones as├¡ncronas con manejo de errores
   * Permite concurrencia entre grupos de operaciones diferentes
   * Incluye timeout de seguridad para evitar bloqueos permanentes
   */
  const ejecutarOperacion = useCallback(async (nombreOperacion, operacion, mensajeExito, grupoBloqueo = 'tema') => {
    if (!validarPermisos()) return { success: false };
    
    // Verificar bloqueo solo dentro del mismo grupo
    const estaBloquado = grupoBloqueo === 'tema' ? hayOperacionTemaEnCurso :
                         grupoBloqueo === 'logo' ? hayOperacionLogoEnCurso :
                         grupoBloqueo === 'identidad' ? hayOperacionIdentidadEnCurso :
                         grupoBloqueo === 'reportes' ? hayOperacionReportesEnCurso : false;
    
    if (estaBloquado) {
      toast.error('Espera a que termine la operaci├│n actual');
      return { success: false };
    }

    setOperacionEnCurso(prev => ({ ...prev, [nombreOperacion]: true }));
    
    // Configurar timeout de seguridad
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => {
      setOperacionEnCurso(prev => {
        if (prev[nombreOperacion]) {
          toast.error('La operaci├│n tard├│ demasiado. Se ha desbloqueado autom├íticamente.');
          return { ...prev, [nombreOperacion]: false };
        }
        return prev;
      });
    }, TIMEOUT_OPERACION_MS);
    
    try {
      const resultado = await operacion();
      
      if (resultado.success) {
        toast.success(mensajeExito);
        return resultado;
      } else {
        toast.error(resultado.error || 'Error en la operaci├│n');
        return resultado;
      }
    } catch (error) {
      console.error(`Error en ${nombreOperacion}:`, error);
      const mensaje = error.response?.data?.error || 
                      error.message || 
                      'Error de conexi├│n. Intenta de nuevo.';
      toast.error(mensaje);
      return { success: false, error: mensaje };
    } finally {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      setOperacionEnCurso(prev => ({ ...prev, [nombreOperacion]: false }));
    }
  }, [validarPermisos, hayOperacionTemaEnCurso, hayOperacionLogoEnCurso, hayOperacionIdentidadEnCurso, hayOperacionReportesEnCurso]);

  /**
   * Maneja cambios en inputs de texto
   */
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setModoEdicion(true);
  };

  /**
   * Maneja cambios en inputs de color con validaci├│n
   * Aplica preview en tiempo real si el color es v├ílido
   */
  const handleColorChange = (e) => {
    const { name, value } = e.target;
    
    // Siempre actualizar el formData para que el usuario vea lo que escribe
    const nuevoFormData = { ...formData, [name]: value };
    setFormData(nuevoFormData);
    setModoEdicion(true);
    
    // Validar el color
    if (value && !esColorValido(value)) {
      setErroresColor(prev => ({ ...prev, [name]: 'Formato inv├ílido. Use #RRGGBB' }));
    } else {
      setErroresColor(prev => {
        const nuevos = { ...prev };
        delete nuevos[name];
        return nuevos;
      });
      
      // Aplicar preview en tiempo real si el color es v├ílido
      if (esColorValido(value)) {
        aplicarCSSVariablesLocalmente(nuevoFormData);
      }
    }
  };

  /**
   * Valida todos los colores antes de guardar
   */
  const validarColoresAntesDeGuardar = () => {
    const camposColor = [
      'color_primario', 'color_primario_hover', 'color_secundario', 'color_acento',
      'color_fondo', 'color_fondo_sidebar', 'color_fondo_header', 'color_fondo_card',
      'color_texto', 'color_texto_secundario', 'color_texto_sidebar', 'color_texto_header',
      'color_exito', 'color_advertencia', 'color_error', 'color_info'
    ];
    
    const errores = {};
    camposColor.forEach(campo => {
      if (formData[campo] && !esColorValido(formData[campo])) {
        errores[campo] = 'Color inv├ílido';
      }
    });
    
    if (Object.keys(errores).length > 0) {
      setErroresColor(errores);
      return false;
    }
    return true;
  };

  /**
   * Aplica un tema predefinido
   */
  const handleTemaChange = async (tema) => {
    if (tema === 'custom') {
      setTemaSeleccionado('custom');
      setModoEdicion(true);
      return;
    }
    
    // Evitar llamadas redundantes si el tema ya est├í activo
    if (tema === temaSeleccionado && tema === configuracion?.tema_activo) {
      toast.info('Este tema ya est├í activo');
      return;
    }

    const resultado = await ejecutarOperacion(
      'aplicandoTema',
      () => aplicarTemaPredefinido(tema),
      `Tema "${tema}" aplicado correctamente`,
      'tema'
    );

    if (resultado.success) {
      setTemaSeleccionado(tema);
      setModoEdicion(false);
    }
  };

  /**
   * Guarda los colores personalizados usando TemaGlobal API
   * NOTA: Los colores hover se generan autom├íticamente oscureciendo el color base
   */
  const handleGuardar = async () => {
    if (!validarColoresAntesDeGuardar()) {
      toast.error('Corrige los colores con formato inv├ílido');
      return;
    }

    // Preparar datos para TemaGlobal - mapeo directo a columnas de BD
    // Los colores hover se generan autom├íticamente oscureciendo el color base
    const datosActualizacion = {
      // Colores principales con hover generado
      color_primario: formData.color_primario,
      color_primario_hover: formData.color_primario_hover || generarColorHover(formData.color_primario),
      color_secundario: formData.color_secundario,
      color_secundario_hover: generarColorHover(formData.color_secundario),
      // Colores de fondo
      color_fondo_principal: formData.color_fondo,
      color_fondo_sidebar: formData.color_fondo_sidebar,
      color_fondo_header: formData.color_fondo_header,
      // Colores de texto
      color_texto_principal: formData.color_texto,
      color_texto_sidebar: formData.color_texto_sidebar,
      color_texto_header: formData.color_texto_header,
      color_texto_links: formData.color_primario,
      // Colores de estado con hover generado autom├íticamente
      color_exito: formData.color_exito,
      color_exito_hover: generarColorHover(formData.color_exito),
      color_alerta: formData.color_advertencia,
      color_alerta_hover: generarColorHover(formData.color_advertencia),
      color_error: formData.color_error,
      color_error_hover: generarColorHover(formData.color_error),
      color_info: formData.color_info,
      color_info_hover: generarColorHover(formData.color_info),
      // Bordes
      color_borde_inputs: '#E0E0E0',
      color_borde_focus: formData.color_primario,
    };

    const resultado = await ejecutarOperacion(
      'guardandoColores',
      () => actualizarTemaGlobal ? actualizarTemaGlobal(datosActualizacion) : actualizarTema({ ...formData, tema_activo: 'custom' }),
      'Configuraci├│n de colores guardada correctamente',
      'tema'
    );

    if (resultado.success) {
      setModoEdicion(false);
      // Forzar recarga del tema para aplicar cambios inmediatamente
      if (cargarTema) {
        setTimeout(() => cargarTema(), 500);
      }
    }
  };

  /**
   * Guarda la identidad institucional usando TemaGlobal
   */
  const handleGuardarIdentidad = async () => {
    const datosIdentidad = {
      titulo_sistema: formData.nombre_institucion || formData.nombre_sistema,
      subtitulo_sistema: formData.subtitulo_institucion,
    };

    const resultado = await ejecutarOperacion(
      'guardandoIdentidad',
      () => actualizarTemaGlobal ? actualizarTemaGlobal(datosIdentidad) : actualizarTema({
        ...formData,
      }),
      'Identidad institucional actualizada',
      'identidad'
    );

    if (resultado.success) {
      setModoEdicion(false);
    }
  };

  /**
   * Guarda la configuraci├│n de reportes usando TemaGlobal
   * Solo guarda campos que existen en BD: reporte_color_encabezado, reporte_color_texto
   */
  const handleGuardarReportes = async () => {
    const datosReportes = {
      reporte_color_encabezado: formData.reporte_color_encabezado,
      reporte_color_texto: formData.reporte_color_texto_encabezado,
    };

    const resultado = await ejecutarOperacion(
      'guardandoReportes',
      () => actualizarTemaGlobal ? actualizarTemaGlobal(datosReportes) : actualizarTema(datosReportes),
      'Configuraci├│n de reportes actualizada',
      'reportes'
    );

    if (resultado.success) {
      setModoEdicion(false);
    }
  };

  // ISS-SEC: Funci├│n de ejecuci├│n para restablecer tema
  const executeRestablecer = async () => {
    const resultado = await ejecutarOperacion(
      'restableciendo',
      restablecerTema,
      'Colores restablecidos a valores por defecto',
      'tema'
    );

    if (resultado.success) {
      setModoEdicion(false);
      setErroresColor({});
    }
  };

  /**
   * Restablece el tema a valores por defecto (legacy)
   * ISS-SEC: Ahora usa confirmaci├│n en 2 pasos
   */
  const handleRestablecer = () => {
    requestDeleteConfirmation({
      title: 'Restablecer colores',
      message: 'Esto restablecer├í todos los colores pero mantendr├í los logos e informaci├│n institucional.',
      itemInfo: { 'Acci├│n': 'Restablecer a valores por defecto' },
      onConfirm: executeRestablecer,
      isCritical: false,
      confirmText: 'Restablecer'
    });
  };

  /**
   * Restablece completamente al tema institucional (TemaGlobal)
   * Restaura colores, tipograf├¡as, logos y fondos oficiales
   */
  const handleRestablecerInstitucional = async () => {
  // ISS-SEC: Funci├│n de ejecuci├│n para restablecer tema institucional
  const executeRestablecerInstitucional = async () => {
    const resultado = await ejecutarOperacion(
      'restablecerInstitucional',
      restablecerTemaInstitucional,
      'Tema institucional restaurado completamente',
      'tema'
    );

    if (resultado.success) {
      setModoEdicion(false);
      setErroresColor({});
    }
  };

  /**
   * Restablece completamente al tema institucional (TemaGlobal)
   * Restaura colores, tipograf├¡as, logos y fondos oficiales
   * ISS-SEC: Ahora usa confirmaci├│n en 2 pasos con escritura obligatoria
   */
  const handleRestablecerInstitucional = () => {
    requestDeleteConfirmation({
      title: 'Restablecer tema institucional',
      message: 'Esta acci├│n restaurar├í todos los colores oficiales, tipograf├¡as, logos institucionales y fondos. Esta acci├│n no se puede deshacer.',
      itemInfo: {
        'Afectar├í': 'Colores, tipograf├¡as, logos y fondos',
        'Advertencia': 'Los cambios personalizados se perder├ín'
      },
      onConfirm: executeRestablecerInstitucional,
      isCritical: true,
      confirmPhrase: 'RESTABLECER',
      confirmText: 'Restablecer todo'
    });
  };

  /**
   * Sube el logo del header
   */
  const handleSubirLogoHeader = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validaciones
    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Formato no v├ílido. Use PNG, JPG o WebP');
      return;
    }
    if (file.size > 500 * 1024) {
      toast.error('El archivo no puede superar 500KB');
      return;
    }

    await ejecutarOperacion(
      'subiendoLogoHeader',
      () => subirLogoHeader(file),
      'Logo del header actualizado',
      'logo'
    );
    
    // Limpiar input
    if (logoHeaderRef.current) logoHeaderRef.current.value = '';
  };

  /**
   * Sube el logo para PDFs
   */
  const handleSubirLogoPdf = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validaciones
    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Formato no v├ílido. Use PNG o JPG');
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      toast.error('El archivo no puede superar 2MB');
      return;
    }

    await ejecutarOperacion(
      'subiendoLogoPdf',
      () => subirLogoPdf(file),
      'Logo para PDFs actualizado',
      'logo'
    );
    
    // Limpiar input
    if (logoPdfRef.current) logoPdfRef.current.value = '';
  };

  // ISS-SEC: Funci├│n de ejecuci├│n para eliminar logo header
  const executeEliminarLogoHeader = async () => {
    await ejecutarOperacion(
      'eliminandoLogoHeader',
      eliminarLogoHeader,
      'Logo del header eliminado',
      'logo'
    );
  };

  /**
   * Elimina el logo del header
   * ISS-SEC: Ahora usa confirmaci├│n en 2 pasos
   */
  const handleEliminarLogoHeader = () => {
    requestDeleteConfirmation({
      title: 'Eliminar logo del header',
      message: '┬┐Est├í seguro de eliminar el logo del header? Esta acci├│n no se puede deshacer.',
      itemInfo: { 'Tipo': 'Logo de encabezado' },
      onConfirm: executeEliminarLogoHeader,
      isCritical: false,
      confirmText: 'Eliminar'
    });
  };

  // ISS-SEC: Funci├│n de ejecuci├│n para eliminar logo PDF
  const executeEliminarLogoPdf = async () => {
    await ejecutarOperacion(
      'eliminandoLogoPdf',
      eliminarLogoPdf,
      'Logo para PDFs eliminado',
      'logo'
    );
  };

  /**
   * Elimina el logo para PDFs
   * ISS-SEC: Ahora usa confirmaci├│n en 2 pasos
   */
  const handleEliminarLogoPdf = () => {
    requestDeleteConfirmation({
      title: 'Eliminar logo para PDFs',
      message: '┬┐Est├í seguro de eliminar el logo para PDFs? Los reportes se generar├ín sin logo.',
      itemInfo: { 'Tipo': 'Logo de PDFs/Reportes' },
      onConfirm: executeEliminarLogoPdf,
      isCritical: false,
      confirmText: 'Eliminar'
    });
  };

  /**
   * Handler gen├®rico para subir logos usando TemaGlobal API
   * @param {string} tipo - header, login, reportes, favicon, fondo_login, fondo_reportes
   * @param {string} nombreOperacion - nombre para el estado de operaci├│n
   * @param {File} file - archivo a subir
   * @param {object} validaciones - { maxSize, allowedTypes }
   */
  const handleSubirLogoTema = async (tipo, nombreOperacion, file, validaciones) => {
    if (!file) return;

    const { maxSize = 500 * 1024, allowedTypes = ['image/png', 'image/jpeg', 'image/jpg'] } = validaciones;

    if (!allowedTypes.includes(file.type)) {
      toast.error('Formato no v├ílido');
      return;
    }
    if (file.size > maxSize) {
      toast.error(`El archivo no puede superar ${Math.round(maxSize / 1024)}KB`);
      return;
    }

    await ejecutarOperacion(
      nombreOperacion,
      () => subirLogoTema(tipo, file),
      `${tipo.charAt(0).toUpperCase() + tipo.slice(1).replace('_', ' ')} actualizado`,
      'logo'
    );
  };

  /**
   * Handler gen├®rico para eliminar logos usando TemaGlobal API
   * ISS-SEC: Ahora usa confirmaci├│n en 2 pasos
   */
  const handleEliminarLogoTema = (tipo, nombreOperacion, mensaje) => {
    const executeEliminar = async () => {
      await ejecutarOperacion(
        nombreOperacion,
        () => eliminarLogoTema(tipo),
        `${mensaje} eliminado`,
        'logo'
      );
    };

    requestDeleteConfirmation({
      title: `Eliminar ${mensaje}`,
      message: `┬┐Est├í seguro de eliminar ${mensaje.toLowerCase()}? Esta acci├│n no se puede deshacer.`,
      itemInfo: { 'Tipo': mensaje },
      onConfirm: executeEliminar,
      isCritical: false,
      confirmText: 'Eliminar'
    });
  };

  // Handlers espec├¡ficos para cada tipo de logo/imagen del TemaGlobal
  const handleSubirLogoLogin = async (e) => {
    await handleSubirLogoTema('login', 'subiendoLogoLogin', e.target.files[0], {
      maxSize: 500 * 1024,
      allowedTypes: ['image/png', 'image/jpeg', 'image/jpg', 'image/webp']
    });
    if (logoLoginRef.current) logoLoginRef.current.value = '';
  };

  const handleSubirFavicon = async (e) => {
    await handleSubirLogoTema('favicon', 'subiendoFavicon', e.target.files[0], {
      maxSize: 100 * 1024,
      allowedTypes: ['image/png', 'image/x-icon', 'image/ico', 'image/vnd.microsoft.icon']
    });
    if (faviconRef.current) faviconRef.current.value = '';
  };

  const handleSubirFondoLogin = async (e) => {
    await handleSubirLogoTema('fondo_login', 'subiendoFondoLogin', e.target.files[0], {
      maxSize: 2 * 1024 * 1024,
      allowedTypes: ['image/png', 'image/jpeg', 'image/jpg', 'image/webp']
    });
    if (fondoLoginRef.current) fondoLoginRef.current.value = '';
  };

  const handleSubirFondoReportes = async (e) => {
    await handleSubirLogoTema('fondo_reportes', 'subiendoFondoReportes', e.target.files[0], {
      maxSize: 2 * 1024 * 1024,
      allowedTypes: ['image/png', 'image/jpeg', 'image/jpg']
    });
    if (fondoReportesRef.current) fondoReportesRef.current.value = '';
  };

  const handleEliminarLogoLogin = () => handleEliminarLogoTema('login', 'eliminandoLogoLogin', 'el logo de login');
  const handleEliminarFavicon = () => handleEliminarLogoTema('favicon', 'eliminandoFavicon', 'el favicon');
  const handleEliminarFondoLogin = () => handleEliminarLogoTema('fondo_login', 'eliminandoFondoLogin', 'el fondo de login');
  const handleEliminarFondoReportes = () => handleEliminarLogoTema('fondo_reportes', 'eliminandoFondoReportes', 'el fondo de reportes');

  // Estado de carga inicial (permisos + tema)
  if (!permisosResueltos || cargandoTema) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <FaSpinner className="animate-spin text-4xl mx-auto mb-4 text-theme-primary" />
          <p className="text-gray-600">
            {!permisosResueltos ? 'Verificando permisos...' : 'Cargando configuraci├│n...'}
          </p>
        </div>
      </div>
    );
  }

  // Acceso restringido (solo despu├®s de resolver permisos)
  // Usa tienePermisoTema para ser coherente con el guard de rutas
  if (!tienePermisoTema) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white p-8 rounded-xl shadow-lg text-center max-w-md">
          <FaLock className="text-6xl text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Acceso Restringido</h2>
          <p className="text-gray-600">Solo los administradores del sistema y personal de farmacia pueden acceder a la configuraci├│n del tema.</p>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: 'temas', label: 'Temas', icon: FaPalette },
    { id: 'colores', label: 'Colores', icon: FaDesktop },
    { id: 'logos', label: 'Logos', icon: FaImage },
    { id: 'reportes', label: 'Reportes', icon: FaFileAlt },
    { id: 'identidad', label: 'Identidad', icon: FaBuilding },
  ];

  // Obtener URLs de logos desde temaGlobal o configuracion
  const logoUrls = {
    header: temaGlobal?.logo_header_url || temaGlobal?.logos?.header || configuracion?.logo_header_url,
    login: temaGlobal?.logo_login_url || temaGlobal?.logos?.login,
    reportes: temaGlobal?.logo_reportes_url || temaGlobal?.logos?.reportes || configuracion?.logo_pdf_url,
    favicon: temaGlobal?.favicon_url || temaGlobal?.logos?.favicon,
    fondoLogin: temaGlobal?.imagen_fondo_login_url || temaGlobal?.imagenes?.fondo_login,
    fondoReportes: temaGlobal?.imagen_fondo_reportes_url || temaGlobal?.imagenes?.fondo_reportes,
  };

  // Verifica si hay errores de color
  const hayErroresColor = Object.keys(erroresColor).length > 0;

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-lg p-6 border-l-4" style={{ borderLeftColor: 'var(--color-primary, #9F2241)' }}>
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-full" style={{ background: 'var(--color-sidebar-bg, linear-gradient(135deg, #9F2241 0%, #6B1839 100%))' }}>
            <FaPalette className="text-2xl text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Configuraci├│n del Tema</h1>
            <p className="text-gray-600">Personaliza la apariencia del sistema, logos y colores de reportes PDF</p>
          </div>
        </div>
      </div>

      {/* Indicador de operaci├│n en curso con bot├│n de desbloqueo */}
      {hayOperacionEnCurso && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FaSpinner className="animate-spin text-blue-500" />
            <span className="text-blue-700">Procesando...</span>
          </div>
          <button
            onClick={resetearOperaciones}
            className="text-sm text-blue-600 hover:text-blue-800 underline"
            title="Usar si la operaci├│n parece bloqueada"
          >
            Desbloquear
          </button>
        </div>
      )}

      {/* Tabs de navegaci├│n */}
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="flex border-b border-gray-200">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              disabled={hayOperacionEnCurso}
              className={`flex-1 flex items-center justify-center gap-2 px-6 py-4 font-medium transition-all disabled:opacity-50 ${
                activeTab === tab.id
                  ? 'text-white border-b-2'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
              style={activeTab === tab.id ? { 
                background: 'var(--color-sidebar-bg, linear-gradient(135deg, #9F2241 0%, #6B1839 100%))',
                borderBottomColor: 'var(--color-primary, #9F2241)'
              } : {}}
            >
              <tab.icon />
              {tab.label}
            </button>
          ))}
        </div>

        <div className="p-6">
          {/* TAB: Temas Predefinidos */}
          {activeTab === 'temas' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-800">Selecciona un Tema</h2>
                <span className="text-sm text-gray-500">
                  Tema activo: <span className="font-semibold text-theme-primary">{temaSeleccionado}</span>
                </span>
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                {temasDisponibles?.filter(t => t.id !== 'custom').map(tema => (
                  <button
                    key={tema.id}
                    className={`relative p-4 rounded-xl border-2 transition-all hover:scale-105 ${
                      temaSeleccionado === tema.id 
                        ? 'border-green-500 shadow-lg' 
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => handleTemaChange(tema.id)}
                    disabled={hayOperacionTemaEnCurso}
                  >
                    <div className={`tema-preview tema-${tema.id} rounded-lg overflow-hidden mb-3`}>
                      <div className="h-6 preview-header"></div>
                      <div className="flex h-16">
                        <div className="w-8 preview-sidebar"></div>
                        <div className="flex-1 preview-content p-2">
                          <div className="h-3 w-full bg-gray-300 rounded mb-1"></div>
                          <div className="h-3 w-2/3 bg-gray-200 rounded"></div>
                        </div>
                      </div>
                    </div>
                    <p className="text-sm font-medium text-gray-700 text-center">{tema.nombre}</p>
                    {temaSeleccionado === tema.id && (
                      <div className="absolute top-2 right-2 bg-green-500 text-white p-1 rounded-full">
                        <FaCheck className="text-xs" />
                      </div>
                    )}
                    {operacionEnCurso.aplicandoTema && temaSeleccionado !== tema.id && (
                      <div className="absolute inset-0 bg-white/50 rounded-xl flex items-center justify-center">
                        <FaSpinner className="animate-spin text-2xl text-gray-400" />
                      </div>
                    )}
                  </button>
                ))}
                
                {/* Opci├│n Personalizado */}
                <button
                  className={`relative p-4 rounded-xl border-2 transition-all hover:scale-105 ${
                    temaSeleccionado === 'custom' 
                      ? 'border-green-500 shadow-lg' 
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => {
                    setTemaSeleccionado('custom');
                    setActiveTab('colores');
                  }}
                  disabled={hayOperacionTemaEnCurso}
                >
                  <div className="h-[88px] rounded-lg bg-gradient-to-br from-pink-500 via-purple-500 to-indigo-500 flex items-center justify-center mb-3">
                    <FaPalette className="text-3xl text-white" />
                  </div>
                  <p className="text-sm font-medium text-gray-700 text-center">Personalizado</p>
                  {temaSeleccionado === 'custom' && (
                    <div className="absolute top-2 right-2 bg-green-500 text-white p-1 rounded-full">
                      <FaCheck className="text-xs" />
                    </div>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* TAB: Personalizaci├│n de Colores */}
          {activeTab === 'colores' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-800">Personalizaci├│n de Colores</h2>
                <div className="flex gap-2">
                  <button
                    onClick={handleRestablecer}
                    disabled={hayOperacionTemaEnCurso}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    {operacionEnCurso.restableciendo ? (
                      <FaSpinner className="animate-spin" />
                    ) : (
                      <FaUndo />
                    )}
                    Restablecer
                  </button>
                  <button
                    onClick={handleGuardar}
                    disabled={hayOperacionTemaEnCurso || !modoEdicion || hayErroresColor}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg text-white disabled:opacity-50 bg-theme-gradient"
                    title={hayErroresColor ? 'Corrige los errores de color primero' : ''}
                  >
                    {operacionEnCurso.guardandoColores ? (
                      <>
                        <FaSpinner className="animate-spin" />
                        Guardando...
                      </>
                    ) : (
                      <>
                        <FaSave /> Guardar Colores
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Alerta de errores de validaci├│n */}
              {hayErroresColor && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-center gap-3">
                  <FaExclamationTriangle className="text-red-500" />
                  <span className="text-red-700">Hay colores con formato inv├ílido. Usa el formato #RRGGBB (ej: #FF5500)</span>
                </div>
              )}

              <div className="grid md:grid-cols-2 gap-6">
                {/* Colores Principales */}
                <div className="bg-gray-50 p-5 rounded-xl">
                  <h3 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full" style={{ background: formData.color_primario }}></span>
                    Colores Principales
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <ColorInput label="Primario" name="color_primario" value={formData.color_primario} onChange={handleColorChange} error={erroresColor.color_primario} disabled={hayOperacionTemaEnCurso} />
                    <ColorInput label="Primario Hover" name="color_primario_hover" value={formData.color_primario_hover} onChange={handleColorChange} error={erroresColor.color_primario_hover} disabled={hayOperacionTemaEnCurso} />
                    <ColorInput label="Secundario" name="color_secundario" value={formData.color_secundario} onChange={handleColorChange} error={erroresColor.color_secundario} disabled={hayOperacionTemaEnCurso} />
                    <ColorInput label="Acento" name="color_acento" value={formData.color_acento} onChange={handleColorChange} error={erroresColor.color_acento} disabled={hayOperacionTemaEnCurso} />
                  </div>
                </div>

                {/* Colores de Fondo */}
                <div className="bg-gray-50 p-5 rounded-xl">
                  <h3 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full border" style={{ background: formData.color_fondo }}></span>
                    Colores de Fondo
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <ColorInput label="Fondo General" name="color_fondo" value={formData.color_fondo} onChange={handleColorChange} error={erroresColor.color_fondo} disabled={hayOperacionTemaEnCurso} />
                    <ColorInput label="Sidebar" name="color_fondo_sidebar" value={formData.color_fondo_sidebar} onChange={handleColorChange} error={erroresColor.color_fondo_sidebar} disabled={hayOperacionTemaEnCurso} />
                    <ColorInput label="Header" name="color_fondo_header" value={formData.color_fondo_header} onChange={handleColorChange} error={erroresColor.color_fondo_header} disabled={hayOperacionTemaEnCurso} />
                    <ColorInput label="Tarjetas" name="color_fondo_card" value={formData.color_fondo_card} onChange={handleColorChange} error={erroresColor.color_fondo_card} disabled={hayOperacionTemaEnCurso} />
                  </div>
                </div>

                {/* Colores de Texto */}
                <div className="bg-gray-50 p-5 rounded-xl">
                  <h3 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full" style={{ background: formData.color_texto }}></span>
                    Colores de Texto
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <ColorInput label="Texto Principal" name="color_texto" value={formData.color_texto} onChange={handleColorChange} error={erroresColor.color_texto} disabled={hayOperacionTemaEnCurso} />
                    <ColorInput label="Texto Secundario" name="color_texto_secundario" value={formData.color_texto_secundario} onChange={handleColorChange} error={erroresColor.color_texto_secundario} disabled={hayOperacionTemaEnCurso} />
                    <ColorInput label="Texto Sidebar" name="color_texto_sidebar" value={formData.color_texto_sidebar} onChange={handleColorChange} error={erroresColor.color_texto_sidebar} disabled={hayOperacionTemaEnCurso} />
                    <ColorInput label="Texto Header" name="color_texto_header" value={formData.color_texto_header} onChange={handleColorChange} error={erroresColor.color_texto_header} disabled={hayOperacionTemaEnCurso} />
                  </div>
                </div>

                {/* Colores de Estado */}
                <div className="bg-gray-50 p-5 rounded-xl">
                  <h3 className="font-semibold text-gray-700 mb-4">Colores de Estado</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <ColorInput label="├ëxito" name="color_exito" value={formData.color_exito} onChange={handleColorChange} error={erroresColor.color_exito} disabled={hayOperacionTemaEnCurso} />
                    <ColorInput label="Advertencia" name="color_advertencia" value={formData.color_advertencia} onChange={handleColorChange} error={erroresColor.color_advertencia} disabled={hayOperacionTemaEnCurso} />
                    <ColorInput label="Error" name="color_error" value={formData.color_error} onChange={handleColorChange} error={erroresColor.color_error} disabled={hayOperacionTemaEnCurso} />
                    <ColorInput label="Info" name="color_info" value={formData.color_info} onChange={handleColorChange} error={erroresColor.color_info} disabled={hayOperacionTemaEnCurso} />
                  </div>
                </div>
              </div>

              {/* Vista Previa */}
              <div className="mt-6">
                <h3 className="font-semibold text-gray-700 mb-4">Vista Previa</h3>
                <div 
                  className="rounded-xl overflow-hidden border shadow-lg"
                  style={{ background: formData.color_fondo }}
                >
                  <div className="flex h-64">
                    {/* Sidebar Preview */}
                    <div className="w-48 p-4" style={{ background: formData.color_fondo_sidebar }}>
                      <div className="text-lg font-bold mb-4" style={{ color: formData.color_texto_sidebar }}>
                        Menu
                      </div>
                      <div className="space-y-2">
                        <div className="px-3 py-2 rounded" style={{ background: formData.color_primario, color: formData.color_texto_header }}>
                          Dashboard
                        </div>
                        <div className="px-3 py-2 rounded" style={{ color: formData.color_texto_sidebar }}>
                          Productos
                        </div>
                        <div className="px-3 py-2 rounded" style={{ color: formData.color_texto_sidebar }}>
                          Reportes
                        </div>
                      </div>
                    </div>
                    
                    {/* Main Content Preview */}
                    <div className="flex-1 flex flex-col">
                      <div className="px-4 py-3 flex items-center justify-between" style={{ background: formData.color_fondo_header }}>
                        <span className="font-semibold" style={{ color: formData.color_texto_header }}>
                          {formData.nombre_sistema || 'Sistema'}
                        </span>
                        <span style={{ color: formData.color_texto_header }}>Usuario</span>
                      </div>
                      <div className="flex-1 p-4">
                        <div className="rounded-lg shadow p-4 mb-4" style={{ background: formData.color_fondo_card }}>
                          <h4 className="font-semibold mb-2" style={{ color: formData.color_texto }}>Tarjeta de Ejemplo</h4>
                          <p className="text-sm mb-3" style={{ color: formData.color_texto_secundario }}>
                            Texto secundario de ejemplo
                          </p>
                          <div className="flex gap-2">
                            <button className="px-3 py-1 rounded text-sm text-white" style={{ background: formData.color_primario }}>
                              Primario
                            </button>
                            <button className="px-3 py-1 rounded text-sm text-white" style={{ background: formData.color_exito }}>
                              ├ëxito
                            </button>
                            <button className="px-3 py-1 rounded text-sm text-white" style={{ background: formData.color_error }}>
                              Error
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB: Logos */}
          {activeTab === 'logos' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-800">Gesti├│n de Logos e Im├ígenes</h2>
                {restablecerTemaInstitucional && (
                  <button
                    onClick={handleRestablecerInstitucional}
                    disabled={hayOperacionTemaEnCurso}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50 disabled:opacity-50"
                  >
                    {operacionEnCurso.restablecerInstitucional ? (
                      <FaSpinner className="animate-spin text-red-500" />
                    ) : (
                      <FaRedo />
                    )}
                    Restablecer Todo
                  </button>
                )}
              </div>

              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* Logo Header */}
                <div className="bg-gray-50 p-6 rounded-xl">
                  <div className="flex items-center gap-3 mb-4">
                    <FaDesktop className="text-xl text-gray-600" />
                    <div>
                      <h3 className="font-semibold text-gray-800">Logo del Header</h3>
                      <p className="text-sm text-gray-500">Barra superior del sistema</p>
                    </div>
                  </div>
                  
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center mb-4 bg-white min-h-[100px] flex items-center justify-center">
                    {logoUrls.header ? (
                      <img src={logoUrls.header} alt="Logo Header" className="max-h-20 mx-auto object-contain" />
                    ) : (
                      <div className="text-gray-400">
                        <FaImage className="text-3xl mx-auto mb-2" />
                        <p className="text-sm">Sin logo</p>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex gap-2">
                    <input type="file" ref={logoHeaderRef} onChange={handleSubirLogoHeader} accept="image/png,image/jpeg,image/jpg,image/webp" className="hidden" disabled={hayOperacionLogoEnCurso} />
                    <button onClick={() => logoHeaderRef.current?.click()} disabled={hayOperacionLogoEnCurso} className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-white text-sm disabled:opacity-50 bg-theme-gradient">
                      {operacionEnCurso.subiendoLogoHeader ? <FaSpinner className="animate-spin" /> : <FaUpload />}
                      {logoUrls.header ? 'Cambiar' : 'Subir'}
                    </button>
                    {logoUrls.header && (
                      <button onClick={handleEliminarLogoHeader} disabled={hayOperacionLogoEnCurso} className="px-3 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50 disabled:opacity-50">
                        {operacionEnCurso.eliminandoLogoHeader ? <FaSpinner className="animate-spin text-red-500" /> : <FaTrash />}
                      </button>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-2">PNG, JPG, WebP. M├íx 500KB</p>
                </div>

                {/* Logo Login */}
                <div className="bg-gray-50 p-6 rounded-xl">
                  <div className="flex items-center gap-3 mb-4">
                    <FaGlobe className="text-xl text-blue-600" />
                    <div>
                      <h3 className="font-semibold text-gray-800">Logo de Login</h3>
                      <p className="text-sm text-gray-500">Pantalla de inicio de sesi├│n</p>
                    </div>
                  </div>
                  
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center mb-4 bg-white min-h-[100px] flex items-center justify-center">
                    {logoUrls.login ? (
                      <img src={logoUrls.login} alt="Logo Login" className="max-h-20 mx-auto object-contain" />
                    ) : (
                      <div className="text-gray-400">
                        <FaGlobe className="text-3xl mx-auto mb-2" />
                        <p className="text-sm">Sin logo</p>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex gap-2">
                    <input type="file" ref={logoLoginRef} onChange={handleSubirLogoLogin} accept="image/png,image/jpeg,image/jpg,image/webp" className="hidden" disabled={hayOperacionLogoEnCurso} />
                    <button onClick={() => logoLoginRef.current?.click()} disabled={hayOperacionLogoEnCurso} className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-white text-sm disabled:opacity-50" style={{ background: 'linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)' }}>
                      {operacionEnCurso.subiendoLogoLogin ? <FaSpinner className="animate-spin" /> : <FaUpload />}
                      {logoUrls.login ? 'Cambiar' : 'Subir'}
                    </button>
                    {logoUrls.login && (
                      <button onClick={handleEliminarLogoLogin} disabled={hayOperacionLogoEnCurso} className="px-3 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50 disabled:opacity-50">
                        {operacionEnCurso.eliminandoLogoLogin ? <FaSpinner className="animate-spin text-red-500" /> : <FaTrash />}
                      </button>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-2">PNG, JPG, WebP. M├íx 500KB</p>
                </div>

                {/* Logo Reportes */}
                <div className="bg-gray-50 p-6 rounded-xl">
                  <div className="flex items-center gap-3 mb-4">
                    <FaFilePdf className="text-xl text-red-600" />
                    <div>
                      <h3 className="font-semibold text-gray-800">Logo de Reportes</h3>
                      <p className="text-sm text-gray-500">Encabezado de PDFs</p>
                    </div>
                  </div>
                  
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center mb-4 bg-white min-h-[100px] flex items-center justify-center">
                    {logoUrls.reportes ? (
                      <img src={logoUrls.reportes} alt="Logo Reportes" className="max-h-20 mx-auto object-contain" />
                    ) : (
                      <div className="text-gray-400">
                        <FaFilePdf className="text-3xl mx-auto mb-2" />
                        <p className="text-sm">Sin logo</p>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex gap-2">
                    <input type="file" ref={logoPdfRef} onChange={handleSubirLogoPdf} accept="image/png,image/jpeg,image/jpg" className="hidden" disabled={hayOperacionLogoEnCurso} />
                    <button onClick={() => logoPdfRef.current?.click()} disabled={hayOperacionLogoEnCurso} className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-white text-sm disabled:opacity-50" style={{ background: 'linear-gradient(135deg, #DC2626 0%, #991B1B 100%)' }}>
                      {operacionEnCurso.subiendoLogoPdf ? <FaSpinner className="animate-spin" /> : <FaUpload />}
                      {logoUrls.reportes ? 'Cambiar' : 'Subir'}
                    </button>
                    {logoUrls.reportes && (
                      <button onClick={handleEliminarLogoPdf} disabled={hayOperacionLogoEnCurso} className="px-3 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50 disabled:opacity-50">
                        {operacionEnCurso.eliminandoLogoPdf ? <FaSpinner className="animate-spin text-red-500" /> : <FaTrash />}
                      </button>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-2">PNG, JPG. M├íx 2MB</p>
                </div>

                {/* Favicon */}
                <div className="bg-gray-50 p-6 rounded-xl">
                  <div className="flex items-center gap-3 mb-4">
                    <FaImage className="text-xl text-purple-600" />
                    <div>
                      <h3 className="font-semibold text-gray-800">Favicon</h3>
                      <p className="text-sm text-gray-500">Icono del navegador</p>
                    </div>
                  </div>
                  
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center mb-4 bg-white min-h-[100px] flex items-center justify-center">
                    {logoUrls.favicon ? (
                      <img src={logoUrls.favicon} alt="Favicon" className="max-h-16 mx-auto object-contain" />
                    ) : (
                      <div className="text-gray-400">
                        <FaImage className="text-3xl mx-auto mb-2" />
                        <p className="text-sm">Sin favicon</p>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex gap-2">
                    <input type="file" ref={faviconRef} onChange={handleSubirFavicon} accept="image/png,image/x-icon,image/ico" className="hidden" disabled={hayOperacionLogoEnCurso} />
                    <button onClick={() => faviconRef.current?.click()} disabled={hayOperacionLogoEnCurso} className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-white text-sm disabled:opacity-50" style={{ background: 'linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)' }}>
                      {operacionEnCurso.subiendoFavicon ? <FaSpinner className="animate-spin" /> : <FaUpload />}
                      {logoUrls.favicon ? 'Cambiar' : 'Subir'}
                    </button>
                    {logoUrls.favicon && (
                      <button onClick={handleEliminarFavicon} disabled={hayOperacionLogoEnCurso} className="px-3 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50 disabled:opacity-50">
                        {operacionEnCurso.eliminandoFavicon ? <FaSpinner className="animate-spin text-red-500" /> : <FaTrash />}
                      </button>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-2">PNG, ICO. M├íx 100KB. 32x32 recomendado</p>
                </div>

                {/* Fondo Login */}
                <div className="bg-gray-50 p-6 rounded-xl">
                  <div className="flex items-center gap-3 mb-4">
                    <FaDesktop className="text-xl text-teal-600" />
                    <div>
                      <h3 className="font-semibold text-gray-800">Fondo de Login</h3>
                      <p className="text-sm text-gray-500">Imagen de fondo en login</p>
                    </div>
                  </div>
                  
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center mb-4 bg-white min-h-[100px] flex items-center justify-center">
                    {logoUrls.fondoLogin ? (
                      <img src={logoUrls.fondoLogin} alt="Fondo Login" className="max-h-20 mx-auto object-contain" />
                    ) : (
                      <div className="text-gray-400">
                        <FaDesktop className="text-3xl mx-auto mb-2" />
                        <p className="text-sm">Sin fondo</p>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex gap-2">
                    <input type="file" ref={fondoLoginRef} onChange={handleSubirFondoLogin} accept="image/png,image/jpeg,image/jpg,image/webp" className="hidden" disabled={hayOperacionLogoEnCurso} />
                    <button onClick={() => fondoLoginRef.current?.click()} disabled={hayOperacionLogoEnCurso} className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-white text-sm disabled:opacity-50" style={{ background: 'linear-gradient(135deg, #14B8A6 0%, #0D9488 100%)' }}>
                      {operacionEnCurso.subiendoFondoLogin ? <FaSpinner className="animate-spin" /> : <FaUpload />}
                      {logoUrls.fondoLogin ? 'Cambiar' : 'Subir'}
                    </button>
                    {logoUrls.fondoLogin && (
                      <button onClick={handleEliminarFondoLogin} disabled={hayOperacionLogoEnCurso} className="px-3 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50 disabled:opacity-50">
                        {operacionEnCurso.eliminandoFondoLogin ? <FaSpinner className="animate-spin text-red-500" /> : <FaTrash />}
                      </button>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-2">PNG, JPG, WebP. M├íx 2MB</p>
                </div>

                {/* Fondo Reportes */}
                <div className="bg-gray-50 p-6 rounded-xl">
                  <div className="flex items-center gap-3 mb-4">
                    <FaFileAlt className="text-xl text-orange-600" />
                    <div>
                      <h3 className="font-semibold text-gray-800">Fondo de Reportes</h3>
                      <p className="text-sm text-gray-500">Marca de agua en PDFs</p>
                    </div>
                  </div>
                  
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center mb-4 bg-white min-h-[100px] flex items-center justify-center">
                    {logoUrls.fondoReportes ? (
                      <img src={logoUrls.fondoReportes} alt="Fondo Reportes" className="max-h-20 mx-auto object-contain" />
                    ) : (
                      <div className="text-gray-400">
                        <FaFileAlt className="text-3xl mx-auto mb-2" />
                        <p className="text-sm">Sin fondo</p>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex gap-2">
                    <input type="file" ref={fondoReportesRef} onChange={handleSubirFondoReportes} accept="image/png,image/jpeg,image/jpg" className="hidden" disabled={hayOperacionLogoEnCurso} />
                    <button onClick={() => fondoReportesRef.current?.click()} disabled={hayOperacionLogoEnCurso} className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-white text-sm disabled:opacity-50" style={{ background: 'linear-gradient(135deg, #F97316 0%, #EA580C 100%)' }}>
                      {operacionEnCurso.subiendoFondoReportes ? <FaSpinner className="animate-spin" /> : <FaUpload />}
                      {logoUrls.fondoReportes ? 'Cambiar' : 'Subir'}
                    </button>
                    {logoUrls.fondoReportes && (
                      <button onClick={handleEliminarFondoReportes} disabled={hayOperacionLogoEnCurso} className="px-3 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50 disabled:opacity-50">
                        {operacionEnCurso.eliminandoFondoReportes ? <FaSpinner className="animate-spin text-red-500" /> : <FaTrash />}
                      </button>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-2">PNG, JPG. M├íx 2MB</p>
                </div>
              </div>
            </div>
          )}

          {/* TAB: Reportes */}
          {activeTab === 'reportes' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-800">Configuraci├│n de Reportes PDF</h2>
                <button
                  onClick={handleGuardarReportes}
                  disabled={hayOperacionReportesEnCurso}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-white disabled:opacity-50 bg-theme-gradient"
                >
                  {operacionEnCurso.guardandoReportes ? (
                    <>
                      <FaSpinner className="animate-spin" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      <FaSave /> Guardar Configuraci├│n
                    </>
                  )}
                </button>
              </div>

              {/* Aviso sobre campos persistentes */}
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-3">
                <FaExclamationTriangle className="text-amber-500 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-amber-700">
                  <strong>Nota:</strong> Solo los colores de encabezado y texto se guardan en la base de datos. 
                  Las opciones de "Filas Alternas", "Pie de P├ígina" y "A├▒o Visible" aplican solo durante esta sesi├│n.
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                {/* Colores de Reportes */}
                <div className="bg-gray-50 p-5 rounded-xl">
                  <h3 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                    <FaPalette className="text-gray-500" />
                    Colores de Tablas en Reportes
                  </h3>
                  <div className="space-y-4">
                    <ColorInput 
                      label="Color de Encabezado" 
                      name="reporte_color_encabezado" 
                      value={formData.reporte_color_encabezado} 
                      onChange={handleColorChange} 
                      disabled={hayOperacionReportesEnCurso} 
                    />
                    <ColorInput 
                      label="Color de Texto Encabezado" 
                      name="reporte_color_texto_encabezado" 
                      value={formData.reporte_color_texto_encabezado} 
                      onChange={handleColorChange} 
                      disabled={hayOperacionReportesEnCurso} 
                    />
                    <ColorInput 
                      label="Color Filas Alternas (solo vista previa)" 
                      name="reporte_color_filas_alternas" 
                      value={formData.reporte_color_filas_alternas} 
                      onChange={handleColorChange} 
                      disabled={hayOperacionReportesEnCurso} 
                    />
                  </div>
                </div>

                {/* Configuraci├│n adicional */}
                <div className="bg-gray-50 p-5 rounded-xl">
                  <h3 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                    <FaFileAlt className="text-gray-500" />
                    Textos y Opciones
                  </h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Pie de P├ígina
                      </label>
                      <input
                        type="text"
                        name="reporte_pie_pagina"
                        value={formData.reporte_pie_pagina || ''}
                        onChange={handleInputChange}
                        placeholder="Texto del pie de p├ígina en reportes"
                        disabled={hayOperacionReportesEnCurso}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-pink-500 disabled:opacity-50 disabled:bg-gray-100"
                      />
                    </div>
                    <div>
                      <label className="flex items-center gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          name="reporte_ano_visible"
                          checked={formData.reporte_ano_visible ?? true}
                          onChange={(e) => {
                            setFormData(prev => ({ ...prev, reporte_ano_visible: e.target.checked }));
                            setModoEdicion(true);
                          }}
                          disabled={hayOperacionReportesEnCurso}
                          className="w-5 h-5 rounded border-gray-300 text-pink-600 focus:ring-pink-500"
                        />
                        <span className="text-sm font-medium text-gray-700">
                          Mostrar a├▒o en reportes
                        </span>
                      </label>
                      <p className="text-xs text-gray-500 mt-1 ml-8">
                        Muestra el a├▒o actual en el encabezado de los reportes PDF
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Vista previa de tabla de reporte */}
              <div className="mt-6">
                <h3 className="font-semibold text-gray-700 mb-4">Vista Previa de Tabla</h3>
                <div className="bg-white rounded-lg border shadow overflow-hidden">
                  <table className="w-full">
                    <thead>
                      <tr style={{ backgroundColor: formData.reporte_color_encabezado, color: formData.reporte_color_texto_encabezado }}>
                        <th className="px-4 py-3 text-left font-semibold">Producto</th>
                        <th className="px-4 py-3 text-left font-semibold">Cantidad</th>
                        <th className="px-4 py-3 text-left font-semibold">Precio</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="px-4 py-3">Producto A</td>
                        <td className="px-4 py-3">100</td>
                        <td className="px-4 py-3">$50.00</td>
                      </tr>
                      <tr style={{ backgroundColor: formData.reporte_color_filas_alternas }}>
                        <td className="px-4 py-3">Producto B</td>
                        <td className="px-4 py-3">250</td>
                        <td className="px-4 py-3">$75.00</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-3">Producto C</td>
                        <td className="px-4 py-3">50</td>
                        <td className="px-4 py-3">$120.00</td>
                      </tr>
                    </tbody>
                  </table>
                  {formData.reporte_pie_pagina && (
                    <div className="border-t px-4 py-2 text-xs text-gray-500 text-center">
                      {formData.reporte_pie_pagina} {formData.reporte_ano_visible && `- ${new Date().getFullYear()}`}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB: Identidad Institucional */}
          {activeTab === 'identidad' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-800">Identidad Institucional</h2>
                <button
                  onClick={handleGuardarIdentidad}
                  disabled={hayOperacionIdentidadEnCurso}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-white disabled:opacity-50 bg-theme-gradient"
                >
                  {operacionEnCurso.guardandoIdentidad ? (
                    <>
                      <FaSpinner className="animate-spin" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      <FaSave /> Guardar
                    </>
                  )}
                </button>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Nombre del Sistema
                    </label>
                    <input
                      type="text"
                      name="nombre_sistema"
                      value={formData.nombre_sistema || ''}
                      onChange={handleInputChange}
                      placeholder="Sistema de Farmacia Penitenciaria"
                      disabled={hayOperacionIdentidadEnCurso}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-pink-500 disabled:opacity-50 disabled:bg-gray-100"
                    />
                    <p className="text-xs text-gray-500 mt-1">Aparece en el t├¡tulo del navegador y header</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Nombre de la Instituci├│n
                    </label>
                    <input
                      type="text"
                      name="nombre_institucion"
                      value={formData.nombre_institucion || ''}
                      onChange={handleInputChange}
                      placeholder="Secretar├¡a de Seguridad"
                      disabled={hayOperacionIdentidadEnCurso}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-pink-500 disabled:opacity-50 disabled:bg-gray-100"
                    />
                    <p className="text-xs text-gray-500 mt-1">T├¡tulo principal en reportes PDF</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Subt├¡tulo de la Instituci├│n
                    </label>
                    <input
                      type="text"
                      name="subtitulo_institucion"
                      value={formData.subtitulo_institucion || ''}
                      onChange={handleInputChange}
                      placeholder="Direcci├│n General de Prevenci├│n y Reinserci├│n Social"
                      disabled={hayOperacionIdentidadEnCurso}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-pink-500 disabled:opacity-50 disabled:bg-gray-100"
                    />
                    <p className="text-xs text-gray-500 mt-1">Subt├¡tulo en reportes PDF</p>
                  </div>
                </div>

                {/* Vista previa de encabezado de reporte */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Vista Previa de Encabezado PDF
                  </label>
                  <div className="border rounded-lg p-6 bg-white shadow-inner">
                    <div className="text-center border-b pb-4">
                      {logoUrls.reportes ? (
                        <img 
                          src={logoUrls.reportes} 
                          alt="Logo" 
                          className="h-16 mx-auto mb-2 object-contain"
                        />
                      ) : (
                        <div className="w-16 h-16 mx-auto mb-2 bg-gray-200 rounded flex items-center justify-center">
                          <FaBuilding className="text-gray-400 text-2xl" />
                        </div>
                      )}
                      <h3 className="text-lg font-bold text-gray-800">
                        {formData.nombre_institucion || 'Nombre de la Instituci├│n'}
                      </h3>
                      <p className="text-sm text-gray-600">
                        {formData.subtitulo_institucion || 'Subt├¡tulo de la Instituci├│n'}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {formData.nombre_sistema || 'Sistema de Farmacia'}
                        {formData.reporte_ano_visible && ` - ${new Date().getFullYear()}`}
                      </p>
                    </div>
                    <div className="mt-4 text-center text-xs text-gray-400">
                      [Contenido del reporte]
                    </div>
                    {formData.reporte_pie_pagina && (
                      <div className="mt-4 pt-2 border-t text-center text-xs text-gray-500">
                        {formData.reporte_pie_pagina}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Modal de confirmaci├│n en dos pasos */}
      <TwoStepConfirmModal
        isOpen={confirmState.isOpen}
        onClose={cancelConfirmation}
        onConfirm={() => executeWithConfirmation(confirmState.onConfirm)}
        title={confirmState.title}
        message={confirmState.message}
        itemInfo={confirmState.itemInfo}
        confirmText={confirmState.confirmText}
        cancelText={confirmState.cancelText}
        actionType={confirmState.actionType}
        isCritical={confirmState.isCritical}
        confirmPhrase={confirmState.confirmPhrase}
        isLoading={confirmState.isLoading}
      />
    </div>
  );
};

export default ConfiguracionTema;
