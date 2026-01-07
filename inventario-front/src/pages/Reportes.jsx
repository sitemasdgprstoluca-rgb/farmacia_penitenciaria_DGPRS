import React, { useEffect, useMemo, useState } from "react";
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
  FaExchangeAlt,
  FaExclamationTriangle,
  FaTimesCircle,
  FaDatabase,
  FaSpinner,
  FaLock,
  FaChevronDown,
  FaChevronRight,
  FaChevronLeft,
  FaAngleDoubleLeft,
  FaAngleDoubleRight
} from "react-icons/fa";
import { reportesAPI, centrosAPI, descargarArchivo } from "../services/api";
import PageHeader from "../components/PageHeader";
import { usePermissions } from '../hooks/usePermissions';

// Los colores ahora se leen del tema CSS - esto es solo para compatibilidad
const getThemeColor = (varName, fallback) => {
  return getComputedStyle(document.documentElement).getPropertyValue(varName).trim() || fallback;
};

const COLORS = {
  get vino() { return getThemeColor('--color-primary', '#9F2241'); },
  get vinoOscuro() { return getThemeColor('--color-primary-hover', '#6B1839'); },
};

// Helper para obtener el primer día del mes actual en formato YYYY-MM-DD
const getFirstDayOfMonth = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
};

// Helper para obtener la fecha actual en formato YYYY-MM-DD
const getTodayDate = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
};

const baseFilters = {
  tipo: "inventario",
  estado: "",
  dias: 30,
  fechaInicio: "",
  fechaFin: "",
  centro: "",
  nivelStock: "",
  tipoMovimiento: "",
};

// Configuración de columnas por tipo de reporte
const COLUMNAS_CONFIG = {
  inventario: [
    { key: '#', label: '#', width: '50px' },
    { key: 'clave', label: 'Clave', width: '80px' },
    { key: 'descripcion', label: 'Descripción', width: '180px' },
    { key: 'presentacion', label: 'Presentación', width: '140px' },
    { key: 'unidad_medida', label: 'Unidad', width: '70px' },
    { key: 'stock_actual', label: 'Inventario', width: '80px', align: 'right' },
    { key: 'lotes_activos', label: 'Lotes', width: '50px', align: 'center' },
    { key: 'nivel_stock', label: 'Nivel', width: '70px', align: 'center' },
    { key: 'precio_unitario', label: 'Precio', width: '80px', align: 'right' },
    { key: 'marca', label: 'Marca / Laboratorio', width: '130px' },
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
  movimientos: [
    { key: 'expand', label: '', width: '40px', align: 'center' },
    { key: 'fecha', label: 'Fecha', width: '130px' },
    { key: 'tipo', label: 'Tipo', width: '90px', align: 'center' },
    { key: 'subtipo_display', label: 'Subtipo', width: '120px', align: 'center' },
    { key: 'referencia', label: 'Referencia', width: '160px' },
    { key: 'centro_origen', label: 'Origen', width: '150px' },
    { key: 'centro_destino', label: 'Destino', width: '150px' },
    { key: 'numero_expediente', label: 'No. Exp.', width: '100px' },
    { key: 'total_productos', label: 'Prods.', width: '70px', align: 'center' },
    { key: 'total_cantidad', label: 'Cantidad', width: '80px', align: 'right' },
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
  // ISS-DB-002: Estados alineados con BD Supabase
  if (e === 'enviada') return { bg: '#DBEAFE', text: '#1E40AF' };
  if (e === 'autorizada') return { bg: '#D1FAE5', text: '#065F46' };
  if (e === 'en_surtido') return { bg: '#FFEDD5', text: '#9A3412' };
  if (e === 'parcial') return { bg: '#FEF3C7', text: '#92400E' };
  if (e === 'rechazada') return { bg: '#FEE2E2', text: '#991B1B' };
  if (e === 'surtida') return { bg: '#D1FAE5', text: '#065F46' };
  if (e === 'entregada') return { bg: '#DBEAFE', text: '#1E40AF' };
  if (e === 'cancelada') return { bg: '#E5E7EB', text: '#6B7280' };
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
  const { user, permisos, getRolPrincipal } = usePermissions();
  
  // Verificación de permisos
  const rolPrincipal = getRolPrincipal();
  const esAdmin = rolPrincipal === 'ADMIN';
  const esFarmacia = rolPrincipal === 'FARMACIA';
  const esSuperusuario = permisos?.isSuperuser;
  const esAdminOFarmacia = esAdmin || esFarmacia || esSuperusuario;
  
  // Si el usuario tiene centro asignado y no es admin/farmacia, forzar filtro por su centro
  const userCentroId = user?.centro?.id || null;
  
  const [filtros, setFiltros] = useState(baseFilters);
  const [datos, setDatos] = useState([]);
  const [resumen, setResumen] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");
  const [centros, setCentros] = useState([]);
  const [expandedRows, setExpandedRows] = useState({});  // Para expandir filas de movimientos
  
  // Paginación
  const [paginaActual, setPaginaActual] = useState(1);
  const registrosPorPagina = 25;
  
  // Calcular datos paginados
  const totalPaginas = Math.ceil(datos.length / registrosPorPagina);
  const indiceInicio = (paginaActual - 1) * registrosPorPagina;
  const indiceFin = indiceInicio + registrosPorPagina;
  const datosPaginados = datos.slice(indiceInicio, indiceFin);

  // Toggle para expandir/colapsar fila de transacción
  const toggleRowExpansion = (referencia) => {
    setExpandedRows(prev => ({
      ...prev,
      [referencia]: !prev[referencia]
    }));
  };

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
    
    // Aplicar filtro de centro: usuarios no admin/farmacia forzados a su centro
    if (!esAdminOFarmacia && userCentroId) {
      params.centro = userCentroId;
    } else if (filtros.centro && filtros.centro !== '') {
      // Centro específico seleccionado (ID numérico o 'central')
      params.centro = filtros.centro;
    } else {
      // Sin selección = ver todos los centros
      params.centro = 'todos';
    }
    
    // Parámetros específicos por tipo de reporte
    if (filtros.tipo === "inventario") {
      if (filtros.nivelStock) params.nivel_stock = filtros.nivelStock;
    } else if (filtros.tipo === "caducidades") {
      params.dias = filtros.dias || 30;
      if (filtros.estado) params.estado = filtros.estado;
    } else if (filtros.tipo === "requisiciones") {
      if (filtros.estado) params.estado = filtros.estado;
      if (filtros.fechaInicio) params.fecha_inicio = filtros.fechaInicio;
      if (filtros.fechaFin) params.fecha_fin = filtros.fechaFin;
    } else if (filtros.tipo === "movimientos") {
      if (filtros.tipoMovimiento) params.tipo = filtros.tipoMovimiento;
      if (filtros.fechaInicio) params.fecha_inicio = filtros.fechaInicio;
      if (filtros.fechaFin) params.fecha_fin = filtros.fechaFin;
    }
    
    return params;
  };

  const cargarReporte = async () => {
    setLoading(true);
    setError("");
    setDatos([]);
    setPaginaActual(1);
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
      } else if (filtros.tipo === "movimientos") {
        response = await reportesAPI.movimientos(params);
      } else {
        throw new Error("Tipo de reporte no soportado");
      }

      const payload = response.data || {};
      const datosFull = payload.datos || [];
      
      if (!Array.isArray(datosFull)) {
        console.warn('Datos no es un array:', datosFull);
        setDatos([]);
      } else {
        setDatos(datosFull);
        setPaginaActual(1);  // Reset a página 1
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

  // Cuando cambia el tipo de reporte, resetear fechas según el tipo (sin cargar automáticamente)
  const handleTipoChange = (nuevoTipo) => {
    let nuevosFiltros = { ...filtros, tipo: nuevoTipo };
    
    // Para movimientos, establecer fechas del mes actual por defecto
    if (nuevoTipo === "movimientos") {
      nuevosFiltros.fechaInicio = getFirstDayOfMonth();
      nuevosFiltros.fechaFin = getTodayDate();
    } else {
      // Para otros tipos, limpiar fechas
      nuevosFiltros.fechaInicio = "";
      nuevosFiltros.fechaFin = "";
    }
    
    setFiltros(nuevosFiltros);
    // No cargar automáticamente - el usuario debe dar clic en "Aplicar Filtros"
  };

  // Función para aplicar filtros manualmente (botón)
  const aplicarFiltros = () => {
    cargarReporte();
  };

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
      } else if (filtros.tipo === "movimientos") {
        response = await reportesAPI.exportarMovimientosExcel(params);
        filename = `movimientos_${new Date().toISOString().split("T")[0]}.xlsx`;
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
      } else if (filtros.tipo === "movimientos") {
        response = await reportesAPI.exportarMovimientosPDF(params);
        filename = `reporte_movimientos_${new Date().toISOString().split("T")[0]}.pdf`;
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
    // Limpiar todos los datos del reporte
    setDatos([]);
    setPaginaActual(1);
    setResumen(null);
    setError("");
  };

  const getTipoIcon = () => {
    if (filtros.tipo === 'inventario') return <FaBox />;
    if (filtros.tipo === 'caducidades') return <FaClock />;
    if (filtros.tipo === 'requisiciones') return <FaClipboardList />;
    if (filtros.tipo === 'movimientos') return <FaExchangeAlt />;
    return <FaChartBar />;
  };

  const renderCellValue = (fila, col, idx) => {
    // FIX: Manejar columna # (índice de fila)
    if (col.key === '#') {
      return idx + 1;
    }
    
    // Columna de expansión para movimientos agrupados
    if (col.key === 'expand' && filtros.tipo === 'movimientos') {
      const isExpanded = expandedRows[fila.referencia];
      return (
        <button
          onClick={() => toggleRowExpansion(fila.referencia)}
          className="p-1 hover:bg-gray-200 rounded transition-colors"
          title={isExpanded ? 'Colapsar' : 'Expandir'}
        >
          {isExpanded ? (
            <FaChevronDown className="text-gray-600" />
          ) : (
            <FaChevronRight className="text-gray-600" />
          )}
        </button>
      );
    }
    
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
    
    // Renderizar tipo de movimiento con colores
    if (col.key === 'tipo' && filtros.tipo === 'movimientos') {
      const esEntrada = (value || '').toLowerCase() === 'entrada';
      const colors = esEntrada 
        ? { bg: '#D1FAE5', text: '#065F46' }  // Verde para entradas
        : { bg: '#FEE2E2', text: '#991B1B' }; // Rojo para salidas
      return (
        <span 
          className="px-2 py-1 rounded-full text-xs font-bold"
          style={{ backgroundColor: colors.bg, color: colors.text }}
        >
          {esEntrada ? '📥 ENTRADA' : '📤 SALIDA'}
        </span>
      );
    }
    
    return formatted;
  };

  const renderResumen = () => {
    if (!resumen) return null;

    if (filtros.tipo === 'inventario') {
      return (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 md:gap-4 p-3 md:p-4 bg-gradient-to-r from-gray-50 to-white border-t">
          <div className="flex items-center gap-2 md:gap-3 p-2 md:p-3 bg-blue-50 rounded-lg">
            <FaBox className="text-xl md:text-2xl text-blue-600" />
            <div>
              <p className="text-[10px] md:text-xs text-blue-600 font-semibold">Total Productos</p>
              <p className="text-lg md:text-xl font-bold text-blue-800">{resumen.total_productos || 0}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 md:gap-3 p-2 md:p-3 bg-green-50 rounded-lg">
            <FaDatabase className="text-xl md:text-2xl text-green-600" />
            <div>
              <p className="text-[10px] md:text-xs text-green-600 font-semibold">Inventario Total</p>
              <p className="text-lg md:text-xl font-bold text-green-800">{(resumen.stock_total || 0).toLocaleString()}</p>
            </div>
          </div>
        </div>
      );
    }

    if (filtros.tipo === 'caducidades') {
      return (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 bg-gradient-to-r from-gray-50 to-white border-t">
          <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
            <FaClock className="text-2xl text-blue-600" />
            <div>
              <p className="text-xs text-blue-600 font-semibold">Total Lotes</p>
              <p className="text-xl font-bold text-blue-800">{resumen.total || datos.length}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-red-50 rounded-lg">
            <FaTimesCircle className="text-2xl text-red-600" />
            <div>
              <p className="text-xs text-red-600 font-semibold">Vencidos</p>
              <p className="text-xl font-bold text-red-800">{resumen.vencidos || 0}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-orange-50 rounded-lg">
            <FaExclamationTriangle className="text-2xl text-orange-600" />
            <div>
              <p className="text-xs text-orange-600 font-semibold">Críticos (≤7 días)</p>
              <p className="text-xl font-bold text-orange-800">{resumen.criticos || 0}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-yellow-50 rounded-lg">
            <FaClock className="text-2xl text-yellow-600" />
            <div>
              <p className="text-xs text-yellow-600 font-semibold">Próximos</p>
              <p className="text-xl font-bold text-yellow-800">{resumen.proximos || 0}</p>
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

    if (filtros.tipo === 'movimientos') {
      // Formatear las fechas para mostrar el período
      const formatearFecha = (fecha) => {
        if (!fecha) return null;
        try {
          return new Date(fecha + 'T00:00:00').toLocaleDateString('es-MX', { 
            day: '2-digit', 
            month: 'short', 
            year: 'numeric' 
          });
        } catch {
          return fecha;
        }
      };
      
      const fechaInicioStr = formatearFecha(filtros.fechaInicio);
      const fechaFinStr = formatearFecha(filtros.fechaFin);
      const periodoTexto = fechaInicioStr && fechaFinStr 
        ? `${fechaInicioStr} - ${fechaFinStr}`
        : fechaInicioStr 
          ? `Desde ${fechaInicioStr}`
          : fechaFinStr
            ? `Hasta ${fechaFinStr}`
            : 'Todo el historial';
      
      return (
        <div className="p-3 md:p-4 bg-gradient-to-r from-gray-50 to-white border-t">
          {/* Indicador de período */}
          <div className="flex items-center justify-center mb-2 md:mb-3">
            <span className="px-2 md:px-3 py-1 bg-blue-100 text-blue-800 text-[10px] md:text-xs font-semibold rounded-full flex items-center gap-1 md:gap-2">
              <FaClock className="text-blue-600" />
              Período: {periodoTexto}
            </span>
          </div>
          {/* Resumen general de transacciones */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 md:gap-3">
            <div className="flex items-center gap-2 md:gap-3 p-2 md:p-3 bg-indigo-50 rounded-lg">
              <FaClipboardList className="text-lg md:text-2xl text-indigo-600" />
              <div>
                <p className="text-[10px] md:text-xs text-indigo-600 font-semibold">Transacciones</p>
                <p className="text-base md:text-xl font-bold text-indigo-800">{resumen.total_transacciones || datos.length}</p>
                <p className="text-[9px] md:text-[10px] text-indigo-500">grupos únicos</p>
              </div>
            </div>
            <div className="flex items-center gap-2 md:gap-3 p-2 md:p-3 bg-blue-50 rounded-lg">
              <FaExchangeAlt className="text-lg md:text-2xl text-blue-600" />
              <div>
                <p className="text-[10px] md:text-xs text-blue-600 font-semibold">Productos</p>
                <p className="text-base md:text-xl font-bold text-blue-800">{resumen.total_movimientos || 0}</p>
                <p className="text-[9px] md:text-[10px] text-blue-500">items movidos</p>
              </div>
            </div>
            <div className="flex items-center gap-2 md:gap-3 p-2 md:p-3 bg-green-50 rounded-lg">
              <span className="text-lg md:text-2xl">📥</span>
              <div>
                <p className="text-[10px] md:text-xs text-green-600 font-semibold">Entradas</p>
                <p className="text-base md:text-xl font-bold text-green-800">{(resumen.total_entradas || 0).toLocaleString()} uds</p>
                <p className="text-[9px] md:text-[10px] text-green-500">{resumen.trans_entradas || 0} trans.</p>
              </div>
            </div>
            <div className="flex items-center gap-2 md:gap-3 p-2 md:p-3 bg-red-50 rounded-lg">
              <span className="text-lg md:text-2xl">📤</span>
              <div>
                <p className="text-[10px] md:text-xs text-red-600 font-semibold">Salidas</p>
                <p className="text-base md:text-xl font-bold text-red-800">{(resumen.total_salidas || 0).toLocaleString()} uds</p>
                <p className="text-[9px] md:text-[10px] text-red-500">{resumen.trans_salidas || 0} trans.</p>
              </div>
            </div>
            <div className="flex items-center gap-2 md:gap-3 p-2 md:p-3 bg-purple-50 rounded-lg col-span-2 sm:col-span-1">
              <FaDatabase className="text-lg md:text-2xl text-purple-600" />
              <div>
                <p className="text-[10px] md:text-xs text-purple-600 font-semibold">Balance</p>
                <p className={`text-base md:text-xl font-bold ${(resumen.diferencia || 0) >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                  {(resumen.diferencia || 0) >= 0 ? '+' : ''}{(resumen.diferencia || 0).toLocaleString()} uds
                </p>
                <p className="text-[9px] md:text-[10px] text-purple-500">neto</p>
              </div>
            </div>
          </div>
          <p className="text-[10px] md:text-xs text-gray-500 mt-2 text-center">
            💡 Haz clic en una fila para ver los productos de cada transacción
          </p>
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
    <div className="p-4 md:p-6 space-y-4 md:space-y-6 max-w-full overflow-hidden">
      <PageHeader
        icon={FaChartBar}
        title="Reportes"
        subtitle="Consulta y exporta información clave del inventario"
        badge={badgeContent}
      />

      {/* Panel de Filtros */}
      <div className="bg-white rounded-xl shadow-lg p-4 md:p-6 border-l-4 card-theme-border">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
          <h3 className="text-base md:text-lg font-bold flex items-center gap-2 text-theme-primary-hover">
            <FaFilter />
            Filtros de Reporte
          </h3>
          <div className="flex items-center gap-2">
            {getTipoIcon()}
            <span className="text-sm font-semibold capitalize">{filtros.tipo}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 mb-4">
          {/* Tipo de reporte */}
          <div className="space-y-1">
            <label className="text-sm font-semibold text-gray-700">Tipo de reporte</label>
            <select
              value={filtros.tipo}
              onChange={(e) => handleTipoChange(e.target.value)}
              className="w-full rounded-lg border-2 border-gray-200 px-3 py-2.5 focus:outline-none focus:border-rose-500 transition-colors"
            >
              <option value="inventario">📦 Inventario</option>
              <option value="caducidades">⏰ Caducidades</option>
              <option value="requisiciones">📋 Requisiciones</option>
              <option value="movimientos">🔄 Movimientos</option>
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
                  value={!esAdminOFarmacia && userCentroId ? userCentroId : filtros.centro}
                  onChange={(e) => handleFiltro("centro", e.target.value)}
                  disabled={!esAdminOFarmacia && userCentroId}
                  className={`w-full rounded-lg border-2 border-gray-200 px-3 py-2.5 focus:outline-none focus:border-rose-500 transition-colors ${!esAdminOFarmacia && userCentroId ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                >
                  {esAdminOFarmacia ? (
                    <>
                      <option value="">Todos los centros</option>
                      <option value="central">🏥 Almacén Central</option>
                      {centros.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.nombre}
                        </option>
                      ))}
                    </>
                  ) : (
                    <option value={userCentroId}>
                      {centros.find(c => c.id === userCentroId)?.nombre || 'Tu centro'}
                    </option>
                  )}
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
                  {/* ISS-DB-002: Estados alineados con BD Supabase */}
                  <option value="">Todos los estados</option>
                  <option value="borrador">📝 Borrador</option>
                  <option value="enviada">📤 Enviada</option>
                  <option value="autorizada">✅ Autorizada</option>
                  <option value="en_surtido">🔄 En Surtido</option>
                  <option value="parcial">⏳ Parcialmente Surtida</option>
                  <option value="rechazada">❌ Rechazada</option>
                  <option value="surtida">✔️ Surtida</option>
                  <option value="entregada">📦 Entregada</option>
                  <option value="cancelada">🚫 Cancelada</option>
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-semibold text-gray-700">Centro</label>
                <select
                  value={!esAdminOFarmacia && userCentroId ? userCentroId : filtros.centro}
                  onChange={(e) => handleFiltro("centro", e.target.value)}
                  disabled={!esAdminOFarmacia && userCentroId}
                  className={`w-full rounded-lg border-2 border-gray-200 px-3 py-2.5 focus:outline-none focus:border-rose-500 transition-colors ${!esAdminOFarmacia && userCentroId ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                >
                  {esAdminOFarmacia ? (
                    <>
                      <option value="">Todos los centros</option>
                      {centros.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.nombre}
                        </option>
                      ))}
                    </>
                  ) : (
                    <option value={userCentroId}>
                      {centros.find(c => c.id === userCentroId)?.nombre || 'Tu centro'}
                    </option>
                  )}
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
                  value={!esAdminOFarmacia && userCentroId ? userCentroId : filtros.centro}
                  onChange={(e) => handleFiltro("centro", e.target.value)}
                  disabled={!esAdminOFarmacia && userCentroId}
                  className={`w-full rounded-lg border-2 border-gray-200 px-3 py-2.5 focus:outline-none focus:border-rose-500 transition-colors ${!esAdminOFarmacia && userCentroId ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                >
                  {esAdminOFarmacia ? (
                    <>
                      <option value="">Todos los centros</option>
                      <option value="central">🏥 Farmacia Central</option>
                      {centros.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.nombre}
                        </option>
                      ))}
                    </>
                  ) : (
                    <option value={userCentroId}>
                      {centros.find(c => c.id === userCentroId)?.nombre || 'Tu centro'}
                    </option>
                  )}
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

          {filtros.tipo === "movimientos" && (
            <>
              <div className="space-y-1">
                <label className="text-sm font-semibold text-gray-700">Tipo de movimiento</label>
                <select
                  value={filtros.tipoMovimiento}
                  onChange={(e) => handleFiltro("tipoMovimiento", e.target.value)}
                  className="w-full rounded-lg border-2 border-gray-200 px-3 py-2.5 focus:outline-none focus:border-rose-500 transition-colors"
                >
                  <option value="">Todos los movimientos</option>
                  <option value="entrada">📥 Entradas</option>
                  <option value="salida">📤 Salidas</option>
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-semibold text-gray-700">Centro</label>
                <select
                  value={!esAdminOFarmacia && userCentroId ? userCentroId : filtros.centro}
                  onChange={(e) => handleFiltro("centro", e.target.value)}
                  disabled={!esAdminOFarmacia && userCentroId}
                  className={`w-full rounded-lg border-2 border-gray-200 px-3 py-2.5 focus:outline-none focus:border-rose-500 transition-colors ${!esAdminOFarmacia && userCentroId ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                >
                  {esAdminOFarmacia ? (
                    <>
                      <option value="">Todos los centros</option>
                      <option value="central">🏥 Farmacia Central</option>
                      {centros.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.nombre}
                        </option>
                      ))}
                    </>
                  ) : (
                    <option value={userCentroId}>
                      {centros.find(c => c.id === userCentroId)?.nombre || 'Tu centro'}
                    </option>
                  )}
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
              {/* Botones rápidos de período */}
              <div className="space-y-1 col-span-full">
                <label className="text-sm font-semibold text-gray-700">Período rápido</label>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setFiltros(prev => ({
                        ...prev,
                        fechaInicio: getFirstDayOfMonth(),
                        fechaFin: getTodayDate()
                      }));
                    }}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                      filtros.fechaInicio === getFirstDayOfMonth() 
                        ? 'bg-rose-600 text-white' 
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    📅 Este mes
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setFiltros(prev => ({
                        ...prev,
                        fechaInicio: "",
                        fechaFin: ""
                      }));
                    }}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                      !filtros.fechaInicio && !filtros.fechaFin 
                        ? 'bg-rose-600 text-white' 
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    🗓️ Todo el historial
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Botones de acción */}
        <div className="flex flex-wrap gap-2 md:gap-3">
          <button
            onClick={cargarReporte}
            disabled={loading}
            className="flex items-center gap-2 px-3 md:px-4 py-2 md:py-2.5 rounded-lg text-white font-semibold text-sm md:text-base transition-all hover:scale-105 disabled:opacity-60 bg-theme-gradient"
          >
            {loading ? (
              <>
                <FaSpinner className="animate-spin" />
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
            className="px-3 md:px-4 py-2 md:py-2.5 rounded-lg bg-gray-200 text-gray-700 font-semibold text-sm md:text-base hover:bg-gray-300 transition disabled:opacity-60"
          >
            Limpiar
          </button>
          <button
            onClick={exportarExcel}
            disabled={loading || exporting || datos.length === 0}
            className="flex items-center gap-2 px-3 md:px-4 py-2 md:py-2.5 rounded-lg bg-green-600 text-white font-semibold text-sm md:text-base hover:bg-green-700 transition disabled:opacity-60"
          >
            {exporting ? (
              <>
                <FaSpinner className="animate-spin" />
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
            className="flex items-center gap-2 px-3 md:px-4 py-2 md:py-2.5 rounded-lg text-white font-semibold text-sm md:text-base hover:opacity-90 transition disabled:opacity-60"
            style={{ background: 'linear-gradient(135deg, #DC2626 0%, #991B1B 100%)' }}
          >
            {exporting ? (
              <>
                <FaSpinner className="animate-spin" />
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
      <div className="bg-white rounded-xl shadow-lg overflow-hidden border-l-4 card-theme-border max-w-full">
        <div className="p-3 md:p-4 border-b border-gray-200 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
          <div>
            <h3 className="text-base md:text-lg font-bold text-gray-800 flex items-center gap-2">
              {getTipoIcon()}
              Reporte de {filtros.tipo.charAt(0).toUpperCase() + filtros.tipo.slice(1)}
            </h3>
            <p className="text-xs md:text-sm text-gray-500">
              Mostrando {indiceInicio + 1}-{Math.min(indiceFin, datos.length)} de {datos.length} registros
            </p>
          </div>
        </div>

        {/* Resumen */}
        {renderResumen()}

        {/* Tabla */}
        <div className="w-full overflow-x-auto" style={{ maxWidth: '100%' }}>
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="text-center">
                <FaSpinner className="animate-spin text-4xl mx-auto mb-4 text-theme-primary" />
                <p className="text-gray-600 font-semibold">Cargando reporte...</p>
              </div>
            </div>
          ) : datosPaginados.length === 0 ? (
            <div className="text-center py-20">
              <FaChartBar className="mx-auto text-6xl text-gray-300 mb-4" />
              <p className="text-xl font-semibold text-gray-600">No hay datos para mostrar</p>
              <p className="text-gray-500 mt-2">Intenta ajustar los filtros o selecciona otro tipo de reporte</p>
            </div>
          ) : (
            <table className="w-full text-xs md:text-sm" style={{ minWidth: '800px' }}>
              <thead className="bg-theme-gradient sticky top-0 z-10">
                <tr>
                  {columnas.map((col) => (
                    <th 
                      key={col.key} 
                      className="px-2 md:px-4 py-2 md:py-3 text-xs font-bold text-white uppercase tracking-wider whitespace-nowrap"
                      style={{ 
                        textAlign: col.align || 'left'
                      }}
                    >
                      {col.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {datosPaginados.map((fila, idx) => {
                  const isMovimientos = filtros.tipo === 'movimientos';
                  const isExpanded = isMovimientos && expandedRows[fila.referencia];
                  const globalIdx = indiceInicio + idx;  // Índice global para numeración
                  
                  return (
                    <React.Fragment key={idx}>
                      {/* Fila principal */}
                      <tr 
                        className={`${isMovimientos ? 'cursor-pointer' : ''} hover:bg-gray-50 transition-colors ${isExpanded ? 'bg-blue-50' : ''}`}
                        onClick={isMovimientos ? () => toggleRowExpansion(fila.referencia) : undefined}
                      >
                        {columnas.map((col) => (
                          <td 
                            key={col.key} 
                            className="px-2 md:px-4 py-2 md:py-3 text-gray-800 truncate max-w-[200px]"
                            style={{ 
                              textAlign: col.align || 'left',
                              width: col.width,
                              minWidth: col.width
                            }}
                            title={typeof fila[col.key] === 'string' ? fila[col.key] : undefined}
                          >
                            {renderCellValue(fila, col, globalIdx)}
                          </td>
                        ))}
                      </tr>
                      
                      {/* Fila de detalles expandida (solo para movimientos) */}
                      {isExpanded && fila.detalles && fila.detalles.length > 0 && (
                        <tr className="bg-gray-50">
                          <td colSpan={columnas.length} className="px-6 py-3">
                            <div className="bg-white rounded-lg border shadow-sm p-4">
                              <h4 className="text-sm font-semibold text-gray-700 mb-3">
                                📦 Productos en esta transacción ({fila.detalles.length} items)
                              </h4>
                              <table className="w-full text-sm">
                                <thead className="bg-gray-100">
                                  <tr>
                                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600">#</th>
                                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600">Producto</th>
                                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600">Lote</th>
                                    <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600">Cantidad</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-100">
                                  {fila.detalles.map((det, detIdx) => (
                                    <tr key={detIdx} className="hover:bg-gray-50">
                                      <td className="px-3 py-2 text-gray-500">{detIdx + 1}</td>
                                      <td className="px-3 py-2 text-gray-800 font-medium">{det.producto}</td>
                                      <td className="px-3 py-2 text-gray-600">{det.lote || '-'}</td>
                                      <td className="px-3 py-2 text-gray-800 text-right font-semibold">{det.cantidad}</td>
                                    </tr>
                                  ))}
                                </tbody>
                                <tfoot className="bg-gray-50">
                                  <tr>
                                    <td colSpan="3" className="px-3 py-2 text-right text-xs font-semibold text-gray-600">Total:</td>
                                    <td className="px-3 py-2 text-right text-sm font-bold text-gray-800">{fila.total_cantidad}</td>
                                  </tr>
                                </tfoot>
                              </table>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Controles de Paginación */}
        {datos.length > 0 && (
          <div className="p-3 md:p-4 bg-gray-50 border-t flex flex-col sm:flex-row items-center justify-between gap-3">
            <p className="text-xs md:text-sm text-gray-600">
              Página {paginaActual} de {totalPaginas} ({datos.length} registros)
            </p>
            <div className="flex items-center gap-1 md:gap-2">
              {/* Primera página */}
              <button
                onClick={() => setPaginaActual(1)}
                disabled={paginaActual === 1}
                className="p-1.5 md:p-2 rounded-lg bg-white border border-gray-300 text-gray-600 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition"
                title="Primera página"
              >
                <FaAngleDoubleLeft className="text-sm" />
              </button>
              {/* Página anterior */}
              <button
                onClick={() => setPaginaActual(prev => Math.max(1, prev - 1))}
                disabled={paginaActual === 1}
                className="p-1.5 md:p-2 rounded-lg bg-white border border-gray-300 text-gray-600 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition"
                title="Página anterior"
              >
                <FaChevronLeft className="text-sm" />
              </button>
              
              {/* Números de página */}
              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(5, totalPaginas) }, (_, i) => {
                  let pageNum;
                  if (totalPaginas <= 5) {
                    pageNum = i + 1;
                  } else if (paginaActual <= 3) {
                    pageNum = i + 1;
                  } else if (paginaActual >= totalPaginas - 2) {
                    pageNum = totalPaginas - 4 + i;
                  } else {
                    pageNum = paginaActual - 2 + i;
                  }
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setPaginaActual(pageNum)}
                      className={`w-7 h-7 md:w-8 md:h-8 rounded-lg text-xs md:text-sm font-semibold transition ${
                        paginaActual === pageNum
                          ? 'bg-theme-gradient text-white'
                          : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>
              
              {/* Página siguiente */}
              <button
                onClick={() => setPaginaActual(prev => Math.min(totalPaginas, prev + 1))}
                disabled={paginaActual === totalPaginas}
                className="p-1.5 md:p-2 rounded-lg bg-white border border-gray-300 text-gray-600 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition"
                title="Página siguiente"
              >
                <FaChevronRight className="text-sm" />
              </button>
              {/* Última página */}
              <button
                onClick={() => setPaginaActual(totalPaginas)}
                disabled={paginaActual === totalPaginas}
                className="p-1.5 md:p-2 rounded-lg bg-white border border-gray-300 text-gray-600 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition"
                title="Última página"
              >
                <FaAngleDoubleRight className="text-sm" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Reportes;
