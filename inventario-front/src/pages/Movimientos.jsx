import { useEffect, useMemo, useState, useRef } from "react";
import { useLocation } from "react-router-dom";
import { toast } from "react-hot-toast";
import Pagination from "../components/Pagination";
import { movimientosAPI, productosAPI, centrosAPI, lotesAPI, descargarArchivo } from "../services/api";

const PAGE_SIZE = 25;

const Movimientos = () => {
  const location = useLocation();
  const highlightId = location.state?.highlightId;
  const highlightRef = useRef(null);
  
  const [movimientos, setMovimientos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState({ entradas: 0, salidas: 0, balance: 0 });
  const [expandedId, setExpandedId] = useState(highlightId || null);

  // filtros
  const [filtros, setFiltros] = useState({
    fecha_inicio: "",
    fecha_fin: "",
    tipo: "",
    producto: "",
    centro: "",
    lote: "",
    search: "",
  });

  const [productos, setProductos] = useState([]);
  const [centros, setCentros] = useState([]);
  const [lotes, setLotes] = useState([]);
  const [lotesDisponibles, setLotesDisponibles] = useState([]);

  // Formulario de registro
  const [formData, setFormData] = useState({
    lote: "",
    tipo: "entrada",
    cantidad: "",
    centro: "",
    observaciones: "",
  });
  const [productoFiltro, setProductoFiltro] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const columnas = useMemo(
    () => ["producto", "tipo", "cantidad", "centro", "fecha"],
    []
  );

  const cargarCatalogos = async () => {
    try {
      const [prodResp, centroResp, lotesResp] = await Promise.all([
        productosAPI.getAll({ page_size: 500, ordering: "descripcion", activo: true }),
        centrosAPI.getAll({ page_size: 100, ordering: "nombre", activo: true }),
        lotesAPI.getAll({ page_size: 500, ordering: "-fecha_caducidad", estado: "disponible" }),
      ]);
      setProductos(prodResp.data.results || prodResp.data || []);
      setCentros(centroResp.data.results || centroResp.data || []);
      const lotesData = lotesResp.data.results || lotesResp.data || [];
      setLotes(lotesData);
      setLotesDisponibles(lotesData.filter(l => l.cantidad_actual > 0));
    } catch (err) {
      console.warn("No se pudieron cargar catálogos", err.message);
    }
  };

  const calcularStats = (data) => {
    let entradas = 0;
    let salidas = 0;
    data.forEach((m) => {
      if (m.tipo === "entrada") entradas += Math.abs(Number(m.cantidad || 0));
      if (m.tipo === "salida") salidas += Math.abs(Number(m.cantidad || 0));
      if (m.tipo === "ajuste") {
        if (Number(m.cantidad) > 0) entradas += Number(m.cantidad);
        else salidas += Math.abs(Number(m.cantidad));
      }
    });
    setStats({ entradas, salidas, balance: entradas - salidas });
  };

  const cargarMovimientos = async () => {
    setLoading(true);
    try {
      const params = {
        page,
        page_size: PAGE_SIZE,
        ordering: "-fecha",
        ...filtros,
      };
      const response = await movimientosAPI.getAll(params);
      const data = response.data?.results || response.data || [];
      setMovimientos(Array.isArray(data) ? data : []);
      setTotal(response.data?.count || data.length || 0);
      calcularStats(Array.isArray(data) ? data : []);
    } catch (err) {
      toast.error(err.response?.data?.detail || "No se pudieron cargar los movimientos");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarCatalogos();
  }, []);

  useEffect(() => {
    cargarMovimientos();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, filtros]);

  // Scroll al movimiento resaltado cuando viene del dashboard
  useEffect(() => {
    if (highlightId && highlightRef.current && !loading) {
      setTimeout(() => {
        highlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 300);
    }
  }, [highlightId, loading, movimientos]);

  // Filtrar lotes cuando cambia el producto
  useEffect(() => {
    if (productoFiltro) {
      const lotesFiltrados = lotes.filter(
        l => l.producto === parseInt(productoFiltro) && l.cantidad_actual > 0
      );
      setLotesDisponibles(lotesFiltrados);
      setFormData(prev => ({ ...prev, lote: "" }));
    } else {
      setLotesDisponibles(lotes.filter(l => l.cantidad_actual > 0));
    }
  }, [productoFiltro, lotes]);

  const handleFormChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const getLoteLabel = (lote) => {
    const producto = productos.find(p => p.id === lote.producto);
    const fechaCad = lote.fecha_caducidad ? new Date(lote.fecha_caducidad).toLocaleDateString() : 'S/F';
    return `${lote.numero_lote} - ${producto?.descripcion?.substring(0, 25) || 'Producto'} (${lote.cantidad_actual} uds, Cad: ${fechaCad})`;
  };

  const registrarMovimiento = async () => {
    if (!formData.lote) {
      toast.error("Selecciona un lote");
      return;
    }
    if (!formData.cantidad || Number(formData.cantidad) <= 0) {
      toast.error("Ingresa una cantidad válida mayor a 0");
      return;
    }

    const loteSeleccionado = lotes.find(l => l.id === parseInt(formData.lote));
    if (formData.tipo === "salida" && loteSeleccionado && Number(formData.cantidad) > loteSeleccionado.cantidad_actual) {
      toast.error(`Inventario insuficiente. Disponible: ${loteSeleccionado.cantidad_actual}`);
      return;
    }

    setSubmitting(true);
    try {
      await movimientosAPI.create({
        lote: parseInt(formData.lote),
        tipo: formData.tipo,
        cantidad: Number(formData.cantidad),
        centro: formData.centro ? parseInt(formData.centro) : null,
        observaciones: formData.observaciones,
      });
      toast.success("Movimiento registrado exitosamente");
      setFormData({
        lote: "",
        tipo: "entrada",
        cantidad: "",
        centro: "",
        observaciones: "",
      });
      setProductoFiltro("");
      cargarMovimientos();
      cargarCatalogos();
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.response?.data?.mensaje || 
                       err.response?.data?.detail || err.response?.data?.cantidad?.[0] ||
                       "No se pudo registrar el movimiento";
      toast.error(errorMsg);
    } finally {
      setSubmitting(false);
    }
  };

  const exportarExcel = async () => {
    try {
      const response = await movimientosAPI.exportarExcel({ ...filtros });
      descargarArchivo(response, `movimientos_${new Date().toISOString().split("T")[0]}.xlsx`);
      toast.success("Excel generado");
    } catch (err) {
      toast.error(err.response?.data?.detail || "No se pudo exportar");
    }
  };

  const exportarPdf = async () => {
    try {
      const response = await movimientosAPI.exportarPdf({ ...filtros });
      descargarArchivo(response, `movimientos_${new Date().toISOString().split("T")[0]}.pdf`);
      toast.success("PDF generado");
    } catch (err) {
      toast.error(err.response?.data?.detail || "No se pudo generar el PDF");
    }
  };

  const handleFiltro = (field, value) => {
    setPage(1);
    setFiltros((prev) => ({ ...prev, [field]: value }));
  };

  const limpiarFiltros = () => {
    setFiltros({
      fecha_inicio: "",
      fecha_fin: "",
      tipo: "",
      producto: "",
      centro: "",
      lote: "",
      search: "",
    });
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-bold text-gray-900">Movimientos</h1>
          <p className="text-gray-600">Registra y consulta movimientos de inventario</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">Nuevo movimiento</h2>

            <div className="space-y-4">
              {/* Filtro por producto */}
              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700">Producto (filtro)</label>
                <select
                  value={productoFiltro}
                  onChange={(e) => setProductoFiltro(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">-- Todos --</option>
                  {productos.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.clave} - {p.descripcion}
                    </option>
                  ))}
                </select>
              </div>

              {/* Selección de lote */}
              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700">Lote *</label>
                <select
                  value={formData.lote}
                  onChange={(e) => handleFormChange("lote", e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="">-- Selecciona un lote --</option>
                  {lotesDisponibles.map((l) => (
                    <option key={l.id} value={l.id}>
                      {getLoteLabel(l)}
                    </option>
                  ))}
                </select>
                {lotesDisponibles.length === 0 && (
                  <p className="text-xs text-orange-600">No hay lotes disponibles</p>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700">Tipo *</label>
                <select
                  value={formData.tipo}
                  onChange={(e) => handleFormChange("tipo", e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="entrada">Entrada</option>
                  <option value="salida">Salida</option>
                  <option value="ajuste">Ajuste</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700">Cantidad *</label>
                <input
                  type="number"
                  min="1"
                  value={formData.cantidad}
                  onChange={(e) => handleFormChange("cantidad", e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Cantidad"
                />
              </div>

              {/* Centro opcional */}
              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700">Centro</label>
                <select
                  value={formData.centro}
                  onChange={(e) => handleFormChange("centro", e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">-- Sin centro --</option>
                  {centros.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nombre}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700">Observaciones</label>
                <textarea
                  value={formData.observaciones}
                  onChange={(e) => handleFormChange("observaciones", e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Notas adicionales..."
                  rows={2}
                />
              </div>

              <button
                onClick={registrarMovimiento}
                disabled={submitting}
                className="w-full px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 transition disabled:opacity-50"
              >
                {submitting ? "Registrando..." : "Registrar movimiento"}
              </button>
            </div>
          </div>

          <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200 flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-800">Movimientos</h3>
                <div className="flex gap-2">
                  <button
                    onClick={exportarPdf}
                    className="text-sm px-3 py-1 rounded bg-red-600 text-white hover:bg-red-700"
                    disabled={loading}
                  >
                    Exportar PDF
                  </button>
                  <button
                    onClick={exportarExcel}
                    className="text-sm px-3 py-1 rounded bg-green-600 text-white hover:bg-green-700"
                    disabled={loading}
                  >
                    Exportar Excel
                  </button>
                  <button
                    onClick={cargarMovimientos}
                    className="text-sm text-blue-600 hover:text-blue-800"
                    disabled={loading}
                  >
                    Recargar
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-gray-700">Fecha inicio</label>
                  <input
                    type="date"
                    value={filtros.fecha_inicio}
                    onChange={(e) => handleFiltro("fecha_inicio", e.target.value)}
                    className="border rounded-lg px-3 py-2"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-gray-700">Fecha fin</label>
                  <input
                    type="date"
                    value={filtros.fecha_fin}
                    onChange={(e) => handleFiltro("fecha_fin", e.target.value)}
                    className="border rounded-lg px-3 py-2"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-gray-700">Tipo</label>
                  <select
                    value={filtros.tipo}
                    onChange={(e) => handleFiltro("tipo", e.target.value)}
                    className="border rounded-lg px-3 py-2"
                  >
                    <option value="">Todos</option>
                    <option value="entrada">Entrada</option>
                    <option value="salida">Salida</option>
                    <option value="ajuste">Ajuste</option>
                  </select>
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-gray-700">Producto</label>
                  <select
                    value={filtros.producto}
                    onChange={(e) => handleFiltro("producto", e.target.value)}
                    className="border rounded-lg px-3 py-2"
                  >
                    <option value="">Todos</option>
                    {productos.slice(0, 50).map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.clave} - {p.descripcion}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-gray-700">Centro</label>
                  <select
                    value={filtros.centro}
                    onChange={(e) => handleFiltro("centro", e.target.value)}
                    className="border rounded-lg px-3 py-2"
                  >
                    <option value="">Todos</option>
                    {centros.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nombre}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-gray-700">Lote</label>
                  <input
                    type="text"
                    value={filtros.lote}
                    onChange={(e) => handleFiltro("lote", e.target.value)}
                    className="border rounded-lg px-3 py-2"
                    placeholder="Número de lote"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-gray-700">Buscar</label>
                  <input
                    type="text"
                    value={filtros.search}
                    onChange={(e) => handleFiltro("search", e.target.value)}
                    className="border rounded-lg px-3 py-2"
                    placeholder="Producto o documento"
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => cargarMovimientos()}
                  className="px-3 py-2 rounded bg-blue-600 text-white text-sm hover:bg-blue-700"
                  disabled={loading}
                >
                  Aplicar filtros
                </button>
                <button
                  onClick={limpiarFiltros}
                  className="px-3 py-2 rounded bg-gray-200 text-sm hover:bg-gray-300"
                  disabled={loading}
                >
                  Limpiar
                </button>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-100 border-b border-gray-200">
                  <tr>
                    {columnas.map((col) => (
                      <th key={col} className="px-4 py-3 text-left font-semibold">
                        {col.toUpperCase()}
                      </th>
                    ))}
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                      Acciones
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {!movimientos.length ? (
                    <tr>
                      <td colSpan={columnas.length + 1} className="px-4 py-6 text-center text-gray-500">
                        {loading ? "Cargando..." : "Sin movimientos"}
                      </td>
                    </tr>
                  ) : (
                    movimientos.map((mov) => (
                      <>
                        <tr 
                          key={mov.id} 
                          ref={highlightId === mov.id ? highlightRef : null}
                          className={`border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors ${
                            highlightId === mov.id ? 'bg-yellow-50 ring-2 ring-yellow-400' : ''
                          } ${expandedId === mov.id ? 'bg-blue-50' : ''}`}
                          onClick={() => setExpandedId(expandedId === mov.id ? null : mov.id)}
                        >
                          <td className="px-4 py-3 text-gray-800">
                            <div className="font-medium">{mov.producto_descripcion || mov.producto_nombre || mov.producto || ""}</div>
                            <div className="text-xs text-gray-500">Lote: {mov.lote_codigo || mov.numero_lote || 'N/A'}</div>
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`px-2 py-1 rounded text-xs font-semibold ${
                                mov.tipo === "entrada"
                                  ? "bg-green-100 text-green-800"
                                  : mov.tipo === "salida"
                                  ? "bg-red-100 text-red-800"
                                  : "bg-yellow-100 text-yellow-800"
                              }`}
                            >
                              {mov.tipo?.toUpperCase()}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right font-semibold text-gray-900">
                            {mov.tipo === 'salida' ? '-' : '+'}{Math.abs(mov.cantidad)}
                          </td>
                          <td className="px-4 py-3 text-gray-700">{mov.centro_nombre || mov.centro || "Farmacia Central"}</td>
                          <td className="px-4 py-3 text-gray-600">
                            {mov.fecha_movimiento
                              ? new Date(mov.fecha_movimiento).toLocaleString('es-MX')
                              : mov.fecha
                              ? new Date(mov.fecha).toLocaleString('es-MX')
                              : ""}
                          </td>
                          <td className="px-4 py-3">
                            <button 
                              className="text-blue-600 hover:text-blue-800 text-sm"
                              onClick={(e) => { e.stopPropagation(); setExpandedId(expandedId === mov.id ? null : mov.id); }}
                            >
                              {expandedId === mov.id ? '▲ Ocultar' : '▼ Detalles'}
                            </button>
                          </td>
                        </tr>
                        {/* Fila expandida con detalles */}
                        {expandedId === mov.id && (
                          <tr key={`${mov.id}-detail`} className="bg-gray-50">
                            <td colSpan={columnas.length + 1} className="px-6 py-4">
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                <div>
                                  <span className="font-semibold text-gray-600">ID Movimiento:</span>
                                  <p className="text-gray-800">{mov.id}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-gray-600">Producto:</span>
                                  <p className="text-gray-800">{mov.producto_clave || 'N/A'} - {mov.producto_descripcion || mov.producto_nombre || ''}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-gray-600">Lote:</span>
                                  <p className="text-gray-800">{mov.lote_codigo || mov.numero_lote || 'N/A'}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-gray-600">Centro:</span>
                                  <p className="text-gray-800">{mov.centro_nombre || 'Farmacia Central'}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-gray-600">Usuario:</span>
                                  <p className="text-gray-800">{mov.usuario_nombre || mov.usuario || 'Sistema'}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-gray-600">Requisición:</span>
                                  <p className="text-gray-800">{mov.requisicion_folio || 'N/A'}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-gray-600">Fecha exacta:</span>
                                  <p className="text-gray-800">{mov.fecha_movimiento || mov.fecha ? new Date(mov.fecha_movimiento || mov.fecha).toLocaleString('es-MX', { dateStyle: 'full', timeStyle: 'medium' }) : ''}</p>
                                </div>
                                {mov.observaciones && (
                                  <div className="col-span-2 md:col-span-4">
                                    <span className="font-semibold text-gray-600">Observaciones:</span>
                                    <p className="text-gray-800 bg-white p-2 rounded border mt-1">{mov.observaciones}</p>
                                  </div>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            <div className="px-6 py-4 border-t border-gray-200 text-sm text-gray-700 flex flex-wrap gap-4">
              <span>
                <strong>Entradas:</strong> +{stats.entradas}
              </span>
              <span>
                <strong>Salidas:</strong> -{stats.salidas}
              </span>
              <span className={stats.balance >= 0 ? "text-green-600" : "text-red-600"}>
                <strong>Balance:</strong> {stats.balance >= 0 ? "+" : ""}{stats.balance}
              </span>
            </div>
          </div>
        </div>

        {total > 0 && (
          <div className="mt-6">
            <Pagination
              page={page}
              totalPages={Math.max(1, Math.ceil(total / PAGE_SIZE))}
              totalItems={total}
              pageSize={PAGE_SIZE}
              onPageChange={setPage}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default Movimientos;
