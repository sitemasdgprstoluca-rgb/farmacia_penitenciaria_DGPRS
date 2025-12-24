import { useState, useEffect, useCallback, useRef } from 'react';
import { donacionesAPI, productosDonacionAPI, centrosAPI, salidasDonacionesAPI, detallesDonacionAPI } from '../services/api';
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
  FaArrowRight,
  FaExclamationTriangle,
  FaFileExport,
  FaFileImport,
  FaDownload,
  FaShoppingCart,
  FaTable,
  FaClipboardCheck,
  FaFilePdf,
} from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import { COLORS } from '../constants/theme';
import Pagination from '../components/Pagination';
import { usePermissions } from '../hooks/usePermissions';
import ConfirmModal from '../components/ConfirmModal';
import { esFarmaciaAdmin as checkEsFarmaciaAdmin } from '../utils/roles';
import SalidaMasivaDonaciones from '../components/SalidaMasivaDonaciones';

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
  
  // Importación/Exportación de catálogo de productos de donaciones
  const [exportingCatalogo, setExportingCatalogo] = useState(false);
  const [importingCatalogo, setImportingCatalogo] = useState(false);
  const catalogoFileInputRef = useRef(null);
  
  // Modal rápido para crear producto desde formulario de donación
  const [showQuickProductModal, setShowQuickProductModal] = useState(false);
  const [quickProductForm, setQuickProductForm] = useState({
    clave: '',
    nombre: '',
    unidad_medida: 'PIEZA',
    presentacion: '',
  });
  const [savingQuickProduct, setSavingQuickProduct] = useState(false);
  
  // Modal de carga masiva de productos
  const [showBulkAddModal, setShowBulkAddModal] = useState(false);
  const [bulkText, setBulkText] = useState('');
  const [bulkProducts, setBulkProducts] = useState([]);
  const [parsingBulk, setParsingBulk] = useState(false);
  
  // Inventario de Donaciones (productos con stock disponible)
  const [inventarioDonaciones, setInventarioDonaciones] = useState([]);
  const [loadingInventario, setLoadingInventario] = useState(false);
  const [inventarioPage, setInventarioPage] = useState(1);
  const [inventarioTotalPages, setInventarioTotalPages] = useState(1);
  const [searchInventario, setSearchInventario] = useState('');
  
  // Historial de Entregas (todas las salidas)
  const [todasEntregas, setTodasEntregas] = useState([]);
  const [loadingEntregas, setLoadingEntregas] = useState(false);
  const [entregasPage, setEntregasPage] = useState(1);
  const [entregasTotalPages, setEntregasTotalPages] = useState(1);
  const [searchEntregas, setSearchEntregas] = useState('');
  
  // Exportación de entregas (solo export, sin import)
  const [exportingEntregas, setExportingEntregas] = useState(false);
  
  // Importación/Exportación de donaciones
  const [exportingDonaciones, setExportingDonaciones] = useState(false);
  const [importingDonaciones, setImportingDonaciones] = useState(false);
  const donacionFileInputRef = useRef(null); // Para donaciones
  
  // Modal de Entrega Masiva de Donaciones
  const [showSalidaMasiva, setShowSalidaMasiva] = useState(false);
  
  // Estadísticas del almacén de donaciones
  const [estadisticas, setEstadisticas] = useState({
    totalProductos: 0,
    totalUnidades: 0,
    productosAgotados: 0,
    productosPorCaducar: 0,
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

  // Estado para número de donación auto-generado
  const [siguienteNumero, setSiguienteNumero] = useState('');
  
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

  // Cargar catálogos - USA CATÁLOGO INDEPENDIENTE DE DONACIONES
  const cargarCatalogos = useCallback(async () => {
    try {
      const [prodDonRes, centrosRes] = await Promise.all([
        productosDonacionAPI.getAll({ page_size: 500, activo: true, ordering: 'nombre' }),
        centrosAPI.getAll({ page_size: 100, activo: true, ordering: 'nombre' }),
      ]);
      setProductosDonacion(prodDonRes.data.results || prodDonRes.data || []);
      setCentros(centrosRes.data.results || centrosRes.data || []);
    } catch (err) {
      console.error('Error cargando catálogos:', err);
    }
  }, []);

  // Generar siguiente número de donación automático
  const generarSiguienteNumero = useCallback(async () => {
    try {
      // Obtener todas las donaciones para encontrar el último número
      const response = await donacionesAPI.getAll({ page_size: 1, ordering: '-id' });
      const ultimaDonacion = response.data.results?.[0] || response.data?.[0];
      
      // Generar el siguiente número basado en el formato DON-YYYY-NNNN
      const year = new Date().getFullYear();
      let siguienteSeq = 1;
      
      if (ultimaDonacion && ultimaDonacion.numero) {
        // Intentar extraer el número secuencial del último registro
        const match = ultimaDonacion.numero.match(/DON-(\d{4})-(\d+)/);
        if (match) {
          const lastYear = parseInt(match[1]);
          const lastSeq = parseInt(match[2]);
          if (lastYear === year) {
            siguienteSeq = lastSeq + 1;
          }
        } else {
          // Si el formato es diferente, usar el ID como base
          siguienteSeq = (ultimaDonacion.id || 0) + 1;
        }
      }
      
      const nuevoNumero = `DON-${year}-${String(siguienteSeq).padStart(4, '0')}`;
      setSiguienteNumero(nuevoNumero);
      return nuevoNumero;
    } catch (err) {
      console.error('Error generando número:', err);
      // Fallback: usar timestamp
      const fallback = `DON-${new Date().getFullYear()}-${Date.now().toString().slice(-4)}`;
      setSiguienteNumero(fallback);
      return fallback;
    }
  }, []);

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
        disponible: 'true', // Solo productos con stock > 0
      };
      if (searchInventario) params.search = searchInventario;

      const response = await detallesDonacionAPI.getAll(params);
      const data = response.data;

      if (data.results) {
        setInventarioDonaciones(data.results);
        setInventarioTotalPages(Math.ceil((data.count || 0) / PAGE_SIZE));
      } else {
        setInventarioDonaciones(data || []);
        setInventarioTotalPages(1);
      }

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
  }, [inventarioPage, searchInventario]);

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
  }, [entregasPage, searchEntregas]);

  // Exportar entregas a Excel
  const handleExportarEntregas = async () => {
    setExportingEntregas(true);
    try {
      const params = {};
      if (searchEntregas) params.destinatario = searchEntregas;
      
      const response = await salidasDonacionesAPI.exportarExcel(params);
      
      // Crear blob y descargar
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `entregas_donaciones_${new Date().toISOString().split('T')[0]}.xlsx`;
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

  // Generar PDF de recibo para una salida individual
  const generarPdfSalida = async (salidaId) => {
    try {
      toast.loading('Generando recibo PDF...', { id: 'pdf-loading' });
      
      const response = await salidasDonacionesAPI.generarPdf(salidaId);
      
      // Crear blob y descargar
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `recibo_salida_donacion_${salidaId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.dismiss('pdf-loading');
      toast.success('Recibo PDF generado correctamente');
    } catch (err) {
      console.error('Error generando PDF:', err);
      toast.dismiss('pdf-loading');
      toast.error('Error al generar el recibo PDF');
    }
  };

  // Finalizar una salida de donación (marcarla como entregada)
  const finalizarSalida = async (salidaId) => {
    try {
      toast.loading('Finalizando entrega...', { id: 'finalizar-loading' });
      
      await salidasDonacionesAPI.finalizar(salidaId);
      
      toast.dismiss('finalizar-loading');
      toast.success('Entrega finalizada correctamente');
      
      // Recargar la lista de entregas
      cargarTodasEntregas();
    } catch (err) {
      console.error('Error finalizando salida:', err);
      toast.dismiss('finalizar-loading');
      toast.error(err.response?.data?.error || 'Error al finalizar la entrega');
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
      
      const response = await donacionesAPI.importarExcel(formData);
      
      const { resultados } = response.data;
      
      if (resultados.exitosos > 0) {
        toast.success(`${resultados.exitosos} donaciones importadas correctamente`);
        cargarDonaciones();
      }
      
      if (resultados.fallidos > 0) {
        toast.error(`${resultados.fallidos} donaciones fallaron`);
        // Mostrar errores detallados
        resultados.errores?.forEach((err, idx) => {
          if (idx < 3) { // Mostrar máximo 3 errores
            toast.error(`Fila ${err.fila}: ${err.error}`, { duration: 5000 });
          }
        });
      }
    } catch (err) {
      console.error('Error importando donaciones:', err);
      const errorMsg = err.response?.data?.error || 'Error al importar donaciones';
      toast.error(errorMsg);
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

  // === IMPORTACIÓN/EXPORTACIÓN DEL CATÁLOGO DE PRODUCTOS DE DONACIONES ===
  
  // Exportar catálogo a Excel
  const handleExportarCatalogo = async () => {
    setExportingCatalogo(true);
    try {
      const response = await productosDonacionAPI.exportarExcel({ search: searchCatalogo });
      
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `catalogo_productos_donaciones_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('Catálogo exportado correctamente');
    } catch (err) {
      console.error('Error exportando catálogo:', err);
      toast.error('Error al exportar catálogo');
    } finally {
      setExportingCatalogo(false);
    }
  };

  // Descargar plantilla de importación de catálogo
  const handleDescargarPlantillaCatalogo = async () => {
    try {
      const response = await productosDonacionAPI.plantillaExcel();
      
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'plantilla_catalogo_donaciones.xlsx';
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

  // Importar catálogo desde Excel
  const handleImportarCatalogo = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    setImportingCatalogo(true);
    try {
      const formData = new FormData();
      formData.append('archivo', file);
      
      const response = await productosDonacionAPI.importarExcel(formData);
      
      const { resultados } = response.data;
      
      if (resultados.exitosos > 0) {
        toast.success(`${resultados.exitosos} productos importados correctamente`);
        cargarCatalogos();
      }
      
      if (resultados.fallidos > 0) {
        toast.error(`${resultados.fallidos} productos fallaron`);
        resultados.errores?.slice(0, 3).forEach((err) => {
          toast.error(`Fila ${err.fila}: ${err.error}`, { duration: 5000 });
        });
      }
    } catch (err) {
      console.error('Error importando catálogo:', err);
      const errorMsg = err.response?.data?.error || 'Error al importar catálogo';
      toast.error(errorMsg);
    } finally {
      setImportingCatalogo(false);
      if (catalogoFileInputRef.current) {
        catalogoFileInputRef.current.value = '';
      }
    }
  };

  // Crear producto rápido desde el formulario de donación
  const handleCrearProductoRapido = async () => {
    if (!quickProductForm.clave || !quickProductForm.nombre) {
      toast.error('La clave y el nombre son obligatorios');
      return;
    }

    setSavingQuickProduct(true);
    try {
      const nuevoProducto = await productosDonacionAPI.create({
        ...quickProductForm,
        activo: true,
      });
      
      toast.success('Producto creado correctamente');
      
      // Recargar catálogo para tener el nuevo producto
      await cargarCatalogos();
      
      // Seleccionar automáticamente el nuevo producto en el formulario
      setDetalleForm(prev => ({
        ...prev,
        producto_donacion: nuevoProducto.data.id.toString(),
      }));
      
      // Cerrar modal y limpiar formulario
      setShowQuickProductModal(false);
      setQuickProductForm({
        clave: '',
        nombre: '',
        unidad_medida: 'PIEZA',
        presentacion: '',
      });
    } catch (err) {
      console.error('Error creando producto rápido:', err);
      toast.error(err.response?.data?.clave?.[0] || err.response?.data?.error || 'Error al crear producto');
    } finally {
      setSavingQuickProduct(false);
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
  const handleNuevo = async () => {
    resetForm();
    // Generar número de donación automático
    const nuevoNumero = await generarSiguienteNumero();
    setFormData(prev => ({ ...prev, numero: nuevoNumero }));
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
    if (!detalleForm.producto_donacion || !detalleForm.cantidad) {
      toast.error('Selecciona un producto y cantidad');
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

  // ========== CARGA MASIVA DE PRODUCTOS ==========
  
  // Parsear texto pegado (formato: Clave | Nombre | Lote | Cantidad | Caducidad)
  const handleParseBulkText = () => {
    if (!bulkText.trim()) {
      toast.error('Pega el texto con los productos');
      return;
    }
    
    setParsingBulk(true);
    try {
      const lines = bulkText.trim().split('\n').filter(line => line.trim());
      const parsed = [];
      const errors = [];
      
      lines.forEach((line, idx) => {
        // Soporta separadores: | , ; TAB
        const parts = line.split(/[|,;\t]/).map(p => p.trim());
        
        if (parts.length < 2) {
          errors.push(`Línea ${idx + 1}: Formato incorrecto (mínimo clave y cantidad)`);
          return;
        }
        
        // Buscar producto por clave o nombre
        const claveONombre = parts[0];
        const producto = productosDonacion.find(
          p => p.clave?.toLowerCase() === claveONombre.toLowerCase() ||
               p.nombre?.toLowerCase().includes(claveONombre.toLowerCase())
        );
        
        if (!producto) {
          errors.push(`Línea ${idx + 1}: Producto "${claveONombre}" no encontrado en catálogo`);
          return;
        }
        
        // Parsear cantidad (puede estar en posición 1, 2, 3 o 4)
        let cantidad = null;
        let lote = '';
        let caducidad = '';
        
        // Detectar formato basado en contenido
        for (let i = 1; i < parts.length; i++) {
          const val = parts[i];
          if (!val) continue;
          
          // Es número? -> cantidad
          if (/^\d+$/.test(val)) {
            cantidad = parseInt(val);
          }
          // Es fecha? (YYYY-MM-DD o DD/MM/YYYY)
          else if (/^\d{4}-\d{2}-\d{2}$/.test(val) || /^\d{2}\/\d{2}\/\d{4}$/.test(val)) {
            // Convertir DD/MM/YYYY a YYYY-MM-DD
            if (/^\d{2}\/\d{2}\/\d{4}$/.test(val)) {
              const [d, m, y] = val.split('/');
              caducidad = `${y}-${m}-${d}`;
            } else {
              caducidad = val;
            }
          }
          // Es lote (alfanumérico)
          else if (/^[A-Za-z0-9-]+$/.test(val) && val.length > 2) {
            lote = val;
          }
        }
        
        if (!cantidad || cantidad <= 0) {
          errors.push(`Línea ${idx + 1}: Cantidad no válida`);
          return;
        }
        
        parsed.push({
          tempId: Date.now() + idx,
          producto_donacion: producto.id,
          producto_clave: producto.clave,
          producto_nombre: producto.nombre,
          numero_lote: lote,
          cantidad,
          fecha_caducidad: caducidad,
          estado_producto: 'bueno',
          notas: '',
        });
      });
      
      if (errors.length > 0 && parsed.length === 0) {
        toast.error(errors.slice(0, 3).join('\n'));
      } else {
        setBulkProducts(parsed);
        if (errors.length > 0) {
          toast(`${parsed.length} productos listos, ${errors.length} con errores`, { icon: '⚠️' });
        } else {
          toast.success(`${parsed.length} productos listos para agregar`);
        }
      }
    } catch (err) {
      console.error('Error parseando:', err);
      toast.error('Error al procesar el texto');
    } finally {
      setParsingBulk(false);
    }
  };
  
  // Agregar todos los productos parseados
  const handleAddBulkProducts = () => {
    if (bulkProducts.length === 0) {
      toast.error('No hay productos para agregar');
      return;
    }
    
    setFormData(prev => ({
      ...prev,
      detalles: [...prev.detalles, ...bulkProducts],
    }));
    
    toast.success(`${bulkProducts.length} productos agregados`);
    setBulkProducts([]);
    setBulkText('');
    setShowBulkAddModal(false);
  };

  // Guardar donación
  const handleGuardar = async () => {
    // Validaciones completas
    if (!formData.donante_nombre?.trim()) {
      toast.error('El nombre del donante es obligatorio');
      return;
    }
    if (!formData.fecha_donacion) {
      toast.error('La fecha de donación es obligatoria');
      return;
    }
    if (formData.detalles.length === 0) {
      toast.error('Debes agregar al menos un producto a la donación');
      return;
    }

    setActionLoading('guardar');
    try {
      const payload = {
        ...formData,
        // centro_destino es opcional - las donaciones llegan a farmacia central
        centro_destino: formData.centro_destino ? parseInt(formData.centro_destino) : null,
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
      centro_destino: '',  // Centro destino obligatorio
      motivo: '',
      notas: '',
    });
    setShowSalidaModal(true);
  };

  // Registrar salida de donación
  const handleRegistrarSalida = async () => {
    if (!salidaForm.cantidad || !salidaForm.centro_destino) {
      toast.error('Completa cantidad y centro destino');
      return;
    }

    const cantidad = parseInt(salidaForm.cantidad);
    if (cantidad <= 0 || cantidad > salidaDetalle.cantidad_disponible) {
      toast.error(`Cantidad inválida. Disponible: ${salidaDetalle.cantidad_disponible}`);
      return;
    }

    // Obtener nombre del centro para el destinatario
    const centroSeleccionado = centros.find(c => c.id === parseInt(salidaForm.centro_destino));

    setActionLoading('salida');
    try {
      await salidasDonacionesAPI.create({
        detalle_donacion: salidaDetalle.id,
        cantidad: cantidad,
        centro_destino: parseInt(salidaForm.centro_destino),
        destinatario: centroSeleccionado?.nombre || 'Centro',  // Nombre del centro como destinatario
        motivo: salidaForm.motivo || null,
        notas: salidaForm.notas || null,
      });
      toast.success('Salida registrada correctamente');
      setShowSalidaModal(false);
      setSalidaDetalle(null);
      // Refrescar donación si está abierta
      if (viewingDonacion) {
        const updated = await donacionesAPI.getById(viewingDonacion.id);
        setViewingDonacion(updated.data);
      }
      // Refrescar según la tab activa
      if (activeTab === 'donaciones') {
        cargarDonaciones();
      } else if (activeTab === 'inventario') {
        cargarInventarioDonaciones();
      } else if (activeTab === 'entregas') {
        cargarTodasEntregas();
      }
    } catch (err) {
      console.error('Error registrando salida:', err);
      toast.error(err.response?.data?.error || err.response?.data?.cantidad?.[0] || 'Error al registrar salida');
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
            <FaHandHoldingMedical /> Salidas Donación
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
                  <span className="flex items-center gap-1"><FaHandHoldingMedical className="text-purple-500" /> Salida</span>
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
            <FaSpinner className="animate-spin text-4xl text-gray-400" />
          </div>
        ) : donaciones.length === 0 ? (
          <div className="text-center py-20 text-gray-500">
            <FaGift className="mx-auto text-5xl mb-4 opacity-30" />
            <p>No se encontraron donaciones</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Número</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Donante</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Tipo</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Fecha</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Items</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Estado</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Acciones</th>
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

              {/* Acciones del catálogo */}
              <div className="flex gap-2 flex-wrap">
                {/* Exportar Excel */}
                <button
                  onClick={handleExportarCatalogo}
                  disabled={exportingCatalogo || productosDonacion.length === 0}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg border text-green-700 border-green-300 hover:bg-green-50 transition-colors disabled:opacity-50"
                >
                  {exportingCatalogo ? <FaSpinner className="animate-spin" /> : <FaFileExport />}
                  Exportar
                </button>

                {/* Descargar Plantilla */}
                {puede.crear && (
                  <button
                    onClick={handleDescargarPlantillaCatalogo}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg border text-blue-700 border-blue-300 hover:bg-blue-50 transition-colors"
                    title="Descargar plantilla Excel para importar productos"
                  >
                    <FaDownload /> Plantilla
                  </button>
                )}

                {/* Importar Excel */}
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
                      className="flex items-center gap-2 px-4 py-2 rounded-lg border text-purple-700 border-purple-300 hover:bg-purple-50 transition-colors disabled:opacity-50"
                    >
                      {importingCatalogo ? <FaSpinner className="animate-spin" /> : <FaFileImport />}
                      Importar
                    </button>
                  </>
                )}

                {/* Agregar Producto */}
                {puede.crear && (
                  <button
                    onClick={() => {
                      setCatalogoForm({ clave: '', nombre: '', descripcion: '', unidad_medida: 'PIEZA', presentacion: '', activo: true, notas: '' });
                      setEditingProductoDonacion(null);
                      setShowCatalogoModal(true);
                    }}
                    className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
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
                <FaSpinner className="animate-spin text-4xl text-gray-400" />
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
              <div className="flex items-center gap-2">
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
          </div>

          {/* Tabla de inventario */}
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            {loadingInventario ? (
              <div className="flex items-center justify-center py-20">
                <FaSpinner className="animate-spin text-4xl text-gray-400" />
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
                      const esCritico = item.cantidad_disponible === 0;
                      const porCaducar = item.fecha_caducidad && new Date(item.fecha_caducidad) <= new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);
                      return (
                        <tr key={item.id} className={`hover:bg-gray-50 ${esCritico ? 'bg-red-50' : porCaducar ? 'bg-yellow-50' : ''}`}>
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
                            <span className={`text-sm ${porCaducar ? 'text-yellow-600 font-medium' : 'text-gray-600'}`}>
                              {formatFecha(item.fecha_caducidad)}
                              {porCaducar && <FaExclamationTriangle className="inline ml-1 text-yellow-500" />}
                            </span>
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

      {/* ========== TAB: SALIDAS DE DONACIÓN ========== */}
      {activeTab === 'entregas' && (
        <>
          {/* Barra de búsqueda y acciones salidas */}
          <div className="bg-white rounded-xl shadow-sm border p-4 mb-6">
            <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center justify-between">
              <div className="relative flex-1 max-w-md">
                <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Buscar por destinatario..."
                  value={searchEntregas}
                  onChange={(e) => {
                    setSearchEntregas(e.target.value);
                    setEntregasPage(1);
                  }}
                  className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                />
              </div>
              <div className="flex flex-wrap items-center gap-2">
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
                
                {/* NOTA: Importación de salidas removida - solo exportar para verificar movimientos */}
              </div>
            </div>
          </div>

          {/* Tabla de salidas */}
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            {loadingEntregas ? (
              <div className="flex items-center justify-center py-20">
                <FaSpinner className="animate-spin text-4xl text-gray-400" />
              </div>
            ) : todasEntregas.length === 0 ? (
              <div className="text-center py-20 text-gray-500">
                <FaHandHoldingMedical className="mx-auto text-5xl mb-4 opacity-30" />
                <p>No hay salidas registradas</p>
                <p className="text-sm mt-2">Las salidas aparecerán aquí cuando se registren desde el inventario</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Fecha</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Producto</th>
                      <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Cantidad</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Destinatario</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Motivo</th>
                      <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Estado</th>
                      <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Acciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {todasEntregas.map((entrega) => (
                      <tr key={entrega.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {new Date(entrega.fecha_entrega).toLocaleString('es-MX', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </td>
                        <td className="px-4 py-3 font-medium">{entrega.producto_nombre || '-'}</td>
                        <td className="px-4 py-3 text-center">
                          <span className="font-bold text-primary">{entrega.cantidad}</span>
                        </td>
                        <td className="px-4 py-3">{entrega.destinatario}</td>
                        <td className="px-4 py-3 text-sm text-gray-600">{entrega.motivo || '-'}</td>
                        <td className="px-4 py-3 text-center">
                          {entrega.finalizado ? (
                            <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">
                              <FaCheck className="text-green-600" /> Entregado
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-100 text-yellow-700 rounded-full text-xs font-medium">
                              ⏳ Pendiente
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <div className="flex items-center justify-center gap-1">
                            {!entrega.finalizado && (
                              <button
                                onClick={() => finalizarSalida(entrega.id)}
                                className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                                title="Finalizar entrega"
                              >
                                <FaCheck />
                              </button>
                            )}
                            <button
                              onClick={() => generarPdfSalida(entrega.id)}
                              className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                              title={entrega.finalizado ? "Descargar comprobante" : "Descargar hoja de firmas"}
                            >
                              <FaFilePdf />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
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
              {/* Datos del donante */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <FaUser /> Información del Donante
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">
                      Nombre del Donante *
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
                    <label className="block text-sm font-medium text-gray-600 mb-1">Tipo de Donante</label>
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
                    <label className="block text-sm font-medium text-gray-600 mb-1">RFC</label>
                    <input
                      type="text"
                      value={formData.donante_rfc}
                      onChange={(e) => setFormData({ ...formData, donante_rfc: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                      placeholder="RFC del donante"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Dirección</label>
                    <input
                      type="text"
                      value={formData.donante_direccion}
                      onChange={(e) => setFormData({ ...formData, donante_direccion: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                      placeholder="Dirección"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Contacto</label>
                    <input
                      type="text"
                      value={formData.donante_contacto}
                      onChange={(e) => setFormData({ ...formData, donante_contacto: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                      placeholder="Teléfono o email"
                    />
                  </div>
                </div>
              </div>

              {/* Datos de la donación */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <FaGift /> Datos de la Donación
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Número de Donación</label>
                    <input
                      type="text"
                      value={formData.numero}
                      onChange={(e) => setFormData({ ...formData, numero: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                      placeholder="DON-001"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Fecha de Donación</label>
                    <input
                      type="date"
                      value={formData.fecha_donacion}
                      onChange={(e) => setFormData({ ...formData, fecha_donacion: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Fecha de Recepción</label>
                    <input
                      type="date"
                      value={formData.fecha_recepcion}
                      onChange={(e) => setFormData({ ...formData, fecha_recepcion: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Documento/Referencia</label>
                    <input
                      type="text"
                      value={formData.documento_donacion}
                      onChange={(e) => setFormData({ ...formData, documento_donacion: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                      placeholder="Folio, factura, carta..."
                    />
                  </div>
                </div>
                <div className="grid grid-cols-1 gap-4 mt-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Notas</label>
                    <textarea
                      value={formData.notas}
                      onChange={(e) => setFormData({ ...formData, notas: e.target.value })}
                      rows={2}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                      placeholder="Observaciones adicionales..."
                    />
                  </div>
                </div>
              </div>

              {/* Productos donados */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <FaBox /> Productos Donados ({formData.detalles.length})
                </h3>

                {/* Formulario para agregar producto individual */}
                <div className="bg-gray-50 rounded-lg p-4 mb-4">
                  <p className="text-xs text-gray-500 mb-3">Agregar producto individual:</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3">
                    <div className="lg:col-span-2">
                      <label className="block text-xs font-medium text-gray-600 mb-1">Producto Donación *</label>
                      <div className="flex gap-2">
                        <select
                          value={detalleForm.producto_donacion}
                          onChange={(e) => setDetalleForm({ ...detalleForm, producto_donacion: e.target.value })}
                          className="flex-1 border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary"
                        >
                          <option value="">Seleccionar producto</option>
                          {productosDonacion.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.clave} - {p.nombre}
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          onClick={() => setShowQuickProductModal(true)}
                          className="px-3 py-2 rounded-lg text-white transition-colors flex items-center justify-center"
                          style={{ backgroundColor: COLORS.primary }}
                          title="Crear nuevo producto"
                        >
                          <FaPlus />
                        </button>
                      </div>
                      {productosDonacion.length === 0 && (
                        <p className="text-xs text-amber-600 mt-1">
                          No hay productos en el catálogo. Crea uno con el botón +
                        </p>
                      )}
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Lote</label>
                      <input
                        type="text"
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
                      <label className="block text-xs font-medium text-gray-600 mb-1">Caducidad</label>
                      <input
                        type="date"
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
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end gap-3">
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
                disabled={actionLoading === 'guardar'}
                className="px-6 py-2 rounded-lg text-white transition-colors disabled:opacity-50 flex items-center gap-2"
                style={{ backgroundColor: COLORS.primary }}
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

              {/* Info del donante */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div>
                  <span className="text-sm text-gray-500">Donante</span>
                  <p className="font-medium">{viewingDonacion.donante_nombre}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Tipo</span>
                  <p className="font-medium capitalize">{viewingDonacion.donante_tipo}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">RFC</span>
                  <p className="font-medium">{viewingDonacion.donante_rfc || '-'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Contacto</span>
                  <p className="font-medium">{viewingDonacion.donante_contacto || '-'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Fecha Donación</span>
                  <p className="font-medium">{formatFecha(viewingDonacion.fecha_donacion)}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Documento</span>
                  <p className="font-medium">{viewingDonacion.documento_donacion || '-'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Notas</span>
                  <p className="font-medium text-sm">{viewingDonacion.notas || '-'}</p>
                </div>
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

              {/* Notas */}
              {viewingDonacion.notas && (
                <div className="mt-6">
                  <h3 className="font-semibold text-gray-700 mb-2">Notas</h3>
                  <p className="text-gray-600 bg-gray-50 p-3 rounded-lg">{viewingDonacion.notas}</p>
                </div>
              )}
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

      {/* Modal de Registrar Salida de Donación */}
      {showSalidaModal && salidaDetalle && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
            {/* Header */}
            <div
              className="px-6 py-4 border-b flex items-center justify-between"
              style={{ backgroundColor: COLORS.primary }}
            >
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <FaHandHoldingMedical /> Registrar Salida Donación
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
                    <FaBuilding className="inline mr-1" /> Centro Destino *
                  </label>
                  <select
                    value={salidaForm.centro_destino}
                    onChange={(e) => setSalidaForm({ ...salidaForm, centro_destino: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                  >
                    <option value="">Seleccionar centro destino...</option>
                    {centros.map((centro) => (
                      <option key={centro.id} value={centro.id}>
                        {centro.nombre}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    Solo se puede entregar a centros registrados en el sistema
                  </p>
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
                    placeholder="Motivo de la salida"
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
                    <FaHandHoldingMedical /> Registrar Salida
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
                  <FaSpinner className="animate-spin text-3xl text-gray-400" />
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
                        <th className="px-4 py-3 text-center font-medium text-gray-600">Estado</th>
                        <th className="px-4 py-3 text-center font-medium text-gray-600">Acciones</th>
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
                          <td className="px-4 py-3 text-center">
                            {salida.finalizado ? (
                              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                                <FaCheckCircle />
                                Entregado
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">
                                <FaClock />
                                Pendiente
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <div className="flex items-center justify-center gap-1">
                              {/* Botón de PDF - muestra firmas si pendiente, sello si finalizado */}
                              <button
                                onClick={() => generarPdfSalida(salida.id)}
                                className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                title={salida.finalizado ? 'Ver comprobante de entrega' : 'Descargar hoja de firmas'}
                              >
                                <FaFilePdf />
                              </button>
                              {/* Botón de finalizar - solo si no está finalizado */}
                              {!salida.finalizado && (
                                <button
                                  onClick={() => {
                                    if (window.confirm('¿Marcar esta entrega como finalizada? El PDF mostrará un sello de ENTREGADO.')) {
                                      finalizarSalida(salida.id);
                                    }
                                  }}
                                  className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                                  title="Finalizar entrega (marcar como entregado)"
                                >
                                  <FaCheck />
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
                className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {actionLoading === 'guardarProducto' && <FaSpinner className="animate-spin" />}
                {editingProductoDonacion ? 'Actualizar' : 'Crear Producto'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========== MODAL: Carga Masiva de Productos ========== */}
      {showBulkAddModal && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b bg-gradient-to-r from-blue-600 to-indigo-600 rounded-t-xl">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <FaTable />
                Carga Masiva de Productos
              </h2>
              <p className="text-blue-100 text-sm mt-1">
                Pega o escribe varios productos a la vez desde Excel o texto
              </p>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6">
              {/* Instrucciones */}
              <div className="bg-blue-50 rounded-lg p-4 mb-4">
                <h4 className="font-medium text-blue-800 mb-2">📋 Formato esperado:</h4>
                <p className="text-sm text-blue-700 mb-2">
                  Pega una línea por producto, con los valores separados por <code className="bg-blue-100 px-1 rounded">|</code> <code className="bg-blue-100 px-1 rounded">,</code> <code className="bg-blue-100 px-1 rounded">;</code> o <code className="bg-blue-100 px-1 rounded">TAB</code>
                </p>
                <div className="bg-white rounded p-3 text-xs font-mono text-gray-700">
                  <div>CLAVE-001 | 100 | LOTE-ABC | 2025-12-31</div>
                  <div>CLAVE-002 , 50</div>
                  <div>Paracetamol ; 200 ; L123</div>
                </div>
                <p className="text-xs text-blue-600 mt-2">
                  ✓ Clave o nombre del producto (debe existir en el catálogo)<br/>
                  ✓ Cantidad (obligatorio)<br/>
                  ✓ Lote y Caducidad (opcionales)
                </p>
              </div>

              {/* Área de texto */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Pega aquí los productos:
                </label>
                <textarea
                  value={bulkText}
                  onChange={(e) => setBulkText(e.target.value)}
                  rows={8}
                  className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                  placeholder="Ejemplo:
DON-001 | 100 | LOTE-123 | 2025-12-31
DON-002 , 50
Paracetamol ; 200"
                />
              </div>

              {/* Botón de procesar */}
              <button
                onClick={handleParseBulkText}
                disabled={!bulkText.trim() || parsingBulk}
                className="w-full mb-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {parsingBulk ? <FaSpinner className="animate-spin" /> : <FaClipboardCheck />}
                Procesar Texto
              </button>

              {/* Vista previa de productos parseados */}
              {bulkProducts.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2 flex items-center gap-2">
                    <FaCheck className="text-green-500" />
                    {bulkProducts.length} productos listos para agregar:
                  </h4>
                  <div className="border rounded-lg overflow-hidden max-h-48 overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 border-b sticky top-0">
                        <tr>
                          <th className="px-3 py-2 text-left">Producto</th>
                          <th className="px-3 py-2 text-center">Cantidad</th>
                          <th className="px-3 py-2 text-left">Lote</th>
                          <th className="px-3 py-2 text-left">Caducidad</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {bulkProducts.map((p, idx) => (
                          <tr key={idx} className="hover:bg-gray-50">
                            <td className="px-3 py-2">
                              <span className="font-medium">{p.producto_clave}</span>
                              <span className="block text-xs text-gray-500">{p.producto_nombre}</span>
                            </td>
                            <td className="px-3 py-2 text-center font-bold text-blue-600">{p.cantidad}</td>
                            <td className="px-3 py-2 text-gray-600">{p.numero_lote || '-'}</td>
                            <td className="px-3 py-2 text-gray-600">{p.fecha_caducidad || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t bg-gray-50 rounded-b-xl flex justify-between">
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
                onClick={handleAddBulkProducts}
                disabled={bulkProducts.length === 0}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                <FaPlus />
                Agregar {bulkProducts.length} Productos
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========== MODAL RÁPIDO: Crear Producto desde Formulario de Donación ========== */}
      {showQuickProductModal && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
            <div className="px-6 py-4 border-b bg-gradient-to-r from-green-600 to-emerald-600 rounded-t-xl">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <FaPlus />
                Crear Producto Rápido
              </h2>
              <p className="text-green-100 text-sm mt-1">
                El producto se agregará al catálogo de donaciones
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
                    value={quickProductForm.clave}
                    onChange={(e) => setQuickProductForm({ ...quickProductForm, clave: e.target.value.toUpperCase() })}
                    className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    placeholder="Ej: DON-001"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Unidad de Medida
                  </label>
                  <select
                    value={quickProductForm.unidad_medida}
                    onChange={(e) => setQuickProductForm({ ...quickProductForm, unidad_medida: e.target.value })}
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
                  value={quickProductForm.nombre}
                  onChange={(e) => setQuickProductForm({ ...quickProductForm, nombre: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                  placeholder="Nombre completo del producto donado"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Presentación
                </label>
                <input
                  type="text"
                  value={quickProductForm.presentacion}
                  onChange={(e) => setQuickProductForm({ ...quickProductForm, presentacion: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                  placeholder="Ej: Caja con 30 tabletas de 500mg"
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t bg-gray-50 rounded-b-xl flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowQuickProductModal(false);
                  setQuickProductForm({ clave: '', nombre: '', unidad_medida: 'PIEZA', presentacion: '' });
                }}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleCrearProductoRapido}
                disabled={savingQuickProduct}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {savingQuickProduct && <FaSpinner className="animate-spin" />}
                Crear y Seleccionar
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
    </div>
  );
};

export default Donaciones;
