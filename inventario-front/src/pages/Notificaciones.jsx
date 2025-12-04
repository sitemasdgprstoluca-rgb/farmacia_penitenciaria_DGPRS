import { useEffect, useState } from "react";
import { toast } from "react-hot-toast";
import ConfirmModal from "../components/ConfirmModal";
import { notificacionesAPI } from "../services/api";
import { usePermissions } from "../hooks/usePermissions";
import { ProtectedButton } from "../components/ProtectedAction";

const TIPOS = [
  { value: "", label: "Todos" },
  { value: "info", label: "Información" },
  { value: "success", label: "Éxitos" },
  { value: "warning", label: "Advertencias" },
  { value: "error", label: "Errores" },
];

const ESTADOS = [
  { value: "", label: "Todas" },
  { value: "false", label: "Pendientes" },
  { value: "true", label: "Leídas" },
];

const badgeByTipo = {
  info: "bg-blue-100 text-blue-700",
  success: "bg-green-100 text-green-700",
  warning: "bg-yellow-100 text-yellow-800",
  error: "bg-red-100 text-red-700",
};

function Notificaciones() {
  const { permisos, loading: loadingPermisos } = usePermissions();
  const [notificaciones, setNotificaciones] = useState([]);
  const [total, setTotal] = useState(0);
  const [sinLeer, setSinLeer] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [loading, setLoading] = useState(false);
  const [marcandoTodas, setMarcandoTodas] = useState(false); // Estado para evitar doble clic
  const [marcandoId, setMarcandoId] = useState(null); // ID de notificación que se está marcando
  const [deleteId, setDeleteId] = useState(null);
  const [eliminandoId, setEliminandoId] = useState(null); // ID de notificación que se está eliminando
  const [fechaError, setFechaError] = useState(''); // Error de validación de fechas
  const [filters, setFilters] = useState({
    tipo: "",
    desde: "",
    hasta: "",
    leida: "",
  });

  // Verificar permiso de ver notificaciones
  const tienePermisoVer = permisos?.verNotificaciones;
  const tienePermisoGestionar = permisos?.gestionarNotificaciones;

  const fetchData = async (targetPage = 1) => {
    // VALIDAR PERMISO antes de llamar al backend
    if (!tienePermisoVer) {
      console.warn('Notificaciones: Usuario sin permiso verNotificaciones');
      return;
    }
    
    // Validar rango de fechas antes de consultar
    if (filters.desde && filters.hasta && filters.desde > filters.hasta) {
      setFechaError('La fecha "Desde" no puede ser mayor a "Hasta"');
      return;
    }
    setFechaError('');
    
    setLoading(true);
    try {
      const params = {
        page: targetPage,
        page_size: pageSize,
        ordering: "-fecha_creacion",
      };
      if (filters.tipo) params.tipo = filters.tipo;
      if (filters.desde) params.desde = filters.desde;
      if (filters.hasta) params.hasta = filters.hasta;
      if (filters.leida) params.leida = filters.leida;

      const res = await notificacionesAPI.getAll(params);
      const data = res.data?.results || res.data || [];
      const count = res.data?.count ?? data.length;
      setNotificaciones(data);
      setTotal(count);
      try {
        const noLeidasRes = await notificacionesAPI.noLeidasCount();
        const unread = noLeidasRes.data?.no_leidas ?? noLeidasRes.data?.count ?? 0;
        setSinLeer(unread);
      } catch {
        const unreadLocal = data.filter((n) => !n.leida).length;
        setSinLeer(unreadLocal);
      }
      setPage(targetPage);
    } catch (error) {
      toast.error(error.response?.data?.detail || "No se pudieron cargar las notificaciones");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Solo cargar si tiene permiso
    if (tienePermisoVer) {
      fetchData(1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.tipo, filters.desde, filters.hasta, filters.leida, pageSize, tienePermisoVer]);

  // Ya no necesitamos filtrado local - el backend ya filtrÃ³
  const filtered = notificaciones;

  // Usar el conteo del backend en lugar del filtrado local
  const leidas = total - sinLeer;

  const marcarLeida = async (id) => {
    // Evitar doble clic
    if (marcandoId === id) return;
    setMarcandoId(id);
    try {
      await notificacionesAPI.marcarLeida(id);
      setNotificaciones((prev) => prev.map((n) => (n.id === id ? { ...n, leida: true } : n)));
      // Actualizar contador global de no leídas
      setSinLeer((prev) => Math.max(prev - 1, 0));
    } catch (error) {
      toast.error(error.response?.data?.detail || "No se pudo marcar como leída");
    } finally {
      setMarcandoId(null);
    }
  };

  const marcarTodas = async () => {
    if (sinLeer === 0 || marcandoTodas) return;
    setMarcandoTodas(true);
    try {
      // Construir parámetros respetando los filtros activos
      const params = {};
      if (filters.tipo) params.tipo = filters.tipo;
      if (filters.desde) params.desde = filters.desde;
      if (filters.hasta) params.hasta = filters.hasta;
      // Solo marcar las no leídas (no tiene sentido marcar las ya leídas)
      params.leida = 'false';
      
      // Usar endpoint batch pasando los filtros activos
      const res = await notificacionesAPI.marcarTodasLeidas(params);
      const marcadas = res.data?.marcadas || 0;
      
      // Actualizar solo las notificaciones visibles que coinciden con filtros
      setNotificaciones((prev) => prev.map((n) => ({ ...n, leida: true })));
      setSinLeer((prev) => Math.max(prev - marcadas, 0));
      toast.success(`${marcadas} notificaciones marcadas como leídas`);
    } catch (error) {
      toast.error(error.response?.data?.detail || "No se pudo completar la acción");
    } finally {
      setMarcandoTodas(false);
    }
  };

  const eliminar = async (id) => {
    // Evitar doble clic
    if (eliminandoId === id) return;
    setEliminandoId(id);
    
    const notif = notificaciones.find((n) => n.id === id);
    try {
      await notificacionesAPI.delete(id);
      setNotificaciones((prev) => prev.filter((n) => n.id !== id));
      setTotal((prev) => Math.max(prev - 1, 0));
      // Si era no leída, decrementar contador
      if (notif && !notif.leida) {
        setSinLeer((prev) => Math.max(prev - 1, 0));
      }
      toast.success("Notificación eliminada");
      // Si la página queda vacía y hay más páginas, retroceder
      if (notificaciones.length === 1 && page > 1) {
        fetchData(page - 1);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "No se pudo eliminar");
    } finally {
      setDeleteId(null);
      setEliminandoId(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  // Si el usuario no tiene permiso para ver notificaciones, mostrar mensaje
  if (!tienePermisoVer) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
          <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h2 className="text-xl font-semibold text-gray-900">Acceso denegado</h2>
        <p className="text-gray-600 text-center max-w-md">
          No tienes permiso para ver las notificaciones. Contacta al administrador si crees que deberías tener acceso.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Notificaciones</h1>
          <p className="text-gray-600 text-sm">Historial de eventos y alertas del sistema</p>
        </div>
        <div className="flex items-center gap-3">
          <ProtectedButton
            permission="gestionarNotificaciones"
            onClick={marcarTodas}
            className="px-4 py-2 rounded-lg bg-primary-600 text-white text-sm hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed"
            disabled={loading || marcandoTodas || sinLeer === 0}
          >
            {marcandoTodas ? 'Marcando...' : 'Marcar todas como leídas'}
          </ProtectedButton>
          <ProtectedButton
            permission="verNotificaciones"
            onClick={() => fetchData(page)}
            className="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={loading}
          >
            Refrescar
          </ProtectedButton>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="md:col-span-3 bg-white rounded-xl shadow p-4">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-500">Tipo</label>
              <select
                value={filters.tipo}
                onChange={(e) => setFilters((f) => ({ ...f, tipo: e.target.value }))}
                className="mt-1 w-full border-gray-200 rounded-lg focus:ring-primary-500 focus:border-primary-500"
              >
                {TIPOS.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500">Estado</label>
              <select
                value={filters.leida}
                onChange={(e) => setFilters((f) => ({ ...f, leida: e.target.value }))}
                className="mt-1 w-full border-gray-200 rounded-lg focus:ring-primary-500 focus:border-primary-500"
              >
                {ESTADOS.map((e) => (
                  <option key={e.value} value={e.value}>
                    {e.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500">Desde</label>
              <input
                type="date"
                value={filters.desde}
                onChange={(e) => setFilters((f) => ({ ...f, desde: e.target.value }))}
                className={`mt-1 w-full border-gray-200 rounded-lg focus:ring-primary-500 focus:border-primary-500 ${fechaError ? 'border-red-500' : ''}`}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500">Hasta</label>
              <input
                type="date"
                value={filters.hasta}
                onChange={(e) => setFilters((f) => ({ ...f, hasta: e.target.value }))}
                className={`mt-1 w-full border-gray-200 rounded-lg focus:ring-primary-500 focus:border-primary-500 ${fechaError ? 'border-red-500' : ''}`}
              />
              {fechaError && (
                <p className="text-xs text-red-600 mt-1">{fechaError}</p>
              )}
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500">Por página</label>
              <select
                value={pageSize}
                onChange={(e) => setPageSize(Number(e.target.value))}
                className="mt-1 w-full border-gray-200 rounded-lg focus:ring-primary-500 focus:border-primary-500"
              >
                {[10, 20, 50].map((n) => (
                  <option key={n} value={n}>
                    {n} registros
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow p-4">
          <p className="text-sm text-gray-500">Sin leer</p>
          <p className="text-3xl font-bold text-primary-700">{sinLeer}</p>
          <p className="text-xs text-gray-500 mt-1">Leídas: {leidas} / Total: {total}</p>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Título</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Mensaje</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Tipo</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Fecha</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Estado</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-sm text-gray-500">
                    Cargando notificaciones...
                  </td>
                </tr>
              )}

              {!loading && !filtered.length && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-sm text-gray-500">
                    No hay notificaciones con los filtros seleccionados.
                  </td>
                </tr>
              )}

              {!loading &&
                filtered.map((notif) => (
                  <tr key={notif.id} className={!notif.leida ? "bg-blue-50/60" : ""}>
                    <td className="px-4 py-3 text-sm font-semibold text-gray-900">{notif.titulo}</td>
                    <td className="px-4 py-3 text-sm text-gray-700 max-w-xs">
                      <p className="line-clamp-2">{notif.mensaje || notif.descripcion}</p>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-semibold ${badgeByTipo[notif.tipo] || "bg-gray-100 text-gray-700"}`}
                      >
                        {notif.tipo || "info"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {notif.fecha_creacion ? new Date(notif.fecha_creacion).toLocaleString() : "-"}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span
                        className={`inline-flex items-center gap-2 px-2 py-1 rounded-full text-xs font-semibold ${
                          notif.leida ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-800"
                        }`}
                      >
                        <span className={`w-2 h-2 rounded-full ${notif.leida ? "bg-green-500" : "bg-yellow-500"}`} />
                          {notif.leida ? "Leída" : "Pendiente"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-right space-x-2">
                      {!notif.leida && (
                        <ProtectedButton
                          permission="verNotificaciones"
                          onClick={() => marcarLeida(notif.id)}
                          disabled={marcandoId === notif.id}
                          className="px-3 py-1 rounded-lg border border-primary-100 text-primary-600 hover:bg-primary-50 text-xs disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {marcandoId === notif.id ? 'Marcando...' : 'Marcar leída'}
                        </ProtectedButton>
                      )}
                      <ProtectedButton
                        permission="gestionarNotificaciones"
                        onClick={() => setDeleteId(notif.id)}
                        disabled={eliminandoId === notif.id}
                        className="px-3 py-1 rounded-lg border border-red-100 text-red-600 hover:bg-red-50 text-xs disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {eliminandoId === notif.id ? 'Eliminando...' : 'Eliminar'}
                      </ProtectedButton>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between px-4 py-3 bg-gray-50 border-t border-gray-200 gap-3">
          <div className="text-sm text-gray-600">
            Página {page} de {totalPages} · {total} registros
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchData(Math.max(1, page - 1))}
              className="px-3 py-1 rounded border border-gray-200 text-sm disabled:opacity-50"
              disabled={page <= 1 || loading}
            >
              Anterior
            </button>
            <button
              onClick={() => fetchData(Math.min(totalPages, page + 1))}
              className="px-3 py-1 rounded border border-gray-200 text-sm disabled:opacity-50"
              disabled={page >= totalPages || loading}
            >
              Siguiente
            </button>
          </div>
        </div>
      </div>

      <ConfirmModal
        open={Boolean(deleteId)}
        title="Eliminar notificación"
        message="Esta acción eliminará la notificación de manera permanente."
        confirmText="Eliminar"
        onCancel={() => setDeleteId(null)}
        onConfirm={() => eliminar(deleteId)}
      />
    </div>
  );
}

export default Notificaciones;

