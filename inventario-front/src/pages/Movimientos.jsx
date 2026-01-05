import React, { useEffect, useMemo, useState, useRef, useCallback } from "react";
import { useLocation } from "react-router-dom";
import { toast } from "react-hot-toast";
import Pagination from "../components/Pagination";
import SalidaMasiva from "../components/SalidaMasiva";
import { movimientosAPI, productosAPI, centrosAPI, lotesAPI, salidaMasivaAPI, descargarArchivo } from "../services/api";
import { usePermissions } from "../hooks/usePermissions";
import { FaFilter, FaChevronDown, FaChevronRight, FaExchangeAlt, FaFileExcel, FaFilePdf, FaSpinner, FaInfoCircle, FaExclamationTriangle, FaTruck, FaLayerGroup, FaList, FaFileDownload, FaCheckCircle, FaClipboardCheck, FaTrash } from "react-icons/fa";
import { COLORS } from "../constants/theme";

const PAGE_SIZE = 25;

const Movimientos = () => {
  const location = useLocation();
  const highlightId = location.state?.highlightId;
  const highlightRef = useRef(null);
  const { user, permisos, getRolPrincipal } = usePermissions();
  
  // Detectar si puede ver todos los centros o solo el suyo
  const rolPrincipal = getRolPrincipal();
  const puedeVerTodosCentros = ['ADMIN', 'FARMACIA', 'VISTA'].includes(rolPrincipal);
  const centroUsuario = user?.centro?.id || user?.centro || user?.centro_id;
  const centroNombre = user?.centro?.nombre || user?.centro_nombre || null;
  const esCentroUser = rolPrincipal === 'CENTRO';
  
  // ISS-MEDICO FIX v2: Detectar si el usuario es médico específicamente
  const esMedico = (user?.rol_efectivo || user?.rol || '').toLowerCase() === 'medico';
  
  // Permisos específicos para acciones (usando permisos granulares)
  // ISS-MEDICO FIX v2: Médicos pueden registrar movimientos de SALIDA
  const puedeRegistrarMovimiento = permisos?.crearMovimiento === true || esMedico;
  const puedeExportar = permisos?.exportarMovimientos === true;
  
  const [movimientos, setMovimientos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState({ entradas: 0, salidas: 0, balance: 0 });
  const [expandedId, setExpandedId] = useState(highlightId || null);
  const [vistaAgrupada, setVistaAgrupada] = useState(true); // Por defecto agrupada
  const [gruposExpandidos, setGruposExpandidos] = useState(new Set());

  // Filtros aplicados (los que realmente se envían al backend)
  // Si el usuario tiene centro asignado (no es admin/farmacia), pre-filtrar por su centro
  const centroInicial = !puedeVerTodosCentros && centroUsuario ? centroUsuario.toString() : "";
  
  const [filtrosAplicados, setFiltrosAplicados] = useState({
    fecha_inicio: "",
    fecha_fin: "",
    tipo: "",
    subtipo_salida: "",
    producto: "",
    centro: centroInicial,
    lote: "",
    search: "",
    estado_confirmacion: "",
  });
  
  // Filtros en edición (estado local de los inputs)
  const [filtros, setFiltros] = useState({
    fecha_inicio: "",
    fecha_fin: "",
    tipo: "",
    subtipo_salida: "",
    producto: "",
    centro: centroInicial,
    lote: "",
    search: "",
    estado_confirmacion: "",
  });

  const [productos, setProductos] = useState([]);
  const [centros, setCentros] = useState([]);
  const [lotes, setLotes] = useState([]);
  const [lotesDisponibles, setLotesDisponibles] = useState([]);

  // Formulario de registro
  // ISS-FIX: Movimientos simplificados - tipo FIJO a "salida"
  // Subtipo: "transferencia" para Farmacia/Admin, "receta" para Médico (único permitido)
  const getSubtipoInicial = () => {
    if (puedeVerTodosCentros) return "transferencia";
    if (esMedico) return "receta";  // Médicos SOLO pueden hacer dispensación por receta
    return "consumo_interno";
  };
  
  const [formData, setFormData] = useState({
    lote: "",
    tipo: "salida",  // FIJO: Solo salidas
    cantidad: "",
    centro: "",
    observaciones: "",
    // Subtipo depende del rol: transferencia para farmacia, receta para médico
    subtipo_salida: puedeVerTodosCentros ? "transferencia" : (esMedico ? "receta" : "consumo_interno"),
    numero_expediente: "",
  });
  const [productoFiltro, setProductoFiltro] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [exporting, setExporting] = useState(null); // 'pdf' | 'excel' | null
  const [showFiltersMenu, setShowFiltersMenu] = useState(false);
  const [showSalidaMasiva, setShowSalidaMasiva] = useState(false); // Modal salida masiva
  
  // Detectar si es usuario Farmacia (puede usar salida masiva)
  const esFarmacia = rolPrincipal === 'FARMACIA' || rolPrincipal === 'ADMIN';

  const columnas = useMemo(
    () => ["producto", "tipo", "cantidad", "centro", "fecha"],
    []
  );

  const cargarCatalogos = useCallback(async () => {
    try {
      // Cargar productos (todos pueden ver el catálogo de productos)
      const prodResp = await productosAPI.getAll({ page_size: 500, ordering: "descripcion", activo: true });
      setProductos(prodResp.data.results || prodResp.data || []);
      
      // Cargar centros según permisos
      if (puedeVerTodosCentros) {
        // Admin/Farmacia/Vista: ver todos los centros
        const centroResp = await centrosAPI.getAll({ page_size: 100, ordering: "nombre", activo: true });
        setCentros(centroResp.data.results || centroResp.data || []);
      } else if (centroUsuario && user?.centro) {
        // Usuario de centro: usar info del usuario directamente (evita llamada API)
        setCentros([user.centro]);
      } else {
        setCentros([]);
      }
      
      // ISS-FIX (lotes-central): Para Farmacia/Admin, cargar lotes de Farmacia Central
      // Para usuarios de centro/médico, cargar lotes de su centro (los que farmacia les ha enviado)
      const lotesParams = { 
        page_size: 500, 
        ordering: "-fecha_caducidad", 
        activo: true,  // ISS-FIX: Solo lotes activos
        con_stock: true,  // ISS-FIX: Solo lotes con stock > 0
      };
      
      // ISS-FIX: Farmacia/Admin ven lotes de farmacia central para transferencias
      if (puedeVerTodosCentros) {
        lotesParams.centro = "central";  // Farmacia central
      } else if (centroUsuario) {
        // Usuario de centro/médico ve lotes de su centro (los surtidos por farmacia)
        lotesParams.centro = centroUsuario;
      }
      
      const lotesResp = await lotesAPI.getAll(lotesParams);
      const lotesData = lotesResp.data.results || lotesResp.data || [];
      setLotes(lotesData);
      // ISS-FIX: El filtro ya viene del backend, solo confirmar cantidad > 0
      setLotesDisponibles(lotesData.filter(l => l.cantidad_actual > 0));
    } catch (err) {
      console.warn("No se pudieron cargar catálogos", err.message);
    }
  }, [puedeVerTodosCentros, centroUsuario, user?.centro]);

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

  // Función para extraer el grupo de salida del motivo/observaciones
  const extraerGrupoSalida = (mov) => {
    const motivo = mov.observaciones || mov.motivo || '';
    const match = motivo.match(/\[(SAL-[^\]]+)\]/);
    return match ? match[1] : null;
  };
  
  // Función para verificar si un movimiento está confirmado
  const estaConfirmado = (mov) => {
    const motivo = mov.observaciones || mov.motivo || '';
    return motivo.includes('[CONFIRMADO]');
  };

  // Agrupar movimientos por grupo de salida
  const movimientosAgrupados = useMemo(() => {
    if (!vistaAgrupada) return null;
    
    const grupos = new Map();
    const sinGrupo = [];
    
    movimientos.forEach(mov => {
      const grupoId = extraerGrupoSalida(mov);
      if (grupoId && mov.tipo === 'salida' && mov.subtipo_salida === 'transferencia') {
        if (!grupos.has(grupoId)) {
          grupos.set(grupoId, {
            id: grupoId,
            items: [],
            centro_nombre: mov.centro_nombre || 'N/A',
            fecha: mov.fecha || mov.fecha_movimiento,
            usuario_nombre: mov.usuario_nombre || 'Sistema',
            totalCantidad: 0,
            confirmado: estaConfirmado(mov), // Detectar si está confirmado
          });
        }
        const grupo = grupos.get(grupoId);
        grupo.items.push(mov);
        grupo.totalCantidad += Math.abs(mov.cantidad || 0);
      } else {
        sinGrupo.push(mov);
      }
    });
    
    // Convertir a array y ordenar por fecha descendente
    const gruposArray = Array.from(grupos.values()).sort((a, b) => 
      new Date(b.fecha) - new Date(a.fecha)
    );
    
    return { grupos: gruposArray, sinGrupo };
  }, [movimientos, vistaAgrupada]);

  // Toggle para expandir/colapsar grupo
  const toggleGrupo = (grupoId) => {
    setGruposExpandidos(prev => {
      const newSet = new Set(prev);
      if (newSet.has(grupoId)) {
        newSet.delete(grupoId);
      } else {
        newSet.add(grupoId);
      }
      return newSet;
    });
  };

  const cargarMovimientos = useCallback(async () => {
    setLoading(true);
    try {
      // Crear copia de filtros sin estado_confirmacion (se filtra en frontend)
      const { estado_confirmacion, ...filtrosBackend } = filtrosAplicados;
      const params = {
        page,
        page_size: PAGE_SIZE,
        ordering: "-fecha",
        ...filtrosBackend,
      };
      // Limpiar parámetros vacíos
      Object.keys(params).forEach(key => {
        if (params[key] === "" || params[key] === null || params[key] === undefined) {
          delete params[key];
        }
      });
      const response = await movimientosAPI.getAll(params);
      let data = response.data?.results || response.data || [];
      // Agregar campo 'confirmado' a cada movimiento
      let dataConConfirmado = (Array.isArray(data) ? data : []).map(mov => ({
        ...mov,
        confirmado: estaConfirmado(mov)
      }));
      
      // Filtrar por estado de confirmación en frontend
      if (estado_confirmacion === 'confirmado') {
        dataConConfirmado = dataConConfirmado.filter(mov => mov.confirmado);
      } else if (estado_confirmacion === 'pendiente') {
        dataConConfirmado = dataConConfirmado.filter(mov => !mov.confirmado && mov.tipo === 'salida');
      }
      
      setMovimientos(dataConConfirmado);
      setTotal(response.data?.count || data.length || 0);
      calcularStats(dataConConfirmado);
    } catch (err) {
      toast.error(err.response?.data?.detail || "No se pudieron cargar los movimientos");
    } finally {
      setLoading(false);
    }
  }, [page, filtrosAplicados]);

  useEffect(() => {
    cargarCatalogos();
  }, [cargarCatalogos]);

  // Estado para saber si el centro del usuario ya fue resuelto (evita carga prematura)
  const [centroResuelto, setCentroResuelto] = useState(puedeVerTodosCentros || !!centroInicial);

  // Sincronizar filtro de centro cuando el usuario se hidrata tardíamente
  // Esto evita que usuarios de centro vean movimientos de otros centros durante carga inicial
  useEffect(() => {
    if (puedeVerTodosCentros) {
      // Admin/Farmacia/Vista pueden ver todo, marcar como resuelto
      setCentroResuelto(true);
    } else if (centroUsuario) {
      // Usuario de centro: sincronizar filtro y marcar resuelto
      const centroStr = centroUsuario.toString();
      if (filtros.centro !== centroStr) {
        setFiltros(prev => ({ ...prev, centro: centroStr }));
      }
      if (filtrosAplicados.centro !== centroStr) {
        setFiltrosAplicados(prev => ({ ...prev, centro: centroStr }));
      }
      setCentroResuelto(true);
    }
    // Si no es admin y aún no tiene centro, seguir esperando (centroResuelto = false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [centroUsuario, puedeVerTodosCentros]);

  // Solo recargar cuando cambia la página o los filtros APLICADOS Y el centro está resuelto
  useEffect(() => {
    if (centroResuelto) {
      cargarMovimientos();
    }
  }, [cargarMovimientos, centroResuelto]);

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
    setFormData(prev => {
      const newState = { ...prev, [field]: value };
      
      // MEJORA FLUJO 5: Limpiar campos de salida cuando cambie el tipo
      if (field === "tipo" && value !== "salida") {
        newState.subtipo_salida = "";
        newState.numero_expediente = "";
      }
      // Si cambia subtipo y ya no es receta, limpiar expediente
      if (field === "subtipo_salida" && value !== "receta") {
        newState.numero_expediente = "";
      }
      
      return newState;
    });
  };

  const getLoteLabel = (lote) => {
    const producto = productos.find(p => p.id === lote.producto);
    const fechaCad = lote.fecha_caducidad ? new Date(lote.fecha_caducidad).toLocaleDateString() : 'S/F';
    return `${lote.numero_lote} - ${producto?.nombre?.substring(0, 25) || 'Producto'} (${lote.cantidad_actual} uds, Cad: ${fechaCad})`;
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
    
    // Validar centro destino obligatorio para transferencias
    if (puedeVerTodosCentros && !formData.centro) {
      toast.error("Selecciona el centro destino para la transferencia");
      return;
    }

    const loteSeleccionado = lotes.find(l => l.id === parseInt(formData.lote));
    if (loteSeleccionado && Number(formData.cantidad) > loteSeleccionado.cantidad_actual) {
      toast.error(`Inventario insuficiente. Disponible: ${loteSeleccionado.cantidad_actual}`);
      return;
    }

    // Determinar centro final - para usuarios de centro, se pone su propio centro como referencia
    const centroFinal = !puedeVerTodosCentros && centroUsuario 
      ? parseInt(centroUsuario) 
      : (formData.centro ? parseInt(formData.centro) : null);

    // Validar centro para transferencias de farmacia
    if (puedeVerTodosCentros && !centroFinal) {
      toast.error("Debe seleccionar un centro destino");
      return;
    }

    // Validar expediente para recetas
    if (!puedeVerTodosCentros && formData.subtipo_salida === 'receta' && !formData.numero_expediente?.trim()) {
      toast.error("Debe ingresar el número de expediente para recetas");
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        lote: parseInt(formData.lote),
        tipo: "salida",
        cantidad: Number(formData.cantidad),
        centro: centroFinal,
        observaciones: formData.observaciones,
        // Subtipo según rol: transferencia para farmacia, lo que elija el centro para centro
        subtipo_salida: puedeVerTodosCentros ? "transferencia" : formData.subtipo_salida,
      };
      
      // Agregar expediente si es receta
      if (formData.subtipo_salida === 'receta' && formData.numero_expediente) {
        payload.numero_expediente = formData.numero_expediente.trim();
      }
      
      await movimientosAPI.create(payload);
      toast.success("Salida registrada exitosamente");
      setFormData({
        lote: "",
        tipo: "salida",
        cantidad: "",
        centro: "",
        observaciones: "",
        // Reset subtipo según rol: transferencia para farmacia, receta para médico, consumo para otros
        subtipo_salida: puedeVerTodosCentros ? "transferencia" : (esMedico ? "receta" : "consumo_interno"),
        numero_expediente: "",
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

  // Detectar si hay filtros pendientes de aplicar (mover antes de exportar)
  const hayFiltrosPendientes = useMemo(() => {
    return JSON.stringify(filtros) !== JSON.stringify(filtrosAplicados);
  }, [filtros, filtrosAplicados]);
  
  // Detectar si hay filtros activos
  const hayFiltrosActivos = useMemo(() => {
    return Object.values(filtrosAplicados).some(v => v !== "");
  }, [filtrosAplicados]);

  const exportarExcel = async () => {
    if (exporting) return; // Evitar exportaciones simultáneas
    
    setExporting('excel');
    try {
      // Sanitizar filtros: eliminar valores vacíos antes de enviar
      const filtrosLimpios = Object.fromEntries(
        Object.entries(filtrosAplicados).filter(([, v]) => v !== "" && v !== null && v !== undefined)
      );
      const response = await movimientosAPI.exportarExcel(filtrosLimpios);
      descargarArchivo(response, `movimientos_${new Date().toISOString().split("T")[0]}.xlsx`);
      toast.success("Excel generado");
    } catch (err) {
      toast.error(err.response?.data?.detail || "No se pudo exportar");
    } finally {
      setExporting(null);
    }
  };

  const exportarPdf = async () => {
    if (exporting) return; // Evitar exportaciones simultáneas
    
    setExporting('pdf');
    try {
      // Sanitizar filtros: eliminar valores vacíos antes de enviar
      const filtrosLimpios = Object.fromEntries(
        Object.entries(filtrosAplicados).filter(([, v]) => v !== "" && v !== null && v !== undefined)
      );
      const response = await movimientosAPI.exportarPdf(filtrosLimpios);
      descargarArchivo(response, `movimientos_${new Date().toISOString().split("T")[0]}.pdf`);
      toast.success("PDF generado");
    } catch (err) {
      toast.error(err.response?.data?.detail || "No se pudo generar el PDF");
    } finally {
      setExporting(null);
    }
  };

  // Descargar recibo de salida con campos de firma
  const descargarReciboSalida = async (movimiento) => {
    try {
      toast.loading("Generando recibo...", { id: "recibo" });
      const response = await movimientosAPI.getReciboSalida(movimiento.id);
      const fecha = new Date(movimiento.fecha || movimiento.fecha_movimiento).toISOString().split("T")[0];
      // ISS-FIX: Usar response.data ya que axios devuelve los datos en .data
      descargarArchivo(response.data || response, `recibo_salida_${movimiento.id}_${fecha}.pdf`);
      toast.success("Recibo generado", { id: "recibo" });
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.response?.data?.detail || err.message || "No se pudo generar el recibo";
      toast.error(errorMsg, { id: "recibo" });
      console.error("Error generando recibo:", err);
    }
  };

  // Descargar recibo de entrega finalizada (con sello ENTREGADO en lugar de firmas)
  const descargarReciboFinalizado = async (movimiento) => {
    try {
      toast.loading("Generando comprobante de entrega...", { id: "recibo-final" });
      const response = await movimientosAPI.getReciboSalida(movimiento.id, true);
      const fecha = new Date(movimiento.fecha || movimiento.fecha_movimiento).toISOString().split("T")[0];
      // ISS-FIX: Usar response.data ya que axios devuelve los datos en .data
      descargarArchivo(response.data || response, `comprobante_entrega_${movimiento.id}_${fecha}.pdf`);
      toast.success("Comprobante generado", { id: "recibo-final" });
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.response?.data?.detail || err.message || "No se pudo generar el comprobante";
      toast.error(errorMsg, { id: "recibo-final" });
      console.error("Error generando comprobante:", err);
    }
  };

  // Descargar hoja de entrega para grupo de salida masiva
  const descargarHojaEntregaGrupo = async (grupoId) => {
    try {
      toast.loading("Generando hoja de entrega...", { id: "hoja-grupo" });
      const response = await salidaMasivaAPI.hojaEntregaPdf(grupoId, false);
      descargarArchivo(response.data, `Hoja_Entrega_${grupoId}.pdf`);
      toast.success("Hoja de entrega descargada", { id: "hoja-grupo" });
    } catch (err) {
      toast.error("No se pudo generar la hoja de entrega", { id: "hoja-grupo" });
      console.error("Error generando hoja:", err);
    }
  };

  // Descargar comprobante de entrega para grupo de salida masiva
  const descargarComprobanteGrupo = async (grupoId) => {
    try {
      toast.loading("Generando comprobante de entrega...", { id: "comp-grupo" });
      const response = await salidaMasivaAPI.hojaEntregaPdf(grupoId, true);
      descargarArchivo(response.data, `Comprobante_Entrega_${grupoId}.pdf`);
      toast.success("Comprobante de entrega descargado", { id: "comp-grupo" });
    } catch (err) {
      toast.error("No se pudo generar el comprobante", { id: "comp-grupo" });
      console.error("Error generando comprobante:", err);
    }
  };
  
  // Confirmar entrega de grupo de salida masiva
  const [confirmandoGrupo, setConfirmandoGrupo] = useState(null);
  
  // Estado para confirmar entregas individuales
  const [confirmandoMovimiento, setConfirmandoMovimiento] = useState(null);
  const [cancelandoGrupo, setCancelandoGrupo] = useState(null);
  const [confirmCancelarGrupo, setConfirmCancelarGrupo] = useState(null);
  
  const confirmarEntregaGrupo = async (grupoId) => {
    setConfirmandoGrupo(grupoId);
    try {
      toast.loading("Confirmando entrega...", { id: "confirmar-grupo" });
      await salidaMasivaAPI.confirmarEntrega(grupoId);
      toast.success("Entrega confirmada exitosamente", { id: "confirmar-grupo" });
      // Recargar movimientos para actualizar el estado
      cargarMovimientos();
    } catch (err) {
      const msg = err.response?.data?.message || "No se pudo confirmar la entrega";
      toast.error(msg, { id: "confirmar-grupo" });
      console.error("Error confirmando entrega:", err);
    } finally {
      setConfirmandoGrupo(null);
    }
  };
  
  // Cancelar salida masiva NO confirmada (devuelve stock al inventario)
  const cancelarSalidaGrupo = async (grupoId) => {
    setCancelandoGrupo(grupoId);
    try {
      toast.loading("Cancelando salida y devolviendo stock...", { id: "cancelar-grupo" });
      const response = await salidaMasivaAPI.cancelar(grupoId);
      const itemsDevueltos = response.data?.items_devueltos?.length || 0;
      toast.success(`Salida cancelada. ${itemsDevueltos} productos devueltos al inventario.`, { id: "cancelar-grupo" });
      // Recargar movimientos para actualizar el estado
      cargarMovimientos();
    } catch (err) {
      const msg = err.response?.data?.message || "No se pudo cancelar la salida";
      toast.error(msg, { id: "cancelar-grupo" });
      console.error("Error cancelando salida:", err);
    } finally {
      setCancelandoGrupo(null);
      setConfirmCancelarGrupo(null);
    }
  };
  
  // Confirmar entrega individual de un movimiento
  const confirmarEntregaIndividual = async (movimientoId) => {
    setConfirmandoMovimiento(movimientoId);
    try {
      toast.loading("Confirmando entrega...", { id: "confirmar-individual" });
      await movimientosAPI.confirmarEntrega(movimientoId);
      toast.success("Entrega confirmada exitosamente", { id: "confirmar-individual" });
      // Recargar movimientos para actualizar el estado
      cargarMovimientos();
    } catch (err) {
      const msg = err.response?.data?.message || "No se pudo confirmar la entrega";
      toast.error(msg, { id: "confirmar-individual" });
      console.error("Error confirmando entrega individual:", err);
    } finally {
      setConfirmandoMovimiento(null);
    }
  };

  // Actualiza solo el estado local de filtros (sin disparar recarga)
  const handleFiltro = (field, value) => {
    // Protección: usuarios de centro no pueden cambiar el filtro de centro
    if (field === 'centro' && !puedeVerTodosCentros && centroUsuario) {
      return; // Ignorar cambios al filtro de centro para usuarios restringidos
    }
    setFiltros((prev) => {
      const newState = { ...prev, [field]: value };
      // Limpiar subtipo_salida si el tipo cambia a algo que no es salida
      if (field === 'tipo' && value !== 'salida' && value !== '') {
        newState.subtipo_salida = '';
      }
      return newState;
    });
  };

  // Validar y aplicar filtros (dispara recarga)
  const aplicarFiltros = () => {
    // Validar rango de fechas
    if (filtros.fecha_inicio && filtros.fecha_fin) {
      const inicio = new Date(filtros.fecha_inicio);
      const fin = new Date(filtros.fecha_fin);
      if (inicio > fin) {
        toast.error("La fecha de inicio debe ser menor o igual a la fecha de fin");
        return;
      }
    }
    
    // Protección: forzar centro del usuario si no tiene permisos globales
    const filtrosFinales = { ...filtros };
    if (!puedeVerTodosCentros && centroUsuario) {
      filtrosFinales.centro = centroUsuario.toString();
    }
    
    setPage(1);
    setFiltrosAplicados(filtrosFinales);
  };

  const limpiarFiltros = () => {
    // Mantener filtro de centro para usuarios que no pueden ver todos
    const centroFijo = !puedeVerTodosCentros && centroUsuario ? centroUsuario.toString() : "";
    const filtrosVacios = {
      fecha_inicio: "",
      fecha_fin: "",
      tipo: "",
      subtipo_salida: "",
      producto: "",
      centro: centroFijo,
      lote: "",
      search: "",
      estado_confirmacion: "",
    };
    setFiltros(filtrosVacios);
    setFiltrosAplicados(filtrosVacios);
    setPage(1);
  };

  return (
    <div className="space-y-6 p-4 sm:p-6">
      {/* Header con gradiente institucional */}
      <div
        className="rounded-2xl p-6 text-white shadow-lg bg-theme-gradient"
      >
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="bg-white/20 p-3 rounded-full">
              <FaExchangeAlt size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold">Movimientos de Inventario</h1>
              <p className="text-white/80 text-sm">
                {hayFiltrosActivos ? 'Filtrados:' : 'Total:'} {total} movimientos
              </p>
            </div>
          </div>
          {hayFiltrosActivos && (
            <span className="bg-white/20 px-4 py-1 rounded-full text-sm font-semibold">
              {Object.values(filtrosAplicados).filter(v => v !== "").length} filtros activos
            </span>
          )}
          <div className="flex flex-wrap gap-3">
            {/* Botón Salida Masiva - Solo Farmacia */}
            {esFarmacia && (
              <button
                onClick={() => setShowSalidaMasiva(true)}
                className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition bg-white text-rose-700 hover:bg-rose-50"
                title="Salida masiva a centros"
              >
                <FaTruck />
                Salida Masiva
              </button>
            )}
            {/* Toggle Vista Agrupada/Individual */}
            <button
              onClick={() => setVistaAgrupada(!vistaAgrupada)}
              className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition ${
                vistaAgrupada 
                  ? 'bg-white text-rose-700 hover:bg-rose-50' 
                  : 'bg-white/20 text-white hover:bg-white/30'
              }`}
              title={vistaAgrupada ? "Ver movimientos individuales" : "Agrupar salidas masivas"}
            >
              {vistaAgrupada ? <FaLayerGroup /> : <FaList />}
              {vistaAgrupada ? 'Agrupado' : 'Individual'}
            </button>
            {/* TEMPORALMENTE DESHABILITADO: Exportar PDF/Excel 
            {puedeExportar && (
              <>
                <button
                  onClick={exportarPdf}
                  disabled={loading || exporting !== null}
                  className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{
                    background: 'rgba(255,255,255,0.2)',
                    border: '1px solid rgba(255,255,255,0.4)'
                  }}
                  title="Exportar a PDF"
                >
                  {exporting === 'pdf' ? <FaSpinner className="animate-spin" /> : <FaFilePdf />}
                  {exporting === 'pdf' ? 'Generando...' : 'PDF'}
                </button>
                <button
                  onClick={exportarExcel}
                  disabled={loading || exporting !== null}
                  className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{
                    background: 'rgba(255,255,255,0.2)',
                    border: '1px solid rgba(255,255,255,0.4)'
                  }}
                  title="Exportar a Excel"
                >
                  {exporting === 'excel' ? <FaSpinner className="animate-spin" /> : <FaFileExcel />}
                  {exporting === 'excel' ? 'Generando...' : 'Excel'}
                </button>
              </>
            )}
            */}
          </div>
        </div>
      </div>

      {/* ISS-FIX: Banner para usuarios CENTRO indicando que solo ven movimientos de su centro */}
      {esCentroUser && centroNombre && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center gap-3">
          <div className="bg-blue-100 p-2 rounded-lg">
            <FaInfoCircle className="text-blue-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-blue-800">
              Movimientos de: {centroNombre}
            </p>
            <p className="text-xs text-blue-600">
              Estás viendo solo los movimientos relacionados a tu centro.
            </p>
          </div>
        </div>
      )}

      {/* ISS-CENTRO: Aviso si usuario de centro no tiene centro asignado */}
      {esCentroUser && !centroUsuario && (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-lg">
          <div className="flex items-center">
            <FaExclamationTriangle className="text-yellow-400 mr-3 text-xl" />
            <div>
              <h3 className="text-lg font-semibold text-yellow-800">Centro no asignado</h3>
              <p className="text-yellow-700 mt-1">
                Tu cuenta está configurada como usuario de Centro pero no tienes un centro asignado.
                Por favor contacta al administrador para que te asigne un centro.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          {/* Formulario de registro - solo para admin/farmacia */}
          {puedeRegistrarMovimiento ? (
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
                      {p.clave} - {p.nombre}
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
                  <div className="text-xs p-2 bg-orange-50 border border-orange-200 rounded">
                    <p className="text-orange-700 font-medium">No hay lotes disponibles</p>
                    {!puedeVerTodosCentros && (
                      <p className="text-orange-600 mt-1">
                        El inventario de tu centro está vacío. Contacta a Farmacia Central para solicitar surtimiento.
                      </p>
                    )}
                  </div>
                )}
                {/* ISS-MEDICO FIX v2: Mostrar stock disponible del lote seleccionado */}
                {formData.lote && (() => {
                  const loteInfo = lotesDisponibles.find(l => l.id === parseInt(formData.lote));
                  const productoInfo = loteInfo ? productos.find(p => p.id === loteInfo.producto) : null;
                  if (!loteInfo) return null;
                  return (
                    <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-center gap-2 text-blue-800">
                        <FaInfoCircle />
                        <span className="font-semibold">Stock disponible</span>
                      </div>
                      <div className="mt-1 text-sm text-blue-700">
                        <div><strong>Producto:</strong> {productoInfo?.nombre || 'N/A'}</div>
                        <div><strong>Lote:</strong> {loteInfo.numero_lote}</div>
                        <div><strong>Disponible:</strong> <span className="font-bold text-lg">{loteInfo.cantidad_actual}</span> unidades</div>
                        {loteInfo.fecha_caducidad && (
                          <div><strong>Caducidad:</strong> {new Date(loteInfo.fecha_caducidad).toLocaleDateString()}</div>
                        )}
                      </div>
                    </div>
                  );
                })()}
              </div>

              {/* Tipo FIJO: Salida - Solo informativo */}
              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700">Tipo de Movimiento</label>
                {puedeVerTodosCentros ? (
                  <>
                    <div className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-700 font-medium">
                      <FaTruck className="inline mr-2 text-blue-600" />
                      Salida / Transferencia a Centro
                    </div>
                    <p className="text-xs text-gray-500">
                      Las salidas desde Almacén Central se registran como transferencias a centros penitenciarios.
                    </p>
                  </>
                ) : esMedico ? (
                  // MÉDICOS: Solo pueden hacer dispensación por receta
                  <>
                    <div className="w-full rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-blue-700 font-medium">
                      💊 Dispensación por receta
                    </div>
                    <p className="text-xs text-gray-500">
                      Como médico, solo puedes registrar dispensaciones por receta médica.
                    </p>
                  </>
                ) : (
                  // OTROS USUARIOS DE CENTRO: Todas las opciones de salida
                  <>
                    <select
                      value={formData.subtipo_salida}
                      onChange={(e) => handleFormChange("subtipo_salida", e.target.value)}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    >
                      <option value="consumo_interno">🏥 Consumo interno</option>
                      <option value="receta">💊 Dispensación por receta</option>
                      <option value="merma">📉 Merma / Pérdida</option>
                      <option value="caducidad">⏰ Caducidad</option>
                    </select>
                    <p className="text-xs text-gray-500">
                      Selecciona el motivo de la salida de inventario.
                    </p>
                  </>
                )}
              </div>

              {/* Centro destino - Solo para Farmacia/Admin */}
              {puedeVerTodosCentros && (
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-gray-700">Centro Destino <span className="text-red-500">*</span></label>
                  <select
                    value={formData.centro}
                    onChange={(e) => handleFormChange("centro", e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  >
                    <option value="">-- Seleccione centro destino --</option>
                    {centros.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nombre}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500">
                    Seleccione el centro penitenciario al que se transferirá el medicamento.
                  </p>
                </div>
              )}

              {/* Número de expediente - Solo para recetas */}
              {!puedeVerTodosCentros && formData.subtipo_salida === 'receta' && (
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-gray-700">No. Expediente <span className="text-red-500">*</span></label>
                  <input
                    type="text"
                    value={formData.numero_expediente}
                    onChange={(e) => handleFormChange("numero_expediente", e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Número de expediente del paciente"
                    required
                  />
                </div>
              )}

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

              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700">
                  Observaciones
                </label>
                <textarea
                  value={formData.observaciones}
                  onChange={(e) => handleFormChange("observaciones", e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Notas adicionales (opcional)..."
                  rows={2}
                  required={esMedico}
                />
                {esMedico && (
                  <p className="text-xs text-blue-600">
                    <FaExclamationTriangle className="inline mr-1" />
                    Obligatorio: Indique motivo de la dispensación (mín. 5 caracteres).
                  </p>
                )}
              </div>

              <button
                onClick={registrarMovimiento}
                disabled={submitting}
                className="w-full px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {submitting && <FaSpinner className="animate-spin" />}
                {submitting ? "Registrando..." : "Registrar movimiento"}
              </button>
            </div>
          </div>
          ) : (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-500 mb-2">Registro no disponible</h2>
            <p className="text-gray-400 text-sm">No tienes permisos para registrar movimientos.</p>
          </div>
          )}

          <div className={`${puedeRegistrarMovimiento ? 'lg:col-span-2' : 'lg:col-span-3'} bg-white rounded-2xl shadow-sm border border-gray-200`}>
            <div className="px-6 py-4 border-b border-gray-200 flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-800">Lista de Movimientos</h3>
                <div className="flex gap-2 items-center">
                  {hayFiltrosPendientes && (
                    <span className="text-xs text-orange-600 mr-2" title="Aplica los filtros antes de exportar">
                      ⚠ Filtros sin aplicar
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => setShowFiltersMenu(!showFiltersMenu)}
                    className="flex items-center gap-2 rounded-full border border-gray-200 bg-white/90 px-4 py-2 text-sm font-semibold text-gray-700 shadow-sm transition hover:bg-white"
                  >
                    <FaFilter className="text-theme-primary" />
                    {showFiltersMenu ? 'Ocultar filtros' : 'Mostrar filtros'}
                    <FaChevronDown className={`transition ${showFiltersMenu ? 'rotate-180' : ''}`} />
                  </button>
                  <button
                    onClick={cargarMovimientos}
                    className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50 px-3 py-2"
                    disabled={loading || exporting !== null}
                  >
                    {loading ? "Cargando..." : "Recargar"}
                  </button>
                </div>
              </div>

              {/* Panel de filtros colapsable */}
              {showFiltersMenu && (
                <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 space-y-3">
                  <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3">
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
                {/* Filtro por subtipo de salida - solo visible cuando tipo=salida o sin filtro */}
                {(filtros.tipo === "" || filtros.tipo === "salida") && (
                  <div className="flex flex-col gap-1">
                    <label className="text-xs font-semibold text-gray-700">Subtipo Salida</label>
                    <select
                      value={filtros.subtipo_salida}
                      onChange={(e) => handleFiltro("subtipo_salida", e.target.value)}
                      className="border rounded-lg px-3 py-2"
                    >
                      <option value="">Todos</option>
                      <option value="receta">💊 Receta médica</option>
                      <option value="consumo_interno">🏥 Consumo interno</option>
                      <option value="merma">📉 Merma</option>
                      <option value="caducidad">⏰ Caducidad</option>
                      <option value="transferencia">🔄 Transferencia</option>
                      <option value="otro">Otro</option>
                    </select>
                  </div>
                )}
                {/* Filtro por estado de confirmación - solo para salidas */}
                {(filtros.tipo === "" || filtros.tipo === "salida") && (
                  <div className="flex flex-col gap-1">
                    <label className="text-xs font-semibold text-gray-700">Estado Entrega</label>
                    <select
                      value={filtros.estado_confirmacion}
                      onChange={(e) => handleFiltro("estado_confirmacion", e.target.value)}
                      className="border rounded-lg px-3 py-2"
                    >
                      <option value="">Todos</option>
                      <option value="confirmado">✅ Confirmados</option>
                      <option value="pendiente">⏳ Pendientes</option>
                    </select>
                  </div>
                )}
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-gray-700">Producto</label>
                  <select
                    value={filtros.producto}
                    onChange={(e) => handleFiltro("producto", e.target.value)}
                    className="border rounded-lg px-3 py-2"
                  >
                    <option value="">Todos</option>
                    {productos.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.clave} - {p.nombre}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-gray-700">Centro</label>
                  <select
                    value={filtros.centro}
                    onChange={(e) => handleFiltro("centro", e.target.value)}
                    className="border rounded-lg px-3 py-2 disabled:bg-gray-100 disabled:cursor-not-allowed"
                    disabled={!puedeVerTodosCentros}
                    title={!puedeVerTodosCentros ? "Solo puedes ver movimientos de tu centro" : ""}
                  >
                    {puedeVerTodosCentros && <option value="">Todos</option>}
                    {centros.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nombre}
                      </option>
                    ))}
                  </select>
                </div>
                {/* ISS-FIX (lotes-centro): Mejorar filtro de lote con select y búsqueda por texto */}
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-gray-700">Lote</label>
                  <select
                    value={filtros.lote}
                    onChange={(e) => handleFiltro("lote", e.target.value)}
                    className="border rounded-lg px-3 py-2"
                  >
                    <option value="">Todos los lotes</option>
                    {/* Filtrar lotes por producto seleccionado si hay uno */}
                    {(filtros.producto 
                      ? lotes.filter(l => l.producto === parseInt(filtros.producto))
                      : lotes
                    ).map((l) => {
                      const prod = productos.find(p => p.id === l.producto);
                      const fechaCad = l.fecha_caducidad ? new Date(l.fecha_caducidad).toLocaleDateString('es-MX', { month: 'short', year: 'numeric' }) : 'S/F';
                      return (
                        <option key={l.id} value={l.id}>
                          {l.numero_lote} - {prod?.clave || 'Prod'} (Stock: {l.cantidad_actual}, Cad: {fechaCad})
                        </option>
                      );
                    })}
                  </select>
                  <p className="text-xs text-gray-400">
                    {lotes.length} lote(s) disponible(s)
                    {filtros.producto && ` (filtrado por producto)`}
                  </p>
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

                  <div className="flex gap-2 items-center col-span-full">
                    <button
                      onClick={aplicarFiltros}
                      className="px-4 py-2 rounded-lg text-white text-sm font-semibold transition bg-theme-gradient"
                      disabled={loading}
                    >
                      {hayFiltrosPendientes ? '⚡ Aplicar' : 'Aplicar'}
                    </button>
                    <button
                      onClick={limpiarFiltros}
                      className="px-3 py-2 rounded-lg border bg-white text-sm hover:bg-gray-50"
                      disabled={loading || !hayFiltrosActivos}
                    >
                      Limpiar
                    </button>
                    {hayFiltrosActivos && (
                      <span className="text-xs text-gray-500 ml-2">
                        {Object.values(filtrosAplicados).filter(v => v !== "").length} filtro(s) activo(s)
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm table-fixed">
                <thead className="bg-theme-gradient sticky top-0 z-10">
                  <tr>
                    <th className="w-[30%] px-2 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white">Producto</th>
                    <th className="w-[15%] px-2 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white">Tipo</th>
                    <th className="w-[10%] px-2 py-3 text-right text-xs font-semibold uppercase tracking-wider text-white">Cant.</th>
                    <th className="w-[20%] px-2 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white">Centro</th>
                    <th className="w-[15%] px-2 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white">Fecha</th>
                    <th className="w-[10%] px-2 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white">Acc.</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-100">
                  {loading ? (
                    <tr>
                      <td colSpan={6} className="text-center py-8">
                        <div className="flex justify-center items-center">
                          <div className="animate-spin rounded-full h-8 w-8 border-4 border-t-transparent spinner-institucional"></div>
                          <span className="ml-2 text-gray-600">Cargando movimientos...</span>
                        </div>
                      </td>
                    </tr>
                  ) : !movimientos.length ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                        Sin movimientos
                      </td>
                    </tr>
                  ) : vistaAgrupada && movimientosAgrupados ? (
                    <>
                      {/* Mostrar grupos de salidas masivas */}
                      {movimientosAgrupados.grupos.map((grupo, gIndex) => (
                        <React.Fragment key={grupo.id}>
                          {/* Fila del grupo colapsado */}
                          <tr 
                            className={`transition cursor-pointer ${gIndex % 2 === 0 ? 'bg-rose-50' : 'bg-rose-100/50'} hover:bg-rose-100 border-l-4 ${grupo.confirmado ? 'border-green-500' : 'border-rose-500'}`}
                            onClick={() => toggleGrupo(grupo.id)}
                          >
                            <td className="px-4 py-3 text-sm">
                              <div className="flex items-center gap-2">
                                {gruposExpandidos.has(grupo.id) ? <FaChevronDown className="text-rose-600 flex-shrink-0" /> : <FaChevronRight className="text-rose-600 flex-shrink-0" />}
                                <div className="min-w-0">
                                  <div className="font-bold text-rose-800 flex items-center gap-1 flex-wrap">
                                    <FaTruck className="text-rose-600 flex-shrink-0" />
                                    <span className="truncate">SM: {grupo.id.slice(-8)}</span>
                                    {grupo.confirmado && (
                                      <span className="px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-semibold">✓</span>
                                    )}
                                  </div>
                                  <div className="text-xs text-rose-600">{grupo.items.length} prod.</div>
                                </div>
                              </div>
                            </td>
                            <td className="px-2 py-3">
                              <span className="px-1.5 py-0.5 rounded text-xs font-semibold bg-rose-200 text-rose-800">
                                MASIVA
                              </span>
                            </td>
                            <td className="px-2 py-3 text-right font-bold text-rose-800">
                              -{grupo.totalCantidad}
                            </td>
                            <td className="px-2 py-3 text-rose-800 font-semibold text-xs truncate" title={grupo.centro_nombre}>{grupo.centro_nombre}</td>
                            <td className="px-2 py-3 text-rose-700 text-xs">
                              {grupo.fecha ? new Date(grupo.fecha).toLocaleDateString('es-MX') : ''}
                            </td>
                            <td className="px-2 py-3">
                              <div className="flex items-center justify-center gap-1">
                                {!grupo.confirmado ? (
                                  <>
                                    {/* Hoja de Entrega (para firmas) */}
                                    <button
                                      onClick={(e) => { e.stopPropagation(); descargarHojaEntregaGrupo(grupo.id); }}
                                      className="inline-flex items-center gap-1 px-2 py-1 bg-rose-600 text-white rounded text-xs font-medium hover:bg-rose-700 transition"
                                      title="Hoja de entrega"
                                    >
                                      <FaClipboardCheck className="text-xs" />
                                    </button>
                                    {/* Confirmar Entrega */}
                                    <button
                                      onClick={(e) => { e.stopPropagation(); confirmarEntregaGrupo(grupo.id); }}
                                      disabled={confirmandoGrupo === grupo.id}
                                      className="inline-flex items-center gap-1 px-2 py-1 bg-green-600 text-white rounded text-xs font-medium hover:bg-green-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                                      title="Confirmar entrega física"
                                    >
                                      {confirmandoGrupo === grupo.id ? (
                                        <FaSpinner className="text-xs animate-spin" />
                                      ) : (
                                        <FaCheckCircle className="text-xs" />
                                      )}
                                    </button>
                                    {/* Cancelar Salida (devuelve stock) */}
                                    <button
                                      onClick={(e) => { e.stopPropagation(); setConfirmCancelarGrupo(grupo.id); }}
                                      disabled={cancelandoGrupo === grupo.id}
                                      className="inline-flex items-center gap-1 px-2 py-1 bg-red-600 text-white rounded text-xs font-medium hover:bg-red-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                                      title="Cancelar salida (devuelve stock)"
                                    >
                                      {cancelandoGrupo === grupo.id ? (
                                        <FaSpinner className="text-xs animate-spin" />
                                      ) : (
                                        <FaTrash className="text-xs" />
                                      )}
                                    </button>
                                  </>
                                ) : (
                                  /* Solo comprobante si ya está confirmado */
                                  <button
                                    onClick={(e) => { e.stopPropagation(); descargarComprobanteGrupo(grupo.id); }}
                                    className="inline-flex items-center gap-1 px-2 py-1 bg-green-600 text-white rounded text-xs font-medium hover:bg-green-700 transition"
                                    title="Descargar comprobante de entrega"
                                  >
                                    <FaFileDownload className="text-xs" />
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                          {/* Items del grupo expandidos */}
                          {gruposExpandidos.has(grupo.id) && grupo.items.map((mov, iIndex) => (
                            <tr 
                              key={mov.id}
                              className={`transition ${iIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-gray-100 border-l-4 border-rose-200`}
                            >
                              <td className="px-2 py-2 text-sm pl-8">
                                <div className="font-medium text-gray-800 truncate text-xs">{mov.producto_nombre || mov.producto || ""}</div>
                                <div className="text-xs text-gray-500">Lote: {mov.lote_codigo || mov.numero_lote || 'N/A'}</div>
                              </td>
                              <td className="px-2 py-2">
                                <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                                  item
                                </span>
                              </td>
                              <td className="px-2 py-2 text-right font-semibold text-gray-700">
                                -{Math.abs(mov.cantidad)}
                              </td>
                              <td className="px-2 py-2 text-gray-600 text-xs truncate">{mov.centro_nombre || "Almacén Central"}</td>
                              <td className="px-2 py-2 text-gray-500 text-xs">
                                {mov.lote?.fecha_caducidad ? new Date(mov.lote.fecha_caducidad).toLocaleDateString('es-MX') : ''}
                              </td>
                              <td className="px-2 py-2 text-center text-xs text-gray-400">
                                #{mov.id}
                              </td>
                            </tr>
                          ))}
                        </React.Fragment>
                      ))}
                      {/* Mostrar movimientos sin grupo (individuales) */}
                      {movimientosAgrupados.sinGrupo.map((mov, index) => (
                        <React.Fragment key={mov.id}>
                          <tr 
                            ref={highlightId === mov.id ? highlightRef : null}
                            className={`transition cursor-pointer ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-gray-100 ${
                              highlightId === mov.id ? 'bg-yellow-50 ring-2 ring-yellow-400' : ''
                            } ${expandedId === mov.id ? 'bg-blue-50' : ''}`}
                            onClick={() => setExpandedId(expandedId === mov.id ? null : mov.id)}
                          >
                            <td className="px-2 py-3">
                              <div className="font-semibold text-gray-800 truncate text-sm">{mov.producto_nombre || mov.producto || ""}</div>
                              <div className="text-xs text-gray-500">Lote: {mov.lote_codigo || mov.numero_lote || 'N/A'}</div>
                            </td>
                            <td className="px-2 py-3">
                              <div className="flex flex-col gap-0.5">
                                <span className={`px-1.5 py-0.5 rounded text-xs font-semibold inline-block w-fit ${
                                  mov.tipo === "entrada" ? "bg-green-100 text-green-800" :
                                  mov.tipo === "salida" ? "bg-red-100 text-red-800" : "bg-yellow-100 text-yellow-800"
                                }`}>
                                  {mov.tipo?.toUpperCase()}
                                </span>
                                {mov.tipo === 'salida' && mov.subtipo_salida && (
                                  <span className="text-xs text-gray-500">
                                    {mov.subtipo_salida === 'receta' ? '💊' :
                                     mov.subtipo_salida === 'consumo_interno' ? '🏥' :
                                     mov.subtipo_salida === 'merma' ? '📉' :
                                     mov.subtipo_salida === 'caducidad' ? '⏰' :
                                     mov.subtipo_salida === 'transferencia' ? '🔄' : ''}
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className="px-2 py-3 text-right font-semibold text-gray-900">
                              {mov.tipo === 'salida' ? '-' : '+'}{Math.abs(mov.cantidad)}
                            </td>
                            <td className="px-2 py-3 text-gray-700 text-xs truncate">{mov.centro_nombre || mov.centro || "Almacén Central"}</td>
                            <td className="px-2 py-3 text-gray-600 text-xs">
                              {mov.fecha_movimiento ? new Date(mov.fecha_movimiento).toLocaleDateString('es-MX') :
                               mov.fecha ? new Date(mov.fecha).toLocaleDateString('es-MX') : ""}
                            </td>
                            <td className="px-2 py-3 text-center">
                              <button 
                                className="text-blue-600 hover:text-blue-800 text-xs"
                                onClick={(e) => { e.stopPropagation(); setExpandedId(expandedId === mov.id ? null : mov.id); }}
                              >
                                {expandedId === mov.id ? '▲' : '▼'}
                              </button>
                            </td>
                          </tr>
                          {expandedId === mov.id && (
                            <tr className="bg-gray-50">
                              <td colSpan={6} className="px-4 py-3">
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                                  <div><span className="font-semibold text-gray-600">ID:</span><p className="text-gray-800">{mov.id}</p></div>
                                  <div><span className="font-semibold text-gray-600">Usuario:</span><p className="text-gray-800">{mov.usuario_nombre || 'Sistema'}</p></div>
                                  {mov.observaciones && (
                                    <div className="col-span-2 md:col-span-4">
                                      <span className="font-semibold text-gray-600">Observaciones:</span>
                                      <p className="text-gray-800 bg-white p-2 rounded border mt-1">{mov.observaciones}</p>
                                    </div>
                                  )}
                                  {/* Botones de acción para movimientos de salida */}
                                  {mov.tipo === 'salida' && (
                                    <div className="col-span-2 md:col-span-4 flex flex-wrap gap-3 mt-4 pt-4 border-t border-gray-200">
                                      {!mov.confirmado ? (
                                        <>
                                          {/* Hoja de Entrega (solo si NO está confirmado) */}
                                          <button
                                            onClick={(e) => { e.stopPropagation(); descargarReciboSalida(mov); }}
                                            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm font-medium"
                                            title="Descargar hoja de entrega con campos para firmas"
                                          >
                                            <FaFilePdf className="text-lg" />
                                            Hoja de Entrega
                                          </button>
                                          {/* Botón confirmar entrega */}
                                          <button
                                            onClick={(e) => { e.stopPropagation(); confirmarEntregaIndividual(mov.id); }}
                                            disabled={confirmandoMovimiento === mov.id}
                                            className="flex items-center gap-2 px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition text-sm font-medium disabled:opacity-50"
                                            title="Confirmar que la entrega fue recibida"
                                          >
                                            {confirmandoMovimiento === mov.id ? (
                                              <FaSpinner className="animate-spin text-lg" />
                                            ) : (
                                              <FaClipboardCheck className="text-lg" />
                                            )}
                                            {confirmandoMovimiento === mov.id ? 'Confirmando...' : 'Confirmar Entrega'}
                                          </button>
                                        </>
                                      ) : (
                                        /* Comprobante solo si ya está confirmado */
                                        <button
                                          onClick={(e) => { e.stopPropagation(); descargarReciboFinalizado(mov); }}
                                          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition text-sm font-medium"
                                          title="Descargar comprobante con sello de ENTREGADO"
                                        >
                                          <FaCheckCircle className="text-lg" />
                                          Comprobante Entregado
                                        </button>
                                      )}
                                    </div>
                                  )}
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      ))}
                    </>
                  ) : (
                    /* Vista individual (sin agrupar) */
                    movimientos.map((mov, index) => (
                      <React.Fragment key={mov.id}>
                        <tr 
                          ref={highlightId === mov.id ? highlightRef : null}
                          className={`transition cursor-pointer ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-gray-100 ${
                            highlightId === mov.id ? 'bg-yellow-50 ring-2 ring-yellow-400' : ''
                          } ${expandedId === mov.id ? 'bg-blue-50' : ''}`}
                          onClick={() => setExpandedId(expandedId === mov.id ? null : mov.id)}
                        >
                          <td className="px-2 py-3">
                            <div className="font-semibold text-gray-800 truncate text-sm">{mov.producto_nombre || mov.producto || ""}</div>
                            <div className="text-xs text-gray-500">Lote: {mov.lote_codigo || mov.numero_lote || 'N/A'}</div>
                          </td>
                          <td className="px-2 py-3">
                            <div className="flex flex-col gap-0.5">
                              <span
                                className={`px-1.5 py-0.5 rounded text-xs font-semibold inline-block w-fit ${
                                  mov.tipo === "entrada"
                                    ? "bg-green-100 text-green-800"
                                    : mov.tipo === "salida"
                                    ? "bg-red-100 text-red-800"
                                    : "bg-yellow-100 text-yellow-800"
                                }`}
                              >
                                {mov.tipo?.toUpperCase()}
                              </span>
                              {mov.tipo === 'salida' && mov.subtipo_salida && (
                                <span className="text-xs text-gray-500">
                                  {mov.subtipo_salida === 'receta' ? '💊' :
                                   mov.subtipo_salida === 'consumo_interno' ? '🏥' :
                                   mov.subtipo_salida === 'merma' ? '📉' :
                                   mov.subtipo_salida === 'caducidad' ? '⏰' :
                                   mov.subtipo_salida === 'transferencia' ? '🔄' : ''}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-2 py-3 text-right font-semibold text-gray-900">
                            {mov.tipo === 'salida' ? '-' : '+'}{Math.abs(mov.cantidad)}
                          </td>
                          <td className="px-2 py-3 text-gray-700 text-xs truncate">{mov.centro_nombre || mov.centro || "Almacén Central"}</td>
                          <td className="px-2 py-3 text-gray-600 text-xs">
                            {mov.fecha_movimiento
                              ? new Date(mov.fecha_movimiento).toLocaleDateString('es-MX')
                              : mov.fecha
                              ? new Date(mov.fecha).toLocaleDateString('es-MX')
                              : ""}
                          </td>
                          <td className="px-2 py-3 text-center">
                            <button 
                              className="text-blue-600 hover:text-blue-800 text-xs"
                              onClick={(e) => { e.stopPropagation(); setExpandedId(expandedId === mov.id ? null : mov.id); }}
                            >
                              {expandedId === mov.id ? '▲' : '▼'}
                            </button>
                          </td>
                        </tr>
                        {/* Fila expandida con detalles */}
                        {expandedId === mov.id && (
                          <tr className="bg-gray-50">
                            <td colSpan={6} className="px-4 py-3">
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                                <div>
                                  <span className="font-semibold text-gray-600">ID Movimiento:</span>
                                  <p className="text-gray-800">{mov.id}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-gray-600">Producto:</span>
                                  <p className="text-gray-800">{mov.producto_clave || 'N/A'} - {mov.producto_nombre || ''}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-gray-600">Lote:</span>
                                  <p className="text-gray-800">{mov.lote_codigo || mov.numero_lote || 'N/A'}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-gray-600">Centro:</span>
                                  <p className="text-gray-800">{mov.centro_nombre || 'Almacén Central'}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-gray-600">Usuario:</span>
                                  <p className="text-gray-800">{mov.usuario_nombre || mov.usuario || 'Sistema'}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-gray-600">Requisición:</span>
                                  <p className="text-gray-800">{mov.requisicion_folio || 'N/A'}</p>
                                </div>
                                {mov.tipo === 'salida' && (
                                  <div>
                                    <span className="font-semibold text-gray-600">Subtipo Salida:</span>
                                    <p className="text-gray-800">
                                      {mov.subtipo_salida === 'receta' ? '💊 Receta médica' :
                                       mov.subtipo_salida === 'consumo_interno' ? '🏥 Consumo interno' :
                                       mov.subtipo_salida === 'merma' ? '📉 Merma' :
                                       mov.subtipo_salida === 'caducidad' ? '⏰ Caducidad' :
                                       mov.subtipo_salida === 'transferencia' ? '🔄 Transferencia' :
                                       mov.subtipo_salida || 'No especificado'}
                                    </p>
                                  </div>
                                )}
                                {mov.tipo === 'salida' && mov.subtipo_salida === 'receta' && (
                                  <div>
                                    <span className="font-semibold text-gray-600">No. Expediente:</span>
                                    <p className="text-gray-800 font-mono bg-blue-50 px-2 py-1 rounded">{mov.numero_expediente || 'N/A'}</p>
                                  </div>
                                )}
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
                                {/* Botones de acción para movimientos de salida */}
                                {mov.tipo === 'salida' && (
                                  <div className="col-span-2 md:col-span-4 flex flex-wrap gap-3 mt-4 pt-4 border-t border-gray-200">
                                    <button
                                      onClick={(e) => { e.stopPropagation(); descargarReciboSalida(mov); }}
                                      className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm font-medium"
                                      title="Descargar hoja de entrega con campos para firmas"
                                    >
                                      <FaFilePdf className="text-lg" />
                                      Hoja de Entrega
                                    </button>
                                    {!mov.confirmado ? (
                                      /* Botón confirmar entrega si no está confirmado */
                                      <button
                                        onClick={(e) => { e.stopPropagation(); confirmarEntregaIndividual(mov.id); }}
                                        disabled={confirmandoMovimiento === mov.id}
                                        className="flex items-center gap-2 px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition text-sm font-medium disabled:opacity-50"
                                        title="Confirmar que la entrega fue recibida"
                                      >
                                        {confirmandoMovimiento === mov.id ? (
                                          <FaSpinner className="animate-spin text-lg" />
                                        ) : (
                                          <FaClipboardCheck className="text-lg" />
                                        )}
                                        {confirmandoMovimiento === mov.id ? 'Confirmando...' : 'Confirmar Entrega'}
                                      </button>
                                    ) : (
                                      /* Botón comprobante solo si ya está confirmado */
                                      <button
                                        onClick={(e) => { e.stopPropagation(); descargarReciboFinalizado(mov); }}
                                        className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition text-sm font-medium"
                                        title="Descargar comprobante con sello de ENTREGADO"
                                      >
                                        <FaCheckCircle className="text-lg" />
                                        Comprobante Entregado
                                      </button>
                                    )}
                                  </div>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))
                  )}
                </tbody>
              </table>
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
      
      {/* Modal Salida Masiva */}
      {showSalidaMasiva && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="max-h-[90vh] overflow-y-auto">
            <SalidaMasiva
              onClose={() => setShowSalidaMasiva(false)}
              onSuccess={() => {
                cargarMovimientos();
                cargarCatalogos();
              }}
            />
          </div>
        </div>
      )}
      
      {/* Modal Confirmación Cancelar Salida */}
      {confirmCancelarGrupo && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
            <div className="px-6 py-4 border-b bg-red-600 rounded-t-xl">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <FaTrash /> Cancelar Salida
              </h2>
            </div>
            <div className="p-6">
              <p className="text-gray-700 mb-4">
                ¿Estás seguro de cancelar esta salida masiva?
              </p>
              <p className="text-sm text-gray-600 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                <FaExclamationTriangle className="inline text-yellow-600 mr-2" />
                <strong>Importante:</strong> El stock de todos los productos será devuelto al inventario de Farmacia Central.
              </p>
            </div>
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end gap-3 rounded-b-xl">
              <button
                onClick={() => setConfirmCancelarGrupo(null)}
                className="px-4 py-2 border rounded-lg hover:bg-gray-100 transition-colors"
              >
                No, mantener
              </button>
              <button
                onClick={() => cancelarSalidaGrupo(confirmCancelarGrupo)}
                disabled={cancelandoGrupo === confirmCancelarGrupo}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {cancelandoGrupo === confirmCancelarGrupo ? (
                  <>
                    <FaSpinner className="animate-spin" /> Cancelando...
                  </>
                ) : (
                  <>
                    <FaTrash /> Sí, cancelar y devolver stock
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Movimientos;
