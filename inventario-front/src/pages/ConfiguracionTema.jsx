import { useState, useEffect } from 'react';
import { useTheme } from '../hooks/useTheme';
import { useAuth } from '../hooks/useAuth';
import { toast } from 'react-hot-toast';
import './ConfiguracionTema.css';

/**
 * Página de configuración del tema del sistema
 * Solo accesible por superusuarios
 */
const ConfiguracionTema = () => {
  const { user } = useAuth();
  const { 
    configuracion, 
    cargando, 
    actualizarTema, 
    aplicarTemaPredefinido, 
    restablecerTema,
    temasDisponibles 
  } = useTheme();
  
  const [formData, setFormData] = useState({});
  const [guardando, setGuardando] = useState(false);
  const [temaSeleccionado, setTemaSeleccionado] = useState('');
  const [modoEdicion, setModoEdicion] = useState(false);

  // Verificar permisos
  const esSuperusuario = user?.is_superuser;

  // Inicializar formulario con datos actuales
  useEffect(() => {
    if (configuracion) {
      setFormData({
        nombre_sistema: configuracion.nombre_sistema || '',
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

  const handleRestablecer = async () => {
    if (!window.confirm('¿Estás seguro de restablecer a los valores por defecto?')) {
      return;
    }

    setGuardando(true);
    const resultado = await restablecerTema();
    setGuardando(false);

    if (resultado.success) {
      toast.success('Configuración restablecida');
      setModoEdicion(false);
    } else {
      toast.error(resultado.error);
    }
  };

  if (!esSuperusuario) {
    return (
      <div className="config-tema-container">
        <div className="acceso-denegado">
          <h2>⚠️ Acceso Restringido</h2>
          <p>Solo los superusuarios pueden acceder a la configuración del tema.</p>
        </div>
      </div>
    );
  }

  if (cargando) {
    return (
      <div className="config-tema-container">
        <div className="cargando">Cargando configuración...</div>
      </div>
    );
  }

  return (
    <div className="config-tema-container">
      <div className="config-tema-header">
        <h1>🎨 Configuración del Tema</h1>
        <p>Personaliza los colores y apariencia del sistema</p>
      </div>

      {/* Selector de Temas Predefinidos */}
      <section className="config-section">
        <h2>Temas Predefinidos</h2>
        <div className="temas-grid">
          {temasDisponibles?.filter(t => t.id !== 'custom').map(tema => (
            <button
              key={tema.id}
              className={`tema-card ${temaSeleccionado === tema.id ? 'activo' : ''}`}
              onClick={() => handleTemaChange(tema.id)}
              disabled={guardando}
            >
              <div className={`tema-preview tema-${tema.id}`}>
                <div className="preview-header"></div>
                <div className="preview-sidebar"></div>
                <div className="preview-content"></div>
              </div>
              <span className="tema-nombre">{tema.nombre}</span>
              {temaSeleccionado === tema.id && <span className="tema-badge">✓ Activo</span>}
            </button>
          ))}
          <button
            className={`tema-card ${temaSeleccionado === 'custom' ? 'activo' : ''}`}
            onClick={() => handleTemaChange('custom')}
            disabled={guardando}
          >
            <div className="tema-preview tema-custom">
              <span className="custom-icon">🎨</span>
            </div>
            <span className="tema-nombre">Personalizado</span>
            {temaSeleccionado === 'custom' && <span className="tema-badge">✓ Activo</span>}
          </button>
        </div>
      </section>

      {/* Configuración del Sistema */}
      <section className="config-section">
        <h2>Configuración General</h2>
        <div className="form-group">
          <label htmlFor="nombre_sistema">Nombre del Sistema</label>
          <input
            type="text"
            id="nombre_sistema"
            name="nombre_sistema"
            value={formData.nombre_sistema || ''}
            onChange={handleInputChange}
            placeholder="Sistema de Farmacia Penitenciaria"
          />
        </div>
        <div className="form-group">
          <label htmlFor="logo_url">URL del Logo (opcional)</label>
          <input
            type="url"
            id="logo_url"
            name="logo_url"
            value={formData.logo_url || ''}
            onChange={handleInputChange}
            placeholder="https://ejemplo.com/logo.png"
          />
        </div>
      </section>

      {/* Editor de Colores */}
      <section className="config-section colores-section">
        <h2>Personalización de Colores</h2>
        
        <div className="colores-grupo">
          <h3>Colores Principales</h3>
          <div className="colores-grid">
            <ColorInput
              label="Color Primario"
              name="color_primario"
              value={formData.color_primario}
              onChange={handleInputChange}
            />
            <ColorInput
              label="Primario (Hover)"
              name="color_primario_hover"
              value={formData.color_primario_hover}
              onChange={handleInputChange}
            />
            <ColorInput
              label="Color Secundario"
              name="color_secundario"
              value={formData.color_secundario}
              onChange={handleInputChange}
            />
            <ColorInput
              label="Color de Acento"
              name="color_acento"
              value={formData.color_acento}
              onChange={handleInputChange}
            />
          </div>
        </div>

        <div className="colores-grupo">
          <h3>Colores de Fondo</h3>
          <div className="colores-grid">
            <ColorInput
              label="Fondo General"
              name="color_fondo"
              value={formData.color_fondo}
              onChange={handleInputChange}
            />
            <ColorInput
              label="Fondo Sidebar"
              name="color_fondo_sidebar"
              value={formData.color_fondo_sidebar}
              onChange={handleInputChange}
            />
            <ColorInput
              label="Fondo Header"
              name="color_fondo_header"
              value={formData.color_fondo_header}
              onChange={handleInputChange}
            />
            <ColorInput
              label="Fondo Tarjetas"
              name="color_fondo_card"
              value={formData.color_fondo_card}
              onChange={handleInputChange}
            />
          </div>
        </div>

        <div className="colores-grupo">
          <h3>Colores de Texto</h3>
          <div className="colores-grid">
            <ColorInput
              label="Texto Principal"
              name="color_texto"
              value={formData.color_texto}
              onChange={handleInputChange}
            />
            <ColorInput
              label="Texto Secundario"
              name="color_texto_secundario"
              value={formData.color_texto_secundario}
              onChange={handleInputChange}
            />
            <ColorInput
              label="Texto Sidebar"
              name="color_texto_sidebar"
              value={formData.color_texto_sidebar}
              onChange={handleInputChange}
            />
            <ColorInput
              label="Texto Header"
              name="color_texto_header"
              value={formData.color_texto_header}
              onChange={handleInputChange}
            />
          </div>
        </div>

        <div className="colores-grupo">
          <h3>Colores de Estado</h3>
          <div className="colores-grid">
            <ColorInput
              label="Éxito"
              name="color_exito"
              value={formData.color_exito}
              onChange={handleInputChange}
            />
            <ColorInput
              label="Advertencia"
              name="color_advertencia"
              value={formData.color_advertencia}
              onChange={handleInputChange}
            />
            <ColorInput
              label="Error"
              name="color_error"
              value={formData.color_error}
              onChange={handleInputChange}
            />
            <ColorInput
              label="Información"
              name="color_info"
              value={formData.color_info}
              onChange={handleInputChange}
            />
          </div>
        </div>
      </section>

      {/* Botones de Acción */}
      <div className="config-acciones">
        <button
          className="btn btn-secondary"
          onClick={handleRestablecer}
          disabled={guardando}
        >
          🔄 Restablecer
        </button>
        <button
          className="btn btn-primary"
          onClick={handleGuardar}
          disabled={guardando || !modoEdicion}
        >
          {guardando ? '⏳ Guardando...' : '💾 Guardar Cambios'}
        </button>
      </div>

      {/* Vista Previa */}
      <section className="config-section preview-section">
        <h2>Vista Previa</h2>
        <div className="preview-container" style={{
          '--preview-primary': formData.color_primario,
          '--preview-secondary': formData.color_secundario,
          '--preview-bg': formData.color_fondo,
          '--preview-sidebar': formData.color_fondo_sidebar,
          '--preview-header': formData.color_fondo_header,
          '--preview-card': formData.color_fondo_card,
          '--preview-text': formData.color_texto,
          '--preview-text-secondary': formData.color_texto_secundario,
          '--preview-sidebar-text': formData.color_texto_sidebar,
          '--preview-header-text': formData.color_texto_header,
        }}>
          <div className="preview-app">
            <div className="preview-sidebar-full">
              <div className="preview-logo">Logo</div>
              <div className="preview-menu-item active">Dashboard</div>
              <div className="preview-menu-item">Productos</div>
              <div className="preview-menu-item">Requisiciones</div>
            </div>
            <div className="preview-main">
              <div className="preview-header-full">
                <span>Sistema de Farmacia</span>
                <span>Usuario</span>
              </div>
              <div className="preview-content-full">
                <div className="preview-card-item">
                  <h4>Tarjeta de Ejemplo</h4>
                  <p>Contenido de la tarjeta</p>
                  <button style={{ background: formData.color_primario, color: formData.color_texto_header }}>
                    Botón Primario
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

/**
 * Componente de input de color
 */
const ColorInput = ({ label, name, value, onChange }) => (
  <div className="color-input-group">
    <label htmlFor={name}>{label}</label>
    <div className="color-input-wrapper">
      <input
        type="color"
        id={name}
        name={name}
        value={value || '#000000'}
        onChange={onChange}
        className="color-picker"
      />
      <input
        type="text"
        value={value || ''}
        onChange={onChange}
        name={name}
        placeholder="#000000"
        pattern="^#[0-9A-Fa-f]{6}$"
        className="color-text"
      />
    </div>
  </div>
);

export default ConfiguracionTema;
