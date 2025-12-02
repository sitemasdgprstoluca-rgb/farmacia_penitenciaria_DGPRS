import { useEffect, useMemo, useState } from "react";
import { toast } from "react-hot-toast";
import { 
  FaChartBar, 
  FaFileExcel,
  FaFilePdf, 
  FaFilter, 
  FaSync, 
  FaBox, 
  FaClock, 
  FaClipboardList,
  FaExclamationTriangle,
  FaTimesCircle,
  FaDatabase
} from "react-icons/fa";
import { reportesAPI, centrosAPI, descargarArchivo } from "../services/api";
import PageHeader from "../components/PageHeader";

const COLORS = {
  vino: '#9F2241',
  vinoOscuro: '#6B1839',
};

const baseFilters = {
  tipo: "inventario",
  estado: "",
  dias: 30,
  fechaInicio: "",
  fechaFin: "",
  centro: "",
  nivelStock: "",
};

// Configuración de columnas por tipo de reporte
const COLUMNAS_CONFIG = {
  inventario: [
    { key: '#', label: '#', width: '60px' },
    { key: 'clave', label: 'Clave', width: '120px' },
    { key: 'descripcion', label: 'Descripción', width: '250px' },
    { key: 'unidad_medida', label: 'Unidad', width: '100px' },
    { key: 'stock_minimo', label: 'Inv. Mín.', width: '100px', align: 'right' },
    { key: 'stock_actual', label: 'Inv. Actual', width: '100px', align: 'right' },
    { key: 'lotes_activos', label: 'Lotes', width: '80px', align: 'center' },
    { key: 'nivel_stock', label: 'Nivel', width: '100px', align: 'center' },
    { key: 'precio_unitario', label: 'Precio', width: '100px', align: 'right' },
  ],
  caducidades: [
    { key: 'producto', label: 'Producto', width: '300px' },
    { key: 'lote', label: 'Lote', width: '120px' },
    { key: 'caducidad', label: 'Caducidad', width: '120px' },
    { key: 'dias_restantes', label: 'Días Rest.', width: '100px', align: 'right' },
    { key: 'stock', label: 'Inventario', width: '80px', align: 'right' },
    { key: 'estado', label: 'Estado', width: '100px', align: 'center' },
  ],
  requisiciones: [
    { key: 'id', label: 'ID', width: '60px' },
    { key: 'folio', label: 'Folio', width: '140px' },
    { key: 'centro', label: 'Centro', width: '200px' },
    { key: 'estado', label: 'Estado', width: '120px', align: 'center' },
    { key: 'fecha_solicitud', label: 'Fecha', width: '150px' },
    { key: 'total_productos', label: 'Productos', width: '100px', align: 'center' },
    { key: 'solicitante', label: 'Solicitante', width: '150px' },
  ],
};

const getNivelColor = (nivel) => {
  const n = (nivel || '').toLowerCase();
  if (n === 'critico' || n === 'sin_stock') return { bg: '#FEE2E2', text: '#991B1B' };
  if (n === 'bajo') return { bg: '#FEF3C7', text: '#92400E' };
  if (n === 'alto' || n === 'suficiente') return { bg: '#D1FAE5', text: '#065F46' };
  return { bg: '#F3F4F6', text: '#374151' };
};

const getEstadoColor = (estado) => {
  const e = (estado || '').toLowerCase();
  if (e === 'vencido') return { bg: '#FEE2E2', text: '#991B1B' };
  if (e === 'critico') return { bg: '#FFEDD5', text: '#9A3412' };
  if (e === 'proximo') return { bg: '#FEF3C7', text: '#92400E' };
  if (e === 'borrador') return { bg: '#E5E7EB', text: '#374151' };
  if (e === 'enviada') return { bg: '#DBEAFE', text: '#1E40AF' };
  if (e === 'autorizada') return { bg: '#D1FAE5', text: '#065F46' };
  if (e === 'rechazada') return { bg: '#FEE2E2', text: '#991B1B' };
  if (e === 'surtida') return { bg: '#D1FAE5', text: '#065F46' };
  return { bg: '#F3F4F6', text: '#374151' };
};

const formatValue = (value, key) => {
  if (value === null || value === undefined) return '-';
  
  if (key === 'fecha_solicitud' || key === 'caducidad') {
    try {
      const date = new Date(value);
      return date.toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
      return value;
    }
  }
  
  if (key === 'precio_unitario') {
    return `$${parseFloat(value).toFixed(2)}`;
  }
  
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  
  return value;
};

const Reportes = () => {
  const [filtros, setFiltros] = useState(baseFilters);
  const [datos, setDatos] = useState([]);
  const [preview, setPreview] = useState([]);
  const [resumen, setResumen] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");
  const [centros, setCentros] = useState([]);

  const columnas = useMemo(() => {
    return COLUMNAS_CONFIG[filtros.tipo] || [];
  }, [filtros.tipo]);

  const cargarCatalogos = async () => {
    try {
      const centrosResp = await centrosAPI.getAll({ page_size: 100, ordering: "nombre" });
      setCentros(centrosResp.data.results || centrosResp.data || []);
    } catch (err) {
      console.warn("No se pudieron cargar catálogos", err.message);
    }
  };

  const buildParams = () => {
    const params = {};
    if (filtros.estado) params.estado = filtros.estado;
    if (filtros.fechaInicio) params.fecha_inicio = filtros.fechaInicio;
    if (filtros.fechaFin) params.fecha_fin = filtros.fechaFin;
    if (filtros.centro) params.centro = filtros.centro;
    if (filtros.nivelStock) params.nivel_stock = filtros.nivelStock;
    if (filtros.tipo === "caducidades") params.dias = filtros.dias || 30;
    return params;
  };

  const cargarReporte = async () => {
    setLoading(true);
    setError("");
    setDatos([]);
    setPreview([]);
    setResumen(null);

    try {
      let response;
      const params = buildParams();
      
      if (filtros.tipo === "inventario") {
        response = await reportesAPI.inventario(params);
      } else if (filtros.tipo === "caducidades") {
        response = await reportesAPI.caducidades(params);
      } else if (filtros.tipo === "requisiciones") {
        response = await reportesAPI.requisiciones(params);
      } else {
        throw new Error("Tipo de reporte no soportado");
      }

      const payload = response.data || {};
      const datosFull = payload.datos || [];
      
      if (!Array.isArray(datosFull)) {
        console.warn('Datos no es un array:', datosFull);
        setDatos([]);
        setPreview([]);
      } else {
        setDatos(datosFull);
        setPreview(datosFull.slice(0, 50));
      }
      
      setResumen(payload.resumen || null);
      
      if (datosFull.length === 0) {
        toast('No se encontraron registros con los filtros aplicados', { icon: 'ℹ️' });
      }
    } catch (err) {
      console.error('Error al cargar reporte:', err);
      const msg = err.response?.data?.detail || err.response?.data?.error || err.message || "Error al cargar reporte";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarCatalogos();
  }, []);

  useEffect(() => {
    cargarReporte();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtros.tipo]);

  const exportarExcel = async () => {
    setExporting(true);
    const toastId = toast.loading("Generando archivo Excel...");
    try {
      const params = { ...buildParams(), formato: 'excel' };
      let response;
      let filename;
      
      if (filtros.tipo === "inventario") {
        response = await reportesAPI.exportarInventarioExcel(params);
        filename = `inventario_${new Date().toISOString().split("T")[0]}.xlsx`;
      } else if (filtros.tipo === "caducidades") {
        response = await reportesAPI.exportarCaducidadesExcel(params);
        filename = `caducidades_${new Date().toISOString().split("T")[0]}.xlsx`;
      } else if (filtros.tipo === "requisiciones") {
        response = await reportesAPI.exportarRequisicionesExcel(params);
        filename = `requisiciones_${new Date().toISOString().split("T")[0]}.xlsx`;
      } else {
        toast.error("Tipo de reporte no soportado", { id: toastId });
        return;
      }
      
      descargarArchivo(response, filename);
      toast.success(`✅ ${filename} descargado`, { id: toastId });
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Error al exportar";
      toast.error(`❌ ${msg}`, { id: toastId });
    } finally {
      setExporting(false);
    }
  };

  const exportarPDF = async () => {
    setExporting(true);
    const toastId = toast.loading("Generando archivo PDF...");
    try {
      const params = { ...buildParams(), formato: 'pdf' };
      let response;
      let filename;
      
      if (filtros.tipo === "inventario") {
        response = await reportesAPI.exportarInventarioPDF(params);
        filename = `reporte_inventario_${new Date().toISOString().split("T")[0]}.pdf`;
      } else if (filtros.tipo === "caducidades") {
        response = await reportesAPI.exportarCaducidadesPDF(params);
        filename = `reporte_caducidades_${new Date().toISOString().split("T")[0]}.pdf`;
      } else if (filtros.tipo === "requisiciones") {
        response = await reportesAPI.exportarRequisicionesPDF(params);
        filename = `reporte_requisiciones_${new Date().toISOString().split("T")[0]}.pdf`;
      } else {
        toast.error("Tipo de reporte no soportado para PDF", { id: toastId });
        return;
      }
      
      descargarArchivo(response, filename);
      toast.success(`✅ ${filename} descargado`, { id: toastId });
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Error al exportar PDF";
      toast.error(`❌ ${msg}`, { id: toastId });
    } finally {
      setExporting(false);
    }
  };

  const handleFiltro = (name, value) => {
    setFiltros((prev) => ({ ...prev, [name]: value }));
  };

  const limpiarFiltros = () => {
    setFiltros(baseFilters);
  };

  const getTipoIcon = () => {
    if (filtros.tipo === 'inventario') return <FaBox />;
    if (filtros.tipo === 'caducidades') return <FaClock />;
    if (filtros.tipo === 'requisiciones') return <FaClipboardList />;
    return <FaChartBar />;
  };

  const renderCellValue = (fila, col) => {
    const value = fila[col.key];
    const formatted = formatValue(value, col.key);
    
    if (col.key === 'nivel' || col.key === 'nivel_stock') {
      const colors = getNivelColor(value);
      return (
        <span 
          className="px-2 py-1 rounded-full text-xs font-bold"
          style={{ backgroundColor: colors.bg, color: colors.text }}
        >
          {formatted}
        </span>
      );
    }
    
    if (col.key === 'estado') {
      const colors = getEstadoColor(value);
      return (
        <span 
          className="px-2 py-1 rounded-full text-xs font-bold"
          style={{ backgroundColor: colors.bg, color: colors.text }}
        >
          {(formatted || '').toUpperCase()}
        </span>
      );
    }
    
    return formatted;
  };

  const renderResumen = () => {
    if (!resumen) return null;

    if (filtros.tipo === 'inventario') {
      return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-gradient-to-r from-gray-50 to-white border-t">
          <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
            <FaBox className="text-2xl text-blue-600" />
            <div>
              <p className="text-xs text-blue-600 font-semibold">Total Productos</p>
              <p className="text-xl font-bold text-blue-800">{resumen.total_productos || 0}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
            <FaDatabase className="text-2xl text-green-600" />
            <div>
              <p className="text-xs text-green-600 font-semibold">Inventario Total</p>
              <p className="text-xl font-bold text-green-800">{(resumen.stock_total || 0).toLocaleString()}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-red-50 rounded-lg">
            <FaExclamationTriangle className="text-2xl text-red-600" />
            <div>
              <p className="text-xs text-red-600 font-semibold">Bajo Inventario Mínimo</p>
              <p className="text-xl font-bold text-red-800">{resumen.productos_bajo_minimo || 0}</p>
            </div>
          </div>
        </div>
      );
    }

    if (filtros.tipo === 'caducidades') {
      return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-gradient-to-r from-gray-50 to-white border-t">
          <div className="flex items-center gap-3 p-3 bg-yellow-50 rounded-lg">
            <FaClock className="text-2xl text-yellow-600" />
            <div>
              <p className="text-xs text-yellow-600 font-semibold">Total Lotes por Caducar</p>
              <p className="text-xl font-bold text-yellow-800">{resumen.total_lotes || datos.length}</p>
            </div>
          </div>
        </div>
      );
    }

    if (filtros.tipo === 'requisiciones') {
      const porEstado = resumen.por_estado || {};
      return (
        <div className="p-4 bg-gradient-to-r from-gray-50 to-white border-t">
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
            <div className="flex items-center gap-2 p-2 bg-gray-100 rounded-lg">
              <span className="text-lg font-bold text-gray-700">{resumen.total || datos.length}</span>
              <span className="text-xs text-gray-500">Total</span>
            </div>
            {Object.entries(porEstado).map(([estado, count]) => {
              const colors = getEstadoColor(estado);
              return (
                <div 
                  key={estado} 
                  className="flex items-center gap-2 p-2 rounded-lg"
                  style={{ backgroundColor: colors.bg }}
                >
                  <span className="text-lg font-bold" style={{ color: colors.text }}>{count}</span>
                  <span className="text-xs capitalize" style={{ color: colors.text }}>{estado}</span>
                </div>
              );
            })}
          </div>
        </div>
      );
    }

    return null;
  };

  const badgeContent = (
    <span className="flex items-center gap-2 rounded-full bg-white/20 px-4 py-1 text-sm font-semibold">
      <FaDatabase />
      {datos.length} registros
    </span>
  );

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        icon={FaChartBar}
        title="Reportes"
        subtitle="Consulta y exporta información clave del inventario"
        badge={badgeContent}
      />

      {/* Panel de Filtros */}
      <div className="bg-white rounded-xl shadow-lg p-6 border-l-4" style={{ borderLeftColor: COLORS.vino }}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold flex items-center gap-2" style={{ color: COLORS.vinoOscuro }}>
            <FaFilter />
            Filtros de Reporte
          </h3>
          <div className="flex items-center gap-2">
            {getTipoIcon()}
            <span className="text-sm font-semibold capitalize">{filtros.tipo}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          {/* Tipo de reporte */}
          <div className="space-y-1">
            <label className="text-sm font-semibold text-gray-700">Tipo de reporte</label>
            <select
              value={filtros.tipo}
              onChange={(e) => handleFiltro("tipo", e.target.value)}
              className="w-full rounded-lg border-2 border-gray-200 px-3 py-2.5 focus:outline-none focus:border-rose-500 transition-colors"
            >
              <option value="inventario">📦 Inventario</option>
              <option value="caducidades">⏰ Caducidades</option>
              <option value="requisiciones">📋 Requisiciones</option>
            </select>
          </div>

          {/* Filtros específicos por tipo */}
          {filtros.tipo === "caducidades" && (
            <>
              <div className="space-y-1">
                <label className="text-sm font-semibold text-gray-700">Días próximos</label>
                <input
                  type="number"
                  min="1"
                  max="365"
                  value={filtros.dias}
                  onChange={(e) => handleFiltro("dias", Number(e.target.value) || 30)}
                  className="w-full rounded-lg border-2 border-gray-200 px-3 py-2.5 focus:outline-none focus:border-rose-500 transition-colors"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-semibold text-gray-700">Centro</label>
                <select
                  value={filtros.centro}
                  onChange={(e) => handleFiltro("centro", e.target.value)}
                  className="w-full rounded-lg border-2 border-gray-200 px-3 py-2.5 focus:outline-none focus:border-rose-500 transition-colors"
                >
                  <option value="">Todos los centros</option>
                  <option value="central">🏥 Farmacia Central</option>
                  {centros.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nombre}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-semibold text-gray-700">Estado caducidad</label>
                <select
                  value={filtros.estado}
                  onChange={(e) => handleFiltro("estado", e.target.value)}
                  className="w-full rounded-lg border-2 border-gray-200 px-3 py-2.5 focus:outline-none focus:border-rose-500 transition-colors"
                >
                  <option value="">Todos los estados</option>
                  <option value="vencido">🔴 Vencido</option>
                  <option value="critico">🟠 Crítico (≤7 días)</option>
                  <option value="proximo">🟡 Próximo a vencer</option>
                </select>
              </div>
            </>
          )}

          {filtros.tipo === "requisiciones" && (
            <>
              <div className="space-y-1">
                <label className="text-sm font-semibold text-gray-700">Estado</label>
                <select
                  value={filtros.estado}
                  onChange={(e) => handleFiltro("estado", e.target.value)}
                  className="w-full rounded-lg border-2 border-gray-200 px-3 py-2.5 focus:outline-none focus:border-rose-500 transition-colors"
                >
                  <option value="">Todos los estados</option>
                  <option value="borrador">📝 Borrador</option>
                  <option value="enviada">📤 Enviada</option>
                  <option value="autorizada">✅ Autorizada</option>
                  <option value="rechazada">❌ Rechazada</option>
                  <option value="surtida">✔️ Surtida</option>
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-semibold text-gray-700">Centro</label>
                <select
                  value={filtros.centro}
                  onChange={(e) => handleFiltro("centro", e.target.value)}
                  className="w-full rounded-lg border-2 border-gray-200 px-3 py-2.5 focus:outline-none focus:border-rose-500 transition-colors"
                >
                  <option value="">Todos los centros</option>
                  {centros.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nombre}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-semibold text-gray-700">Desde</label>
                <input
                  type="date"
                  value={filtros.fechaInicio}
                  onChange={(e) => handleFiltro("fechaInicio", e.target.value)}
                  className="w-full rounded-lg border-2 border-gray-200 px-3 py-2.5 focus:outline-none focus:border-rose-500 transition-colors"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-semibold text-gray-700">Hasta</label>
                <input
                  type="date"
                  value={filtros.fechaFin}
                  onChange={(e) => handleFiltro("fechaFin", e.target.value)}
                  className="w-full rounded-lg border-2 border-gray-200 px-3 py-2.5 focus:outline-none focus:border-rose-500 transition-colors"
                />
              </div>
            </>
          )}

          {filtros.tipo === "inventario" && (
            <>
              <div className="space-y-1">
                <label className="text-sm font-semibold text-gray-700">Centro</label>
                <select
                  value={filtros.centro}
                  onChange={(e) => handleFiltro("centro", e.target.value)}
                  className="w-full rounded-lg border-2 border-gray-200 px-3 py-2.5 focus:outline-none focus:border-rose-500 transition-colors"
                >
                  <option value="">Todos los centros</option>
                  <option value="central">🏥 Farmacia Central</option>
                  {centros.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nombre}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-semibold text-gray-700">Nivel de inventario</label>
                <select
                  value={filtros.nivelStock}
                  onChange={(e) => handleFiltro("nivelStock", e.target.value)}
                  className="w-full rounded-lg border-2 border-gray-200 px-3 py-2.5 focus:outline-none focus:border-rose-500 transition-colors"
                >
                  <option value="">Todos los niveles</option>
                  <option value="critico">🔴 Crítico</option>
                  <option value="bajo">🟡 Bajo</option>
                  <option value="alto">🟢 Alto</option>
                  <option value="sin_stock">⚪ Sin Inventario</option>
                </select>
              </div>
            </>
          )}
        </div>

        {/* Botones de acción */}
        <div className="flex flex-wrap gap-3">
          <button
            onClick={cargarReporte}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-white font-semibold transition-all hover:scale-105 disabled:opacity-60"
            style={{ background: `linear-gradient(135deg, ${COLORS.vino} 0%, ${COLORS.vinoOscuro} 100%)` }}
          >
            {loading ? (
              <>
                <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                Cargando...
              </>
            ) : (
              <>
                <FaSync />
                Aplicar Filtros
              </>
            )}
          </button>
          <button
            onClick={limpiarFiltros}
            disabled={loading}
            className="px-4 py-2.5 rounded-lg bg-gray-200 text-gray-700 font-semibold hover:bg-gray-300 transition disabled:opacity-60"
          >
            Limpiar
          </button>
          <button
            onClick={exportarExcel}
            disabled={loading || exporting || datos.length === 0}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-green-600 text-white font-semibold hover:bg-green-700 transition disabled:opacity-60"
          >
            {exporting ? (
              <>
                <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                Exportando...
              </>
            ) : (
              <>
                <FaFileExcel />
                Exportar Excel
              </>
            )}
          </button>
          <button
            onClick={exportarPDF}
            disabled={loading || exporting || datos.length === 0}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-white font-semibold hover:opacity-90 transition disabled:opacity-60"
            style={{ background: 'linear-gradient(135deg, #DC2626 0%, #991B1B 100%)' }}
          >
            {exporting ? (
              <>
                <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                Exportando...
              </>
            ) : (
              <>
                <FaFilePdf />
                Exportar PDF
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm flex items-center gap-2">
            <FaTimesCircle />
            {error}
          </div>
        )}
      </div>

      {/* Tabla de Datos */}
      <div className="bg-white rounded-xl shadow-lg overflow-hidden border-l-4" style={{ borderLeftColor: COLORS.vino }}>
        <div className="p-4 border-b border-gray-200 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
          <div>
            <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
              {getTipoIcon()}
              Reporte de {filtros.tipo.charAt(0).toUpperCase() + filtros.tipo.slice(1)}
            </h3>
            <p className="text-sm text-gray-500">
              Mostrando {preview.length} de {datos.length} registros
            </p>
          </div>
        </div>

        {/* Resumen */}
        {renderResumen()}

        {/* Tabla */}
        <div className="overflow-x-auto">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="text-center">
                <div className="animate-spin rounded-full h-16 w-16 border-4 border-t-transparent mx-auto mb-4" style={{ borderColor: '#9F224133', borderTopColor: '#9F2241' }}></div>
                <p className="text-gray-600 font-semibold">Cargando reporte...</p>
              </div>
            </div>
          ) : preview.length === 0 ? (
            <div className="text-center py-20">
              <FaChartBar className="mx-auto text-6xl text-gray-300 mb-4" />
              <p className="text-xl font-semibold text-gray-600">No hay datos para mostrar</p>
              <p className="text-gray-500 mt-2">Intenta ajustar los filtros o selecciona otro tipo de reporte</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead style={{ background: `linear-gradient(135deg, ${COLORS.vino} 0%, ${COLORS.vinoOscuro} 100%)` }}>
                <tr>
                  {columnas.map((col) => (
                    <th 
                      key={col.key} 
                      className="px-4 py-3 text-xs font-bold text-white uppercase tracking-wider"
                      style={{ 
                        width: col.width,
                        textAlign: col.align || 'left'
                      }}
                    >
                      {col.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {preview.map((fila, idx) => (
                  <tr key={idx} className="hover:bg-gray-50 transition-colors">
                    {columnas.map((col) => (
                      <td 
                        key={col.key} 
                        className="px-4 py-3 text-gray-800"
                        style={{ textAlign: col.align || 'left' }}
                      >
                        {renderCellValue(fila, col)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {datos.length > 50 && (
          <div className="p-4 bg-gray-50 border-t text-center">
            <p className="text-sm text-gray-600">
              Mostrando los primeros 50 registros. Exporta a Excel para ver todos los {datos.length} registros.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Reportes;
