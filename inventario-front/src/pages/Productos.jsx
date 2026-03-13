import { useState, useEffect, useMemo, useCallback, useRef } from 'react';

import {

  FaPlus,

  FaEdit,

  FaTrash,

  FaToggleOn,

  FaToggleOff,

  FaFileUpload,

  FaFilter,

  FaChevronDown,

  FaDownload,

  FaBoxOpen,

  FaHistory,

  FaTimes,

  FaLayerGroup,

  FaCalendarAlt

} from 'react-icons/fa';

import { toast } from 'react-hot-toast';

import { productosAPI } from '../services/api';

import { DEV_CONFIG } from '../config/dev';

import { usePermissions } from '../hooks/usePermissions';

import { ProtectedButton } from '../components/ProtectedAction';
import PageHeader from '../components/PageHeader';
import Pagination from '../components/Pagination';
import { ProductosSkeleton } from '../components/skeletons';
import LimpiarInventario from '../components/LimpiarInventario';
// ISS-SEC: Componentes para confirmación en 2 pasos
import TwoStepConfirmModal from '../components/TwoStepConfirmModal';
import { useConfirmation } from '../hooks/useConfirmation';
import ImportadorModerno from '../components/ImportadorModerno';
import useEscapeToClose from '../hooks/useEscapeToClose';

import { COLORS } from '../constants/theme';

import { createExcelReport } from '../utils/reportExport';

import { hasAccessToken } from '../services/tokenManager';

// ISS-003 FIX: Importar validadores alineados con backend
import { validarProducto, normalizarProducto, sanitizeInput } from '../utils/validation';

// ISS-002 FIX: Importar contratos DTO para normalización de datos
import { getStockProducto, formatStock } from '../utils/dtoContracts';

// ISS-003 FIX (audit27): Importar hook de catálogos dinámicos
import { useCatalogos } from '../hooks/useCatalogos';


// ISS-003 FIX (audit27): Estas constantes se usan como fallback
// El hook useCatalogos obtiene los valores actualizados del API
const UNIDADES_FALLBACK = [

  'AMPOLLETA',

  'CAJA',

  'CAPSULA',

  'FRASCO',

  'GR',

  'ML',

  'PIEZA',

  'SOBRE',

  'TABLETA',

];



const resolveNivelStock = (producto) => calcularNivelStock(producto);



const normalizeText = (text) =>

  text

    ? text

        .toString()

        .normalize('NFD')

        .replace(/[\u0300-\u036f]/g, '')

        .toLowerCase()

    : '';



const NIVELES_INVENTARIO = [

  { value: '', label: 'Todos los niveles' },

  { value: 'sin_stock', label: 'Sin inventario' },

  { value: 'critico', label: 'Crítico' },

  { value: 'bajo', label: 'Bajo' },

  { value: 'normal', label: 'Normal' },

  { value: 'alto', label: 'Alto' },

];



const isDevSession = () => {
  return DEV_CONFIG.MOCKS_ENABLED && !hasAccessToken();
};



// ISS-002 FIX: Usar contrato DTO centralizado para obtener stock
// La función getStockProducto de dtoContracts.js maneja la normalización
// y valida el contrato con el backend de forma consistente
const getInventarioDisponible = (producto) => {
  return getStockProducto(producto, { strict: false, logWarnings: true });
};

// ISS-002 FIX: Usar formateo centralizado
const formatInventario = (producto) => {
  return formatStock(producto);
};

// ISS-UX: Generar tooltip informativo para el inventario del producto
const generarTooltipInventario = (producto) => {
  const inventario = getInventarioDisponible(producto);
  const minimo = Number(producto.stock_minimo) || 0;
  const nivelStock = calcularNivelStock(producto);
  const estado = determinarEstadoProducto(producto);
  
  const nivelLabels = {
    sin_stock: '🔴 Sin inventario',
    critico: '🔴 Crítico',
    bajo: '🟡 Bajo',
    normal: '🟢 Normal',
    alto: '🟢 Alto',
  };
  
  const estadoEmojis = {
    'Activo': '✅',
    'Inactivo': '⛔',
    'Sin inventario': '📭',
    'Por surtir': '⚠️',
  };
  
  const diferencia = inventario - minimo;
  let lineaDiferencia = '';
  if (minimo > 0) {
    if (diferencia > 0) {
      lineaDiferencia = `✨ Excedente: +${diferencia.toLocaleString()}`;
    } else if (diferencia < 0) {
      lineaDiferencia = `⏳ Faltante: ${diferencia.toLocaleString()}`;
    } else {
      lineaDiferencia = `⚖️ Justo en mínimo`;
    }
  }
  
  return [
    `📦 Inventario de Producto`,
    `━━━━━━━━━━━━━━━━━━━━`,
    `📊 Stock actual: ${inventario.toLocaleString()}`,
    `📉 Stock mínimo: ${minimo > 0 ? minimo.toLocaleString() : 'No definido'}`,
    minimo > 0 ? `━━━━━━━━━━━━━━━━━━━━` : null,
    lineaDiferencia || null,
    `━━━━━━━━━━━━━━━━━━━━`,
    `${nivelLabels[nivelStock] || nivelStock}`,
    `${estadoEmojis[estado.label] || '•'} ${estado.label}`,
  ].filter(Boolean).join('\n');
};



const calcularNivelStock = (producto) => {

  const inventario = getInventarioDisponible(producto);

  const minimo = Number(producto.stock_minimo) || 0;

  if (inventario <= 0) return 'sin_stock';

  if (minimo <= 0) {

    if (inventario < 25) return 'bajo';

    if (inventario < 100) return 'normal';

    return 'alto';

  }

  const ratio = inventario / minimo;

  if (ratio < 0.5) return 'critico';

  if (ratio < 1) return 'bajo';

  if (ratio <= 2) return 'normal';

  return 'alto';

};



const determinarEstadoProducto = (producto) => {

  const inventario = getInventarioDisponible(producto);

  const minimo = Number(producto.stock_minimo) || 0;

  if (!producto.activo) {

    return { label: 'Inactivo', activo: false };

  }

  if (inventario <= 0) {

    return { label: 'Sin inventario', activo: false };

  }

  if (minimo > 0 && inventario < minimo) {

    return { label: 'Por surtir', activo: true };

  }

  return { label: 'Activo', activo: true };

};



const renderEstadoBadge = (texto, activo = true) => {

  const color = activo ? COLORS.success : COLORS.danger;

  return (

    <span

      style={{

        backgroundColor: `${color}22`,

        color,

      }}

      className="px-2 py-0.5 rounded-full text-[11px] font-semibold whitespace-nowrap"

    >

      {texto}

    </span>

  );

};



const renderStockBadge = (nivel) => {

  const map = {

    sin_stock: COLORS.danger,

    critico: COLORS.danger,

    bajo: COLORS.warning,

    normal: COLORS.info,

    alto: COLORS.success,

  };

  const label = {

    sin_stock: 'Sin inventario',

    critico: 'Crítico',

    bajo: 'Bajo',

    normal: 'Normal',

    alto: 'Alto',

  };

  const color = map[nivel] || COLORS.info;

  return (

    <span

      style={{ backgroundColor: `${color}22`, color }}

      className="px-2 py-0.5 rounded-full text-[11px] font-semibold whitespace-nowrap"

    >

      {label[nivel] || nivel || 'N/D'}

    </span>

  );

};



const DEFAULT_FORM = {
  clave: '',
  nombre: '',
  nombre_comercial: '',
  descripcion: '',
  unidad_medida: 'PIEZA',
  categoria: 'medicamento',
  stock_minimo: '10',
  sustancia_activa: '',
  presentacion: '',
  concentracion: '',
  via_administracion: '',
  requiere_receta: false,
  es_controlado: false,
  activo: true,
  imagen: null,
  imagenPreview: null,
};

// ISS-003 FIX (audit27): Constantes removidas - ahora se obtienen del hook useCatalogos
// Las constantes CATEGORIAS y VIAS_ADMINISTRACION ahora vienen del API
// Ver: inventario-front/src/hooks/useCatalogos.js

// ISS-PERMS FIX: Unidades para MOCK_PRODUCTS (fuera del componente)
const MOCK_UNIDADES = ['TABLETA', 'CAJA', 'FRASCO', 'AMPOLLETA', 'SOBRE', 'PIEZA'];

const MOCK_PRODUCTS = Array.from({ length: 124 }).map((_, index) => {
  const id = index + 1;
  const baseNames = [
    'Paracetamol 500mg tabletas',
    'Ibuprofeno 400mg cápsulas',
    'Amoxicilina 875mg',
    'Alcohol etílico 70%',
    'Clonazepam 2mg',
    'Diclofenaco sódico 75mg',
    'Omeprazol 20mg',
    'Metformina 850mg',
    'Metamizol sódico 500mg',
    'Ranitidina 150mg',
  ];
  const alertas = ['critico', 'bajo', 'normal', 'alto'];
  return {
    id,
    clave: `MED-${String(id).padStart(3, '0')}`,
    nombre: baseNames[id % baseNames.length],
    unidad_medida: MOCK_UNIDADES[id % MOCK_UNIDADES.length],
    stock_minimo: 25 + (id % 6) * 5,
    stock_actual: 120 + (id % 8) * 15,
    activo: id % 9 !== 0,
    alerta_stock: alertas[id % alertas.length],
    creado_por: 'admin@edomex.gob.mx',
    created_at: new Date(Date.now() - id * 86400000).toISOString(),
  };
});

// ─── Helpers para el historial de auditoría ─────────────────────────────────
const LABELS_CAMPO = {
  clave: 'Clave',
  nombre: 'Nombre del producto',
  nombre_comercial: 'Nombre comercial',
  descripcion: 'Descripción',
  unidad_medida: 'Unidad de medida',
  stock_minimo: 'Stock mínimo',
  stock_actual: 'Stock actual',
  categoria: 'Categoría',
  presentacion: 'Presentación',
  sustancia_activa: 'Sustancia activa',
  concentracion: 'Concentración',
  via_administracion: 'Vía de administración',
  requiere_receta: 'Requiere receta',
  es_controlado: 'Medicamento controlado',
  activo: 'Estado activo',
  precio_unitario: 'Precio unitario',
  marca: 'Marca',
  laboratorio: 'Laboratorio',
  fabricante: 'Fabricante',
};

const formatearValorAudit = (campo, valor) => {
  if (valor === null || valor === undefined || valor === '') return 'Sin dato';
  if (typeof valor === 'boolean') return valor ? 'Sí' : 'No';
  if (campo === 'activo') return valor ? 'Activo' : 'Inactivo';
  if (campo === 'requiere_receta' || campo === 'es_controlado') return valor ? 'Sí' : 'No';
  if (typeof valor === 'object') return JSON.stringify(valor);
  return String(valor);
};

const calcularDiffAudit = (anterior, nuevo) => {
  if (!anterior && !nuevo) return [];
  const campos = new Set([
    ...Object.keys(anterior || {}),
    ...Object.keys(nuevo || {}),
  ]);
  const IGNORAR = ['id', 'created_at', 'updated_at', 'timestamp'];
  const cambios = [];
  campos.forEach((campo) => {
    if (IGNORAR.includes(campo)) return;
    const antes = (anterior || {})[campo];
    const despues = (nuevo || {})[campo];
    // eslint-disable-next-line eqeqeq
    if (antes != despues) {
      cambios.push({ campo, antes, despues });
    }
  });
  return cambios;
};

const ACCION_ESTILOS = {
  crear:      { bg: 'bg-emerald-100', text: 'text-emerald-800', border: 'border-emerald-300', punto: 'bg-emerald-500' },
  actualizar: { bg: 'bg-blue-100',    text: 'text-blue-800',    border: 'border-blue-300',    punto: 'bg-blue-500' },
  eliminar:   { bg: 'bg-red-100',     text: 'text-red-800',     border: 'border-red-300',     punto: 'bg-red-500' },
  importar:   { bg: 'bg-violet-100',  text: 'text-violet-800',  border: 'border-violet-300',  punto: 'bg-violet-500' },
  activar:    { bg: 'bg-emerald-100', text: 'text-emerald-800', border: 'border-emerald-300', punto: 'bg-emerald-500' },
  desactivar: { bg: 'bg-amber-100',   text: 'text-amber-800',   border: 'border-amber-300',   punto: 'bg-amber-500' },
  otro:       { bg: 'bg-gray-100',    text: 'text-gray-700',    border: 'border-gray-300',    punto: 'bg-gray-400' },
};
// ─────────────────────────────────────────────────────────────────────────────

const Productos = () => {

  const { user, permisos, getRolPrincipal } = usePermissions();
  
  // ISS-SEC: Hook para confirmación en 2 pasos
  const {
    confirmState,
    requestDeleteConfirmation,
    requestSaveConfirmation,
    executeWithConfirmation,
    cancelConfirmation,
  } = useConfirmation();
  
  // ISS-002 FIX (audit31): Cargar catálogos dinámicos desde API
  // IMPORTANTE: Si el catálogo no carga, se bloquea la edición para evitar inconsistencias
  const { catalogos, loading: loadingCatalogos, isFromFallback, error: catalogosError, refetch: refetchCatalogos } = useCatalogos({ autoLoad: true });
  
  // ISS-002 FIX: Estado para rastrear si el usuario reconoció la advertencia de fallback
  const [catalogosFallbackAcknowledged, setCatalogosFallbackAcknowledged] = useState(false);
  
  // ISS-002 FIX: Determinar si los catálogos están en modo degradado (fallback)
  const catalogosDegradados = isFromFallback && !catalogosFallbackAcknowledged;
  
  // Usar catálogos del API - en modo fallback se muestran pero con advertencia
  const UNIDADES = catalogos?.unidades || UNIDADES_FALLBACK;
  const CATEGORIAS = catalogos?.categorias || ['medicamento', 'material_curacion', 'insumo', 'equipo', 'otro'];
  const VIAS_ADMINISTRACION = catalogos?.viasAdministracion || ['oral', 'intravenosa', 'intramuscular', 'subcutanea', 'topica', 'inhalatoria', 'rectal', 'oftalmico', 'otico', 'nasal', 'otra'];
  
  // ISS-002 FIX: Bloquear creación/edición cuando catálogos no sincronizados
  const catalogosSincronizados = !isFromFallback || catalogosFallbackAcknowledged;

  const rolPrincipal = getRolPrincipal(); // ADMIN | FARMACIA | CENTRO | VISTA | SIN_ROL
  const esAdmin = rolPrincipal === 'ADMIN';
  const esFarmacia = rolPrincipal === 'FARMACIA';
  const esFarmaciaAdmin = esAdmin || esFarmacia; // Admin o Farmacia pueden gestionar productos
  const esCentroUser = rolPrincipal === 'CENTRO';
  const esVistaUser = rolPrincipal === 'VISTA';
  
  // ISS-FIX: Obtener nombre del centro para usuarios CENTRO
  const centroNombre = user?.centro?.nombre || user?.centro_nombre || null;
  
  // Verificar permisos granulares del backend para productos
  // Estos flags específicos tienen prioridad sobre el rol genérico
  const tienePermisoProductos = permisos?.verProductos === true;
  const tieneCrearProducto = permisos?.crearProducto === true;
  const tieneEditarProducto = permisos?.editarProducto === true;
  const tieneEliminarProducto = permisos?.eliminarProducto === true;
  const tieneExportarProductos = permisos?.exportarProductos === true;
  const tieneImportarProductos = permisos?.importarProductos === true;

  const puede = useMemo(() => ({
    // Para ver productos: debe tener permiso Y (ser farmacia/admin O vista O centro)
    // ISS-FIX: CENTRO users can view products (read-only) per backend permissions
    ver: tienePermisoProductos && (esFarmaciaAdmin || esVistaUser || esCentroUser),
    // Para acciones de escritura: usar permisos granulares del backend
    // El rol solo habilita si el permiso específico está activo
    crear: tienePermisoProductos && tieneCrearProducto,
    editar: tienePermisoProductos && tieneEditarProducto,
    eliminar: tienePermisoProductos && tieneEliminarProducto,
    exportar: tienePermisoProductos && tieneExportarProductos,
    importar: tienePermisoProductos && tieneImportarProductos,
    // cambiarEstado usa el permiso de editar (toggle activo es edición)
    cambiarEstado: tienePermisoProductos && tieneEditarProducto,
    // Solo CENTRO ve solo activos; VISTA puede ver todos (según permisos backend)
    verSoloActivos: esCentroUser,
    soloLectura: !tieneEditarProducto || !tienePermisoProductos,
    auditoria: tienePermisoProductos && esFarmaciaAdmin,
    // Indica si debe mostrar la columna de acciones (al menos un permiso de acción)
    tieneAcciones: tieneEditarProducto || tieneEliminarProducto || (tienePermisoProductos && esFarmaciaAdmin),
  }), [tienePermisoProductos, tieneCrearProducto, tieneEditarProducto, tieneEliminarProducto, tieneExportarProductos, tieneImportarProductos, esFarmaciaAdmin, esCentroUser, esVistaUser]);



  const [productos, setProductos] = useState([]);

  const [loading, setLoading] = useState(false); // Estado para carga de tabla
  const [savingProduct, setSavingProduct] = useState(false); // Estado separado para guardar en modal
  const [exportLoading, setExportLoading] = useState(false); // Estado separado para exportar
  const [importLoading, setImportLoading] = useState(false); // Estado separado para importar
  const [showImportModal, setShowImportModal] = useState(false); // Modal de ImportadorModerno
  const [actionLoading, setActionLoading] = useState(null); // ID del producto en acción (toggle/delete)

  const [error, setError] = useState(null);

  const [showModal, setShowModal] = useState(false);

  const mockProductosRef = useRef([...MOCK_PRODUCTS]);

  const [showFiltersMenu, setShowFiltersMenu] = useState(false);

  const [editingProduct, setEditingProduct] = useState(null);

  const [formData, setFormData] = useState(DEFAULT_FORM);

  const [formErrors, setFormErrors] = useState({});

  const [auditoriaVisible, setAuditoriaVisible] = useState(false);

  const [auditoriaLoading, setAuditoriaLoading] = useState(false);

  const [auditoriaData, setAuditoriaData] = useState(null);

  // ISS-FIX: Estado para modal de lotes de un producto específico
  const [lotesModalVisible, setLotesModalVisible] = useState(false);
  const [lotesModalLoading, setLotesModalLoading] = useState(false);
  const [lotesModalData, setLotesModalData] = useState(null);

  const [currentPage, setCurrentPage] = useState(1);

  const [totalPages, setTotalPages] = useState(1);

  const [totalProductos, setTotalProductos] = useState(0);

  const PAGE_SIZE = 25;



  const [filters, setFilters] = useState({

    search: '',

    estado: '',

    unidad: '',

    stock: '',

    tipo_medicamento: '',

  });

  // ESC para cerrar modales
  useEscapeToClose({
    isOpen: showModal,
    onClose: () => setShowModal(false),
    modalId: 'productos-form-modal',
    disabled: false
  });

  useEscapeToClose({
    isOpen: auditoriaVisible,
    onClose: () => setAuditoriaVisible(false),
    modalId: 'productos-auditoria-modal',
    disabled: auditoriaLoading
  });

  useEscapeToClose({
    isOpen: lotesModalVisible,
    onClose: () => setLotesModalVisible(false),
    modalId: 'productos-lotes-modal',
    disabled: lotesModalLoading
  });

  useEscapeToClose({
    isOpen: showImportModal,
    onClose: () => setShowImportModal(false),
    modalId: 'productos-import-modal',
    disabled: importLoading
  });



  const filtrosActivos = useMemo(() => {

    // Para roles con verSoloActivos, el filtro de estado está forzado y no cuenta como filtro "activo" del usuario

    const base = puede.verSoloActivos 

      ? [filters.search, filters.unidad, filters.stock] // Excluir estado

      : [filters.search, filters.estado, filters.unidad, filters.stock];

    return base.filter((v) => Boolean(v)).length;

  }, [filters, puede.verSoloActivos]);

  const toggleFiltersMenu = () => setShowFiltersMenu((prev) => !prev);



  const applyMockProductos = useCallback(() => {

    let data = [...mockProductosRef.current];



    if (filters.search) {

      const term = normalizeText(filters.search);

      data = data.filter((producto) => {

        const clave = normalizeText(producto.clave);

        const nombre = normalizeText(producto.nombre);

        return clave.includes(term) || nombre.includes(term);

      });

    }



    if (filters.unidad) {

      data = data.filter((producto) => producto.unidad_medida === filters.unidad);

    }



    if (filters.stock) {

      data = data.filter((producto) => resolveNivelStock(producto) === filters.stock);

    }



    if (puede.verSoloActivos) {

      data = data.filter((producto) => producto.activo);

    } else if (filters.estado) {

      const shouldBeActive = filters.estado === 'activo';

      data = data.filter((producto) => producto.activo === shouldBeActive);

    }



    const total = data.length;

    const start = (currentPage - 1) * PAGE_SIZE;

    const results = data.slice(start, start + PAGE_SIZE);

    const enrichedResults = results.map((producto) => ({

      ...producto,

      alerta_stock: resolveNivelStock(producto),

    }));



    setProductos(enrichedResults);

    setTotalProductos(total);

    setTotalPages(Math.max(1, Math.ceil(total / PAGE_SIZE)));

    setError(null);

    setLoading(false);

  }, [PAGE_SIZE, filters, currentPage, puede.verSoloActivos]);



  const fetchProductos = useCallback(async () => {

    setLoading(true);

    setError(null);

    try {

      if (isDevSession()) {

        applyMockProductos();

        return;

      }



      const params = {

        page: currentPage,
        page_size: PAGE_SIZE, // Sincronizar tamaño de página con el backend

      };



      if (filters.search) params.search = filters.search;

      if (filters.unidad) params.unidad_medida = filters.unidad;

      if (filters.stock) params.stock_status = filters.stock;

      if (filters.tipo_medicamento) params.tipo_medicamento = filters.tipo_medicamento;



      if (puede.verSoloActivos) {

        params.activo = 'true';

      } else if (filters.estado) {

        params.activo = filters.estado === 'activo' ? 'true' : 'false';

      }



      const response = await productosAPI.getAll(params);

      const data = response.data;

      const results = data.results || [];

      const enriched = results.map((producto) => ({

        ...producto,

        alerta_stock: resolveNivelStock(producto),

      }));

      setProductos(enriched);

      // Usar count del backend y PAGE_SIZE fijo para calcular páginas
      const total = data.count || enriched.length;

      setTotalProductos(total);

      // Usar PAGE_SIZE constante para cálculo consistente de páginas
      setTotalPages(Math.max(1, Math.ceil(total / PAGE_SIZE)));

    } catch (err) {

      console.error('Error al cargar productos', err);

      if (DEV_CONFIG.MOCKS_ENABLED) {

        applyMockProductos();

        return;

      }

      setError(err.response?.data?.detail || err.response?.data?.error || 'Error al cargar productos');

      toast.error(err.response?.data?.error || 'Error al cargar productos');

    } finally {

      setLoading(false);

    }

  }, [filters, currentPage, puede.verSoloActivos, applyMockProductos]);



  useEffect(() => {

    // Carga inicial de productos (devLog eliminado para producción)

    const timeout = setTimeout(() => {

      fetchProductos();

    }, 500);

    return () => clearTimeout(timeout);

  }, [fetchProductos]);


  const limpiarFiltros = useCallback(() => {
    setFilters({
      search: '',
      estado: '',
      unidad: '',
      stock: '',
      tipo_medicamento: '',
    });
    setCurrentPage(1);
    // Cerrar panel de filtros para indicar visualmente el reset
    setShowFiltersMenu(false);
    // El useEffect ya dispara fetchProductos cuando cambian los filtros
    // No llamar manualmente para evitar peticiones duplicadas
  }, []);



  const handleFilterChange = (key, value) => {

    setFilters((prev) => ({

      ...prev,

      [key]: value,

    }));

    setCurrentPage(1);

  };



  // ISS-003 FIX: Validación alineada con el backend
  const validarFormulario = (data) => {
    // Usar validador centralizado que conoce el contrato del backend
    const { valido, errores, primerError } = validarProducto(data, !!editingProduct);
    
    // Validación adicional local: unidad_medida debe ser de la lista
    // Solo validar si los catálogos están cargados (UNIDADES tiene elementos)
    if (data.unidad_medida && UNIDADES.length > 0 && !UNIDADES.includes(data.unidad_medida)) {
      errores.unidad_medida = 'Seleccione una unidad válida';
    }

    // Validación adicional local: categoria debe ser de la lista
    // Solo validar si los catálogos están cargados (CATEGORIAS tiene elementos)
    if (data.categoria && CATEGORIAS.length > 0 && !CATEGORIAS.includes(data.categoria)) {
      errores.categoria = 'Seleccione una categoría válida';
    }

    return errores;
  };



  const openModal = (producto = null) => {
    if (producto) {
      setEditingProduct(producto);
      setFormData({
        clave: producto.clave || '',
        nombre: producto.nombre || '',
        nombre_comercial: producto.nombre_comercial || '',
        descripcion: producto.descripcion || '',
        unidad_medida: producto.unidad_medida || 'PIEZA',
        categoria: producto.categoria || 'medicamento',
        stock_minimo: producto.stock_minimo ?? 10,
        sustancia_activa: producto.sustancia_activa || '',
        presentacion: producto.presentacion || '',
        concentracion: producto.concentracion || '',
        via_administracion: producto.via_administracion || '',
        requiere_receta: producto.requiere_receta ?? false,
        es_controlado: producto.es_controlado ?? false,
        activo: producto.activo ?? true,
        imagen: null,
        imagenPreview: producto.imagen || null,
      });
    } else {
      setEditingProduct(null);
      setFormData(DEFAULT_FORM);
    }
    setFormErrors({});
    setShowModal(true);
  };



  const closeModal = () => {

    setShowModal(false);

    setEditingProduct(null);

    setFormData(DEFAULT_FORM);

    setFormErrors({});

  };



  const handleSubmit = async (e) => {

    e.preventDefault();
    
    // ISS-002 FIX: Bloquear si catálogos no sincronizados y no reconocido
    if (isFromFallback && !catalogosFallbackAcknowledged) {
      toast.error('Los catálogos no están sincronizados. Las unidades/categorías pueden no coincidir con el backend.');
      return;
    }
    
    if (editingProduct && !puede.editar) {

      toast.error('No tiene permisos para editar productos');

      return;

    }

    if (!editingProduct && !puede.crear) {

      toast.error('No tiene permisos para crear productos');

      return;

    }

    const errors = validarFormulario(formData);

    if (Object.keys(errors).length) {

      setFormErrors(errors);

      toast.error('Verifique los campos marcados');

      return;

    }



    try {

      setSavingProduct(true); // Estado separado para no bloquear la tabla

      if (isDevSession()) {

        if (editingProduct) {

          mockProductosRef.current = mockProductosRef.current.map((producto) => {

            if (producto.id !== editingProduct.id) return producto;

            const stockMinimo = Number(formData.stock_minimo) || 0;

            const actualizado = {

              ...producto,

              ...formData,

              stock_minimo: stockMinimo,

            };

            actualizado.alerta_stock = resolveNivelStock(actualizado);

            return actualizado;

          });

          toast.success('Producto actualizado (modo demo)');

        } else {

          const stockMinimo = Number(formData.stock_minimo) || 0;

          const stockActual = Math.max(stockMinimo * 2, 50);

          const nuevoProducto = {

            ...formData,

            id: Date.now(),

            stock_minimo: stockMinimo,

            stock_actual: stockActual,

            alerta_stock: null,

            creado_por: user?.email || 'demo@edomex.gob.mx',

            created_at: new Date().toISOString(),

            activo: formData.activo ?? true,

          };

          nuevoProducto.alerta_stock = resolveNivelStock(nuevoProducto);

          mockProductosRef.current = [nuevoProducto, ...mockProductosRef.current];

          toast.success('Producto creado correctamente');

        }

        closeModal();

        applyMockProductos();

        setSavingProduct(false); // Limpiar antes de return

        return;

      }

      // Preparar datos para enviar al backend
      // Usar FormData si hay imagen, de lo contrario JSON normal
      let dataToSend;
      let hasImage = formData.imagen instanceof File;
      
      if (hasImage) {
        dataToSend = new FormData();
        dataToSend.append('clave', formData.clave || '');
        dataToSend.append('nombre', formData.nombre);
        dataToSend.append('nombre_comercial', formData.nombre_comercial || '');
        dataToSend.append('descripcion', formData.descripcion || '');
        dataToSend.append('unidad_medida', formData.unidad_medida);
        dataToSend.append('categoria', formData.categoria || 'medicamento');
        dataToSend.append('stock_minimo', parseInt(formData.stock_minimo, 10) || 0);
        dataToSend.append('sustancia_activa', formData.sustancia_activa || '');
        dataToSend.append('presentacion', formData.presentacion || '');
        dataToSend.append('concentracion', formData.concentracion || '');
        dataToSend.append('via_administracion', formData.via_administracion || '');
        dataToSend.append('requiere_receta', formData.requiere_receta);
        dataToSend.append('es_controlado', formData.es_controlado);
        dataToSend.append('activo', formData.activo);
        dataToSend.append('imagen', formData.imagen);
      } else {
        dataToSend = {
          clave: formData.clave || '',
          nombre: formData.nombre,
          nombre_comercial: formData.nombre_comercial || '',
          descripcion: formData.descripcion || '',
          unidad_medida: formData.unidad_medida,
          categoria: formData.categoria || 'medicamento',
          stock_minimo: parseInt(formData.stock_minimo, 10) || 0,
          sustancia_activa: formData.sustancia_activa || '',
          presentacion: formData.presentacion || '',
          concentracion: formData.concentracion || '',
          via_administracion: formData.via_administracion || '',
          requiere_receta: formData.requiere_receta,
          es_controlado: formData.es_controlado,
          activo: formData.activo,
        };
      }

      if (editingProduct) {

        await productosAPI.update(editingProduct.id, dataToSend, hasImage);

        toast.success('Producto actualizado correctamente');

      } else {

        const resp = await productosAPI.create(dataToSend, hasImage);
        const varInfo = resp?.data?.variante_info;
        if (varInfo?.es_variante) {
          // ISS-PROD-VAR: Notificar código asignado cuando es variante nueva
          toast(
            `Código asignado: ${varInfo.codigo_asignado} (variante de ${varInfo.codigo_base} por presentación diferente)`,
            { icon: 'ℹ️', duration: 10000 }
          );
        } else {
          toast.success('Producto creado correctamente');
        }

      }

      closeModal();

      fetchProductos();

    } catch (err) {

      console.error('Error al guardar producto', err);
      
      // Mapear errores del backend a campos del formulario
      const backendErrors = err.response?.data;
      if (backendErrors && typeof backendErrors === 'object') {
        const newFormErrors = {};
        // Mapear campos de error del backend a campos del frontend
        const fieldMap = {
          'clave': 'clave',
          'nombre': 'nombre',
          'unidad_medida': 'unidad_medida',
          'categoria': 'categoria',
          'stock_minimo': 'stock_minimo',
          'descripcion': 'descripcion',
          'sustancia_activa': 'sustancia_activa',
          'presentacion': 'presentacion',
          'concentracion': 'concentracion',
          'via_administracion': 'via_administracion',
        };
        
        let hasFieldErrors = false;
        for (const [backendField, messages] of Object.entries(backendErrors)) {
          if (Array.isArray(messages) && messages.length > 0) {
            const frontendField = fieldMap[backendField] || backendField;
            newFormErrors[frontendField] = messages[0];
            hasFieldErrors = true;
          }
        }
        
        if (hasFieldErrors) {
          setFormErrors(newFormErrors);
          toast.error('Por favor corrige los errores del formulario');
        } else if (backendErrors.error) {
          toast.error(backendErrors.error);
        } else if (backendErrors.detail) {
          toast.error(backendErrors.detail);
        } else {
          toast.error('Error al guardar producto');
        }
      } else {
        toast.error(err.response?.data?.error || 'Error al guardar producto');
      }

    } finally {

      setSavingProduct(false);

    }

  };



  const handleToggleActivo = async (producto) => {

    if (!puede.cambiarEstado) return;
    if (actionLoading === producto.id) return; // Evitar clics repetidos
    setActionLoading(producto.id);

    try {

      if (isDevSession()) {

        mockProductosRef.current = mockProductosRef.current.map((item) =>

          item.id === producto.id ? { ...item, activo: !item.activo } : item,

        );

        toast.success(`Producto ${producto.activo ? 'desactivado' : 'activado'} (modo demo)`);

        applyMockProductos();

        setActionLoading(null); // Limpiar antes de return

        return;

      }

      await productosAPI.toggleActivo(producto.id);

      toast.success(`Producto ${producto.activo ? 'desactivado' : 'activado'}`);

      fetchProductos();

    } catch (err) {

      console.error('Error al cambiar estado', err);
      console.error('Response data:', err.response?.data);
      console.error('Response status:', err.response?.status);

      const errorMsg = err.response?.data?.error || 
                       err.response?.data?.detail ||
                       JSON.stringify(err.response?.data) ||
                       'No se pudo cambiar el estado';
      toast.error(errorMsg);

    } finally {
      setActionLoading(null);
    }

  };

  // ISS-SEC: Función auxiliar para ejecutar eliminación de producto con confirmación
  const executeDeleteProducto = async ({ confirmed, actionData }) => {
    const { producto } = actionData;
    
    setActionLoading(producto.id);

    try {

      if (isDevSession()) {

        mockProductosRef.current = mockProductosRef.current.filter((item) => item.id !== producto.id);

        toast.success('Producto eliminado (modo demo)');

        applyMockProductos();

        setActionLoading(null);

        return;

      }

      await productosAPI.delete(producto.id, { confirmed });

      toast.success('Producto eliminado correctamente');

      fetchProductos();

    } catch (err) {

      console.error('Error al eliminar producto', err);

      // Mostrar razón específica del error
      const errorData = err.response?.data;
      let errorMsg = 'No se pudo eliminar el producto';
      if (errorData?.razon) {
        errorMsg = `${errorData.error}: ${errorData.razon}. ${errorData.sugerencia || ''}`;
      } else if (errorData?.error) {
        errorMsg = errorData.error;
      }
      toast.error(errorMsg);
      throw err; // Re-lanzar para que el modal maneje el estado

    } finally {
      setActionLoading(null);
    }
  };

  // ISS-SEC: handleDelete ahora inicia el flujo de confirmación en 2 pasos
  const handleDelete = (producto) => {

    if (!puede.eliminar) return;
    if (actionLoading === producto.id) return; // Evitar clics repetidos

    // Solicitar confirmación en 2 pasos con escritura de "ELIMINAR"
    requestDeleteConfirmation({
      title: 'Confirmar Eliminación de Producto',
      message: '¿Confirma ELIMINAR DEFINITIVAMENTE este producto?',
      warnings: [
        'Esta acción NO se puede deshacer',
        'Si el producto tiene lotes asociados, no podrá eliminarse',
        'Se eliminarán todos los datos del producto'
      ],
      itemInfo: {
        'Clave': producto.clave,
        'Nombre': producto.nombre,
        'Inventario': formatInventario(producto)
      },
      isCritical: true, // Eliminación permanente = crítica
      confirmPhrase: 'ELIMINAR', // Requiere escribir para confirmar
      confirmText: 'Eliminar Permanentemente',
      cancelText: 'Cancelar',
      tone: 'danger',
      onConfirm: executeDeleteProducto,
      actionData: { producto }
    });

  };



  const handleExportar = async () => {

    if (!puede.exportar) return;
    if (exportLoading) return; // Evitar clics repetidos

    try {

      setExportLoading(true);

      if (isDevSession()) {

        await createExcelReport({

          title: 'Listado de Productos',

          subtitle: `Generado ${new Date().toLocaleString('es-MX')}`,

          columns: [

            { header: '#', value: (_, idx) => idx + 1, width: 6 },

            { header: 'Clave', key: 'clave', width: 14 },

            { header: 'Nombre', key: 'nombre', width: 30 },

            { header: 'Unidad', key: 'unidad_medida', width: 12 },

            { header: 'Inventario', value: (row) => getInventarioDisponible(row), width: 14 },

            { header: 'Stock Mínimo', key: 'stock_minimo', width: 14 },

            { header: 'Estado', value: (row) => determinarEstadoProducto(row).label, width: 14 },

            { header: 'Nivel', value: (row) => resolveNivelStock(row), width: 12 }

          ],

          rows: mockProductosRef.current,

          fileName: `productos_demo_${new Date().toISOString().slice(0, 10)}`

        });

        toast.success('Archivo exportado (modo demo)');

        return;

      }

      const params = {};

      Object.entries(filters).forEach(([key, value]) => {

        if (!value) return;

        if (key === 'unidad') params.unidad_medida = value;

        else if (key === 'stock') params.stock_status = value;

        else if (key === 'estado') params.activo = value === 'activo' ? 'true' : 'false';

        else params[key] = value;

      });

      if (puede.verSoloActivos) params.activo = 'true';



      const response = await productosAPI.exportar(params);

      const blob = new Blob([response.data]);

      const url = window.URL.createObjectURL(blob);

      const link = document.createElement('a');

      link.href = url;

      link.setAttribute('download', `productos_${new Date().toISOString().slice(0, 10)}.xlsx`);

      document.body.appendChild(link);

      link.click();

      link.remove();

      // Liberar recursos del ObjectURL para evitar memory leaks
      window.URL.revokeObjectURL(url);

      toast.success('Archivo exportado correctamente');

    } catch (err) {

      console.error('Error al exportar', err);

      toast.error(err.response?.data?.error || 'No se pudo exportar');

    } finally {

      setExportLoading(false);

    }

  };

  // Handler para descargar plantilla de importación
  const handleDescargarPlantilla = async () => {
    try {
      const response = await productosAPI.plantilla();
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'Plantilla_Productos.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Plantilla descargada correctamente');
    } catch (err) {
      console.error('Error al descargar plantilla', err);
      toast.error('No se pudo descargar la plantilla');
    }
  };

  // Constantes para validación de importación
  const IMPORT_MAX_SIZE_MB = 10;
  const IMPORT_ALLOWED_EXTENSIONS = ['.xlsx', '.xls'];

  const handleImportar = async (e) => {
    if (!puede.importar) {
      toast.error('No tiene permisos para importar productos');
      e.target.value = null;
      return;
    }
    if (importLoading) {
      e.target.value = null;
      return; // Evitar clics repetidos
    }

    const file = e.target.files?.[0];
    if (!file) return;

    // Validar extensión del archivo
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!IMPORT_ALLOWED_EXTENSIONS.includes(extension)) {
      toast.error(`Extensión no permitida: ${extension}. Use: ${IMPORT_ALLOWED_EXTENSIONS.join(', ')}`);
      e.target.value = null;
      return;
    }

    // Validar tamaño del archivo
    const sizeMB = file.size / (1024 * 1024);
    if (sizeMB > IMPORT_MAX_SIZE_MB) {
      toast.error(`Archivo demasiado grande: ${sizeMB.toFixed(1)}MB. Máximo: ${IMPORT_MAX_SIZE_MB}MB`);
      e.target.value = null;
      return;
    }

    const form = new FormData();
    form.append('file', file);

    // Limpiar input inmediatamente para permitir reimportar el mismo archivo
    e.target.value = null;

    try {
      setImportLoading(true);
      if (isDevSession()) {
        const nuevos = Array.from({ length: 3 }).map((_, idx) => {
          const stockMin = 20 + idx * 5;
          const stockActual = stockMin + 50 + idx * 10;
          const demo = {
            id: Date.now() + idx,
            clave: `IMP-${String(mockProductosRef.current.length + idx + 1).padStart(3, '0')}`,
            nombre: `Producto importado ${idx + 1}`,
            unidad_medida: UNIDADES[(idx + mockProductosRef.current.length) % UNIDADES.length],
            precio_unitario: (12 + idx * 1.5).toFixed(2),
            stock_minimo: stockMin,
            stock_actual: stockActual,
            activo: true,
            creado_por: user?.email || 'demo@edomex.gob.mx',
            created_at: new Date().toISOString(),
          };
          demo.alerta_stock = resolveNivelStock(demo);
          return demo;
        });
        mockProductosRef.current = [...nuevos, ...mockProductosRef.current];
        toast.success(`Importación demo completada: ${nuevos.length} productos simulados`, { duration: 5000 });
        applyMockProductos();
        setImportLoading(false); // Limpiar antes de return
        return;
      }

      const response = await productosAPI.importar(form);
      const resumen = response.data?.resumen || response.data || {};
      const errores = response.data?.errores || [];

      toast.success(
        `Importación completada. Creados: ${resumen.creados || 0} | Actualizados: ${resumen.actualizados || 0} | Total: ${resumen.total_registros || 0}`,
        { duration: 5000 }
      );
      if (errores.length) {
        console.warn('Errores de importación de productos', errores);
        toast.error(`${errores.length} fila(s) con error. Revisa detalles en consola.`);
      }

      fetchProductos();
    } catch (err) {
      console.error('Error al importar', err);
      const errorMsg = err.response?.data?.error || 'No se pudo importar';
      toast.error(`Error: ${errorMsg}`, { duration: 5000 });
    } finally {
      setImportLoading(false);
    }
  };



  const verAuditoriaProducto = async (producto) => {

    if (!puede.auditoria) return;

    setAuditoriaVisible(true);

    setAuditoriaLoading(true);

    try {

      const response = await productosAPI.auditoria(producto.id);

      setAuditoriaData(response.data);

    } catch (err) {

      console.error('Error al cargar auditoría', err);

      toast.error(err.response?.data?.error || 'No se pudo cargar el historial');

      setAuditoriaVisible(false);

    } finally {

      setAuditoriaLoading(false);

    }

  };



  const cerrarAuditoria = () => {

    setAuditoriaVisible(false);

    setAuditoriaData(null);

  };

  // ISS-FIX: Función para ver lotes de un producto específico
  const verLotesProducto = async (producto) => {
    setLotesModalVisible(true);
    setLotesModalLoading(true);
    try {
      const response = await productosAPI.lotes(producto.id);
      setLotesModalData(response.data);
    } catch (err) {
      console.error('Error al cargar lotes del producto', err);
      toast.error(err.response?.data?.error || 'No se pudo cargar los lotes');
      setLotesModalVisible(false);
    } finally {
      setLotesModalLoading(false);
    }
  };

  const cerrarLotesModal = () => {
    setLotesModalVisible(false);
    setLotesModalData(null);
  };

  const formatFecha = (valor) => {

    if (!valor) return '-';

    try {

      return new Date(valor).toLocaleString('es-MX', {

        dateStyle: 'short',

        timeStyle: 'short',

      });

    } catch (err) {

      return valor;

    }

  };



  const renderTabla = () => {

    if (loading) {

      return <ProductosSkeleton />;

    }



    if (error) {

      return (

        <div className="py-12 text-center">

          <p className="text-danger font-medium">{error}</p>

          <button

            type="button"

            onClick={fetchProductos}

            className="mt-4 px-4 py-2 rounded-lg text-white bg-theme-gradient"

          >

            Reintentar

          </button>

        </div>

      );

    }



    if (!productos.length) {

      return (

        <div className="py-12 text-center text-gray-500">

          {filters.search || filters.unidad || filters.stock || filters.estado

            ? 'No hay productos que coincidan con los filtros.'

            : 'Aún no hay productos registrados.'}

        </div>

      );

    }

    // Vista de tarjetas para móvil
    const renderMobileCards = () => (
      <div className="space-y-3 lg:hidden">
        {productos.map((producto, idx) => {
          const consecutivo = (currentPage - 1) * PAGE_SIZE + idx + 1;
          const estadoInventario = determinarEstadoProducto(producto);
          const nivelStock = resolveNivelStock(producto);
          const numLotes = producto.lotes_activos ?? producto.lotes_count ?? producto.num_lotes ?? '-';
          
          return (
            <div key={producto.id} className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
              {/* Header con clave y estado */}
              <div className="flex items-start justify-between gap-2 mb-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs text-gray-500">#{consecutivo}</span>
                    <span className="font-bold text-theme-primary">{producto.clave || '-'}</span>
                    {renderEstadoBadge(estadoInventario.label, estadoInventario.activo)}
                  </div>
                  <h3 className="font-semibold text-gray-800 mt-1 line-clamp-2">{producto.nombre}</h3>
                  <p className="text-sm text-gray-500">{producto.presentacion || producto.unidad_medida || '-'}</p>
                </div>
                {renderStockBadge(nivelStock)}
              </div>
              
              {/* Info grid */}
              <div className={`grid ${esCentroUser ? 'grid-cols-2' : 'grid-cols-3'} gap-3 text-center py-3 border-y border-gray-100`}>
                <div>
                  <div className={`text-lg font-bold ${
                    nivelStock === 'sin_stock' || nivelStock === 'critico' ? 'text-red-600' :
                    nivelStock === 'bajo' ? 'text-amber-600' : 'text-slate-700'
                  }`}>
                    {formatInventario(producto)}
                  </div>
                  <div className="text-xs text-gray-500">Inventario</div>
                </div>
                <div>
                  <button
                    type="button"
                    onClick={() => verLotesProducto(producto)}
                    className="text-lg font-bold text-blue-600 hover:text-blue-800"
                  >
                    {numLotes}
                  </button>
                  <div className="text-xs text-gray-500">Lotes</div>
                </div>
                {!esCentroUser && (
                <div>
                  <div className="text-lg font-bold text-slate-700">{producto.stock_minimo || '-'}</div>
                  <div className="text-xs text-gray-500">Mín.</div>
                </div>
                )}
              </div>
              
              {/* Acciones */}
              {puede.tieneAcciones && (
                <div className="flex items-center justify-end gap-4 mt-3 pt-2">
                  {puede.editar && (
                    <button type="button" onClick={() => openModal(producto)} className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg">
                      <FaEdit size={18} />
                    </button>
                  )}
                  {puede.cambiarEstado && (
                    <button
                      type="button"
                      onClick={() => handleToggleActivo(producto)}
                      disabled={actionLoading === producto.id}
                      className={`p-2 rounded-lg ${producto.activo ? 'text-green-600 hover:bg-green-50' : 'text-gray-500 hover:bg-gray-100'}`}
                    >
                      {producto.activo ? <FaToggleOn size={20} /> : <FaToggleOff size={20} />}
                    </button>
                  )}
                  {puede.eliminar && (
                    <button
                      type="button"
                      onClick={() => handleDelete(producto)}
                      disabled={actionLoading === producto.id}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                    >
                      <FaTrash size={18} />
                    </button>
                  )}
                  {puede.auditoria && (
                    <button type="button" onClick={() => verAuditoriaProducto(producto)} className="p-2 text-purple-600 hover:bg-purple-50 rounded-lg">
                      <FaHistory size={18} />
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );

    return (
      <>
        {/* Vista móvil: tarjetas */}
        {renderMobileCards()}
        
        {/* Vista desktop: tabla */}
        <div className="hidden lg:block w-full table-soft">
        <table className="w-full table-fixed divide-y divide-gray-200">

          <thead className="thead-soft sticky top-0 z-10">

            <tr>

              {[

                { key: '#', width: 'w-[3%]' },

                { key: 'Clave', width: esCentroUser ? 'w-[8%]' : 'w-[7%]' },

                { key: 'Nombre', width: esCentroUser ? 'w-[22%]' : 'w-[18%]' },

                { key: 'Presentación', width: esCentroUser ? 'w-[18%]' : 'w-[14%]' },

                { key: 'Inventario', width: esCentroUser ? 'w-[10%]' : 'w-[8%]' },

                { key: 'Lotes', width: esCentroUser ? 'w-[7%]' : 'w-[5%]' },

                ...(!esCentroUser ? [{ key: 'Inv. Mín.', width: 'w-[6%]' }] : []),

                { key: 'Estado', width: esCentroUser ? 'w-[10%]' : 'w-[9%]' },

                { key: 'Nivel', width: esCentroUser ? 'w-[10%]' : 'w-[9%]' },

                ...(!esCentroUser ? [{ key: 'Creado por', width: 'w-[10%]' }] : []),

                ...(puede.tieneAcciones ? [{ key: 'Acciones', width: esCentroUser ? 'w-[12%]' : 'w-[11%]' }] : []),

              ].map((col) => (

                <th key={col.key} className={`px-2 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-white ${col.width}`}>

                  {col.key}

                </th>

              ))}

            </tr>

          </thead>

          <tbody className="bg-white divide-y divide-gray-100">

            {productos.map((producto, idx) => {

              const consecutivo = (currentPage - 1) * PAGE_SIZE + idx + 1;

              const estadoInventario = determinarEstadoProducto(producto);

              const nivelStock = resolveNivelStock(producto);

              // ISS-FIX: Usar lotes_activos que viene del serializer del backend
              const numLotes = producto.lotes_activos ?? producto.lotes_count ?? producto.num_lotes ?? '-';

              return (

              <tr

                key={producto.id}

                className={`transition ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-gray-100`}

              >

                <td className="px-2 py-2 text-xs font-semibold text-gray-500">{consecutivo}</td>

                <td className="px-2 py-2 text-xs font-semibold text-gray-800">{producto.clave || '-'}</td>

                <td className="px-2 py-2 text-xs text-gray-600" title={producto.nombre}>
                  <span className="line-clamp-2 leading-tight">
                    {producto.nombre}
                    {producto.es_controlado && (
                      <span className="ml-1 inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold bg-red-100 text-red-700 align-middle" title="Medicamento Controlado">CTRL</span>
                    )}
                  </span>
                </td>

                <td className="px-2 py-2 text-xs text-gray-600"><span className="line-clamp-2 leading-tight">{producto.presentacion || producto.unidad_medida || <span className="text-gray-400 italic">-</span>}</span></td>

                {/* Inventario con tooltip informativo */}
                <td className="px-2 py-2 text-xs">
                  <span 
                    className={`font-semibold tabular-nums cursor-help ${
                      nivelStock === 'sin_stock' || nivelStock === 'critico'
                        ? 'text-red-600'
                        : nivelStock === 'bajo'
                          ? 'text-amber-600'
                          : 'text-slate-700'
                    }`}
                    title={generarTooltipInventario(producto)}
                  >
                    {formatInventario(producto)}
                  </span>
                </td>

                <td className="px-2 py-2 text-xs">
                  <button
                    type="button"
                    onClick={() => verLotesProducto(producto)}
                    className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors cursor-pointer text-xs"
                    title={`📦 Ver lotes de: ${producto.nombre}\n━━━━━━━━━━━━━━━━━━━━\n📋 Lotes activos: ${numLotes}\n💡 Click para ver detalle`}
                  >
                    <FaLayerGroup className="text-[10px]" />
                    <span className="font-semibold">{numLotes !== null ? numLotes : '?'}</span>
                  </button>
                </td>

                {!esCentroUser && (
                <td 
                  className="px-2 py-2 text-xs cursor-help"
                  title={`📉 Stock Mínimo\n━━━━━━━━━━━━━━━━━━━━\nCantidad: ${producto.stock_minimo || 'No definido'}\n💡 Cuando el inventario baja de este valor, el producto se marca como "Por surtir"`}
                >
                  <span className={producto.stock_minimo ? 'text-slate-700' : 'text-gray-400 italic'}>
                    {producto.stock_minimo || '-'}
                  </span>
                </td>
                )}

                <td className="px-2 py-2 text-xs">{renderEstadoBadge(estadoInventario.label, estadoInventario.activo)}</td>

                <td className="px-2 py-2 text-xs">{renderStockBadge(nivelStock)}</td>

                {/* Creado por / Modificado por - solo visible para Farmacia/Admin */}
                {!esCentroUser && (
                <td className="px-2 py-2 text-[11px]">
                  {producto.creado_por_nombre ? (
                    <div className="leading-tight">
                      <div className="font-medium text-slate-700 truncate" title={producto.creado_por_nombre}>
                        {producto.creado_por_nombre.length > 12 ? producto.creado_por_nombre.substring(0, 12) + '…' : producto.creado_por_nombre}
                      </div>
                      {producto.modificado_por_nombre && producto.modificado_por_nombre !== producto.creado_por_nombre && (
                        <div className="text-amber-600 truncate" title={`Modificado por: ${producto.modificado_por_nombre}`}>
                          ✏️ {producto.modificado_por_nombre.length > 10 ? producto.modificado_por_nombre.substring(0, 10) + '…' : producto.modificado_por_nombre}
                        </div>
                      )}
                    </div>
                  ) : (
                    <span className="text-gray-400 italic">Sistema</span>
                  )}
                </td>
                )}

                {puede.tieneAcciones && (
                <td className="px-2 py-2 text-xs">

                  <div className="flex items-center gap-1.5">

                    {puede.editar && (

                      <button

                        type="button"

                        title="Editar"

                        onClick={() => openModal(producto)}

                        className="text-blue-600 hover:text-blue-800"

                      >

                        <FaEdit />

                      </button>

                    )}

                    {puede.cambiarEstado && (

                      <button

                        type="button"

                        title="Cambiar estado"

                        onClick={() => handleToggleActivo(producto)}

                        disabled={actionLoading === producto.id}

                        className={`${producto.activo ? 'text-green-600 hover:text-green-800' : 'text-gray-500 hover:text-gray-700'} disabled:opacity-50 disabled:cursor-not-allowed`}

                      >

                        {actionLoading === producto.id ? (
                          <div className="animate-spin rounded-full h-4 w-4 border-2 border-current border-t-transparent inline-block" />
                        ) : (
                          producto.activo ? <FaToggleOn size={18} /> : <FaToggleOff size={18} />
                        )}

                      </button>

                    )}

                    {puede.eliminar && (

                      <button

                        type="button"

                        title="Eliminar"

                        onClick={() => handleDelete(producto)}

                        disabled={actionLoading === producto.id}

                        className="text-red-600 hover:text-red-800 disabled:opacity-50 disabled:cursor-not-allowed"

                      >

                        {actionLoading === producto.id ? (
                          <div className="animate-spin rounded-full h-4 w-4 border-2 border-current border-t-transparent inline-block" />
                        ) : (
                          <FaTrash />
                        )}

                      </button>

                    )}

                    {puede.auditoria && (

                      <button

                        type="button"

                        title="Ver historial de cambios"

                        onClick={() => verAuditoriaProducto(producto)}

                        className="text-purple-600 hover:text-purple-800"

                      >

                        <FaHistory />

                      </button>

                    )}

                  </div>

                </td>
                )}

              </tr>

            )})}

          </tbody>

        </table>

      </div>
      </> 
    );

  };



  return (

    <div className="space-y-4 p-4 sm:p-6">

      <PageHeader
        icon={FaBoxOpen}
        title="Gestión de Productos"
        subtitle={`Total activos: ${totalProductos}`}
        badge={filtrosActivos > 0 ? `${filtrosActivos} filtros activos` : undefined}
        actions={
          <div className="flex flex-wrap gap-2 items-center">
            {/* Exportar - Solo si tiene permiso */}
            {puede.exportar && (
              <button
                type="button"
                onClick={handleExportar}
                disabled={exportLoading}
                className="cc-btn cc-btn-secondary"
              >
                {exportLoading ? (
                  <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-current border-t-transparent" />
                ) : (
                  <FaDownload className="text-xs" />
                )}
                <span className="hidden sm:inline">{exportLoading ? 'Exportando...' : 'Exportar'}</span>
              </button>
            )}

            {/* Importar - Solo Farmacia/Admin */}
            {puede.importar && (
              <>
                <button
                  type="button"
                  onClick={() => setShowImportModal(true)}
                  disabled={importLoading}
                  className="cc-btn cc-btn-secondary"
                >
                  {importLoading ? (
                    <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-current border-t-transparent" />
                  ) : (
                    <FaFileUpload className="text-xs" />
                  )}
                  <span className="hidden sm:inline">{importLoading ? 'Importando...' : 'Importar'}</span>
                </button>
                
                <button
                  type="button"
                  onClick={handleDescargarPlantilla}
                  className="cc-btn cc-btn-ghost"
                  title="Descargar plantilla Excel para importación"
                >
                  <FaDownload className="text-xs" />
                  <span className="hidden sm:inline">Plantilla</span>
                </button>
              </>
            )}

            {/* Nuevo Producto - Solo Farmacia/Admin */}
            {puede.crear && (
              <button
                type="button"
                onClick={() => openModal()}
                className="cc-btn cc-btn-primary"
              >
                <FaPlus className="text-xs" />
                <span className="hidden sm:inline">Nuevo Producto</span>
              </button>
            )}
            
            {/* Botón de limpieza de inventario - SOLO SUPERUSUARIOS */}
            {permisos?.isSuperuser && (
              <LimpiarInventario onLimpiezaCompletada={() => fetchProductos()} />
            )}
          </div>
        }
        filters={
          <>
            <button
              type="button"
              onClick={toggleFiltersMenu}
              aria-expanded={showFiltersMenu}
              className="cc-filter-toggle"
            >
              <FaFilter className="text-[10px]" style={{ color: 'var(--color-primary)' }} />
              <span>Filtros</span>
              <FaChevronDown className={`text-[10px] transition-transform ${showFiltersMenu ? 'rotate-180' : ''}`} />
            </button>

            {!puede.verSoloActivos && (
              <select
                value={filters.estado}
                onChange={(e) => handleFilterChange('estado', e.target.value)}
                className="cc-filter-select"
              >
                <option value="">Estado ▾</option>
                <option value="activo">Activos</option>
                <option value="inactivo">Inactivos</option>
              </select>
            )}

            <select
              value={filters.stock}
              onChange={(e) => handleFilterChange('stock', e.target.value)}
              className="cc-filter-select"
            >
              {NIVELES_INVENTARIO.map((nivel) => (
                <option key={nivel.value} value={nivel.value}>
                  {nivel.value === '' ? 'Inventario ▾' : nivel.label}
                </option>
              ))}
            </select>

            <select
              value={filters.unidad}
              onChange={(e) => handleFilterChange('unidad', e.target.value)}
              className="cc-filter-select"
            >
              <option value="">Unidad ▾</option>
              {UNIDADES.map((unidad) => (
                <option key={unidad} value={unidad}>
                  {unidad}
                </option>
              ))}
            </select>

            <select
              value={filters.tipo_medicamento}
              onChange={(e) => handleFilterChange('tipo_medicamento', e.target.value)}
              className="cc-filter-select"
            >
              <option value="">Tipo Med. ▾</option>
              <option value="controlados">Controlados</option>
              <option value="no_controlados">No Controlados</option>
            </select>
          </>
        }
      />

      {/* Panel de filtros expandido */}
      {showFiltersMenu && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-7">
            <div className="lg:col-span-2">
              <label className="cc-filter-label">Búsqueda</label>
              <div className="cc-filter-input-wrap">
                <FaFilter className="text-gray-400 text-xs" />
                <input
                  type="text"
                  value={filters.search}
                  onChange={(e) => handleFilterChange('search', e.target.value)}
                  className="w-full bg-transparent text-sm focus:outline-none"
                  placeholder="Buscar por clave o descripción"
                />
              </div>
            </div>
            <div>
              <label className="cc-filter-label">Estado</label>
              <select
                value={puede.verSoloActivos ? 'activo' : filters.estado}
                disabled={puede.verSoloActivos}
                onChange={(e) => handleFilterChange('estado', e.target.value)}
                className="cc-filter-select-full"
              >
                <option value="">Todos</option>
                <option value="activo">Activos</option>
                <option value="inactivo">Inactivos</option>
              </select>
              {puede.verSoloActivos && <p className="mt-1 text-[11px] text-gray-400">Solo activos para su rol.</p>}
            </div>
            <div>
              <label className="cc-filter-label">Unidad</label>
              <select
                value={filters.unidad}
                onChange={(e) => handleFilterChange('unidad', e.target.value)}
                className="cc-filter-select-full"
              >
                <option value="">Todas</option>
                {UNIDADES.map((unidad) => (
                  <option key={unidad} value={unidad}>{unidad}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="cc-filter-label">Nivel Inventario</label>
              <select
                value={filters.stock}
                onChange={(e) => handleFilterChange('stock', e.target.value)}
                className="cc-filter-select-full"
              >
                {NIVELES_INVENTARIO.map((nivel) => (
                  <option key={nivel.value} value={nivel.value}>{nivel.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="cc-filter-label">Tipo Medicamento</label>
              <select
                value={filters.tipo_medicamento}
                onChange={(e) => handleFilterChange('tipo_medicamento', e.target.value)}
                className="cc-filter-select-full"
              >
                <option value="">Todos</option>
                <option value="controlados">Controlados</option>
                <option value="no_controlados">No Controlados</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                type="button"
                onClick={limpiarFiltros}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium text-gray-500 hover:bg-gray-50 transition"
              >
                Limpiar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ISS-FIX: Banner para usuarios CENTRO indicando que ven su inventario local */}
      {esCentroUser && centroNombre && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center gap-3">
          <div className="bg-blue-100 p-2 rounded-lg">
            <FaBoxOpen className="text-blue-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-blue-800">
              Inventario de: {centroNombre}
            </p>
            <p className="text-xs text-blue-600">
              Haz clic en el número de lotes para ver el detalle con fechas de caducidad
            </p>
          </div>
        </div>
      )}

      {/* Validación explícita de puede.ver para tabla y paginación */}
      {puede.ver ? (
        <>
          {renderTabla()}
          
          {/* ISS-FIX: Agregar margen y asegurar visibilidad de paginación */}
          <div className="mt-6">
            <Pagination
              page={currentPage}
              totalPages={totalPages}
              totalItems={totalProductos}
              pageSize={PAGE_SIZE}
              onPageChange={setCurrentPage}
            />
          </div>
        </>
      ) : (
        <div className="py-12 text-center bg-white rounded-lg shadow">
          <p className="text-gray-500">No tienes permisos para ver productos.</p>
        </div>
      )}


      {showModal && (

        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 modal-overlay-elevated p-4">

          <div className="w-full max-w-3xl rounded-2xl bg-white modal-elevated max-h-[90vh] overflow-y-auto">

            <div

              className="flex items-center justify-between rounded-t-2xl px-6 py-5 text-white modal-header-elevated sticky top-0 z-10"

            >

              <div className="flex items-center gap-3">

                <div className="modal-icon-badge">
                  <FaBoxOpen className="text-white text-lg" />
                </div>

                <div>

                <h2 className="text-lg font-bold tracking-wide">{editingProduct ? 'Editar producto' : 'Nuevo producto'}</h2>

                <p className="text-xs text-white/60">Complete los campos obligatorios (*)</p>

                </div>

              </div>

              <div className="flex items-center gap-3">

                <span className="px-2.5 py-1 rounded-lg bg-white/15 text-xs font-semibold backdrop-blur-sm">{editingProduct ? editingProduct.clave : 'Nuevo'}</span>

                <button

                  onClick={closeModal}

                  className="p-1.5 rounded-lg hover:bg-white/20 transition-colors"

                  title="Cerrar"

                >

                  <FaTimes className="text-lg" />

                </button>

              </div>

            </div>
            
            {/* ISS-002 FIX: Banner de advertencia cuando catálogos están en fallback */}
            {isFromFallback && (
              <div className="mx-6 mt-4 rounded-lg border border-amber-300 bg-amber-50 p-4">
                <div className="flex items-start gap-3">
                  <span className="text-xl">⚠️</span>
                  <div className="flex-1">
                    <h4 className="font-semibold text-amber-800">Catálogos no sincronizados</h4>
                    <p className="text-sm text-amber-700 mt-1">
                      No se pudieron cargar los catálogos del servidor. Las unidades de medida y categorías 
                      mostradas pueden no coincidir con el backend, lo que podría causar errores al guardar.
                    </p>
                    <div className="mt-3 flex gap-2">
                      <button
                        type="button"
                        onClick={() => refetchCatalogos(true)}
                        disabled={loadingCatalogos}
                        className="px-3 py-1.5 text-sm font-medium rounded-lg bg-amber-100 text-amber-800 hover:bg-amber-200 disabled:opacity-50"
                      >
                        {loadingCatalogos ? 'Sincronizando...' : '🔄 Reintentar sincronización'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setCatalogosFallbackAcknowledged(true)}
                        className="px-3 py-1.5 text-sm font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200"
                      >
                        Continuar de todos modos
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Banner de advertencia cuando el producto tiene lotes asociados */}
            {editingProduct && editingProduct.tiene_lotes && (
              <div className="mx-6 mt-4 rounded-lg border border-blue-300 bg-blue-50 p-4">
                <div className="flex items-start gap-3">
                  <span className="text-xl">🔒</span>
                  <div className="flex-1">
                    <h4 className="font-semibold text-blue-800">Campos protegidos por integridad de datos</h4>
                    <p className="text-sm text-blue-700 mt-1">
                      Este producto tiene lotes asociados. Para garantizar la integridad de los datos y la trazabilidad, 
                      los campos obligatorios (Clave, Nombre, Unidad de Medida, Categoría y Presentación) no pueden modificarse.
                    </p>
                  </div>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="px-6 py-6 space-y-5">

              {/* Clave y Descripción */}
              <div className="section-elevated">
                <div className="section-elevated-title">Datos principales</div>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">

                <div>

                  <label className="label-elevated">Clave <span className="text-red-500">*</span></label>

                  <input

                    type="text"

                    value={formData.clave}

                    onChange={(e) => setFormData({ ...formData, clave: e.target.value.toUpperCase() })}

                    maxLength={50}

                    placeholder="Ej: MED-001"

                    disabled={editingProduct?.tiene_lotes}

                    className={`input-elevated ${formErrors.clave ? '!border-red-500' : ''} ${editingProduct?.tiene_lotes ? '!bg-gray-100 !cursor-not-allowed !text-gray-600' : ''}`}

                  />

                  {editingProduct?.tiene_lotes && (
                    <p className="text-[11px] text-blue-600 mt-1.5">🔒 Campo protegido</p>
                  )}

                  {formErrors.clave && <p className="text-[11px] text-red-600">{formErrors.clave}</p>}

                </div>

                <div>

                  <label className="label-elevated">Nombre <span className="text-red-500">*</span></label>

                  <input

                    type="text"

                    value={formData.nombre}

                    onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}

                    maxLength={500}

                    placeholder="Ej: Paracetamol 500mg Tabletas"

                    disabled={editingProduct?.tiene_lotes}

                    className={`input-elevated ${formErrors.nombre ? '!border-red-500' : ''} ${editingProduct?.tiene_lotes ? '!bg-gray-100 !cursor-not-allowed !text-gray-600' : ''}`}

                  />

                  {editingProduct?.tiene_lotes && (
                    <p className="text-[11px] text-blue-600 mt-1.5">🔒 Campo protegido</p>
                  )}

                  {formErrors.nombre && <p className="text-[11px] text-red-600">{formErrors.nombre}</p>}

                </div>

                <div>

                  <label className="label-elevated">Nombre Comercial</label>

                  <input

                    type="text"

                    value={formData.nombre_comercial}

                    onChange={(e) => setFormData({ ...formData, nombre_comercial: e.target.value })}

                    maxLength={200}

                    placeholder="Ej: Tylenol, Aspirina, Tempra"

                    className="input-elevated"

                  />

                  <p className="text-[11px] text-gray-400 mt-1.5">Opcional - Nombre comercial del producto</p>

                </div>

              </div>
              </div>

              {/* Unidad y Stock Mínimo */}
              <div className="section-elevated">
                <div className="section-elevated-title">Clasificación y medida</div>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>

                  <label className="label-elevated">Unidad de Medida <span className="text-red-500">*</span></label>

                  <select

                    value={formData.unidad_medida}

                    onChange={(e) => setFormData({ ...formData, unidad_medida: e.target.value })}

                    disabled={editingProduct?.tiene_lotes}

                    className={`input-elevated ${formErrors.unidad_medida ? '!border-red-500' : ''} ${editingProduct?.tiene_lotes ? '!bg-gray-100 !cursor-not-allowed !text-gray-600' : ''}`}

                  >

                    {UNIDADES.map((unidad) => (

                      <option key={unidad} value={unidad}>                        {unidad}

                      </option>

                    ))}

                  </select>

                  {editingProduct?.tiene_lotes && (
                    <p className="text-[11px] text-blue-600 mt-1.5">🔒 Campo protegido</p>
                  )}

                  {formErrors.unidad_medida && <p className="text-[11px] text-red-600">{formErrors.unidad_medida}</p>}

                </div>

                <div>

                  <label className="label-elevated">Stock mínimo <span className="text-red-500">*</span></label>

                  <input

                    type="number"

                    min="0"

                    step="1"

                    value={formData.stock_minimo}

                    onChange={(e) => setFormData({ ...formData, stock_minimo: e.target.value })}

                    className={`input-elevated ${formErrors.stock_minimo ? '!border-red-500' : ''}`}

                  />

                  {formErrors.stock_minimo && <p className="text-[11px] text-red-600">{formErrors.stock_minimo}</p>}

                </div>
              </div>

              {/* Categoría y Presentación */}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 mt-4">
                <div>
                  <label className="label-elevated">Categoría <span className="text-red-500">*</span></label>
                  <select
                    value={formData.categoria}
                    onChange={(e) => setFormData({ ...formData, categoria: e.target.value })}
                    disabled={editingProduct?.tiene_lotes}
                    className={`input-elevated ${formErrors.categoria ? '!border-red-500' : ''} ${editingProduct?.tiene_lotes ? '!bg-gray-100 !cursor-not-allowed !text-gray-600' : ''}`}
                  >
                    {CATEGORIAS.map((cat) => (
                      <option key={cat} value={cat}>
                        {cat.charAt(0).toUpperCase() + cat.slice(1).replace('_', ' ')}
                      </option>
                    ))}
                  </select>
                  {editingProduct?.tiene_lotes && (
                    <p className="text-[11px] text-blue-600 mt-1.5">🔒 Campo protegido</p>
                  )}
                  {formErrors.categoria && <p className="text-[11px] text-red-600">{formErrors.categoria}</p>}
                </div>
                <div>
                  <label className="label-elevated">Presentación <span className="text-red-500">*</span></label>
                  <input
                    type="text"
                    value={formData.presentacion}
                    onChange={(e) => setFormData({ ...formData, presentacion: e.target.value })}
                    maxLength={200}
                    placeholder="Ej: CAJA CON 10 TABLETAS, FRASCO 120ML"
                    disabled={editingProduct?.tiene_lotes}
                    className={`input-elevated ${formErrors.presentacion ? '!border-red-500' : ''} ${editingProduct?.tiene_lotes ? '!bg-gray-100 !cursor-not-allowed !text-gray-600' : ''}`}
                  />
                  {editingProduct?.tiene_lotes && (
                    <p className="text-[11px] text-blue-600 mt-1.5">🔒 Campo protegido</p>
                  )}
                  {formErrors.presentacion && <p className="text-[11px] text-red-600">{formErrors.presentacion}</p>}
                </div>
              </div>

              {/* Medicamento Controlado - OBLIGATORIO */}
              <div className="mt-4">
                <label className="label-elevated">Medicamento Controlado <span className="text-red-500">*</span></label>
                <div className="flex items-center gap-4 mt-1">
                  <label className={`flex items-center gap-2 px-4 py-2 rounded-lg border cursor-pointer transition ${formData.es_controlado === true ? 'border-red-400 bg-red-50 text-red-700 font-semibold' : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50'} ${editingProduct?.tiene_movimientos && editingProduct?.es_controlado !== undefined && editingProduct?.es_controlado !== null ? '!cursor-not-allowed !opacity-60' : ''}`}>
                    <input
                      type="radio"
                      name="es_controlado"
                      checked={formData.es_controlado === true}
                      onChange={() => setFormData({ ...formData, es_controlado: true })}
                      disabled={editingProduct?.tiene_movimientos && editingProduct?.es_controlado !== undefined && editingProduct?.es_controlado !== null}
                      className="accent-red-600"
                    />
                    <span>Sí — Controlado</span>
                  </label>
                  <label className={`flex items-center gap-2 px-4 py-2 rounded-lg border cursor-pointer transition ${formData.es_controlado === false ? 'border-green-400 bg-green-50 text-green-700 font-semibold' : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50'} ${editingProduct?.tiene_movimientos && editingProduct?.es_controlado !== undefined && editingProduct?.es_controlado !== null ? '!cursor-not-allowed !opacity-60' : ''}`}>
                    <input
                      type="radio"
                      name="es_controlado"
                      checked={formData.es_controlado === false}
                      onChange={() => setFormData({ ...formData, es_controlado: false })}
                      disabled={editingProduct?.tiene_movimientos && editingProduct?.es_controlado !== undefined && editingProduct?.es_controlado !== null}
                      className="accent-green-600"
                    />
                    <span>No — No controlado</span>
                  </label>
                </div>
                {editingProduct?.tiene_movimientos && editingProduct?.es_controlado !== undefined && editingProduct?.es_controlado !== null && (
                  <p className="text-[11px] text-amber-600 mt-1.5">🔒 Este campo no se puede modificar porque el producto ya tiene movimientos registrados.</p>
                )}
                {formErrors.es_controlado && <p className="text-[11px] text-red-600 mt-1">{formErrors.es_controlado}</p>}
              </div>
              </div>

              {/* Datos Farmacéuticos (desplegable) */}
              <details className="section-elevated group">
                <summary className="cursor-pointer px-4 py-3 text-sm font-bold uppercase tracking-wide text-[var(--color-primary-hover)] hover:bg-gray-100/80 transition-colors flex items-center gap-2">
                  <span className="text-base">📋</span> Datos Farmacéuticos (opcional)
                </summary>
                <div className="space-y-4 px-4 pb-4 pt-2">
                  {/* Descripción (opcional) */}
                  <div>
                    <label className="label-elevated">Descripción adicional</label>
                    <input
                      type="text"
                      value={formData.descripcion}
                      onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                      maxLength={500}
                      placeholder="Descripción adicional del producto (opcional)"
                      className="input-elevated"
                    />
                  </div>
                  {/* Sustancia Activa y Concentración */}
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div>
                      <label className="label-elevated">Sustancia Activa</label>
                      <input
                        type="text"
                        value={formData.sustancia_activa}
                        onChange={(e) => setFormData({ ...formData, sustancia_activa: e.target.value })}
                        maxLength={200}
                        placeholder="Ej: Paracetamol"
                        className="input-elevated"
                      />
                    </div>
                    <div>
                      <label className="label-elevated">Concentración</label>
                      <input
                        type="text"
                        value={formData.concentracion}
                        onChange={(e) => setFormData({ ...formData, concentracion: e.target.value })}
                        maxLength={100}
                        placeholder="Ej: 500mg, 10ml"
                        className="input-elevated"
                      />
                    </div>
                  </div>
                  {/* Vía de Administración */}
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div>
                      <label className="label-elevated">Vía de Administración</label>
                      <select
                        value={formData.via_administracion}
                        onChange={(e) => setFormData({ ...formData, via_administracion: e.target.value })}
                        className="input-elevated"
                      >
                        <option value="">-- Seleccionar --</option>
                        {VIAS_ADMINISTRACION.map((via) => (
                          <option key={via} value={via}>
                            {via.charAt(0).toUpperCase() + via.slice(1)}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  {/* Toggles: Requiere Receta */}
                  <div className="flex flex-wrap gap-6 pt-1">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <div className={`toggle-switch ${formData.requiere_receta ? 'active' : ''}`} onClick={() => setFormData({ ...formData, requiere_receta: !formData.requiere_receta })}>
                        <div className="toggle-switch-knob"></div>
                      </div>
                      <span className="text-sm font-medium text-gray-700">Requiere Receta</span>
                    </label>
                  </div>
                </div>
              </details>

              {/* Toggle: Producto activo */}
              <div className="section-elevated">
                <div className="flex items-center justify-between px-1">
                  <span className="label-elevated !mb-0">Producto Activo</span>
                  <div className={`toggle-switch ${formData.activo ? 'active' : ''}`} onClick={() => setFormData({ ...formData, activo: !formData.activo })}>
                    <div className="toggle-switch-knob"></div>
                  </div>
                </div>
              </div>

              {/* Campo de imagen del producto */}
              <div className="section-elevated">
                <label className="label-elevated">Imagen del producto</label>
                <div className="mt-1 flex items-center gap-4">
                  {formData.imagenPreview && (
                    <div className="relative">
                      <img
                        src={formData.imagenPreview}
                        alt="Preview"
                        className="h-20 w-20 object-cover rounded-lg border-2 border-gray-200"
                      />
                      <button
                        type="button"
                        onClick={() => setFormData(prev => ({ ...prev, imagen: null, imagenPreview: null }))}
                        className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600 text-xs"
                        title="Quitar imagen"
                      >
                        ✕
                      </button>
                    </div>
                  )}
                  <label className="flex items-center gap-2 rounded-xl border-2 border-dashed border-primary px-4 py-3 bg-primary/5 hover:bg-primary/10 cursor-pointer transition-colors">
                    <FaFileUpload className="text-primary" />
                    <span className="text-sm text-primary font-medium">
                      {formData.imagenPreview ? 'Cambiar imagen' : 'Seleccionar imagen'}
                    </span>
                    <input
                      type="file"
                      accept="image/jpeg,image/jpg,image/png,image/gif,image/webp"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files[0];
                        if (file) {
                          if (file.size > 5 * 1024 * 1024) {
                            toast.error('La imagen no puede superar los 5MB');
                            return;
                          }
                          const reader = new FileReader();
                          reader.onloadend = () => {
                            setFormData(prev => ({
                              ...prev,
                              imagen: file,
                              imagenPreview: reader.result
                            }));
                          };
                          reader.readAsDataURL(file);
                        }
                      }}
                      disabled={savingProduct}
                    />
                  </label>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Formatos: JPG, PNG, GIF, WebP • Máximo 5MB
                </p>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-gray-100">

                <button 
                  type="button" 
                  onClick={closeModal} 
                  disabled={savingProduct}
                  className="btn-elevated-cancel disabled:opacity-50 disabled:cursor-not-allowed"
                >

                  Cancelar

                </button>

                <button

                  type="submit"
                  disabled={savingProduct}

                  className="btn-elevated-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"

                >
                  {savingProduct && (
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                  )}
                  {savingProduct ? 'Guardando...' : (editingProduct ? 'Actualizar' : 'Guardar')}

                </button>

              </div>

            </form>

          </div>

        </div>

      )}



      {auditoriaVisible && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 modal-overlay-elevated p-4" onClick={(e) => e.target === e.currentTarget && cerrarAuditoria()}>
          <div className="w-full max-w-2xl bg-white rounded-2xl modal-elevated flex flex-col max-h-[90vh]" style={{ boxShadow: '0 10px 30px rgba(0,0,0,0.08), 0 25px 50px -12px rgba(147,32,67,0.2)' }}>

            {/* Cabecera moderna */}
            <div className="flex items-center justify-between gap-4 px-6 py-5 rounded-t-2xl shrink-0 text-white" style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #7B1D3A) 100%)' }}>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center shrink-0 shadow-inner">
                  <FaHistory className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-xl font-bold tracking-wide leading-tight">Historial de auditoría</h3>
                  <p className="text-sm text-white/75 mt-0.5 uppercase tracking-wider font-medium">
                    {auditoriaData?.producto?.nombre || 'Producto'}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={cerrarAuditoria}
                className="w-8 h-8 flex items-center justify-center rounded-full bg-white/15 hover:bg-white/30 transition-colors shrink-0"
                title="Cerrar"
              >
                <FaTimes className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Contenido */}
            <div className="overflow-y-auto px-6 py-6 flex-1" style={{ background: '#f8f9fb' }}>
              {auditoriaLoading ? (
                <div className="flex flex-col items-center justify-center py-12 gap-3 text-gray-400">
                  <div className="animate-spin rounded-full h-8 w-8 border-2 border-[#632842] border-t-transparent" />
                  <p className="text-sm">Cargando historial...</p>
                </div>
              ) : auditoriaData?.historial?.length ? (
                <div className="relative">
                  {/* Línea de tiempo vertical */}
                  <span className="absolute left-[15px] top-5 bottom-5 w-0.5 bg-gray-200 rounded-full" />

                  <div className="space-y-5">
                    {auditoriaData.historial.map((log, idx) => {
                      const tipo = (log.accion_tipo || log.accion || 'otro').toLowerCase();
                      const est = ACCION_ESTILOS[tipo] || ACCION_ESTILOS.otro;
                      const diff = calcularDiffAudit(log.datos_anteriores, log.datos_nuevos);
                      const esCreacion = tipo === 'crear' || tipo === 'importar';
                      const camposIniciales = esCreacion && log.datos_nuevos
                        ? Object.entries(log.datos_nuevos).filter(([k, v]) =>
                            v !== null && v !== undefined && v !== '' &&
                            !['id','created_at','updated_at','timestamp'].includes(k))
                        : [];
                      const numEvento = auditoriaData.historial.length - idx;

                      return (
                        <div key={log.id || idx} className="relative flex gap-4 items-start">
                          {/* Círculo numerado en la línea */}
                          <div className={`relative z-10 w-8 h-8 rounded-full flex items-center justify-center shrink-0 border-2 border-white shadow-md ${est.punto}`}>
                            <span className="text-white text-xs font-bold">{numEvento}</span>
                          </div>

                          {/* Tarjeta del evento */}
                          <div className="flex-1 bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden" style={{ boxShadow: '0 1px 4px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04)' }}>
                            {/* Cabecera de la tarjeta */}
                            <div className="flex items-center justify-between gap-2 px-5 pt-4 pb-3 border-b border-gray-50">
                              <div className="flex items-center gap-2">
                                <span className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white shrink-0 ${est.punto}`}>{numEvento}</span>
                                <span className="font-semibold text-gray-800 text-sm">
                                  {log.accion_display || log.accion || 'Cambio'}
                                </span>
                              </div>
                              <span className="text-xs text-gray-400 whitespace-nowrap">{formatFecha(log.fecha)}</span>
                            </div>

                            {/* Usuario */}
                            <div className="flex items-center gap-2 px-5 py-2.5">
                              <span className="w-6 h-6 rounded-full bg-[#9F2241]/10 text-[#9F2241] flex items-center justify-center font-bold text-[11px] shrink-0">U</span>
                              <span className="text-sm font-medium text-gray-600">{log.usuario_nombre || 'Sistema'}</span>
                            </div>

                            {/* Cambios realizados (actualizaciones) */}
                            {diff.length > 0 && (
                              <div className="px-5 pb-4">
                                <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-2">Cambios realizados</p>
                                <div className="divide-y divide-gray-50">
                                  {diff.map(({ campo, antes, despues }) => (
                                    <div key={campo} className="flex items-center justify-between py-2 gap-3">
                                      <span className="text-sm text-gray-500 flex-1 min-w-0 truncate">
                                        {LABELS_CAMPO[campo] || campo.replace(/_/g, ' ')}
                                      </span>
                                      <div className="flex items-center gap-1.5 shrink-0">
                                        {antes !== undefined && antes !== null && antes !== '' && (
                                          <span className="inline-flex items-center text-xs bg-red-50 text-red-600 border border-red-100 px-2 py-0.5 rounded-full">
                                            − {formatearValorAudit(campo, antes)}
                                          </span>
                                        )}
                                        {antes !== undefined && antes !== null && antes !== '' && (
                                          <span className="text-gray-300 text-xs">→</span>
                                        )}
                                        <span className="inline-flex items-center text-xs bg-emerald-50 text-emerald-700 border border-emerald-100 px-2 py-0.5 rounded-full font-medium">
                                          + {formatearValorAudit(campo, despues)}
                                        </span>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Campos del registro inicial (creación) */}
                            {esCreacion && camposIniciales.length > 0 && (
                              <div className="px-5 pb-4">
                                <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-2">Cambios realizados</p>
                                <div className="divide-y divide-gray-50">
                                  {camposIniciales.map(([campo, valor]) => (
                                    <div key={campo} className="flex items-center justify-between py-2 gap-3">
                                      <span className="text-sm text-gray-500 flex-1 min-w-0 truncate">
                                        {LABELS_CAMPO[campo] || campo.replace(/_/g, ' ')}
                                      </span>
                                      <span className="inline-flex items-center text-xs bg-emerald-50 text-emerald-700 border border-emerald-100 px-2 py-0.5 rounded-full font-medium shrink-0">
                                        + {formatearValorAudit(campo, valor)}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Sin detalles disponibles */}
                            {diff.length === 0 && !esCreacion && (
                              <p className="text-xs text-gray-400 italic px-5 pb-4">Sin detalles adicionales registrados.</p>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-16 gap-3 text-gray-400">
                  <FaHistory className="w-10 h-10 opacity-30" />
                  <p className="text-sm">Sin cambios registrados para este producto.</p>
                </div>
              )}
            </div>

            {/* Pie */}
            <div className="shrink-0 px-6 py-4 border-t border-gray-100 bg-white rounded-b-2xl flex items-center justify-between">
              <span className="text-sm text-gray-400">
                {auditoriaData?.historial?.length
                  ? `${auditoriaData.historial.length} registro${auditoriaData.historial.length !== 1 ? 's' : ''} en el historial`
                  : ''}
              </span>
              <button
                type="button"
                onClick={cerrarAuditoria}
                className="px-5 py-2 bg-gray-800 hover:bg-gray-700 text-white text-sm font-semibold rounded-xl transition-colors shadow-sm"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Lotes del Producto */}
      {lotesModalVisible && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4" onClick={(e) => e.target === e.currentTarget && cerrarLotesModal()}>
          <div className="w-full max-w-3xl bg-white rounded-2xl shadow-2xl max-h-[85vh] overflow-hidden" style={{ animation: 'modalSlideIn 0.25s ease-out' }}>
            {/* Header degradado */}
            <div className="relative px-6 py-5" style={{ background: 'linear-gradient(135deg, var(--color-primary, #9F2241) 0%, var(--color-primary-hover, #6B1839) 100%)' }}>
              <button
                onClick={cerrarLotesModal}
                className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center rounded-lg bg-white/10 hover:bg-white/25 text-white transition-all"
              >
                <FaTimes size={14} />
              </button>
              <div className="flex items-start gap-4 pr-10">
                <div className="w-11 h-11 rounded-xl bg-white/15 backdrop-blur-sm flex items-center justify-center shrink-0">
                  <FaLayerGroup className="text-white text-lg" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-xl font-bold text-white tracking-wide">Lotes del Producto</h3>
                  <p className="text-sm text-white/75 mt-0.5 truncate">
                    {lotesModalData?.producto?.clave} &bull; {lotesModalData?.producto?.nombre}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2.5 mt-4">
                <span className="inline-flex items-center gap-1.5 bg-white/15 backdrop-blur-sm px-3.5 py-1.5 rounded-full text-sm font-semibold text-white">
                  <FaLayerGroup size={11} />
                  {lotesModalData?.total_lotes || lotesModalData?.lotes?.length || 0} Lote{(lotesModalData?.total_lotes || lotesModalData?.lotes?.length || 0) !== 1 ? 's' : ''}
                </span>
                <span className="inline-flex items-center gap-1.5 bg-white/15 backdrop-blur-sm px-3.5 py-1.5 rounded-full text-sm font-semibold text-white">
                  <FaBoxOpen size={11} />
                  Stock Total: {lotesModalData?.total_stock || 0}
                </span>
              </div>
            </div>

            {/* Contenido */}
            <div className="overflow-y-auto" style={{ maxHeight: 'calc(85vh - 200px)' }}>
              {lotesModalLoading ? (
                <div className="flex flex-col items-center justify-center py-20">
                  <div className="w-12 h-12 rounded-2xl bg-gray-100 flex items-center justify-center mb-3">
                    <div className="animate-spin rounded-full h-6 w-6 border-[3px] border-gray-200 border-t-[var(--color-primary)]"></div>
                  </div>
                  <span className="text-sm font-medium text-gray-400">Cargando lotes...</span>
                </div>
              ) : lotesModalData?.lotes?.length ? (
                <div className="p-5 space-y-3">
                  {/* Tabla desktop */}
                  <div className="hidden md:block rounded-xl border border-gray-200/80 shadow-sm overflow-hidden">
                    <table className="w-full">
                      <thead>
                        <tr className="bg-gray-50/80">
                          <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-gray-400">Lote</th>
                          <th className="px-4 py-3 text-center text-[10px] font-bold uppercase tracking-wider text-gray-400">Cantidad</th>
                          <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-gray-400">Caducidad</th>
                          <th className="px-4 py-3 text-center text-[10px] font-bold uppercase tracking-wider text-gray-400">Días Rest.</th>
                          <th className="px-4 py-3 text-center text-[10px] font-bold uppercase tracking-wider text-gray-400">Estado</th>
                          <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-gray-400">Ubicación</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {lotesModalData.lotes.map((lote) => {
                          const semaforoConfig = {
                            vencido: { bg: 'bg-red-50', text: 'text-red-600', label: 'VENCIDO', dot: 'bg-red-500' },
                            critico: { bg: 'bg-orange-50', text: 'text-orange-600', label: 'CRÍTICO', dot: 'bg-orange-500' },
                            proximo: { bg: 'bg-yellow-50', text: 'text-yellow-600', label: 'PRÓXIMO', dot: 'bg-yellow-500' },
                            normal: { bg: 'bg-emerald-50', text: 'text-emerald-600', label: 'OK', dot: 'bg-emerald-500' },
                            sin_fecha: { bg: 'bg-gray-50', text: 'text-gray-500', label: 'S/F', dot: 'bg-gray-400' },
                          };
                          const semaforo = semaforoConfig[lote.alerta_caducidad] || semaforoConfig.normal;
                          return (
                            <tr key={lote.id} className={`transition-colors hover:bg-gray-50/60 ${lote.alerta_caducidad === 'vencido' ? 'bg-red-50/30' : ''}`}>
                              <td className="px-4 py-3.5">
                                <span className="inline-flex items-center font-mono text-sm font-semibold text-gray-800 bg-gray-100 border border-gray-200 px-2.5 py-0.5 rounded-md">{lote.numero_lote}</span>
                              </td>
                              <td className="px-4 py-3.5 text-center">
                                <span className="text-[15px] font-bold text-gray-900">{lote.cantidad_actual}</span>
                              </td>
                              <td className="px-4 py-3.5">
                                <div className="flex items-center gap-1.5 text-sm text-gray-600">
                                  <FaCalendarAlt className="text-gray-300 shrink-0" size={11} />
                                  {lote.fecha_caducidad
                                    ? new Date(lote.fecha_caducidad).toLocaleDateString('es-MX', { year: 'numeric', month: 'short', day: 'numeric' })
                                    : 'Sin fecha'}
                                </div>
                              </td>
                              <td className="px-4 py-3.5 text-center">
                                {lote.dias_para_caducar !== null ? (
                                  <span className={`text-sm font-bold ${lote.dias_para_caducar < 0 ? 'text-red-600' : lote.dias_para_caducar <= 30 ? 'text-orange-500' : lote.dias_para_caducar <= 90 ? 'text-yellow-500' : 'text-emerald-600'}`}>
                                    {lote.dias_para_caducar < 0 ? `${Math.abs(lote.dias_para_caducar)} vencido` : `${lote.dias_para_caducar} días`}
                                  </span>
                                ) : <span className="text-gray-300">—</span>}
                              </td>
                              <td className="px-4 py-3.5 text-center">
                                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold ${semaforo.bg} ${semaforo.text}`}>
                                  <span className={`w-1.5 h-1.5 rounded-full ${semaforo.dot}`}></span>
                                  {semaforo.label}
                                </span>
                              </td>
                              <td className="px-4 py-3.5 text-sm text-gray-500">
                                <span className="truncate block max-w-[180px]" title={lote.centro_nombre || 'Almacén Central'}>
                                  {lote.centro_nombre || 'Almacén Central'}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  {/* Cards mobile */}
                  <div className="md:hidden space-y-2.5">
                    {lotesModalData.lotes.map((lote) => {
                      const semaforoConfig = {
                        vencido: { bg: 'bg-red-50', text: 'text-red-600', label: 'VENCIDO', dot: 'bg-red-500' },
                        critico: { bg: 'bg-orange-50', text: 'text-orange-600', label: 'CRÍTICO', dot: 'bg-orange-500' },
                        proximo: { bg: 'bg-yellow-50', text: 'text-yellow-600', label: 'PRÓXIMO', dot: 'bg-yellow-500' },
                        normal: { bg: 'bg-emerald-50', text: 'text-emerald-600', label: 'OK', dot: 'bg-emerald-500' },
                        sin_fecha: { bg: 'bg-gray-50', text: 'text-gray-500', label: 'S/F', dot: 'bg-gray-400' },
                      };
                      const semaforo = semaforoConfig[lote.alerta_caducidad] || semaforoConfig.normal;
                      return (
                        <div
                          key={lote.id}
                          className={`rounded-xl border p-4 ${lote.alerta_caducidad === 'vencido' ? 'border-red-200 bg-red-50/20' : lote.alerta_caducidad === 'critico' ? 'border-orange-200 bg-orange-50/20' : 'border-gray-200 bg-white'}`}
                        >
                          <div className="flex items-center justify-between mb-3">
                            <span className="font-mono font-bold text-sm bg-gray-100 border border-gray-200 px-2.5 py-0.5 rounded-md text-gray-800">{lote.numero_lote}</span>
                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold ${semaforo.bg} ${semaforo.text}`}>
                              <span className={`w-1.5 h-1.5 rounded-full ${semaforo.dot}`}></span>
                              {semaforo.label}
                            </span>
                          </div>
                          <div className="grid grid-cols-3 gap-2 text-center">
                            <div className="bg-gray-50 rounded-lg p-2.5">
                              <p className="text-[10px] font-semibold text-gray-400 uppercase">Cantidad</p>
                              <p className="text-base font-bold text-gray-900 mt-0.5">{lote.cantidad_actual}</p>
                            </div>
                            <div className="bg-gray-50 rounded-lg p-2.5">
                              <p className="text-[10px] font-semibold text-gray-400 uppercase">Caduca</p>
                              <p className="text-xs font-semibold text-gray-700 mt-1">
                                {lote.fecha_caducidad
                                  ? new Date(lote.fecha_caducidad).toLocaleDateString('es-MX', { month: 'short', day: 'numeric', year: '2-digit' })
                                  : 'S/F'}
                              </p>
                            </div>
                            <div className="bg-gray-50 rounded-lg p-2.5">
                              <p className="text-[10px] font-semibold text-gray-400 uppercase">Días</p>
                              <p className={`text-xs font-bold mt-1 ${lote.dias_para_caducar !== null ? (lote.dias_para_caducar < 0 ? 'text-red-600' : lote.dias_para_caducar <= 30 ? 'text-orange-500' : lote.dias_para_caducar <= 90 ? 'text-yellow-500' : 'text-emerald-600') : 'text-gray-400'}`}>
                                {lote.dias_para_caducar !== null ? (lote.dias_para_caducar < 0 ? `${Math.abs(lote.dias_para_caducar)} venc.` : lote.dias_para_caducar) : '—'}
                              </p>
                            </div>
                          </div>
                          <p className="text-xs text-gray-400 mt-2.5 truncate">
                            📍 {lote.centro_nombre || 'Almacén Central'}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="py-20 text-center">
                  <div className="w-14 h-14 rounded-2xl bg-gray-50 flex items-center justify-center mx-auto mb-4">
                    <FaBoxOpen className="text-2xl text-gray-300" />
                  </div>
                  <p className="text-sm font-semibold text-gray-500">Sin lotes disponibles</p>
                  <p className="text-xs text-gray-400 mt-1">Este producto no tiene lotes con stock.</p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 bg-gray-50/50 border-t border-gray-100 flex justify-between items-center">
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-gray-400 font-medium">
                <span className="inline-flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span>+90 días</span>
                <span className="inline-flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-yellow-500 inline-block"></span>31-90 días</span>
                <span className="inline-flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-orange-500 inline-block"></span>1-30 días</span>
                <span className="inline-flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-red-500 inline-block"></span>Vencido</span>
              </div>
              <button
                type="button"
                onClick={cerrarLotesModal}
                className="px-5 py-2 rounded-xl text-sm font-semibold border border-gray-200 text-gray-600 hover:bg-gray-100 hover:border-gray-300 transition-all shadow-sm"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Importar - Usando ImportadorModerno (homologado con Lotes) */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="relative w-full max-w-4xl my-8">
            <ImportadorModerno
              tipo="productos"
              onCerrar={() => setShowImportModal(false)}
              onImportar={async (formData) => {
                setImportLoading(true);
                try {
                  const response = await productosAPI.importar(formData);
                  // Recargar productos después de importar
                  await fetchProductos();
                  return response;
                } finally {
                  setImportLoading(false);
                }
              }}
              onDescargarPlantilla={handleDescargarPlantilla}
              permiteImportar={puede.importar}
            />
          </div>
        </div>
      )}

      {/* ISS-SEC: Modal de confirmación en 2 pasos */}
      <TwoStepConfirmModal
        open={confirmState.isOpen}
        title={confirmState.title}
        message={confirmState.message}
        warnings={confirmState.warnings}
        confirmText={confirmState.confirmText}
        cancelText={confirmState.cancelText}
        tone={confirmState.tone}
        confirmPhrase={confirmState.confirmPhrase}
        itemInfo={confirmState.itemInfo}
        loading={confirmState.loading}
        onConfirm={executeWithConfirmation}
        onCancel={cancelConfirmation}
      />

    </div>

  );

};



export default Productos;



















































