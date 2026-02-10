import React, { useEffect, useMemo, useState, useRef, useCallback } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { toast } from "react-hot-toast";
import Pagination from "../components/Pagination";
import SalidaMasiva from "../components/SalidaMasiva";
import { movimientosAPI, productosAPI, centrosAPI, lotesAPI, salidaMasivaAPI, descargarArchivo, abrirPdfEnNavegador } from "../services/api";
import { usePermissions } from "../hooks/usePermissions";
import { FaFilter, FaChevronDown, FaChevronRight, FaExchangeAlt, FaFileExcel, FaFilePdf, FaSpinner, FaInfoCircle, FaExclamationTriangle, FaTruck, FaLayerGroup, FaList, FaFileDownload, FaCheckCircle, FaClipboardCheck, FaTrash, FaBoxes, FaHistory, FaClock } from "react-icons/fa";
import { COLORS } from "../constants/theme";

// ISS-FIX: Constantes de paginación
const PAGE_SIZE_INDIVIDUAL = 25;
const PAGE_SIZE_AGRUPADA = 200;
const GRUPOS_POR_PAGINA = 15;

// 🎨 DISEÑO PREMIUM: Configuración de colores y estilos por tipo de grupo
const GRUPO_STYLES = {
  requisicion: {
    gradient: 'from-blue-50 via-blue-100 to-blue-50',
    border: 'border-l-blue-500',
    borderConfirmed: 'border-l-emerald-500',
    headerBg: 'bg-gradient-to-r from-blue-100 to-indigo-100',
    badge: 'bg-blue-600 text-white',
    icon: 'text-blue-600',
    hoverBg: 'hover:from-blue-100 hover:to-indigo-100',
    label: 'REQUISICIÓN',
    emoji: '📋',
  },
  salida_masiva: {
    gradient: 'from-pink-50 via-rose-100 to-pink-50',
    border: 'border-l-pink-500',
    borderConfirmed: 'border-l-emerald-500',
    headerBg: 'bg-gradient-to-r from-pink-100 to-rose-100',
    badge: 'bg-pink-600 text-white',
    icon: 'text-pink-600',
    hoverBg: 'hover:from-pink-100 hover:to-rose-100',
    label: 'MASIVA',
    emoji: '🚚',
  },
  transferencia: {
    gradient: 'from-amber-50 via-yellow-100 to-amber-50',
    border: 'border-l-amber-500',
    borderConfirmed: 'border-l-emerald-500',
    headerBg: 'bg-gradient-to-r from-amber-100 to-yellow-100',
    badge: 'bg-amber-600 text-white',
    icon: 'text-amber-600',
    hoverBg: 'hover:from-amber-100 hover:to-yellow-100',
    label: 'TRANSF.',
    emoji: '🔄',
  },
  salida_centro: {
    gradient: 'from-violet-50 via-purple-100 to-violet-50',
    border: 'border-l-violet-500',
    borderConfirmed: 'border-l-emerald-500',
    headerBg: 'bg-gradient-to-r from-violet-100 to-purple-100',
    badge: 'bg-violet-600 text-white',
    icon: 'text-violet-600',
    hoverBg: 'hover:from-violet-100 hover:to-purple-100',
    label: 'DISPENSACIÓN',
    emoji: '🏥',
  },
  transferencia_centro: {
    gradient: 'from-teal-50 via-cyan-100 to-teal-50',
    border: 'border-l-teal-500',
    borderConfirmed: 'border-l-emerald-500',
    headerBg: 'bg-gradient-to-r from-teal-100 to-cyan-100',
    badge: 'bg-teal-600 text-white',
    icon: 'text-teal-600',
    hoverBg: 'hover:from-teal-100 hover:to-cyan-100',
    label: 'ENVÍO A CENTRO',
    emoji: '📦',
  },
};

// 🦴 Skeleton component para loading elegante
const SkeletonRow = ({ index }) => (
  <tr className={`animate-pulse ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}>
    <td className="px-3 py-4">
      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
      <div className="h-3 bg-gray-100 rounded w-1/2"></div>
    </td>
    <td className="px-2 py-4"><div className="h-6 bg-gray-200 rounded w-16"></div></td>
    <td className="px-2 py-4 text-right"><div className="h-4 bg-gray-200 rounded w-10 ml-auto"></div></td>
    <td className="px-2 py-4"><div className="h-4 bg-gray-200 rounded w-24"></div></td>
    <td className="px-2 py-4"><div className="h-4 bg-gray-200 rounded w-20"></div></td>
    <td className="px-2 py-4"><div className="h-4 bg-gray-200 rounded w-8 mx-auto"></div></td>
  </tr>
);

// 🏷️ Badge component reutilizable
const StatusBadge = ({ tipo, confirmado, pendiente }) => {
  if (confirmado) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-gradient-to-r from-emerald-500 to-green-500 text-white text-xs font-bold shadow-sm">
        <FaCheckCircle className="text-[10px]" /> Confirmado
      </span>
    );
  }
  if (pendiente) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-gradient-to-r from-yellow-400 to-amber-400 text-yellow-900 text-xs font-bold shadow-sm animate-pulse">
        <span className="w-2 h-2 bg-yellow-600 rounded-full"></span> Pendiente
      </span>
    );
  }
  return null;
};

// 📊 Contador animado de movimientos
const MovCounter = ({ salidas, entradas }) => (
  <div className="flex items-center gap-2 flex-wrap">
    {salidas > 0 && (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-100 text-red-700 text-xs font-semibold border border-red-200">
        <span className="w-1.5 h-1.5 bg-red-500 rounded-full"></span>
        {salidas} salida{salidas > 1 ? 's' : ''}
      </span>
    )}
    {entradas > 0 && (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 text-xs font-semibold border border-emerald-200">
        <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span>
        {entradas} entrada{entradas > 1 ? 's' : ''}
      </span>
    )}
  </div>
);

const Movimientos = () => {
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const highlightId = location.state?.highlightId;
  const highlightRef = useRef(null);
  const { user, permisos, getRolPrincipal } = usePermissions();
  
  // Request deduplication & abort controller
  const abortControllerRef = useRef(null);
  const requestIdRef = useRef(0);
  
  // ===========================================================================
  // HALLAZGO #5 DOCUMENTACIÓN: Roles y Permisos
  // ===========================================================================
  // Los roles (user.rol, user.rol_efectivo) provienen del contexto usePermissions
  // que los obtiene del endpoint /api/me y del token JWT validado por el backend.
  // 
  // SEGURIDAD: Aunque un usuario malicioso modifique localStorage o el estado
  // de React para mostrar botones admin, el BACKEND valida:
  //   1. Token JWT firmado con clave secreta del servidor
  //   2. Rol del usuario en la base de datos
  //   3. Permisos específicos para cada operación
  // 
  // La UI usa estos valores solo para UX (ocultar/mostrar elementos).
  // Cualquier acción crítica es re-validada por el backend antes de ejecutarse.
  // ===========================================================================
  
  // Detectar si puede ver todos los centros o solo el suyo
  const rolPrincipal = getRolPrincipal();
  const puedeVerTodosCentros = ['ADMIN', 'FARMACIA', 'VISTA'].includes(rolPrincipal);
  const centroUsuario = user?.centro?.id || user?.centro || user?.centro_id;
  const centroNombre = user?.centro?.nombre || user?.centro_nombre || null;
  const esCentroUser = rolPrincipal === 'CENTRO';
  
  // ISS-MEDICO FIX v2: Detectar si el usuario es médico específicamente
  const esMedico = (user?.rol_efectivo || user?.rol || '').toLowerCase() === 'medico';
  
  // Detectar si es usuario Farmacia/Admin (puede usar formulario de movimientos y salida masiva)
  const esFarmacia = rolPrincipal === 'FARMACIA' || rolPrincipal === 'ADMIN';
  
  // ISS-FIX: Permisos diferenciados por rol
  // - FARMACIA/ADMIN: pueden hacer entradas Y salidas desde este módulo
  // - MEDICO/CENTRO: NO pueden registrar desde aquí. Usan:
  //   * Dispensaciones → para salidas por receta/consumo
  //   * Requisiciones → para solicitar medicamentos
  // Este módulo es INFORMATIVO para usuarios de centro
  const puedeRegistrarMovimiento = esFarmacia; // Solo farmacia/admin pueden usar este formulario
  const puedeHacerEntradas = esFarmacia; // Solo farmacia/admin pueden reabastecer
  const puedeExportar = permisos?.exportarMovimientos === true;
  
  const [movimientos, setMovimientos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageGrupos, setPageGrupos] = useState(1);  // ISS-FIX: Página separada para vista agrupada
  const [total, setTotal] = useState(0);
  const [totalGrupos, setTotalGrupos] = useState(0);  // ISS-FIX: Total de grupos
  const [stats, setStats] = useState({ entradas: 0, salidas: 0, balance: 0 });
  const [expandedId, setExpandedId] = useState(highlightId || null);
  const [vistaAgrupada, setVistaAgrupada] = useState(true); // Por defecto agrupada
  const [gruposExpandidos, setGruposExpandidos] = useState(new Set());
  
  // ISS-FIX: Estado para datos de vista agrupada (viene del backend) - DEBE estar antes del useMemo
  const [datosAgrupados, setDatosAgrupados] = useState(null);

  // Filtros aplicados (los que realmente se envían al backend)
  // Si el usuario tiene centro asignado (no es admin/farmacia), pre-filtrar por su centro
  const centroInicial = !puedeVerTodosCentros && centroUsuario ? centroUsuario.toString() : "";
  
  const [filtrosAplicados, setFiltrosAplicados] = useState({
    fecha_inicio: "",
    fecha_fin: "",
    tipo: "",
    subtipo_salida: "",
    origen: "",
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
    origen: "",
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

  // Formulario de registro de movimientos
  // - FARMACIA/ADMIN: pueden elegir entre "entrada" y "salida"
  // - MEDICO/CENTRO: solo pueden hacer "salida" (dispensación/consumo)
  const [formData, setFormData] = useState({
    lote: "",
    tipo: "salida",  // Por defecto: Salida
    cantidad: "",
    centro: "",
    observaciones: "",
    subtipo_salida: esFarmacia ? "transferencia" : (esMedico ? "receta" : "consumo_interno"),
    numero_expediente: "",
    folio_documento: "",  // FORMATO B: Folio/número de documento oficial
    fecha_salida: "",  // Fecha real de salida física del medicamento
  });
  const [productoFiltro, setProductoFiltro] = useState("");
  const [productoBusqueda, setProductoBusqueda] = useState(""); // Texto de búsqueda del producto
  const [showProductoDropdown, setShowProductoDropdown] = useState(false); // Mostrar dropdown de productos
  const productoDropdownRef = useRef(null); // Ref para cerrar al hacer click fuera
  const [submitting, setSubmitting] = useState(false);
  const [exporting, setExporting] = useState(null); // 'pdf' | 'excel' | null
  const [showFiltersMenu, setShowFiltersMenu] = useState(false);
  const [showSalidaMasiva, setShowSalidaMasiva] = useState(false); // Modal salida masiva
  const [errorState, setErrorState] = useState(null); // { status, message } — for 403/422/500 display
  
  // ISS-SEC FIX: Modal de confirmación para merma/caducidad (operaciones irreversibles)
  const [showConfirmMerma, setShowConfirmMerma] = useState(false);
  const [confirmStep, setConfirmStep] = useState(1); // 1: mostrar resumen, 2: confirmar texto
  // MOV-FECHA: Modal de doble confirmación cuando se establece fecha de salida diferente
  const [showConfirmFechaSalida, setShowConfirmFechaSalida] = useState(false);

  const columnas = useMemo(
    () => ["producto", "tipo", "cantidad", "centro", "fecha"],
    []
  );

  // Función auxiliar para verificar si un lote está vencido
  const estaVencido = useCallback((lote) => {
    if (!lote.fecha_caducidad) return false;
    const fechaCad = new Date(lote.fecha_caducidad);
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    return fechaCad < hoy;
  }, []);

  // IDs de productos que tienen lotes vencidos (para filtrar cuando es baja por caducidad)
  const productosConLotesVencidos = useMemo(() => {
    const ids = new Set();
    lotes.forEach(l => {
      if (l.cantidad_actual > 0 && estaVencido(l)) {
        ids.add(l.producto);
      }
    });
    return ids;
  }, [lotes, estaVencido]);

  // Filtrar productos según texto de búsqueda Y tipo de movimiento
  const productosFiltrados = useMemo(() => {
    let filtrados = productos;
    
    // Si es baja por caducidad, mostrar solo productos con lotes vencidos
    if (formData.subtipo_salida === 'caducidad') {
      filtrados = filtrados.filter(p => productosConLotesVencidos.has(p.id));
    }
    
    // Aplicar filtro de búsqueda por texto
    if (productoBusqueda.trim()) {
      const busqueda = productoBusqueda.toLowerCase().trim();
      filtrados = filtrados.filter(p => 
        p.clave?.toLowerCase().includes(busqueda) ||
        p.nombre?.toLowerCase().includes(busqueda)
      );
    }
    
    return filtrados;
  }, [productos, productoBusqueda, formData.subtipo_salida, productosConLotesVencidos]);

  // Cerrar dropdown al hacer click fuera
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (productoDropdownRef.current && !productoDropdownRef.current.contains(event.target)) {
        setShowProductoDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const cargarCatalogos = useCallback(async () => {
    try {
      // Cargar productos (todos pueden ver el catálogo de productos)
      const prodResp = await productosAPI.getAll({ page_size: 500, ordering: "clave", activo: true });
      // Ordenar por clave numérica
      const productosOrdenados = (prodResp.data.results || prodResp.data || []).sort((a, b) => {
        const claveA = parseInt(a.clave) || 0;
        const claveB = parseInt(b.clave) || 0;
        return claveA - claveB;
      });
      setProductos(productosOrdenados);
      
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
      // ISS-FIX (reabastecimiento): FARMACIA/ADMIN necesitan ver lotes sin stock para reabastecer
      const lotesParamsBase = { 
        page_size: 500, 
        ordering: "-fecha_caducidad", 
      };
      
      // ISS-FIX: Farmacia/Admin ven lotes de farmacia central para transferencias
      // FARMACIA/ADMIN: cargar TODOS los lotes (activos e inactivos) para poder reabastecer
      // CENTRO/MEDICO: solo lotes activos con stock
      if (puedeVerTodosCentros) {
        lotesParamsBase.centro = "central";  // Farmacia central
        // ISS-FIX: Incluir lotes inactivos (cantidad=0) para reabastecimiento
        // NO pasar filtro activo = backend devuelve todos
        lotesParamsBase.incluir_inactivos = true;  // Parámetro explícito para incluir inactivos
      } else if (centroUsuario) {
        // Usuario de centro/médico ve lotes de su centro (los surtidos por farmacia)
        lotesParamsBase.centro = centroUsuario;
        lotesParamsBase.activo = true;  // Centro solo ve lotes activos (con stock)
      }
      
      const lotesResp = await lotesAPI.getAll(lotesParamsBase);
      const lotesData = lotesResp.data.results || lotesResp.data || [];
      setLotes(lotesData);
      // ISS-FIX: FARMACIA/ADMIN pueden ver lotes sin stock (para entradas/reabastecimiento)
      // CENTRO solo ve lotes con stock > 0 (solo hacen salidas)
      if (puedeVerTodosCentros) {
        // Farmacia/Admin: mostrar todos los lotes (con y sin stock para reabastecimiento)
        setLotesDisponibles(lotesData);
      } else {
        // Centro: solo lotes con stock disponible
        setLotesDisponibles(lotesData.filter(l => l.cantidad_actual > 0));
      }
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
  // ISS-FIX: Ahora detecta tanto salidas masivas [SAL-...] como movimientos por requisición
  const extraerGrupoSalida = (mov) => {
    const motivo = mov.observaciones || mov.motivo || '';
    
    // Patrón 1: Salidas masivas [SAL-xxx]
    const matchSalida = motivo.match(/\[(SAL-[^\]]+)\]/);
    if (matchSalida) return matchSalida[1];
    
    // Patrón 2: Movimientos por requisición (SALIDA_POR_REQUISICION REQ-xxx o ENTRADA_POR_REQUISICION REQ-xxx)
    const matchRequisicion = motivo.match(/(SALIDA|ENTRADA)_POR_REQUISICION\s+(REQ-[\w-]+)/i);
    if (matchRequisicion) return matchRequisicion[2]; // Solo el folio REQ-xxx
    
    // Patrón 3: Si tiene requisicion_id o requisicion (campo directo)
    if (mov.requisicion_id || mov.requisicion) {
      return `REQ-${mov.requisicion_id || mov.requisicion}`;
    }
    
    // Patrón 4: Transferencias a centro que no tienen grupo explícito pero son del mismo momento
    // Agrupar por timestamp cercano (dentro de 5 segundos) y mismo centro
    if (mov.tipo === 'salida' && mov.subtipo_salida === 'transferencia') {
      const fecha = new Date(mov.fecha_movimiento || mov.fecha).getTime();
      return `TRANSF-${Math.floor(fecha / 5000)}-${mov.centro_id || mov.centro || 'NC'}`;
    }
    
    return null;
  };
  
  // Función para verificar si un movimiento está confirmado
  const estaConfirmado = (mov) => {
    const motivo = mov.observaciones || mov.motivo || '';
    return motivo.includes('[CONFIRMADO]');
  };
  
  // ISS-FIX FLUJO: Función para verificar si un movimiento está pendiente
  const estaPendiente = (mov) => {
    const motivo = mov.observaciones || mov.motivo || '';
    return motivo.includes('[PENDIENTE]');
  };

  // Agrupar movimientos por grupo de salida o requisición
  // ISS-FIX: Ahora usa datos del backend cuando están disponibles
  const movimientosAgrupados = useMemo(() => {
    if (!vistaAgrupada) return null;
    
    // ISS-FIX: Si hay datos del backend, usarlos directamente
    if (datosAgrupados) {
      return {
        grupos: datosAgrupados.grupos || [],
        sinGrupo: datosAgrupados.sin_grupo || [],
        totalElementos: datosAgrupados.total_elementos || 0,
        totalGrupos: datosAgrupados.total_grupos || 0,
        totalSinGrupo: datosAgrupados.total_sin_grupo || 0,
        totalPages: datosAgrupados.total_pages || 1,
      };
    }
    
    // Fallback: agrupar en frontend (solo si no hay datosAgrupados)
    const grupos = new Map();
    const sinGrupo = [];
    
    // ISS-FIX: Primera pasada - agrupar movimientos
    movimientos.forEach(mov => {
      const grupoId = extraerGrupoSalida(mov);
      const motivo = mov.observaciones || mov.motivo || '';
      
      // ISS-FIX MEJORADO: Criterios de agrupación más amplios
      // 1. Tiene grupo SAL-xxx (salida masiva)
      // 2. Tiene grupo REQ-xxx (requisición)
      // 3. Tiene grupo TRANSF-xxx (transferencias agrupadas por timestamp)
      // 4. Tiene grupo AUTO-xxx (salidas de centro agrupadas automáticamente)
      // 5. Cualquier transferencia a centro
      const esSalidaMasiva = grupoId?.startsWith('SAL-');
      const esRequisicion = grupoId?.startsWith('REQ-') || motivo.includes('_POR_REQUISICION');
      const esTransferencia = grupoId?.startsWith('TRANSF-') || (mov.tipo === 'salida' && mov.subtipo_salida === 'transferencia');
      const esSalidaCentro = grupoId?.startsWith('AUTO-');
      
      // Determinar si debe agruparse
      const debeAgruparse = grupoId && (esSalidaMasiva || esRequisicion || esTransferencia || esSalidaCentro);
      
      if (debeAgruparse) {
        if (!grupos.has(grupoId)) {
          // Determinar tipo de grupo y colores
          let tipoGrupo = 'transferencia';
          if (grupoId.startsWith('SAL-')) tipoGrupo = 'salida_masiva';
          else if (grupoId.startsWith('REQ-')) tipoGrupo = 'requisicion';
          else if (grupoId.startsWith('TRANSF-')) tipoGrupo = 'transferencia';
          else if (grupoId.startsWith('AUTO-')) tipoGrupo = 'transferencia_centro';
          
          grupos.set(grupoId, {
            id: grupoId,
            tipo_grupo: tipoGrupo,
            items: [],
            // Inicialmente tomar centro del movimiento
            centro_nombre: mov.centro_nombre || 'Almacén Central',
            centro_id: mov.centro_id || mov.centro,
            // Priorizar fecha_salida (fecha real de salida física) sobre fecha del sistema
            fecha: mov.fecha_salida || mov.fecha || mov.fecha_movimiento,
            usuario_nombre: mov.usuario_nombre || 'Sistema',
            // Contadores detallados
            salidas: [],
            entradas: [],
            cantidad_salidas: 0,
            cantidad_entradas: 0,
            num_salidas: 0,
            num_entradas: 0,
            total_cantidad: 0,
            confirmado: estaConfirmado(mov),
            pendiente: estaPendiente(mov),
            requisicion_folio: tipoGrupo === 'requisicion' ? grupoId : null,
          });
        }
        
        const grupo = grupos.get(grupoId);
        grupo.items.push(mov);
        
        // Clasificar el movimiento como entrada o salida
        if (mov.tipo === 'salida') {
          grupo.salidas.push(mov);
          grupo.cantidad_salidas += Math.abs(mov.cantidad || 0);
          grupo.num_salidas += 1;
        } else if (mov.tipo === 'entrada') {
          grupo.entradas.push(mov);
          grupo.cantidad_entradas += Math.abs(mov.cantidad || 0);
          grupo.num_entradas += 1;
          // Capturar centro destino de las entradas
          if (mov.centro_nombre && mov.centro_nombre !== 'Almacén Central') {
            grupo.centro_nombre = mov.centro_nombre;
            grupo.centro_id = mov.centro_id || mov.centro;
          }
        }
        
        // Total = lo que salió (o entró si no hay salidas)
        grupo.total_cantidad = grupo.cantidad_salidas || grupo.cantidad_entradas;
        
        // Actualizar estados si algún item lo tiene
        if (estaConfirmado(mov)) grupo.confirmado = true;
        if (estaPendiente(mov)) grupo.pendiente = true;
        
        // Fecha más reciente (priorizar fecha_salida para salidas)
        const fechaEfectiva = mov.fecha_salida || mov.fecha || mov.fecha_movimiento;
        const fechaMov = new Date(fechaEfectiva);
        const fechaGrupo = new Date(grupo.fecha);
        if (fechaMov > fechaGrupo) {
          grupo.fecha = fechaEfectiva;
        }
      } else {
        sinGrupo.push(mov);
      }
    });
    
    // ISS-FIX: Ordenar items dentro de cada grupo (salidas primero, luego entradas)
    grupos.forEach(grupo => {
      grupo.items = [...grupo.salidas, ...grupo.entradas];
    });
    
    // Convertir a array y ordenar por fecha descendente
    const gruposArray = Array.from(grupos.values()).sort((a, b) => 
      new Date(b.fecha) - new Date(a.fecha)
    );
    
    // ISS-FIX: Calcular total de elementos para paginación en frontend
    const totalElementos = gruposArray.length + sinGrupo.length;
    
    // Aplicar paginación en frontend para vista agrupada
    const startIndex = (pageGrupos - 1) * GRUPOS_POR_PAGINA;
    const endIndex = startIndex + GRUPOS_POR_PAGINA;
    
    // Paginar grupos primero, luego individuales
    const gruposPaginados = gruposArray.slice(startIndex, Math.min(endIndex, gruposArray.length));
    const espacioRestante = endIndex - gruposArray.length;
    const sinGrupoPaginados = espacioRestante > 0 ? sinGrupo.slice(0, espacioRestante) : [];
    
    return { 
      grupos: gruposPaginados, 
      sinGrupo: sinGrupoPaginados,
      totalElementos,
      totalGrupos: gruposArray.length,
      totalSinGrupo: sinGrupo.length
    };
  }, [movimientos, vistaAgrupada, pageGrupos, datosAgrupados]);

  // ISS-FIX: Actualizar totalGrupos cuando cambie movimientosAgrupados
  useEffect(() => {
    if (movimientosAgrupados) {
      setTotalGrupos(movimientosAgrupados.totalElementos);
    }
  }, [movimientosAgrupados]);

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
    // Cancel any in-flight request to prevent stale data races
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;
    const thisRequestId = ++requestIdRef.current;

    setLoading(true);
    setErrorState(null); // Clear previous errors
    try {
      if (vistaAgrupada) {
        const params = {
          page: pageGrupos,
          page_size: GRUPOS_POR_PAGINA,
          ordering: "-fecha",
          ...filtrosAplicados,
        };
        Object.keys(params).forEach(key => {
          if (params[key] === "" || params[key] === null || params[key] === undefined) {
            delete params[key];
          }
        });
        
        const response = await movimientosAPI.getAgrupados(params);
        // Discard if a newer request was fired
        if (thisRequestId !== requestIdRef.current) return;
        setDatosAgrupados(response.data);
        setTotalGrupos(response.data.total_elementos || 0);
        setMovimientos([]);
        setTotal(0);
      } else {
        const params = {
          page: page,
          page_size: PAGE_SIZE_INDIVIDUAL,
          ordering: "-fecha",
          ...filtrosAplicados,
        };
        Object.keys(params).forEach(key => {
          if (params[key] === "" || params[key] === null || params[key] === undefined) {
            delete params[key];
          }
        });
        
        const response = await movimientosAPI.getAll(params);
        if (thisRequestId !== requestIdRef.current) return;
        let data = response.data?.results || response.data || [];
        let dataConConfirmado = (Array.isArray(data) ? data : []).map(mov => ({
          ...mov,
          confirmado: estaConfirmado(mov)
        }));
        
        setMovimientos(dataConConfirmado);
        setTotal(response.data?.count || data.length || 0);
        setDatosAgrupados(null);
        calcularStats(dataConConfirmado);
      }
    } catch (err) {
      // Ignore aborted requests
      if (err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError') return;
      if (thisRequestId !== requestIdRef.current) return;

      const status = err.response?.status;
      const detail = err.response?.data?.detail;

      // Clear stale data on error — never show previous results as if valid
      setMovimientos([]);
      setDatosAgrupados(null);
      setTotal(0);
      setTotalGrupos(0);

      if (status === 403) {
        setErrorState({ status: 403, message: detail || 'Sin permisos para ver movimientos de este centro.' });
      } else if (status === 422) {
        setErrorState({ status: 422, message: detail || 'Parámetros de filtro no válidos. Revise los campos.' });
        toast.error(detail || 'Filtro no válido — revise los campos');
      } else if (status === 409) {
        setErrorState({ status: 409, message: detail || 'Conflicto en la solicitud. Intente de nuevo.' });
      } else {
        setErrorState({ status: status || 0, message: detail || 'Error al cargar movimientos. Intente de nuevo.' });
        toast.error(detail || 'No se pudieron cargar los movimientos');
      }
    } finally {
      if (thisRequestId === requestIdRef.current) {
        setLoading(false);
      }
    }
  }, [page, pageGrupos, filtrosAplicados, vistaAgrupada]);

  useEffect(() => {
    cargarCatalogos();
  }, [cargarCatalogos]);

  // ISS-FIX: Resetear páginas cuando cambia la vista
  useEffect(() => {
    setPage(1);
    setPageGrupos(1);
    setGruposExpandidos(new Set());
  }, [vistaAgrupada]);

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

  // ─── URL state sync: persist applied filters in URL for sharing / back-navigation ───
  const urlSyncInitDone = useRef(false);
  const FILTER_URL_KEYS = ['tipo', 'subtipo_salida', 'origen', 'producto', 'centro', 'lote', 'search', 'fecha_inicio', 'fecha_fin', 'estado_confirmacion'];

  // On mount: read filters from URL query string (only once)
  useEffect(() => {
    if (urlSyncInitDone.current) return;
    urlSyncInitDone.current = true;
    const initial = {};
    let hasUrlFilters = false;
    FILTER_URL_KEYS.forEach(key => {
      const val = searchParams.get(key);
      if (val) { initial[key] = val; hasUrlFilters = true; }
    });
    if (hasUrlFilters) {
      const merged = { ...filtros, ...initial };
      // Respect centro restriction
      if (!puedeVerTodosCentros && centroUsuario) {
        merged.centro = centroUsuario.toString();
      }
      setFiltros(merged);
      setFiltrosAplicados(merged);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Whenever applied filters change, mirror them to URL (replace, no history push)
  useEffect(() => {
    const params = new URLSearchParams();
    FILTER_URL_KEYS.forEach(key => {
      const val = filtrosAplicados[key];
      if (val) params.set(key, val);
    });
    // Only update if different from current URL to avoid re-renders
    const currentSearch = searchParams.toString();
    const newSearch = params.toString();
    if (currentSearch !== newSearch) {
      setSearchParams(params, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtrosAplicados]);

  // Escuchar evento de limpieza de inventario para refrescar Movimientos
  useEffect(() => {
    const handleInventarioLimpiado = (event) => {
      console.log('🧹 Inventario limpiado, refrescando Movimientos...', event.detail);
      cargarMovimientos();
    };
    
    window.addEventListener('inventarioLimpiado', handleInventarioLimpiado);
    
    return () => {
      window.removeEventListener('inventarioLimpiado', handleInventarioLimpiado);
    };
  }, [cargarMovimientos]);

  // Scroll al movimiento resaltado cuando viene del dashboard
  useEffect(() => {
    if (highlightId && highlightRef.current && !loading) {
      setTimeout(() => {
        highlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 300);
    }
  }, [highlightId, loading, movimientos]);

  // Filtrar lotes cuando cambia el producto o el tipo de movimiento
  // FARMACIA/ADMIN pueden ver lotes sin stock si van a hacer una ENTRADA
  // CENTRO solo ve lotes con stock > 0 (solo pueden hacer salidas)
  // FILTRO ESPECIAL: Caducidad = solo lotes vencidos, Merma = lotes con stock
  useEffect(() => {
    const esEntrada = formData.tipo === 'entrada';
    const esCaducidad = formData.subtipo_salida === 'caducidad';
    const esMerma = formData.subtipo_salida === 'merma';
    // FARMACIA/ADMIN: mostrar lotes sin stock cuando están en modo ENTRADA
    const mostrarSinStock = esFarmacia && esEntrada;
    
    // Función para verificar si un lote está vencido
    const estaVencido = (lote) => {
      if (!lote.fecha_caducidad) return false;
      const fechaCad = new Date(lote.fecha_caducidad);
      const hoy = new Date();
      hoy.setHours(0, 0, 0, 0);
      return fechaCad < hoy;
    };
    
    // Función para filtrar según tipo de movimiento
    const filtrarLote = (l) => {
      const tieneStock = l.cantidad_actual > 0;
      
      // Para CADUCIDAD: solo lotes vencidos con stock
      if (esCaducidad) {
        return tieneStock && estaVencido(l);
      }
      
      // Para MERMA: lotes con stock (no necesariamente vencidos)
      if (esMerma) {
        return tieneStock;
      }
      
      // Para ENTRADA: incluir sin stock (para reabastecer)
      if (mostrarSinStock) {
        return true;
      }
      
      // Salida normal (transferencia): solo con stock
      return tieneStock;
    };
    
    if (productoFiltro) {
      const lotesFiltrados = lotes.filter(l => {
        const esDelProducto = l.producto === parseInt(productoFiltro);
        return esDelProducto && filtrarLote(l);
      });
      setLotesDisponibles(lotesFiltrados);
      setFormData(prev => ({ ...prev, lote: "" }));
    } else {
      // Sin filtro de producto - aplicar filtros según tipo
      setLotesDisponibles(lotes.filter(filtrarLote));
    }
  }, [productoFiltro, lotes, formData.tipo, formData.subtipo_salida, esFarmacia]);

  const handleFormChange = (field, value) => {
    setFormData(prev => {
      const newState = { ...prev, [field]: value };
      
      // ISS-FIX: Limpiar campos según el tipo de movimiento
      if (field === "tipo") {
        if (value === "entrada") {
          // Para entradas: limpiar centro destino y subtipo
          newState.centro = "";
          newState.subtipo_salida = "";
          newState.numero_expediente = "";
        } else if (value === "salida") {
          // Para salidas: establecer subtipo por defecto
          newState.subtipo_salida = "transferencia";
        }
        // Limpiar lote al cambiar tipo (el filtro de lotes cambia)
        newState.lote = "";
      }
      
      // ISS-FIX: Limpiar lote y producto al cambiar subtipo (merma/caducidad filtran diferente)
      if (field === "subtipo_salida") {
        newState.lote = "";
      }
      
      return newState;
    });
  };

  const getLoteLabel = (lote) => {
    const producto = productos.find(p => p.id === lote.producto);
    const fechaCad = lote.fecha_caducidad ? new Date(lote.fecha_caducidad).toLocaleDateString() : 'S/F';
    const stockInfo = lote.cantidad_actual > 0 
      ? `${lote.cantidad_actual} uds` 
      : '⚠️ SIN STOCK';
    return `${lote.numero_lote} - ${producto?.nombre?.substring(0, 25) || 'Producto'} (${stockInfo}, Cad: ${fechaCad})`;
  };

  const registrarMovimiento = async () => {
    // Validaciones básicas
    if (!formData.lote) {
      toast.error("Selecciona un lote");
      return;
    }
    if (!formData.cantidad || Number(formData.cantidad) <= 0) {
      toast.error("Ingresa una cantidad válida mayor a 0");
      return;
    }
    
    // MOV-FECHA: Validar que fecha de salida no sea futura (defensa frontend)
    if (formData.fecha_salida && new Date(formData.fecha_salida) > new Date()) {
      toast.error("La fecha de salida no puede ser una fecha futura");
      return;
    }
    
    // =========================================================================
    // HALLAZGO #1 FIX (RACE CONDITION): Verificar stock ACTUALIZADO antes de enviar
    // El estado local 'lotes' puede estar desactualizado si otro usuario/pestaña
    // modificó el stock. Hacemos un refetch del lote antes de validar.
    // NOTA: El backend TAMBIÉN valida, esto es defensa en profundidad + mejor UX
    // =========================================================================
    let loteSeleccionado = lotes.find(l => l.id === parseInt(formData.lote));
    const esEntrada = formData.tipo === "entrada";
    const esSalida = formData.tipo === "salida";
    
    // Para salidas, verificar stock actualizado del backend antes de proceder
    if (esSalida && loteSeleccionado) {
      try {
        const respLote = await lotesAPI.getById(parseInt(formData.lote));
        const stockActual = respLote.data?.cantidad_actual ?? respLote.data?.stock_disponible;
        
        // Actualizar referencia local con dato fresco
        loteSeleccionado = { ...loteSeleccionado, cantidad_actual: stockActual };
        
        // Validar con stock actualizado
        if (Number(formData.cantidad) > stockActual) {
          toast.error(
            `⚠️ Stock actualizado insuficiente. Disponible ahora: ${stockActual} (antes: ${lotes.find(l => l.id === parseInt(formData.lote))?.cantidad_actual || '?'}). ` +
            `Otro usuario/proceso pudo haber consumido stock. Recargando catálogo...`
          );
          // Refrescar catálogo para mostrar datos actualizados
          cargarCatalogos();
          return;
        }
      } catch (err) {
        console.warn('Error verificando stock actualizado, continuando con validación de backend:', err);
        // No bloquear - el backend también valida. Solo log de warning.
      }
    }
    
    // Validaciones específicas para SALIDA
    if (esSalida) {
      // ISS-SEC FIX: Validar centro destino SOLO para transferencias entre centros
      // Otros subtipos (merma, caducidad, consumo_interno, receta) no requieren centro destino
      if (formData.subtipo_salida === 'transferencia' && !formData.centro) {
        toast.error("Selecciona el centro destino para la transferencia");
        return;
      }
      
      // Validar que no exceda el stock disponible
      if (loteSeleccionado && Number(formData.cantidad) > loteSeleccionado.cantidad_actual) {
        toast.error(`Inventario insuficiente. Disponible: ${loteSeleccionado.cantidad_actual}`);
        return;
      }
      
      // MEDICO: siempre requiere expediente (siempre es dispensación por receta)
      if (esMedico && !formData.numero_expediente?.trim()) {
        toast.error("Debe ingresar el número de expediente del paciente");
        return;
      }
      
      // CENTRO: validar expediente solo si eligió receta
      if (!esMedico && formData.subtipo_salida === 'receta' && !formData.numero_expediente?.trim()) {
        toast.error("Debe ingresar el número de expediente para dispensación por receta");
        return;
      }
      
      // Validar observaciones para médicos
      if (esMedico && (!formData.observaciones || formData.observaciones.trim().length < 5)) {
        toast.error("Indique el motivo de la dispensación (mínimo 5 caracteres)");
        return;
      }
      
      // ISS-FIX: Validar observaciones obligatorias para TODOS (farmacia/admin también)
      // ISS-SEC FIX: Para merma/caducidad, requerir observaciones más detalladas
      const esMermaOCaducidad = ['merma', 'caducidad'].includes(formData.subtipo_salida);
      const longitudMinima = esMermaOCaducidad ? 15 : 5;
      if (!esMedico && (!formData.observaciones || formData.observaciones.trim().length < longitudMinima)) {
        const ejemplos = esMermaOCaducidad 
          ? "Ej: 'Producto dañado por humedad', 'Lote vencido el 15/01/2026'"
          : "Ej: 'Transferencia a centro', 'Dispensación por receta'";
        toast.error(`Las observaciones son obligatorias (mínimo ${longitudMinima} caracteres). ${ejemplos}`);
        return;
      }
    }
    
    // Validaciones específicas para ENTRADA
    if (esEntrada) {
      // Para entradas, la observación es obligatoria (trazabilidad)
      if (!formData.observaciones || formData.observaciones.trim().length < 5) {
        toast.error("Para entradas, debe indicar el motivo (mínimo 5 caracteres). Ej: 'Nueva compra', 'Devolución proveedor'");
        return;
      }
      
      // ISS-SEC FIX: Validar que el lote tenga fecha de caducidad válida
      if (loteSeleccionado && !loteSeleccionado.fecha_caducidad) {
        toast.error("No se pueden registrar entradas a lotes sin fecha de caducidad");
        return;
      }
    }
    
    // MOV-FECHA: Doble confirmación cuando se establece una fecha de salida distinta
    if (esSalida && formData.fecha_salida && !showConfirmFechaSalida && !showConfirmMerma) {
      setShowConfirmFechaSalida(true);
      return; // No continuar hasta confirmar
    }
    
    // ISS-SEC FIX: Para merma/caducidad, mostrar modal de confirmación de varios pasos
    const esMermaOCaducidad = ['merma', 'caducidad'].includes(formData.subtipo_salida);
    if (esSalida && esMermaOCaducidad && puedeHacerEntradas && !showConfirmMerma) {
      setShowConfirmMerma(true);
      setConfirmStep(1);
      return; // No continuar hasta confirmar
    }

    setSubmitting(true);
    try {
      // ISS-SEC FIX: Merma/Caducidad usa flujo normal (no salida_masiva) y NO tiene centro_destino
      const esMermaOCaducidad = ['merma', 'caducidad'].includes(formData.subtipo_salida);
      
      // CASO ESPECIAL: Transferencias a centro (FARMACIA/ADMIN) - NO aplica para merma/caducidad
      // Usar API de salida_masiva para seguir flujo PENDIENTE
      if (esSalida && puedeHacerEntradas && formData.centro && formData.subtipo_salida === 'transferencia') {
        const payloadMasiva = {
          centro_destino_id: parseInt(formData.centro),
          observaciones: formData.observaciones || '',
          auto_confirmar: false, // PENDIENTE hasta confirmar entrega física
          fecha_salida: formData.fecha_salida || null,
          items: [{
            lote_id: parseInt(formData.lote),
            cantidad: Number(formData.cantidad)
          }]
        };
        
        const resp = await salidaMasivaAPI.procesar(payloadMasiva);
        
        if (resp.data.success) {
          toast.success(`✅ Transferencia registrada como PENDIENTE. Folio: ${resp.data.grupo_salida}. Confirme la entrega desde la lista de movimientos.`);
        } else {
          toast.error(resp.data.message || 'Error al procesar transferencia');
          return;
        }
      } else {
        // =====================================================================
        // HALLAZGO #2 DOCUMENTACIÓN: Lógica de Merma/Caducidad
        // =====================================================================
        // Las mermas y caducidades son operaciones contables especiales:
        //   - NO tienen centro destino (el stock se "pierde", no se transfiere)
        //   - Se descuentan del almacén central (centro=null en backend)
        //   - Requieren justificación obligatoria (validada en backend también)
        //
        // La lógica de "si es merma NO enviar centro" está aquí por diseño:
        //   - El backend (registrar_movimiento_stock) interpreta centro=null
        //     como "operación sobre almacén central"
        //   - Si enviáramos centro, se interpretaría como transferencia
        //
        // VALIDACIÓN BACKEND: El backend también valida:
        //   - Longitud mínima de observaciones para ajustes/mermas
        //   - Stock suficiente antes de descontar
        //   - Tipo de movimiento válido
        // =====================================================================
        
        // CASO NORMAL: Merma/caducidad, entradas, dispensaciones, consumos
        const payload = {
          lote: parseInt(formData.lote),
          tipo: formData.tipo,
          cantidad: Number(formData.cantidad),
          observaciones: formData.observaciones || '',
          folio_documento: formData.folio_documento?.trim() || null,
          fecha_salida: formData.fecha_salida || null,
        };
        
        // Campos adicionales para SALIDA (no transferencias)
        if (esSalida) {
          // LÓGICA DE NEGOCIO: Para merma/caducidad, NO enviar centro
          // (se descuenta del almacén central, no es una transferencia)
          // Solo MEDICO/CENTRO envían su centro para dispensaciones
          if (centroUsuario && !esMermaOCaducidad) {
            payload.centro = parseInt(centroUsuario);
          }
          
          // ISS-SEC FIX: Siempre enviar subtipo_salida para todas las salidas
          // MEDICO: siempre es "receta" | Otros: usa el subtipo seleccionado
          payload.subtipo_salida = esMedico ? "receta" : (formData.subtipo_salida || "consumo_interno");
          
          // Agregar expediente para dispensación por receta
          if ((esMedico || formData.subtipo_salida === 'receta') && formData.numero_expediente) {
            payload.numero_expediente = formData.numero_expediente.trim();
          }
        }
        
        await movimientosAPI.create(payload);
        
        // Mensaje según tipo y rol
        let mensajeExito = "";
        if (esEntrada) {
          mensajeExito = "✅ Entrada registrada exitosamente - Stock incrementado";
        } else if (esMedico) {
          mensajeExito = "✅ Dispensación registrada exitosamente";
        } else if (esMermaOCaducidad) {
          const tipoSalida = formData.subtipo_salida === 'merma' ? 'MERMA' : 'CADUCIDAD';
          mensajeExito = `✅ Salida por ${tipoSalida} registrada. El stock se descontó del inventario. Se generó registro en historial.`;
        } else {
          mensajeExito = "✅ Salida registrada exitosamente";
        }
        
        toast.success(mensajeExito);
      }
      
      // ISS-SEC FIX: Resetear modal de confirmación
      setShowConfirmMerma(false);
      setShowConfirmFechaSalida(false);
      setConfirmStep(1);
      
      // Reset del formulario
      setFormData({
        lote: "",
        tipo: "salida",
        cantidad: "",
        centro: "",
        observaciones: "",
        subtipo_salida: puedeHacerEntradas ? "transferencia" : (esMedico ? "receta" : "consumo_interno"),
        numero_expediente: "",
        folio_documento: "",
        fecha_salida: "",
      });
      setProductoFiltro("");
      setProductoBusqueda("");
      cargarMovimientos();
      cargarCatalogos();
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.response?.data?.mensaje || 
                       err.response?.data?.detail || err.response?.data?.cantidad?.[0] ||
                       err.response?.data?.message || err.response?.data?.errores?.join(', ') ||
                       "No se pudo registrar el movimiento";
      toast.error(errorMsg);
      // ISS-SEC FIX: Resetear modal en caso de error también
      setShowConfirmMerma(false);
      setShowConfirmFechaSalida(false);
      setConfirmStep(1);
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
    
    const win = abrirPdfEnNavegador(); // Pre-abrir pestaña (preserva user-gesture)
    if (!win) return;

    setExporting('pdf');
    try {
      // Sanitizar filtros: eliminar valores vacíos antes de enviar
      const filtrosLimpios = Object.fromEntries(
        Object.entries(filtrosAplicados).filter(([, v]) => v !== "" && v !== null && v !== undefined)
      );
      const response = await movimientosAPI.exportarPdf(filtrosLimpios);
      abrirPdfEnNavegador(response, win);
      toast.success("PDF generado");
    } catch (err) {
      toast.error(err.response?.data?.detail || "No se pudo generar el PDF");
    } finally {
      setExporting(null);
    }
  };

  // Descargar recibo de salida con campos de firma
  const descargarReciboSalida = async (movimiento) => {
    const win = abrirPdfEnNavegador();
    if (!win) return;
    try {
      toast.loading("Generando recibo...", { id: "recibo" });
      const response = await movimientosAPI.getReciboSalida(movimiento.id);
      // ISS-FIX: Usar response.data ya que axios devuelve los datos en .data
      abrirPdfEnNavegador(response.data || response, win);
      toast.success("Recibo generado", { id: "recibo" });
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.response?.data?.detail || err.message || "No se pudo generar el recibo";
      toast.error(errorMsg, { id: "recibo" });
      console.error("Error generando recibo:", err);
    }
  };

  // Descargar recibo de entrega finalizada (con sello ENTREGADO en lugar de firmas)
  const descargarReciboFinalizado = async (movimiento) => {
    const win = abrirPdfEnNavegador();
    if (!win) return;
    try {
      toast.loading("Generando comprobante de entrega...", { id: "recibo-final" });
      const response = await movimientosAPI.getReciboSalida(movimiento.id, true);
      // ISS-FIX: Usar response.data ya que axios devuelve los datos en .data
      abrirPdfEnNavegador(response.data || response, win);
      toast.success("Comprobante generado", { id: "recibo-final" });
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.response?.data?.detail || err.message || "No se pudo generar el comprobante";
      toast.error(errorMsg, { id: "recibo-final" });
      console.error("Error generando comprobante:", err);
    }
  };

  // Descargar hoja de entrega para grupo de salida masiva
  const descargarHojaEntregaGrupo = async (grupoId) => {
    const win = abrirPdfEnNavegador();
    if (!win) return;
    try {
      toast.loading("Generando hoja de entrega...", { id: "hoja-grupo" });
      const response = await salidaMasivaAPI.hojaEntregaPdf(grupoId, false);
      abrirPdfEnNavegador(response.data, win);
      toast.success("Hoja de entrega lista", { id: "hoja-grupo" });
    } catch (err) {
      toast.error("No se pudo generar la hoja de entrega", { id: "hoja-grupo" });
      console.error("Error generando hoja:", err);
    }
  };

  // Descargar comprobante de entrega para grupo de salida masiva
  const descargarComprobanteGrupo = async (grupoId) => {
    const win = abrirPdfEnNavegador();
    if (!win) return;
    try {
      toast.loading("Generando comprobante de entrega...", { id: "comp-grupo" });
      const response = await salidaMasivaAPI.hojaEntregaPdf(grupoId, true);
      abrirPdfEnNavegador(response.data, win);
      toast.success("Comprobante de entrega listo", { id: "comp-grupo" });
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
  
  // Estados para confirmación en 2 pasos y modal de éxito
  const [confirmConfirmarGrupo, setConfirmConfirmarGrupo] = useState(null); // {id, centro_nombre, items, total_cantidad}
  const [resultadoConfirmacion, setResultadoConfirmacion] = useState(null); // Resultado exitoso para mostrar modal
  
  const confirmarEntregaGrupo = async (grupoId) => {
    setConfirmandoGrupo(grupoId);
    try {
      toast.loading("Confirmando entrega...", { id: "confirmar-grupo" });
      const response = await salidaMasivaAPI.confirmarEntrega(grupoId);
      toast.dismiss("confirmar-grupo");
      
      // Guardar resultado para mostrar modal de éxito
      setResultadoConfirmacion({
        grupoId: grupoId,
        centroNombre: confirmConfirmarGrupo?.centro_nombre || 'Centro',
        itemsConfirmados: response.data?.items_confirmados || [],
        mensaje: response.data?.message || 'Entrega confirmada exitosamente',
        totalItems: response.data?.items_confirmados?.length || 0
      });
      
      // Cerrar modal de confirmación
      setConfirmConfirmarGrupo(null);
      
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
  
  // Cancelar salida masiva PENDIENTE (solo elimina movimientos, el stock nunca fue descontado)
  const cancelarSalidaGrupo = async (grupoId) => {
    setCancelandoGrupo(grupoId);
    try {
      toast.loading("Cancelando salida pendiente...", { id: "cancelar-grupo" });
      const response = await salidaMasivaAPI.cancelar(grupoId);
      const itemsCancelados = response.data?.items_cancelados?.length || 0;
      toast.success(`Salida cancelada. ${itemsCancelados} movimientos eliminados.`, { id: "cancelar-grupo" });
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

  // ===========================================================================
  // HALLAZGO #4 DOCUMENTACIÓN: Filtros de Centro y Seguridad Multi-tenant
  // ===========================================================================
  // Aunque la UI bloquea cambios al filtro de centro para usuarios restringidos,
  // la SEGURIDAD REAL está en el BACKEND:
  //
  // Backend (inventario/views_legacy.py - MovimientosViewSet.get_queryset):
  //   - Usuarios con centro asignado: queryset.filter(centro_origen=user.centro)
  //   - Ignora cualquier parámetro 'centro' enviado por el frontend
  //   - Solo ADMIN/FARMACIA pueden ver movimientos de otros centros
  //
  // Este bloqueo en UI es solo para UX (evitar confusión), no para seguridad.
  // Un usuario malicioso que modifique el estado de React seguirá viendo
  // solo SUS movimientos porque el backend filtra por token/sesión real.
  // ===========================================================================
  
  // Actualiza solo el estado local de filtros (sin disparar recarga)
  const handleFiltro = (field, value) => {
    // Protección UI: usuarios de centro no pueden cambiar el filtro de centro
    // (La seguridad real está en el backend - ver documentación arriba)
    if (field === 'centro' && !puedeVerTodosCentros && centroUsuario) {
      return; // Ignorar cambios al filtro de centro para usuarios restringidos
    }
    setFiltros((prev) => {
      const newState = { ...prev, [field]: value };
      // Limpiar subtipo_salida y origen si el tipo cambia a algo que no es salida
      if (field === 'tipo' && value !== 'salida' && value !== '') {
        newState.subtipo_salida = '';
        newState.origen = '';
        // También limpiar estado_confirmacion si cambia de salida (pendiente solo aplica a salidas)
        if (prev.estado_confirmacion === 'pendiente') {
          newState.estado_confirmacion = '';
        }
      }
      // ISS-FIX: Si selecciona "pendiente", automáticamente filtrar solo salidas
      if (field === 'estado_confirmacion' && value === 'pendiente') {
        // Pendiente solo tiene sentido para salidas
        if (newState.tipo !== 'salida' && newState.tipo !== '') {
          newState.tipo = 'salida';
        }
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
    
    // ISS-FIX: Resetear ambas páginas al aplicar filtros
    setPage(1);
    setPageGrupos(1);
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
      origen: "",
      producto: "",
      centro: centroFijo,
      lote: "",
      search: "",
      estado_confirmacion: "",
    };
    setFiltros(filtrosVacios);
    setFiltrosAplicados(filtrosVacios);
    // ISS-FIX: Resetear ambas páginas al limpiar filtros
    setPage(1);
    setPageGrupos(1);
  };

  return (
    <div className="space-y-6 p-4 sm:p-6 max-w-[1600px] mx-auto">
      {/* 🎯 HEADER PREMIUM con gradiente institucional del tema */}
      <div className="rounded-2xl overflow-hidden shadow-xl">
        <div className="bg-theme-gradient p-6 text-white relative">
          {/* Decoración de fondo */}
          <div className="absolute inset-0 opacity-10">
            <div className="absolute top-0 right-0 w-64 h-64 bg-white rounded-full blur-3xl transform translate-x-1/3 -translate-y-1/3"></div>
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-white rounded-full blur-3xl transform -translate-x-1/3 translate-y-1/3"></div>
          </div>
          
          <div className="relative flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="bg-gradient-to-br from-white/20 to-white/5 p-4 rounded-2xl backdrop-blur-sm border border-white/10 shadow-lg">
                <FaExchangeAlt size={28} className="text-white" />
              </div>
              <div>
                <h1 className="text-2xl sm:text-3xl font-black tracking-tight">Movimientos de Inventario</h1>
                <p className="text-white/70 text-sm mt-1 flex items-center gap-2">
                  {vistaAgrupada ? (
                    <>
                      <span className="inline-flex items-center gap-1">
                        <FaLayerGroup className="text-xs" />
                        {hayFiltrosActivos ? 'Filtrados:' : 'Total:'} 
                        <span className="font-bold text-white">{totalGrupos}</span> {totalGrupos === 1 ? 'grupo' : 'grupos'}
                      </span>
                      {movimientosAgrupados && (
                        <span className="hidden sm:inline text-white/50">
                          • {movimientosAgrupados.totalGrupos || 0} agrupados, {movimientosAgrupados.totalSinGrupo || 0} individuales
                        </span>
                      )}
                    </>
                  ) : (
                    <>
                      <FaList className="text-xs" />
                      {hayFiltrosActivos ? 'Filtrados:' : 'Total:'} <span className="font-bold text-white">{total}</span> movimientos
                    </>
                  )}
                </p>
              </div>
            </div>
            
            {!esMedico && hayFiltrosActivos && (
              <span className="bg-gradient-to-r from-amber-500 to-orange-500 px-4 py-1.5 rounded-full text-xs font-bold shadow-lg">
                ⚡ {Object.values(filtrosAplicados).filter(v => v !== "").length} filtros activos
              </span>
            )}
            
            <div className="flex flex-wrap gap-2 sm:gap-3">
              {/* Botón Salida Masiva - Solo Farmacia */}
              {esFarmacia && (
                <button
                  onClick={() => setShowSalidaMasiva(true)}
                  className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-all duration-300 bg-gradient-to-r from-pink-500 to-rose-500 text-white hover:from-pink-600 hover:to-rose-600 shadow-lg hover:shadow-xl hover:scale-[1.02]"
                  title="Salida masiva a centros"
                >
                  <FaTruck />
                  <span className="hidden sm:inline">Salida Masiva</span>
                </button>
              )}
              {/* Toggle Vista Agrupada/Individual */}
              <button
                onClick={() => setVistaAgrupada(!vistaAgrupada)}
                className={`
                  flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-all duration-300
                  ${vistaAgrupada 
                    ? 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white shadow-lg hover:shadow-xl hover:scale-[1.02]' 
                    : 'bg-white/10 text-white border border-white/20 hover:bg-white/20'
                  }
                `}
                title={vistaAgrupada ? "Ver movimientos individuales" : "Agrupar salidas masivas"}
              >
                {vistaAgrupada ? <FaLayerGroup /> : <FaList />}
                <span className="hidden sm:inline">{vistaAgrupada ? 'Vista Agrupada' : 'Vista Individual'}</span>
              </button>
              {/* TEMPORALMENTE OCULTO: Exportar PDF/Excel - pendiente de revisión
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
      </div>

      {/* 🏷️ Banner para usuarios CENTRO */}
      {esCentroUser && centroNombre && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4 flex items-center gap-4 shadow-sm">
          <div className="bg-gradient-to-br from-blue-500 to-indigo-500 p-3 rounded-xl shadow-lg">
            <FaInfoCircle className="text-white text-lg" />
          </div>
          <div>
            <p className="text-sm font-bold text-blue-900">
              📍 Movimientos de: {centroNombre}
            </p>
            <p className="text-xs text-blue-600/80">
              Estás viendo solo los movimientos relacionados a tu centro.
            </p>
          </div>
        </div>
      )}

      {/* ⚠️ Aviso si usuario de centro no tiene centro asignado */}
      {esCentroUser && !centroUsuario && (
        <div className="bg-gradient-to-r from-yellow-50 to-amber-50 border-l-4 border-yellow-400 p-4 rounded-xl shadow-sm">
          <div className="flex items-center gap-4">
            <div className="bg-yellow-100 p-3 rounded-xl">
              <FaExclamationTriangle className="text-yellow-600 text-xl" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-yellow-800">Centro no asignado</h3>
              <p className="text-yellow-700 text-sm mt-1">
                Tu cuenta está configurada como usuario de Centro pero no tienes un centro asignado.
                Por favor contacta al administrador para que te asigne un centro.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-6">
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
          {/* 📝 FORMULARIO DE REGISTRO - solo para admin/farmacia */}
          {puedeRegistrarMovimiento ? (
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
            <div className="bg-theme-gradient px-6 py-4">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                Nuevo Movimiento
              </h2>
            </div>
            <div className="p-6 space-y-4">
              {/* 🔄 Tipo de Movimiento - PRIMERO para que el usuario elija la acción */}
              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700">Tipo de Movimiento <span className="text-red-500">*</span></label>
                
                {/* FARMACIA/ADMIN: opciones completas incluyendo merma/caducidad */}
                {puedeHacerEntradas ? (
                  <select
                    value={formData.subtipo_salida === 'merma' ? 'merma' : formData.subtipo_salida === 'caducidad' ? 'caducidad' : formData.tipo}
                    onChange={(e) => {
                      const val = e.target.value;
                      // Limpiar producto y lote al cambiar tipo (los filtros cambian)
                      setProductoFiltro('');
                      setProductoBusqueda('');
                      if (val === 'merma') {
                        handleFormChange("tipo", "salida");
                        handleFormChange("subtipo_salida", "merma");
                      } else if (val === 'caducidad') {
                        handleFormChange("tipo", "salida");
                        handleFormChange("subtipo_salida", "caducidad");
                      } else if (val === 'entrada') {
                        handleFormChange("tipo", "entrada");
                        handleFormChange("subtipo_salida", "transferencia");
                      } else {
                        handleFormChange("tipo", "salida");
                        handleFormChange("subtipo_salida", "transferencia");
                      }
                    }}
                    className="w-full rounded-xl border-2 border-gray-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-800 font-medium transition-all duration-200"
                  >
                    <option value="salida">🚚 Salida / Transferencia a Centro</option>
                    <option value="caducidad">⏰ Baja por Caducidad</option>
                    <option value="entrada">📦 Entrada a Almacén (Nueva compra, reabastecimiento)</option>
                  </select>
                ) : (
                  /* MEDICO/CENTRO: solo pueden hacer salidas */
                  <div className="w-full rounded-xl border-2 border-rose-200 bg-rose-50 px-4 py-3 text-rose-800 font-medium">
                    🏥 Salida / Dispensación de inventario
                  </div>
                )}
                
                {/* Descripción según tipo y rol */}
                {formData.subtipo_salida === 'merma' ? (
                  <div className="p-3 bg-orange-50 border border-orange-300 rounded-lg">
                    <p className="text-xs text-orange-700">
                      <FaExclamationTriangle className="inline mr-1" />
                      <strong>Merma:</strong> Registra pérdida de medicamentos por daño, robo, deterioro u otras causas. 
                      El stock se descuenta permanentemente del inventario. <span className="font-bold">Esta operación es IRREVERSIBLE.</span>
                    </p>
                  </div>
                ) : formData.subtipo_salida === 'caducidad' ? (
                  <div className="p-3 bg-amber-50 border border-amber-300 rounded-lg">
                    <p className="text-xs text-amber-700">
                      <FaClock className="inline mr-1" />
                      <strong>Caducidad:</strong> Registra baja de medicamentos vencidos. Solo se mostrarán lotes con fecha de caducidad expirada.
                      <span className="font-bold"> Esta operación es IRREVERSIBLE.</span>
                    </p>
                  </div>
                ) : formData.tipo === "salida" ? (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg">
                    <p className="text-xs text-rose-700">
                      <FaTruck className="inline mr-1" />
                      {puedeHacerEntradas ? (
                        <><strong>Transferencia:</strong> Envía medicamentos desde Almacén Central hacia un Centro Penitenciario. El stock se descuenta del lote seleccionado.</>
                      ) : esMedico ? (
                        <><strong>Dispensación:</strong> Registra la salida de medicamentos para atención médica. El stock se descuenta del inventario de tu centro.</>
                      ) : (
                        <><strong>Consumo:</strong> Registra la salida de medicamentos de tu centro. El stock se descuenta del inventario asignado.</>
                      )}
                    </p>
                  </div>
                ) : (
                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
                    <p className="text-xs text-emerald-700">
                      <FaBoxes className="inline mr-1" />
                      <strong>Entrada:</strong> Agrega stock a un lote existente (nueva compra, reabastecimiento, devolución). 
                      El stock se suma al lote seleccionado.
                    </p>
                  </div>
                )}
              </div>

              {/* Filtro por producto con búsqueda mejorada */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">
                  Producto (filtro)
                  {formData.subtipo_salida === 'caducidad' && (
                    <span className="ml-2 text-amber-600 normal-case font-normal">- Solo productos con lotes vencidos</span>
                  )}
                </label>
                <div className="relative" ref={productoDropdownRef}>
                  <input
                    type="text"
                    placeholder={
                      formData.subtipo_salida === 'caducidad' 
                        ? "Buscar productos con lotes vencidos..." 
                        : "Buscar producto por clave o nombre..."
                    }
                    value={productoBusqueda}
                    onChange={(e) => {
                      setProductoBusqueda(e.target.value);
                      setShowProductoDropdown(true);
                      // Si borra todo, limpiar también el filtro seleccionado y el lote
                      if (e.target.value === '') {
                        setProductoFiltro('');
                        setFormData(prev => ({ ...prev, lote: '' }));
                      }
                    }}
                    onFocus={() => setShowProductoDropdown(true)}
                    className="w-full rounded-xl border border-gray-200 px-4 py-3 pr-10 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-gray-50 transition-all duration-200"
                  />
                  {(productoFiltro || productoBusqueda) && (
                    <button
                      type="button"
                      onClick={() => {
                        setProductoFiltro('');
                        setProductoBusqueda('');
                        setShowProductoDropdown(false);
                        setFormData(prev => ({ ...prev, lote: '' }));
                      }}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                      title="Limpiar filtro"
                    >
                      ✕
                    </button>
                  )}
                  {/* Dropdown de productos filtrados */}
                  {showProductoDropdown && (
                    <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                      {productos.length === 0 ? (
                        <div className="px-4 py-3 text-sm text-gray-500 text-center">
                          ⏳ Cargando productos...
                        </div>
                      ) : productosFiltrados.length > 0 ? (
                        <>
                          {!productoBusqueda.trim() && (
                            <div className="px-4 py-2 text-xs text-gray-400 bg-gray-50 border-b">
                              ✍️ Escribe para filtrar o selecciona de la lista
                            </div>
                          )}
                          {productosFiltrados.slice(0, 50).map((p) => (
                            <div
                              key={p.id}
                              onClick={() => {
                                setProductoFiltro(p.id.toString());
                                setProductoBusqueda(`${p.clave} - ${p.nombre}`);
                                setShowProductoDropdown(false);
                              }}
                              className={`px-4 py-2 cursor-pointer hover:bg-blue-50 transition-colors ${
                                productoFiltro === p.id.toString() ? 'bg-blue-100 font-semibold' : ''
                              }`}
                            >
                              <span className="font-medium text-gray-900">{p.clave}</span>
                              <span className="text-gray-500"> - {p.nombre}</span>
                            </div>
                          ))}
                          {productosFiltrados.length > 50 && (
                            <div className="px-4 py-2 text-sm text-gray-500 bg-gray-50 border-t">
                              Mostrando 50 de {productosFiltrados.length} productos. Escribe más para filtrar.
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="px-4 py-3 text-sm text-gray-500 text-center">
                          No se encontraron productos con "{productoBusqueda}"
                        </div>
                      )}
                    </div>
                  )}
                </div>
                {/* Mostrar producto seleccionado */}
                {productoFiltro && (() => {
                  const prod = productos.find(p => p.id.toString() === productoFiltro);
                  return prod ? (
                    <div className="flex items-center gap-2 p-2 bg-blue-50 border border-blue-200 rounded-lg text-sm">
                      <FaCheckCircle className="text-blue-600" />
                      <span><strong>{prod.clave}</strong> - {prod.nombre}</span>
                    </div>
                  ) : null;
                })()}
              </div>

              {/* Selección de lote */}
              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700">
                  Lote *
                  {formData.subtipo_salida === 'caducidad' && (
                    <span className="ml-2 text-amber-600 text-xs font-normal">- Solo lotes vencidos</span>
                  )}
                </label>
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
                    <p className="text-orange-700 font-medium">
                      {formData.subtipo_salida === 'caducidad' 
                        ? "No hay lotes vencidos disponibles" 
                        : "No hay lotes disponibles"}
                    </p>
                    {formData.subtipo_salida === 'caducidad' && (
                      <p className="text-orange-600 mt-1">
                        No existen lotes con fecha de caducidad expirada en el inventario.
                      </p>
                    )}
                    {!puedeVerTodosCentros && formData.subtipo_salida !== 'caducidad' && (
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
                  
                  const sinStock = loteInfo.cantidad_actual === 0;
                  const esEntrada = formData.tipo === 'entrada';
                  const estaVencido = loteInfo.fecha_caducidad && new Date(loteInfo.fecha_caducidad) < new Date();
                  
                  return (
                    <div className={`mt-2 p-3 rounded-lg border ${
                      sinStock 
                        ? 'bg-amber-50 border-amber-300' 
                        : estaVencido 
                          ? 'bg-red-50 border-red-300'
                          : 'bg-blue-50 border-blue-200'
                    }`}>
                      <div className={`flex items-center gap-2 ${
                        sinStock ? 'text-amber-800' : estaVencido ? 'text-red-800' : 'text-blue-800'
                      }`}>
                        <FaInfoCircle />
                        <span className="font-semibold">
                          {sinStock ? '⚠️ Lote sin existencias' : estaVencido ? '⚠️ Lote VENCIDO' : 'Stock disponible'}
                        </span>
                      </div>
                      <div className={`mt-1 text-sm ${sinStock ? 'text-amber-700' : estaVencido ? 'text-red-700' : 'text-blue-700'}`}>
                        <div><strong>Producto:</strong> {productoInfo?.nombre || 'N/A'}</div>
                        <div><strong>Lote:</strong> {loteInfo.numero_lote}</div>
                        <div>
                          <strong>Disponible:</strong>{' '}
                          <span className={`font-bold text-lg ${sinStock ? 'text-red-600' : ''}`}>
                            {loteInfo.cantidad_actual}
                          </span> unidades
                        </div>
                        {loteInfo.fecha_caducidad && (
                          <div className={estaVencido ? 'text-red-700 font-semibold' : ''}>
                            <strong>Caducidad:</strong> {new Date(loteInfo.fecha_caducidad).toLocaleDateString()}
                            {estaVencido && ' ⚠️ VENCIDO'}
                          </div>
                        )}
                        {sinStock && esEntrada && (
                          <div className="mt-2 p-2 bg-emerald-100 border border-emerald-300 rounded text-emerald-700 text-xs">
                            💡 <strong>Reabastecimiento:</strong> Puede registrar una entrada para este lote.
                          </div>
                        )}
                        {sinStock && !esEntrada && (
                          <div className="mt-2 p-2 bg-red-100 border border-red-300 rounded text-red-700 text-xs">
                            ⚠️ <strong>Sin stock:</strong> Cambie a "Entrada" para reabastecer este lote.
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })()}
              </div>

              {/* Subtipo de salida para MEDICO/CENTRO */}
              {!puedeHacerEntradas && formData.tipo === "salida" && (
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-gray-700">Motivo de salida <span className="text-red-500">*</span></label>
                  {esMedico ? (
                    /* MÉDICO: Solo dispensación por receta (fijo, no editable) */
                    <div className="w-full rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-blue-800 font-medium">
                      💊 Dispensación por receta
                    </div>
                  ) : (
                    /* CENTRO: Todas las opciones de salida */
                    <select
                      value={formData.subtipo_salida}
                      onChange={(e) => handleFormChange("subtipo_salida", e.target.value)}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    >
                      <option value="consumo_interno">🏥 Consumo interno</option>
                      <option value="receta">💊 Dispensación por receta</option>
                      <option value="merma">📉 Merma</option>
                      <option value="caducidad">⏰ Caducidad</option>
                    </select>
                  )}
                </div>
              )}

              {/* Número de expediente para dispensación por receta (MEDICO siempre, CENTRO cuando selecciona receta) */}
              {(esMedico || formData.subtipo_salida === 'receta') && (
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

              {/* Centro destino - Solo para TRANSFERENCIAS de FARMACIA/ADMIN */}
              {formData.tipo === "salida" && puedeHacerEntradas && formData.subtipo_salida === 'transferencia' && (
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

              {/* FORMATO B: Folio del documento oficial */}
              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700">
                  Folio Documento <span className="text-gray-400 text-xs">(opcional)</span>
                </label>
                <input
                  type="text"
                  value={formData.folio_documento}
                  onChange={(e) => handleFormChange("folio_documento", e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Ej: FACT-2026-001, REQ-001, DON-2026"
                  maxLength={100}
                />
                <p className="text-xs text-gray-500">
                  📋 Número de factura, requisición o documento de referencia para trazabilidad oficial.
                </p>
              </div>

              {/* Fecha de Salida - solo visible para salidas de FARMACIA/ADMIN */}
              {formData.tipo === 'salida' && puedeHacerEntradas && (
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-gray-700">
                    Fecha de Salida <span className="text-gray-400 text-xs">(opcional)</span>
                  </label>
                  <input
                    type="datetime-local"
                    value={formData.fecha_salida}
                    onChange={(e) => handleFormChange("fecha_salida", e.target.value)}
                    max={new Date().toISOString().slice(0, 16)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500">
                    📅 Fecha real de salida física del medicamento. Si no se indica, se usa la fecha de registro en el sistema.
                  </p>
                </div>
              )}

              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700">
                  Observaciones <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={formData.observaciones}
                  onChange={(e) => handleFormChange("observaciones", e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder={
                    formData.tipo === "entrada" 
                      ? "Motivo de la entrada (Ej: Nueva compra, Reabastecimiento, Devolución proveedor)..."
                      : esMedico 
                        ? "Motivo de la dispensación (Ej: Tratamiento dolor, Antibiótico para infección)..."
                        : "Motivo de la transferencia/salida (Ej: Envío a centro, Dispensación por receta)..."
                  }
                  rows={2}
                  required
                />
                <p className="text-xs text-amber-600">
                  <FaInfoCircle className="inline mr-1" />
                  <strong>Obligatorio:</strong> Indique el motivo del movimiento para trazabilidad (mín. 5 caracteres).
                </p>
              </div>

              <button
                onClick={registrarMovimiento}
                disabled={submitting}
                className={`w-full px-4 py-3 rounded-xl font-bold transition-all duration-300 flex items-center justify-center gap-2 shadow-lg hover:shadow-xl disabled:opacity-50 ${
                  formData.tipo === "entrada"
                    ? "bg-gradient-to-r from-emerald-500 to-green-500 text-white hover:from-emerald-600 hover:to-green-600"
                    : "bg-gradient-to-r from-rose-500 to-pink-500 text-white hover:from-rose-600 hover:to-pink-600"
                }`}
              >
                {submitting && <FaSpinner className="animate-spin" />}
                {submitting 
                  ? "Registrando..." 
                  : formData.tipo === "entrada" 
                    ? "📦 Registrar Entrada" 
                    : esMedico 
                      ? "💊 Registrar Dispensación"
                      : puedeHacerEntradas 
                        ? "🚚 Registrar Transferencia" 
                        : "📤 Registrar Salida"
                }
              </button>
            </div>
          </div>
          ) : null}

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
                      <option value="transferencia">🔄 Transferencia</option>
                      <option value="merma">📉 Merma</option>
                      <option value="caducidad">⏰ Caducidad</option>
                      <option value="donacion">🎁 Donación</option>
                      <option value="devolucion">↩️ Devolución</option>
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
                {/* Filtro por origen: Requisición, Salida Masiva, Individual */}
                {(filtros.tipo === "" || filtros.tipo === "salida") && (
                  <div className="flex flex-col gap-1">
                    <label className="text-xs font-semibold text-gray-700">Origen</label>
                    <select
                      value={filtros.origen}
                      onChange={(e) => handleFiltro("origen", e.target.value)}
                      className="border rounded-lg px-3 py-2"
                    >
                      <option value="">Todos</option>
                      <option value="requisicion">📋 Requisición</option>
                      <option value="masiva">📦 Salida Masiva</option>
                      <option value="individual">👤 Individual</option>
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
                {/* ISS-SEC FIX: Ocultar filtro de centro para usuarios que solo ven su centro */}
                {puedeVerTodosCentros && (
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
                )}
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
                  <div className="relative">
                    <input
                      type="text"
                      value={filtros.search}
                      onChange={(e) => handleFiltro("search", e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); aplicarFiltros(); } }}
                      className="border rounded-lg px-3 py-2 pr-8 w-full"
                      placeholder="Producto, lote, expediente o referencia"
                    />
                    {filtros.search && (
                      <button
                        type="button"
                        onClick={() => handleFiltro("search", "")}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-sm font-bold"
                        title="Limpiar búsqueda"
                      >✕</button>
                    )}
                  </div>
                </div>
              </div>

                  <div className="flex gap-2 items-center flex-wrap col-span-full">
                    <button
                      onClick={aplicarFiltros}
                      className="px-4 py-2 rounded-lg text-white text-sm font-semibold transition bg-theme-gradient disabled:opacity-50 disabled:cursor-not-allowed"
                      disabled={loading || submitting}
                    >
                      {loading ? (
                        <span className="flex items-center gap-1"><FaSpinner className="animate-spin text-xs" /> Cargando…</span>
                      ) : hayFiltrosPendientes ? '⚡ Aplicar filtros' : 'Aplicar'}
                    </button>
                    <button
                      onClick={limpiarFiltros}
                      className="px-3 py-2 rounded-lg border bg-white text-sm hover:bg-gray-50 disabled:opacity-50"
                      disabled={loading || !hayFiltrosActivos}
                    >
                      Limpiar todo
                    </button>
                  </div>

                  {/* ═══ Active filter chips ═══ */}
                  {hayFiltrosActivos && (
                    <div className="flex flex-wrap gap-1.5 items-center pt-1 border-t border-gray-200 mt-1">
                      <span className="text-xs text-gray-500 font-medium mr-1">Activos:</span>
                      {filtrosAplicados.tipo && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 text-xs font-medium">
                          Tipo: {filtrosAplicados.tipo}
                          <button onClick={() => { handleFiltro('tipo', ''); setFiltrosAplicados(p => ({ ...p, tipo: '', subtipo_salida: '', origen: '' })); setPage(1); setPageGrupos(1); }} className="ml-0.5 hover:text-indigo-900">✕</button>
                        </span>
                      )}
                      {filtrosAplicados.origen && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-medium">
                          Origen: {filtrosAplicados.origen === 'requisicion' ? 'Requisición' : filtrosAplicados.origen === 'masiva' ? 'Masiva' : 'Individual'}
                          <button onClick={() => { handleFiltro('origen', ''); setFiltrosAplicados(p => ({ ...p, origen: '' })); setPage(1); setPageGrupos(1); }} className="ml-0.5 hover:text-blue-900">✕</button>
                        </span>
                      )}
                      {filtrosAplicados.subtipo_salida && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-pink-100 text-pink-700 text-xs font-medium">
                          Subtipo: {filtrosAplicados.subtipo_salida}
                          <button onClick={() => { handleFiltro('subtipo_salida', ''); setFiltrosAplicados(p => ({ ...p, subtipo_salida: '' })); setPage(1); setPageGrupos(1); }} className="ml-0.5 hover:text-pink-900">✕</button>
                        </span>
                      )}
                      {filtrosAplicados.producto && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 text-xs font-medium">
                          Producto: {productos.find(p => p.id === parseInt(filtrosAplicados.producto))?.clave || filtrosAplicados.producto}
                          <button onClick={() => { handleFiltro('producto', ''); setFiltrosAplicados(p => ({ ...p, producto: '' })); setPage(1); setPageGrupos(1); }} className="ml-0.5 hover:text-emerald-900">✕</button>
                        </span>
                      )}
                      {filtrosAplicados.lote && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 text-xs font-medium">
                          Lote: {lotes.find(l => l.id === parseInt(filtrosAplicados.lote))?.numero_lote || filtrosAplicados.lote}
                          <button onClick={() => { handleFiltro('lote', ''); setFiltrosAplicados(p => ({ ...p, lote: '' })); setPage(1); setPageGrupos(1); }} className="ml-0.5 hover:text-amber-900">✕</button>
                        </span>
                      )}
                      {filtrosAplicados.search && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-200 text-gray-700 text-xs font-medium">
                          Búsqueda: &ldquo;{filtrosAplicados.search}&rdquo;
                          <button onClick={() => { handleFiltro('search', ''); setFiltrosAplicados(p => ({ ...p, search: '' })); setPage(1); setPageGrupos(1); }} className="ml-0.5 hover:text-gray-900">✕</button>
                        </span>
                      )}
                      {filtrosAplicados.centro && puedeVerTodosCentros && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-violet-100 text-violet-700 text-xs font-medium">
                          Centro: {centros.find(c => c.id === parseInt(filtrosAplicados.centro))?.nombre || filtrosAplicados.centro}
                          <button onClick={() => { handleFiltro('centro', ''); setFiltrosAplicados(p => ({ ...p, centro: '' })); setPage(1); setPageGrupos(1); }} className="ml-0.5 hover:text-violet-900">✕</button>
                        </span>
                      )}
                      {filtrosAplicados.fecha_inicio && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-teal-100 text-teal-700 text-xs font-medium">
                          Desde: {filtrosAplicados.fecha_inicio}
                          <button onClick={() => { handleFiltro('fecha_inicio', ''); setFiltrosAplicados(p => ({ ...p, fecha_inicio: '' })); setPage(1); setPageGrupos(1); }} className="ml-0.5 hover:text-teal-900">✕</button>
                        </span>
                      )}
                      {filtrosAplicados.fecha_fin && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-teal-100 text-teal-700 text-xs font-medium">
                          Hasta: {filtrosAplicados.fecha_fin}
                          <button onClick={() => { handleFiltro('fecha_fin', ''); setFiltrosAplicados(p => ({ ...p, fecha_fin: '' })); setPage(1); setPageGrupos(1); }} className="ml-0.5 hover:text-teal-900">✕</button>
                        </span>
                      )}
                      {filtrosAplicados.estado_confirmacion && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700 text-xs font-medium">
                          Estado: {filtrosAplicados.estado_confirmacion === 'confirmado' ? '✅ Confirmado' : '⏳ Pendiente'}
                          <button onClick={() => { handleFiltro('estado_confirmacion', ''); setFiltrosAplicados(p => ({ ...p, estado_confirmacion: '' })); setPage(1); setPageGrupos(1); }} className="ml-0.5 hover:text-yellow-900">✕</button>
                        </span>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="overflow-x-auto rounded-b-xl">
              <table className="w-full text-sm">
                <thead className="bg-theme-gradient sticky top-0 z-10 shadow-md">
                  <tr>
                    <th className="min-w-[280px] px-3 py-3 text-left text-xs font-bold uppercase tracking-wider text-white/90">
                      <div className="flex items-center gap-2">
                        <FaBoxes className="text-white/70" />
                        <span>Detalle / Productos</span>
                      </div>
                    </th>
                    <th className="w-24 px-2 py-3 text-left text-xs font-bold uppercase tracking-wider text-white/90">Estado</th>
                    <th className="w-20 px-2 py-3 text-right text-xs font-bold uppercase tracking-wider text-white/90">Items</th>
                    {!esCentroUser && (
                      <th className="w-36 px-2 py-3 text-left text-xs font-bold uppercase tracking-wider text-white/90 hidden sm:table-cell">Destino</th>
                    )}
                    <th className="w-28 px-2 py-3 text-left text-xs font-bold uppercase tracking-wider text-white/90">Fecha</th>
                    {/* ISS-SEC FIX: Ocultar columna Acciones para Centro (solo pueden ver) */}
                    {esFarmacia && (
                      <th className="w-24 px-2 py-3 text-center text-xs font-bold uppercase tracking-wider text-white/90">Acciones</th>
                    )}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-50">
                  {loading ? (
                    /* 🦴 Skeleton Loading Premium */
                    <>
                      {[...Array(8)].map((_, i) => <SkeletonRow key={i} index={i} />)}
                    </>
                  ) : errorState ? (
                    /* ⚠️ Error State — clear, no stale data */
                    <tr>
                      <td colSpan={esFarmacia ? 6 : esCentroUser ? 4 : 5} className="px-4 py-16 text-center">
                        <div className="flex flex-col items-center justify-center max-w-md mx-auto">
                          <div className={`w-20 h-20 rounded-full flex items-center justify-center mb-4 shadow-inner ${errorState.status === 403 ? 'bg-red-100' : errorState.status === 422 ? 'bg-amber-100' : 'bg-gray-100'}`}>
                            <FaExclamationTriangle className={`text-3xl ${errorState.status === 403 ? 'text-red-500' : errorState.status === 422 ? 'text-amber-500' : 'text-gray-500'}`} />
                          </div>
                          <h3 className="text-lg font-semibold text-gray-700 mb-1">
                            {errorState.status === 403 ? 'Acceso denegado' : errorState.status === 422 ? 'Filtro no válido' : errorState.status === 409 ? 'Conflicto' : 'Error al cargar'}
                          </h3>
                          <p className="text-sm text-gray-500 mb-4">{errorState.message}</p>
                          <div className="flex gap-2">
                            <button
                              onClick={cargarMovimientos}
                              className="px-4 py-2 text-sm rounded-lg bg-theme-gradient text-white font-semibold hover:shadow-lg transition"
                            >
                              Reintentar
                            </button>
                            {hayFiltrosActivos && (
                              <button onClick={limpiarFiltros} className="px-4 py-2 text-sm rounded-lg border bg-white hover:bg-gray-50 transition">
                                Limpiar filtros
                              </button>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  ) : vistaAgrupada && movimientosAgrupados ? (
                    <>
                      {/* 📭 Empty State Premium */}
                      {(!movimientosAgrupados.grupos || movimientosAgrupados.grupos.length === 0) && 
                       (!movimientosAgrupados.sinGrupo || movimientosAgrupados.sinGrupo.length === 0) ? (
                        <tr>
                          <td colSpan={esFarmacia ? 6 : esCentroUser ? 4 : 5} className="px-4 py-16 text-center">
                            <div className="flex flex-col items-center justify-center">
                              <div className="w-20 h-20 bg-gradient-to-br from-gray-100 to-gray-200 rounded-full flex items-center justify-center mb-4 shadow-inner">
                                <FaHistory className="text-3xl text-gray-400" />
                              </div>
                              <h3 className="text-lg font-semibold text-gray-600 mb-1">Sin movimientos</h3>
                              <p className="text-sm text-gray-400">No hay registros que coincidan con los filtros</p>
                            </div>
                          </td>
                        </tr>
                      ) : (
                        <>
                          {/* 🎨 GRUPOS CON DISEÑO PREMIUM */}
                          {movimientosAgrupados.grupos.map((grupo, gIndex) => {
                            // Determinar tipo y estilos
                            const esRequisicion = grupo.tipo_grupo === 'requisicion';
                            const esSalidaMasiva = grupo.tipo_grupo === 'salida_masiva';
                            const esTransferencia = grupo.tipo_grupo === 'transferencia';
                            const esTransferenciaCentro = grupo.tipo_grupo === 'transferencia_centro';
                            
                            // Estilos especiales para Centro: usar colores más sutiles
                            const stylesCentro = esCentroUser ? {
                              gradient: 'from-slate-50 via-slate-100 to-slate-50',
                              border: 'border-l-slate-400',
                              borderConfirmed: 'border-l-emerald-500',
                              headerBg: 'bg-gradient-to-r from-slate-100 to-slate-200',
                              badge: 'bg-slate-700 text-white',
                              icon: 'text-slate-600',
                              hoverBg: 'hover:from-slate-100 hover:to-slate-200',
                            } : null;
                            const styles = stylesCentro || GRUPO_STYLES[grupo.tipo_grupo] || GRUPO_STYLES.transferencia;
                            
                            // Obtener lista de productos únicos del grupo
                            const allItems = grupo.items || [...(grupo.salidas || []), ...(grupo.entradas || [])];
                            const productosUnicos = [...new Set(allItems.map(m => m.producto_nombre || m.producto?.nombre || 'Producto'))];
                            const productosDisplay = productosUnicos.slice(0, 3);
                            const productosRestantes = productosUnicos.length - 3;
                            
                            // Tipo de operación legible - Para Centro mostrar "Entrega" en lugar de "Salida Masiva"
                            const tipoOperacion = esCentroUser 
                              ? 'Entrega'  // Para Centro, simplificar el nombre
                              : esRequisicion ? 'Requisición' 
                              : esSalidaMasiva ? 'Salida Masiva'
                              : esTransferenciaCentro ? 'Transferencia a Centro'
                              : 'Transferencia';
                            
                            const isExpanded = gruposExpandidos.has(grupo.id);
                            
                            return (
                              <React.Fragment key={grupo.id}>
                                {/* ═══════════════════════════════════════════════════════════════════
                                    🎯 HEADER DEL GRUPO - Diseño Premium con información relevante
                                    ═══════════════════════════════════════════════════════════════════ */}
                                <tr 
                                  className={`
                                    group cursor-pointer transition-all duration-300 ease-out
                                    bg-gradient-to-r ${styles.gradient}
                                    ${styles.hoverBg}
                                    border-l-4 ${grupo.confirmado ? styles.borderConfirmed : styles.border}
                                    ${isExpanded ? 'shadow-md' : 'hover:shadow-sm'}
                                  `}
                                  onClick={() => toggleGrupo(grupo.id)}
                                >
                                  {/* Columna: Detalle/Productos */}
                                  <td className="px-3 py-2.5">
                                    <div className="flex items-start gap-2">
                                      {/* Chevron con animación */}
                                      <div className={`
                                        transition-transform duration-300 ease-out ${styles.icon} mt-1
                                        ${isExpanded ? 'rotate-90' : 'rotate-0'}
                                      `}>
                                        <FaChevronRight className="text-sm" />
                                      </div>
                                      
                                      <div className="min-w-0 flex-1">
                                        {/* Tipo de operación y folio */}
                                        <div className="flex items-center gap-2 flex-wrap mb-1">
                                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${styles.badge}`}>
                                            {tipoOperacion}
                                          </span>
                                          <span className="text-xs text-gray-500 font-mono">
                                            #{grupo.id?.slice(-8) || grupo.id}
                                          </span>
                                        </div>
                                        
                                        {/* Lista de productos */}
                                        <div className="space-y-0.5">
                                          {productosDisplay.map((prod, idx) => (
                                            <div key={idx} className="text-xs text-gray-700 truncate flex items-center gap-1">
                                              <span className="w-1 h-1 bg-gray-400 rounded-full flex-shrink-0"></span>
                                              <span className="truncate" title={prod}>{prod}</span>
                                            </div>
                                          ))}
                                          {productosRestantes > 0 && (
                                            <div className="text-[10px] text-gray-500 italic pl-2">
                                              +{productosRestantes} producto{productosRestantes > 1 ? 's' : ''} más...
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  </td>
                                  
                                  {/* Columna: Estado */}
                                  <td className="px-2 py-2.5">
                                    <div className="flex flex-col gap-1">
                                      <StatusBadge 
                                        tipo={grupo.tipo_grupo} 
                                        confirmado={grupo.confirmado} 
                                        pendiente={grupo.pendiente} 
                                      />
                                      <MovCounter 
                                        salidas={grupo.num_salidas} 
                                        entradas={grupo.num_entradas} 
                                      />
                                    </div>
                                  </td>
                                  
                                  {/* Columna: Items/Cantidad */}
                                  <td className="px-2 py-2.5 text-right">
                                    <div className="flex flex-col items-end">
                                      <span className="font-bold text-lg text-gray-800 tabular-nums">
                                        {grupo.total_cantidad}
                                      </span>
                                      <span className="text-[10px] text-gray-500">
                                        {allItems.length} mov.
                                      </span>
                                    </div>
                                  </td>
                                  
                                  {/* Columna: Destino (solo para no-centro) */}
                                  {!esCentroUser && (
                                    <td className="px-2 py-2.5 hidden sm:table-cell">
                                      <div className="max-w-[140px]">
                                        <span className="font-semibold text-xs text-gray-700 truncate block" title={grupo.centro_nombre}>
                                          {grupo.centro_nombre || 'Almacén Central'}
                                        </span>
                                        {grupo.usuario_nombre && (
                                          <span className="text-[10px] text-gray-400 truncate block">
                                            por {grupo.usuario_nombre}
                                          </span>
                                        )}
                                      </div>
                                    </td>
                                  )}
                                  
                                  {/* Columna: Fecha */}
                                  <td className="px-2 py-2.5">
                                    <div className="text-xs text-gray-600">
                                      <div className="font-medium">
                                        {grupo.fecha ? new Date(grupo.fecha).toLocaleDateString('es-MX', { 
                                          day: '2-digit', month: 'short', year: 'numeric' 
                                        }) : '-'}
                                      </div>
                                      <div className="text-[10px] text-gray-400">
                                        {grupo.fecha ? new Date(grupo.fecha).toLocaleTimeString('es-MX', { 
                                          hour: '2-digit', minute: '2-digit' 
                                        }) : ''}
                                      </div>
                                    </div>
                                  </td>
                                  
                                  {/* Columna: Acciones - Solo para Farmacia/Admin */}
                                  {esFarmacia && (
                                    <td className="px-2 py-2.5">
                                      <div className="flex items-center justify-center gap-1 flex-wrap">
                                        {esRequisicion ? (
                                          <a 
                                            href={`/requisiciones?folio=${grupo.id}`}
                                            onClick={(e) => e.stopPropagation()}
                                            className="inline-flex items-center gap-1 px-2 py-1.5 text-xs font-semibold text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 hover:text-blue-800 transition-all duration-200 border border-blue-200"
                                          >
                                            <FaClipboardCheck className="text-[10px]" />
                                            Ver Req.
                                          </a>
                                        ) : grupo.pendiente ? (
                                          <div className="flex gap-1">
                                            {/* Botón Hoja de Recolección (Formato B) */}
                                            <button
                                              onClick={(e) => { e.stopPropagation(); descargarHojaEntregaGrupo(grupo.id); }}
                                              className="p-1.5 bg-gradient-to-b from-blue-500 to-blue-600 text-white rounded hover:from-blue-600 hover:to-blue-700 transition-all duration-200 shadow-sm hover:shadow-md"
                                              title="Hoja de Recolección (Formato B)"
                                            >
                                              <FaClipboardCheck className="text-xs" />
                                            </button>
                                            {/* Botón Confirmar Entrega - Abre modal de confirmación */}
                                            <button
                                              onClick={(e) => { 
                                                e.stopPropagation(); 
                                                setConfirmConfirmarGrupo({
                                                  id: grupo.id,
                                                  centro_nombre: grupo.centro_nombre,
                                                  items: grupo.items || [],
                                                  total_cantidad: grupo.total_cantidad,
                                                  num_items: (grupo.items || []).length
                                                });
                                              }}
                                              disabled={confirmandoGrupo === grupo.id}
                                              className="p-1.5 bg-gradient-to-b from-green-500 to-green-600 text-white rounded hover:from-green-600 hover:to-green-700 transition-all duration-200 shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                                              title="Confirmar Entrega (Descuenta Inventario)"
                                            >
                                              {confirmandoGrupo === grupo.id ? <FaSpinner className="text-xs animate-spin" /> : <FaCheckCircle className="text-xs" />}
                                            </button>
                                            {/* Botón Cancelar */}
                                            <button
                                              onClick={(e) => { e.stopPropagation(); setConfirmCancelarGrupo(grupo.id); }}
                                              disabled={cancelandoGrupo === grupo.id}
                                              className="p-1.5 bg-gradient-to-b from-red-500 to-red-600 text-white rounded hover:from-red-600 hover:to-red-700 transition-all duration-200 shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                                              title="Cancelar salida"
                                            >
                                              {cancelandoGrupo === grupo.id ? <FaSpinner className="text-xs animate-spin" /> : <FaTrash className="text-xs" />}
                                            </button>
                                          </div>
                                        ) : grupo.confirmado ? (
                                          <button
                                            onClick={(e) => { e.stopPropagation(); descargarComprobanteGrupo(grupo.id); }}
                                            className="p-1.5 bg-gradient-to-b from-emerald-500 to-emerald-600 text-white rounded hover:from-emerald-600 hover:to-emerald-700 transition-all duration-200 shadow-sm hover:shadow-md"
                                            title="Descargar comprobante"
                                          >
                                            <FaFileDownload className="text-xs" />
                                          </button>
                                        ) : (
                                          <span className="text-[10px] text-gray-400">Sin acciones</span>
                                        )}
                                      </div>
                                    </td>
                                  )}
                                </tr>
                                
                                {/* ═══════════════════════════════════════════════════════════════════
                                    📦 ITEMS EXPANDIDOS - Detalle de cada movimiento
                                    ═══════════════════════════════════════════════════════════════════ */}
                                {isExpanded && (
                                  <>
                                    {/* ═══════════════════════════════════════════════════════════════
                                        🏥 VISTA PARA USUARIOS DE CENTRO - Diseño limpio y relevante
                                        ═══════════════════════════════════════════════════════════════ */}
                                    {esCentroUser ? (
                                      <>
                                        {/* Tabla de detalle para Centro */}
                                        <tr className="bg-slate-50">
                                          <td colSpan={5} className="p-0">
                                            <div className="mx-4 my-3 bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                                              {/* Header del detalle */}
                                              <div className="bg-gradient-to-r from-slate-700 to-slate-800 px-4 py-2.5">
                                                <h4 className="text-white text-sm font-semibold flex items-center gap-2">
                                                  <FaBoxes className="text-slate-300" />
                                                  Detalle de Medicamentos
                                                  <span className="ml-auto bg-white/20 px-2 py-0.5 rounded text-xs">
                                                    {allItems.length} producto{allItems.length > 1 ? 's' : ''}
                                                  </span>
                                                </h4>
                                              </div>
                                              
                                              {/* Entradas recibidas */}
                                              {(() => {
                                                const entradas = (grupo.entradas || grupo.items || []).filter(m => m.tipo === 'entrada');
                                                if (entradas.length === 0) return null;
                                                return (
                                                  <div className="border-b border-slate-100">
                                                    <div className="bg-emerald-50 px-4 py-2 flex items-center gap-2 border-b border-emerald-100">
                                                      <span className="w-6 h-6 rounded-full bg-emerald-500 text-white flex items-center justify-center text-xs font-bold">📥</span>
                                                      <span className="font-semibold text-emerald-800 text-sm">Medicamentos Recibidos</span>
                                                      <span className="ml-auto text-xs bg-emerald-200 text-emerald-800 px-2 py-0.5 rounded-full font-medium">
                                                        +{entradas.reduce((sum, m) => sum + Math.abs(m.cantidad), 0)} unidades
                                                      </span>
                                                    </div>
                                                    <table className="w-full">
                                                      <thead className="bg-slate-50 text-xs text-slate-600">
                                                        <tr>
                                                          <th className="px-4 py-2 text-left font-semibold">Producto</th>
                                                          <th className="px-2 py-2 text-left font-semibold">Presentación</th>
                                                          <th className="px-3 py-2 text-left font-semibold">Lote</th>
                                                          <th className="px-3 py-2 text-center font-semibold">Cantidad</th>
                                                          <th className="px-3 py-2 text-right font-semibold">Fecha</th>
                                                        </tr>
                                                      </thead>
                                                      <tbody className="divide-y divide-slate-100">
                                                        {entradas.map((mov, idx) => (
                                                          <tr key={`ent-${mov.id}`} className={idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'}>
                                                            <td className="px-4 py-2.5">
                                                              <span className="font-medium text-slate-800 text-sm">{mov.producto_nombre || mov.producto || ""}</span>
                                                            </td>
                                                            <td className="px-2 py-2.5">
                                                              <span className="text-xs text-slate-600">{mov.producto_presentacion || mov.presentacion || '-'}</span>
                                                            </td>
                                                            <td className="px-3 py-2.5">
                                                              <span className="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded text-slate-600">
                                                                {mov.lote_numero || mov.lote_codigo || mov.numero_lote || 'N/A'}
                                                              </span>
                                                            </td>
                                                            <td className="px-3 py-2.5 text-center">
                                                              <span className="font-bold text-emerald-600 text-base">+{Math.abs(mov.cantidad)}</span>
                                                            </td>
                                                            <td className="px-3 py-2.5 text-right text-xs text-slate-500">
                                                              {(mov.fecha_salida || mov.fecha) ? new Date(mov.fecha_salida || mov.fecha).toLocaleDateString('es-MX', {day: '2-digit', month: 'short'}) : '-'}
                                                            </td>
                                                          </tr>
                                                        ))}
                                                      </tbody>
                                                    </table>
                                                  </div>
                                                );
                                              })()}
                                              
                                              {/* Salidas/Dispensaciones */}
                                              {(() => {
                                                const salidas = (grupo.salidas || grupo.items || []).filter(m => m.tipo === 'salida');
                                                if (salidas.length === 0) return null;
                                                return (
                                                  <div>
                                                    <div className="bg-orange-50 px-4 py-2 flex items-center gap-2 border-b border-orange-100">
                                                      <span className="w-6 h-6 rounded-full bg-orange-500 text-white flex items-center justify-center text-xs font-bold">💊</span>
                                                      <span className="font-semibold text-orange-800 text-sm">Dispensado a Internos</span>
                                                      <span className="ml-auto text-xs bg-orange-200 text-orange-800 px-2 py-0.5 rounded-full font-medium">
                                                        -{salidas.reduce((sum, m) => sum + Math.abs(m.cantidad), 0)} unidades
                                                      </span>
                                                    </div>
                                                    <table className="w-full">
                                                      <thead className="bg-slate-50 text-xs text-slate-600">
                                                        <tr>
                                                          <th className="px-4 py-2 text-left font-semibold">Producto</th>
                                                          <th className="px-2 py-2 text-left font-semibold">Presentación</th>
                                                          <th className="px-3 py-2 text-left font-semibold">Lote</th>
                                                          <th className="px-3 py-2 text-center font-semibold">Cantidad</th>
                                                          <th className="px-3 py-2 text-right font-semibold">Fecha</th>
                                                        </tr>
                                                      </thead>
                                                      <tbody className="divide-y divide-slate-100">
                                                        {salidas.map((mov, idx) => (
                                                          <tr key={`sal-${mov.id}`} className={idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'}>
                                                            <td className="px-4 py-2.5">
                                                              <span className="font-medium text-slate-800 text-sm">{mov.producto_nombre || mov.producto || ""}</span>
                                                            </td>
                                                            <td className="px-2 py-2.5">
                                                              <span className="text-xs text-slate-600">{mov.producto_presentacion || mov.presentacion || '-'}</span>
                                                            </td>
                                                            <td className="px-3 py-2.5">
                                                              <span className="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded text-slate-600">
                                                                {mov.lote_numero || mov.lote_codigo || mov.numero_lote || 'N/A'}
                                                              </span>
                                                            </td>
                                                            <td className="px-3 py-2.5 text-center">
                                                              <span className="font-bold text-orange-600 text-base">-{Math.abs(mov.cantidad)}</span>
                                                            </td>
                                                            <td className="px-3 py-2.5 text-right text-xs text-slate-500">
                                                              {(mov.fecha_salida || mov.fecha) ? new Date(mov.fecha_salida || mov.fecha).toLocaleDateString('es-MX', {day: '2-digit', month: 'short'}) : '-'}
                                                            </td>
                                                          </tr>
                                                        ))}
                                                      </tbody>
                                                    </table>
                                                  </div>
                                                );
                                              })()}
                                            </div>
                                          </td>
                                        </tr>
                                      </>
                                    ) : (
                                      /* ═══════════════════════════════════════════════════════════════
                                         🏢 VISTA PARA ADMIN/FARMACIA - Vista completa con flujo
                                         ═══════════════════════════════════════════════════════════════ */
                                      <>
                                        {/* 🔴 SECCIÓN 1: SALIDAS ALMACÉN (Transferencias) */}
                                        {(() => {
                                          const salidasAlmacen = (grupo.salidas || grupo.items || []).filter(
                                            m => m.tipo === 'salida' && (m.subtipo_salida === 'transferencia' || m.centro_nombre === 'Almacén Central')
                                          );
                                          if (salidasAlmacen.length === 0) return null;
                                          return (
                                            <>
                                              <tr className="bg-gradient-to-r from-red-50 to-red-100 border-l-4 border-red-400">
                                                <td colSpan={6} className="px-4 py-2">
                                                  <div className="flex items-center gap-2 text-red-700">
                                                    <div className="w-6 h-6 rounded-full bg-red-200 flex items-center justify-center">
                                                      <span className="text-sm">📤</span>
                                                    </div>
                                                    <span className="font-bold text-xs uppercase tracking-wider">
                                                      1. Salida Almacén Central (Transferencia)
                                                    </span>
                                                    <span className="text-xs bg-red-200 text-red-800 px-2 py-0.5 rounded-full font-medium">
                                                      {salidasAlmacen.length} item{salidasAlmacen.length > 1 ? 's' : ''}
                                                    </span>
                                                  </div>
                                                </td>
                                              </tr>
                                              {salidasAlmacen.map((mov, iIndex) => (
                                                <tr 
                                                  key={`sal-alm-${mov.id}`}
                                                  className={`
                                                    transition-all duration-200 hover:bg-red-100
                                                    ${iIndex % 2 === 0 ? 'bg-red-50/50' : 'bg-red-50/80'}
                                                    border-l-4 border-red-300
                                                  `}
                                                >
                                                  <td className="px-3 py-2.5 pl-10">
                                                    <div className="font-medium text-gray-800 text-sm">{mov.producto_nombre || mov.producto || ""}</div>
                                                    <div className="text-xs text-gray-500 mt-0.5">
                                                      <span className="bg-gray-100 px-1.5 py-0.5 rounded text-gray-600">
                                                        Lote: {mov.lote_numero || mov.lote_codigo || mov.numero_lote || 'N/A'}
                                                      </span>
                                                    </div>
                                                  </td>
                                                  <td className="px-2 py-2.5">
                                                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-semibold bg-red-100 text-red-700 border border-red-200">
                                                      <span className="w-1.5 h-1.5 bg-red-500 rounded-full"></span>
                                                      SALIDA
                                                    </span>
                                                  </td>
                                                  <td className="px-2 py-2.5 text-right">
                                                    <span className="font-bold text-red-600 text-base tabular-nums">
                                                      -{Math.abs(mov.cantidad)}
                                                    </span>
                                                  </td>
                                                  <td className="px-2 py-2.5 text-gray-600 text-xs hidden sm:table-cell">Almacén Central</td>
                                                  <td className="px-2 py-2.5 text-gray-500 text-xs hidden md:table-cell">
                                                    {(mov.fecha_salida || mov.fecha) ? new Date(mov.fecha_salida || mov.fecha).toLocaleDateString('es-MX') : ''}
                                                  </td>
                                                  <td className="px-2 py-2.5 text-center">
                                                    <span className="text-xs text-gray-400 font-mono">#{mov.id}</span>
                                                  </td>
                                                </tr>
                                              ))}
                                            </>
                                          );
                                        })()}
                                        
                                        {/* 🟢 SECCIÓN 2: ENTRADAS CENTRO (Recepción) */}
                                        {(() => {
                                          const entradasCentro = (grupo.entradas || grupo.items || []).filter(m => m.tipo === 'entrada');
                                          if (entradasCentro.length === 0) return null;
                                          return (
                                            <>
                                              <tr className="bg-gradient-to-r from-emerald-50 to-emerald-100 border-l-4 border-emerald-400">
                                                <td colSpan={6} className="px-4 py-2">
                                                  <div className="flex items-center gap-2 text-emerald-700">
                                                    <div className="w-6 h-6 rounded-full bg-emerald-200 flex items-center justify-center">
                                                      <span className="text-sm">📥</span>
                                                    </div>
                                                    <span className="font-bold text-xs uppercase tracking-wider">
                                                      2. Entrada Centro (Recepción)
                                                    </span>
                                                    <span className="text-xs bg-emerald-200 text-emerald-800 px-2 py-0.5 rounded-full font-medium">
                                                      {entradasCentro.length} item{entradasCentro.length > 1 ? 's' : ''}
                                                    </span>
                                                  </div>
                                                </td>
                                              </tr>
                                              {entradasCentro.map((mov, iIndex) => (
                                                <tr 
                                                  key={`ent-${mov.id}`}
                                                  className={`
                                                    transition-all duration-200 hover:bg-emerald-100
                                                    ${iIndex % 2 === 0 ? 'bg-emerald-50/50' : 'bg-emerald-50/80'}
                                                    border-l-4 border-emerald-300
                                                  `}
                                                >
                                                  <td className="px-3 py-2.5 pl-10">
                                                    <div className="font-medium text-gray-800 text-sm">{mov.producto_nombre || mov.producto || ""}</div>
                                                    <div className="text-xs text-gray-500 mt-0.5">
                                                      <span className="bg-gray-100 px-1.5 py-0.5 rounded text-gray-600">
                                                        Lote: {mov.lote_numero || mov.lote_codigo || mov.numero_lote || 'N/A'}
                                                      </span>
                                                    </div>
                                                  </td>
                                                  <td className="px-2 py-2.5">
                                                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-semibold bg-emerald-100 text-emerald-700 border border-emerald-200">
                                                      <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span>
                                                      ENTRADA
                                                    </span>
                                                  </td>
                                                  <td className="px-2 py-2.5 text-right">
                                                    <span className="font-bold text-emerald-600 text-base tabular-nums">
                                                      +{Math.abs(mov.cantidad)}
                                                    </span>
                                                  </td>
                                                  <td className="px-2 py-2.5 text-gray-600 text-xs hidden sm:table-cell">{mov.centro_nombre || grupo.centro_nombre}</td>
                                                  <td className="px-2 py-2.5 text-gray-500 text-xs hidden md:table-cell">
                                                    {(mov.fecha_salida || mov.fecha) ? new Date(mov.fecha_salida || mov.fecha).toLocaleDateString('es-MX') : ''}
                                                  </td>
                                                  <td className="px-2 py-2.5 text-center">
                                                    <span className="text-xs text-gray-400 font-mono">#{mov.id}</span>
                                                  </td>
                                                </tr>
                                              ))}
                                            </>
                                          );
                                        })()}
                                        
                                        {/* 🟠 SECCIÓN 3: SALIDAS CENTRO (Dispensación) */}
                                        {(() => {
                                          const salidasCentro = (grupo.salidas || grupo.items || []).filter(
                                            m => m.tipo === 'salida' && m.subtipo_salida === 'dispensacion' && m.centro_nombre !== 'Almacén Central'
                                          );
                                          if (salidasCentro.length === 0) return null;
                                          return (
                                            <>
                                              <tr className="bg-gradient-to-r from-orange-50 to-orange-100 border-l-4 border-orange-400">
                                                <td colSpan={6} className="px-4 py-2">
                                                  <div className="flex items-center gap-2 text-orange-700">
                                                    <div className="w-6 h-6 rounded-full bg-orange-200 flex items-center justify-center">
                                                      <span className="text-sm">💊</span>
                                                    </div>
                                                    <span className="font-bold text-xs uppercase tracking-wider">
                                                      3. Salida Centro (Dispensación a Internos)
                                                    </span>
                                                    <span className="text-xs bg-orange-200 text-orange-800 px-2 py-0.5 rounded-full font-medium">
                                                      {salidasCentro.length} item{salidasCentro.length > 1 ? 's' : ''}
                                                    </span>
                                                  </div>
                                                </td>
                                              </tr>
                                              {salidasCentro.map((mov, iIndex) => (
                                                <tr 
                                                  key={`sal-cen-${mov.id}`}
                                                  className={`
                                                    transition-all duration-200 hover:bg-orange-100
                                                    ${iIndex % 2 === 0 ? 'bg-orange-50/50' : 'bg-orange-50/80'}
                                                    border-l-4 border-orange-300
                                                  `}
                                                >
                                                  <td className="px-3 py-2.5 pl-10">
                                                    <div className="font-medium text-gray-800 text-sm">{mov.producto_nombre || mov.producto || ""}</div>
                                                    <div className="text-xs text-gray-500 mt-0.5">
                                                      <span className="bg-gray-100 px-1.5 py-0.5 rounded text-gray-600">
                                                        Lote: {mov.lote_numero || mov.lote_codigo || mov.numero_lote || 'N/A'}
                                                      </span>
                                                    </div>
                                                  </td>
                                                  <td className="px-2 py-2.5">
                                                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-semibold bg-orange-100 text-orange-700 border border-orange-200">
                                                      <span className="w-1.5 h-1.5 bg-orange-500 rounded-full"></span>
                                                      DISPENSACIÓN
                                                    </span>
                                                  </td>
                                                  <td className="px-2 py-2.5 text-right">
                                                    <span className="font-bold text-orange-600 text-base tabular-nums">
                                                      -{Math.abs(mov.cantidad)}
                                                    </span>
                                                  </td>
                                                  <td className="px-2 py-2.5 text-gray-600 text-xs hidden sm:table-cell">{mov.centro_nombre || grupo.centro_nombre}</td>
                                                  <td className="px-2 py-2.5 text-gray-500 text-xs hidden md:table-cell">
                                                    {(mov.fecha_salida || mov.fecha) ? new Date(mov.fecha_salida || mov.fecha).toLocaleDateString('es-MX') : ''}
                                                  </td>
                                                  <td className="px-2 py-2.5 text-center">
                                                    <span className="text-xs text-gray-400 font-mono">#{mov.id}</span>
                                                  </td>
                                                </tr>
                                              ))}
                                            </>
                                          );
                                        })()}
                                      </>
                                    )}
                                    
                                    {/* Espaciador visual entre grupos */}
                                    <tr className="bg-gray-100/50">
                                      <td colSpan={esFarmacia ? 6 : esCentroUser ? 4 : 5} className="h-2"></td>
                                    </tr>
                                  </>
                                )}
                              </React.Fragment>
                            );
                          })}
                          
                          {/* 📋 MOVIMIENTOS INDIVIDUALES (sin grupo) */}
                          {movimientosAgrupados.sinGrupo.map((mov, index) => (
                        <React.Fragment key={mov.id}>
                          <tr 
                            ref={highlightId === mov.id ? highlightRef : null}
                            className={`
                              transition-all duration-200 cursor-pointer
                              ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}
                              hover:bg-blue-50/50
                              ${highlightId === mov.id ? 'bg-yellow-50 ring-2 ring-yellow-400 ring-inset' : ''}
                              ${expandedId === mov.id ? 'bg-blue-50 shadow-inner' : ''}
                              border-l-4 ${mov.tipo === 'entrada' ? 'border-emerald-400' : mov.tipo === 'salida' ? 'border-red-400' : 'border-gray-300'}
                            `}
                            onClick={() => setExpandedId(expandedId === mov.id ? null : mov.id)}
                          >
                            <td className="px-3 py-3.5">
                              <div className="font-semibold text-gray-800 text-sm">{mov.producto_nombre || mov.producto || ""}</div>
                              <div className="text-xs text-gray-500 mt-0.5">
                                <span className="bg-gray-100 px-1.5 py-0.5 rounded">
                                  Lote: {mov.lote_numero || mov.lote_codigo || mov.numero_lote || 'N/A'}
                                </span>
                              </div>
                            </td>
                            <td className="px-2 py-3.5">
                              <div className="flex flex-col gap-1">
                                <span className={`
                                  inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold w-fit
                                  ${mov.tipo === "entrada" ? "bg-emerald-100 text-emerald-700 border border-emerald-200" :
                                    mov.tipo === "salida" ? "bg-red-100 text-red-700 border border-red-200" : 
                                    "bg-yellow-100 text-yellow-700 border border-yellow-200"}
                                `}>
                                  <span className={`w-1.5 h-1.5 rounded-full ${
                                    mov.tipo === "entrada" ? "bg-emerald-500" :
                                    mov.tipo === "salida" ? "bg-red-500" : "bg-yellow-500"
                                  }`}></span>
                                  {mov.tipo?.toUpperCase()}
                                </span>
                                {mov.tipo === 'salida' && mov.subtipo_salida && (
                                  <span className="text-xs text-gray-500 pl-0.5">
                                    {mov.subtipo_salida === 'receta' ? '💊 Receta' :
                                     mov.subtipo_salida === 'consumo_interno' ? '🏥 Interno' :
                                     mov.subtipo_salida === 'merma' ? '📉 Merma' :
                                     mov.subtipo_salida === 'caducidad' ? '⏰ Caducidad' :
                                     mov.subtipo_salida === 'transferencia' ? '🔄 Transfer.' : ''}
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className="px-2 py-3.5 text-right">
                              <span className={`font-black text-lg tabular-nums ${
                                mov.tipo === 'salida' ? 'text-red-600' : 
                                mov.tipo === 'entrada' ? 'text-emerald-600' : 'text-gray-700'
                              }`}>
                                {mov.tipo === 'salida' ? '-' : '+'}{Math.abs(mov.cantidad)}
                              </span>
                            </td>
                            <td className="px-2 py-3.5 text-gray-700 text-xs hidden sm:table-cell">
                              <span className="truncate block max-w-[120px]" title={mov.centro_nombre || mov.centro || "Almacén Central"}>
                                {mov.centro_nombre || mov.centro || "Almacén Central"}
                              </span>
                            </td>
                            <td className="px-2 py-3.5 text-gray-600 text-xs hidden md:table-cell">
                              {mov.fecha_salida
                                ? new Date(mov.fecha_salida).toLocaleDateString('es-MX')
                                : mov.fecha_movimiento
                                ? new Date(mov.fecha_movimiento).toLocaleDateString('es-MX')
                                : mov.fecha
                                ? new Date(mov.fecha).toLocaleDateString('es-MX')
                                : ""}
                            </td>
                            <td className="px-2 py-3.5 text-center">
                              <button 
                                className={`
                                  w-7 h-7 flex items-center justify-center rounded-full
                                  transition-all duration-200
                                  ${expandedId === mov.id 
                                    ? 'bg-blue-100 text-blue-600 rotate-180' 
                                    : 'bg-gray-100 text-gray-500 hover:bg-blue-50 hover:text-blue-600'
                                  }
                                `}
                                onClick={(e) => { e.stopPropagation(); setExpandedId(expandedId === mov.id ? null : mov.id); }}
                              >
                                <FaChevronDown className="text-xs" />
                              </button>
                            </td>
                          </tr>
                          {/* 📋 PANEL EXPANDIDO - Detalles del movimiento individual */}
                          {expandedId === mov.id && (
                            <tr className="bg-gradient-to-b from-gray-50 to-white">
                              <td colSpan={esFarmacia ? 6 : esCentroUser ? 4 : 5} className="px-4 py-4">
                                <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                                  {/* Header del panel */}
                                  <div className="bg-gradient-to-r from-slate-100 to-gray-100 px-4 py-2 border-b border-gray-200">
                                    <span className="text-xs font-bold text-gray-600 uppercase tracking-wider">
                                      Detalles del Movimiento #{mov.id}
                                    </span>
                                  </div>
                                  
                                  <div className="p-4">
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                      <div className="bg-gray-50 rounded-lg p-3">
                                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1">ID</span>
                                        <p className="text-gray-800 font-mono font-bold">{mov.id}</p>
                                      </div>
                                      <div className="bg-gray-50 rounded-lg p-3">
                                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1">Usuario</span>
                                        <p className="text-gray-800 font-medium">{mov.usuario_nombre || 'Sistema'}</p>
                                      </div>
                                      <div className="bg-gray-50 rounded-lg p-3">
                                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1">Centro</span>
                                        <p className="text-gray-800 font-medium">{mov.centro_nombre || 'Almacén Central'}</p>
                                      </div>
                                      <div className="bg-gray-50 rounded-lg p-3">
                                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1">Fecha</span>
                                        <p className="text-gray-800 font-medium text-sm">
                                          {(mov.fecha_movimiento || mov.fecha) 
                                            ? new Date(mov.fecha_movimiento || mov.fecha).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' }) 
                                            : '-'}
                                        </p>
                                      </div>
                                    </div>
                                    
                                    {mov.observaciones && (
                                      <div className="mt-4">
                                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-2">Observaciones</span>
                                        <p className="text-gray-700 bg-amber-50 p-3 rounded-lg border border-amber-200 text-sm leading-relaxed">
                                          {mov.observaciones}
                                        </p>
                                      </div>
                                    )}
                                    
                                    {/* ISS-SEC FIX: Acciones solo para Farmacia/Admin */}
                                    {esFarmacia && mov.tipo === 'salida' && (
                                      <div className="mt-5 pt-4 border-t border-gray-200">
                                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-3">Acciones</span>
                                        <div className="flex flex-wrap gap-3">
                                          {!mov.confirmado ? (
                                            <>
                                              {mov.subtipo_salida !== 'receta' && (
                                                <button
                                                  onClick={(e) => { e.stopPropagation(); descargarReciboSalida(mov); }}
                                                  className="inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-b from-blue-500 to-blue-600 text-white rounded-xl hover:from-blue-600 hover:to-blue-700 transition-all duration-200 text-sm font-semibold shadow-sm hover:shadow-md"
                                                  title="Descargar hoja de entrega"
                                                >
                                                  <FaFilePdf className="text-base" />
                                                  Hoja de Entrega
                                                </button>
                                              )}
                                              <button
                                                onClick={(e) => { e.stopPropagation(); confirmarEntregaIndividual(mov.id); }}
                                                disabled={confirmandoMovimiento === mov.id}
                                                className={`
                                                  inline-flex items-center gap-2 px-4 py-2.5 text-white rounded-xl 
                                                  transition-all duration-200 text-sm font-semibold shadow-sm hover:shadow-md
                                                  disabled:opacity-50 disabled:cursor-not-allowed
                                                  ${mov.subtipo_salida === 'receta' 
                                                    ? 'bg-gradient-to-b from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700' 
                                                    : 'bg-gradient-to-b from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700'
                                                  }
                                                `}
                                                title={mov.subtipo_salida === 'receta' 
                                                  ? "Confirmar dispensación" 
                                                  : "Confirmar entrega"
                                                }
                                              >
                                                {confirmandoMovimiento === mov.id ? (
                                                  <FaSpinner className="animate-spin text-base" />
                                                ) : (
                                                  <FaClipboardCheck className="text-base" />
                                                )}
                                                {confirmandoMovimiento === mov.id 
                                                  ? 'Confirmando...' 
                                                  : (mov.subtipo_salida === 'receta' ? 'Confirmar Dispensación' : 'Confirmar Entrega')
                                                }
                                              </button>
                                            </>
                                          ) : !esMedico ? (
                                            <button
                                              onClick={(e) => { e.stopPropagation(); descargarReciboFinalizado(mov); }}
                                              className="inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-b from-emerald-500 to-emerald-600 text-white rounded-xl hover:from-emerald-600 hover:to-emerald-700 transition-all duration-200 text-sm font-semibold shadow-sm hover:shadow-md"
                                              title="Descargar comprobante"
                                            >
                                              <FaCheckCircle className="text-base" />
                                              {mov.subtipo_salida === 'receta' ? 'Comprobante Dispensación' : 'Comprobante Entregado'}
                                            </button>
                                          ) : (
                                            <span className="inline-flex items-center gap-2 px-4 py-2.5 text-emerald-600 text-sm font-semibold">
                                              <FaCheckCircle className="text-base" />
                                              Entregado
                                            </span>
                                          )}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      ))}
                        </>
                      )}
                    </>
                  ) : (
                    /* 📋 VISTA INDIVIDUAL (sin agrupar) */
                    !movimientos.length ? (
                      <tr>
                        <td colSpan={esFarmacia ? 6 : esCentroUser ? 4 : 5} className="px-4 py-16 text-center">
                          <div className="flex flex-col items-center justify-center">
                            <div className="w-20 h-20 bg-gradient-to-br from-gray-100 to-gray-200 rounded-full flex items-center justify-center mb-4 shadow-inner">
                              <FaHistory className="text-3xl text-gray-400" />
                            </div>
                            <h3 className="text-lg font-semibold text-gray-600 mb-1">Sin movimientos</h3>
                            <p className="text-sm text-gray-400">No hay registros que coincidan</p>
                          </div>
                        </td>
                      </tr>
                    ) : movimientos.map((mov, index) => (
                      <React.Fragment key={mov.id}>
                        <tr 
                          ref={highlightId === mov.id ? highlightRef : null}
                          className={`
                            transition-all duration-200 cursor-pointer
                            ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}
                            hover:bg-blue-50/50
                            ${highlightId === mov.id ? 'bg-yellow-50 ring-2 ring-yellow-400 ring-inset' : ''}
                            ${expandedId === mov.id ? 'bg-blue-50 shadow-inner' : ''}
                            border-l-4 ${mov.tipo === 'entrada' ? 'border-emerald-400' : mov.tipo === 'salida' ? 'border-red-400' : 'border-gray-300'}
                          `}
                          onClick={() => setExpandedId(expandedId === mov.id ? null : mov.id)}
                        >
                          <td className="px-3 py-3.5">
                            <div className="font-semibold text-gray-800 text-sm leading-tight">{mov.producto_nombre || mov.producto || ""}</div>
                            <div className="text-xs text-gray-500 mt-1">
                              <span className="bg-gray-100 px-1.5 py-0.5 rounded font-mono">Lote: {mov.lote_codigo || mov.numero_lote || 'N/A'}</span>
                            </div>
                          </td>
                          <td className="px-2 py-3.5 whitespace-nowrap">
                            <div className="flex flex-col gap-1">
                              <span className={`
                                inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold w-fit
                                ${mov.tipo === "entrada" ? "bg-emerald-100 text-emerald-700 border border-emerald-200" :
                                  mov.tipo === "salida" ? "bg-red-100 text-red-700 border border-red-200" : 
                                  "bg-yellow-100 text-yellow-700 border border-yellow-200"}
                              `}>
                                <span className={`w-1.5 h-1.5 rounded-full ${
                                  mov.tipo === "entrada" ? "bg-emerald-500" :
                                  mov.tipo === "salida" ? "bg-red-500" : "bg-yellow-500"
                                }`}></span>
                                {mov.tipo?.toUpperCase()}
                              </span>
                              {mov.tipo === 'salida' && mov.subtipo_salida && (
                                <span className="text-xs text-gray-500 pl-0.5">
                                  {mov.subtipo_salida === 'receta' ? '💊 Receta' :
                                   mov.subtipo_salida === 'consumo_interno' ? '🏥 Interno' :
                                   mov.subtipo_salida === 'merma' ? '📉 Merma' :
                                   mov.subtipo_salida === 'caducidad' ? '⏰ Caducidad' :
                                   mov.subtipo_salida === 'transferencia' ? '🔄 Transfer.' : ''}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-2 py-3.5 text-right whitespace-nowrap">
                            <span className={`font-black text-lg tabular-nums ${
                              mov.tipo === 'salida' ? 'text-red-600' : 
                              mov.tipo === 'entrada' ? 'text-emerald-600' : 'text-gray-700'
                            }`}>
                              {mov.tipo === 'salida' ? '-' : '+'}{Math.abs(mov.cantidad)}
                            </span>
                          </td>
                          <td className="px-2 py-3.5 text-gray-700 text-xs hidden sm:table-cell">
                            <span className="line-clamp-2">{mov.centro_nombre || mov.centro || "Almacén Central"}</span>
                          </td>
                          <td className="px-2 py-3.5 text-gray-600 text-xs hidden md:table-cell whitespace-nowrap">
                            {mov.fecha_salida
                              ? new Date(mov.fecha_salida).toLocaleDateString('es-MX')
                              : mov.fecha_movimiento
                              ? new Date(mov.fecha_movimiento).toLocaleDateString('es-MX')
                              : mov.fecha
                              ? new Date(mov.fecha).toLocaleDateString('es-MX')
                              : ""}
                          </td>
                          <td className="px-2 py-3.5 text-center">
                            <button 
                              className={`
                                w-7 h-7 flex items-center justify-center rounded-full
                                transition-all duration-200
                                ${expandedId === mov.id 
                                  ? 'bg-blue-100 text-blue-600 rotate-180' 
                                  : 'bg-gray-100 text-gray-500 hover:bg-blue-50 hover:text-blue-600'
                                }
                              `}
                              onClick={(e) => { e.stopPropagation(); setExpandedId(expandedId === mov.id ? null : mov.id); }}
                            >
                              <FaChevronDown className="text-xs" />
                            </button>
                          </td>
                        </tr>
                        {/* 📋 PANEL EXPANDIDO Premium */}
                        {expandedId === mov.id && (
                          <tr className="bg-gradient-to-b from-gray-50 to-white">
                            <td colSpan={esFarmacia ? 6 : esCentroUser ? 4 : 5} className="px-4 py-4">
                              <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                                <div className="bg-gradient-to-r from-slate-100 to-gray-100 px-4 py-2 border-b border-gray-200">
                                  <span className="text-xs font-bold text-gray-600 uppercase tracking-wider">
                                    Detalles del Movimiento #{mov.id}
                                  </span>
                                </div>
                                <div className="p-4">
                                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    <div className="bg-gray-50 rounded-lg p-3">
                                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1">Producto</span>
                                      <p className="text-gray-800 font-medium text-sm">{mov.producto_clave || 'N/A'} - {mov.producto_nombre || ''}</p>
                                    </div>
                                    <div className="bg-gray-50 rounded-lg p-3">
                                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1">Lote</span>
                                      <p className="text-gray-800 font-mono font-medium">{mov.lote_codigo || mov.numero_lote || 'N/A'}</p>
                                    </div>
                                    <div className="bg-gray-50 rounded-lg p-3">
                                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1">Centro</span>
                                      <p className="text-gray-800 font-medium">{mov.centro_nombre || 'Almacén Central'}</p>
                                    </div>
                                    <div className="bg-gray-50 rounded-lg p-3">
                                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1">Usuario</span>
                                      <p className="text-gray-800 font-medium">{mov.usuario_nombre || mov.usuario || 'Sistema'}</p>
                                    </div>
                                    {mov.requisicion_folio && (
                                      <div className="bg-blue-50 rounded-lg p-3">
                                        <span className="text-[10px] font-bold text-blue-400 uppercase tracking-wider block mb-1">Requisición</span>
                                        <p className="text-blue-800 font-bold">{mov.requisicion_folio}</p>
                                      </div>
                                    )}
                                    {mov.tipo === 'salida' && (
                                      <div className="bg-gray-50 rounded-lg p-3">
                                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1">Subtipo</span>
                                        <p className="text-gray-800 font-medium">
                                          {mov.subtipo_salida === 'receta' ? '💊 Receta médica' :
                                           mov.subtipo_salida === 'consumo_interno' ? '🏥 Consumo interno' :
                                           mov.subtipo_salida === 'merma' ? '📉 Merma' :
                                           mov.subtipo_salida === 'caducidad' ? '⏰ Caducidad' :
                                           mov.subtipo_salida === 'transferencia' ? '🔄 Transferencia' :
                                           mov.subtipo_salida || 'No especificado'}
                                        </p>
                                      </div>
                                    )}
                                    {mov.tipo === 'salida' && mov.subtipo_salida === 'receta' && mov.numero_expediente && (
                                      <div className="bg-purple-50 rounded-lg p-3">
                                        <span className="text-[10px] font-bold text-purple-400 uppercase tracking-wider block mb-1">No. Expediente</span>
                                        <p className="text-purple-800 font-mono font-bold">{mov.numero_expediente}</p>
                                      </div>
                                    )}
                                    <div className="bg-gray-50 rounded-lg p-3">
                                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1">Fecha Exacta</span>
                                      <p className="text-gray-800 font-medium text-sm">
                                        {(mov.fecha_movimiento || mov.fecha) 
                                          ? new Date(mov.fecha_movimiento || mov.fecha).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' }) 
                                          : '-'}
                                      </p>
                                    </div>
                                  </div>
                                  
                                  {mov.observaciones && (
                                    <div className="mt-4">
                                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-2">Observaciones</span>
                                      <p className="text-gray-700 bg-amber-50 p-3 rounded-lg border border-amber-200 text-sm leading-relaxed">
                                        {mov.observaciones}
                                      </p>
                                    </div>
                                  )}
                                  
                                  {/* ISS-SEC FIX: Acciones solo para Farmacia/Admin */}
                                  {esFarmacia && mov.tipo === 'salida' && (
                                    <div className="mt-5 pt-4 border-t border-gray-200">
                                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-3">Acciones</span>
                                      <div className="flex flex-wrap gap-3">
                                        {mov.subtipo_salida !== 'receta' && (
                                          <button
                                            onClick={(e) => { e.stopPropagation(); descargarReciboSalida(mov); }}
                                            className="inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-b from-blue-500 to-blue-600 text-white rounded-xl hover:from-blue-600 hover:to-blue-700 transition-all duration-200 text-sm font-semibold shadow-sm hover:shadow-md"
                                            title="Descargar hoja de entrega"
                                          >
                                            <FaFilePdf className="text-base" />
                                            Hoja de Entrega
                                          </button>
                                        )}
                                        {!mov.confirmado ? (
                                          <button
                                            onClick={(e) => { e.stopPropagation(); confirmarEntregaIndividual(mov.id); }}
                                            disabled={confirmandoMovimiento === mov.id}
                                            className={`
                                              inline-flex items-center gap-2 px-4 py-2.5 text-white rounded-xl 
                                              transition-all duration-200 text-sm font-semibold shadow-sm hover:shadow-md
                                              disabled:opacity-50 disabled:cursor-not-allowed
                                              ${mov.subtipo_salida === 'receta' 
                                                ? 'bg-gradient-to-b from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700' 
                                                : 'bg-gradient-to-b from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700'
                                              }
                                            `}
                                            title={mov.subtipo_salida === 'receta' ? "Confirmar dispensación" : "Confirmar entrega"}
                                          >
                                            {confirmandoMovimiento === mov.id ? (
                                              <FaSpinner className="animate-spin text-base" />
                                            ) : (
                                              <FaClipboardCheck className="text-base" />
                                            )}
                                            {confirmandoMovimiento === mov.id 
                                              ? 'Confirmando...' 
                                              : (mov.subtipo_salida === 'receta' ? 'Confirmar Dispensación' : 'Confirmar Entrega')
                                            }
                                          </button>
                                        ) : !esMedico ? (
                                          <button
                                            onClick={(e) => { e.stopPropagation(); descargarReciboFinalizado(mov); }}
                                            className="inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-b from-emerald-500 to-emerald-600 text-white rounded-xl hover:from-emerald-600 hover:to-emerald-700 transition-all duration-200 text-sm font-semibold shadow-sm hover:shadow-md"
                                            title="Descargar comprobante"
                                          >
                                            <FaCheckCircle className="text-base" />
                                            {mov.subtipo_salida === 'receta' ? 'Comprobante Dispensación' : 'Comprobante Entregado'}
                                          </button>
                                        ) : (
                                          <span className="inline-flex items-center gap-2 px-4 py-2.5 text-emerald-600 text-sm font-semibold">
                                            <FaCheckCircle className="text-base" />
                                            Entregado
                                          </span>
                                        )}
                                      </div>
                                    </div>
                                  )}
                                </div>
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

        {/* 📄 PAGINACIÓN Premium */}
        {vistaAgrupada ? (
          totalGrupos > 0 && (
            <div className="mt-6">
              <Pagination
                page={pageGrupos}
                totalPages={Math.max(1, Math.ceil(totalGrupos / GRUPOS_POR_PAGINA))}
                totalItems={totalGrupos}
                pageSize={GRUPOS_POR_PAGINA}
                onPageChange={setPageGrupos}
              />
            </div>
          )
        ) : (
          total > 0 && (
            <div className="mt-6">
              <Pagination
                page={page}
                totalPages={Math.max(1, Math.ceil(total / PAGE_SIZE_INDIVIDUAL))}
                totalItems={total}
                pageSize={PAGE_SIZE_INDIVIDUAL}
                onPageChange={setPage}
              />
            </div>
          )
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
                <FaTrash /> Cancelar Salida Pendiente
              </h2>
            </div>
            <div className="p-6">
              <p className="text-gray-700 mb-4">
                ¿Estás seguro de cancelar esta salida pendiente?
              </p>
              <p className="text-sm text-gray-600 bg-blue-50 border border-blue-200 rounded-lg p-3">
                <FaInfoCircle className="inline text-blue-600 mr-2" />
                <strong>Nota:</strong> Como la salida está pendiente, el stock en Farmacia Central no fue afectado. Solo se eliminarán los movimientos registrados.
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
                    <FaTrash /> Sí, cancelar salida
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Modal Confirmación de Entrega (2 pasos) */}
      {confirmConfirmarGrupo && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
            <div className="px-6 py-4 border-b bg-gradient-to-r from-green-600 to-emerald-600 rounded-t-xl">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <FaCheckCircle /> Confirmar Entrega
              </h2>
            </div>
            <div className="p-6">
              <div className="mb-4">
                <p className="text-gray-700 font-medium mb-2">
                  ¿Confirmar la entrega al centro <span className="text-green-700 font-bold">{confirmConfirmarGrupo.centro_nombre}</span>?
                </p>
                <p className="text-sm text-gray-600">
                  Grupo: <span className="font-mono bg-gray-100 px-2 py-0.5 rounded">{confirmConfirmarGrupo.id}</span>
                </p>
              </div>
              
              {/* Resumen de items */}
              <div className="bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-lg p-4 mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-8 h-8 rounded-full bg-green-200 flex items-center justify-center">
                    <span className="text-lg">📦</span>
                  </div>
                  <span className="font-semibold text-green-800">Resumen de la Entrega</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="bg-white/70 rounded p-2">
                    <span className="text-gray-600">Total productos:</span>
                    <span className="font-bold text-green-700 ml-2">{confirmConfirmarGrupo.num_items}</span>
                  </div>
                  <div className="bg-white/70 rounded p-2">
                    <span className="text-gray-600">Cantidad total:</span>
                    <span className="font-bold text-green-700 ml-2">{confirmConfirmarGrupo.total_cantidad}</span>
                  </div>
                </div>
              </div>
              
              {/* Advertencia importante */}
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                <p className="text-sm text-amber-800 flex items-start gap-2">
                  <FaExclamationTriangle className="mt-0.5 flex-shrink-0" />
                  <span>
                    <strong>Importante:</strong> Esta acción descontará el stock del Almacén Central y registrará la entrada en el centro destino. Esta operación no se puede deshacer.
                  </span>
                </p>
              </div>
            </div>
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end gap-3 rounded-b-xl">
              <button
                onClick={() => setConfirmConfirmarGrupo(null)}
                className="px-4 py-2 border rounded-lg hover:bg-gray-100 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={() => confirmarEntregaGrupo(confirmConfirmarGrupo.id)}
                disabled={confirmandoGrupo === confirmConfirmarGrupo.id}
                className="px-4 py-2 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg hover:from-green-700 hover:to-emerald-700 transition-colors disabled:opacity-50 flex items-center gap-2 shadow-md"
              >
                {confirmandoGrupo === confirmConfirmarGrupo.id ? (
                  <>
                    <FaSpinner className="animate-spin" /> Confirmando...
                  </>
                ) : (
                  <>
                    <FaCheckCircle /> Sí, confirmar entrega
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Modal de Éxito después de Confirmar */}
      {resultadoConfirmacion && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
            <div className="px-6 py-4 border-b bg-gradient-to-r from-emerald-500 to-green-600 rounded-t-xl">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <FaCheckCircle /> ¡Entrega Confirmada Exitosamente!
              </h2>
            </div>
            <div className="p-6">
              {/* Icono de éxito animado */}
              <div className="flex justify-center mb-4">
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-green-400 to-emerald-500 flex items-center justify-center shadow-lg animate-pulse">
                  <FaCheckCircle className="text-white text-3xl" />
                </div>
              </div>
              
              <p className="text-center text-gray-700 font-medium mb-4">
                {resultadoConfirmacion.mensaje}
              </p>
              
              {/* Resumen detallado */}
              <div className="bg-gradient-to-br from-emerald-50 to-green-50 border border-emerald-200 rounded-lg p-4 mb-4">
                <h3 className="font-semibold text-emerald-800 mb-3 flex items-center gap-2">
                  <span className="text-lg">📋</span> Detalle de la Confirmación
                </h3>
                
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between items-center bg-white/70 rounded p-2">
                    <span className="text-gray-600">Grupo:</span>
                    <span className="font-mono font-bold text-emerald-700">{resultadoConfirmacion.grupoId}</span>
                  </div>
                  <div className="flex justify-between items-center bg-white/70 rounded p-2">
                    <span className="text-gray-600">Centro destino:</span>
                    <span className="font-bold text-emerald-700">{resultadoConfirmacion.centroNombre}</span>
                  </div>
                  <div className="flex justify-between items-center bg-white/70 rounded p-2">
                    <span className="text-gray-600">Productos procesados:</span>
                    <span className="font-bold text-emerald-700">{resultadoConfirmacion.totalItems}</span>
                  </div>
                </div>
                
                {/* Lista de items confirmados */}
                {resultadoConfirmacion.itemsConfirmados.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-emerald-200">
                    <p className="text-xs font-semibold text-emerald-700 mb-2">Productos confirmados:</p>
                    <div className="max-h-32 overflow-y-auto space-y-1">
                      {resultadoConfirmacion.itemsConfirmados.map((item, idx) => (
                        <div key={idx} className="flex justify-between items-center text-xs bg-white/50 rounded px-2 py-1">
                          <span className="text-gray-700 truncate flex-1">{item.producto || item.numero_lote}</span>
                          <span className="font-bold text-emerald-600 ml-2">-{item.cantidad}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              
              {/* Nota informativa */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <p className="text-sm text-blue-800 flex items-start gap-2">
                  <FaInfoCircle className="mt-0.5 flex-shrink-0" />
                  <span>
                    El stock ha sido descontado del Almacén Central y registrado como entrada en el centro destino. Puedes descargar el comprobante desde la lista de movimientos.
                  </span>
                </p>
              </div>
            </div>
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-center gap-3 rounded-b-xl">
              <button
                onClick={() => {
                  // Descargar comprobante
                  descargarComprobanteGrupo(resultadoConfirmacion.grupoId);
                }}
                className="px-4 py-2 border border-emerald-300 text-emerald-700 rounded-lg hover:bg-emerald-50 transition-colors flex items-center gap-2"
              >
                <FaFileDownload /> Descargar Comprobante
              </button>
              <button
                onClick={() => setResultadoConfirmacion(null)}
                className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-green-600 text-white rounded-lg hover:from-emerald-600 hover:to-green-700 transition-colors flex items-center gap-2 shadow-md"
              >
                <FaCheckCircle /> Aceptar
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* MOV-FECHA: Modal de confirmación de fecha de salida diferente */}
      {showConfirmFechaSalida && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md animate-in fade-in zoom-in duration-200">
            <div className="px-6 py-4 border-b bg-gradient-to-r from-blue-600 to-indigo-600 rounded-t-xl">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                📅 Confirmar Fecha de Salida
              </h2>
              <p className="text-white/80 text-sm mt-1">La fecha efectiva difiere de la fecha actual</p>
            </div>
            
            <div className="p-6">
              <div className="mb-4 p-4 bg-blue-50 border-2 border-blue-200 rounded-lg">
                <p className="text-blue-800 font-semibold text-center mb-2">
                  ⚠️ Está registrando una salida con fecha diferente a la actual
                </p>
                <div className="space-y-2 text-sm mt-3">
                  <div className="flex justify-between py-1 border-b border-blue-100">
                    <span className="text-blue-600">Fecha de salida indicada:</span>
                    <span className="font-bold text-blue-900">
                      {formData.fecha_salida ? new Date(formData.fecha_salida).toLocaleString('es-MX') : '-'}
                    </span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-blue-600">Fecha de registro (sistema):</span>
                    <span className="font-medium text-gray-700">{new Date().toLocaleString('es-MX')}</span>
                  </div>
                </div>
              </div>
              
              <div className="bg-amber-50 border border-amber-300 rounded-lg p-3 text-sm text-amber-800">
                <strong>Nota:</strong> La fecha de salida será registrada para trazabilidad y reportes. 
                La fecha de registro en el sistema se mantendrá automáticamente.
              </div>
            </div>
            
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-between rounded-b-xl">
              <button
                onClick={() => setShowConfirmFechaSalida(false)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={() => {
                  setShowConfirmFechaSalida(false);
                  // Continuar con el registro — re-invocar registrarMovimiento 
                  // que ahora pasará el check de showConfirmFechaSalida=false
                  registrarMovimiento();
                }}
                className="px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-colors font-medium shadow-md flex items-center gap-2"
              >
                <FaCheckCircle />
                Confirmar Fecha y Registrar
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* ISS-SEC FIX: Modal Confirmación Merma/Caducidad - Proceso de 2 pasos */}
      {showConfirmMerma && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg animate-in fade-in zoom-in duration-200">
            {/* Header con color según tipo */}
            <div className={`px-6 py-4 border-b rounded-t-xl ${
              formData.subtipo_salida === 'merma' 
                ? 'bg-gradient-to-r from-orange-500 to-red-500' 
                : 'bg-gradient-to-r from-amber-500 to-orange-500'
            }`}>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <FaExclamationTriangle className="animate-pulse" />
                {formData.subtipo_salida === 'merma' ? '⚠️ Confirmar Salida por MERMA' : '⏰ Confirmar Salida por CADUCIDAD'}
              </h2>
              <p className="text-white/80 text-sm mt-1">Paso {confirmStep} de 2 - Esta operación es IRREVERSIBLE</p>
            </div>
            
            <div className="p-6">
              {confirmStep === 1 ? (
                /* PASO 1: Mostrar resumen */
                <>
                  <div className="mb-4 p-4 bg-red-50 border-2 border-red-200 rounded-lg">
                    <p className="text-red-800 font-semibold text-center">
                      ⚠️ ATENCIÓN: El stock se descontará PERMANENTEMENTE
                    </p>
                  </div>
                  
                  {/* Resumen del producto */}
                  <div className="bg-gray-50 rounded-lg p-4 mb-4 border">
                    <h4 className="font-semibold text-gray-700 mb-3 flex items-center gap-2">
                      <span className="text-xl">📦</span> Resumen de la Operación
                    </h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between py-1 border-b">
                        <span className="text-gray-600">Tipo de salida:</span>
                        <span className={`font-bold ${formData.subtipo_salida === 'merma' ? 'text-red-600' : 'text-orange-600'}`}>
                          {formData.subtipo_salida === 'merma' ? '📉 MERMA' : '⏰ CADUCIDAD'}
                        </span>
                      </div>
                      <div className="flex justify-between py-1 border-b">
                        <span className="text-gray-600">Producto:</span>
                        <span className="font-medium text-gray-800">
                          {(() => {
                            const lote = lotes.find(l => l.id === parseInt(formData.lote));
                            return lote?.producto_nombre || 'N/A';
                          })()}
                        </span>
                      </div>
                      <div className="flex justify-between py-1 border-b">
                        <span className="text-gray-600">Lote:</span>
                        <span className="font-mono bg-gray-200 px-2 rounded">
                          {(() => {
                            const lote = lotes.find(l => l.id === parseInt(formData.lote));
                            return lote?.numero_lote || 'N/A';
                          })()}
                        </span>
                      </div>
                      <div className="flex justify-between py-1 border-b">
                        <span className="text-gray-600">Cantidad a dar de baja:</span>
                        <span className="font-bold text-red-600 text-lg">{formData.cantidad} unidades</span>
                      </div>
                      <div className="flex justify-between py-1">
                        <span className="text-gray-600">Motivo registrado:</span>
                        <span className="text-gray-800 text-right max-w-[200px] break-words">
                          {formData.observaciones || 'Sin especificar'}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="bg-amber-50 border border-amber-300 rounded-lg p-3 text-sm text-amber-800">
                    <strong>Nota:</strong> Se generará un registro en el historial de movimientos y podrá descargar el comprobante PDF después de confirmar.
                  </div>
                </>
              ) : (
                /* PASO 2: Confirmación final */
                <>
                  <div className="mb-4 p-4 bg-red-100 border-2 border-red-300 rounded-lg text-center">
                    <p className="text-red-800 font-bold text-lg mb-2">
                      🛑 CONFIRMACIÓN FINAL
                    </p>
                    <p className="text-red-700">
                      Está a punto de dar de baja <strong className="text-xl">{formData.cantidad}</strong> unidades
                    </p>
                  </div>
                  
                  <div className="text-center py-4">
                    <p className="text-gray-700 mb-4">
                      Para confirmar, haga clic en <strong>"CONFIRMAR BAJA"</strong>
                    </p>
                    <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
                      <FaHistory className="animate-spin" />
                      <span>Se registrará en el historial de auditoría</span>
                    </div>
                  </div>
                </>
              )}
            </div>
            
            {/* Footer con botones */}
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-between rounded-b-xl">
              <button
                onClick={() => {
                  setShowConfirmMerma(false);
                  setConfirmStep(1);
                }}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
                disabled={submitting}
              >
                Cancelar
              </button>
              
              <div className="flex gap-2">
                {confirmStep === 2 && (
                  <button
                    onClick={() => setConfirmStep(1)}
                    className="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
                    disabled={submitting}
                  >
                    ← Volver
                  </button>
                )}
                
                {confirmStep === 1 ? (
                  <button
                    onClick={() => setConfirmStep(2)}
                    className="px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-lg hover:from-amber-600 hover:to-orange-600 transition-colors font-medium shadow-md"
                  >
                    Continuar →
                  </button>
                ) : (
                  <button
                    onClick={() => {
                      // Llamar a registrarMovimiento - el modal ya está abierto
                      registrarMovimiento();
                    }}
                    className={`px-6 py-2 rounded-lg font-bold transition-colors shadow-lg flex items-center gap-2 ${
                      formData.subtipo_salida === 'merma'
                        ? 'bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white'
                        : 'bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-white'
                    }`}
                    disabled={submitting}
                  >
                    {submitting ? (
                      <>
                        <FaSpinner className="animate-spin" />
                        Procesando...
                      </>
                    ) : (
                      <>
                        <FaCheckCircle />
                        CONFIRMAR BAJA
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Movimientos;
