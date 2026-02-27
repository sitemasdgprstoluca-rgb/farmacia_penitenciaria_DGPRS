import { useEffect, useMemo, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { 
  FaSpinner, 
  FaSignOutAlt, 
  FaSave, 
  FaKey, 
  FaUserCircle,
  FaCheckCircle,
  FaShieldAlt,
  FaEye,
  FaEyeSlash,
  FaEnvelope,
  FaPhone,
  FaBuilding,
  FaIdBadge,
  FaUser,
  FaEdit,
  FaLock,
  FaCheck,
  FaExclamationTriangle
} from "react-icons/fa";
import ConfirmModal from "../components/ConfirmModal";
import PageHeader from "../components/PageHeader";
import { usuariosAPI, authAPI } from "../services/api";
import { usePermissions } from "../hooks/usePermissions";
import { clearTokens } from "../services/tokenManager";

// Tiempo de espera antes de redirigir al login tras cambio de contraseña (ms)
const PASSWORD_CHANGE_LOGOUT_DELAY = 2000;

// Permisos internos que no se muestran al usuario final
const PERMISOS_INTERNOS = [
  "esSuperusuario",
  "isAdmin",
  "isFarmaciaAdmin",
  "isCentroUser",
  "isVistaUser",
  "isSuperuser",
  "role",
  "groupNames",
];

// Etiquetas amigables para permisos agrupados por categoría
const CATEGORIAS_PERMISOS = {
  "Navegación": {
    verDashboard: "Dashboard",
    verProductos: "Productos",
    verLotes: "Lotes",
    verRequisiciones: "Requisiciones",
    verCentros: "Centros",
    verUsuarios: "Usuarios",
    verReportes: "Reportes",
    verTrazabilidad: "Trazabilidad",
    verAuditoria: "Auditoría",
    verNotificaciones: "Notificaciones",
    verPerfil: "Perfil",
    verMovimientos: "Movimientos",
    verDonaciones: "Donaciones",
    verDispensaciones: "Dispensaciones",
  },
  "Requisiciones": {
    crearRequisicion: "Crear",
    editarRequisicion: "Editar",
    eliminarRequisicion: "Eliminar",
    enviarRequisicion: "Enviar",
    autorizarRequisicion: "Autorizar",
    rechazarRequisicion: "Rechazar",
    surtirRequisicion: "Surtir",
    cancelarRequisicion: "Cancelar",
    confirmarRecepcion: "Confirmar Recepción",
    descargarHojaRecoleccion: "Hoja Recolección",
  },
  "Productos": {
    crearProducto: "Crear",
    editarProducto: "Editar",
    eliminarProducto: "Eliminar",
    exportarProductos: "Exportar",
    importarProductos: "Importar",
  },
  "Lotes": {
    crearLote: "Crear",
    editarLote: "Editar",
    eliminarLote: "Eliminar",
    exportarLotes: "Exportar",
    importarLotes: "Importar",
  },
  "Movimientos": {
    crearMovimiento: "Crear",
    exportarMovimientos: "Exportar",
  },
  "Donaciones": {
    crearDonacion: "Crear",
    editarDonacion: "Editar",
    eliminarDonacion: "Eliminar",
    recibirDonacion: "Recibir",
    rechazarDonacion: "Rechazar",
  },
  "Administración": {
    gestionUsuarios: "Gestionar Usuarios",
    gestionarNotificaciones: "Gestionar Notificaciones",
    configurarTema: "Configurar Tema",
  },
};

// Componente para mostrar el indicador de fortaleza de contraseña
const PasswordStrengthIndicator = ({ password }) => {
  const checks = [
    { label: "Mínimo 8 caracteres", valid: password.length >= 8 },
    { label: "Una mayúscula", valid: /[A-Z]/.test(password) },
    { label: "Una minúscula", valid: /[a-z]/.test(password) },
    { label: "Un número", valid: /[0-9]/.test(password) },
  ];
  
  const validCount = checks.filter(c => c.valid).length;
  const strength = validCount === 0 ? 0 : validCount === 1 ? 25 : validCount === 2 ? 50 : validCount === 3 ? 75 : 100;
  const strengthColor = strength <= 25 ? 'bg-red-500' : strength <= 50 ? 'bg-orange-500' : strength <= 75 ? 'bg-yellow-500' : 'bg-green-500';
  const strengthText = strength <= 25 ? 'Muy débil' : strength <= 50 ? 'Débil' : strength <= 75 ? 'Buena' : 'Fuerte';
  
  return (
    <div className="mt-3 space-y-2">
      {/* Barra de progreso */}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all duration-300 ${strengthColor}`}
            style={{ width: `${strength}%` }}
          />
        </div>
        <span className={`text-xs font-medium ${strength <= 50 ? 'text-red-600' : 'text-green-600'}`}>
          {password ? strengthText : ''}
        </span>
      </div>
      
      {/* Checklist */}
      <div className="grid grid-cols-2 gap-1">
        {checks.map((check, i) => (
          <div 
            key={i} 
            className={`flex items-center gap-1.5 text-xs transition-colors ${
              check.valid ? 'text-green-600' : 'text-gray-400'
            }`}
          >
            {check.valid ? (
              <FaCheck className="w-3 h-3" />
            ) : (
              <div className="w-3 h-3 rounded-full border border-current" />
            )}
            <span>{check.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// Componente de input con icono - usa CSS variables del tema
const InputWithIcon = ({ icon: Icon, label, error, ...props }) => (
  <div className="space-y-1">
    {label && (
      <label className="block text-sm font-medium text-gray-700">{label}</label>
    )}
    <div className="relative">
      {Icon && (
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Icon className="h-4 w-4 text-gray-400" />
        </div>
      )}
      <input
        {...props}
        className={`
          block w-full rounded-lg border transition-all duration-200
          ${Icon ? 'pl-10' : 'pl-4'} pr-4 py-2.5
          ${error 
            ? 'border-red-300 focus:border-red-500 focus:ring-red-500 bg-red-50' 
            : 'border-gray-300 bg-white'
          }
          focus:ring-2 focus:ring-opacity-20
          placeholder:text-gray-400 text-gray-900
          disabled:bg-gray-100 disabled:cursor-not-allowed
        `}
        style={!error ? { 
          '--tw-ring-color': 'var(--color-primary, #9F2241)',
        } : {}}
        onFocus={(e) => {
          if (!error) {
            e.target.style.borderColor = 'var(--color-primary, #9F2241)';
            e.target.style.boxShadow = '0 0 0 2px var(--color-primary-light, rgba(159, 34, 65, 0.2))';
          }
          props.onFocus?.(e);
        }}
        onBlur={(e) => {
          if (!error) {
            e.target.style.borderColor = '#d1d5db';
            e.target.style.boxShadow = 'none';
          }
          props.onBlur?.(e);
        }}
      />
    </div>
    {error && (
      <p className="text-xs text-red-600 flex items-center gap-1">
        <FaExclamationTriangle className="w-3 h-3" />
        {error}
      </p>
    )}
  </div>
);

// Componente de input de contraseña - usa CSS variables del tema
const PasswordInput = ({ label, show, onToggle, error, ...props }) => (
  <div className="space-y-1">
    {label && (
      <label className="block text-sm font-medium text-gray-700">{label}</label>
    )}
    <div className="relative">
      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        <FaLock className="h-4 w-4 text-gray-400" />
      </div>
      <input
        type={show ? "text" : "password"}
        {...props}
        className={`
          block w-full rounded-lg border transition-all duration-200
          pl-10 pr-12 py-2.5
          ${error 
            ? 'border-red-300 focus:border-red-500 focus:ring-red-500 bg-red-50' 
            : 'border-gray-300 bg-white'
          }
          focus:ring-2 focus:ring-opacity-20
          placeholder:text-gray-400 text-gray-900
        `}
        onFocus={(e) => {
          if (!error) {
            e.target.style.borderColor = 'var(--color-primary, #9F2241)';
            e.target.style.boxShadow = '0 0 0 2px var(--color-primary-light, rgba(159, 34, 65, 0.2))';
          }
          props.onFocus?.(e);
        }}
        onBlur={(e) => {
          if (!error) {
            e.target.style.borderColor = '#d1d5db';
            e.target.style.boxShadow = 'none';
          }
          props.onBlur?.(e);
        }}
      />
      <button
        type="button"
        onClick={onToggle}
        className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 transition-colors"
        tabIndex={-1}
      >
        {show ? <FaEyeSlash className="h-4 w-4" /> : <FaEye className="h-4 w-4" />}
      </button>
    </div>
    {error && (
      <p className="text-xs text-red-600 flex items-center gap-1">
        <FaExclamationTriangle className="w-3 h-3" />
        {error}
      </p>
    )}
  </div>
);

// Componente de tarjeta de información con colores dinámicos del tema
const InfoCard = ({ icon: Icon, label, value, className = "" }) => (
  <div className={`flex items-center gap-3 p-3 rounded-lg bg-gray-50 ${className}`}>
    <div 
      className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center"
      style={{ backgroundColor: 'var(--color-primary-light, rgba(159, 34, 65, 0.1))' }}
    >
      <Icon className="w-5 h-5" style={{ color: 'var(--color-primary, #9F2241)' }} />
    </div>
    <div className="min-w-0 flex-1">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-sm font-semibold text-gray-900 truncate">{value || "—"}</p>
    </div>
  </div>
);

// Componente de badge de permiso
const PermisoBadge = ({ label, active = true }) => (
  <span className={`
    inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium
    transition-all duration-200
    ${active 
      ? 'bg-green-100 text-green-800 border border-green-200' 
      : 'bg-gray-100 text-gray-600 border border-gray-200'
    }
  `}>
    {active && <FaCheckCircle className="w-3 h-3" />}
    {label}
  </span>
);

function Perfil() {
  const { user, permisos, recargarUsuario } = usePermissions();
  // Los colores dinámicos se aplican via CSS variables globales del ThemeContext
  const [perfil, setPerfil] = useState(null);
  const [perfilError, setPerfilError] = useState(null);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    telefono: "",
  });
  const [formErrors, setFormErrors] = useState({});
  const [passForm, setPassForm] = useState({
    old_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [passErrors, setPassErrors] = useState({});
  const [loadingPerfil, setLoadingPerfil] = useState(true);
  const [savingPerfil, setSavingPerfil] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [showOldPassword, setShowOldPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [activeTab, setActiveTab] = useState('info'); // 'info', 'security', 'permissions'
  const navigate = useNavigate();

  // Limpiar sesión completamente y redirigir
  // ISS-SEC FIX: También limpiar sessionStorage para evitar rehidratación involuntaria
  const limpiarSesionYRedirigir = useCallback(() => {
    clearTokens();
    // Limpiar localStorage legacy
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    // ISS-SEC FIX: Limpiar sessionStorage de claves de sesión
    sessionStorage.removeItem("session_uid");
    sessionStorage.removeItem("session_role");
    sessionStorage.removeItem("session_hash");
    navigate("/login");
  }, [navigate]);

  const cargarPerfil = useCallback(async () => {
    setLoadingPerfil(true);
    setPerfilError(null);
    try {
      const res = await usuariosAPI.me();
      setPerfil(res.data);
      setForm({
        first_name: res.data.first_name || "",
        last_name: res.data.last_name || "",
        email: res.data.email || "",
        telefono: res.data.telefono || "",
      });
    } catch (error) {
      const status = error.response?.status;
      const detail = error.response?.data?.detail || "No se pudo cargar el perfil";
      
      if (status === 403) {
        setPerfilError("No tienes permisos para ver tu perfil. Contacta al administrador.");
        toast.error("Acceso denegado al perfil");
      } else if (status === 401) {
        toast.error("Sesión expirada. Por favor inicia sesión nuevamente.");
        limpiarSesionYRedirigir();
        return;
      } else {
        setPerfilError(detail);
        toast.error(detail);
      }
    } finally {
      setLoadingPerfil(false);
    }
  }, [limpiarSesionYRedirigir]);

  useEffect(() => {
    cargarPerfil();
  }, [cargarPerfil]);

  // Validación del formulario de datos personales
  const validarFormDatos = () => {
    const errors = {};
    
    if (!form.first_name?.trim()) {
      errors.first_name = "El nombre es requerido";
    }
    
    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      errors.email = "Email inválido";
    }
    
    if (form.telefono && !/^[\d\s\-+()]{7,20}$/.test(form.telefono)) {
      errors.telefono = "Teléfono inválido";
    }
    
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Validación del formulario de contraseña
  const validarFormPassword = () => {
    const errors = {};
    
    if (!passForm.old_password) {
      errors.old_password = "Ingresa tu contraseña actual";
    }
    
    if (!passForm.new_password) {
      errors.new_password = "Ingresa la nueva contraseña";
    } else {
      if (passForm.new_password.length < 8) {
        errors.new_password = "Mínimo 8 caracteres";
      } else if (!/[A-Z]/.test(passForm.new_password)) {
        errors.new_password = "Falta una mayúscula";
      } else if (!/[a-z]/.test(passForm.new_password)) {
        errors.new_password = "Falta una minúscula";
      } else if (!/[0-9]/.test(passForm.new_password)) {
        errors.new_password = "Falta un número";
      } else if (passForm.new_password === passForm.old_password) {
        errors.new_password = "Debe ser diferente a la actual";
      }
    }
    
    if (!passForm.confirm_password) {
      errors.confirm_password = "Confirma la nueva contraseña";
    } else if (passForm.new_password !== passForm.confirm_password) {
      errors.confirm_password = "Las contraseñas no coinciden";
    }
    
    setPassErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const guardarDatos = async (e) => {
    e.preventDefault();
    
    if (!perfil) {
      toast.error("No se puede guardar: el perfil no se ha cargado");
      return;
    }
    
    if (!validarFormDatos()) return;
    
    setSavingPerfil(true);
    try {
      await usuariosAPI.actualizarPerfil(form);
      toast.success("Perfil actualizado correctamente");
      
      try {
        await recargarUsuario?.();
      } catch (reloadError) {
        console.error("Error al recargar usuario:", reloadError);
      }
      
      cargarPerfil();
    } catch (error) {
      const detail = error.response?.data?.detail || error.response?.data?.error;
      toast.error(detail || "No se pudo actualizar el perfil");
    } finally {
      setSavingPerfil(false);
    }
  };

  const cambiarPassword = async (e) => {
    e.preventDefault();
    
    if (!validarFormPassword()) return;
    
    setPasswordLoading(true);
    try {
      await usuariosAPI.cambiarPasswordPropio(passForm);
      toast.success("Contraseña actualizada. Serás redirigido al login.");
      setPassForm({ old_password: "", new_password: "", confirm_password: "" });
      setPassErrors({});
      
      setTimeout(() => {
        limpiarSesionYRedirigir();
      }, PASSWORD_CHANGE_LOGOUT_DELAY);
    } catch (error) {
      const errorMsg = error.response?.data?.error || "No se pudo cambiar la contraseña";
      toast.error(errorMsg);
      if (errorMsg.toLowerCase().includes("actual") || errorMsg.toLowerCase().includes("incorrect")) {
        setPassErrors(prev => ({ ...prev, old_password: "Contraseña incorrecta" }));
      }
    } finally {
      setPasswordLoading(false);
    }
  };

  // Agrupar permisos por categoría
  const permisosAgrupados = useMemo(() => {
    const grupos = {};
    
    Object.entries(CATEGORIAS_PERMISOS).forEach(([categoria, permisosCat]) => {
      const permisosActivos = Object.entries(permisosCat)
        .filter(([clave]) => {
          const valor = permisos?.[clave];
          return Boolean(valor) && !PERMISOS_INTERNOS.includes(clave);
        })
        .map(([clave, etiqueta]) => ({ clave, etiqueta }));
      
      if (permisosActivos.length > 0) {
        grupos[categoria] = permisosActivos;
      }
    });
    
    return grupos;
  }, [permisos]);

  const totalPermisos = useMemo(() => {
    return Object.values(permisosAgrupados).reduce((sum, arr) => sum + arr.length, 0);
  }, [permisosAgrupados]);

  const logout = async () => {
    setLoggingOut(true);
    try {
      await authAPI.logout();
    } catch (error) {
      console.error("Error al cerrar sesión en servidor:", error);
    } finally {
      limpiarSesionYRedirigir();
      setLoggingOut(false);
    }
  };

  // Estado de error
  if (perfilError && !loadingPerfil) {
    return (
      <div className="space-y-6">
        <PageHeader
          icon={FaUserCircle}
          title="Mi Perfil"
          subtitle="Gestiona tu información y credenciales"
        />
        
        <div className="max-w-lg mx-auto">
          <div className="bg-white rounded-2xl shadow-lg border border-red-100 overflow-hidden">
            <div className="bg-red-50 px-6 py-8 text-center">
              <div className="w-16 h-16 mx-auto rounded-full bg-red-100 flex items-center justify-center mb-4">
                <FaExclamationTriangle className="w-8 h-8 text-red-500" />
              </div>
              <h3 className="text-lg font-semibold text-red-800 mb-2">Error al cargar el perfil</h3>
              <p className="text-sm text-red-600">{perfilError}</p>
            </div>
            <div className="px-6 py-4 flex gap-3 justify-center">
              <button
                onClick={cargarPerfil}
                className="px-4 py-2 rounded-lg text-white text-sm font-semibold transition-colors"
                style={{ backgroundColor: 'var(--color-primary, #9F2241)' }}
                onMouseOver={(e) => e.currentTarget.style.backgroundColor = 'var(--color-primary-hover, #6B1839)'}
                onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'var(--color-primary, #9F2241)'}
              >
                Reintentar
              </button>
              <button
                onClick={() => setShowLogoutConfirm(true)}
                disabled={loggingOut}
                className="px-4 py-2 rounded-lg bg-gray-100 text-gray-700 text-sm font-semibold hover:bg-gray-200 transition-colors inline-flex items-center gap-2"
              >
                {loggingOut ? <FaSpinner className="animate-spin" /> : <FaSignOutAlt />}
                Cerrar sesión
              </button>
            </div>
          </div>
        </div>
        
        <ConfirmModal
          open={showLogoutConfirm}
          title="Cerrar sesión"
          message="¿Estás seguro que deseas cerrar tu sesión?"
          confirmText="Cerrar sesión"
          onCancel={() => setShowLogoutConfirm(false)}
          onConfirm={logout}
        />
      </div>
    );
  }

  // Estado de carga
  if (loadingPerfil) {
    return (
      <div className="space-y-6">
        <PageHeader
          icon={FaUserCircle}
          title="Mi Perfil"
          subtitle="Gestiona tu información y credenciales"
        />
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <FaSpinner 
              className="w-10 h-10 animate-spin mx-auto mb-4" 
              style={{ color: 'var(--color-primary, #9F2241)' }}
            />
            <p className="text-gray-600">Cargando perfil...</p>
          </div>
        </div>
      </div>
    );
  }

  const rolDisplay = perfil?.rol_efectivo || perfil?.rol || user?.rol_efectivo || user?.rol || "Usuario";
  const iniciales = `${perfil?.first_name?.[0] || ''}${perfil?.last_name?.[0] || perfil?.username?.[0] || 'U'}`.toUpperCase();
  
  // ISS-SEC: Solo administradores pueden editar el correo electrónico
  const rolActual = (perfil?.rol || user?.rol || '').toUpperCase();
  const esAdmin = rolActual === 'ADMIN';
  const puedeEditarEmail = esAdmin;

  return (
    <div className="space-y-6 pb-8">
      <PageHeader
        icon={FaUserCircle}
        title="Mi Perfil"
        subtitle="Gestiona tu información personal y seguridad"
      />

      {/* Header con avatar y acciones - Colores dinámicos del tema */}
      <div 
        className="rounded-2xl shadow-lg overflow-hidden"
        style={{ background: 'linear-gradient(to right, var(--color-primary, #9F2241), var(--color-primary-hover, #6B1839))' }}
      >
        <div className="px-6 py-8 flex flex-col sm:flex-row items-center gap-6">
          {/* Avatar */}
          <div className="relative">
            <div className="w-24 h-24 rounded-full bg-white/20 backdrop-blur flex items-center justify-center text-white text-3xl font-bold border-4 border-white/30">
              {iniciales}
            </div>
            <div 
              className="absolute -bottom-1 -right-1 w-7 h-7 rounded-full border-2 border-white flex items-center justify-center"
              style={{ backgroundColor: 'var(--color-success, #4a7c4b)' }}
            >
              <FaCheck className="w-3 h-3 text-white" />
            </div>
          </div>
          
          {/* Info */}
          <div className="flex-1 text-center sm:text-left">
            <h2 className="text-2xl font-bold text-white mb-1">
              {perfil?.first_name} {perfil?.last_name || perfil?.username}
            </h2>
            <p className="text-white/80 mb-2">@{perfil?.username}</p>
            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
              <span className="inline-flex items-center px-3 py-1 rounded-full bg-white/20 text-white text-sm font-medium">
                <FaIdBadge className="w-3.5 h-3.5 mr-1.5" />
                {rolDisplay}
              </span>
              {perfil?.centro_nombre && (
                <span className="inline-flex items-center px-3 py-1 rounded-full bg-white/20 text-white text-sm font-medium">
                  <FaBuilding className="w-3.5 h-3.5 mr-1.5" />
                  {perfil.centro_nombre}
                </span>
              )}
            </div>
          </div>
          
          {/* Botón de logout */}
          <button
            onClick={() => setShowLogoutConfirm(true)}
            disabled={loggingOut}
            className="px-5 py-2.5 rounded-xl bg-white/20 hover:bg-white/30 text-white text-sm font-semibold transition-all duration-200 inline-flex items-center gap-2 backdrop-blur"
          >
            {loggingOut ? (
              <>
                <FaSpinner className="animate-spin" />
                Cerrando...
              </>
            ) : (
              <>
                <FaSignOutAlt />
                Cerrar sesión
              </>
            )}
          </button>
        </div>
        
        {/* Tabs */}
        <div 
          className="px-6"
          style={{ backgroundColor: 'rgba(var(--color-primary-rgb, 107, 24, 57), 0.5)' }}
        >
          <nav className="flex gap-1 -mb-px">
            {[
              { id: 'info', label: 'Información', icon: FaUser },
              { id: 'security', label: 'Seguridad', icon: FaKey },
              { id: 'permissions', label: 'Permisos', icon: FaShieldAlt },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-2 px-4 py-3 text-sm font-medium rounded-t-lg transition-all
                  ${activeTab === tab.id
                    ? 'bg-white'
                    : 'text-white/80 hover:text-white hover:bg-white/10'
                  }
                `}
                style={activeTab === tab.id ? { color: 'var(--color-primary, #9F2241)' } : {}}
              >
                <tab.icon className="w-4 h-4" />
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Contenido según tab activo */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Panel izquierdo - Información rápida */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
              Información de cuenta
            </h3>
            <div className="space-y-3">
              <InfoCard icon={FaUser} label="Usuario" value={perfil?.username} />
              <InfoCard icon={FaEnvelope} label="Email" value={perfil?.email} />
              <InfoCard icon={FaPhone} label="Teléfono" value={perfil?.telefono} />
              <InfoCard icon={FaBuilding} label="Adscripción" value={perfil?.adscripcion} />
            </div>
          </div>
          
          {/* Mini resumen de permisos */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
                Permisos activos
              </h3>
              <span className="text-2xl font-bold" style={{ color: 'var(--color-primary, #9F2241)' }}>{totalPermisos}</span>
            </div>
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
              <div 
                className="h-full rounded-full"
                style={{ 
                  background: 'linear-gradient(to right, var(--color-primary, #9F2241), var(--color-primary-hover, #6B1839))',
                  width: `${Math.min(totalPermisos * 2, 100)}%` 
                }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-2">
              {Object.keys(permisosAgrupados).length} categorías con acceso
            </p>
          </div>
        </div>

        {/* Panel derecho - Contenido dinámico */}
        <div className="lg:col-span-2">
          
          {/* Tab: Información Personal */}
          {activeTab === 'info' && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-3">
                <div 
                  className="w-10 h-10 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: 'var(--color-primary-light, rgba(159, 34, 65, 0.1))' }}
                >
                  <FaEdit className="w-5 h-5" style={{ color: 'var(--color-primary, #9F2241)' }} />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Editar información personal</h3>
                  <p className="text-sm text-gray-500">Actualiza tus datos de contacto</p>
                </div>
              </div>
              
              <form onSubmit={guardarDatos} className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <InputWithIcon
                    icon={FaUser}
                    label="Nombre"
                    type="text"
                    value={form.first_name}
                    onChange={(e) => setForm(f => ({ ...f, first_name: e.target.value }))}
                    placeholder="Tu nombre"
                    maxLength={150}
                    error={formErrors.first_name}
                  />
                  <InputWithIcon
                    icon={FaUser}
                    label="Apellidos"
                    type="text"
                    value={form.last_name}
                    onChange={(e) => setForm(f => ({ ...f, last_name: e.target.value }))}
                    placeholder="Tus apellidos"
                    maxLength={150}
                  />
                  <div className="space-y-1">
                    <InputWithIcon
                      icon={FaEnvelope}
                      label="Correo electrónico"
                      type="email"
                      value={form.email}
                      onChange={(e) => puedeEditarEmail && setForm(f => ({ ...f, email: e.target.value }))}
                      placeholder="correo@ejemplo.com"
                      maxLength={254}
                      error={formErrors.email}
                      disabled={!puedeEditarEmail}
                      readOnly={!puedeEditarEmail}
                      title={!puedeEditarEmail ? 'Solo administradores pueden modificar el correo' : ''}
                    />
                    {!puedeEditarEmail && (
                      <p className="text-xs text-amber-600 flex items-center gap-1 mt-1">
                        <FaLock className="w-3 h-3" />
                        Solo administradores pueden modificar el correo electrónico
                      </p>
                    )}
                  </div>
                  <InputWithIcon
                    icon={FaPhone}
                    label="Teléfono"
                    type="tel"
                    value={form.telefono}
                    onChange={(e) => setForm(f => ({ ...f, telefono: e.target.value }))}
                    placeholder="(123) 456-7890"
                    maxLength={20}
                    error={formErrors.telefono}
                  />
                </div>
                
                <div className="mt-6 flex justify-end">
                  <button
                    type="submit"
                    disabled={savingPerfil}
                    className="px-6 py-2.5 rounded-lg text-white font-semibold disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-200 inline-flex items-center gap-2 shadow-sm hover:shadow"
                    style={{ backgroundColor: 'var(--color-primary, #9F2241)' }}
                    onMouseOver={(e) => e.currentTarget.style.backgroundColor = 'var(--color-primary-hover, #6B1839)'}
                    onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'var(--color-primary, #9F2241)'}
                  >
                    {savingPerfil ? (
                      <>
                        <FaSpinner className="animate-spin" />
                        Guardando...
                      </>
                    ) : (
                      <>
                        <FaSave />
                        Guardar cambios
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Tab: Seguridad */}
          {activeTab === 'security' && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-3">
                <div 
                  className="w-10 h-10 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: 'var(--color-warning-light, rgba(212, 160, 23, 0.1))' }}
                >
                  <FaKey className="w-5 h-5" style={{ color: 'var(--color-warning, #d4a017)' }} />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Cambiar contraseña</h3>
                  <p className="text-sm text-gray-500">Mantén tu cuenta segura con una contraseña fuerte</p>
                </div>
              </div>
              
              <form onSubmit={cambiarPassword} className="p-6">
                <div className="max-w-md space-y-5">
                  <PasswordInput
                    label="Contraseña actual"
                    value={passForm.old_password}
                    onChange={(e) => setPassForm(f => ({ ...f, old_password: e.target.value }))}
                    placeholder="Ingresa tu contraseña actual"
                    autoComplete="current-password"
                    show={showOldPassword}
                    onToggle={() => setShowOldPassword(!showOldPassword)}
                    error={passErrors.old_password}
                  />
                  
                  <div>
                    <PasswordInput
                      label="Nueva contraseña"
                      value={passForm.new_password}
                      onChange={(e) => setPassForm(f => ({ ...f, new_password: e.target.value }))}
                      placeholder="Ingresa tu nueva contraseña"
                      autoComplete="new-password"
                      show={showNewPassword}
                      onToggle={() => setShowNewPassword(!showNewPassword)}
                      error={passErrors.new_password}
                    />
                    {passForm.new_password && (
                      <PasswordStrengthIndicator password={passForm.new_password} />
                    )}
                  </div>
                  
                  <div>
                    <PasswordInput
                      label="Confirmar nueva contraseña"
                      value={passForm.confirm_password}
                      onChange={(e) => setPassForm(f => ({ ...f, confirm_password: e.target.value }))}
                      placeholder="Confirma tu nueva contraseña"
                      autoComplete="new-password"
                      show={showConfirmPassword}
                      onToggle={() => setShowConfirmPassword(!showConfirmPassword)}
                      error={passErrors.confirm_password}
                    />
                    {passForm.confirm_password && passForm.new_password === passForm.confirm_password && !passErrors.confirm_password && (
                      <p className="mt-2 text-xs text-green-600 flex items-center gap-1">
                        <FaCheck className="w-3 h-3" />
                        Las contraseñas coinciden
                      </p>
                    )}
                  </div>
                </div>
                
                <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                  <div className="flex gap-3">
                    <FaExclamationTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-amber-800">Importante</p>
                      <p className="text-sm text-amber-700 mt-1">
                        Al cambiar tu contraseña, tu sesión actual se cerrará y deberás iniciar sesión nuevamente.
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="mt-6 flex justify-end">
                  <button
                    type="submit"
                    disabled={passwordLoading}
                    className="px-6 py-2.5 rounded-lg text-white font-semibold disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-200 inline-flex items-center gap-2 shadow-sm hover:shadow"
                    style={{ backgroundColor: 'var(--color-warning, #d4a017)' }}
                    onMouseOver={(e) => e.currentTarget.style.opacity = '0.9'}
                    onMouseOut={(e) => e.currentTarget.style.opacity = '1'}
                  >
                    {passwordLoading ? (
                      <>
                        <FaSpinner className="animate-spin" />
                        Actualizando...
                      </>
                    ) : (
                      <>
                        <FaKey />
                        Actualizar contraseña
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Tab: Permisos */}
          {activeTab === 'permissions' && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-3">
                <div 
                  className="w-10 h-10 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: 'var(--color-primary-light, rgba(159, 34, 65, 0.1))' }}
                >
                  <FaShieldAlt className="w-5 h-5" style={{ color: 'var(--color-primary, #9F2241)' }} />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Permisos asignados</h3>
                  <p className="text-sm text-gray-500">
                    Permisos activos según tu rol: <span className="font-medium">{rolDisplay}</span>
                  </p>
                </div>
              </div>
              
              <div className="p-6">
                {Object.keys(permisosAgrupados).length > 0 ? (
                  <div className="space-y-6">
                    {Object.entries(permisosAgrupados).map(([categoria, permisosList]) => (
                      <div key={categoria}>
                        <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                          <span 
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: 'var(--color-primary, #9F2241)' }}
                          ></span>
                          {categoria}
                          <span className="text-xs font-normal text-gray-400">
                            ({permisosList.length})
                          </span>
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {permisosList.map(({ clave, etiqueta }) => (
                            <PermisoBadge key={clave} label={etiqueta} />
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <div className="w-16 h-16 mx-auto rounded-full bg-gray-100 flex items-center justify-center mb-4">
                      <FaShieldAlt className="w-8 h-8 text-gray-400" />
                    </div>
                    <p className="text-gray-600 font-medium">No hay permisos asignados</p>
                    <p className="text-sm text-gray-500 mt-1">Contacta al administrador si necesitas acceso adicional</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      <ConfirmModal
        open={showLogoutConfirm}
        title="Cerrar sesión"
        message="¿Estás seguro que deseas cerrar tu sesión? Tendrás que iniciar sesión nuevamente para acceder al sistema."
        confirmText="Cerrar sesión"
        onCancel={() => setShowLogoutConfirm(false)}
        onConfirm={logout}
      />
    </div>
  );
}

export default Perfil;
