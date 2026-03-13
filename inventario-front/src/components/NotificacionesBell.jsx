import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { notificacionesAPI } from "../services/api";
import { usePermissions } from "../hooks/usePermissions";
import { hasAccessToken } from "../services/tokenManager";

const BELL_PAGE_SIZE = 10; // Límite de notificaciones en el dropdown

/**
 * Componente de campana de notificaciones.
 * Valida el permiso verNotificaciones antes de renderizar o hacer llamadas API.
 * Recibe opcionalmente un contador externo desde Layout para evitar doble polling.
 */
const NotificacionesBell = ({ externalCount, onCountChange }) => {
  const navigate = useNavigate();
  const { user, permisos } = usePermissions();
  const [notificaciones, setNotificaciones] = useState([]);
  const [sinLeer, setSinLeer] = useState(0);
  const [abierto, setAbierto] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [marcandoTodas, setMarcandoTodas] = useState(false); // Estado para evitar doble clic
  const [actionLoading, setActionLoading] = useState(null); // ID de notificación en acción
  const dropdownRef = useRef(null);
  const botonRef = useRef(null);

  // IDs descartados desde la campana (dismiss local, sin borrar del backend).
  // Se persisten en localStorage por usuario para sobrevivir recargas.
  const dismissKey = user?.id ? `bell_dismissed_${user.id}` : null;
  const [dismissed, setDismissed] = useState(() => {
    if (!dismissKey) return new Set();
    try {
      const raw = localStorage.getItem(dismissKey);
      return raw ? new Set(JSON.parse(raw)) : new Set();
    } catch {
      return new Set();
    }
  });

  // Sincronizar dismissed con localStorage cuando cambia
  useEffect(() => {
    if (!dismissKey) return;
    try {
      localStorage.setItem(dismissKey, JSON.stringify([...dismissed]));
    } catch { /* cuota excedida, ignorar */ }
  }, [dismissed, dismissKey]);

  // Limpiar dismissed cuando el usuario cambia (logout / cambio de cuenta)
  useEffect(() => {
    if (user?.id) {
      const key = `bell_dismissed_${user.id}`;
      try {
        const raw = localStorage.getItem(key);
        setDismissed(raw ? new Set(JSON.parse(raw)) : new Set());
      } catch {
        setDismissed(new Set());
      }
    } else {
      setDismissed(new Set());
    }
  }, [user?.id]);

  // Usar contador externo si se proporciona (desde Layout)
  const displayCount = externalCount !== undefined ? externalCount : sinLeer;

  // Verificar si tiene permiso de ver notificaciones
  const tienePermiso = permisos?.verNotificaciones;

  // Cargar contador de no leídas (endpoint dedicado)
  const cargarContador = useCallback(async () => {
    // ISS-FIX: Validar permiso Y token disponible para evitar 401
    if (!user || !tienePermiso || !hasAccessToken()) return;
    try {
      const res = await notificacionesAPI.noLeidasCount();
      const count = res.data?.no_leidas ?? 0;
      setSinLeer(count);
      // Notificar al padre si existe callback
      if (onCountChange) onCountChange(count);
    } catch {
      // Silencioso - el contador se actualizará en la próxima carga
    }
  }, [user, tienePermiso, onCountChange]);

  // Cargar notificaciones para el dropdown (limitado)
  const cargar = useCallback(async () => {
    // ISS-FIX: Validar permiso Y token disponible para evitar 401
    if (!user || !tienePermiso || !hasAccessToken()) return;
    setCargando(true);
    try {
      const [notifRes, countRes] = await Promise.all([
        notificacionesAPI.getAll({ 
          ordering: "-fecha_creacion", 
          page_size: BELL_PAGE_SIZE 
        }),
        notificacionesAPI.noLeidasCount()
      ]);
      const data = notifRes.data?.results || notifRes.data || [];
      const notificacionesArray = Array.isArray(data) ? data : [];
      setNotificaciones(notificacionesArray);
      
      // ISS-FIX: Sincronizar contador con notificaciones reales no leídas
      // El contador del backend puede estar desincronizado si hubo cambios de sesión
      const noLeidasEnLista = notificacionesArray.filter(n => !n.leida).length;
      const countBackend = countRes.data?.no_leidas ?? 0;
      
      // Usar el mayor de los dos para evitar mostrar "1 sin leer" pero lista vacía
      // Si hay notificaciones, usar el count de las no leídas reales
      // Si no hay notificaciones pero backend dice que hay, puede ser paginación o error
      const countFinal = notificacionesArray.length > 0 ? countBackend : Math.min(countBackend, noLeidasEnLista);
      
      setSinLeer(countFinal);
      // Notificar al padre si existe callback
      if (onCountChange) onCountChange(countFinal);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      if (msg) toast.error(msg);
    } finally {
      setCargando(false);
    }
  }, [user, tienePermiso, onCountChange]);

  useEffect(() => {
    // No iniciar polling sin permiso
    if (!user || !tienePermiso) {
      return;
    }
    
    cargar();
    // Refresco cada 30s solo del contador para minimizar tráfico
    // Solo si no hay contador externo (evita doble polling)
    if (externalCount === undefined) {
      const id = setInterval(cargarContador, 30000);
      return () => clearInterval(id);
    }
  }, [user, tienePermiso, cargar, cargarContador, externalCount]);

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
    if (actionLoading) return; // Evitar acción si hay otra en curso
    setActionLoading(id);
    try {
      await notificacionesAPI.marcarLeida(id);
      setNotificaciones((prev) => prev.map((n) => (n.id === id ? { ...n, leida: true } : n)));
      const nuevoContador = Math.max(sinLeer - 1, 0);
      setSinLeer(nuevoContador);
      // Sincronizar contador externo (Layout)
      if (onCountChange) onCountChange(nuevoContador);
    } catch (err) {
      toast.error(err.response?.data?.detail || "No se pudo marcar como leida");
    } finally {
      setActionLoading(null);
    }
  };

  // Quitar notificación de la campana (dismiss local).
  // NO borra el registro del backend → sigue visible en el historial.
  const descartarDesdeCampana = (id) => {
    const notif = notificaciones.find((n) => n.id === id);
    setDismissed((prev) => new Set([...prev, id]));
    // Si era no leída, descontar del badge
    if (notif && !notif.leida) {
      const nuevoContador = Math.max(sinLeer - 1, 0);
      setSinLeer(nuevoContador);
      if (onCountChange) onCountChange(nuevoContador);
    }
  };

  const marcarTodas = async () => {
    if (sinLeer === 0 || marcandoTodas) return;
    setMarcandoTodas(true);
    try {
      // Usar endpoint batch en lugar de loop individual
      const res = await notificacionesAPI.marcarTodasLeidas();
      const marcadas = res.data?.marcadas || 0;
      setNotificaciones((prev) => prev.map((n) => ({ ...n, leida: true })));
      setSinLeer(0);
      // Sincronizar contador externo (Layout)
      if (onCountChange) onCountChange(0);
      if (marcadas > 0) {
        toast.success(`${marcadas} notificaciones marcadas`);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "No se pudieron marcar todas");
    } finally {
      setMarcandoTodas(false);
    }
  };

  // ISS-NOTIF: Navegar al recurso asociado a la notificación
  const handleNotificationClick = async (notif) => {
    // Si tiene URL, navegar a ella
    const url = notif.url || (notif.datos?.requisicion_id ? `/requisiciones/${notif.datos.requisicion_id}` : null);
    
    if (url) {
      // Marcar como leída si no lo está
      if (!notif.leida) {
        await marcarLeida(notif.id);
      }
      setAbierto(false);
      navigate(url);
    }
  };

  // ISS-FIX: Recargar notificaciones al abrir el dropdown para asegurar datos frescos
  const handleToggleDropdown = () => {
    const nuevoEstado = !abierto;
    setAbierto(nuevoEstado);
    // Al abrir, recargar notificaciones frescas
    if (nuevoEstado && !cargando) {
      cargar();
    }
  };

  // No renderizar si no hay usuario O no tiene permiso de ver notificaciones
  if (!user || !tienePermiso) return null;

  return (
    <div className="relative">
      <button
        ref={botonRef}
        onClick={handleToggleDropdown}
        className="relative w-9 h-9 flex items-center justify-center hover:bg-gray-100 transition-colors rounded-lg text-gray-500 hover:text-gray-700"
        aria-label="Notificaciones"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
          />
        </svg>
        {displayCount > 0 && (
          <span className="absolute top-1 right-1 flex items-center justify-center min-w-[16px] h-4 px-1 text-[10px] font-bold text-white bg-red-500 rounded-full">
            {displayCount > 9 ? "9+" : displayCount}
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
              <p className="text-xs text-gray-500">{sinLeer} sin leer · <span className="cursor-pointer text-primary-600 hover:underline" onClick={() => { setAbierto(false); navigate('/notificaciones'); }}>Ver historial</span></p>
            </div>
            {sinLeer > 0 && (
              <button
                onClick={marcarTodas}
                className="text-xs text-primary-600 hover:text-primary-800 disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={cargando || marcandoTodas}
              >
                {marcandoTodas ? 'Marcando...' : 'Marcar todas'}
              </button>
            )}
          </div>

          <div className="flex-1 overflow-y-auto">
            {cargando && (
              <div className="px-4 py-8 text-center text-gray-500 text-sm">
                <div className="animate-spin rounded-full h-6 w-6 border-2 border-gray-400 border-t-primary-600 mx-auto mb-2" />
                Cargando notificaciones...
              </div>
            )}
            {!cargando && !notificaciones.filter((n) => !dismissed.has(n.id)).length && (
              <div className="px-4 py-8 text-center text-gray-500 text-sm">No hay notificaciones</div>
            )}
            {!cargando && notificaciones.filter((n) => !dismissed.has(n.id)).map((notif) => {
              // Determinar si la notificación tiene un enlace navegable
              const tieneEnlace = notif.url || notif.datos?.requisicion_id;
              
              return (
              <div
                key={notif.id}
                className={`px-4 py-3 border-b border-gray-100 ${!notif.leida ? "bg-blue-50" : "bg-white"} ${tieneEnlace ? "cursor-pointer hover:bg-gray-50" : ""}`}
                onClick={tieneEnlace ? () => handleNotificationClick(notif) : undefined}
                role={tieneEnlace ? "button" : undefined}
                tabIndex={tieneEnlace ? 0 : undefined}
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
                  <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                    {!notif.leida && (
                      <button
                        onClick={() => marcarLeida(notif.id)}
                        disabled={actionLoading === notif.id}
                        className="text-gray-400 hover:text-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Marcar como leída"
                      >
                        {actionLoading === notif.id ? <div className="animate-spin rounded-full h-3 w-3 border-2 border-gray-400 border-t-transparent inline-block" /> : '✓'}
                      </button>
                    )}
                    <button
                      onClick={() => descartarDesdeCampana(notif.id)}
                      className="text-gray-400 hover:text-red-600"
                      title="Quitar de la campana (queda en historial)"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              </div>
            );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificacionesBell;
