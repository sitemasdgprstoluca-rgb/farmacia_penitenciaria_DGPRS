import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { usuariosAPI } from "../services/api";
import { usePermissions } from "../hooks/usePermissions";

function Perfil() {
  const { user, permisos, recargarUsuario } = usePermissions();
  const [perfil, setPerfil] = useState(null);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    telefono: "",
    cargo: "",
  });
  const [passForm, setPassForm] = useState({
    old_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [loading, setLoading] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const navigate = useNavigate();

  const cargarPerfil = async () => {
    setLoading(true);
    try {
      const res = await usuariosAPI.me();
      setPerfil(res.data);
      setForm((prev) => ({
        ...prev,
        first_name: res.data.first_name || "",
        last_name: res.data.last_name || "",
        email: res.data.email || "",
        telefono: res.data.telefono || "",
        cargo: res.data.cargo || "",
      }));
    } catch (error) {
      toast.error(error.response?.data?.detail || "No se pudo cargar el perfil");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarPerfil();
  }, []);

  const guardarDatos = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await usuariosAPI.actualizarPerfil(form);
      toast.success("Perfil actualizado");
      recargarUsuario?.();
      cargarPerfil();
    } catch (error) {
      const detail = error.response?.data?.detail || error.response?.data?.error;
      toast.error(detail || "No se pudo actualizar el perfil");
    } finally {
      setLoading(false);
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
    setPasswordLoading(true);
    try {
      await usuariosAPI.cambiarPasswordPropio(passForm);
      toast.success("Contraseña actualizada");
      setPassForm({ old_password: "", new_password: "", confirm_password: "" });
    } catch (error) {
      toast.error(error.response?.data?.error || "No se pudo cambiar la contraseña");
    } finally {
      setPasswordLoading(false);
    }
  };

  const permisosActivos = useMemo(() => {
    return Object.entries(permisos || {}).filter(([, value]) => Boolean(value));
  }, [permisos]);

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    navigate("/login");
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Mi Perfil</h1>
          <p className="text-gray-600 text-sm">Gestiona tu información y credenciales</p>
        </div>
        <button
          onClick={logout}
          className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-semibold hover:bg-red-700"
        >
          Cerrar sesión
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
              <div className="md:col-span-2">
                <label className="block text-xs font-semibold text-gray-500">Cargo</label>
                <input
                  type="text"
                  value={form.cargo}
                  onChange={(e) => setForm((f) => ({ ...f, cargo: e.target.value }))}
                  className="mt-1 w-full border-gray-200 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <button
                type="submit"
                className="px-5 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-60"
                disabled={loading}
              >
                {loading ? "Guardando..." : "Guardar cambios"}
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
              <p className="mt-1 text-xs text-gray-500">
                Mínimo 8 caracteres, una mayúscula y un número
              </p>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500">Confirmar nueva contraseña</label>
              <input
                type="password"
                value={passForm.confirm_password}
                onChange={(e) => setPassForm((f) => ({ ...f, confirm_password: e.target.value }))}
                className="mt-1 w-full border-gray-200 rounded-lg focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <button
              type="submit"
              className="w-full px-4 py-2 rounded-lg bg-emerald-600 text-white font-semibold hover:bg-emerald-700 disabled:opacity-60"
              disabled={passwordLoading}
            >
              {passwordLoading ? "Actualizando..." : "Actualizar contraseña"}
            </button>
          </form>
        </div>

        <div className="lg:col-span-2 bg-white rounded-xl shadow p-5">
          <h3 className="text-base font-semibold text-gray-900 mb-3">Permisos asignados</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
            {permisosActivos.map(([clave]) => (
              <div key={clave} className="px-3 py-2 rounded-lg bg-gray-50 border border-gray-100 text-sm font-semibold text-gray-800">
                {clave}
              </div>
            ))}
            {!permisosActivos.length && <p className="text-sm text-gray-600">No hay permisos asignados.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Perfil;
