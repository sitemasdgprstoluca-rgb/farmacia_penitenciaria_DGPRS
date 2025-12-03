import { useState, useEffect, useRef, useCallback } from 'react';
import { useTheme } from '../hooks/useTheme';
import { usePermissions } from '../hooks/usePermissions';
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
  FaLock
} from 'react-icons/fa';
import './ConfiguracionTema.css';

/**
 * Expresión regular para validar colores hex
 */
const HEX_COLOR_REGEX = /^#[0-9A-Fa-f]{6}$/;

/**
 * Valida si un string es un color hexadecimal válido
 */
const esColorValido = (color) => {
  if (!color) return false;
  return HEX_COLOR_REGEX.test(color);
};

/**
 * Normaliza un color a formato hex válido
 * Retorna el color si es válido, o un fallback si no
 */
const normalizarColor = (color, fallback = '#000000') => {
  if (!color) return fallback;
  // Si ya es válido, retornar
  if (esColorValido(color)) return color.toUpperCase();
  // Intentar agregar # si falta
  if (/^[0-9A-Fa-f]{6}$/.test(color)) return `#${color}`.toUpperCase();
  return fallback;
};

/**
 * Página de configuración del tema del sistema
 * Solo accesible por superusuarios
 * 
 * Funcionalidades:
 * - Selección de temas predefinidos
 * - Personalización de colores
 * - Subida de logos (header e institucional para PDFs)
 * - Configuración de textos institucionales
 * - Vista previa en tiempo real
 */
const ConfiguracionTema = () => {
  const { user, permisos, loading: cargandoPermisos } = usePermissions();
  const { 
    configuracion, 
    cargando: cargandoTema, 
    actualizarTema, 
    aplicarTemaPredefinido, 
    restablecerTema,
    subirLogoHeader,
    subirLogoPdf,
    eliminarLogoHeader,
    eliminarLogoPdf,
    temasDisponibles,
    aplicarCSSVariablesLocalmente // Para preview en tiempo real 
  } = useTheme();
  
  const [formData, setFormData] = useState({});
  const [temaSeleccionado, setTemaSeleccionado] = useState('');
  const [modoEdicion, setModoEdicion] = useState(false);
  const [activeTab, setActiveTab] = useState('temas');
  const [erroresColor, setErroresColor] = useState({});
  
  // Estados de carga separados para cada operación
  const [operacionEnCurso, setOperacionEnCurso] = useState({
    aplicandoTema: false,
    guardandoColores: false,
    guardandoIdentidad: false,
    restableciendo: false,
    subiendoLogoHeader: false,
    subiendoLogoPdf: false,
    eliminandoLogoHeader: false,
    eliminandoLogoPdf: false,
  });
  
  // Timeout de seguridad para operaciones bloqueadas (30 segundos)
  const TIMEOUT_OPERACION_MS = 30000;
  const timeoutRef = useRef(null);
  
  const logoHeaderRef = useRef(null);
  const logoPdfRef = useRef(null);

  // Verificar permisos usando el sistema de permisos coherente
  // Usa el permiso 'configurarTema' que incluye ADMIN y FARMACIA
  const tienePermisoTema = permisos?.configurarTema || user?.is_superuser || permisos?.esSuperusuario;
  const permisosResueltos = !cargandoPermisos && user !== undefined;
  
  // Agrupar operaciones por tipo para permitir concurrencia entre grupos diferentes
  const operacionesBloqueantes = ['aplicandoTema', 'guardandoColores', 'restableciendo'];
  const operacionesLogos = ['subiendoLogoHeader', 'subiendoLogoPdf', 'eliminandoLogoHeader', 'eliminandoLogoPdf'];
  
  // Estado de operaciones por grupo (para bloqueo interno del grupo)
  const hayOperacionTemaEnCurso = operacionesBloqueantes.some(op => operacionEnCurso[op]);
  const hayOperacionLogoEnCurso = operacionesLogos.some(op => operacionEnCurso[op]);
  const hayOperacionIdentidadEnCurso = operacionEnCurso.guardandoIdentidad;
  
  // Para deshabilitar UI global (indicador visual)
  const hayOperacionEnCurso = Object.values(operacionEnCurso).some(v => v);
  
  /**
   * Resetea todas las operaciones en curso (escape de seguridad)
   * Útil cuando una operación queda bloqueada por error de red
   */
  const resetearOperaciones = useCallback(() => {
    setOperacionEnCurso({
      aplicandoTema: false,
      guardandoColores: false,
      guardandoIdentidad: false,
      restableciendo: false,
      subiendoLogoHeader: false,
      subiendoLogoPdf: false,
      eliminandoLogoHeader: false,
      eliminandoLogoPdf: false,
    });
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    toast.info('Operaciones desbloqueadas');
  }, []);

  // Inicializar formulario con datos actuales
  useEffect(() => {
    if (configuracion) {
      setFormData({
        nombre_sistema: configuracion.nombre_sistema || '',
        nombre_institucion: configuracion.nombre_institucion || '',
        subtitulo_institucion: configuracion.subtitulo_institucion || '',
        logo_url: configuracion.logo_url || '',
        color_primario: normalizarColor(configuracion.color_primario, '#9F2241'),
        color_primario_hover: normalizarColor(configuracion.color_primario_hover, '#6B1839'),
        color_secundario: normalizarColor(configuracion.color_secundario, '#424242'),
        color_acento: normalizarColor(configuracion.color_acento, '#BC955C'),
        color_fondo: normalizarColor(configuracion.color_fondo, '#F5F5F5'),
        color_fondo_sidebar: normalizarColor(configuracion.color_fondo_sidebar, '#9F2241'),
        color_fondo_header: normalizarColor(configuracion.color_fondo_header, '#9F2241'),
        color_fondo_card: normalizarColor(configuracion.color_fondo_card, '#FFFFFF'),
        color_texto: normalizarColor(configuracion.color_texto, '#212121'),
        color_texto_secundario: normalizarColor(configuracion.color_texto_secundario, '#757575'),
        color_texto_sidebar: normalizarColor(configuracion.color_texto_sidebar, '#FFFFFF'),
        color_texto_header: normalizarColor(configuracion.color_texto_header, '#FFFFFF'),
        color_exito: normalizarColor(configuracion.color_exito, '#4CAF50'),
        color_advertencia: normalizarColor(configuracion.color_advertencia, '#FF9800'),
        color_error: normalizarColor(configuracion.color_error, '#F44336'),
        color_info: normalizarColor(configuracion.color_info, '#2196F3'),
      });
      setTemaSeleccionado(configuracion.tema_activo || 'default');
      setModoEdicion(false);
      setErroresColor({});
    }
  }, [configuracion]);

  /**
   * Valida permisos antes de ejecutar una acción
   */
  const validarPermisos = useCallback(() => {
    if (!tienePermisoTema) {
      toast.error('No tienes permisos para realizar esta acción');
      return false;
    }
    return true;
  }, [tienePermisoTema]);

  /**
   * Handler genérico para operaciones asíncronas con manejo de errores
   * Permite concurrencia entre grupos de operaciones diferentes
   * Incluye timeout de seguridad para evitar bloqueos permanentes
   */
  const ejecutarOperacion = useCallback(async (nombreOperacion, operacion, mensajeExito, grupoBloqueo = 'tema') => {
    if (!validarPermisos()) return { success: false };
    
    // Verificar bloqueo solo dentro del mismo grupo
    const estaBloquado = grupoBloqueo === 'tema' ? hayOperacionTemaEnCurso :
                         grupoBloqueo === 'logo' ? hayOperacionLogoEnCurso :
                         grupoBloqueo === 'identidad' ? hayOperacionIdentidadEnCurso : false;
    
    if (estaBloquado) {
      toast.error('Espera a que termine la operación actual');
      return { success: false };
    }

    setOperacionEnCurso(prev => ({ ...prev, [nombreOperacion]: true }));
    
    // Configurar timeout de seguridad
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => {
      setOperacionEnCurso(prev => {
        if (prev[nombreOperacion]) {
          toast.error('La operación tardó demasiado. Se ha desbloqueado automáticamente.');
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
        toast.error(resultado.error || 'Error en la operación');
        return resultado;
      }
    } catch (error) {
      console.error(`Error en ${nombreOperacion}:`, error);
      const mensaje = error.response?.data?.error || 
                      error.message || 
                      'Error de conexión. Intenta de nuevo.';
      toast.error(mensaje);
      return { success: false, error: mensaje };
    } finally {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      setOperacionEnCurso(prev => ({ ...prev, [nombreOperacion]: false }));
    }
  }, [validarPermisos, hayOperacionTemaEnCurso, hayOperacionLogoEnCurso, hayOperacionIdentidadEnCurso]);

  /**
   * Maneja cambios en inputs de texto
   */
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setModoEdicion(true);
  };

  /**
   * Maneja cambios en inputs de color con validación
   * Aplica preview en tiempo real si el color es válido
   */
  const handleColorChange = (e) => {
    const { name, value } = e.target;
    
    // Siempre actualizar el formData para que el usuario vea lo que escribe
    const nuevoFormData = { ...formData, [name]: value };
    setFormData(nuevoFormData);
    setModoEdicion(true);
    
    // Validar el color
    if (value && !esColorValido(value)) {
      setErroresColor(prev => ({ ...prev, [name]: 'Formato inválido. Use #RRGGBB' }));
    } else {
      setErroresColor(prev => {
        const nuevos = { ...prev };
        delete nuevos[name];
        return nuevos;
      });
      
      // Aplicar preview en tiempo real si el color es válido
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
        errores[campo] = 'Color inválido';
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
    
    // Evitar llamadas redundantes si el tema ya está activo
    if (tema === temaSeleccionado && tema === configuracion?.tema_activo) {
      toast.info('Este tema ya está activo');
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
   * Guarda los colores personalizados
   */
  const handleGuardar = async () => {
    if (!validarColoresAntesDeGuardar()) {
      toast.error('Corrige los colores con formato inválido');
      return;
    }

    const resultado = await ejecutarOperacion(
      'guardandoColores',
      () => actualizarTema({ ...formData, tema_activo: 'custom' }),
      'Configuración guardada correctamente',
      'tema'
    );

    if (resultado.success) {
      setModoEdicion(false);
    }
  };

  /**
   * Guarda la identidad institucional
   * Envía la configuración completa para no perder colores ni tema activo
   */
  const handleGuardarIdentidad = async () => {
    const resultado = await ejecutarOperacion(
      'guardandoIdentidad',
      () => actualizarTema({
        ...formData, // Incluir todos los datos del formulario (colores + identidad)
      }),
      'Identidad institucional actualizada',
      'identidad'
    );

    if (resultado.success) {
      setModoEdicion(false);
    }
  };

  /**
   * Restablece el tema a valores por defecto
   */
  const handleRestablecer = async () => {
    if (!window.confirm('¿Estás seguro de restablecer a los valores por defecto?\n\nEsto restablecerá todos los colores pero mantendrá los logos e información institucional.')) {
      return;
    }

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
   * Sube el logo del header
   */
  const handleSubirLogoHeader = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validaciones
    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Formato no válido. Use PNG, JPG o WebP');
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
      toast.error('Formato no válido. Use PNG o JPG');
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

  /**
   * Elimina el logo del header
   */
  const handleEliminarLogoHeader = async () => {
    if (!window.confirm('¿Eliminar el logo del header?')) return;

    await ejecutarOperacion(
      'eliminandoLogoHeader',
      eliminarLogoHeader,
      'Logo del header eliminado',
      'logo'
    );
  };

  /**
   * Elimina el logo para PDFs
   */
  const handleEliminarLogoPdf = async () => {
    if (!window.confirm('¿Eliminar el logo para PDFs?')) return;

    await ejecutarOperacion(
      'eliminandoLogoPdf',
      eliminarLogoPdf,
      'Logo para PDFs eliminado',
      'logo'
    );
  };

  // Estado de carga inicial (permisos + tema)
  if (!permisosResueltos || cargandoTema) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-t-transparent mx-auto mb-4" style={{ borderColor: '#9F224133', borderTopColor: '#9F2241' }}></div>
          <p className="text-gray-600">
            {!permisosResueltos ? 'Verificando permisos...' : 'Cargando configuración...'}
          </p>
        </div>
      </div>
    );
  }

  // Acceso restringido (solo después de resolver permisos)
  // Usa tienePermisoTema para ser coherente con el guard de rutas
  if (!tienePermisoTema) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white p-8 rounded-xl shadow-lg text-center max-w-md">
          <FaLock className="text-6xl text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Acceso Restringido</h2>
          <p className="text-gray-600">Solo los administradores del sistema y personal de farmacia pueden acceder a la configuración del tema.</p>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: 'temas', label: 'Temas', icon: FaPalette },
    { id: 'colores', label: 'Colores', icon: FaDesktop },
    { id: 'logos', label: 'Logos', icon: FaImage },
    { id: 'identidad', label: 'Identidad', icon: FaBuilding },
  ];

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
            <h1 className="text-2xl font-bold text-gray-800">Configuración del Tema</h1>
            <p className="text-gray-600">Personaliza la apariencia del sistema, logos y colores de reportes PDF</p>
          </div>
        </div>
      </div>

      {/* Indicador de operación en curso con botón de desbloqueo */}
      {hayOperacionEnCurso && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full"></div>
            <span className="text-blue-700">Procesando...</span>
          </div>
          <button
            onClick={resetearOperaciones}
            className="text-sm text-blue-600 hover:text-blue-800 underline"
            title="Usar si la operación parece bloqueada"
          >
            Desbloquear
          </button>
        </div>
      )}

      {/* Tabs de navegación */}
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
                background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)',
                borderBottomColor: '#9F2241'
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
                  Tema activo: <span className="font-semibold" style={{ color: '#9F2241' }}>{temaSeleccionado}</span>
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
                        <div className="animate-spin h-6 w-6 border-2 border-gray-400 border-t-transparent rounded-full"></div>
                      </div>
                    )}
                  </button>
                ))}
                
                {/* Opción Personalizado */}
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

          {/* TAB: Personalización de Colores */}
          {activeTab === 'colores' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-800">Personalización de Colores</h2>
                <div className="flex gap-2">
                  <button
                    onClick={handleRestablecer}
                    disabled={hayOperacionTemaEnCurso}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    {operacionEnCurso.restableciendo ? (
                      <div className="animate-spin h-4 w-4 border-2 border-gray-500 border-t-transparent rounded-full"></div>
                    ) : (
                      <FaUndo />
                    )}
                    Restablecer
                  </button>
                  <button
                    onClick={handleGuardar}
                    disabled={hayOperacionTemaEnCurso || !modoEdicion || hayErroresColor}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg text-white disabled:opacity-50"
                    style={{ background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)' }}
                    title={hayErroresColor ? 'Corrige los errores de color primero' : ''}
                  >
                    {operacionEnCurso.guardandoColores ? (
                      <>
                        <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
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

              {/* Alerta de errores de validación */}
              {hayErroresColor && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-center gap-3">
                  <FaExclamationTriangle className="text-red-500" />
                  <span className="text-red-700">Hay colores con formato inválido. Usa el formato #RRGGBB (ej: #FF5500)</span>
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
                    <ColorInput label="Éxito" name="color_exito" value={formData.color_exito} onChange={handleColorChange} error={erroresColor.color_exito} disabled={hayOperacionTemaEnCurso} />
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
                              Éxito
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
              <h2 className="text-lg font-bold text-gray-800">Gestión de Logos</h2>

              <div className="grid md:grid-cols-2 gap-6">
                {/* Logo Header */}
                <div className="bg-gray-50 p-6 rounded-xl">
                  <div className="flex items-center gap-3 mb-4">
                    <FaDesktop className="text-xl text-gray-600" />
                    <div>
                      <h3 className="font-semibold text-gray-800">Logo del Header</h3>
                      <p className="text-sm text-gray-500">Aparece en la barra superior del sistema</p>
                    </div>
                  </div>
                  
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center mb-4 bg-white">
                    {configuracion?.logo_header_url ? (
                      <img 
                        src={configuracion.logo_header_url} 
                        alt="Logo Header" 
                        className="max-h-20 mx-auto object-contain"
                      />
                    ) : (
                      <div className="text-gray-400">
                        <FaImage className="text-4xl mx-auto mb-2" />
                        <p>Sin logo configurado</p>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex gap-2">
                    <input
                      type="file"
                      ref={logoHeaderRef}
                      onChange={handleSubirLogoHeader}
                      accept="image/png,image/jpeg,image/jpg,image/webp"
                      className="hidden"
                      disabled={hayOperacionLogoEnCurso}
                    />
                    <button
                      onClick={() => logoHeaderRef.current?.click()}
                      disabled={hayOperacionLogoEnCurso}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-white disabled:opacity-50"
                      style={{ background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)' }}
                    >
                      {operacionEnCurso.subiendoLogoHeader ? (
                        <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                      ) : (
                        <FaUpload />
                      )}
                      {configuracion?.logo_header_url ? 'Cambiar' : 'Subir Logo'}
                    </button>
                    {configuracion?.logo_header_url && (
                      <button
                        onClick={handleEliminarLogoHeader}
                        disabled={hayOperacionLogoEnCurso}
                        className="px-4 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50 disabled:opacity-50"
                      >
                        {operacionEnCurso.eliminandoLogoHeader ? (
                          <div className="animate-spin h-4 w-4 border-2 border-red-500 border-t-transparent rounded-full"></div>
                        ) : (
                          <FaTrash />
                        )}
                      </button>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-2">PNG, JPG o WebP. Máximo 500KB.</p>
                </div>

                {/* Logo PDF */}
                <div className="bg-gray-50 p-6 rounded-xl">
                  <div className="flex items-center gap-3 mb-4">
                    <FaFilePdf className="text-xl text-red-600" />
                    <div>
                      <h3 className="font-semibold text-gray-800">Logo Institucional (PDFs)</h3>
                      <p className="text-sm text-gray-500">Fondo/logo para reportes y documentos PDF</p>
                    </div>
                  </div>
                  
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center mb-4 bg-white">
                    {configuracion?.logo_pdf_url ? (
                      <img 
                        src={configuracion.logo_pdf_url} 
                        alt="Logo PDF" 
                        className="max-h-32 mx-auto object-contain"
                      />
                    ) : (
                      <div className="text-gray-400">
                        <FaFilePdf className="text-4xl mx-auto mb-2" />
                        <p>Sin logo institucional</p>
                        <p className="text-xs">Se usará el fondo por defecto</p>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex gap-2">
                    <input
                      type="file"
                      ref={logoPdfRef}
                      onChange={handleSubirLogoPdf}
                      accept="image/png,image/jpeg,image/jpg"
                      className="hidden"
                      disabled={hayOperacionLogoEnCurso}
                    />
                    <button
                      onClick={() => logoPdfRef.current?.click()}
                      disabled={hayOperacionLogoEnCurso}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-white disabled:opacity-50"
                      style={{ background: 'linear-gradient(135deg, #DC2626 0%, #991B1B 100%)' }}
                    >
                      {operacionEnCurso.subiendoLogoPdf ? (
                        <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                      ) : (
                        <FaUpload />
                      )}
                      {configuracion?.logo_pdf_url ? 'Cambiar' : 'Subir Logo'}
                    </button>
                    {configuracion?.logo_pdf_url && (
                      <button
                        onClick={handleEliminarLogoPdf}
                        disabled={hayOperacionLogoEnCurso}
                        className="px-4 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50 disabled:opacity-50"
                      >
                        {operacionEnCurso.eliminandoLogoPdf ? (
                          <div className="animate-spin h-4 w-4 border-2 border-red-500 border-t-transparent rounded-full"></div>
                        ) : (
                          <FaTrash />
                        )}
                      </button>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-2">PNG o JPG. Recomendado 800x1200px. Máximo 2MB.</p>
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
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-white disabled:opacity-50"
                  style={{ background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)' }}
                >
                  {operacionEnCurso.guardandoIdentidad ? (
                    <>
                      <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
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
                    <p className="text-xs text-gray-500 mt-1">Aparece en el título del navegador y header</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Nombre de la Institución
                    </label>
                    <input
                      type="text"
                      name="nombre_institucion"
                      value={formData.nombre_institucion || ''}
                      onChange={handleInputChange}
                      placeholder="Secretaría de Seguridad"
                      disabled={hayOperacionIdentidadEnCurso}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-pink-500 disabled:opacity-50 disabled:bg-gray-100"
                    />
                    <p className="text-xs text-gray-500 mt-1">Título principal en reportes PDF</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Subtítulo de la Institución
                    </label>
                    <input
                      type="text"
                      name="subtitulo_institucion"
                      value={formData.subtitulo_institucion || ''}
                      onChange={handleInputChange}
                      placeholder="Dirección General de Prevención y Reinserción Social"
                      disabled={hayOperacionIdentidadEnCurso}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-pink-500 disabled:opacity-50 disabled:bg-gray-100"
                    />
                    <p className="text-xs text-gray-500 mt-1">Subtítulo en reportes PDF</p>
                  </div>
                </div>

                {/* Vista previa de encabezado de reporte */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Vista Previa de Encabezado PDF
                  </label>
                  <div className="border rounded-lg p-6 bg-white shadow-inner">
                    <div className="text-center border-b pb-4">
                      {configuracion?.logo_pdf_url ? (
                        <img 
                          src={configuracion.logo_pdf_url} 
                          alt="Logo" 
                          className="h-16 mx-auto mb-2 object-contain"
                        />
                      ) : (
                        <div className="w-16 h-16 mx-auto mb-2 bg-gray-200 rounded flex items-center justify-center">
                          <FaBuilding className="text-gray-400 text-2xl" />
                        </div>
                      )}
                      <h3 className="text-lg font-bold text-gray-800">
                        {formData.nombre_institucion || 'Nombre de la Institución'}
                      </h3>
                      <p className="text-sm text-gray-600">
                        {formData.subtitulo_institucion || 'Subtítulo de la Institución'}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {formData.nombre_sistema || 'Sistema de Farmacia'}
                      </p>
                    </div>
                    <div className="mt-4 text-center text-xs text-gray-400">
                      [Contenido del reporte]
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * Componente de input de color mejorado con validación
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

export default ConfiguracionTema;
