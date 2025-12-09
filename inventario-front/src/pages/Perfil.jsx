import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { FaSpinner, FaSignOutAlt, FaSave, FaKey } from "react-icons/fa";
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

// Etiquetas amigables para permisos
const ETIQUETAS_PERMISOS = {
  // Permisos de módulos principales
  verDashboard: "Ver Dashboard",
  verProductos: "Ver Productos",
  verLotes: "Ver Lotes",
  verRequisiciones: "Ver Requisiciones",
  verCentros: "Ver Centros",
  verUsuarios: "Ver Usuarios",
  verReportes: "Ver Reportes",
  verTrazabilidad: "Ver Trazabilidad",
  verAuditoria: "Ver Auditoría",
  verNotificaciones: "Ver Notificaciones",
  verPerfil: "Ver Perfil",
  verMovimientos: "Ver Movimientos",
  verDonaciones: "Ver Donaciones",
  // Permisos de requisiciones
  crearRequisicion: "Crear Requisiciones",
  editarRequisicion: "Editar Requisiciones",
  eliminarRequisicion: "Eliminar Requisiciones",
  enviarRequisicion: "Enviar Requisiciones",
  autorizarRequisicion: "Autorizar Requisiciones",
  rechazarRequisicion: "Rechazar Requisiciones",
  surtirRequisicion: "Surtir Requisiciones",
  cancelarRequisicion: "Cancelar Requisiciones",
  confirmarRecepcion: "Confirmar Recepción",
  descargarHojaRecoleccion: "Descargar Hoja de Recolección",
  // Permisos de gestión de usuarios
  gestionUsuarios: "Gestionar Usuarios",
  // Permisos de lotes
  crearLote: "Crear Lotes",
  editarLote: "Editar Lotes",
  eliminarLote: "Eliminar Lotes",
  exportarLotes: "Exportar Lotes",
  importarLotes: "Importar Lotes",
  // Permisos de movimientos
  crearMovimiento: "Crear Movimientos",
  exportarMovimientos: "Exportar Movimientos",
  // Permisos de productos
  crearProducto: "Crear Productos",
  editarProducto: "Editar Productos",
  eliminarProducto: "Eliminar Productos",
  exportarProductos: "Exportar Productos",
  importarProductos: "Importar Productos",
  // Permisos de notificaciones
  gestionarNotificaciones: "Gestionar Notificaciones",
  // Permisos de configuración
  configurarTema: "Configurar Tema",
  // Permisos de donaciones
  crearDonacion: "Crear Donaciones",
  editarDonacion: "Editar Donaciones",
  eliminarDonacion: "Eliminar Donaciones",
  recibirDonacion: "Recibir Donaciones",
  rechazarDonacion: "Rechazar Donaciones",
};

function Perfil() {
  const { user, permisos, recargarUsuario } = usePermissions();
  const [perfil, setPerfil] = useState(null);
  const [perfilError, setPerfilError] = useState(null);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    telefono: "",
  });
  const [passForm, setPassForm] = useState({
    old_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [loadingPerfil, setLoadingPerfil] = useState(true);
  const [savingPerfil, setSavingPerfil] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const navigate = useNavigate();

  const cargarPerfil = async () => {
    setLoadingPerfil(true);
    setPerfilError(null);
    try {
      const res = await usuariosAPI.me();
      setPerfil(res.data);
      setForm((prev) => ({
        ...prev,
        first_name: res.data.first_name || "",
        last_name: res.data.last_name || "",
        email: res.data.email || "",
        telefono: res.data.telefono || "",
      }));
    } catch (error) {
      const status = error.response?.status;
      const detail = error.response?.data?.detail || "No se pudo cargar el perfil";
      
      if (status === 403) {
        setPerfilError("No tienes permisos para ver tu perfil. Contacta al administrador.");
        toast.error("Acceso denegado al perfil");
      } else if (status === 401) {
        // Sesión expirada, redirigir al login
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
  };

  useEffect(() => {
    cargarPerfil();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const guardarDatos = async (e) => {
    e.preventDefault();
    
    // No permitir guardar si el perfil no se cargó correctamente
    if (!perfil) {
      toast.error("No se puede guardar: el perfil no se ha cargado correctamente");
      return;
    }
    
    setSavingPerfil(true);
    try {
      await usuariosAPI.actualizarPerfil(form);
      toast.success("Perfil actualizado");
      
      // Recargar usuario con manejo de errores
      try {
        await recargarUsuario?.();
      } catch (reloadError) {
        console.error("Error al recargar usuario:", reloadError);
        // Si falla la recarga, notificar pero no bloquear
        toast.error("Perfil guardado, pero hubo un error al sincronizar. Recarga la página.");
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
    if (!passForm.new_password || !passForm.old_password) {
      toast.error("Completa los campos de contraseña");
      return;
    }
    if (passForm.new_password !== passForm.confirm_password) {
      toast.error("Las contraseñas nuevas no coinciden");
      return;
    }
    // Validar reglas de contraseña según especificación SIFP
    if (passForm.new_password.length < 8) {
      toast.error("La contraseña debe tener mínimo 8 caracteres");
      return;
    }
    if (!/[A-Z]/.test(passForm.new_password)) {
      toast.error("La contraseña debe tener al menos una mayúscula");
      return;
    }
    if (!/[a-z]/.test(passForm.new_password)) {
      toast.error("La contraseña debe tener al menos una minúscula");
      return;
    }
    if (!/[0-9]/.test(passForm.new_password)) {
      toast.error("La contraseña debe tener al menos un número");
      return;
    }
    // Validar que la nueva contraseña sea diferente de la actual
    if (passForm.new_password === passForm.old_password) {
      toast.error("La nueva contraseña debe ser diferente a la actual");
      return;
    }
    setPasswordLoading(true);
    try {
      await usuariosAPI.cambiarPasswordPropio(passForm);
      toast.success("Contraseña actualizada. Serás redirigido al login.");
      setPassForm({ old_password: "", new_password: "", confirm_password: "" });
      // Según especificación: cerrar sesión forzosamente después de cambiar contraseña
      setTimeout(() => {
        limpiarSesionYRedirigir();
      }, PASSWORD_CHANGE_LOGOUT_DELAY);
    } catch (error) {
      toast.error(error.response?.data?.error || "No se pudo cambiar la contraseña");
    } finally {
      setPasswordLoading(false);
    }
  };

  // Filtrar permisos para mostrar solo los relevantes al usuario
  const permisosVisibles = useMemo(() => {
    return Object.entries(permisos || {})
      .filter(([clave, value]) => {
        // Excluir permisos internos/técnicos
        if (PERMISOS_INTERNOS.includes(clave)) return false;
        // Solo mostrar permisos activos
        return Boolean(value);
      })
      .map(([clave, value]) => ({
        clave,
        etiqueta: ETIQUETAS_PERMISOS[clave] || clave,
        value,
      }));
  }, [permisos]);

  // Limpiar sesión completamente y redirigir
  const limpiarSesionYRedirigir = () => {
    clearTokens();
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    navigate("/login");
  };

  const logout = async () => {
    setLoggingOut(true);
    try {
      // Llamar al endpoint de logout para invalidar el refresh token en servidor
      await authAPI.logout();
    } catch (error) {
      // Si falla el logout en servidor, continuar con limpieza local
      console.error("Error al cerrar sesión en servidor:", error);
    } finally {
      // Siempre limpiar localmente y redirigir
      limpiarSesionYRedirigir();
      setLoggingOut(false);
    }
  };

  // Mostrar error si no se pudo cargar el perfil
  if (perfilError && !loadingPerfil) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Mi Perfil</h1>
            <p className="text-gray-600 text-sm">Gestiona tu información y credenciales</p>
          </div>
          <button
            onClick={logout}
            disabled={loggingOut}
            className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-semibold hover:bg-red-700 disabled:opacity-60 flex items-center gap-2"
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
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-700 font-semibold mb-2">Error al cargar el perfil</p>
          <p className="text-red-600 text-sm mb-4">{perfilError}</p>
          <button
            onClick={cargarPerfil}
            className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-semibold hover:bg-red-700"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Mi Perfil</h1>
          <p className="text-gray-600 text-sm">Gestiona tu información y credenciales</p>
        </div>
        <button
          onClick={logout}
          disabled={loggingOut}
          className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-semibold hover:bg-red-700 disabled:opacity-60 flex items-center gap-2"
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow p-5 space-y-3">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Información básica</p>
          <div className="flex items-center gap-3">
            <div className="w-14 h-14 rounded-full bg-gradient-to-br from-rose-500 to-red-600 flex items-center justify-center text-white text-xl font-bold">
              {perfil?.first_name?.[0] || perfil?.username?.[0] || "U"}
            </div>
            <div>
              <p className="text-lg font-semibold text-gray-900">
                {perfil?.first_name} {perfil?.last_name}
              </p>
              <p className="text-sm text-gray-600">{perfil?.email}</p>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-gray-500">Usuario</span>
              <span className="font-semibold text-gray-900">{perfil?.username || user?.username}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-500">Rol</span>
              <span className="font-semibold text-gray-900">{perfil?.rol || user?.rol}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-500">Centro</span>
              <span className="font-semibold text-gray-900">{perfil?.centro_nombre || "No asignado"}</span>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 bg-white rounded-xl shadow p-5">
          <form className="space-y-4" onSubmit={guardarDatos}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500">Nombre</label>
                <input
                  type="text"
                  value={form.first_name}
                  onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))}
                  className="mt-1 w-full border-gray-200 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500">Apellidos</label>
                <input
                  type="text"
                  value={form.last_name}
                  onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))}
                  className="mt-1 w-full border-gray-200 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500">Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                  className="mt-1 w-full border-gray-200 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500">Teléfono</label>
                <input
                  type="text"
                  value={form.telefono}
                  onChange={(e) => setForm((f) => ({ ...f, telefono: e.target.value }))}
                  className="mt-1 w-full border-gray-200 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <button
                type="submit"
                className="px-5 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-60 flex items-center gap-2"
                disabled={savingPerfil || loadingPerfil || !perfil}
                title={!perfil ? "Carga el perfil primero" : ""}
              >
                {savingPerfil ? (
                  <>
                    <FaSpinner className="animate-spin" />
                    Guardando...
                  </>
                ) : loadingPerfil ? (
                  <>
                    <FaSpinner className="animate-spin" />
                    Cargando...
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
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow p-5">
          <h3 className="text-base font-semibold text-gray-900 mb-3">Cambiar contraseña</h3>
          <form className="space-y-3" onSubmit={cambiarPassword}>
            <div>
              <label className="block text-xs font-semibold text-gray-500">Contraseña actual</label>
              <input
                type="password"
                value={passForm.old_password}
                onChange={(e) => setPassForm((f) => ({ ...f, old_password: e.target.value }))}
                className="mt-1 w-full border-gray-200 rounded-lg focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500">Nueva contraseña</label>
              <input
                type="password"
                value={passForm.new_password}
                onChange={(e) => setPassForm((f) => ({ ...f, new_password: e.target.value }))}
                className="mt-1 w-full border-gray-200 rounded-lg focus:ring-primary-500 focus:border-primary-500"
              />
              {/* Indicadores de validación de contraseña */}
              <div className="mt-2 space-y-1">
                <p className={`text-xs flex items-center gap-1 ${passForm.new_password.length >= 8 ? 'text-green-600' : 'text-gray-400'}`}>
                  {passForm.new_password.length >= 8 ? '✓' : '○'} Mínimo 8 caracteres
                </p>
                <p className={`text-xs flex items-center gap-1 ${/[A-Z]/.test(passForm.new_password) ? 'text-green-600' : 'text-gray-400'}`}>
                  {/[A-Z]/.test(passForm.new_password) ? '✓' : '○'} Al menos una mayúscula
                </p>
                <p className={`text-xs flex items-center gap-1 ${/[a-z]/.test(passForm.new_password) ? 'text-green-600' : 'text-gray-400'}`}>
                  {/[a-z]/.test(passForm.new_password) ? '✓' : '○'} Al menos una minúscula
                </p>
                <p className={`text-xs flex items-center gap-1 ${/[0-9]/.test(passForm.new_password) ? 'text-green-600' : 'text-gray-400'}`}>
                  {/[0-9]/.test(passForm.new_password) ? '✓' : '○'} Al menos un número
                </p>
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500">Confirmar nueva contraseña</label>
              <input
                type="password"
                value={passForm.confirm_password}
                onChange={(e) => setPassForm((f) => ({ ...f, confirm_password: e.target.value }))}
                className="mt-1 w-full border-gray-200 rounded-lg focus:ring-primary-500 focus:border-primary-500"
              />
              {passForm.confirm_password && passForm.new_password !== passForm.confirm_password && (
                <p className="mt-1 text-xs text-red-500">Las contraseñas no coinciden</p>
              )}
              {passForm.confirm_password && passForm.new_password === passForm.confirm_password && (
                <p className="mt-1 text-xs text-green-600">✓ Las contraseñas coinciden</p>
              )}
            </div>
            <button
              type="submit"
              className="w-full px-4 py-2 rounded-lg bg-emerald-600 text-white font-semibold hover:bg-emerald-700 disabled:opacity-60 flex items-center justify-center gap-2"
              disabled={passwordLoading}
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
          </form>
        </div>

        <div className="lg:col-span-2 bg-white rounded-xl shadow p-5">
          <h3 className="text-base font-semibold text-gray-900 mb-3">Permisos asignados</h3>
          <p className="text-xs text-gray-500 mb-3">
            Estos son los permisos activos según tu rol ({permisos?.role || user?.rol || "—"})
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
            {permisosVisibles.map(({ clave, etiqueta }) => (
              <div key={clave} className="px-3 py-2 rounded-lg bg-gray-50 border border-gray-100 text-sm font-semibold text-gray-800">
                {etiqueta}
              </div>
            ))}
            {!permisosVisibles.length && <p className="text-sm text-gray-600">No hay permisos asignados.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Perfil;
