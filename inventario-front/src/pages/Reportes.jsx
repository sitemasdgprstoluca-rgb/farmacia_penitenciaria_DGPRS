import React, { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
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
  FaAngleDoubleRight,
  FaFileContract,
  FaCubes,
  FaChartLine,
  FaDollarSign
} from "react-icons/fa";
import { reportesAPI, centrosAPI, descargarArchivo, abrirPdfEnNavegador } from "../services/api";
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
  centro: "todos",  // Por defecto: todos los centros (para admin/farmacia)
  nivelStock: "",
  tipoMovimiento: "",
  numeroContrato: "",  // Filtro para reporte de contratos
  soloSobreentregas: false,  // Filtro para reporte de parcialidades
  mesControlMensual: new Date().getMonth() + 1,
  anioControlMensual: new Date().getFullYear(),
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
  contratos: [
    { key: 'expand', label: '', width: '40px', align: 'center' },
    { key: 'numero_contrato', label: 'No. Contrato', width: '140px' },
    { key: 'total_lotes', label: 'Lotes', width: '60px', align: 'center' },
    { key: 'total_productos', label: 'Prods', width: '60px', align: 'center' },
    { key: 'cantidad_inicial', label: 'Inicial', width: '80px', align: 'right' },
    { key: 'cantidad_actual', label: 'Actual', width: '80px', align: 'right' },
    { key: 'cantidad_consumida', label: 'Consumido', width: '85px', align: 'right' },
    { key: 'porcentaje_uso', label: '% Uso', width: '65px', align: 'center' },
    { key: 'movimientos_entrada', label: 'Entradas', width: '75px', align: 'center' },
    { key: 'movimientos_salida', label: 'Salidas', width: '70px', align: 'center' },
    { key: 'valor_total', label: 'Valor Total', width: '100px', align: 'right' },
    { key: 'estado', label: 'Estado', width: '100px', align: 'center' },
  ],
  parcialidades: [
    { key: 'fecha_entrega', label: 'Fecha Entrega', width: '110px' },
    { key: 'numero_lote', label: 'Lote', width: '120px' },
    { key: 'clave_producto', label: 'Clave', width: '80px' },
    { key: 'producto_nombre', label: 'Producto', width: '180px' },
    { key: 'cantidad', label: 'Cantidad', width: '80px', align: 'right' },
    { key: 'numero_factura', label: 'Factura', width: '100px' },
    { key: 'proveedor', label: 'Proveedor', width: '140px' },
    { key: 'centro', label: 'Centro', width: '150px' },
    { key: 'es_sobreentrega', label: 'Sobre-entrega', width: '100px', align: 'center' },
    { key: 'usuario', label: 'Registró', width: '100px' },
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
  // Estados de caducidades
  if (e === 'vencido') return { bg: '#FEE2E2', text: '#991B1B' };
  if (e === 'critico') return { bg: '#FFEDD5', text: '#9A3412' };
  if (e === 'proximo') return { bg: '#FEF3C7', text: '#92400E' };
  // Estados de requisiciones - FLUJO V2
  // Estados del flujo del centro
  if (e === 'borrador') return { bg: '#E5E7EB', text: '#374151' };
  if (e === 'pendiente_admin') return { bg: '#FEF3C7', text: '#92400E' };
  if (e === 'pendiente_director') return { bg: '#FEF3C7', text: '#92400E' };
  if (e === 'devuelta') return { bg: '#FFEDD5', text: '#9A3412' };
  // Estados del flujo de farmacia
  if (e === 'enviada') return { bg: '#DBEAFE', text: '#1E40AF' };
  if (e === 'en_revision') return { bg: '#E0E7FF', text: '#3730A3' };
  if (e === 'autorizada') return { bg: '#D1FAE5', text: '#065F46' };
  if (e === 'en_surtido') return { bg: '#FFEDD5', text: '#9A3412' };
  if (e === 'surtida') return { bg: '#D1FAE5', text: '#065F46' };
  if (e === 'entregada') return { bg: '#DBEAFE', text: '#1E40AF' };
  // Estados finales negativos
  if (e === 'rechazada') return { bg: '#FEE2E2', text: '#991B1B' };
  if (e === 'vencida') return { bg: '#FEE2E2', text: '#991B1B' };
  if (e === 'cancelada') return { bg: '#E5E7EB', text: '#6B7280' };
  // Compatibilidad legacy
  if (e === 'parcial') return { bg: '#FEF3C7', text: '#92400E' };
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
  const location = useLocation();
  
  // Verificación de permisos
  const rolPrincipal = getRolPrincipal();
  const esAdmin = rolPrincipal === 'ADMIN';
  const esFarmacia = rolPrincipal === 'FARMACIA';
  const esSuperusuario = permisos?.isSuperuser;
  const esAdminOFarmacia = esAdmin || esFarmacia || esSuperusuario;
  
  // Si el usuario tiene centro asignado y no es admin/farmacia, forzar filtro por su centro
  const userCentroId = user?.centro?.id || null;
  
  // Inicializar filtros desde navegación si vienen en state
  const initFiltros = () => {
    const navegacionState = location.state || {};
    const filtrosBase = { ...baseFilters };
    
    // Si viene tipo de reporte desde navegación, aplicarlo
    if (navegacionState.tipo) {
      filtrosBase.tipo = navegacionState.tipo;
    }
    
    // Si viene centro desde navegación, aplicarlo
    if (navegacionState.centro) {
      filtrosBase.centro = navegacionState.centro;
    }
    
    return filtrosBase;
  };
  
  const [filtros, setFiltros] = useState(initFiltros());
  const [datos, setDatos] = useState([]);
  const [resumen, setResumen] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");
  const [centros, setCentros] = useState([]);
  const [expandedRows, setExpandedRows] = useState({});  // Para expandir filas de movimientos y contratos
  
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
    
    // ── Centro ──────────────────────────────────────────────────────────
    // Contratos y Control Mensual no usan el filtro global de centro
    const reporteUsaCentro = !['contratos', 'control_mensual'].includes(filtros.tipo);
    
    if (reporteUsaCentro) {
      if (!esAdminOFarmacia && userCentroId) {
        // Usuario restringido: siempre su centro
        params.centro = userCentroId;
      } else if (esAdminOFarmacia) {
        // Admin/Farmacia: enviar valor explícito del selector
        const centroVal = filtros.centro;
        if (centroVal && centroVal !== '' && centroVal !== null && centroVal !== undefined) {
          params.centro = centroVal;  // 'todos', 'central', o ID numérico
        }
        // Si no hay valor → no enviar param → backend trata como 'todos'
      }
    }
    
    // ── Parámetros específicos por tipo de reporte ──────────────────────
    if (filtros.tipo === "inventario") {
      if (filtros.nivelStock) params.nivel_stock = filtros.nivelStock;
      if (filtros.fechaInicio) params.fecha_inicio = filtros.fechaInicio;
      if (filtros.fechaFin) params.fecha_fin = filtros.fechaFin;
    } else if (filtros.tipo === "caducidades") {
      if (filtros.dias && filtros.dias !== 30) params.dias = filtros.dias;
      if (filtros.estado) params.estado = filtros.estado;
    } else if (filtros.tipo === "requisiciones") {
      if (filtros.estado) params.estado = filtros.estado;
      if (filtros.fechaInicio) params.fecha_inicio = filtros.fechaInicio;
      if (filtros.fechaFin) params.fecha_fin = filtros.fechaFin;
    } else if (filtros.tipo === "movimientos") {
      if (filtros.tipoMovimiento) params.tipo = filtros.tipoMovimiento;
      if (filtros.fechaInicio) params.fecha_inicio = filtros.fechaInicio;
      if (filtros.fechaFin) params.fecha_fin = filtros.fechaFin;
    } else if (filtros.tipo === "contratos") {
      if (filtros.numeroContrato && filtros.numeroContrato.trim()) {
        params.numero_contrato = filtros.numeroContrato.trim();
      }
    } else if (filtros.tipo === "parcialidades") {
      if (filtros.fechaInicio) params.fecha_inicio = filtros.fechaInicio;
      if (filtros.fechaFin) params.fecha_fin = filtros.fechaFin;
      if (filtros.soloSobreentregas) params.es_sobreentrega = 'true';
    }
    
    return params;
  };

  const cargarReporte = async () => {
    // Control Mensual es solo PDF, no tiene vista previa
    if (filtros.tipo === "control_mensual") {
      toast('El Control Mensual solo está disponible como PDF. Use el botón "Exportar PDF" para generarlo.', 
        { icon: '📊', duration: 4000 });
      return;
    }
    
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
      } else if (filtros.tipo === "contratos") {
        response = await reportesAPI.contratos(params);
      } else if (filtros.tipo === "parcialidades") {
        response = await reportesAPI.parcialidades(params);
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
      // Mostrar errores de validación del backend (400) de forma amigable
      const errData = err.response?.data;
      let msg;
      if (errData?.errores && Array.isArray(errData.errores)) {
        msg = errData.errores.join('\n');
      } else {
        msg = errData?.detail || errData?.error || err.message || "Error al cargar reporte";
      }
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarCatalogos();
  }, []);

  // Si viene navegación desde Dashboard con filtros, cargar automáticamente el reporte
  useEffect(() => {
    const navegacionState = location.state || {};
    if (navegacionState.tipo || navegacionState.centro) {
      // Hay filtros desde navegación, cargar automáticamente después de que estén los catálogos
      const timer = setTimeout(() => {
        cargarReporte();
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [location.state]);

  // Cuando cambia el tipo de reporte, resetear filtros específicos según el tipo
  const handleTipoChange = (nuevoTipo) => {
    // Resetear todos los filtros pero mantener el centro actual del usuario
    const centroActual = filtros.centro;
    
    // Determinar centro adecuado para el nuevo tipo de reporte
    let centroNuevo = centroActual;
    if (nuevoTipo === 'control_mensual') {
      // Control Mensual requiere un centro específico (no tiene opción "todos")
      centroNuevo = (centroActual && centroActual !== 'todos') ? centroActual : 'central';
    } else if (nuevoTipo === 'contratos') {
      // Contratos no usa filtro de centro
      centroNuevo = centroActual;
    } else {
      // Demás reportes: si el centro era solo válido para control_mensual, resetear a 'todos'
      centroNuevo = centroActual || 'todos';
    }
    
    // Crear filtros base limpios
    let nuevosFiltros = {
      tipo: nuevoTipo,
      estado: "",
      dias: 30,
      fechaInicio: "",
      fechaFin: "",
      centro: centroNuevo,
      nivelStock: "",
      tipoMovimiento: "",
      numeroContrato: "",
      soloSobreentregas: false,
      mesControlMensual: new Date().getMonth() + 1,
      anioControlMensual: new Date().getFullYear(),
    };
    
    // Para movimientos, establecer fechas del mes actual por defecto
    if (nuevoTipo === "movimientos") {
      nuevosFiltros.fechaInicio = getFirstDayOfMonth();
      nuevosFiltros.fechaFin = getTodayDate();
    }
    
    setFiltros(nuevosFiltros);
    // Limpiar datos previos para evitar confusión
    setDatos([]);
    setResumen(null);
    setPaginaActual(1);
    // No cargar automáticamente - el usuario debe dar clic en "Aplicar Filtros"
  };

  // Función para aplicar filtros manualmente (botón)
  const aplicarFiltros = () => {
    cargarReporte();
  };

  const exportarExcel = async () => {
    // Control Mensual es solo PDF
    if (filtros.tipo === "control_mensual") {
      toast.error('El Control Mensual solo está disponible en formato PDF oficial.');
      return;
    }
    
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
      } else if (filtros.tipo === "contratos") {
        response = await reportesAPI.exportarContratosExcel(params);
        filename = `contratos_${new Date().toISOString().split("T")[0]}.xlsx`;
      } else if (filtros.tipo === "parcialidades") {
        response = await reportesAPI.exportarParcialidadesExcel(params);
        filename = `historial_entregas_${new Date().toISOString().split("T")[0]}.xlsx`;
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
    const win = abrirPdfEnNavegador(); // Pre-abrir pestaña (preserva user-gesture)
    if (!win) return;

    setExporting(true);
    const toastId = toast.loading("Generando archivo PDF...");
    try {
      const params = { ...buildParams(), formato: 'pdf' };
      let response;
      
      if (filtros.tipo === "inventario") {
        response = await reportesAPI.exportarInventarioPDF(params);
      } else if (filtros.tipo === "caducidades") {
        response = await reportesAPI.exportarCaducidadesPDF(params);
      } else if (filtros.tipo === "requisiciones") {
        response = await reportesAPI.exportarRequisicionesPDF(params);
      } else if (filtros.tipo === "movimientos") {
        response = await reportesAPI.exportarMovimientosPDF(params);
      } else if (filtros.tipo === "contratos") {
        response = await reportesAPI.exportarContratosPDF(params);
      } else if (filtros.tipo === "parcialidades") {
        response = await reportesAPI.exportarParcialidadesPDF(params);
      } else if (filtros.tipo === "control_mensual") {
        // Control Mensual - Formato Oficial A
        // Normalizar centro: 'todos' no es válido para control_mensual, usar 'central'
        let centroControl = filtros.centro;
        if (!centroControl || centroControl === 'todos') centroControl = 'central';
        const controlParams = {
          mes: filtros.mesControlMensual || new Date().getMonth() + 1,
          anio: filtros.anioControlMensual || new Date().getFullYear(),
          centro: centroControl
        };
        response = await reportesAPI.exportarControlMensualPDF(controlParams);
      } else {
        try { win.close(); } catch {}
        toast.error("Tipo de reporte no soportado para PDF", { id: toastId });
        return;
      }
      
      abrirPdfEnNavegador(response, win);
      toast.success(`✅ PDF generado`, { id: toastId });
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
    // Determinar el centro apropiado según el rol del usuario
    const centroDefault = (!esAdminOFarmacia && userCentroId) ? userCentroId : "todos";
    
    // Resetear a filtros base pero con el centro apropiado
    setFiltros({
      ...baseFilters,
      centro: centroDefault
    });
    
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
    if (filtros.tipo === 'control_mensual') return <FaDatabase />;
    if (filtros.tipo === 'contratos') return <FaFileContract />;
    if (filtros.tipo === 'parcialidades') return <FaCubes />;
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
    
    // Columna de expansión para contratos (mostrar lotes)
    if (col.key === 'expand' && filtros.tipo === 'contratos') {
      const hasLotes = fila.lotes && fila.lotes.length > 0;
      if (!hasLotes) return null;
      const isExpanded = expandedRows[fila.numero_contrato];
      return (
        <button
          onClick={() => toggleRowExpansion(fila.numero_contrato)}
          className="p-1 hover:bg-gray-200 rounded transition-colors"
          title={isExpanded ? 'Colapsar' : 'Ver lotes del contrato'}
        >
          {isExpanded ? (
            <FaChevronDown className="text-indigo-600" />
          ) : (
            <FaChevronRight className="text-indigo-600" />
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
    
    // Renderizar sobre-entrega para parcialidades
    if (col.key === 'es_sobreentrega' && filtros.tipo === 'parcialidades') {
      const esSobre = value === true;
      const colors = esSobre 
        ? { bg: '#FEE2E2', text: '#991B1B' }  // Rojo para sobre-entregas
        : { bg: '#D1FAE5', text: '#065F46' }; // Verde normal
      return (
        <span 
          className="px-2 py-1 rounded-full text-xs font-bold"
          style={{ backgroundColor: colors.bg, color: colors.text }}
        >
          {esSobre ? '⚠️ SÍ' : '✓ No'}
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

    // Resumen para reporte de contratos
    if (filtros.tipo === 'contratos') {
      return (
        <div className="p-3 md:p-4 bg-gradient-to-r from-gray-50 to-white border-t">
          <div className="text-center mb-3">
            <span className="px-3 py-1 bg-indigo-100 text-indigo-800 text-xs font-semibold rounded-full">
              📝 Seguimiento completo de contratos: Entrada → Consumo
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 md:gap-3">
            <div className="flex items-center gap-2 p-2 md:p-3 bg-indigo-50 rounded-lg">
              <FaFileContract className="text-lg md:text-2xl text-indigo-600" />
              <div>
                <p className="text-[10px] md:text-xs text-indigo-600 font-semibold">Contratos</p>
                <p className="text-base md:text-xl font-bold text-indigo-800">{resumen.total_contratos || datos.length}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 p-2 md:p-3 bg-blue-50 rounded-lg">
              <FaCubes className="text-lg md:text-2xl text-blue-600" />
              <div>
                <p className="text-[10px] md:text-xs text-blue-600 font-semibold">Total Lotes</p>
                <p className="text-base md:text-xl font-bold text-blue-800">{resumen.total_lotes || 0}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 p-2 md:p-3 bg-green-50 rounded-lg">
              <span className="text-lg md:text-2xl">📥</span>
              <div>
                <p className="text-[10px] md:text-xs text-green-600 font-semibold">Entradas</p>
                <p className="text-base md:text-xl font-bold text-green-800">{resumen.total_movimientos_entrada || 0}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 p-2 md:p-3 bg-red-50 rounded-lg">
              <span className="text-lg md:text-2xl">📤</span>
              <div>
                <p className="text-[10px] md:text-xs text-red-600 font-semibold">Salidas</p>
                <p className="text-base md:text-xl font-bold text-red-800">{resumen.total_movimientos_salida || 0}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 p-2 md:p-3 bg-orange-50 rounded-lg">
              <FaChartLine className="text-lg md:text-2xl text-orange-600" />
              <div>
                <p className="text-[10px] md:text-xs text-orange-600 font-semibold">Consumido</p>
                <p className="text-base md:text-xl font-bold text-orange-800">{(resumen.cantidad_consumida_global || 0).toLocaleString()}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 p-2 md:p-3 bg-purple-50 rounded-lg">
              <FaDollarSign className="text-lg md:text-2xl text-purple-600" />
              <div>
                <p className="text-[10px] md:text-xs text-purple-600 font-semibold">Valor Total</p>
                <p className="text-base md:text-xl font-bold text-purple-800">${(resumen.valor_total_global || 0).toLocaleString()}</p>
              </div>
            </div>
          </div>
          <p className="text-[10px] md:text-xs text-gray-500 mt-2 text-center">
            💡 Haz clic en una fila para ver los lotes de cada contrato con su seguimiento detallado
          </p>
        </div>
      );
    }

    // Resumen para reporte de historial de entregas (parcialidades)
    if (filtros.tipo === 'parcialidades') {
      return (
        <div className="p-3 md:p-4 bg-gradient-to-r from-gray-50 to-white border-t">
          <div className="text-center mb-3">
            <span className="px-3 py-1 bg-emerald-100 text-emerald-800 text-xs font-semibold rounded-full">
              📦 Historial de Entregas y Parcialidades
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 md:gap-3">
            <div className="flex items-center gap-2 p-2 md:p-3 bg-blue-50 rounded-lg">
              <FaClipboardList className="text-lg md:text-2xl text-blue-600" />
              <div>
                <p className="text-[10px] md:text-xs text-blue-600 font-semibold">Total Entregas</p>
                <p className="text-base md:text-xl font-bold text-blue-800">{resumen.total_registros || datos.length}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 p-2 md:p-3 bg-green-50 rounded-lg">
              <FaCubes className="text-lg md:text-2xl text-green-600" />
              <div>
                <p className="text-[10px] md:text-xs text-green-600 font-semibold">Cantidad Total</p>
                <p className="text-base md:text-xl font-bold text-green-800">{(resumen.total_cantidad_entregada || 0).toLocaleString()}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 p-2 md:p-3 bg-red-50 rounded-lg">
              <FaExclamationTriangle className="text-lg md:text-2xl text-red-600" />
              <div>
                <p className="text-[10px] md:text-xs text-red-600 font-semibold">Sobre-entregas</p>
                <p className="text-base md:text-xl font-bold text-red-800">{resumen.total_sobreentregas || 0}</p>
              </div>
            </div>
          </div>
          {resumen.fecha_inicio_filtro && resumen.fecha_fin_filtro && (
            <p className="text-[10px] md:text-xs text-gray-500 mt-2 text-center">
              📅 Período: {resumen.fecha_inicio_filtro} - {resumen.fecha_fin_filtro}
            </p>
          )}
        </div>
      );
    }

    return null;
  };

  return (
    <div className="p-4 md:p-6 space-y-5 md:space-y-6 max-w-full overflow-hidden">
      {/* Modern Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-primary-hover)] flex items-center justify-center text-white text-2xl shadow-lg shadow-[var(--color-primary)]/20">
            {getTipoIcon()}
          </div>
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-gray-900 capitalize">
              {filtros.tipo === 'control_mensual' ? 'Control Mensual' : filtros.tipo === 'parcialidades' ? 'Historial de Entregas' : filtros.tipo}
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">Consulta y exporta informes clave del inventario</p>
          </div>
        </div>
        <button
          onClick={limpiarFiltros}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-gray-200 text-sm font-medium text-gray-600 bg-white hover:bg-gray-50 hover:border-gray-300 transition-all disabled:opacity-50 shadow-sm"
        >
          <FaSync className="text-xs" />
          Restablecer filtros
        </button>
      </div>

      {/* Panel de Filtros - Clean Flat Card */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-5 md:p-6 space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-5">
          {/* Tipo de reporte */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-gray-500">Tipo de reporte</label>
            <select
              value={filtros.tipo}
              onChange={(e) => handleTipoChange(e.target.value)}
              className="w-full rounded-xl border border-gray-200 bg-gray-50/50 px-3.5 py-2.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/20 focus:border-[var(--color-primary)] transition-all hover:border-gray-300"
            >
              <option value="inventario">📦 Inventario</option>
              <option value="caducidades">⏰ Caducidades</option>
              <option value="requisiciones">📋 Requisiciones</option>
              <option value="movimientos">🔄 Movimientos</option>
              <option value="contratos">📝 Contratos (Lotes y Consumo)</option>
              <option value="parcialidades">📦 Historial de Entregas</option>
              <option value="control_mensual">📊 Control Mensual (Formato A)</option>
            </select>
          </div>

          {/* Filtros específicos por tipo */}
          {filtros.tipo === "caducidades" && (
            <>
              <div className="space-y-1.5">
                <label className="label-elevated">Días próximos</label>
                <input
                  type="number"
                  min="1"
                  max="365"
                  value={filtros.dias}
                  onChange={(e) => handleFiltro("dias", Number(e.target.value) || 30)}
                  className="input-elevated"
                />
              </div>
              <div className="space-y-1.5">
                <label className="label-elevated">Centro</label>
                <select
                  value={!esAdminOFarmacia && userCentroId ? userCentroId : (filtros.centro || 'todos')}
                  onChange={(e) => handleFiltro("centro", e.target.value)}
                  disabled={!esAdminOFarmacia && userCentroId}
                  className={`input-elevated ${!esAdminOFarmacia && userCentroId ? 'opacity-60 cursor-not-allowed' : ''}`}
                >
                  {esAdminOFarmacia ? (
                    <>
                      <option value="todos">Todos los centros</option>
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
              <div className="space-y-1.5">
                <label className="label-elevated">Estado caducidad</label>
                <select
                  value={filtros.estado}
                  onChange={(e) => handleFiltro("estado", e.target.value)}
                  className="input-elevated"
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
              <div className="space-y-1.5">
                <label className="label-elevated">Estado</label>
                <select
                  value={filtros.estado}
                  onChange={(e) => handleFiltro("estado", e.target.value)}
                  className="input-elevated"
                >
                  {/* ISS-DB-002: Estados alineados con BD Supabase y FLUJO V2 */}
                  <option value="">Todos los estados</option>
                  {/* Estados del flujo del centro */}
                  <option value="borrador">📝 Borrador</option>
                  <option value="pendiente_admin">⏳ Pendiente Admin</option>
                  <option value="pendiente_director">⏳ Pendiente Director</option>
                  {/* Estados del flujo de farmacia */}
                  <option value="enviada">📤 Enviada</option>
                  <option value="en_revision">🔍 En Revisión</option>
                  <option value="autorizada">✅ Autorizada</option>
                  <option value="en_surtido">🔄 En Surtido</option>
                  <option value="surtida">✔️ Surtida</option>
                  <option value="entregada">📦 Entregada</option>
                  {/* Estados finales negativos */}
                  <option value="rechazada">❌ Rechazada</option>
                  <option value="vencida">⏰ Vencida</option>
                  <option value="cancelada">🚫 Cancelada</option>
                  <option value="devuelta">↩️ Devuelta</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="label-elevated">Centro</label>
                <select
                  value={!esAdminOFarmacia && userCentroId ? userCentroId : (filtros.centro || 'todos')}
                  onChange={(e) => handleFiltro("centro", e.target.value)}
                  disabled={!esAdminOFarmacia && userCentroId}
                  className={`input-elevated ${!esAdminOFarmacia && userCentroId ? 'opacity-60 cursor-not-allowed' : ''}`}
                >
                  {esAdminOFarmacia ? (
                    <>
                      <option value="todos">Todos los centros</option>
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
              <div className="space-y-1.5">
                <label className="label-elevated">Desde</label>
                <input
                  type="date"
                  value={filtros.fechaInicio}
                  onChange={(e) => handleFiltro("fechaInicio", e.target.value)}
                  className="input-elevated"
                />
              </div>
              <div className="space-y-1.5">
                <label className="label-elevated">Hasta</label>
                <input
                  type="date"
                  value={filtros.fechaFin}
                  onChange={(e) => handleFiltro("fechaFin", e.target.value)}
                  className="input-elevated"
                />
              </div>
            </>
          )}

          {filtros.tipo === "inventario" && (
            <>
              <div className="space-y-1.5">
                <label className="label-elevated">Centro</label>
                <select
                  value={!esAdminOFarmacia && userCentroId ? userCentroId : (filtros.centro || 'todos')}
                  onChange={(e) => handleFiltro("centro", e.target.value)}
                  disabled={!esAdminOFarmacia && userCentroId}
                  className={`input-elevated ${!esAdminOFarmacia && userCentroId ? 'opacity-60 cursor-not-allowed' : ''}`}
                >
                  {esAdminOFarmacia ? (
                    <>
                      <option value="todos">Todos los centros</option>
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
              <div className="space-y-1.5">
                <label className="label-elevated">Nivel de inventario</label>
                <select
                  value={filtros.nivelStock}
                  onChange={(e) => handleFiltro("nivelStock", e.target.value)}
                  className="input-elevated"
                >
                  <option value="">Todos los niveles</option>
                  <option value="critico">🔴 Crítico</option>
                  <option value="bajo">🟡 Bajo</option>
                  <option value="alto">🟢 Alto</option>
                  <option value="sin_stock">⚪ Sin Inventario</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="label-elevated">Desde</label>
                <input
                  type="date"
                  value={filtros.fechaInicio}
                  onChange={(e) => handleFiltro("fechaInicio", e.target.value)}
                  className="input-elevated"
                />
              </div>
              <div className="space-y-1.5">
                <label className="label-elevated">Hasta</label>
                <input
                  type="date"
                  value={filtros.fechaFin}
                  onChange={(e) => handleFiltro("fechaFin", e.target.value)}
                  className="input-elevated"
                />
              </div>
              {/* Botones rápidos de período para inventario */}
              <div className="space-y-1.5 col-span-full">
                <label className="label-elevated">Período rápido</label>
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
                      filtros.fechaInicio === getFirstDayOfMonth() && filtros.fechaFin === getTodayDate()
                        ? 'bg-rose-600 text-white' 
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    📅 Este mes
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const now = new Date();
                      const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
                      const lastDayLastMonth = new Date(now.getFullYear(), now.getMonth(), 0);
                      setFiltros(prev => ({
                        ...prev,
                        fechaInicio: `${lastMonth.getFullYear()}-${String(lastMonth.getMonth() + 1).padStart(2, '0')}-01`,
                        fechaFin: `${lastDayLastMonth.getFullYear()}-${String(lastDayLastMonth.getMonth() + 1).padStart(2, '0')}-${String(lastDayLastMonth.getDate()).padStart(2, '0')}`
                      }));
                    }}
                    className="px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors bg-gray-100 text-gray-700 hover:bg-gray-200"
                  >
                    📆 Mes anterior
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
                    🗓️ Sin filtro de fecha
                  </button>
                </div>
              </div>
            </>
          )}

          {filtros.tipo === "movimientos" && (
            <>
              <div className="space-y-1.5">
                <label className="label-elevated">Tipo de movimiento</label>
                <select
                  value={filtros.tipoMovimiento}
                  onChange={(e) => handleFiltro("tipoMovimiento", e.target.value)}
                  className="input-elevated"
                >
                  <option value="">Todos los movimientos</option>
                  <option value="entrada">📥 Entradas</option>
                  <option value="salida">📤 Salidas</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="label-elevated">Centro</label>
                <select
                  value={!esAdminOFarmacia && userCentroId ? userCentroId : (filtros.centro || 'todos')}
                  onChange={(e) => handleFiltro("centro", e.target.value)}
                  disabled={!esAdminOFarmacia && userCentroId}
                  className={`input-elevated ${!esAdminOFarmacia && userCentroId ? 'opacity-60 cursor-not-allowed' : ''}`}
                >
                  {esAdminOFarmacia ? (
                    <>
                      <option value="todos">Todos los centros</option>
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
              <div className="space-y-1.5">
                <label className="label-elevated">Desde</label>
                <input
                  type="date"
                  value={filtros.fechaInicio}
                  onChange={(e) => handleFiltro("fechaInicio", e.target.value)}
                  className="input-elevated"
                />
              </div>
              <div className="space-y-1.5">
                <label className="label-elevated">Hasta</label>
                <input
                  type="date"
                  value={filtros.fechaFin}
                  onChange={(e) => handleFiltro("fechaFin", e.target.value)}
                  className="input-elevated"
                />
              </div>
              {/* Botones rápidos de período */}
              <div className="space-y-1.5 col-span-full">
                <label className="label-elevated">Período rápido</label>
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

          {/* Filtros para Contratos */}
          {filtros.tipo === "contratos" && (
            <div className="space-y-1.5 col-span-full">
              <label className="label-elevated">Buscar por número de contrato</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={filtros.numeroContrato}
                  onChange={(e) => handleFiltro("numeroContrato", e.target.value)}
                  placeholder="Ej: CB/A/37/2025"
                  className="input-elevated flex-1"
                />
                {filtros.numeroContrato && (
                  <button
                    type="button"
                    onClick={() => handleFiltro("numeroContrato", "")}
                    className="px-3.5 py-2.5 text-sm font-semibold rounded-xl border-2 border-gray-200 text-gray-600 hover:bg-gray-100 hover:border-gray-300 transition-all"
                    title="Limpiar filtro"
                  >
                    ✕
                  </button>
                )}
              </div>
              <p className="text-[11px] text-gray-400 mt-1">
                Deja vacío para ver todos los contratos, o escribe parte del número para filtrar
              </p>
            </div>
          )}

          {/* Filtros para Historial de Entregas (Parcialidades) */}
          {filtros.tipo === "parcialidades" && (
            <>
              <div className="space-y-1.5">
                <label className="label-elevated">Fecha inicio</label>
                <input
                  type="date"
                  value={filtros.fechaInicio}
                  onChange={(e) => handleFiltro("fechaInicio", e.target.value)}
                  className="input-elevated"
                />
              </div>
              <div className="space-y-1.5">
                <label className="label-elevated">Fecha fin</label>
                <input
                  type="date"
                  value={filtros.fechaFin}
                  onChange={(e) => handleFiltro("fechaFin", e.target.value)}
                  className="input-elevated"
                />
              </div>
              <div className="space-y-1.5">
                <label className="label-elevated">Centro</label>
                <select
                  value={!esAdminOFarmacia && userCentroId ? userCentroId : (filtros.centro || 'todos')}
                  onChange={(e) => handleFiltro("centro", e.target.value)}
                  disabled={!esAdminOFarmacia && userCentroId}
                  className={`input-elevated ${!esAdminOFarmacia && userCentroId ? 'opacity-60 cursor-not-allowed' : ''}`}
                >
                  {esAdminOFarmacia ? (
                    <>
                      <option value="todos">Todos los centros</option>
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
              <div className="space-y-1.5 flex items-end">
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={filtros.soloSobreentregas || false}
                    onChange={(e) => handleFiltro("soloSobreentregas", e.target.checked)}
                    className="w-5 h-5 rounded-lg border-2 border-gray-300 text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
                  />
                  <span className="label-elevated">Solo sobre-entregas</span>
                </label>
              </div>
            </>
          )}

          {/* Control Mensual - Formato Oficial A */}
          {filtros.tipo === "control_mensual" && (
            <>
              <div className="space-y-1.5">
                <label className="label-elevated">Mes</label>
                <select
                  value={filtros.mesControlMensual || new Date().getMonth() + 1}
                  onChange={(e) => handleFiltro("mesControlMensual", parseInt(e.target.value))}
                  className="input-elevated"
                >
                  <option value={1}>Enero</option>
                  <option value={2}>Febrero</option>
                  <option value={3}>Marzo</option>
                  <option value={4}>Abril</option>
                  <option value={5}>Mayo</option>
                  <option value={6}>Junio</option>
                  <option value={7}>Julio</option>
                  <option value={8}>Agosto</option>
                  <option value={9}>Septiembre</option>
                  <option value={10}>Octubre</option>
                  <option value={11}>Noviembre</option>
                  <option value={12}>Diciembre</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="label-elevated">Año</label>
                <select
                  value={filtros.anioControlMensual || new Date().getFullYear()}
                  onChange={(e) => handleFiltro("anioControlMensual", parseInt(e.target.value))}
                  className="input-elevated"
                >
                  {[...Array(5)].map((_, i) => {
                    const year = new Date().getFullYear() - 2 + i;
                    return <option key={year} value={year}>{year}</option>;
                  })}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="label-elevated">Centro / Almacén</label>
                <select
                  value={!esAdminOFarmacia && userCentroId ? userCentroId : (filtros.centro || 'central')}
                  onChange={(e) => handleFiltro("centro", e.target.value)}
                  disabled={!esAdminOFarmacia && userCentroId}
                  className={`input-elevated ${!esAdminOFarmacia && userCentroId ? 'opacity-60 cursor-not-allowed' : ''}`}
                >
                  {esAdminOFarmacia ? (
                    <>
                      <option value="central">🏥 Farmacia Central (CIA)</option>
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
              <div className="col-span-full">
                <div className="p-3.5 bg-blue-50/80 border border-blue-100 rounded-xl text-sm text-blue-700">
                  <strong>📊 Formato A - Control Mensual:</strong> Este reporte genera un PDF oficial apaisado con el control consolidado 
                  de entradas, salidas y existencias de insumos médicos para el período seleccionado. Incluye movimientos del mes y 
                  totales acumulados.
                </div>
              </div>
            </>
          )}
        </div>

        {/* Botones de acción */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={cargarReporte}
            disabled={loading}
            className="btn-elevated-primary text-sm"
          >
            {loading ? (
              <>
                <FaSpinner className="animate-spin" />
                Cargando...
              </>
            ) : (
              <>
                <FaFilter className="text-xs" />
                Aplicar filtros
              </>
            )}
          </button>
          <button
            onClick={limpiarFiltros}
            disabled={loading}
            className="btn-elevated-cancel text-sm"
          >
            <FaSync className="text-xs" />
            Limpiar
          </button>
          <button
            onClick={exportarExcel}
            disabled={loading || exporting || datos.length === 0 || filtros.tipo === 'control_mensual'}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-white font-medium text-sm transition-all hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed bg-emerald-600 shadow-sm"
            title={filtros.tipo === 'control_mensual' ? 'Control Mensual solo disponible en PDF' : ''}
          >
            {exporting ? <FaSpinner className="animate-spin" /> : <FaFileExcel />}
            Exportar Excel
          </button>
          <button
            onClick={exportarPDF}
            disabled={loading || exporting || (datos.length === 0 && filtros.tipo !== 'control_mensual')}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-white font-medium text-sm transition-all hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed bg-red-600 shadow-sm"
          >
            {exporting ? <FaSpinner className="animate-spin" /> : <FaFilePdf />}
            Exportar PDF
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-red-50 border border-red-100 text-red-600 text-sm flex items-center gap-2">
            <FaTimesCircle className="flex-shrink-0" />
            {error}
          </div>
        )}
      </div>
      </div>

      {/* Tabla de Datos */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden max-w-full">
        <div className="p-4 md:p-5 border-b border-gray-100 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-gray-500 text-lg">
              {getTipoIcon()}
            </div>
            <div>
              <h3 className="text-base md:text-lg font-semibold text-gray-800">
                Reporte de {filtros.tipo.charAt(0).toUpperCase() + filtros.tipo.slice(1)}
              </h3>
              <p className="text-xs text-gray-400">
                Mostrando {indiceInicio + 1}-{Math.min(indiceFin, datos.length)} de {datos.length} registros
              </p>
            </div>
          </div>
        </div>

        {/* Resumen */}
        {renderResumen()}

        {/* Tabla */}
        <div className="w-full overflow-x-auto" style={{ maxWidth: '100%' }}>
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="text-center">
                <div className="w-14 h-14 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-4">
                  <FaSpinner className="animate-spin text-xl text-gray-400" />
                </div>
                <p className="text-gray-600 font-medium">Cargando reporte...</p>
                <p className="text-xs text-gray-400 mt-1">Procesando datos</p>
              </div>
            </div>
          ) : datosPaginados.length === 0 ? (
            <div className="text-center py-20">
              <div className="w-16 h-16 rounded-2xl bg-gray-50 flex items-center justify-center mx-auto mb-4">
                <FaChartBar className="text-3xl text-gray-300" />
              </div>
              <p className="text-lg font-semibold text-gray-600">No hay datos para mostrar</p>
              <p className="text-sm text-gray-400 mt-1">Intenta ajustar los filtros o selecciona otro tipo de reporte</p>
            </div>
          ) : (
            <div className="table-soft overflow-x-auto">
            <table className="w-full text-xs md:text-sm" style={{ minWidth: '800px' }}>
              <thead className="sticky top-0 z-10">
                <tr className="bg-gradient-to-r from-gray-50 to-gray-100/80">
                  {columnas.map((col) => (
                    <th 
                      key={col.key} 
                      className="px-2 md:px-4 py-2.5 md:py-3 text-[10px] font-bold text-gray-500 uppercase tracking-wider whitespace-nowrap"
                      style={{ 
                        textAlign: col.align || 'left'
                      }}
                    >
                      {col.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {datosPaginados.map((fila, idx) => {
                  const isMovimientos = filtros.tipo === 'movimientos';
                  const isContratos = filtros.tipo === 'contratos';
                  const isExpandable = isMovimientos || isContratos;
                  const expandKey = isMovimientos ? fila.referencia : (isContratos ? fila.numero_contrato : null);
                  const isExpanded = isExpandable && expandedRows[expandKey];
                  const globalIdx = indiceInicio + idx;  // Índice global para numeración
                  
                  return (
                    <React.Fragment key={idx}>
                      {/* Fila principal */}
                      <tr 
                        className={`${isExpandable ? 'cursor-pointer' : ''} hover:bg-gray-50/80 transition-colors ${isExpanded ? (isContratos ? 'bg-indigo-50/50' : 'bg-blue-50/50') : ''}`}
                        onClick={isExpandable ? () => toggleRowExpansion(expandKey) : undefined}
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
                      {isExpanded && isMovimientos && fila.detalles && fila.detalles.length > 0 && (
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
                                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600">Presentación</th>
                                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600">Lote</th>
                                    <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600">Cantidad</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-100">
                                  {fila.detalles.map((det, detIdx) => (
                                    <tr key={detIdx} className="hover:bg-gray-50">
                                      <td className="px-3 py-2 text-gray-500">{detIdx + 1}</td>
                                      <td className="px-3 py-2 text-gray-800 font-medium">{det.producto}</td>
                                      <td className="px-3 py-2 text-gray-600">{det.presentacion || '-'}</td>
                                      <td className="px-3 py-2 text-gray-600">{det.lote || '-'}</td>
                                      <td className="px-3 py-2 text-gray-800 text-right font-semibold">{det.cantidad}</td>
                                    </tr>
                                  ))}
                                </tbody>
                                <tfoot className="bg-gray-50">
                                  <tr>
                                    <td colSpan="4" className="px-3 py-2 text-right text-xs font-semibold text-gray-600">Total:</td>
                                    <td className="px-3 py-2 text-right text-sm font-bold text-gray-800">{fila.total_cantidad}</td>
                                  </tr>
                                </tfoot>
                              </table>
                            </div>
                          </td>
                        </tr>
                      )}
                      
                      {/* Fila de detalles expandida (para contratos - muestra lotes) */}
                      {isExpanded && isContratos && fila.lotes && fila.lotes.length > 0 && (
                        <tr className="bg-indigo-50/30">
                          <td colSpan={columnas.length} className="px-4 py-3">
                            <div className="bg-white rounded-lg border border-indigo-200 shadow-sm p-4">
                              <div className="flex items-center justify-between mb-3">
                                <h4 className="text-sm font-semibold text-indigo-800">
                                  📦 Lotes del contrato {fila.numero_contrato} ({fila.lotes.length} lotes)
                                </h4>
                                <span className="text-xs text-indigo-600 bg-indigo-100 px-2 py-1 rounded-full">
                                  Seguimiento completo: Entrada → Consumo
                                </span>
                              </div>
                              <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                  <thead className="bg-indigo-100">
                                    <tr>
                                      <th className="px-3 py-2 text-left text-xs font-semibold text-indigo-800">#</th>
                                      <th className="px-3 py-2 text-left text-xs font-semibold text-indigo-800">Lote</th>
                                      <th className="px-3 py-2 text-left text-xs font-semibold text-indigo-800">Producto</th>
                                      <th className="px-3 py-2 text-left text-xs font-semibold text-indigo-800">Presentación</th>
                                      <th className="px-3 py-2 text-right text-xs font-semibold text-indigo-800">Inicial</th>
                                      <th className="px-3 py-2 text-right text-xs font-semibold text-indigo-800">Actual</th>
                                      <th className="px-3 py-2 text-right text-xs font-semibold text-indigo-800">Consumido</th>
                                      <th className="px-3 py-2 text-center text-xs font-semibold text-indigo-800">Entradas</th>
                                      <th className="px-3 py-2 text-center text-xs font-semibold text-indigo-800">Salidas</th>
                                      <th className="px-3 py-2 text-left text-xs font-semibold text-indigo-800">Caducidad</th>
                                      <th className="px-3 py-2 text-left text-xs font-semibold text-indigo-800">Centro</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-indigo-100">
                                    {fila.lotes.map((lote, loteIdx) => (
                                      <tr key={loteIdx} className="hover:bg-indigo-50/50">
                                        <td className="px-3 py-2 text-gray-500">{loteIdx + 1}</td>
                                        <td className="px-3 py-2 text-indigo-700 font-mono text-xs">{lote.numero_lote}</td>
                                        <td className="px-3 py-2 text-gray-800 font-medium">{lote.producto_clave} - {lote.producto_nombre}</td>
                                        <td className="px-3 py-2 text-gray-600 text-xs">{lote.presentacion || '-'}</td>
                                        <td className="px-3 py-2 text-gray-800 text-right">{(lote.cantidad_inicial || 0).toLocaleString()}</td>
                                        <td className="px-3 py-2 text-right font-semibold">
                                          <span className={lote.cantidad_actual === 0 ? 'text-red-600' : 'text-green-700'}>
                                            {(lote.cantidad_actual || 0).toLocaleString()}
                                          </span>
                                        </td>
                                        <td className="px-3 py-2 text-orange-700 text-right">{(lote.cantidad_consumida || 0).toLocaleString()}</td>
                                        <td className="px-3 py-2 text-center">
                                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-800">
                                            📥 {lote.movimientos_entrada || 0}
                                          </span>
                                        </td>
                                        <td className="px-3 py-2 text-center">
                                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-800">
                                            📤 {lote.movimientos_salida || 0}
                                          </span>
                                        </td>
                                        <td className="px-3 py-2 text-gray-600 text-xs">{lote.fecha_caducidad || '-'}</td>
                                        <td className="px-3 py-2 text-gray-600 text-xs">{lote.centro || 'Almacén Central'}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                  <tfoot className="bg-indigo-100/50">
                                    <tr className="font-semibold">
                                      <td colSpan="4" className="px-3 py-2 text-right text-xs text-indigo-800">Totales del contrato:</td>
                                      <td className="px-3 py-2 text-right text-indigo-800">{(fila.cantidad_inicial || 0).toLocaleString()}</td>
                                      <td className="px-3 py-2 text-right text-indigo-800">{(fila.cantidad_actual || 0).toLocaleString()}</td>
                                      <td className="px-3 py-2 text-right text-orange-700">{(fila.cantidad_consumida || 0).toLocaleString()}</td>
                                      <td className="px-3 py-2 text-center text-green-700">{fila.movimientos_entrada || 0}</td>
                                      <td className="px-3 py-2 text-center text-red-700">{fila.movimientos_salida || 0}</td>
                                      <td colSpan="2" className="px-3 py-2 text-xs text-indigo-600">
                                        {fila.porcentaje_uso || 0}% consumido
                                      </td>
                                    </tr>
                                  </tfoot>
                                </table>
                              </div>
                              {/* Información adicional de tracking */}
                              <div className="mt-3 flex flex-wrap gap-3 text-xs text-gray-600">
                                <span className="flex items-center gap-1 bg-gray-100 px-2 py-1 rounded">
                                  📅 Primera entrada: <strong>{fila.fecha_primera_entrada || '-'}</strong>
                                </span>
                                <span className="flex items-center gap-1 bg-gray-100 px-2 py-1 rounded">
                                  📅 Última salida: <strong>{fila.fecha_ultima_salida || '-'}</strong>
                                </span>
                                <span className="flex items-center gap-1 bg-gray-100 px-2 py-1 rounded">
                                  💰 Valor total: <strong>${(fila.valor_total || 0).toLocaleString()}</strong>
                                </span>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
            </div>
          )}
        </div>

        {/* Controles de Paginación */}
        {datos.length > 0 && (
          <div className="p-4 md:p-5 bg-gray-50/50 border-t border-gray-100 flex flex-col sm:flex-row items-center justify-between gap-3">
            <p className="text-xs text-gray-400 font-medium">
              Página {paginaActual} de {totalPaginas} · {datos.length} registros
            </p>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setPaginaActual(1)}
                disabled={paginaActual === 1}
                className="p-2 rounded-lg bg-white border border-gray-200 text-gray-500 hover:bg-gray-50 hover:border-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transition-all text-xs"
                title="Primera página"
              >
                <FaAngleDoubleLeft />
              </button>
              <button
                onClick={() => setPaginaActual(prev => Math.max(1, prev - 1))}
                disabled={paginaActual === 1}
                className="p-2 rounded-lg bg-white border border-gray-200 text-gray-500 hover:bg-gray-50 hover:border-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transition-all text-xs"
                title="Página anterior"
              >
                <FaChevronLeft />
              </button>
              
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
                      className={`w-8 h-8 rounded-lg text-xs font-medium transition-all ${
                        paginaActual === pageNum
                          ? 'bg-[var(--color-primary)] text-white shadow-sm'
                          : 'bg-white border border-gray-200 text-gray-500 hover:bg-gray-50 hover:border-gray-300'
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
                className="p-2 rounded-lg bg-white border border-gray-200 text-gray-500 hover:bg-gray-50 hover:border-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transition-all text-xs"
                title="Página siguiente"
              >
                <FaChevronRight />
              </button>
              {/* Última página */}
              <button
                onClick={() => setPaginaActual(totalPaginas)}
                disabled={paginaActual === totalPaginas}
                className="p-2 rounded-lg bg-white border border-gray-200 text-gray-500 hover:bg-gray-50 hover:border-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transition-all text-xs"
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
