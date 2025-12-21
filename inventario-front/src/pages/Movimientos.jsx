import React, { useEffect, useMemo, useState, useRef, useCallback } from "react";
import { useLocation } from "react-router-dom";
import { toast } from "react-hot-toast";
import Pagination from "../components/Pagination";
import SalidaMasiva from "../components/SalidaMasiva";
import { movimientosAPI, productosAPI, centrosAPI, lotesAPI, descargarArchivo } from "../services/api";
import { usePermissions } from "../hooks/usePermissions";
import { FaFilter, FaChevronDown, FaChevronRight, FaExchangeAlt, FaFileExcel, FaFilePdf, FaSpinner, FaInfoCircle, FaExclamationTriangle, FaTruck, FaLayerGroup, FaList } from "react-icons/fa";
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
  });

  const [productos, setProductos] = useState([]);
  const [centros, setCentros] = useState([]);
  const [lotes, setLotes] = useState([]);
  const [lotesDisponibles, setLotesDisponibles] = useState([]);

  // Formulario de registro
  // ISS-FIX: Tipo por defecto según rol - CENTRO solo puede salida/ajuste
  const tipoDefault = puedeVerTodosCentros ? "entrada" : "salida";
  const [formData, setFormData] = useState({
    lote: "",
    tipo: tipoDefault,
    cantidad: "",
    centro: "",
    observaciones: "",
    // MEJORA FLUJO 5: Campos para trazabilidad de pacientes
    subtipo_salida: "",
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
      
      // ISS-FIX (lotes-centro): Cargar lotes con filtro explícito de centro
      // El backend ya filtra por centro del usuario, pero enviamos el parámetro
      // para asegurar consistencia y logging
      const lotesParams = { 
        page_size: 500, 
        ordering: "-fecha_caducidad", 
        activo: true,  // ISS-FIX: Solo lotes activos
        con_stock: "con_stock",  // ISS-FIX: Solo lotes con stock > 0
      };
      
      // ISS-FIX: Si usuario de centro, el backend filtra automáticamente
      // pero podemos agregar el centro explícitamente si está disponible
      if (!puedeVerTodosCentros && centroUsuario) {
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
      const params = {
        page,
        page_size: PAGE_SIZE,
        ordering: "-fecha",
        ...filtrosAplicados,
      };
      // Limpiar parámetros vacíos
      Object.keys(params).forEach(key => {
        if (params[key] === "" || params[key] === null || params[key] === undefined) {
          delete params[key];
        }
      });
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

    // ISS-MEDICO FIX v2: Observaciones obligatorias para médicos
    if (esMedico && (!formData.observaciones || formData.observaciones.trim().length < 5)) {
      toast.error("Las observaciones son obligatorias (mínimo 5 caracteres). Indique motivo de la salida.");
      return;
    }

    const loteSeleccionado = lotes.find(l => l.id === parseInt(formData.lote));
    if (formData.tipo === "salida" && loteSeleccionado && Number(formData.cantidad) > loteSeleccionado.cantidad_actual) {
      toast.error(`Inventario insuficiente. Disponible: ${loteSeleccionado.cantidad_actual}`);
      return;
    }

    // MEJORA FLUJO 5: Validar numero_expediente si es salida por receta
    if (formData.tipo === "salida" && formData.subtipo_salida === "receta") {
      if (!formData.numero_expediente || formData.numero_expediente.trim().length < 3) {
        toast.error("El número de expediente es obligatorio para salidas por receta (mínimo 3 caracteres)");
        return;
      }
    }

    // ISS-FIX: Forzar centro del usuario si no tiene permisos globales
    const centroFinal = !puedeVerTodosCentros && centroUsuario 
      ? parseInt(centroUsuario) 
      : (formData.centro ? parseInt(formData.centro) : null);

    setSubmitting(true);
    try {
      const payload = {
        lote: parseInt(formData.lote),
        tipo: formData.tipo,
        cantidad: Number(formData.cantidad),
        centro: centroFinal,
        observaciones: formData.observaciones,
      };
      
      // MEJORA FLUJO 5: Incluir campos de trazabilidad si es salida
      if (formData.tipo === "salida" && formData.subtipo_salida) {
        payload.subtipo_salida = formData.subtipo_salida;
        if (formData.subtipo_salida === "receta") {
          payload.numero_expediente = formData.numero_expediente.trim();
        }
      }
      
      await movimientosAPI.create(payload);
      toast.success("Movimiento registrado exitosamente");
      setFormData({
        lote: "",
        tipo: tipoDefault, // ISS-FIX: Usar tipo correcto según rol
        cantidad: "",
        centro: "",
        observaciones: "",
        subtipo_salida: "",
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

  // Descargar recibo de salida con firmas para un movimiento específico
  const descargarReciboSalida = async (movimientoId) => {
    try {
      toast.loading('Generando recibo PDF...', { id: 'pdf-loading' });
      const response = await movimientosAPI.reciboSalidaPdf(movimientoId);
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `recibo_salida_movimiento_${movimientoId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.dismiss('pdf-loading');
      toast.success('Recibo PDF generado correctamente');
    } catch (err) {
      toast.dismiss('pdf-loading');
      toast.error(err.response?.data?.detail || 'Error al generar el recibo PDF');
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
              <p className="text-white/80 text-sm">Total: {total} movimientos | Balance: {stats.balance >= 0 ? '+' : ''}{stats.balance}</p>
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
                  <p className="text-xs text-orange-600">No hay lotes disponibles</p>
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

              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700">Tipo *</label>
                <select
                  value={formData.tipo}
                  onChange={(e) => handleFormChange("tipo", e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                  disabled={esMedico}
                >
                  {/* ISS-FIX: CENTRO solo puede hacer salidas y ajustes, no entradas */}
                  {/* ISS-MEDICO FIX v2: Médicos SOLO pueden hacer salidas */}
                  {puedeVerTodosCentros && <option value="entrada">Entrada</option>}
                  <option value="salida">Salida</option>
                  {!esMedico && <option value="ajuste">Ajuste</option>}
                </select>
                {esMedico && (
                  <p className="text-xs text-blue-600">
                    <FaInfoCircle className="inline mr-1" />
                    Como médico, solo puedes registrar salidas para dispensación a pacientes.
                  </p>
                )}
                {!puedeVerTodosCentros && !esMedico && (
                  <p className="text-xs text-gray-500">Las entradas solo se realizan desde Farmacia Central.</p>
                )}
              </div>

              {/* MEJORA FLUJO 5: Subtipo de salida - Simplificado para usuarios */}
              {formData.tipo === "salida" && (
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-gray-700">Motivo de salida</label>
                  <select
                    value={formData.subtipo_salida}
                    onChange={(e) => handleFormChange("subtipo_salida", e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">-- Seleccionar motivo --</option>
                    <option value="receta">Receta médica</option>
                    <option value="consumo_interno">Consumo interno</option>
                    <option value="transferencia">Transferencia a centro</option>
                    <option value="otro">Otro</option>
                  </select>
                </div>
              )}

              {/* MEJORA FLUJO 5: Número de expediente (obligatorio para receta) */}
              {formData.tipo === "salida" && formData.subtipo_salida === "receta" && (
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-gray-700">
                    Número de expediente *
                  </label>
                  <input
                    type="text"
                    value={formData.numero_expediente}
                    onChange={(e) => handleFormChange("numero_expediente", e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Ej: EXP-2024-001234"
                  />
                  <p className="text-xs text-gray-500">
                    Obligatorio para salidas por receta médica (mín. 3 caracteres).
                  </p>
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

              {/* Centro opcional - bloqueado para usuarios de centro */}
              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700">Centro</label>
                <select
                  value={!puedeVerTodosCentros && centroUsuario ? centroUsuario.toString() : formData.centro}
                  onChange={(e) => handleFormChange("centro", e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                  disabled={!puedeVerTodosCentros}
                  title={!puedeVerTodosCentros ? "Solo puedes registrar movimientos en tu centro" : ""}
                >
                  {puedeVerTodosCentros && <option value="">-- Sin centro --</option>}
                  {centros.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nombre}
                    </option>
                  ))}
                </select>
                {!puedeVerTodosCentros && (
                  <p className="text-xs text-gray-500">Movimientos limitados a tu centro asignado.</p>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700">
                  Observaciones {esMedico && <span className="text-red-500">*</span>}
                </label>
                <textarea
                  value={formData.observaciones}
                  onChange={(e) => handleFormChange("observaciones", e.target.value)}
                  className={`w-full rounded-lg border px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    esMedico ? 'border-blue-400 bg-blue-50' : 'border-gray-300'
                  }`}
                  placeholder={esMedico 
                    ? "OBLIGATORIO: Indique motivo de salida, paciente, diagnóstico, etc."
                    : "Notas adicionales..."
                  }
                  rows={esMedico ? 3 : 2}
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
              <table className="min-w-full text-sm">
                <thead className="thead-theme">
                  <tr>
                    {columnas.map((col) => (
                      <th key={col} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white">
                        {col.toUpperCase()}
                      </th>
                    ))}
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white">
                      Acciones
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-100">
                  {loading ? (
                    <tr>
                      <td colSpan={columnas.length + 1} className="text-center py-8">
                        <div className="flex justify-center items-center">
                          <div className="animate-spin rounded-full h-8 w-8 border-4 border-t-transparent spinner-institucional"></div>
                          <span className="ml-2 text-gray-600">Cargando movimientos...</span>
                        </div>
                      </td>
                    </tr>
                  ) : !movimientos.length ? (
                    <tr>
                      <td colSpan={columnas.length + 1} className="px-4 py-8 text-center text-gray-500">
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
                            className={`transition cursor-pointer ${gIndex % 2 === 0 ? 'bg-rose-50' : 'bg-rose-100/50'} hover:bg-rose-100 border-l-4 border-rose-500`}
                            onClick={() => toggleGrupo(grupo.id)}
                          >
                            <td className="px-4 py-3 text-sm">
                              <div className="flex items-center gap-2">
                                {gruposExpandidos.has(grupo.id) ? <FaChevronDown className="text-rose-600" /> : <FaChevronRight className="text-rose-600" />}
                                <div>
                                  <div className="font-bold text-rose-800 flex items-center gap-2">
                                    <FaTruck className="text-rose-600" />
                                    Salida Masiva: {grupo.id}
                                  </div>
                                  <div className="text-xs text-rose-600">{grupo.items.length} productos</div>
                                </div>
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <span className="px-2 py-1 rounded text-xs font-semibold bg-rose-200 text-rose-800">
                                SALIDA MASIVA
                              </span>
                            </td>
                            <td className="px-4 py-3 text-right font-bold text-rose-800">
                              -{grupo.totalCantidad}
                            </td>
                            <td className="px-4 py-3 text-rose-800 font-semibold">{grupo.centro_nombre}</td>
                            <td className="px-4 py-3 text-rose-700">
                              {grupo.fecha ? new Date(grupo.fecha).toLocaleString('es-MX') : ''}
                            </td>
                            <td className="px-4 py-3">
                              <span className="text-rose-600 text-sm font-semibold">
                                {gruposExpandidos.has(grupo.id) ? '▲ Colapsar' : '▼ Ver items'}
                              </span>
                            </td>
                          </tr>
                          {/* Items del grupo expandidos */}
                          {gruposExpandidos.has(grupo.id) && grupo.items.map((mov, iIndex) => (
                            <tr 
                              key={mov.id}
                              className={`transition ${iIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-gray-100 border-l-4 border-rose-200`}
                            >
                              <td className="px-4 py-2 text-sm pl-10">
                                <div className="font-medium text-gray-800">{mov.producto_nombre || mov.producto || ""}</div>
                                <div className="text-xs text-gray-500">Lote: {mov.lote_codigo || mov.numero_lote || 'N/A'}</div>
                              </td>
                              <td className="px-4 py-2">
                                <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                                  item
                                </span>
                              </td>
                              <td className="px-4 py-2 text-right font-semibold text-gray-700">
                                -{Math.abs(mov.cantidad)}
                              </td>
                              <td className="px-4 py-2 text-gray-600 text-sm">{mov.centro_nombre || "Farmacia Central"}</td>
                              <td className="px-4 py-2 text-gray-500 text-xs">
                                Cad: {mov.lote?.fecha_caducidad ? new Date(mov.lote.fecha_caducidad).toLocaleDateString('es-MX') : 'N/A'}
                              </td>
                              <td className="px-4 py-2 text-xs text-gray-400">
                                ID: {mov.id}
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
                            <td className="px-4 py-3 text-sm">
                              <div className="font-semibold text-gray-800">{mov.producto_nombre || mov.producto || ""}</div>
                              <div className="text-xs text-gray-500">Lote: {mov.lote_codigo || mov.numero_lote || 'N/A'}</div>
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex flex-col gap-1">
                                <span className={`px-2 py-1 rounded text-xs font-semibold inline-block w-fit ${
                                  mov.tipo === "entrada" ? "bg-green-100 text-green-800" :
                                  mov.tipo === "salida" ? "bg-red-100 text-red-800" : "bg-yellow-100 text-yellow-800"
                                }`}>
                                  {mov.tipo?.toUpperCase()}
                                </span>
                                {mov.tipo === 'salida' && mov.subtipo_salida && (
                                  <span className="text-xs text-gray-500">
                                    {mov.subtipo_salida === 'receta' ? '💊 Receta' :
                                     mov.subtipo_salida === 'consumo_interno' ? '🏥 Consumo' :
                                     mov.subtipo_salida === 'merma' ? '📉 Merma' :
                                     mov.subtipo_salida === 'caducidad' ? '⏰ Caducidad' :
                                     mov.subtipo_salida === 'transferencia' ? '🔄 Transfer.' : mov.subtipo_salida}
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className="px-4 py-3 text-right font-semibold text-gray-900">
                              {mov.tipo === 'salida' ? '-' : '+'}{Math.abs(mov.cantidad)}
                            </td>
                            <td className="px-4 py-3 text-gray-700">{mov.centro_nombre || mov.centro || "Farmacia Central"}</td>
                            <td className="px-4 py-3 text-gray-600">
                              {mov.fecha_movimiento ? new Date(mov.fecha_movimiento).toLocaleString('es-MX') :
                               mov.fecha ? new Date(mov.fecha).toLocaleString('es-MX') : ""}
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
                          {expandedId === mov.id && (
                            <tr className="bg-gray-50">
                              <td colSpan={columnas.length + 1} className="px-6 py-4">
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                  <div><span className="font-semibold text-gray-600">ID:</span><p className="text-gray-800">{mov.id}</p></div>
                                  <div><span className="font-semibold text-gray-600">Usuario:</span><p className="text-gray-800">{mov.usuario_nombre || 'Sistema'}</p></div>
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
                          <td className="px-4 py-3 text-sm">
                            <div className="font-semibold text-gray-800">{mov.producto_nombre || mov.producto || ""}</div>
                            <div className="text-xs text-gray-500">Lote: {mov.lote_codigo || mov.numero_lote || 'N/A'}</div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex flex-col gap-1">
                              <span
                                className={`px-2 py-1 rounded text-xs font-semibold inline-block w-fit ${
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
                                  {mov.subtipo_salida === 'receta' ? '💊 Receta' :
                                   mov.subtipo_salida === 'consumo_interno' ? '🏥 Consumo' :
                                   mov.subtipo_salida === 'merma' ? '📉 Merma' :
                                   mov.subtipo_salida === 'caducidad' ? '⏰ Caducidad' :
                                   mov.subtipo_salida === 'transferencia' ? '🔄 Transfer.' :
                                   mov.subtipo_salida}
                                </span>
                              )}
                            </div>
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
                            <div className="flex items-center gap-2">
                              <button 
                                className="text-blue-600 hover:text-blue-800 text-sm"
                                onClick={(e) => { e.stopPropagation(); setExpandedId(expandedId === mov.id ? null : mov.id); }}
                              >
                                {expandedId === mov.id ? '▲ Ocultar' : '▼ Detalles'}
                              </button>
                              {mov.tipo === 'salida' && (
                                <button 
                                  className="text-red-600 hover:text-red-800 text-sm"
                                  onClick={(e) => { e.stopPropagation(); descargarReciboSalida(mov.id); }}
                                  title="Descargar recibo con firmas"
                                >
                                  📄 PDF
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                        {/* Fila expandida con detalles */}
                        {expandedId === mov.id && (
                          <tr className="bg-gray-50">
                            <td colSpan={columnas.length + 1} className="px-6 py-4">
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
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
    </div>
  );
};

export default Movimientos;
