import { useEffect, useRef, useState, useCallback } from "react";
import { toast } from "react-hot-toast";
import { notificacionesAPI } from "../services/api";
import { usePermissions } from "../hooks/usePermissions";

const NotificacionesBell = () => {
  const { user } = usePermissions();
  const [notificaciones, setNotificaciones] = useState([]);
  const [abierto, setAbierto] = useState(false);
  const [cargando, setCargando] = useState(false);
  const dropdownRef = useRef(null);
  const botonRef = useRef(null);

  const cargar = useCallback(async () => {
    if (!user) return;
    setCargando(true);
    try {
      const response = await notificacionesAPI.getAll({ ordering: "-fecha_creacion" });
      const data = response.data?.results || response.data || [];
      setNotificaciones(Array.isArray(data) ? data : []);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      if (msg) toast.error(msg);
    } finally {
      setCargando(false);
    }
  }, [user]);

  useEffect(() => {
    if (!user) return;
    cargar();
    const id = setInterval(cargar, 30000);
    return () => clearInterval(id);
  }, [user, cargar]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target) &&
        botonRef.current &&
        !botonRef.current.contains(event.target)
      ) {
        setAbierto(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const marcarLeida = async (id) => {
    try {
      await notificacionesAPI.marcarLeida(id);
      setNotificaciones((prev) => prev.map((n) => (n.id === id ? { ...n, leida: true } : n)));
    } catch (err) {
      toast.error(err.response?.data?.detail || "No se pudo marcar como leida");
    }
  };

  const eliminar = async (id) => {
    try {
      await notificacionesAPI.delete(id);
      setNotificaciones((prev) => prev.filter((n) => n.id !== id));
    } catch (err) {
      toast.error(err.response?.data?.detail || "No se pudo eliminar");
    }
  };

  const marcarTodas = async () => {
    const pendientes = notificaciones.filter((n) => !n.leida);
    try {
      for (const notif of pendientes) {
        await notificacionesAPI.marcarLeida(notif.id);
      }
      setNotificaciones((prev) => prev.map((n) => ({ ...n, leida: true })));
    } catch (err) {
      toast.error(err.response?.data?.detail || "No se pudieron marcar todas");
    }
  };

  const sinLeer = notificaciones.filter((n) => !n.leida).length;

  if (!user) return null;

  return (
    <div className="relative">
      <button
        ref={botonRef}
        onClick={() => setAbierto((v) => !v)}
        className="relative p-2 text-gray-600 hover:text-gray-900 transition"
        aria-label="Notificaciones"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>
        {sinLeer > 0 && (
          <span className="absolute -top-1 -right-1 inline-flex items-center justify-center px-2 py-1 text-xs font-bold text-white bg-red-600 rounded-full">
            {sinLeer > 9 ? "9+" : sinLeer}
          </span>
        )}
      </button>

      {abierto && (
        <div
          ref={dropdownRef}
          className="absolute right-0 mt-3 w-96 bg-white rounded-lg shadow-xl border border-gray-200 z-50 max-h-96 flex flex-col"
        >
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
            <div>
              <p className="text-sm font-semibold text-gray-900">Notificaciones</p>
              <p className="text-xs text-gray-500">{sinLeer} sin leer</p>
            </div>
            {sinLeer > 0 && (
              <button
                onClick={marcarTodas}
                className="text-xs text-blue-600 hover:text-blue-800"
                disabled={cargando}
              >
                Marcar todas
              </button>
            )}
          </div>

          <div className="flex-1 overflow-y-auto">
            {!notificaciones.length && (
              <div className="px-4 py-8 text-center text-gray-500 text-sm">No hay notificaciones</div>
            )}
            {notificaciones.map((notif) => (
              <div
                key={notif.id}
                className={`px-4 py-3 border-b border-gray-100 ${!notif.leida ? "bg-blue-50" : "bg-white"}`}
              >
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold ${
                    notif.tipo === "success"
                      ? "bg-green-500"
                      : notif.tipo === "warning"
                      ? "bg-yellow-500"
                      : notif.tipo === "error"
                      ? "bg-red-500"
                      : "bg-blue-500"
                  }`}>
                    {notif.tipo === "warning" ? "!" : notif.tipo === "error" ? "x" : notif.tipo === "success" ? "✓" : "i"}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900 truncate">{notif.titulo}</p>
                    <p className="text-sm text-gray-700 mt-0.5 break-words">
                      {notif.mensaje || notif.descripcion || ""}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {notif.fecha_creacion
                        ? new Date(notif.fecha_creacion).toLocaleString()
                        : ""}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {!notif.leida && (
                      <button
                        onClick={() => marcarLeida(notif.id)}
                        className="text-gray-400 hover:text-blue-600"
                        title="Marcar como leída"
                      >
                        ✓
                      </button>
                    )}
                    <button
                      onClick={() => eliminar(notif.id)}
                      className="text-gray-400 hover:text-red-600"
                      title="Eliminar"
                    >
                      x
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificacionesBell;
