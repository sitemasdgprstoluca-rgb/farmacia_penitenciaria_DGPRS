import { useState, useEffect, useRef } from 'react';
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
  FaExclamationTriangle
} from 'react-icons/fa';
import './ConfiguracionTema.css';

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
  const { user, permisos } = usePermissions();
  const { 
    configuracion, 
    cargando, 
    actualizarTema, 
    aplicarTemaPredefinido, 
    restablecerTema,
    subirLogoHeader,
    subirLogoPdf,
    eliminarLogoHeader,
    eliminarLogoPdf,
    temasDisponibles 
  } = useTheme();
  
  const [formData, setFormData] = useState({});
  const [guardando, setGuardando] = useState(false);
  const [temaSeleccionado, setTemaSeleccionado] = useState('');
  const [modoEdicion, setModoEdicion] = useState(false);
  const [activeTab, setActiveTab] = useState('temas');
  const [subiendoLogo, setSubiendoLogo] = useState(null);
  
  const logoHeaderRef = useRef(null);
  const logoPdfRef = useRef(null);

  // Verificar permisos
  const esSuperusuario = user?.is_superuser || permisos?.isSuperuser;

  // Inicializar formulario con datos actuales
  useEffect(() => {
    if (configuracion) {
      setFormData({
        nombre_sistema: configuracion.nombre_sistema || '',
        nombre_institucion: configuracion.nombre_institucion || '',
        subtitulo_institucion: configuracion.subtitulo_institucion || '',
        logo_url: configuracion.logo_url || '',
        color_primario: configuracion.color_primario || '#1976D2',
        color_primario_hover: configuracion.color_primario_hover || '#1565C0',
        color_secundario: configuracion.color_secundario || '#424242',
        color_acento: configuracion.color_acento || '#FF5722',
        color_fondo: configuracion.color_fondo || '#F5F5F5',
        color_fondo_sidebar: configuracion.color_fondo_sidebar || '#263238',
        color_fondo_header: configuracion.color_fondo_header || '#1976D2',
        color_fondo_card: configuracion.color_fondo_card || '#FFFFFF',
        color_texto: configuracion.color_texto || '#212121',
        color_texto_secundario: configuracion.color_texto_secundario || '#757575',
        color_texto_sidebar: configuracion.color_texto_sidebar || '#ECEFF1',
        color_texto_header: configuracion.color_texto_header || '#FFFFFF',
        color_exito: configuracion.color_exito || '#4CAF50',
        color_advertencia: configuracion.color_advertencia || '#FF9800',
        color_error: configuracion.color_error || '#F44336',
        color_info: configuracion.color_info || '#2196F3',
      });
      setTemaSeleccionado(configuracion.tema_activo || 'default');
    }
  }, [configuracion]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setModoEdicion(true);
  };

  const handleTemaChange = async (tema) => {
    if (tema === 'custom') {
      setTemaSeleccionado('custom');
      setModoEdicion(true);
      return;
    }

    setGuardando(true);
    const resultado = await aplicarTemaPredefinido(tema);
    setGuardando(false);

    if (resultado.success) {
      toast.success(`Tema "${tema}" aplicado correctamente`);
      setTemaSeleccionado(tema);
      setModoEdicion(false);
    } else {
      toast.error(resultado.error);
    }
  };

  const handleGuardar = async () => {
    setGuardando(true);
    const resultado = await actualizarTema({
      ...formData,
      tema_activo: 'custom'
    });
    setGuardando(false);

    if (resultado.success) {
      toast.success('Configuración guardada correctamente');
      setModoEdicion(false);
    } else {
      toast.error(resultado.error);
    }
  };

  const handleGuardarIdentidad = async () => {
    setGuardando(true);
    const resultado = await actualizarTema({
      nombre_sistema: formData.nombre_sistema,
      nombre_institucion: formData.nombre_institucion,
      subtitulo_institucion: formData.subtitulo_institucion,
    });
    setGuardando(false);

    if (resultado.success) {
      toast.success('Identidad institucional actualizada');
      setModoEdicion(false);
    } else {
      toast.error(resultado.error);
    }
  };

  const handleRestablecer = async () => {
    if (!window.confirm('¿Estás seguro de restablecer a los valores por defecto?\n\nEsto restablecerá todos los colores pero mantendrá los logos e información institucional.')) {
      return;
    }

    setGuardando(true);
    const resultado = await restablecerTema();
    setGuardando(false);

    if (resultado.success) {
      toast.success('Colores restablecidos a valores por defecto');
      setModoEdicion(false);
    } else {
      toast.error(resultado.error);
    }
  };

  // Manejo de logos
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

    setSubiendoLogo('header');
    const resultado = await subirLogoHeader(file);
    setSubiendoLogo(null);

    if (resultado.success) {
      toast.success('Logo del header actualizado');
    } else {
      toast.error(resultado.error);
    }
    
    // Limpiar input
    if (logoHeaderRef.current) logoHeaderRef.current.value = '';
  };

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

    setSubiendoLogo('pdf');
    const resultado = await subirLogoPdf(file);
    setSubiendoLogo(null);

    if (resultado.success) {
      toast.success('Logo para PDFs actualizado');
    } else {
      toast.error(resultado.error);
    }
    
    // Limpiar input
    if (logoPdfRef.current) logoPdfRef.current.value = '';
  };

  const handleEliminarLogoHeader = async () => {
    if (!window.confirm('¿Eliminar el logo del header?')) return;

    setSubiendoLogo('header');
    const resultado = await eliminarLogoHeader();
    setSubiendoLogo(null);

    if (resultado.success) {
      toast.success('Logo del header eliminado');
    } else {
      toast.error(resultado.error);
    }
  };

  const handleEliminarLogoPdf = async () => {
    if (!window.confirm('¿Eliminar el logo para PDFs?')) return;

    setSubiendoLogo('pdf');
    const resultado = await eliminarLogoPdf();
    setSubiendoLogo(null);

    if (resultado.success) {
      toast.success('Logo para PDFs eliminado');
    } else {
      toast.error(resultado.error);
    }
  };

  if (!esSuperusuario) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white p-8 rounded-xl shadow-lg text-center max-w-md">
          <FaExclamationTriangle className="text-6xl text-amber-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Acceso Restringido</h2>
          <p className="text-gray-600">Solo los administradores del sistema pueden acceder a la configuración del tema.</p>
        </div>
      </div>
    );
  }

  if (cargando) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-t-transparent mx-auto mb-4" style={{ borderColor: '#9F224133', borderTopColor: '#9F2241' }}></div>
          <p className="text-gray-600">Cargando configuración...</p>
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

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-lg p-6 border-l-4" style={{ borderLeftColor: '#9F2241' }}>
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-full" style={{ background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)' }}>
            <FaPalette className="text-2xl text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Configuración del Tema</h1>
            <p className="text-gray-600">Personaliza la apariencia del sistema, logos y colores de reportes PDF</p>
          </div>
        </div>
      </div>

      {/* Tabs de navegación */}
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="flex border-b border-gray-200">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 px-6 py-4 font-medium transition-all ${
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
                    disabled={guardando}
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
                  disabled={guardando}
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
                    disabled={guardando}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    <FaUndo /> Restablecer
                  </button>
                  <button
                    onClick={handleGuardar}
                    disabled={guardando || !modoEdicion}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg text-white disabled:opacity-50"
                    style={{ background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)' }}
                  >
                    {guardando ? (
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

              <div className="grid md:grid-cols-2 gap-6">
                {/* Colores Principales */}
                <div className="bg-gray-50 p-5 rounded-xl">
                  <h3 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full" style={{ background: formData.color_primario }}></span>
                    Colores Principales
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <ColorInput label="Primario" name="color_primario" value={formData.color_primario} onChange={handleInputChange} />
                    <ColorInput label="Primario Hover" name="color_primario_hover" value={formData.color_primario_hover} onChange={handleInputChange} />
                    <ColorInput label="Secundario" name="color_secundario" value={formData.color_secundario} onChange={handleInputChange} />
                    <ColorInput label="Acento" name="color_acento" value={formData.color_acento} onChange={handleInputChange} />
                  </div>
                </div>

                {/* Colores de Fondo */}
                <div className="bg-gray-50 p-5 rounded-xl">
                  <h3 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full border" style={{ background: formData.color_fondo }}></span>
                    Colores de Fondo
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <ColorInput label="Fondo General" name="color_fondo" value={formData.color_fondo} onChange={handleInputChange} />
                    <ColorInput label="Sidebar" name="color_fondo_sidebar" value={formData.color_fondo_sidebar} onChange={handleInputChange} />
                    <ColorInput label="Header" name="color_fondo_header" value={formData.color_fondo_header} onChange={handleInputChange} />
                    <ColorInput label="Tarjetas" name="color_fondo_card" value={formData.color_fondo_card} onChange={handleInputChange} />
                  </div>
                </div>

                {/* Colores de Texto */}
                <div className="bg-gray-50 p-5 rounded-xl">
                  <h3 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full" style={{ background: formData.color_texto }}></span>
                    Colores de Texto
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <ColorInput label="Texto Principal" name="color_texto" value={formData.color_texto} onChange={handleInputChange} />
                    <ColorInput label="Texto Secundario" name="color_texto_secundario" value={formData.color_texto_secundario} onChange={handleInputChange} />
                    <ColorInput label="Texto Sidebar" name="color_texto_sidebar" value={formData.color_texto_sidebar} onChange={handleInputChange} />
                    <ColorInput label="Texto Header" name="color_texto_header" value={formData.color_texto_header} onChange={handleInputChange} />
                  </div>
                </div>

                {/* Colores de Estado */}
                <div className="bg-gray-50 p-5 rounded-xl">
                  <h3 className="font-semibold text-gray-700 mb-4">Colores de Estado</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <ColorInput label="Éxito" name="color_exito" value={formData.color_exito} onChange={handleInputChange} />
                    <ColorInput label="Advertencia" name="color_advertencia" value={formData.color_advertencia} onChange={handleInputChange} />
                    <ColorInput label="Error" name="color_error" value={formData.color_error} onChange={handleInputChange} />
                    <ColorInput label="Info" name="color_info" value={formData.color_info} onChange={handleInputChange} />
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
                    />
                    <button
                      onClick={() => logoHeaderRef.current?.click()}
                      disabled={subiendoLogo === 'header'}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-white disabled:opacity-50"
                      style={{ background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)' }}
                    >
                      {subiendoLogo === 'header' ? (
                        <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                      ) : (
                        <FaUpload />
                      )}
                      {configuracion?.logo_header_url ? 'Cambiar' : 'Subir Logo'}
                    </button>
                    {configuracion?.logo_header_url && (
                      <button
                        onClick={handleEliminarLogoHeader}
                        disabled={subiendoLogo === 'header'}
                        className="px-4 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50 disabled:opacity-50"
                      >
                        <FaTrash />
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
                    />
                    <button
                      onClick={() => logoPdfRef.current?.click()}
                      disabled={subiendoLogo === 'pdf'}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-white disabled:opacity-50"
                      style={{ background: 'linear-gradient(135deg, #DC2626 0%, #991B1B 100%)' }}
                    >
                      {subiendoLogo === 'pdf' ? (
                        <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                      ) : (
                        <FaUpload />
                      )}
                      {configuracion?.logo_pdf_url ? 'Cambiar' : 'Subir Logo'}
                    </button>
                    {configuracion?.logo_pdf_url && (
                      <button
                        onClick={handleEliminarLogoPdf}
                        disabled={subiendoLogo === 'pdf'}
                        className="px-4 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50 disabled:opacity-50"
                      >
                        <FaTrash />
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
                  disabled={guardando}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-white disabled:opacity-50"
                  style={{ background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)' }}
                >
                  {guardando ? (
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
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-pink-500"
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
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-pink-500"
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
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-pink-500"
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
 * Componente de input de color mejorado
 */
const ColorInput = ({ label, name, value, onChange }) => (
  <div>
    <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
    <div className="flex items-center gap-2">
      <input
        type="color"
        id={name}
        name={name}
        value={value || '#000000'}
        onChange={onChange}
        className="w-10 h-10 rounded cursor-pointer border-0"
      />
      <input
        type="text"
        value={value || ''}
        onChange={onChange}
        name={name}
        placeholder="#000000"
        pattern="^#[0-9A-Fa-f]{6}$"
        className="flex-1 px-3 py-2 border border-gray-300 rounded text-sm font-mono"
      />
    </div>
  </div>
);

export default ConfiguracionTema;
