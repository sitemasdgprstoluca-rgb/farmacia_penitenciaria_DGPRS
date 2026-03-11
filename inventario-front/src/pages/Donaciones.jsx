import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { donacionesAPI, productosDonacionAPI, centrosAPI, lotesAPI, salidasDonacionesAPI, detallesDonacionAPI, abrirPdfEnNavegador } from '../services/api';
import { toast } from 'react-hot-toast';
import {
  FaPlus,
  FaEdit,
  FaTrash,
  FaEye,
  FaCheck,
  FaCheckCircle,
  FaClock,
  FaFilter,
  FaGift,
  FaChevronDown,
  FaTimes,
  FaSpinner,
  FaBuilding,
  FaUser,
  FaCalendar,
  FaBox,
  FaSearch,
  FaHandHoldingMedical,
  FaHistory,
  FaWarehouse,
  FaClipboardList,
  FaClipboardCheck,
  FaArrowRight,
  FaExclamationTriangle,
  FaFileExport,
  FaFileImport,
  FaDownload,
  FaUpload,
  FaShoppingCart,
  FaTable,
  FaFilePdf,
  FaFileExcel,
  FaInfoCircle,
} from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import { COLORS } from '../constants/theme';
import Pagination from '../components/Pagination';
import { usePermissions } from '../hooks/usePermissions';
import ConfirmModal from '../components/ConfirmModal';
import TwoStepConfirmModal from '../components/TwoStepConfirmModal';
import { esFarmaciaAdmin as checkEsFarmaciaAdmin } from '../utils/roles';
import SalidaMasivaDonaciones from '../components/SalidaMasivaDonaciones';
import useEscapeToClose from '../hooks/useEscapeToClose';

const PAGE_SIZE = 25;

// ISS-DB-ALIGN: Estados alineados con BD Supabase
// BD permite: pendiente, recibida, procesada, rechazada
const ESTADOS_DONACION = {
  pendiente: { label: 'Pendiente', color: 'bg-yellow-100 text-yellow-800', icon: '⏳' },
  recibida: { label: 'Recibida', color: 'bg-blue-100 text-blue-800', icon: '📦' },
  procesada: { label: 'Procesada', color: 'bg-green-100 text-green-800', icon: '✅' },
  rechazada: { label: 'Rechazada', color: 'bg-red-100 text-red-800', icon: '❌' },
};

// ISS-DB-ALIGN: Tipos de donante alineados con BD Supabase (core/models.py TIPOS_DONANTE)
const TIPOS_DONANTE = [
  { value: 'empresa', label: 'Empresa' },
  { value: 'gobierno', label: 'Gobierno' },
  { value: 'ong', label: 'ONG' },
  { value: 'particular', label: 'Particular' },
  { value: 'otro', label: 'Otro' },
];

// ISS-DB-ALIGN: Estados de producto alineados con BD Supabase
// BD permite: bueno, regular, malo
const ESTADOS_PRODUCTO = [
  { value: 'bueno', label: 'Bueno' },
  { value: 'regular', label: 'Regular' },
  { value: 'malo', label: 'Malo' },
];

// Semáforo de caducidad para productos en inventario de donaciones
const getSemaforoCaducidad = (fechaCaducidad) => {
  if (!fechaCaducidad) return { estado: 'sin_fecha', clase: 'bg-gray-100 text-gray-600', label: 'Sin fecha', icono: '❓' };
  
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  const fecha = new Date(fechaCaducidad);
  fecha.setHours(0, 0, 0, 0);
  
  const diasRestantes = Math.ceil((fecha - hoy) / (1000 * 60 * 60 * 24));
  
  if (diasRestantes < 0) {
    return { estado: 'vencido', clase: 'bg-red-100 text-red-800', label: 'VENCIDO', icono: '🔴', dias: diasRestantes };
  } else if (diasRestantes <= 30) {
    return { estado: 'critico', clase: 'bg-orange-100 text-orange-800', label: 'CRÍTICO', icono: '🟠', dias: diasRestantes };
  } else if (diasRestantes <= 90) {
    return { estado: 'proximo', clase: 'bg-yellow-100 text-yellow-800', label: 'PRÓXIMO', icono: '🟡', dias: diasRestantes };
  } else {
    return { estado: 'normal', clase: 'bg-green-100 text-green-800', label: 'VIGENTE', icono: '🟢', dias: diasRestantes };
  }
};

const Donaciones = () => {
  const { getRolPrincipal, permisos, user, verificarPermiso } = usePermissions();
  const rolPrincipal = getRolPrincipal();
  // FRONT-006 FIX: Usar lógica centralizada de roles
  const esFarmaciaAdmin = checkEsFarmaciaAdmin(user);
  
  // Verificar permiso granular de donaciones (perm_donaciones en BD → verDonaciones en frontend)
  const tienePermisoDonaciones = verificarPermiso('verDonaciones');

  // Permisos - Crear/Editar/Procesar solo para ADMIN y FARMACIA
  // Ver: cualquier rol con permiso de donaciones
  const puede = {
    crear: esFarmaciaAdmin && tienePermisoDonaciones,
    editar: esFarmaciaAdmin && tienePermisoDonaciones,
    eliminar: esFarmaciaAdmin && tienePermisoDonaciones,
    procesar: esFarmaciaAdmin && tienePermisoDonaciones,
    ver: tienePermisoDonaciones,
  };

  // Estados
  const [donaciones, setDonaciones] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [showDetalleModal, setShowDetalleModal] = useState(false);
  const [editingDonacion, setEditingDonacion] = useState(null);
  const [viewingDonacion, setViewingDonacion] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [confirmProcesar, setConfirmProcesar] = useState(null);
  const [confirmRecibir, setConfirmRecibir] = useState(null);
  const [confirmRechazar, setConfirmRechazar] = useState(null);
  const [confirmProcesarTodas, setConfirmProcesarTodas] = useState(false);
  const [procesandoTodas, setProcesandoTodas] = useState(false);
  const [motivoRechazo, setMotivoRechazo] = useState('');

  // Salidas de donaciones (entregas a centros)
  const [showSalidaModal, setShowSalidaModal] = useState(false);
  const [salidaDetalle, setSalidaDetalle] = useState(null);
  const [salidaForm, setSalidaForm] = useState({
    cantidad: '',
    centro_destino: '',  // ID del centro destino (obligatorio)
    motivo: '',
    notas: '',
  });
  const [showHistorialModal, setShowHistorialModal] = useState(false);
  const [historialSalidas, setHistorialSalidas] = useState([]);
  const [loadingSalidas, setLoadingSalidas] = useState(false);

  // Sistema de Tabs: donaciones | catalogo | inventario | entregas
  const [activeTab, setActiveTab] = useState('donaciones');
  
  // Catálogo de Productos de Donaciones (independiente)
  const [loadingCatalogo, setLoadingCatalogo] = useState(false);
  const [searchCatalogo, setSearchCatalogo] = useState('');
  const [showCatalogoModal, setShowCatalogoModal] = useState(false);
  const [editingProductoDonacion, setEditingProductoDonacion] = useState(null);
  const [confirmDeleteProducto, setConfirmDeleteProducto] = useState(null);
  const [catalogoForm, setCatalogoForm] = useState({
    clave: '',
    nombre: '',
    descripcion: '',
    unidad_medida: 'PIEZA',
    presentacion: '',
    activo: true,
    notas: '',
  });
  
  // Inventario de Donaciones (productos con stock disponible)
  const [inventarioDonaciones, setInventarioDonaciones] = useState([]);
  const [loadingInventario, setLoadingInventario] = useState(false);
  const [inventarioPage, setInventarioPage] = useState(1);
  const [inventarioTotalPages, setInventarioTotalPages] = useState(1);
  const [searchInventario, setSearchInventario] = useState('');
  
  // Filtros de inventario de donaciones
  const [filtroEstadoProducto, setFiltroEstadoProducto] = useState('');
  const [filtroCaducidadInv, setFiltroCaducidadInv] = useState(''); // '', 'vencido', 'critico', 'proximo', 'normal'
  const [filtroDisponibilidad, setFiltroDisponibilidad] = useState('constock'); // 'todos', 'constock', 'agotado'
  const [showFiltrosInventario, setShowFiltrosInventario] = useState(false);
  
  // Historial de Entregas (todas las salidas)
  const [todasEntregas, setTodasEntregas] = useState([]);
  const [loadingEntregas, setLoadingEntregas] = useState(false);
  const [entregasPage, setEntregasPage] = useState(1);
  const [entregasTotalPages, setEntregasTotalPages] = useState(1);
  const [searchEntregas, setSearchEntregas] = useState('');
  const [filtroCentroEntregas, setFiltroCentroEntregas] = useState(''); // Filtro por centro destino
  const [filtroFechaDesdeEntregas, setFiltroFechaDesdeEntregas] = useState(''); // Filtro fecha desde
  const [filtroFechaHastaEntregas, setFiltroFechaHastaEntregas] = useState(''); // Filtro fecha hasta
  
  // Vista agrupada de entregas (para salidas masivas)
  const [gruposExpandidos, setGruposExpandidos] = useState(new Set());
  
  // Exportación de entregas (solo export, sin import)
  const [exportingEntregas, setExportingEntregas] = useState(false);
  
  // Importación/Exportación de donaciones
  const [exportingDonaciones, setExportingDonaciones] = useState(false);
  const [importingDonaciones, setImportingDonaciones] = useState(false);
  const donacionFileInputRef = useRef(null); // Para donaciones
  
  // Importación/Exportación del catálogo de productos de donación
  const [exportingCatalogo, setExportingCatalogo] = useState(false);
  const [importingCatalogo, setImportingCatalogo] = useState(false);
  const catalogoFileInputRef = useRef(null); // Para catálogo de productos
  const [importResultModal, setImportResultModal] = useState(null); // Modal de resultados de importación (catálogo y donaciones)
  const [importDonacionResultModal, setImportDonacionResultModal] = useState(null); // Modal específico para resultados de importación de donaciones
  
  // Exportación del inventario de donaciones
  const [exportingInventario, setExportingInventario] = useState(false);
  
  // Modal de Entrega Masiva de Donaciones
  const [showSalidaMasiva, setShowSalidaMasiva] = useState(false);
  
  // Número de donación auto-generado
  const [siguienteNumero, setSiguienteNumero] = useState('');
  
  // Modal de creación rápida de producto
  const [showQuickProductModal, setShowQuickProductModal] = useState(false);
  const [quickProductForm, setQuickProductForm] = useState({
    clave: '',
    nombre: '',
    descripcion: '',
    unidad_medida: 'PIEZA',
    presentacion: '',
  });
  
  // Modal de carga masiva de productos
  const [showBulkAddModal, setShowBulkAddModal] = useState(false);
  const [bulkText, setBulkText] = useState('');
  const [bulkProducts, setBulkProducts] = useState([]);
  
  // Confirmación de finalización de entrega
  const [confirmFinalizarEntrega, setConfirmFinalizarEntrega] = useState(null);
  
  // Confirmación de finalización de GRUPO de entregas (salida masiva)
  const [confirmFinalizarGrupo, setConfirmFinalizarGrupo] = useState(null);
  const [finalizandoGrupo, setFinalizandoGrupo] = useState(false);
  
  // Confirmación de eliminación de entrega pendiente
  const [confirmEliminarEntrega, setConfirmEliminarEntrega] = useState(null);
  
  // Modal para ver detalles de una entrega
  const [detalleEntregaModal, setDetalleEntregaModal] = useState(null);
  
  // Estadísticas del almacén de donaciones
  const [estadisticas, setEstadisticas] = useState({
    totalProductos: 0,
    totalUnidades: 0,
    productosAgotados: 0,
    productosPorCaducar: 0,
  });

  // ESC para cerrar modales
  useEscapeToClose({
    isOpen: showModal,
    onClose: () => setShowModal(false),
    modalId: 'donaciones-form-modal',
    disabled: loading
  });

  useEscapeToClose({
    isOpen: showDetalleModal,
    onClose: () => setShowDetalleModal(false),
    modalId: 'donaciones-detalle-modal',
    disabled: false
  });

  useEscapeToClose({
    isOpen: showSalidaModal,
    onClose: () => setShowSalidaModal(false),
    modalId: 'donaciones-salida-modal',
    disabled: false
  });

  useEscapeToClose({
    isOpen: showHistorialModal,
    onClose: () => setShowHistorialModal(false),
    modalId: 'donaciones-historial-modal',
    disabled: loadingSalidas
  });

  useEscapeToClose({
    isOpen: showCatalogoModal,
    onClose: () => setShowCatalogoModal(false),
    modalId: 'donaciones-catalogo-modal',
    disabled: loadingCatalogo
  });

  useEscapeToClose({
    isOpen: !!importResultModal,
    onClose: () => setImportResultModal(null),
    modalId: 'donaciones-import-result-modal',
    disabled: false
  });

  useEscapeToClose({
    isOpen: !!importDonacionResultModal,
    onClose: () => setImportDonacionResultModal(null),
    modalId: 'donaciones-import-donacion-result-modal',
    disabled: false
  });

  useEscapeToClose({
    isOpen: showSalidaMasiva,
    onClose: () => setShowSalidaMasiva(false),
    modalId: 'donaciones-salida-masiva-modal',
    disabled: false
  });

  useEscapeToClose({
    isOpen: showQuickProductModal,
    onClose: () => setShowQuickProductModal(false),
    modalId: 'donaciones-quick-product-modal',
    disabled: false
  });

  useEscapeToClose({
    isOpen: showBulkAddModal,
    onClose: () => setShowBulkAddModal(false),
    modalId: 'donaciones-bulk-add-modal',
    disabled: false
  });

  useEscapeToClose({
    isOpen: !!detalleEntregaModal,
    onClose: () => setDetalleEntregaModal(null),
    modalId: 'donaciones-detalle-entrega-modal',
    disabled: false
  });


  // Paginación
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalDonaciones, setTotalDonaciones] = useState(0);

  // Filtros
  const [showFiltersMenu, setShowFiltersMenu] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('');
  const [filtroTipoDonante, setFiltroTipoDonante] = useState('');
  const [filtroCentro, setFiltroCentro] = useState('');
  const [filtroFechaDesde, setFiltroFechaDesde] = useState('');
  const [filtroFechaHasta, setFiltroFechaHasta] = useState('');

  // Catálogos
  const [productosDonacion, setProductosDonacion] = useState([]);  // Catálogo independiente de donaciones
  const [centros, setCentros] = useState([]);
  const [lotes, setLotes] = useState([]);

  // Formulario - ISS-DB-ALIGN: donante_tipo default 'empresa' (primer valor del array)
  const [formData, setFormData] = useState({
    numero: '',
    donante_nombre: '',
    donante_tipo: 'empresa',
    donante_rfc: '',
    donante_direccion: '',
    donante_contacto: '',
    fecha_donacion: new Date().toISOString().split('T')[0],
    fecha_recepcion: new Date().toISOString().split('T')[0],
    centro_destino: '',
    notas: '',
    documento_donacion: '', // ISS-DB-ALIGN: Campo de BD para referencia de documento
    detalles: [],
  });

  // Detalle en edición - usa producto_donacion del catálogo independiente
  const [detalleForm, setDetalleForm] = useState({
    producto_donacion: '',  // Catálogo independiente de donaciones
    numero_lote: '',
    cantidad: '',
    fecha_caducidad: '',
    estado_producto: 'bueno',
    notas: '',
  });

  const filtrosActivos = [searchTerm, filtroEstado, filtroTipoDonante, filtroCentro, filtroFechaDesde, filtroFechaHasta].filter(Boolean).length;

  // ========== AGRUPACIÓN DE ENTREGAS MASIVAS ==========
  // Agrupa entregas que fueron creadas en el mismo minuto con el mismo destinatario
  // para mostrarlas como una sola "entrega masiva"
  const entregasAgrupadas = useMemo(() => {
    if (!todasEntregas || todasEntregas.length === 0) return [];
    
    const grupos = {};
    
    todasEntregas.forEach(entrega => {
      // Crear clave de grupo: destinatario + fecha truncada al minuto
      const fecha = new Date(entrega.fecha_entrega);
      const fechaMinuto = fecha.toISOString().slice(0, 16); // YYYY-MM-DDTHH:MM
      const claveGrupo = `${entrega.destinatario || ''}_${fechaMinuto}`;
      
      if (!grupos[claveGrupo]) {
        grupos[claveGrupo] = {
          clave: claveGrupo,
          destinatario: entrega.destinatario,
          fecha_entrega: entrega.fecha_entrega,
          centro_destino_nombre: entrega.centro_destino_nombre,
          entregado_por_nombre: entrega.entregado_por_nombre,
          entregas: [],
          totalCantidad: 0,
          todosFinalizados: true,
          algunoFinalizado: false,
        };
      }
      
      grupos[claveGrupo].entregas.push(entrega);
      grupos[claveGrupo].totalCantidad += entrega.cantidad || 0;
      
      // Actualizar estados de finalización
      const esFinalizado = entrega.estado_entrega === 'entregado' || entrega.finalizado;
      grupos[claveGrupo].todosFinalizados = grupos[claveGrupo].todosFinalizados && esFinalizado;
      grupos[claveGrupo].algunoFinalizado = grupos[claveGrupo].algunoFinalizado || esFinalizado;
    });
    
    // Convertir a array y ordenar por fecha más reciente
    return Object.values(grupos).sort((a, b) => 
      new Date(b.fecha_entrega) - new Date(a.fecha_entrega)
    );
  }, [todasEntregas]);

  // Toggle expandir/colapsar grupo
  const toggleGrupo = (clave) => {
    setGruposExpandidos(prev => {
      const newSet = new Set(prev);
      if (newSet.has(clave)) {
        newSet.delete(clave);
      } else {
        newSet.add(clave);
      }
      return newSet;
    });
  };

  // Cargar siguiente número de donación
  const cargarSiguienteNumero = useCallback(async () => {
    try {
      const response = await donacionesAPI.getSiguienteNumero();
      setSiguienteNumero(response.data?.numero || '');
    } catch (err) {
      // Si no existe el endpoint, generar localmente
      const year = new Date().getFullYear();
      const randomNum = Math.floor(Math.random() * 1000).toString().padStart(4, '0');
      setSiguienteNumero(`DON-${year}-${randomNum}`);
    }
  }, []);

  // Cargar catálogos - USA CATÁLOGO INDEPENDIENTE DE DONACIONES
  const cargarCatalogos = useCallback(async () => {
    try {
      const [prodDonRes, centrosRes] = await Promise.all([
        productosDonacionAPI.getAll({ page_size: 500, activo: true, ordering: 'nombre' }),
        centrosAPI.getAll({ page_size: 100, activo: true, ordering: 'nombre' }),
      ]);
      setProductosDonacion(prodDonRes.data.results || prodDonRes.data || []);
      setCentros(centrosRes.data.results || centrosRes.data || []);
      
      // Cargar siguiente número de donación
      await cargarSiguienteNumero();
    } catch (err) {
      console.error('Error cargando catálogos:', err);
    }
  }, [cargarSiguienteNumero]);

  // Cargar donaciones
  const cargarDonaciones = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page: currentPage,
        page_size: PAGE_SIZE,
        ordering: '-fecha_donacion',
      };

      if (searchTerm) params.search = searchTerm;
      if (filtroEstado) params.estado = filtroEstado;
      if (filtroTipoDonante) params.donante_tipo = filtroTipoDonante;
      // ISS-DB-ALIGN: Backend espera 'centro' no 'centro_destino'
      if (filtroCentro) params.centro = filtroCentro;
      if (filtroFechaDesde) params.fecha_desde = filtroFechaDesde;
      if (filtroFechaHasta) params.fecha_hasta = filtroFechaHasta;

      const response = await donacionesAPI.getAll(params);
      const data = response.data;

      if (data.results) {
        setDonaciones(data.results);
        setTotalDonaciones(data.count || 0);
        setTotalPages(Math.ceil((data.count || 0) / PAGE_SIZE));
      } else {
        setDonaciones(data || []);
        setTotalDonaciones(data?.length || 0);
        setTotalPages(1);
      }
    } catch (err) {
      console.error('Error cargando donaciones:', err);
      toast.error('Error al cargar donaciones');
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchTerm, filtroEstado, filtroTipoDonante, filtroCentro, filtroFechaDesde, filtroFechaHasta]);

  // Cargar inventario de donaciones (productos con stock disponible)
  const cargarInventarioDonaciones = useCallback(async () => {
    setLoadingInventario(true);
    try {
      const params = {
        page: inventarioPage,
        page_size: PAGE_SIZE,
      };
      
      // Filtro de disponibilidad - ISS-FIX: Backend espera 'agotado' no 'false'
      if (filtroDisponibilidad === 'constock') {
        params.disponible = 'true';
      } else if (filtroDisponibilidad === 'agotado') {
        params.disponible = 'agotado';  // ISS-FIX: Correcto valor para backend
      }
      // 'todos' no agrega filtro
      
      if (searchInventario) params.search = searchInventario;
      if (filtroEstadoProducto) params.estado_producto = filtroEstadoProducto;
      // ISS-FIX: Enviar filtro de caducidad al backend también
      if (filtroCaducidadInv) params.caducidad = filtroCaducidadInv;

      const response = await detallesDonacionAPI.getAll(params);
      const data = response.data;

      // ISS-FIX: El filtro de caducidad ahora se aplica en el backend
      const items = data.results || data || [];

      setInventarioDonaciones(items);
      setInventarioTotalPages(Math.ceil((data.count || items.length) / PAGE_SIZE));

      // Calcular estadísticas
      const allItems = data.results || data || [];
      const hoy = new Date();
      const en30Dias = new Date(hoy.getTime() + 30 * 24 * 60 * 60 * 1000);
      
      let totalUnidades = 0;
      let productosAgotados = 0;
      let productosPorCaducar = 0;

      allItems.forEach(item => {
        totalUnidades += item.cantidad_disponible || 0;
        if ((item.cantidad_disponible || 0) === 0) productosAgotados++;
        if (item.fecha_caducidad) {
          const fechaCad = new Date(item.fecha_caducidad);
          if (fechaCad <= en30Dias) productosPorCaducar++;
        }
      });

      setEstadisticas({
        totalProductos: allItems.length,
        totalUnidades,
        productosAgotados,
        productosPorCaducar,
      });

    } catch (err) {
      console.error('Error cargando inventario de donaciones:', err);
      toast.error('Error al cargar inventario');
    } finally {
      setLoadingInventario(false);
    }
  }, [inventarioPage, searchInventario, filtroEstadoProducto, filtroCaducidadInv, filtroDisponibilidad]);

  // Cargar historial de todas las entregas
  const cargarTodasEntregas = useCallback(async () => {
    setLoadingEntregas(true);
    try {
      const params = {
        page: entregasPage,
        page_size: PAGE_SIZE,
        ordering: '-fecha_entrega',
      };
      if (searchEntregas) params.destinatario = searchEntregas;
      if (filtroCentroEntregas) params.centro_destino = filtroCentroEntregas;
      if (filtroFechaDesdeEntregas) params.fecha_desde = filtroFechaDesdeEntregas;
      if (filtroFechaHastaEntregas) params.fecha_hasta = filtroFechaHastaEntregas;

      const response = await salidasDonacionesAPI.getAll(params);
      const data = response.data;

      if (data.results) {
        setTodasEntregas(data.results);
        setEntregasTotalPages(Math.ceil((data.count || 0) / PAGE_SIZE));
      } else {
        setTodasEntregas(data || []);
        setEntregasTotalPages(1);
      }
    } catch (err) {
      console.error('Error cargando entregas:', err);
      toast.error('Error al cargar historial de entregas');
    } finally {
      setLoadingEntregas(false);
    }
  }, [entregasPage, searchEntregas, filtroCentroEntregas, filtroFechaDesdeEntregas, filtroFechaHastaEntregas]);

  // Exportar entregas a Excel
  const handleExportarEntregas = async () => {
    setExportingEntregas(true);
    try {
      const params = {};
      if (searchEntregas) params.destinatario = searchEntregas;
      if (filtroCentroEntregas) params.centro_destino = filtroCentroEntregas;
      if (filtroFechaDesdeEntregas) params.fecha_desde = filtroFechaDesdeEntregas;
      if (filtroFechaHastaEntregas) params.fecha_hasta = filtroFechaHastaEntregas;
      
      const response = await salidasDonacionesAPI.exportarExcel(params);
      
      // Crear blob y descargar
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Nombre con centro si se filtró
      const centroNombre = filtroCentroEntregas 
        ? centros.find(c => c.id == filtroCentroEntregas)?.nombre?.substring(0, 20).replace(/\s+/g, '_') || 'centro'
        : 'todos';
      link.download = `entregas_donaciones_${centroNombre}_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('Entregas exportadas correctamente');
    } catch (err) {
      console.error('Error exportando entregas:', err);
      toast.error('Error al exportar entregas');
    } finally {
      setExportingEntregas(false);
    }
  };

  // NOTA: Funciones handleDescargarPlantilla y handleImportarEntregas eliminadas
  // Las entregas solo se exportan para verificar movimientos, no se importan

  // === IMPORTACIÓN/EXPORTACIÓN DE DONACIONES ===
  
  // Exportar donaciones a Excel
  const handleExportarDonaciones = async () => {
    setExportingDonaciones(true);
    try {
      const params = {};
      if (filtroEstado) params.estado = filtroEstado;
      if (filtroTipoDonante) params.donante_tipo = filtroTipoDonante;
      if (filtroCentro) params.centro_destino = filtroCentro;
      if (filtroFechaDesde) params.fecha_desde = filtroFechaDesde;
      if (filtroFechaHasta) params.fecha_hasta = filtroFechaHasta;
      if (searchTerm) params.search = searchTerm;
      
      const response = await donacionesAPI.exportarExcel(params);
      
      // Crear blob y descargar
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `donaciones_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('Donaciones exportadas correctamente');
    } catch (err) {
      console.error('Error exportando donaciones:', err);
      toast.error('Error al exportar donaciones');
    } finally {
      setExportingDonaciones(false);
    }
  };

  // Descargar plantilla de importación de donaciones
  const handleDescargarPlantillaDonaciones = async () => {
    try {
      const response = await donacionesAPI.plantillaExcel();
      
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'plantilla_donaciones.xlsx';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('Plantilla descargada');
    } catch (err) {
      console.error('Error descargando plantilla:', err);
      toast.error('Error al descargar plantilla');
    }
  };

  // Importar donaciones desde Excel
  const handleImportarDonaciones = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    setImportingDonaciones(true);
    try {
      const formData = new FormData();
      formData.append('archivo', file);
      
      console.log('[Donaciones] Importando archivo:', file.name);
      const response = await donacionesAPI.importarExcel(formData);
      console.log('[Donaciones] Respuesta importación:', response.data);
      
      const { resultados, mensaje } = response.data;
      
      // ISS-FIX: Usar modal persistente para mostrar resultados
      if (resultados) {
        const { 
          exitosos = 0, 
          fallidos = 0, 
          donaciones_creadas = 0, 
          detalles_creados = 0, 
          errores = [],
          filas_procesadas = 0,
          filas_vacias = 0,
          filas_ejemplo = 0
        } = resultados;
        
        console.log('[Donaciones] Resultados:', { exitosos, fallidos, donaciones_creadas, detalles_creados, filas_procesadas, filas_vacias, filas_ejemplo });
        
        // Determinar tipo de resultado y mensaje principal
        let tipoResultado = 'success';
        let mensajePrincipal = '';
        
        if (donaciones_creadas > 0 || detalles_creados > 0) {
          mensajePrincipal = `Importación exitosa: ${donaciones_creadas} donaciones, ${detalles_creados} detalles`;
          cargarDonaciones();
        } else if (exitosos > 0) {
          mensajePrincipal = `${exitosos} registros importados correctamente`;
          cargarDonaciones();
        } else if (fallidos === 0 && exitosos === 0) {
          tipoResultado = 'error';
          if (filas_procesadas === 0 && filas_ejemplo > 0) {
            mensajePrincipal = `No se importó nada: ${filas_ejemplo} filas fueron ignoradas porque contienen "[EJEMPLO]" o "ELIMINAR". Debe eliminar estas palabras de sus datos o eliminar las filas de ejemplo antes de importar.`;
          } else if (filas_procesadas === 0 && filas_vacias > 0) {
            mensajePrincipal = 'El archivo no contiene datos. Solo se encontraron filas vacías después de los encabezados.';
          } else if (filas_procesadas === 0) {
            mensajePrincipal = 'No se encontraron datos para importar. Verifique que el archivo tenga el formato correcto.';
          } else if (filas_procesadas > 0) {
            mensajePrincipal = `Se procesaron ${filas_procesadas} filas pero ningún producto coincide con el Catálogo de Donaciones. Verifique que las claves de producto existan en el catálogo.`;
          }
        }
        
        if (fallidos > 0 || errores.length > 0) {
          tipoResultado = exitosos > 0 ? 'warning' : 'error';
        }
        
        // Mostrar modal persistente con resultados
        setImportDonacionResultModal({
          tipo: tipoResultado,
          mensaje: mensajePrincipal,
          donaciones_creadas,
          detalles_creados,
          exitosos,
          fallidos,
          errores,
          filas_procesadas,
          filas_vacias,
          filas_ejemplo,
        });
        
        // Toast breve de confirmación
        if (tipoResultado === 'success') {
          toast.success('Importación completada - ver detalles');
        } else if (tipoResultado === 'warning') {
          toast.warning ? toast.warning('Importación parcial - ver errores') : toast.error('Importación parcial - ver errores');
        }
      } else {
        // Respuesta sin estructura esperada
        toast.info(mensaje || 'Importación completada');
      }
    } catch (err) {
      console.error('Error importando donaciones:', err);
      const errorMsg = err.response?.data?.error || err.response?.data?.mensaje || 'Error al importar donaciones';
      // Mostrar error en modal persistente
      setImportDonacionResultModal({
        tipo: 'error',
        mensaje: errorMsg,
        donaciones_creadas: 0,
        detalles_creados: 0,
        exitosos: 0,
        fallidos: 1,
        errores: [{ fila: 0, error: errorMsg }],
        filas_procesadas: 0,
      });
    } finally {
      setImportingDonaciones(false);
      // Limpiar input
      if (donacionFileInputRef.current) {
        donacionFileInputRef.current.value = '';
      }
    }
  };

  // ========== FUNCIONES DEL CATÁLOGO DE PRODUCTOS DE DONACIONES ==========
  
  // Guardar producto de donación (crear o editar)
  const handleGuardarProductoDonacion = async () => {
    if (!catalogoForm.clave || !catalogoForm.nombre) {
      toast.error('Clave y nombre son obligatorios');
      return;
    }

    setActionLoading('guardarProducto');
    try {
      if (editingProductoDonacion) {
        await productosDonacionAPI.update(editingProductoDonacion.id, catalogoForm);
        toast.success('Producto actualizado correctamente');
      } else {
        await productosDonacionAPI.create(catalogoForm);
        toast.success('Producto creado correctamente');
      }
      setShowCatalogoModal(false);
      setCatalogoForm({ clave: '', nombre: '', descripcion: '', unidad_medida: 'PIEZA', presentacion: '', activo: true, notas: '' });
      setEditingProductoDonacion(null);
      cargarCatalogos();
    } catch (err) {
      console.error('Error guardando producto de donación:', err);
      toast.error(err.response?.data?.clave?.[0] || err.response?.data?.error || 'Error al guardar producto');
    } finally {
      setActionLoading(null);
    }
  };

  // Eliminar producto de donación
  const handleEliminarProductoDonacion = async (producto) => {
    setActionLoading(producto.id);
    try {
      await productosDonacionAPI.delete(producto.id);
      toast.success('Producto eliminado correctamente');
      cargarCatalogos();
    } catch (err) {
      console.error('Error eliminando producto de donación:', err);
      toast.error(err.response?.data?.error || 'No se puede eliminar: el producto tiene donaciones asociadas');
    } finally {
      setActionLoading(null);
      setConfirmDeleteProducto(null);
    }
  };

  // ========== IMPORTACIÓN/EXPORTACIÓN DEL CATÁLOGO ==========
  
  // Descargar plantilla Excel para importar productos
  const handleDescargarPlantillaCatalogo = async () => {
    setExportingCatalogo(true);
    try {
      const response = await productosDonacionAPI.descargarPlantilla();
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'plantilla_productos_donacion.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Plantilla descargada correctamente');
    } catch (err) {
      console.error('Error descargando plantilla:', err);
      toast.error('Error al descargar plantilla');
    } finally {
      setExportingCatalogo(false);
    }
  };

  // Exportar catálogo de productos a Excel
  const handleExportarCatalogo = async () => {
    setExportingCatalogo(true);
    try {
      const response = await productosDonacionAPI.exportarExcel();
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const fecha = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      link.setAttribute('download', `productos_donacion_${fecha}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Catálogo exportado correctamente');
    } catch (err) {
      console.error('Error exportando catálogo:', err);
      toast.error('Error al exportar catálogo');
    } finally {
      setExportingCatalogo(false);
    }
  };

  // Importar productos desde Excel
  const handleImportarCatalogo = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validar extensión
    const validExtensions = ['.xlsx', '.xls'];
    const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!validExtensions.includes(fileExt)) {
      toast.error('Solo se permiten archivos Excel (.xlsx, .xls)');
      if (catalogoFileInputRef.current) catalogoFileInputRef.current.value = '';
      return;
    }

    // Validar tamaño (máximo 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('El archivo no debe superar 5MB');
      if (catalogoFileInputRef.current) catalogoFileInputRef.current.value = '';
      return;
    }

    setImportingCatalogo(true);
    try {
      const formData = new FormData();
      formData.append('archivo', file);
      
      const response = await productosDonacionAPI.importarExcel(formData);
      const result = response.data;
      
      // Mostrar modal con resultados
      setImportResultModal({
        success: result.success,
        creados: result.creados || 0,
        actualizados: result.actualizados || 0,
        total: result.total || 0,
        errores: result.errores || [],
      });
      
      // Recargar catálogo si hubo cambios
      if (result.total > 0) {
        cargarCatalogos();
      }
    } catch (err) {
      console.error('Error importando productos:', err);
      const errorMsg = err.response?.data?.error || 'Error al importar archivo';
      setImportResultModal({
        success: false,
        creados: 0,
        actualizados: 0,
        total: 0,
        errores: [errorMsg],
      });
    } finally {
      setImportingCatalogo(false);
      if (catalogoFileInputRef.current) catalogoFileInputRef.current.value = '';
    }
  };

  // ========== EXPORTAR INVENTARIO DE DONACIONES ==========
  
  // Construir parámetros de filtro actuales del inventario
  const getInventarioFilterParams = () => {
    const params = {};
    if (searchInventario) params.search = searchInventario;
    if (filtroDisponibilidad === 'constock') params.disponible = 'true';
    else if (filtroDisponibilidad === 'agotado') params.disponible = 'agotado';
    if (filtroCaducidadInv) params.caducidad = filtroCaducidadInv;
    if (filtroEstadoProducto) params.estado_producto = filtroEstadoProducto;
    return params;
  };

  // Exportar inventario a Excel con formato trazabilidad
  const handleExportarInventarioExcel = async () => {
    setExportingInventario(true);
    try {
      const params = getInventarioFilterParams();
      const response = await detallesDonacionAPI.exportarExcel(params);
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const fecha = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      link.setAttribute('download', `inventario_donaciones_trazabilidad_${fecha}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Inventario exportado a Excel correctamente');
    } catch (err) {
      console.error('Error exportando inventario Excel:', err);
      toast.error('Error al exportar inventario a Excel');
    } finally {
      setExportingInventario(false);
    }
  };

  // Exportar inventario a PDF
  const handleExportarInventarioPdf = async () => {
    const win = abrirPdfEnNavegador(); // Pre-abrir pestaña (preserva user-gesture)
    if (!win) return;

    setExportingInventario(true);
    try {
      const params = getInventarioFilterParams();
      const response = await detallesDonacionAPI.exportarPdf(params);
      
      if (abrirPdfEnNavegador(response.data, win)) {
        toast.success('Inventario exportado a PDF correctamente');
      }
    } catch (err) {
      console.error('Error exportando inventario PDF:', err);
      toast.error('Error al exportar inventario a PDF');
    } finally {
      setExportingInventario(false);
    }
  };

  // ========== CREACIÓN RÁPIDA DE PRODUCTO ==========
  
  // Guardar producto rápido desde modal
  const handleGuardarQuickProduct = async () => {
    if (!quickProductForm.clave || !quickProductForm.nombre) {
      toast.error('Clave y nombre son obligatorios');
      return;
    }

    setActionLoading('quickProduct');
    try {
      await productosDonacionAPI.create({
        ...quickProductForm,
        activo: true,
      });
      toast.success('Producto creado correctamente');
      setShowQuickProductModal(false);
      setQuickProductForm({ clave: '', nombre: '', descripcion: '', unidad_medida: 'PIEZA', presentacion: '' });
      cargarCatalogos();
    } catch (err) {
      console.error('Error creando producto rápido:', err);
      toast.error(err.response?.data?.clave?.[0] || err.response?.data?.error || 'Error al crear producto');
    } finally {
      setActionLoading(null);
    }
  };

  // ========== CARGA MASIVA DE PRODUCTOS ==========
  
  // Parsear texto de carga masiva
  const parseBulkText = () => {
    if (!bulkText.trim()) {
      setBulkProducts([]);
      return;
    }
    
    const lines = bulkText.split('\n').filter(line => line.trim());
    const products = lines.map((line, idx) => {
      // Formato esperado: CLAVE | NOMBRE | DESCRIPCION | UNIDAD
      // O simplemente: CLAVE - NOMBRE
      const parts = line.includes('|') 
        ? line.split('|').map(p => p.trim())
        : line.split('-').map(p => p.trim());
      
      return {
        id: idx,
        clave: parts[0] || '',
        nombre: parts[1] || parts[0] || '',
        descripcion: parts[2] || '',
        unidad_medida: parts[3] || 'PIEZA',
        valid: Boolean(parts[0] && parts[1]),
      };
    });
    
    setBulkProducts(products);
  };

  // Importar productos masivamente
  const handleBulkImport = async () => {
    const validProducts = bulkProducts.filter(p => p.valid);
    if (validProducts.length === 0) {
      toast.error('No hay productos válidos para importar');
      return;
    }

    setActionLoading('bulkImport');
    let exitosos = 0;
    let fallidos = 0;

    for (const product of validProducts) {
      try {
        await productosDonacionAPI.create({
          clave: product.clave,
          nombre: product.nombre,
          descripcion: product.descripcion,
          unidad_medida: product.unidad_medida,
          activo: true,
        });
        exitosos++;
      } catch (err) {
        console.error(`Error importando ${product.clave}:`, err);
        fallidos++;
      }
    }

    setActionLoading(null);
    
    if (exitosos > 0) {
      toast.success(`${exitosos} productos importados correctamente`);
      cargarCatalogos();
    }
    if (fallidos > 0) {
      toast.error(`${fallidos} productos fallaron (posibles duplicados)`);
    }

    setShowBulkAddModal(false);
    setBulkText('');
    setBulkProducts([]);
  };

  // ========== FINALIZACIÓN DE ENTREGAS ==========
  
  // Finalizar una entrega (marcar como entregado)
  const handleFinalizarEntrega = async (entrega) => {
    setActionLoading(entrega.id);
    try {
      await salidasDonacionesAPI.finalizar(entrega.id);
      toast.success('Entrega marcada como finalizada');
      cargarTodasEntregas();
      cargarInventarioDonaciones();  // Mantener UI sincronizada
      if (historialSalidas.length > 0) {
        // Actualizar también el historial del modal si está abierto
        setHistorialSalidas(prev => prev.map(s => 
          s.id === entrega.id ? { ...s, estado_entrega: 'entregado', finalizado: true } : s
        ));
      }
    } catch (err) {
      console.error('Error finalizando entrega:', err);
      toast.error(err.response?.data?.error || 'Error al finalizar entrega');
    } finally {
      setActionLoading(null);
      setConfirmFinalizarEntrega(null);
    }
  };

  // Finalizar GRUPO de entregas (salida masiva completa)
  const handleFinalizarGrupo = async (grupo) => {
    setFinalizandoGrupo(true);
    const entregas = grupo.entregas.filter(e => !e.finalizado && e.estado_entrega !== 'entregado');
    let exitosos = 0;
    let errores = [];
    
    for (const entrega of entregas) {
      try {
        await salidasDonacionesAPI.finalizar(entrega.id);
        exitosos++;
      } catch (err) {
        errores.push({ producto: entrega.producto_nombre, error: err.response?.data?.error || 'Error' });
      }
    }
    
    if (exitosos > 0) {
      toast.success(`${exitosos} entregas finalizadas correctamente`);
      cargarTodasEntregas();
      cargarInventarioDonaciones();
    }
    if (errores.length > 0) {
      toast.error(`${errores.length} entregas fallaron: ${errores[0].error}`);
    }
    
    setFinalizandoGrupo(false);
    setConfirmFinalizarGrupo(null);
  };

  // Eliminar una entrega pendiente (devuelve stock al inventario)
  const handleEliminarEntrega = async (entrega) => {
    setActionLoading(entrega.id);
    try {
      await salidasDonacionesAPI.delete(entrega.id);
      toast.success('Entrega eliminada - Stock devuelto al inventario');
      cargarTodasEntregas();
      cargarInventarioDonaciones();  // Actualizar inventario para reflejar stock devuelto
      if (historialSalidas.length > 0) {
        // Remover del historial si está abierto
        setHistorialSalidas(prev => prev.filter(s => s.id !== entrega.id));
      }
    } catch (err) {
      console.error('Error eliminando entrega:', err);
      toast.error(err.response?.data?.error || 'Error al eliminar entrega');
    } finally {
      setActionLoading(null);
      setConfirmEliminarEntrega(null);
    }
  };

  // Descargar recibo de salida como PDF
  // ISS-FIX: Soporta entregas agrupadas pasando todos los IDs del grupo
  const handleDescargarReciboSalida = async (salida, finalizado = false, grupo = null) => {
    try {
      // Obtener todos los IDs del grupo si está disponible
      const ids = grupo?.entregas?.map(e => e.id) || [];
      const response = await salidasDonacionesAPI.getReciboPdf(salida.id, finalizado, ids);
      
      if (abrirPdfEnNavegador(response.data)) {
        const count = ids.length || 1;
        toast.success(`Recibo abierto (${count} producto${count > 1 ? 's' : ''})`);
      }
    } catch (err) {
      console.error('Error abriendo recibo:', err);
      toast.error('Error al abrir recibo');
    }
  };

  useEffect(() => {
    cargarCatalogos();
  }, [cargarCatalogos]);

  useEffect(() => {
    if (activeTab === 'donaciones') {
      cargarDonaciones();
    } else if (activeTab === 'catalogo') {
      cargarCatalogos();
    } else if (activeTab === 'inventario') {
      cargarInventarioDonaciones();
    } else if (activeTab === 'entregas') {
      cargarTodasEntregas();
    }
  }, [activeTab, cargarDonaciones, cargarCatalogos, cargarInventarioDonaciones, cargarTodasEntregas]);

  // Reset formulario
  const resetForm = () => {
    setFormData({
      numero: '',
      donante_nombre: '',
      donante_tipo: 'empresa',  // ISS-DB-ALIGN: Primer valor del array de tipos
      donante_rfc: '',
      donante_direccion: '',
      donante_contacto: '',
      fecha_donacion: new Date().toISOString().split('T')[0],
      fecha_recepcion: new Date().toISOString().split('T')[0],
      centro_destino: '',
      notas: '',
      documento_donacion: '', // ISS-DB-ALIGN: Campo para referencia de documento
      detalles: [],
    });
    setDetalleForm({
      producto_donacion: '',  // Nuevo catálogo independiente
      numero_lote: '',
      cantidad: '',
      fecha_caducidad: '',
      estado_producto: 'bueno',  // ISS-DB-ALIGN: Valor de BD
      notas: '',
    });
    setEditingDonacion(null);
  };

  // Abrir modal de creación
  const handleNuevo = () => {
    resetForm();
    // Auto-rellenar número de donación
    if (siguienteNumero) {
      setFormData(prev => ({ ...prev, numero: siguienteNumero }));
    }
    setShowModal(true);
  };

  // Abrir modal de edición
  const handleEditar = (donacion) => {
    setEditingDonacion(donacion);
    setFormData({
      numero: donacion.numero || '',
      donante_nombre: donacion.donante_nombre || '',
      donante_tipo: donacion.donante_tipo || 'empresa',
      donante_rfc: donacion.donante_rfc || '',
      donante_direccion: donacion.donante_direccion || '',
      donante_contacto: donacion.donante_contacto || '',
      fecha_donacion: donacion.fecha_donacion || '',
      fecha_recepcion: donacion.fecha_recepcion || '',
      centro_destino: donacion.centro_destino || '',
      notas: donacion.notas || '',
      documento_donacion: donacion.documento_donacion || '', // ISS-DB-ALIGN
      detalles: donacion.detalles || [],
    });
    setShowModal(true);
  };

  // Ver detalle
  const handleVerDetalle = (donacion) => {
    setViewingDonacion(donacion);
    setShowDetalleModal(true);
  };

  // Agregar detalle al formulario - USA CATÁLOGO INDEPENDIENTE
  const handleAgregarDetalle = () => {
    // Validación de campos obligatorios
    if (!detalleForm.producto_donacion) {
      toast.error('Selecciona un producto del catálogo de donaciones');
      return;
    }
    if (!detalleForm.cantidad || parseInt(detalleForm.cantidad) <= 0) {
      toast.error('La cantidad debe ser mayor a 0');
      return;
    }
    if (!detalleForm.numero_lote || detalleForm.numero_lote.trim() === '') {
      toast.error('El número de lote es obligatorio');
      return;
    }
    if (!detalleForm.fecha_caducidad) {
      toast.error('La fecha de caducidad es obligatoria');
      return;
    }
    // Validar que la fecha no sea pasada
    const fechaCad = new Date(detalleForm.fecha_caducidad);
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    if (fechaCad < hoy) {
      toast.error('La fecha de caducidad no puede ser una fecha pasada');
      return;
    }
    // Validar que la fecha no esté más de 8 años en el futuro
    const fechaMaxima = new Date();
    fechaMaxima.setFullYear(fechaMaxima.getFullYear() + 8);
    if (fechaCad > fechaMaxima) {
      const maxFechaStr = fechaMaxima.toLocaleDateString('es-MX');
      const caducidadStr = fechaCad.toLocaleDateString('es-MX');
      toast.error(`Fecha de caducidad muy lejana (${caducidadStr}). Máximo 8 años desde hoy (${maxFechaStr}). Verifique el formato (DD/MM/AAAA).`);
      return;
    }

    const producto = productosDonacion.find((p) => p.id === parseInt(detalleForm.producto_donacion));
    const nuevoDetalle = {
      tempId: Date.now(),
      producto_donacion: parseInt(detalleForm.producto_donacion),  // Nuevo catálogo
      producto_clave: producto?.clave || '',
      producto_nombre: producto?.nombre || '',
      numero_lote: detalleForm.numero_lote,
      cantidad: parseInt(detalleForm.cantidad),
      fecha_caducidad: detalleForm.fecha_caducidad || null,
      estado_producto: detalleForm.estado_producto,
      notas: detalleForm.notas,
    };

    setFormData((prev) => ({
      ...prev,
      detalles: [...prev.detalles, nuevoDetalle],
    }));

    setDetalleForm({
      producto_donacion: '',
      numero_lote: '',
      cantidad: '',
      fecha_caducidad: '',
      estado_producto: 'bueno',
      notas: '',
    });
  };

  // Eliminar detalle del formulario
  const handleEliminarDetalle = (index) => {
    setFormData((prev) => ({
      ...prev,
      detalles: prev.detalles.filter((_, i) => i !== index),
    }));
  };

  // Guardar donación
  const handleGuardar = async () => {
    // Validación: debe tener productos
    if (formData.detalles.length === 0) {
      toast.error('Debe agregar al menos un producto a la donación');
      return;
    }
    
    if (!formData.donante_nombre || !formData.centro_destino) {
      toast.error('Completa el nombre del donante y el centro destino');
      return;
    }

    setActionLoading('guardar');
    try {
      const payload = {
        ...formData,
        centro_destino: parseInt(formData.centro_destino),
        detalles: formData.detalles.map((d) => ({
          producto_donacion: d.producto_donacion,  // Nuevo catálogo independiente
          numero_lote: d.numero_lote || null,
          cantidad: d.cantidad,
          fecha_caducidad: d.fecha_caducidad || null,
          estado_producto: d.estado_producto,
          notas: d.notas || '',
        })),
      };

      if (editingDonacion) {
        await donacionesAPI.update(editingDonacion.id, payload);
        toast.success('Donación actualizada correctamente');
      } else {
        await donacionesAPI.create(payload);
        toast.success('Donación registrada correctamente');
      }

      setShowModal(false);
      resetForm();
      cargarDonaciones();
    } catch (err) {
      console.error('Error guardando donación:', err);
      toast.error(err.response?.data?.error || 'Error al guardar donación');
    } finally {
      setActionLoading(null);
    }
  };

  // Eliminar donación
  const handleEliminar = async (id) => {
    setActionLoading(id);
    try {
      await donacionesAPI.delete(id);
      toast.success('Donación eliminada correctamente');
      cargarDonaciones();
    } catch (err) {
      console.error('Error eliminando donación:', err);
      toast.error(err.response?.data?.error || 'Error al eliminar donación');
    } finally {
      setActionLoading(null);
      setConfirmDelete(null);
    }
  };

  // Procesar donación
  const handleProcesar = async (id) => {
    setActionLoading(id);
    try {
      await donacionesAPI.procesar(id);
      toast.success('Donación procesada - Se crearon los movimientos de entrada');
      cargarDonaciones();
    } catch (err) {
      console.error('Error procesando donación:', err);
      toast.error(err.response?.data?.error || 'Error al procesar donación');
    } finally {
      setActionLoading(null);
      setConfirmProcesar(null);
    }
  };

  // Procesar TODAS las donaciones pendientes de una vez
  const handleProcesarTodas = async () => {
    setProcesandoTodas(true);
    try {
      const response = await donacionesAPI.procesarTodas();
      const { procesadas, errores } = response.data;
      
      if (procesadas > 0) {
        toast.success(`${procesadas} donaciones procesadas correctamente`);
        cargarDonaciones();
      } else {
        toast.info('No había donaciones pendientes para procesar');
      }
      
      if (errores && errores.length > 0) {
        errores.slice(0, 3).forEach(err => {
          toast.error(`Error en ${err.donacion}: ${err.error}`);
        });
      }
    } catch (err) {
      console.error('Error procesando todas las donaciones:', err);
      toast.error(err.response?.data?.error || 'Error al procesar donaciones');
    } finally {
      setProcesandoTodas(false);
      setConfirmProcesarTodas(false);
    }
  };

  // Recibir donación (pendiente → recibida)
  const handleRecibir = async (id) => {
    setActionLoading(id);
    try {
      await donacionesAPI.recibir(id);
      toast.success('Donación marcada como recibida');
      cargarDonaciones();
    } catch (err) {
      console.error('Error recibiendo donación:', err);
      toast.error(err.response?.data?.error || 'Error al recibir donación');
    } finally {
      setActionLoading(null);
      setConfirmRecibir(null);
    }
  };

  // Rechazar donación
  const handleRechazar = async (id, motivo) => {
    setActionLoading(id);
    try {
      await donacionesAPI.rechazar(id, { motivo });
      toast.success('Donación rechazada');
      cargarDonaciones();
    } catch (err) {
      console.error('Error rechazando donación:', err);
      toast.error(err.response?.data?.error || 'Error al rechazar donación');
    } finally {
      setActionLoading(null);
      setConfirmRechazar(null);
    }
  };

  // Limpiar filtros
  const limpiarFiltros = () => {
    setSearchTerm('');
    setFiltroEstado('');
    setFiltroTipoDonante('');
    setFiltroCentro('');
    setFiltroFechaDesde('');
    setFiltroFechaHasta('');
    setCurrentPage(1);
  };

  // =====================================================
  // SALIDAS DE DONACIONES (Almacén Separado)
  // =====================================================

  // Abrir modal para registrar salida
  const handleAbrirSalida = (detalle, donacion) => {
    setSalidaDetalle({ ...detalle, donacion_numero: donacion.numero });
    setSalidaForm({
      cantidad: '',
      destinatario: '',
      motivo: '',
      notas: '',
    });
    setShowSalidaModal(true);
  };

  // Registrar salida de donación
  const handleRegistrarSalida = async () => {
    // Prevenir doble envío
    if (actionLoading === 'salida') {
      return;
    }
    
    if (!salidaForm.cantidad || !salidaForm.destinatario) {
      toast.error('Completa cantidad y destinatario');
      return;
    }

    const cantidad = parseInt(salidaForm.cantidad);
    if (cantidad <= 0 || cantidad > salidaDetalle.cantidad_disponible) {
      toast.error(`Cantidad inválida. Disponible: ${salidaDetalle.cantidad_disponible}`);
      return;
    }

    setActionLoading('salida');
    try {
      await salidasDonacionesAPI.create({
        detalle_donacion: salidaDetalle.id,
        cantidad: cantidad,
        destinatario: salidaForm.destinatario,
        motivo: salidaForm.motivo || null,
        notas: salidaForm.notas || null,
      });
      toast.success('Entrega registrada correctamente');
      
      // IMPORTANTE: Cerrar modal INMEDIATAMENTE para evitar duplicados
      setShowSalidaModal(false);
      setSalidaDetalle(null);
      
      // Refrescar donación si está abierta
      if (viewingDonacion) {
        const updated = await donacionesAPI.getById(viewingDonacion.id);
        setViewingDonacion(updated.data);
      }
      
      // SIEMPRE actualizar inventario ya que el stock cambió
      cargarInventarioDonaciones();
      
      // Refrescar según la tab activa (además del inventario)
      if (activeTab === 'donaciones') {
        cargarDonaciones();
      } else if (activeTab === 'entregas') {
        cargarTodasEntregas();
      }
    } catch (err) {
      console.error('Error registrando salida:', err);
      const errorMsg = err.response?.data?.error || err.response?.data?.cantidad?.[0] || 'Error al registrar entrega';
      toast.error(errorMsg);
      
      // Si el error es de stock insuficiente, actualizar la cantidad disponible en el modal
      if (err.response?.data?.cantidad || errorMsg.includes('Stock insuficiente') || errorMsg.includes('Disponible')) {
        // Recargar datos del inventario para obtener cantidad actualizada
        try {
          cargarInventarioDonaciones();
          // Buscar el detalle actualizado
          const response = await detallesDonacionAPI.getById(salidaDetalle.id);
          if (response.data) {
            setSalidaDetalle(prev => ({
              ...prev,
              cantidad_disponible: response.data.cantidad_disponible
            }));
          }
        } catch (refreshErr) {
          console.error('Error actualizando cantidad disponible:', refreshErr);
        }
      }
    } finally {
      setActionLoading(null);
    }
  };

  // Ver historial de salidas de una donación
  const handleVerHistorialSalidas = async (donacion) => {
    setLoadingSalidas(true);
    setShowHistorialModal(true);
    try {
      const res = await salidasDonacionesAPI.getAll({ donacion: donacion.id, page_size: 100 });
      setHistorialSalidas(res.data.results || res.data || []);
    } catch (err) {
      console.error('Error cargando historial:', err);
      toast.error('Error al cargar historial de entregas');
    } finally {
      setLoadingSalidas(false);
    }
  };

  // Formatear fecha
  const formatFecha = (fecha) => {
    if (!fecha) return '-';
    return new Date(fecha).toLocaleDateString('es-MX', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  // Si el usuario no tiene permiso para ver donaciones
  if (!puede.ver) {
    return (
      <div className="p-6">
        <PageHeader
          title="Donaciones"
          subtitle="Gestión de donaciones recibidas"
          icon={FaGift}
        />
        <div className="bg-white rounded-xl shadow-sm border p-8 text-center">
          <FaGift className="mx-auto text-5xl text-gray-300 mb-4" />
          <h2 className="text-xl font-semibold text-gray-700 mb-2">Acceso Restringido</h2>
          <p className="text-gray-500">No tienes permisos para acceder al módulo de Donaciones.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <PageHeader
        title="Donaciones"
        subtitle="Gestión completa del almacén de donaciones"
        icon={FaGift}
      />

      {/* Tabs de navegación */}
      <div className="bg-white rounded-xl shadow-sm border mb-6">
        <div className="flex border-b overflow-x-auto">
          <button
            onClick={() => setActiveTab('donaciones')}
            className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors border-b-2 -mb-px whitespace-nowrap ${
              activeTab === 'donaciones'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <FaGift /> Donaciones
          </button>
          <button
            onClick={() => setActiveTab('catalogo')}
            className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors border-b-2 -mb-px whitespace-nowrap ${
              activeTab === 'catalogo'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <FaClipboardList /> Catálogo Productos
          </button>
          <button
            onClick={() => setActiveTab('inventario')}
            className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors border-b-2 -mb-px whitespace-nowrap ${
              activeTab === 'inventario'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <FaWarehouse /> Inventario
          </button>
          <button
            onClick={() => setActiveTab('entregas')}
            className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors border-b-2 -mb-px whitespace-nowrap ${
              activeTab === 'entregas'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <FaHandHoldingMedical /> Entregas
          </button>
        </div>
      </div>

      {/* ========== TAB: DONACIONES ========== */}
      {activeTab === 'donaciones' && (
        <>
          {/* Banner informativo del flujo */}
          <div className="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-xl p-4 mb-6">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <FaGift className="text-purple-600 text-xl" />
              </div>
              <div>
                <h3 className="font-semibold text-purple-800">Flujo de Donaciones</h3>
                <div className="flex flex-wrap items-center gap-2 text-sm text-purple-700 mt-1">
                  <span className="flex items-center gap-1"><FaPlus className="text-purple-500" /> Registrar</span>
                  <FaArrowRight className="text-purple-400" />
                  <span className="flex items-center gap-1"><FaCheck className="text-purple-500" /> Procesar</span>
                  <FaArrowRight className="text-purple-400" />
                  <span className="flex items-center gap-1"><FaWarehouse className="text-purple-500" /> Inventario</span>
                  <FaArrowRight className="text-purple-400" />
                  <span className="flex items-center gap-1"><FaHandHoldingMedical className="text-purple-500" /> Entregar</span>
                </div>
                <p className="text-xs text-purple-600 mt-2">
                  Las donaciones procesadas aparecen en "Inventario" donde puedes dar salida a los productos.
                </p>
              </div>
            </div>
          </div>

          {/* Barra de acciones */}
          <div className="bg-white rounded-xl shadow-sm border p-4 mb-6">
            <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center justify-between">
              {/* Búsqueda */}
              <div className="relative flex-1 max-w-md">
                <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Buscar por número, donante..."
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                />
              </div>

              {/* Acciones */}
              <div className="flex gap-2 flex-wrap">
                {/* Toggle filtros */}
                <button
                  onClick={() => setShowFiltersMenu(!showFiltersMenu)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                    filtrosActivos > 0
                      ? 'bg-primary/10 border-primary text-primary'
                      : 'bg-white hover:bg-gray-50'
                  }`}
                >
                  <FaFilter />
                  Filtros
                  {filtrosActivos > 0 && (
                    <span className="bg-primary text-white text-xs px-2 py-0.5 rounded-full">
                      {filtrosActivos}
                    </span>
                  )}
                  <FaChevronDown className={`transition-transform ${showFiltersMenu ? 'rotate-180' : ''}`} />
                </button>

                {/* Botón Exportar Excel */}
                <button
                  onClick={handleExportarDonaciones}
                  disabled={exportingDonaciones || donaciones.length === 0}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg border text-green-700 border-green-300 hover:bg-green-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {exportingDonaciones ? (
                    <FaSpinner className="animate-spin" />
                  ) : (
                    <FaFileExport />
                  )}
                  Exportar
                </button>

                {/* Botones de Importación - Solo para admin/farmacia */}
                {puede.crear && (
                  <>
                    {/* Descargar Plantilla */}
                    <button
                      onClick={handleDescargarPlantillaDonaciones}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg border text-blue-700 border-blue-300 hover:bg-blue-50 transition-colors"
                      title="Descargar plantilla Excel para importar donaciones"
                    >
                      <FaDownload /> Plantilla
                    </button>
                    
                    {/* Importar Excel */}
                    <label className="flex items-center gap-2 px-4 py-2 rounded-lg border text-purple-700 border-purple-300 hover:bg-purple-50 transition-colors cursor-pointer">
                      {importingDonaciones ? (
                        <FaSpinner className="animate-spin" />
                      ) : (
                        <FaFileImport />
                      )}
                      Importar
                      <input
                        ref={donacionFileInputRef}
                        type="file"
                        accept=".xlsx,.xls"
                        onChange={handleImportarDonaciones}
                        disabled={importingDonaciones}
                        className="hidden"
                      />
                    </label>
                  </>
                )}

                {/* Procesar Todas las Pendientes - Botón separado para mayor visibilidad */}
                {puede.procesar && (() => {
                  const pendientes = donaciones.filter(d => ['pendiente', 'recibida'].includes(d.estado)).length;
                  if (pendientes === 0) return null;
                  return (
                    <button
                      onClick={() => setConfirmProcesarTodas(true)}
                      disabled={procesandoTodas}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-500 text-white hover:bg-orange-600 transition-colors disabled:opacity-50 font-medium shadow-sm"
                      title={`Procesar ${pendientes} donaciones pendientes de una vez`}
                    >
                      {procesandoTodas ? (
                        <FaSpinner className="animate-spin" />
                      ) : (
                        <FaCheck />
                      )}
                      Procesar Todas ({pendientes})
                    </button>
                  );
                })()}

                {/* Botón nueva donación */}
                {puede.crear && (
              <button
                onClick={handleNuevo}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-white transition-colors"
                style={{ backgroundColor: COLORS.primary }}
              >
                <FaPlus /> Nueva Donación
              </button>
            )}
          </div>
        </div>

        {/* Panel de filtros colapsable */}
        {showFiltersMenu && (
          <div className="mt-4 pt-4 border-t grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
              <select
                value={filtroEstado}
                onChange={(e) => {
                  setFiltroEstado(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
              >
                <option value="">Todos los estados</option>
                {Object.entries(ESTADOS_DONACION).map(([key, val]) => (
                  <option key={key} value={key}>
                    {val.icon} {val.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Donante</label>
              <select
                value={filtroTipoDonante}
                onChange={(e) => {
                  setFiltroTipoDonante(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
              >
                <option value="">Todos los tipos</option>
                {TIPOS_DONANTE.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex gap-2">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">Desde</label>
                <input
                  type="date"
                  value={filtroFechaDesde}
                  onChange={(e) => {
                    setFiltroFechaDesde(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                />
              </div>
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">Hasta</label>
                <input
                  type="date"
                  value={filtroFechaHasta}
                  onChange={(e) => {
                    setFiltroFechaHasta(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            {filtrosActivos > 0 && (
              <button
                onClick={limpiarFiltros}
                className="text-sm text-gray-600 hover:text-primary flex items-center gap-1"
              >
                <FaTimes /> Limpiar filtros
              </button>
            )}
          </div>
        )}
      </div>

      {/* Tabla de donaciones */}
      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <FaSpinner className="animate-spin text-4xl text-theme-primary" />
          </div>
        ) : donaciones.length === 0 ? (
          <div className="text-center py-20 text-gray-500">
            <FaGift className="mx-auto text-5xl mb-4 opacity-30" />
            <p>No se encontraron donaciones</p>
          </div>
        ) : (
          <>
          {/* Vista móvil: tarjetas */}
        <div className="lg:hidden space-y-3 p-4">
          {donaciones.map((donacion) => {
            const estado = ESTADOS_DONACION[donacion.estado] || ESTADOS_DONACION.pendiente;
            return (
              <div key={donacion.id} className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                {/* Header con número y estado */}
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-theme-primary">{donacion.numero || `DON-${donacion.id}`}</span>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${estado.color}`}>
                        {estado.icon} {estado.label}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1 flex items-center gap-1">
                      <FaUser className="text-gray-400" />
                      {donacion.donante_nombre}
                    </p>
                    <p className="text-xs text-gray-500">
                      {TIPOS_DONANTE.find((t) => t.value === donacion.donante_tipo)?.label || donacion.donante_tipo}
                    </p>
                  </div>
                  <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                    <FaBox /> {donacion.detalles?.length || 0}
                  </span>
                </div>
                
                {/* Info grid */}
                <div className="grid grid-cols-2 gap-3 py-3 border-y border-gray-100 text-sm">
                  <div>
                    <div className="text-gray-500 text-xs">Centro destino</div>
                    <div className="font-medium text-gray-800">{donacion.centro_destino_nombre || '-'}</div>
                  </div>
                  <div>
                    <div className="text-gray-500 text-xs">Fecha</div>
                    <div className="font-medium text-gray-800">{formatFecha(donacion.fecha_donacion)}</div>
                  </div>
                </div>
                
                {/* Acciones */}
                <div className="flex items-center justify-end gap-3 mt-3 pt-2">
                  <button
                    onClick={() => handleVerDetalle(donacion)}
                    className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                    title="Ver detalle"
                  >
                    <FaEye size={18} />
                  </button>
                  {donacion.estado === 'procesada' && (
                    <button
                      onClick={() => handleVerHistorialSalidas(donacion)}
                      className="p-2 text-purple-600 hover:bg-purple-50 rounded-lg"
                      title="Ver historial"
                    >
                      <FaHistory size={18} />
                    </button>
                  )}
                  {puede.editar && donacion.estado === 'pendiente' && (
                    <button onClick={() => handleEditar(donacion)} className="p-2 text-amber-600 hover:bg-amber-50 rounded-lg">
                      <FaEdit size={18} />
                    </button>
                  )}
                  {puede.procesar && donacion.estado === 'pendiente' && (
                    <button
                      onClick={() => setConfirmRecibir(donacion)}
                      disabled={actionLoading === donacion.id}
                      className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg disabled:opacity-50"
                    >
                      <FaBox size={18} />
                    </button>
                  )}
                  {puede.procesar && ['pendiente', 'recibida'].includes(donacion.estado) && (
                    <button
                      onClick={() => setConfirmProcesar(donacion)}
                      disabled={actionLoading === donacion.id}
                      className="p-2 text-green-600 hover:bg-green-50 rounded-lg disabled:opacity-50"
                    >
                      <FaCheck size={18} />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
        
        {/* Vista desktop: tabla */}
        <div className="hidden lg:block w-full overflow-x-auto rounded-lg border border-gray-200 shadow-md">
          <table className="w-full min-w-[700px]">
              <thead className="bg-theme-gradient sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Número</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Donante</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Tipo</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Centro Destino</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Fecha</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Items</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Estado</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {donaciones.map((donacion) => {
                  const estado = ESTADOS_DONACION[donacion.estado] || ESTADOS_DONACION.pendiente;
                  return (
                    <tr key={donacion.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-900">
                        {donacion.numero || `DON-${donacion.id}`}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <FaUser className="text-gray-400" />
                          <span>{donacion.donante_nombre}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 capitalize text-sm text-gray-600">
                        {TIPOS_DONANTE.find((t) => t.value === donacion.donante_tipo)?.label || donacion.donante_tipo}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <FaBuilding className="text-gray-400" />
                          <span>{donacion.centro_destino_nombre || '-'}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        <div className="flex items-center gap-2">
                          <FaCalendar className="text-gray-400" />
                          <span>{formatFecha(donacion.fecha_donacion)}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                          <FaBox /> {donacion.detalles?.length || 0} productos
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${estado.color}`}>
                          {estado.icon} {estado.label}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-1">
                          {/* Ver detalle */}
                          <button
                            onClick={() => handleVerDetalle(donacion)}
                            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                            title="Ver detalle"
                          >
                            <FaEye />
                          </button>

                          {/* Ver historial de entregas (solo procesadas) */}
                          {donacion.estado === 'procesada' && (
                            <button
                              onClick={() => handleVerHistorialSalidas(donacion)}
                              className="p-2 text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                              title="Ver historial de entregas"
                            >
                              <FaHistory />
                            </button>
                          )}

                          {/* Editar (solo pendientes) */}
                          {puede.editar && donacion.estado === 'pendiente' && (
                            <button
                              onClick={() => handleEditar(donacion)}
                              className="p-2 text-amber-600 hover:bg-amber-50 rounded-lg transition-colors"
                              title="Editar"
                            >
                              <FaEdit />
                            </button>
                          )}

                          {/* Recibir (solo pendientes) */}
                          {puede.procesar && donacion.estado === 'pendiente' && (
                            <button
                              onClick={() => setConfirmRecibir(donacion)}
                              disabled={actionLoading === donacion.id}
                              className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50"
                              title="Marcar como recibida"
                            >
                              {actionLoading === donacion.id ? (
                                <FaSpinner className="animate-spin" />
                              ) : (
                                <FaBox />
                              )}
                            </button>
                          )}

                          {/* Procesar (pendientes o recibidas - según backend) */}
                          {puede.procesar && ['pendiente', 'recibida'].includes(donacion.estado) && (
                            <button
                              onClick={() => setConfirmProcesar(donacion)}
                              disabled={actionLoading === donacion.id}
                              className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors disabled:opacity-50"
                              title="Procesar donación (activar stock)"
                            >
                              {actionLoading === donacion.id ? (
                                <FaSpinner className="animate-spin" />
                              ) : (
                                <FaCheck />
                              )}
                            </button>
                          )}

                          {/* Rechazar (pendientes o recibidas) */}
                          {puede.procesar && ['pendiente', 'recibida'].includes(donacion.estado) && (
                            <button
                              onClick={() => setConfirmRechazar(donacion)}
                              disabled={actionLoading === donacion.id}
                              className="p-2 text-orange-600 hover:bg-orange-50 rounded-lg transition-colors disabled:opacity-50"
                              title="Rechazar donación"
                            >
                              <FaTimes />
                            </button>
                          )}

                          {/* Eliminar (solo pendientes) */}
                          {puede.eliminar && donacion.estado === 'pendiente' && (
                            <button
                              onClick={() => setConfirmDelete(donacion)}
                              disabled={actionLoading === donacion.id}
                              className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                              title="Eliminar"
                            >
                              <FaTrash />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Paginación */}
        {totalPages > 1 && (
          <div className="border-t p-4">
            <Pagination
              page={currentPage}
              totalPages={totalPages}
              onPageChange={setCurrentPage}
              totalItems={totalDonaciones}
              pageSize={PAGE_SIZE}
            />
          </div>
        )}
        </>
        )}
      </div>
      </>
      )}

      {/* ========== TAB: CATÁLOGO DE PRODUCTOS DONACIONES ========== */}
      {activeTab === 'catalogo' && (
        <>
          {/* Banner informativo */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4 mb-6">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <FaClipboardList className="text-blue-600 text-xl" />
              </div>
              <div>
                <h3 className="font-semibold text-blue-800">Catálogo Independiente de Productos de Donaciones</h3>
                <p className="text-sm text-blue-700 mt-1">
                  Este catálogo es <strong>completamente separado</strong> del catálogo principal de la farmacia.
                  Los productos de donaciones pueden tener <strong>claves y nombres diferentes</strong> a los del inventario ordinario.
                  El inventario de donaciones <strong>NO se mezcla</strong> con el inventario principal.
                </p>
              </div>
            </div>
          </div>

          {/* Barra de acciones del catálogo */}
          <div className="bg-white rounded-xl shadow-sm border p-4 mb-6">
            <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center justify-between">
              {/* Búsqueda */}
              <div className="relative flex-1 max-w-md">
                <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Buscar por clave o nombre..."
                  value={searchCatalogo}
                  onChange={(e) => setSearchCatalogo(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                />
              </div>

              {/* Botones de acción */}
              <div className="flex flex-wrap gap-2 items-center">
                {/* Descargar Plantilla */}
                <button
                  onClick={handleDescargarPlantillaCatalogo}
                  disabled={exportingCatalogo}
                  className="flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
                  title="Descargar plantilla Excel para importar productos"
                >
                  {exportingCatalogo ? <FaSpinner className="animate-spin" /> : <FaDownload />}
                  Plantilla
                </button>

                {/* Importar */}
                {puede.crear && (
                  <>
                    <input
                      type="file"
                      ref={catalogoFileInputRef}
                      onChange={handleImportarCatalogo}
                      accept=".xlsx,.xls"
                      className="hidden"
                    />
                    <button
                      onClick={() => catalogoFileInputRef.current?.click()}
                      disabled={importingCatalogo}
                      className="flex items-center gap-2 px-3 py-2 text-sm border border-blue-300 text-blue-700 rounded-lg hover:bg-blue-50 transition-colors disabled:opacity-50"
                      title="Importar productos desde Excel"
                    >
                      {importingCatalogo ? <FaSpinner className="animate-spin" /> : <FaFileImport />}
                      Importar
                    </button>
                  </>
                )}

                {/* Exportar Catálogo */}
                <button
                  onClick={handleExportarCatalogo}
                  disabled={exportingCatalogo || productosDonacion.length === 0}
                  className="flex items-center gap-2 px-3 py-2 text-sm border border-green-300 text-green-700 rounded-lg hover:bg-green-50 transition-colors disabled:opacity-50"
                  title="Exportar catálogo actual a Excel"
                >
                  {exportingCatalogo ? <FaSpinner className="animate-spin" /> : <FaFileExport />}
                  Exportar
                </button>

                {/* Agregar Producto */}
                {puede.crear && (
                  <button
                    onClick={() => {
                      setCatalogoForm({ clave: '', nombre: '', descripcion: '', unidad_medida: 'PIEZA', presentacion: '', activo: true, notas: '' });
                      setEditingProductoDonacion(null);
                      setShowCatalogoModal(true);
                    }}
                    className="flex items-center gap-2 px-4 py-2 text-white rounded-lg transition-colors"
                    style={{ backgroundColor: COLORS.primary }}
                  >
                    <FaPlus /> Agregar Producto
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Tabla del catálogo */}
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            {loadingCatalogo ? (
              <div className="flex items-center justify-center py-20">
                <FaSpinner className="animate-spin text-4xl text-theme-primary" />
              </div>
            ) : productosDonacion.length === 0 ? (
              <div className="text-center py-20 text-gray-500">
                <FaClipboardList className="mx-auto text-5xl mb-4 opacity-30" />
                <p>No hay productos en el catálogo de donaciones</p>
                <p className="text-sm mt-2">Agrega productos para poder registrar donaciones</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Clave</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Nombre</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Unidad</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Presentación</th>
                      <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Estado</th>
                      <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Acciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {productosDonacion
                      .filter(p => 
                        !searchCatalogo || 
                        p.clave?.toLowerCase().includes(searchCatalogo.toLowerCase()) ||
                        p.nombre?.toLowerCase().includes(searchCatalogo.toLowerCase())
                      )
                      .map((producto) => (
                        <tr key={producto.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-mono font-medium text-primary">{producto.clave}</td>
                          <td className="px-4 py-3">{producto.nombre}</td>
                          <td className="px-4 py-3 text-gray-600">{producto.unidad_medida}</td>
                          <td className="px-4 py-3 text-gray-600">{producto.presentacion || '-'}</td>
                          <td className="px-4 py-3 text-center">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              producto.activo 
                                ? 'bg-green-100 text-green-800' 
                                : 'bg-gray-100 text-gray-600'
                            }`}>
                              {producto.activo ? 'Activo' : 'Inactivo'}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center justify-center gap-2">
                              {puede.editar && (
                                <button
                                  onClick={() => {
                                    setCatalogoForm({
                                      clave: producto.clave,
                                      nombre: producto.nombre,
                                      descripcion: producto.descripcion || '',
                                      unidad_medida: producto.unidad_medida || 'PIEZA',
                                      presentacion: producto.presentacion || '',
                                      activo: producto.activo,
                                      notas: producto.notas || '',
                                    });
                                    setEditingProductoDonacion(producto);
                                    setShowCatalogoModal(true);
                                  }}
                                  className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                  title="Editar"
                                >
                                  <FaEdit />
                                </button>
                              )}
                              {puede.eliminar && (
                                <button
                                  onClick={() => setConfirmDeleteProducto(producto)}
                                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                  title="Eliminar"
                                >
                                  <FaTrash />
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {/* ========== TAB: INVENTARIO DE DONACIONES ========== */}
      {activeTab === 'inventario' && (
        <>
          {/* Banner informativo */}
          <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-xl p-4 mb-6">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <FaHandHoldingMedical className="text-green-600 text-xl" />
              </div>
              <div>
                <h3 className="font-semibold text-green-800">Almacén de Donaciones</h3>
                <p className="text-sm text-green-700 mt-1">
                  Este inventario es <strong>independiente</strong> del inventario principal de la farmacia. 
                  Para dar salida a productos donados, usa el botón <FaHandHoldingMedical className="inline mx-1" /> 
                  en la columna "Entregar". Las salidas se registran en la pestaña "Entregas".
                </p>
              </div>
            </div>
          </div>

          {/* Estadísticas del almacén */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-xl shadow-sm border p-4">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-lg bg-blue-100">
                  <FaBox className="text-blue-600 text-xl" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Total Productos</p>
                  <p className="text-2xl font-bold text-gray-800">{estadisticas.totalProductos}</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-xl shadow-sm border p-4">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-lg bg-green-100">
                  <FaWarehouse className="text-green-600 text-xl" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Total Unidades</p>
                  <p className="text-2xl font-bold text-gray-800">{estadisticas.totalUnidades.toLocaleString()}</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-xl shadow-sm border p-4">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-lg bg-red-100">
                  <FaTimes className="text-red-600 text-xl" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Agotados</p>
                  <p className="text-2xl font-bold text-red-600">{estadisticas.productosAgotados}</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-xl shadow-sm border p-4">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-lg bg-yellow-100">
                  <FaExclamationTriangle className="text-yellow-600 text-xl" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Por Caducar (30 días)</p>
                  <p className="text-2xl font-bold text-yellow-600">{estadisticas.productosPorCaducar}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Barra de búsqueda inventario */}
          <div className="bg-white rounded-xl shadow-sm border p-4 mb-6">
            <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center justify-between">
              <div className="flex flex-1 items-center gap-3">
                <div className="relative flex-1 max-w-md">
                  <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Buscar producto en inventario de donaciones..."
                    value={searchInventario}
                    onChange={(e) => {
                      setSearchInventario(e.target.value);
                      setInventarioPage(1);
                    }}
                    className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                  />
                </div>
                {/* Botón de filtros */}
                <button
                  onClick={() => setShowFiltrosInventario(!showFiltrosInventario)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                    showFiltrosInventario || filtroCaducidadInv || filtroEstadoProducto || filtroDisponibilidad !== 'constock'
                      ? 'bg-theme-primary text-white border-theme-primary'
                      : 'hover:bg-gray-50'
                  }`}
                >
                  <FaFilter />
                  Filtros
                  {(filtroCaducidadInv || filtroEstadoProducto || filtroDisponibilidad !== 'constock') && (
                    <span className="bg-white text-theme-primary text-xs font-bold px-1.5 rounded-full">
                      {[filtroCaducidadInv, filtroEstadoProducto, filtroDisponibilidad !== 'constock' ? '1' : ''].filter(Boolean).length}
                    </span>
                  )}
                </button>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {/* Botones de Exportar Inventario */}
                <div className="flex items-center border rounded-lg overflow-hidden">
                  <button
                    onClick={handleExportarInventarioExcel}
                    disabled={exportingInventario || inventarioDonaciones.length === 0}
                    className="flex items-center gap-2 px-3 py-2 text-sm border-r text-green-700 hover:bg-green-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Exportar a Excel con formato de trazabilidad (respeta filtros)"
                  >
                    {exportingInventario ? <FaSpinner className="animate-spin" /> : <FaFileExcel />}
                    Excel
                  </button>
                  <button
                    onClick={handleExportarInventarioPdf}
                    disabled={exportingInventario || inventarioDonaciones.length === 0}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-red-700 hover:bg-red-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Exportar a PDF con formato profesional (respeta filtros)"
                  >
                    {exportingInventario ? <FaSpinner className="animate-spin" /> : <FaFilePdf />}
                    PDF
                  </button>
                </div>
                
                {/* Botón Entrega Masiva - Solo para admin/farmacia */}
                {puede.procesar && (
                  <button
                    onClick={() => setShowSalidaMasiva(true)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-600 text-white hover:bg-purple-700 transition-colors"
                    title="Registrar múltiples entregas a un destinatario"
                  >
                    <FaShoppingCart /> Entrega Masiva
                  </button>
                )}
                <button
                  onClick={() => cargarInventarioDonaciones()}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-gray-50 transition-colors"
                >
                  <FaHistory /> Actualizar
                </button>
              </div>
            </div>

            {/* Panel de filtros expandible */}
            {showFiltrosInventario && (
              <div className="mt-4 pt-4 border-t grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Filtro de caducidad */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Caducidad</label>
                  <select
                    value={filtroCaducidadInv}
                    onChange={(e) => {
                      setFiltroCaducidadInv(e.target.value);
                      setInventarioPage(1);
                    }}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                  >
                    <option value="">Todos</option>
                    <option value="vencido">🔴 Vencidos</option>
                    <option value="critico">🟠 Crítico (≤30 días)</option>
                    <option value="proximo">🟡 Próximo (31-90 días)</option>
                    <option value="normal">🟢 Vigente (+90 días)</option>
                  </select>
                </div>

                {/* Filtro de estado del producto */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Estado Producto</label>
                  <select
                    value={filtroEstadoProducto}
                    onChange={(e) => {
                      setFiltroEstadoProducto(e.target.value);
                      setInventarioPage(1);
                    }}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                  >
                    <option value="">Todos</option>
                    <option value="bueno">Bueno</option>
                    <option value="regular">Regular</option>
                    <option value="malo">Malo</option>
                  </select>
                </div>

                {/* Filtro de disponibilidad */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Disponibilidad</label>
                  <select
                    value={filtroDisponibilidad}
                    onChange={(e) => {
                      setFiltroDisponibilidad(e.target.value);
                      setInventarioPage(1);
                    }}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                  >
                    <option value="todos">Todos</option>
                    <option value="constock">Con stock disponible</option>
                    <option value="agotado">Agotados</option>
                  </select>
                </div>

                {/* Botón limpiar filtros */}
                <div className="md:col-span-3 flex justify-end">
                  <button
                    onClick={() => {
                      setFiltroCaducidadInv('');
                      setFiltroEstadoProducto('');
                      setFiltroDisponibilidad('constock');
                      setInventarioPage(1);
                    }}
                    className="text-sm text-gray-600 hover:text-gray-800 flex items-center gap-1"
                  >
                    <FaTimes className="text-xs" /> Limpiar filtros
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Tabla de inventario */}
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            {loadingInventario ? (
              <div className="flex items-center justify-center py-20">
                <FaSpinner className="animate-spin text-4xl text-theme-primary" />
              </div>
            ) : inventarioDonaciones.length === 0 ? (
              <div className="text-center py-20 text-gray-500">
                <FaWarehouse className="mx-auto text-5xl mb-4 opacity-30" />
                <p>No hay productos en el inventario de donaciones</p>
                <p className="text-sm mt-2">Procesa una donación para agregar productos al inventario</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Producto</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Donación</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Lote</th>
                      <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Recibido</th>
                      <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Disponible</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Caducidad</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Estado</th>
                      {puede.procesar && (
                        <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Entregar</th>
                      )}
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {inventarioDonaciones.map((item) => {
                      const semaforo = getSemaforoCaducidad(item.fecha_caducidad);
                      const esCritico = item.cantidad_disponible === 0;
                      const rowBg = esCritico 
                        ? 'bg-red-50' 
                        : semaforo.estado === 'vencido' 
                          ? 'bg-red-50' 
                          : semaforo.estado === 'critico'
                            ? 'bg-orange-50'
                            : semaforo.estado === 'proximo'
                              ? 'bg-yellow-50'
                              : '';
                      return (
                        <tr key={item.id} className={`hover:bg-gray-50 ${rowBg}`}>
                          <td className="px-4 py-3">
                            <span className="font-medium">{item.producto_codigo}</span>
                            <span className="block text-xs text-gray-500">{item.producto_nombre}</span>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600">
                            {item.donacion_numero || `DON-${item.donacion}`}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600">{item.numero_lote || '-'}</td>
                          <td className="px-4 py-3 text-center text-gray-600">{item.cantidad}</td>
                          <td className="px-4 py-3 text-center">
                            <span className={`font-bold ${item.cantidad_disponible > 0 ? 'text-green-600' : 'text-red-500'}`}>
                              {item.cantidad_disponible}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${semaforo.clase}`}>
                                <span>{semaforo.icono}</span>
                                <span>{semaforo.label}</span>
                              </span>
                              <span className="text-xs text-gray-500">
                                {formatFecha(item.fecha_caducidad)}
                              </span>
                            </div>
                            {semaforo.dias !== undefined && semaforo.dias >= 0 && semaforo.dias <= 90 && (
                              <span className="text-xs text-gray-400 block">
                                {semaforo.dias} días restantes
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 capitalize text-sm text-gray-600">{item.estado_producto}</td>
                          {puede.procesar && (
                            <td className="px-4 py-3 text-center">
                              {item.cantidad_disponible > 0 ? (
                                <button
                                  onClick={() => handleAbrirSalida(item, { numero: item.donacion_numero || `DON-${item.donacion}` })}
                                  className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                                  title="Registrar entrega"
                                >
                                  <FaHandHoldingMedical />
                                </button>
                              ) : (
                                <span className="text-gray-400 text-xs">Agotado</span>
                              )}
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Paginación inventario */}
            {inventarioTotalPages > 1 && (
              <div className="border-t p-4">
                <Pagination
                  page={inventarioPage}
                  totalPages={inventarioTotalPages}
                  onPageChange={setInventarioPage}
                  totalItems={inventarioDonaciones.length}
                  pageSize={PAGE_SIZE}
                />
              </div>
            )}
          </div>
        </>
      )}

      {/* ========== TAB: HISTORIAL DE ENTREGAS ========== */}
      {activeTab === 'entregas' && (
        <>
          {/* Barra de filtros y acciones entregas */}
          <div className="bg-white rounded-xl shadow-sm border p-4 mb-6">
            {/* Fila 1: Filtros principales */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-4">
              {/* Búsqueda */}
              <div className="relative">
                <label className="block text-xs font-medium text-gray-500 mb-1">Buscar</label>
                <div className="relative">
                  <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Destinatario..."
                    value={searchEntregas}
                    onChange={(e) => {
                      setSearchEntregas(e.target.value);
                      setEntregasPage(1);
                    }}
                    className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                  />
                </div>
              </div>
              
              {/* Filtro por Centro */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Centro Destino</label>
                <select
                  value={filtroCentroEntregas}
                  onChange={(e) => {
                    setFiltroCentroEntregas(e.target.value);
                    setEntregasPage(1);
                  }}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary bg-white"
                >
                  <option value="">Todos los centros</option>
                  {centros.map(centro => (
                    <option key={centro.id} value={centro.id}>
                      {centro.nombre}
                    </option>
                  ))}
                </select>
              </div>
              
              {/* Fecha Desde */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Desde</label>
                <input
                  type="date"
                  value={filtroFechaDesdeEntregas}
                  onChange={(e) => {
                    setFiltroFechaDesdeEntregas(e.target.value);
                    setEntregasPage(1);
                  }}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary bg-white"
                />
              </div>
              
              {/* Fecha Hasta */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Hasta</label>
                <input
                  type="date"
                  value={filtroFechaHastaEntregas}
                  onChange={(e) => {
                    setFiltroFechaHastaEntregas(e.target.value);
                    setEntregasPage(1);
                  }}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary bg-white"
                />
              </div>
              
              {/* Botón Limpiar Filtros */}
              <div className="flex items-end">
                <button
                  onClick={() => {
                    setSearchEntregas('');
                    setFiltroCentroEntregas('');
                    setFiltroFechaDesdeEntregas('');
                    setFiltroFechaHastaEntregas('');
                    setEntregasPage(1);
                  }}
                  className="w-full px-3 py-2 text-gray-600 border rounded-lg hover:bg-gray-50 transition-colors flex items-center justify-center gap-2"
                >
                  <FaTimes className="text-sm" />
                  Limpiar
                </button>
              </div>
            </div>
            
            {/* Fila 2: Botones de acción */}
            <div className="flex flex-wrap items-center justify-end gap-2 pt-3 border-t">
              {/* Botón Actualizar */}
              <button
                onClick={() => cargarTodasEntregas()}
                className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-gray-50 transition-colors"
              >
                <FaHistory /> Actualizar
              </button>
              
              {/* Botón Exportar Excel */}
              <button
                onClick={handleExportarEntregas}
                disabled={exportingEntregas || todasEntregas.length === 0}
                className="flex items-center gap-2 px-4 py-2 rounded-lg border text-green-700 border-green-300 hover:bg-green-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {exportingEntregas ? (
                  <FaSpinner className="animate-spin" />
                ) : (
                  <FaFileExport />
                )}
                Exportar
              </button>
            </div>
          </div>

          {/* Tabla de entregas - Vista Agrupada para salidas masivas */}
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            {loadingEntregas ? (
              <div className="flex items-center justify-center py-20">
                <FaSpinner className="animate-spin text-4xl text-theme-primary" />
              </div>
            ) : entregasAgrupadas.length === 0 ? (
              <div className="text-center py-20 text-gray-500">
                <FaHandHoldingMedical className="mx-auto text-5xl mb-4 opacity-30" />
                <p>No hay entregas registradas</p>
                <p className="text-sm mt-2">Las entregas aparecerán aquí cuando se registren desde el inventario</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Fecha</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Centro Destino</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Productos</th>
                      <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Cantidad</th>
                      <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Estado</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Entregado por</th>
                      <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Acciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {entregasAgrupadas.map((grupo) => {
                      const estaExpandido = gruposExpandidos.has(grupo.clave);
                      const esGrupo = grupo.entregas.length > 1;
                      
                      return (
                        <React.Fragment key={grupo.clave}>
                          {/* Fila del grupo/entrega */}
                          <tr className={`hover:bg-gray-50 ${esGrupo ? 'bg-indigo-50/30' : ''}`}>
                            <td className="px-4 py-3 text-sm text-gray-600">
                              {new Date(grupo.fecha_entrega).toLocaleString('es-MX', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                <FaBuilding className="text-theme-primary" />
                                <span className="font-medium">{grupo.centro_destino_nombre || grupo.destinatario || '-'}</span>
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              {esGrupo ? (
                                <button
                                  onClick={() => toggleGrupo(grupo.clave)}
                                  className="flex items-center gap-2 text-left font-medium text-indigo-700 hover:text-indigo-900"
                                >
                                  <FaChevronDown className={`transition-transform ${estaExpandido ? 'rotate-180' : ''}`} />
                                  <span className="bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded-full text-xs">
                                    {grupo.entregas.length} productos
                                  </span>
                                </button>
                              ) : (
                                <span className="font-medium">{grupo.entregas[0]?.producto_nombre || '-'}</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <span className="font-bold text-primary">{grupo.totalCantidad}</span>
                            </td>
                            <td className="px-4 py-3 text-center">
                              {grupo.todosFinalizados ? (
                                <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                  <FaCheckCircle className="text-green-600" />
                                  Entregado
                                </span>
                              ) : grupo.algunoFinalizado ? (
                                <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                                  <FaClock className="text-orange-600" />
                                  Parcial
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                  <FaClock className="text-yellow-600" />
                                  Pendiente
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">{grupo.entregado_por_nombre || '-'}</td>
                            <td className="px-4 py-3 text-center">
                              <div className="flex items-center justify-center gap-2">
                                {/* Si es grupo, mostrar acciones de grupo */}
                                {esGrupo && (
                                  <>
                                    <button
                                      onClick={() => toggleGrupo(grupo.clave)}
                                      className="p-1.5 text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                                      title={estaExpandido ? "Colapsar" : "Ver productos"}
                                    >
                                      <FaEye />
                                    </button>
                                    {/* Botón Hoja de Entrega para grupos pendientes */}
                                    {!grupo.todosFinalizados && (
                                      <button
                                        onClick={() => handleDescargarReciboSalida(grupo.entregas[0], false, grupo)}
                                        className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                        title="Hoja de Entrega"
                                      >
                                        <FaFilePdf />
                                      </button>
                                    )}
                                    {/* Botón finalizar grupo completo */}
                                    {!grupo.todosFinalizados && puede.procesar && (
                                      <button
                                        onClick={() => setConfirmFinalizarGrupo(grupo)}
                                        disabled={finalizandoGrupo}
                                        className="p-1.5 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                                        title="Confirmar entrega completa"
                                      >
                                        {finalizandoGrupo ? (
                                          <FaSpinner className="animate-spin" />
                                        ) : (
                                          <FaCheck />
                                        )}
                                      </button>
                                    )}
                                    {/* Botón Eliminar grupo pendiente */}
                                    {!grupo.todosFinalizados && puede.eliminar && (
                                      <button
                                        onClick={() => setConfirmEliminarEntrega(grupo.entregas[0])}
                                        className="p-1.5 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                        title="Eliminar"
                                      >
                                        <FaTrash />
                                      </button>
                                    )}
                                    {/* Comprobante si ya está entregado */}
                                    {grupo.todosFinalizados && (
                                      <button
                                        onClick={() => handleDescargarReciboSalida(grupo.entregas[0], true, grupo)}
                                        className="p-1.5 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                                        title="Comprobante"
                                      >
                                        <FaCheckCircle />
                                      </button>
                                    )}
                                  </>
                                )}
                                {/* Si es entrega individual, mostrar acciones normales */}
                                {!esGrupo && (
                                  <>
                                    <button
                                      onClick={() => setDetalleEntregaModal(grupo.entregas[0])}
                                      className="p-1.5 text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                                      title="Ver detalles"
                                    >
                                      <FaEye />
                                    </button>
                                    {!grupo.todosFinalizados && (
                                      <button
                                        onClick={() => handleDescargarReciboSalida(grupo.entregas[0], false, grupo)}
                                        className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                        title="Hoja de Entrega"
                                      >
                                        <FaFilePdf />
                                      </button>
                                    )}
                                    {!grupo.todosFinalizados && puede.procesar && (
                                      <button
                                        onClick={() => setConfirmFinalizarEntrega(grupo.entregas[0])}
                                        disabled={actionLoading === grupo.entregas[0].id}
                                        className="p-1.5 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                                        title="Confirmar entrega"
                                      >
                                        <FaCheck />
                                      </button>
                                    )}
                                    {!grupo.todosFinalizados && puede.eliminar && (
                                      <button
                                        onClick={() => setConfirmEliminarEntrega(grupo.entregas[0])}
                                        className="p-1.5 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                        title="Eliminar"
                                      >
                                        <FaTrash />
                                      </button>
                                    )}
                                    {grupo.todosFinalizados && (
                                      <button
                                        onClick={() => handleDescargarReciboSalida(grupo.entregas[0], true, grupo)}
                                        className="p-1.5 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                                        title="Comprobante"
                                      >
                                        <FaCheckCircle />
                                      </button>
                                    )}
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                          
                          {/* Filas expandidas del grupo (productos individuales) */}
                          {esGrupo && estaExpandido && grupo.entregas.map((entrega, idx) => (
                            <tr key={entrega.id} className="bg-gray-50/70 border-l-4 border-indigo-300">
                              <td className="px-4 py-2 text-sm text-gray-500 pl-8">
                                <div className="flex items-center gap-1">
                                  <span className="text-gray-400">└</span>
                                  <span className="bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded text-xs font-mono">
                                    #{idx + 1}
                                  </span>
                                </div>
                              </td>
                              <td className="px-4 py-2 text-sm text-gray-500">
                                {entrega.numero_lote ? (
                                  <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-xs">
                                    Lote: {entrega.numero_lote}
                                  </span>
                                ) : '-'}
                              </td>
                              <td className="px-4 py-2">
                                <div>
                                  <span className="font-medium text-sm text-gray-800">{entrega.producto_nombre || '-'}</span>
                                  {entrega.producto_clave && (
                                    <span className="ml-2 text-xs text-gray-500">({entrega.producto_clave})</span>
                                  )}
                                </div>
                              </td>
                              <td className="px-4 py-2 text-center">
                                <span className="font-bold text-primary text-sm">{entrega.cantidad}</span>
                              </td>
                              <td className="px-4 py-2 text-center">
                                {entrega.estado_entrega === 'entregado' || entrega.finalizado ? (
                                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                    <FaCheckCircle className="text-green-600 text-xs" />
                                    <span>OK</span>
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                    <FaClock className="text-yellow-600 text-xs" />
                                    <span>Pend.</span>
                                  </span>
                                )}
                              </td>
                              <td className="px-4 py-2 text-sm text-gray-500">
                                {entrega.entregado_por_nombre || '-'}
                              </td>
                              <td className="px-4 py-2 text-center">
                                <div className="flex items-center justify-center gap-1">
                                  <button
                                    onClick={() => setDetalleEntregaModal(entrega)}
                                    className="p-1 text-indigo-600 hover:bg-indigo-50 rounded transition-colors"
                                    title="Ver detalles"
                                  >
                                    <FaEye className="text-xs" />
                                  </button>
                                  {!(entrega.estado_entrega === 'entregado' || entrega.finalizado) && puede.procesar && (
                                    <button
                                      onClick={() => setConfirmFinalizarEntrega(entrega)}
                                      disabled={actionLoading === entrega.id}
                                      className="p-1 text-green-600 hover:bg-green-50 rounded transition-colors"
                                      title="Confirmar"
                                    >
                                      {actionLoading === entrega.id ? (
                                        <FaSpinner className="animate-spin text-xs" />
                                      ) : (
                                        <FaCheck className="text-xs" />
                                      )}
                                    </button>
                                  )}
                                  {!(entrega.estado_entrega === 'entregado' || entrega.finalizado) && puede.eliminar && (
                                    <button
                                      onClick={() => setConfirmEliminarEntrega(entrega)}
                                      disabled={actionLoading === entrega.id}
                                      className="p-1 text-red-600 hover:bg-red-50 rounded transition-colors"
                                      title="Eliminar"
                                    >
                                      <FaTrash className="text-xs" />
                                    </button>
                                  )}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Paginación entregas */}
            {entregasTotalPages > 1 && (
              <div className="border-t p-4">
                <Pagination
                  page={entregasPage}
                  totalPages={entregasTotalPages}
                  onPageChange={setEntregasPage}
                  totalItems={todasEntregas.length}
                  pageSize={PAGE_SIZE}
                />
              </div>
            )}
          </div>
        </>
      )}

      {/* Modal de Creación/Edición */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div
              className="px-6 py-4 border-b flex items-center justify-between"
              style={{ backgroundColor: COLORS.primary }}
            >
              <h2 className="text-lg font-semibold text-white">
                {editingDonacion ? 'Editar Donación' : 'Nueva Donación'}
              </h2>
              <button
                onClick={() => {
                  setShowModal(false);
                  resetForm();
                }}
                className="text-white/80 hover:text-white transition-colors"
              >
                <FaTimes size={20} />
              </button>
            </div>

            {/* Contenido */}
            <div className="flex-1 overflow-y-auto p-6">
              {/* Datos principales - Simplificados */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <FaGift /> Datos de la Donación
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Número *</label>
                    <input
                      type="text"
                      value={formData.numero}
                      onChange={(e) => setFormData({ ...formData, numero: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                      placeholder="DON-001"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">
                      Donante *
                    </label>
                    <input
                      type="text"
                      value={formData.donante_nombre}
                      onChange={(e) => setFormData({ ...formData, donante_nombre: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                      placeholder="Nombre o razón social"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Tipo</label>
                    <select
                      value={formData.donante_tipo}
                      onChange={(e) => setFormData({ ...formData, donante_tipo: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    >
                      {TIPOS_DONANTE.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Fecha Donación *</label>
                    <input
                      type="date"
                      value={formData.fecha_donacion}
                      onChange={(e) => setFormData({ ...formData, fecha_donacion: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Centro Destino *</label>
                    <select
                      value={formData.centro_destino}
                      onChange={(e) => setFormData({ ...formData, centro_destino: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    >
                      <option value="">Seleccionar centro</option>
                      {centros.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.nombre}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Notas</label>
                    <input
                      type="text"
                      value={formData.notas}
                      onChange={(e) => setFormData({ ...formData, notas: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                      placeholder="Observaciones (opcional)"
                    />
                  </div>
                </div>
              </div>

              {/* Productos donados */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <FaBox /> Productos Donados (Catálogo Independiente)
                </h3>

                {/* Formulario para agregar producto */}
                <div className="bg-gray-50 rounded-lg p-4 mb-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3">
                    <div className="lg:col-span-2">
                      <label className="block text-xs font-medium text-gray-600 mb-1">Producto Donación *</label>
                      <select
                        value={detalleForm.producto_donacion}
                        onChange={(e) => setDetalleForm({ ...detalleForm, producto_donacion: e.target.value })}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary"
                      >
                        <option value="">Seleccionar producto</option>
                        {productosDonacion.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.clave} - {p.nombre}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Lote *</label>
                      <input
                        type="text"
                        required
                        value={detalleForm.numero_lote}
                        onChange={(e) => setDetalleForm({ ...detalleForm, numero_lote: e.target.value })}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary"
                        placeholder="Nº lote"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Cantidad *</label>
                      <input
                        type="number"
                        min="1"
                        value={detalleForm.cantidad}
                        onChange={(e) => setDetalleForm({ ...detalleForm, cantidad: e.target.value })}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary"
                        placeholder="0"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Caducidad *</label>
                      <input
                        type="date"
                        required
                        value={detalleForm.fecha_caducidad}
                        onChange={(e) => setDetalleForm({ ...detalleForm, fecha_caducidad: e.target.value })}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary"
                      />
                    </div>
                    <div className="flex items-end">
                      <button
                        type="button"
                        onClick={handleAgregarDetalle}
                        className="w-full px-4 py-2 rounded-lg text-white transition-colors"
                        style={{ backgroundColor: COLORS.primary }}
                      >
                        <FaPlus className="inline mr-1" /> Agregar
                      </button>
                    </div>
                  </div>
                </div>

                {/* Lista de productos agregados */}
                {formData.detalles.length > 0 ? (
                  <div className="border rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 border-b">
                        <tr>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">Producto</th>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">Lote</th>
                          <th className="px-3 py-2 text-center font-medium text-gray-600">Cantidad</th>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">Caducidad</th>
                          <th className="px-3 py-2 text-center font-medium text-gray-600"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {formData.detalles.map((d, idx) => (
                          <tr key={d.tempId || d.id || idx} className="hover:bg-gray-50">
                            <td className="px-3 py-2">
                              <span className="font-medium">{d.producto_clave}</span>
                              <span className="block text-xs text-gray-500">{d.producto_nombre}</span>
                            </td>
                            <td className="px-3 py-2 text-gray-600">{d.numero_lote || '-'}</td>
                            <td className="px-3 py-2 text-center font-medium">{d.cantidad}</td>
                            <td className="px-3 py-2 text-gray-600">{d.fecha_caducidad || '-'}</td>
                            <td className="px-3 py-2 text-center">
                              <button
                                onClick={() => handleEliminarDetalle(idx)}
                                className="p-1 text-red-500 hover:bg-red-50 rounded transition-colors"
                              >
                                <FaTrash />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-400 border-2 border-dashed rounded-lg">
                    <FaBox className="mx-auto text-3xl mb-2" />
                    <p>No hay productos agregados</p>
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-between items-center">
              {/* Mensaje de ayuda si no hay productos */}
              {formData.detalles.length === 0 && (
                <p className="text-sm text-amber-600 flex items-center gap-1">
                  <FaExclamationTriangle className="text-amber-500" />
                  Agregue al menos un producto para guardar
                </p>
              )}
              {formData.detalles.length > 0 && <div />}
              
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowModal(false);
                    resetForm();
                  }}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-100 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleGuardar}
                  disabled={actionLoading === 'guardar' || formData.detalles.length === 0}
                  className="px-6 py-2 rounded-lg text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  style={{ backgroundColor: formData.detalles.length === 0 ? '#9CA3AF' : COLORS.primary }}
                  title={formData.detalles.length === 0 ? 'Debe agregar al menos un producto' : ''}
                >
                  {actionLoading === 'guardar' ? (
                    <>
                      <FaSpinner className="animate-spin" /> Guardando...
                    </>
                  ) : (
                    <>Guardar Donación</>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Ver Detalle */}
      {showDetalleModal && viewingDonacion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div
              className="px-6 py-4 border-b flex items-center justify-between"
              style={{ backgroundColor: COLORS.primary }}
            >
              <h2 className="text-lg font-semibold text-white">
                Detalle de Donación {viewingDonacion.numero || `DON-${viewingDonacion.id}`}
              </h2>
              <button
                onClick={() => {
                  setShowDetalleModal(false);
                  setViewingDonacion(null);
                }}
                className="text-white/80 hover:text-white transition-colors"
              >
                <FaTimes size={20} />
              </button>
            </div>

            {/* Contenido */}
            <div className="flex-1 overflow-y-auto p-6">
              {/* Estado */}
              <div className="mb-6 flex items-center gap-4">
                <span
                  className={`px-4 py-2 rounded-full text-sm font-medium ${
                    ESTADOS_DONACION[viewingDonacion.estado]?.color || 'bg-gray-100'
                  }`}
                >
                  {ESTADOS_DONACION[viewingDonacion.estado]?.icon}{' '}
                  {ESTADOS_DONACION[viewingDonacion.estado]?.label || viewingDonacion.estado}
                </span>
              </div>

              {/* Info principal - Solo campos con datos */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6 bg-gray-50 p-4 rounded-lg">
                <div>
                  <span className="text-sm text-gray-500">Donante</span>
                  <p className="font-medium">{viewingDonacion.donante_nombre}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Tipo</span>
                  <p className="font-medium capitalize">{viewingDonacion.donante_tipo}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Fecha Donación</span>
                  <p className="font-medium">{formatFecha(viewingDonacion.fecha_donacion)}</p>
                </div>
                {viewingDonacion.centro_destino_nombre && (
                  <div>
                    <span className="text-sm text-gray-500">Centro Destino</span>
                    <p className="font-medium">{viewingDonacion.centro_destino_nombre}</p>
                  </div>
                )}
                {viewingDonacion.notas && (
                  <div className="col-span-2">
                    <span className="text-sm text-gray-500">Notas</span>
                    <p className="font-medium text-sm">{viewingDonacion.notas}</p>
                  </div>
                )}
              </div>

              {/* Productos */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">
                  Productos Donados 
                  {viewingDonacion.estado === 'procesada' && (
                    <span className="text-sm font-normal text-gray-500 ml-2">(Stock disponible para entregas)</span>
                  )}
                </h3>
                {viewingDonacion.detalles && viewingDonacion.detalles.length > 0 ? (
                  <div className="border rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 border-b">
                        <tr>
                          <th className="px-4 py-2 text-left font-medium text-gray-600">Producto</th>
                          <th className="px-4 py-2 text-left font-medium text-gray-600">Lote</th>
                          <th className="px-4 py-2 text-center font-medium text-gray-600">Recibido</th>
                          {viewingDonacion.estado === 'procesada' && (
                            <th className="px-4 py-2 text-center font-medium text-gray-600">Disponible</th>
                          )}
                          <th className="px-4 py-2 text-left font-medium text-gray-600">Caducidad</th>
                          <th className="px-4 py-2 text-left font-medium text-gray-600">Estado</th>
                          {viewingDonacion.estado === 'procesada' && puede.procesar && (
                            <th className="px-4 py-2 text-center font-medium text-gray-600">Entregar</th>
                          )}
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {viewingDonacion.detalles.map((d, idx) => (
                          <tr key={d.id || idx}>
                            <td className="px-4 py-2">
                              <span className="font-medium">{d.producto_codigo || d.producto_clave}</span>
                              <span className="block text-xs text-gray-500">{d.producto_nombre}</span>
                            </td>
                            <td className="px-4 py-2 text-gray-600">{d.numero_lote || '-'}</td>
                            <td className="px-4 py-2 text-center font-medium">{d.cantidad}</td>
                            {viewingDonacion.estado === 'procesada' && (
                              <td className="px-4 py-2 text-center">
                                <span className={`font-medium ${d.cantidad_disponible > 0 ? 'text-green-600' : 'text-red-500'}`}>
                                  {d.cantidad_disponible || 0}
                                </span>
                              </td>
                            )}
                            <td className="px-4 py-2 text-gray-600">{formatFecha(d.fecha_caducidad)}</td>
                            <td className="px-4 py-2 capitalize text-gray-600">{d.estado_producto}</td>
                            {viewingDonacion.estado === 'procesada' && puede.procesar && (
                              <td className="px-4 py-2 text-center">
                                {d.cantidad_disponible > 0 ? (
                                  <button
                                    onClick={() => handleAbrirSalida(d, viewingDonacion)}
                                    className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                                    title="Registrar entrega"
                                  >
                                    <FaHandHoldingMedical />
                                  </button>
                                ) : (
                                  <span className="text-gray-400 text-xs">Agotado</span>
                                )}
                              </td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-gray-500">Sin productos registrados</p>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end">
              <button
                onClick={() => {
                  setShowDetalleModal(false);
                  setViewingDonacion(null);
                }}
                className="px-4 py-2 border rounded-lg hover:bg-gray-100 transition-colors"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de confirmación eliminar */}
      <ConfirmModal
        open={!!confirmDelete}
        title="Eliminar Donación"
        message={confirmDelete ? `¿Estás seguro de eliminar la donación "${confirmDelete.numero || 'DON-' + confirmDelete.id}"? Esta acción no se puede deshacer.` : ''}
        confirmText="Eliminar"
        cancelText="Cancelar"
        tone="danger"
        onConfirm={() => confirmDelete && handleEliminar(confirmDelete.id)}
        onCancel={() => setConfirmDelete(null)}
      />

      {/* Modal de confirmación recibir */}
      <ConfirmModal
        open={!!confirmRecibir}
        title="Recibir Donación"
        message={confirmRecibir ? `¿Confirmas que has recibido físicamente la donación "${confirmRecibir.numero || 'DON-' + confirmRecibir.id}"?` : ''}
        confirmText="Confirmar Recepción"
        cancelText="Cancelar"
        tone="info"
        onConfirm={() => confirmRecibir && handleRecibir(confirmRecibir.id)}
        onCancel={() => setConfirmRecibir(null)}
      />

      {/* Modal de confirmación procesar */}
      <ConfirmModal
        open={!!confirmProcesar}
        title="Procesar Donación"
        message={confirmProcesar ? `¿Estás seguro de procesar la donación "${confirmProcesar.numero || 'DON-' + confirmProcesar.id}"? Esto activará el stock disponible en el almacén de donaciones para registrar entregas.` : ''}
        confirmText="Procesar"
        cancelText="Cancelar"
        tone="info"
        onConfirm={() => confirmProcesar && handleProcesar(confirmProcesar.id)}
        onCancel={() => setConfirmProcesar(null)}
      />

      {/* Modal de confirmación procesar TODAS */}
      <ConfirmModal
        open={confirmProcesarTodas}
        title="Procesar Todas las Donaciones"
        message={`¿Estás seguro de procesar TODAS las ${donaciones.filter(d => ['pendiente', 'recibida'].includes(d.estado)).length} donaciones pendientes? Esto activará el stock disponible de todas ellas en el almacén de donaciones.`}
        confirmText="Procesar Todas"
        cancelText="Cancelar"
        tone="warning"
        onConfirm={handleProcesarTodas}
        onCancel={() => setConfirmProcesarTodas(false)}
      />

      {/* Modal de rechazo con motivo */}
      {confirmRechazar && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
            <div className="px-6 py-4 border-b bg-red-600">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <FaTimes /> Rechazar Donación
              </h2>
            </div>
            <div className="p-6">
              <p className="text-gray-700 mb-4">
                ¿Estás seguro de rechazar la donación <strong>"{confirmRechazar.numero || 'DON-' + confirmRechazar.id}"</strong>?
                Esta acción no se puede deshacer.
              </p>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Motivo del rechazo *
                </label>
                <textarea
                  value={motivoRechazo}
                  onChange={(e) => setMotivoRechazo(e.target.value)}
                  rows={3}
                  className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-red-500"
                  placeholder="Indica el motivo del rechazo..."
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end gap-3">
              <button
                onClick={() => {
                  setConfirmRechazar(null);
                  setMotivoRechazo('');
                }}
                className="px-4 py-2 border rounded-lg hover:bg-gray-100 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={() => {
                  if (!motivoRechazo.trim()) {
                    toast.error('Debes indicar un motivo para rechazar');
                    return;
                  }
                  handleRechazar(confirmRechazar.id, motivoRechazo);
                  setMotivoRechazo('');
                }}
                disabled={actionLoading === confirmRechazar.id}
                className="px-4 py-2 rounded-lg text-white bg-red-600 hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {actionLoading === confirmRechazar.id ? (
                  <>
                    <FaSpinner className="animate-spin" /> Rechazando...
                  </>
                ) : (
                  'Rechazar Donación'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Registrar Salida/Entrega */}
      {showSalidaModal && salidaDetalle && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
            {/* Header */}
            <div
              className="px-6 py-4 border-b flex items-center justify-between"
              style={{ backgroundColor: COLORS.primary }}
            >
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <FaHandHoldingMedical /> Registrar Entrega
              </h2>
              <button
                onClick={() => {
                  setShowSalidaModal(false);
                  setSalidaDetalle(null);
                }}
                className="text-white/80 hover:text-white transition-colors"
              >
                <FaTimes size={20} />
              </button>
            </div>

            {/* Contenido */}
            <div className="p-6">
              {/* Info del producto */}
              <div className="bg-gray-50 rounded-lg p-4 mb-4">
                <p className="text-sm text-gray-500">Producto</p>
                <p className="font-semibold">{salidaDetalle.producto_nombre}</p>
                <p className="text-sm text-gray-600">
                  Donación: {salidaDetalle.donacion_numero} | Lote: {salidaDetalle.numero_lote || 'N/A'}
                </p>
                <p className="text-sm mt-2">
                  Stock disponible: <span className="font-bold text-green-600">{salidaDetalle.cantidad_disponible}</span>
                </p>
              </div>

              {/* Formulario */}
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Cantidad a entregar *
                  </label>
                  <input
                    type="number"
                    min="1"
                    max={salidaDetalle.cantidad_disponible}
                    value={salidaForm.cantidad}
                    onChange={(e) => setSalidaForm({ ...salidaForm, cantidad: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Destinatario *
                  </label>
                  <select
                    value={salidaForm.destinatario}
                    onChange={(e) => setSalidaForm({ ...salidaForm, destinatario: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:outline-none"
                    style={{ '--tw-ring-color': COLORS.primary }}
                  >
                    <option value="">-- Seleccionar centro destino --</option>
                    {centros.map((centro) => (
                      <option key={centro.id} value={centro.nombre}>
                        {centro.nombre}
                      </option>
                    ))}
                    <option value="Otro">Otro (especificar en notas)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Motivo
                  </label>
                  <input
                    type="text"
                    value={salidaForm.motivo}
                    onChange={(e) => setSalidaForm({ ...salidaForm, motivo: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    placeholder="Motivo de la entrega"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Notas
                  </label>
                  <textarea
                    value={salidaForm.notas}
                    onChange={(e) => setSalidaForm({ ...salidaForm, notas: e.target.value })}
                    rows={2}
                    className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    placeholder="Observaciones adicionales..."
                  />
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowSalidaModal(false);
                  setSalidaDetalle(null);
                }}
                className="px-4 py-2 border rounded-lg hover:bg-gray-100 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleRegistrarSalida}
                disabled={actionLoading === 'salida'}
                className="px-6 py-2 rounded-lg text-white transition-colors disabled:opacity-50 flex items-center gap-2"
                style={{ backgroundColor: COLORS.primary }}
              >
                {actionLoading === 'salida' ? (
                  <>
                    <FaSpinner className="animate-spin" /> Registrando...
                  </>
                ) : (
                  <>
                    <FaHandHoldingMedical /> Registrar Entrega
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Historial de Entregas */}
      {showHistorialModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div
              className="px-6 py-4 border-b flex items-center justify-between"
              style={{ backgroundColor: COLORS.primary }}
            >
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <FaHistory /> Historial de Entregas
              </h2>
              <button
                onClick={() => {
                  setShowHistorialModal(false);
                  setHistorialSalidas([]);
                }}
                className="text-white/80 hover:text-white transition-colors"
              >
                <FaTimes size={20} />
              </button>
            </div>

            {/* Contenido */}
            <div className="flex-1 overflow-y-auto p-6">
              {loadingSalidas ? (
                <div className="flex items-center justify-center py-12">
                  <FaSpinner className="animate-spin text-3xl text-theme-primary" />
                </div>
              ) : historialSalidas.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <FaHistory className="mx-auto text-4xl mb-3 opacity-30" />
                  <p>No hay entregas registradas para esta donación</p>
                </div>
              ) : (
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="px-4 py-3 text-left font-medium text-gray-600">Fecha</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600">Producto</th>
                        <th className="px-4 py-3 text-center font-medium text-gray-600">Cantidad</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600">Destinatario</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600">Entregado por</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {historialSalidas.map((salida) => (
                        <tr key={salida.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-gray-600">
                            {new Date(salida.fecha_entrega).toLocaleString('es-MX', {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </td>
                          <td className="px-4 py-3 font-medium">{salida.producto_nombre || '-'}</td>
                          <td className="px-4 py-3 text-center font-bold text-primary">{salida.cantidad}</td>
                          <td className="px-4 py-3">{salida.destinatario}</td>
                          <td className="px-4 py-3 text-gray-600">{salida.entregado_por_nombre || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end">
              <button
                onClick={() => {
                  setShowHistorialModal(false);
                  setHistorialSalidas([]);
                }}
                className="px-4 py-2 border rounded-lg hover:bg-gray-100 transition-colors"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Modal de Entrega Masiva de Donaciones */}
      {showSalidaMasiva && (
        <SalidaMasivaDonaciones
          onClose={() => setShowSalidaMasiva(false)}
          onSuccess={() => {
            // Recargar inventario y entregas después de procesar
            cargarInventarioDonaciones();
            cargarTodasEntregas();
          }}
        />
      )}

      {/* ========== MODAL: Crear/Editar Producto del Catálogo de Donaciones ========== */}
      {showCatalogoModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b bg-gradient-to-r from-blue-600 to-indigo-600 rounded-t-xl">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <FaClipboardList />
                {editingProductoDonacion ? 'Editar Producto' : 'Nuevo Producto de Donación'}
              </h2>
              <p className="text-blue-100 text-sm mt-1">
                Catálogo independiente (no afecta inventario principal)
              </p>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Clave *
                  </label>
                  <input
                    type="text"
                    value={catalogoForm.clave}
                    onChange={(e) => setCatalogoForm({ ...catalogoForm, clave: e.target.value.toUpperCase() })}
                    className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary font-mono"
                    placeholder="Ej: DON001"
                    disabled={!!editingProductoDonacion}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Unidad de Medida
                  </label>
                  <select
                    value={catalogoForm.unidad_medida}
                    onChange={(e) => setCatalogoForm({ ...catalogoForm, unidad_medida: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                  >
                    <option value="PIEZA">PIEZA</option>
                    <option value="CAJA">CAJA</option>
                    <option value="FRASCO">FRASCO</option>
                    <option value="SOBRE">SOBRE</option>
                    <option value="AMPOLLETA">AMPOLLETA</option>
                    <option value="TUBO">TUBO</option>
                    <option value="LITRO">LITRO</option>
                    <option value="ML">ML</option>
                    <option value="GRAMO">GRAMO</option>
                    <option value="KG">KG</option>
                  </select>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre del Producto *
                </label>
                <input
                  type="text"
                  value={catalogoForm.nombre}
                  onChange={(e) => setCatalogoForm({ ...catalogoForm, nombre: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                  placeholder="Nombre completo del producto"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Presentación
                </label>
                <input
                  type="text"
                  value={catalogoForm.presentacion}
                  onChange={(e) => setCatalogoForm({ ...catalogoForm, presentacion: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                  placeholder="Ej: Caja con 30 tabletas de 500mg"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descripción
                </label>
                <textarea
                  value={catalogoForm.descripcion}
                  onChange={(e) => setCatalogoForm({ ...catalogoForm, descripcion: e.target.value })}
                  rows={2}
                  className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                  placeholder="Descripción adicional del producto"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Notas
                </label>
                <textarea
                  value={catalogoForm.notas}
                  onChange={(e) => setCatalogoForm({ ...catalogoForm, notas: e.target.value })}
                  rows={2}
                  className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                  placeholder="Notas internas sobre el producto"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="activo"
                  checked={catalogoForm.activo}
                  onChange={(e) => setCatalogoForm({ ...catalogoForm, activo: e.target.checked })}
                  className="rounded border-gray-300 text-primary focus:ring-primary"
                />
                <label htmlFor="activo" className="text-sm text-gray-700">
                  Producto activo (disponible para selección)
                </label>
              </div>
            </div>
            <div className="px-6 py-4 border-t bg-gray-50 rounded-b-xl flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowCatalogoModal(false);
                  setEditingProductoDonacion(null);
                  setCatalogoForm({ clave: '', nombre: '', descripcion: '', unidad_medida: 'PIEZA', presentacion: '', activo: true, notas: '' });
                }}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleGuardarProductoDonacion}
                disabled={actionLoading === 'guardarProducto'}
                className="px-4 py-2 text-white rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
                style={{ backgroundColor: COLORS.primary }}
              >
                {actionLoading === 'guardarProducto' && <FaSpinner className="animate-spin" />}
                {editingProductoDonacion ? 'Actualizar' : 'Crear Producto'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de creación rápida de producto */}
      {showQuickProductModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
            <div
              className="px-6 py-4 border-b flex items-center justify-between"
              style={{ backgroundColor: COLORS.primary }}
            >
              <h2 className="text-lg font-semibold text-white">Crear Producto Rápido</h2>
              <button
                onClick={() => {
                  setShowQuickProductModal(false);
                  setQuickProductForm({ clave: '', nombre: '', descripcion: '', unidad_medida: 'PIEZA', presentacion: '' });
                }}
                className="text-white/80 hover:text-white"
              >
                <FaTimes size={20} />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Clave *</label>
                <input
                  type="text"
                  value={quickProductForm.clave}
                  onChange={(e) => setQuickProductForm({ ...quickProductForm, clave: e.target.value.toUpperCase() })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary"
                  placeholder="Ej: PROD-001"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nombre *</label>
                <input
                  type="text"
                  value={quickProductForm.nombre}
                  onChange={(e) => setQuickProductForm({ ...quickProductForm, nombre: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary"
                  placeholder="Nombre del producto"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Presentación</label>
                <input
                  type="text"
                  value={quickProductForm.presentacion}
                  onChange={(e) => setQuickProductForm({ ...quickProductForm, presentacion: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary"
                  placeholder="Ej: Caja con 30 tabletas"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Unidad de Medida</label>
                <select
                  value={quickProductForm.unidad_medida}
                  onChange={(e) => setQuickProductForm({ ...quickProductForm, unidad_medida: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary"
                >
                  <option value="PIEZA">Pieza</option>
                  <option value="CAJA">Caja</option>
                  <option value="FRASCO">Frasco</option>
                  <option value="SOBRE">Sobre</option>
                  <option value="TUBO">Tubo</option>
                </select>
              </div>
            </div>
            <div className="px-6 py-4 border-t flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowQuickProductModal(false);
                  setQuickProductForm({ clave: '', nombre: '', descripcion: '', unidad_medida: 'PIEZA', presentacion: '' });
                }}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleGuardarQuickProduct}
                disabled={actionLoading === 'quickProduct'}
                className="px-4 py-2 text-white rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
                style={{ backgroundColor: COLORS.primary }}
              >
                {actionLoading === 'quickProduct' && <FaSpinner className="animate-spin" />}
                Crear Producto
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de carga masiva de productos */}
      {showBulkAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
            <div
              className="px-6 py-4 border-b flex items-center justify-between"
              style={{ backgroundColor: COLORS.primary }}
            >
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <FaTable /> Carga Masiva de Productos
              </h2>
              <button
                onClick={() => {
                  setShowBulkAddModal(false);
                  setBulkText('');
                  setBulkProducts([]);
                }}
                className="text-white/80 hover:text-white"
              >
                <FaTimes size={20} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
                <p className="font-medium">Formato de entrada:</p>
                <p>Una línea por producto. Usar <code>|</code> o <code>-</code> como separador.</p>
                <p className="mt-1">Ejemplo: <code>CLAVE | NOMBRE | DESCRIPCION | UNIDAD</code></p>
                <p>O simplemente: <code>CLAVE - NOMBRE</code></p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Productos (uno por línea)</label>
                <textarea
                  value={bulkText}
                  onChange={(e) => setBulkText(e.target.value)}
                  onBlur={parseBulkText}
                  rows={8}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary font-mono text-sm"
                  placeholder="PROD-001 | Paracetamol 500mg | Analgésico | CAJA&#10;PROD-002 | Ibuprofeno 400mg | Antiinflamatorio | CAJA&#10;PROD-003 - Aspirina 100mg"
                />
              </div>
              {bulkProducts.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-2">
                    Vista previa: {bulkProducts.filter(p => p.valid).length} productos válidos de {bulkProducts.length}
                  </p>
                  <div className="max-h-40 overflow-y-auto border rounded-lg">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-2 py-1 text-left">Clave</th>
                          <th className="px-2 py-1 text-left">Nombre</th>
                          <th className="px-2 py-1 text-center">Estado</th>
                        </tr>
                      </thead>
                      <tbody>
                        {bulkProducts.map((p) => (
                          <tr key={p.id} className={p.valid ? '' : 'bg-red-50'}>
                            <td className="px-2 py-1">{p.clave || '-'}</td>
                            <td className="px-2 py-1">{p.nombre || '-'}</td>
                            <td className="px-2 py-1 text-center">
                              {p.valid ? (
                                <FaCheckCircle className="text-green-500 inline" />
                              ) : (
                                <FaExclamationTriangle className="text-red-500 inline" />
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
            <div className="px-6 py-4 border-t flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowBulkAddModal(false);
                  setBulkText('');
                  setBulkProducts([]);
                }}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleBulkImport}
                disabled={actionLoading === 'bulkImport' || bulkProducts.filter(p => p.valid).length === 0}
                className="px-4 py-2 text-white rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
                style={{ backgroundColor: COLORS.primary }}
              >
                {actionLoading === 'bulkImport' && <FaSpinner className="animate-spin" />}
                Importar {bulkProducts.filter(p => p.valid).length} Productos
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de confirmación eliminar producto del catálogo */}
      <ConfirmModal
        open={!!confirmDeleteProducto}
        title="Eliminar Producto del Catálogo"
        message={confirmDeleteProducto ? `¿Estás seguro de eliminar el producto "${confirmDeleteProducto.clave} - ${confirmDeleteProducto.nombre}"? Esta acción no se puede deshacer si el producto tiene donaciones asociadas.` : ''}
        confirmText="Eliminar"
        cancelText="Cancelar"
        tone="danger"
        onConfirm={() => confirmDeleteProducto && handleEliminarProductoDonacion(confirmDeleteProducto)}
        onCancel={() => setConfirmDeleteProducto(null)}
      />

      {/* ISS-SEC: Modal de confirmación de 2 pasos para finalizar entrega */}
      <TwoStepConfirmModal
        open={!!confirmFinalizarEntrega}
        title="Confirmar Entrega de Donación"
        message={confirmFinalizarEntrega ? `¿Confirmas que la entrega de ${confirmFinalizarEntrega.cantidad} unidades a "${confirmFinalizarEntrega.destinatario}" ha sido completada?` : ''}
        warnings={[
          'Se descontará el stock del inventario de donaciones',
          'Se generará el comprobante de entrega',
          'Esta operación no se puede deshacer'
        ]}
        itemInfo={confirmFinalizarEntrega ? {
          'Producto': confirmFinalizarEntrega.producto_nombre || 'N/A',
          'Cantidad': `${confirmFinalizarEntrega.cantidad} unidades`,
          'Destinatario': confirmFinalizarEntrega.destinatario
        } : null}
        confirmText="Sí, Confirmar Entrega"
        cancelText="No, volver"
        tone="warning"
        onConfirm={() => confirmFinalizarEntrega && handleFinalizarEntrega(confirmFinalizarEntrega)}
        onCancel={() => setConfirmFinalizarEntrega(null)}
      />

      {/* ISS-SEC: Modal de confirmación de 2 pasos para finalizar GRUPO de entregas */}
      <TwoStepConfirmModal
        open={!!confirmFinalizarGrupo}
        title="Confirmar Entrega Completa (Grupo)"
        message={confirmFinalizarGrupo ? `¿Confirmas que TODA la entrega a "${confirmFinalizarGrupo.destinatario}" ha sido completada?` : ''}
        warnings={[
          `Se marcarán ${confirmFinalizarGrupo?.entregas?.length || 0} productos como entregados`,
          `Se descontarán ${confirmFinalizarGrupo?.totalCantidad || 0} unidades del inventario`,
          'Esta operación afecta múltiples items',
          'No se puede deshacer'
        ]}
        itemInfo={confirmFinalizarGrupo ? {
          'Destinatario': confirmFinalizarGrupo.destinatario,
          'Total Productos': confirmFinalizarGrupo.entregas?.length || 0,
          'Total Unidades': confirmFinalizarGrupo.totalCantidad || 0
        } : null}
        confirmText={finalizandoGrupo ? "Procesando..." : "Sí, Confirmar Todo"}
        cancelText="No, volver"
        tone="warning"
        loading={finalizandoGrupo}
        onConfirm={() => confirmFinalizarGrupo && handleFinalizarGrupo(confirmFinalizarGrupo)}
        onCancel={() => setConfirmFinalizarGrupo(null)}
      />

      {/* Modal de confirmación eliminar entrega pendiente */}
      <ConfirmModal
        open={!!confirmEliminarEntrega}
        title="Eliminar Entrega"
        message={confirmEliminarEntrega ? `¿Estás seguro de eliminar esta entrega pendiente?\n\n• Producto: ${confirmEliminarEntrega.producto_nombre || 'N/A'}\n• Cantidad: ${confirmEliminarEntrega.cantidad}\n• Destinatario: ${confirmEliminarEntrega.destinatario}\n\nEl stock será devuelto al inventario de donaciones.` : ''}
        confirmText="Sí, Eliminar"
        cancelText="Cancelar"
        tone="danger"
        onConfirm={() => confirmEliminarEntrega && handleEliminarEntrega(confirmEliminarEntrega)}
        onCancel={() => setConfirmEliminarEntrega(null)}
      />

      {/* Modal de detalles de entrega */}
      {detalleEntregaModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="px-6 py-4 border-b bg-indigo-600 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <FaEye /> Detalle de Entrega
              </h2>
              <button
                onClick={() => setDetalleEntregaModal(null)}
                className="text-white/80 hover:text-white transition-colors"
              >
                <FaTimes size={20} />
              </button>
            </div>

            {/* Contenido */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {/* Información del Producto */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-600 mb-3 flex items-center gap-2">
                  <FaBox className="text-indigo-600" /> Producto Entregado
                </h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Producto:</span>
                    <span className="font-semibold text-gray-800">
                      {detalleEntregaModal.producto_nombre || 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Cantidad:</span>
                    <span className="font-bold text-lg text-indigo-600">{detalleEntregaModal.cantidad}</span>
                  </div>
                  {detalleEntregaModal.detalle_donacion_info && (
                    <>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Donación:</span>
                        <span className="text-gray-800">{detalleEntregaModal.detalle_donacion_info.donacion_numero}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Stock restante:</span>
                        <span className="text-gray-800">{detalleEntregaModal.detalle_donacion_info.cantidad_disponible}</span>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Información del Destinatario */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-600 mb-3 flex items-center gap-2">
                  <FaUser className="text-indigo-600" /> Destinatario
                </h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Nombre:</span>
                    <span className="font-semibold text-gray-800">{detalleEntregaModal.destinatario}</span>
                  </div>
                  {detalleEntregaModal.centro_destino_nombre && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Centro:</span>
                      <span className="text-gray-800">{detalleEntregaModal.centro_destino_nombre}</span>
                    </div>
                  )}
                  {detalleEntregaModal.motivo && (
                    <div>
                      <span className="text-gray-500 block mb-1">Motivo:</span>
                      <p className="bg-white p-2 rounded border text-gray-700 text-sm">{detalleEntregaModal.motivo}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Información de Entrega */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-600 mb-3 flex items-center gap-2">
                  <FaCalendar className="text-indigo-600" /> Información de Entrega
                </h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Fecha registro:</span>
                    <span className="text-gray-800">
                      {new Date(detalleEntregaModal.fecha_entrega).toLocaleString('es-MX', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Registrado por:</span>
                    <span className="text-gray-800">{detalleEntregaModal.entregado_por_nombre || 'Sistema'}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-500">Estado:</span>
                    {detalleEntregaModal.estado_entrega === 'entregado' || detalleEntregaModal.finalizado ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        <FaCheckCircle className="text-green-600" />
                        Entregado
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        <FaClock className="text-yellow-600" />
                        Pendiente
                      </span>
                    )}
                  </div>
                  {detalleEntregaModal.finalizado && detalleEntregaModal.fecha_finalizado && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Fecha finalización:</span>
                      <span className="text-gray-800">
                        {new Date(detalleEntregaModal.fecha_finalizado).toLocaleString('es-MX', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                  )}
                  {detalleEntregaModal.finalizado_por_nombre && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Finalizado por:</span>
                      <span className="text-gray-800">{detalleEntregaModal.finalizado_por_nombre}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Notas */}
              {detalleEntregaModal.notas && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-sm font-semibold text-gray-600 mb-2">Notas adicionales</h3>
                  <p className="bg-white p-3 rounded border text-gray-700 text-sm">{detalleEntregaModal.notas}</p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end">
              <button
                onClick={() => setDetalleEntregaModal(null)}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========== MODAL: RESULTADO DE IMPORTACIÓN ========== */}
      {importResultModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-lg w-full shadow-2xl overflow-hidden">
            {/* Header */}
            <div className={`px-6 py-4 ${importResultModal.total > 0 ? 'bg-green-600' : 'bg-red-600'} text-white`}>
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold flex items-center gap-2">
                  {importResultModal.total > 0 ? (
                    <>
                      <FaCheckCircle /> Importación Exitosa
                    </>
                  ) : (
                    <>
                      <FaExclamationTriangle /> Error en Importación
                    </>
                  )}
                </h2>
                <button
                  onClick={() => setImportResultModal(null)}
                  className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                >
                  <FaTimes />
                </button>
              </div>
            </div>

            {/* Contenido */}
            <div className="p-6 space-y-4">
              {importResultModal.total > 0 ? (
                <>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div className="bg-green-50 rounded-lg p-4">
                      <p className="text-3xl font-bold text-green-600">{importResultModal.creados}</p>
                      <p className="text-sm text-green-700">Creados</p>
                    </div>
                    <div className="bg-blue-50 rounded-lg p-4">
                      <p className="text-3xl font-bold text-blue-600">{importResultModal.actualizados}</p>
                      <p className="text-sm text-blue-700">Actualizados</p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="text-3xl font-bold text-gray-600">{importResultModal.total}</p>
                      <p className="text-sm text-gray-700">Total</p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600 text-center">
                    Los productos se han importado correctamente al catálogo de donaciones.
                  </p>
                </>
              ) : (
                <div className="bg-red-50 rounded-lg p-4">
                  <p className="text-red-700 font-medium mb-2">No se pudo importar el archivo:</p>
                  <p className="text-red-600 text-sm">{importResultModal.errores?.[0] || 'Error desconocido'}</p>
                </div>
              )}

              {/* Errores de filas individuales */}
              {importResultModal.errores?.length > 0 && importResultModal.total > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <p className="font-medium text-yellow-800 mb-2 flex items-center gap-2">
                    <FaExclamationTriangle className="text-yellow-600" />
                    Advertencias ({importResultModal.errores.length}):
                  </p>
                  <ul className="text-sm text-yellow-700 space-y-1 max-h-32 overflow-y-auto">
                    {importResultModal.errores.slice(0, 10).map((err, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-yellow-500">•</span>
                        {err}
                      </li>
                    ))}
                    {importResultModal.errores.length > 10 && (
                      <li className="text-yellow-600 italic">
                        ... y {importResultModal.errores.length - 10} más
                      </li>
                    )}
                  </ul>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end">
              <button
                onClick={() => setImportResultModal(null)}
                className="px-4 py-2 bg-primary text-white rounded-lg hover:opacity-90 transition-colors"
                style={{ backgroundColor: COLORS.primary }}
              >
                Entendido
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========== MODAL: RESULTADO DE IMPORTACIÓN DE DONACIONES ========== */}
      {importDonacionResultModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-2xl w-full shadow-2xl overflow-hidden">
            {/* Header */}
            <div className={`px-6 py-4 ${
              importDonacionResultModal.tipo === 'success' ? 'bg-green-600' : 
              importDonacionResultModal.tipo === 'warning' ? 'bg-yellow-500' : 'bg-red-600'
            } text-white`}>
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold flex items-center gap-2">
                  {importDonacionResultModal.tipo === 'success' ? (
                    <>
                      <FaCheckCircle /> Importación de Donaciones Exitosa
                    </>
                  ) : importDonacionResultModal.tipo === 'warning' ? (
                    <>
                      <FaExclamationTriangle /> Importación Parcial
                    </>
                  ) : (
                    <>
                      <FaExclamationTriangle /> Error en Importación
                    </>
                  )}
                </h2>
                <button
                  onClick={() => setImportDonacionResultModal(null)}
                  className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                  title="Cerrar (X)"
                >
                  <FaTimes />
                </button>
              </div>
            </div>

            {/* Contenido */}
            <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
              {/* Mensaje principal */}
              <div className={`rounded-lg p-4 ${
                importDonacionResultModal.tipo === 'success' ? 'bg-green-50 border border-green-200' :
                importDonacionResultModal.tipo === 'warning' ? 'bg-yellow-50 border border-yellow-200' :
                'bg-red-50 border border-red-200'
              }`}>
                <p className={`font-medium ${
                  importDonacionResultModal.tipo === 'success' ? 'text-green-800' :
                  importDonacionResultModal.tipo === 'warning' ? 'text-yellow-800' :
                  'text-red-800'
                }`}>
                  {importDonacionResultModal.mensaje}
                </p>
              </div>

              {/* Estadísticas si hubo éxito */}
              {(importDonacionResultModal.donaciones_creadas > 0 || importDonacionResultModal.detalles_creados > 0) && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
                  <div className="bg-green-50 rounded-lg p-3">
                    <p className="text-2xl font-bold text-green-600">{importDonacionResultModal.donaciones_creadas || 0}</p>
                    <p className="text-xs text-green-700">Donaciones</p>
                  </div>
                  <div className="bg-blue-50 rounded-lg p-3">
                    <p className="text-2xl font-bold text-blue-600">{importDonacionResultModal.detalles_creados || 0}</p>
                    <p className="text-xs text-blue-700">Detalles</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-2xl font-bold text-gray-600">{importDonacionResultModal.filas_procesadas || 0}</p>
                    <p className="text-xs text-gray-700">Filas procesadas</p>
                  </div>
                  <div className="bg-red-50 rounded-lg p-3">
                    <p className="text-2xl font-bold text-red-600">{importDonacionResultModal.fallidos || 0}</p>
                    <p className="text-xs text-red-700">Errores</p>
                  </div>
                </div>
              )}

              {/* Info adicional sobre filas ignoradas */}
              {(importDonacionResultModal.filas_vacias > 0 || importDonacionResultModal.filas_ejemplo > 0) && (
                <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-600">
                  <p className="flex items-center gap-2">
                    <FaInfoCircle className="text-gray-400" />
                    {importDonacionResultModal.filas_vacias > 0 && `${importDonacionResultModal.filas_vacias} filas vacías ignoradas. `}
                    {importDonacionResultModal.filas_ejemplo > 0 && `${importDonacionResultModal.filas_ejemplo} filas de ejemplo ignoradas.`}
                  </p>
                </div>
              )}

              {/* Lista de errores detallados */}
              {importDonacionResultModal.errores?.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <p className="font-semibold text-red-800 mb-3 flex items-center gap-2">
                    <FaExclamationTriangle className="text-red-600" />
                    Errores encontrados ({importDonacionResultModal.errores.length}):
                  </p>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {importDonacionResultModal.errores.slice(0, 20).map((err, idx) => (
                      <div key={idx} className="bg-white rounded p-2 text-sm border border-red-100">
                        <span className="font-medium text-red-700">
                          {err.fila ? `Fila ${err.fila}: ` : ''}
                        </span>
                        <span className="text-red-600">{err.error || err}</span>
                      </div>
                    ))}
                    {importDonacionResultModal.errores.length > 20 && (
                      <p className="text-red-500 text-sm italic text-center py-2">
                        ... y {importDonacionResultModal.errores.length - 20} errores más
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Footer con botón de cerrar prominente */}
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-between items-center">
              <p className="text-xs text-gray-500">
                Este mensaje permanecerá visible hasta que lo cierre
              </p>
              <button
                onClick={() => setImportDonacionResultModal(null)}
                className="px-6 py-2.5 bg-primary text-white rounded-lg hover:opacity-90 transition-colors font-semibold flex items-center gap-2"
                style={{ backgroundColor: COLORS.primary }}
              >
                <FaTimes /> Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Donaciones;
