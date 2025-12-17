import { useState, useEffect, useCallback, useRef } from 'react';
import { donacionesAPI, productosAPI, centrosAPI, lotesAPI, salidasDonacionesAPI, detallesDonacionAPI } from '../services/api';
import { toast } from 'react-hot-toast';
import {
  FaPlus,
  FaEdit,
  FaTrash,
  FaEye,
  FaCheck,
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
} from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import { COLORS } from '../constants/theme';
import Pagination from '../components/Pagination';
import { usePermissions } from '../hooks/usePermissions';
import ConfirmModal from '../components/ConfirmModal';
import { esFarmaciaAdmin as checkEsFarmaciaAdmin } from '../utils/roles';

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

  // Salidas de donaciones (entregas)
  const [showSalidaModal, setShowSalidaModal] = useState(false);
  const [salidaDetalle, setSalidaDetalle] = useState(null);
  const [salidaForm, setSalidaForm] = useState({
    cantidad: '',
    destinatario: '',
    motivo: '',
    notas: '',
  });
  const [showHistorialModal, setShowHistorialModal] = useState(false);
  const [historialSalidas, setHistorialSalidas] = useState([]);
  const [loadingSalidas, setLoadingSalidas] = useState(false);

  // Sistema de Tabs: donaciones | inventario | entregas
  const [activeTab, setActiveTab] = useState('donaciones');
  
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
  
  // Importación/Exportación de entregas
  const [exportingEntregas, setExportingEntregas] = useState(false);
  const [importingEntregas, setImportingEntregas] = useState(false);
  
  // Importación/Exportación de donaciones
  const [exportingDonaciones, setExportingDonaciones] = useState(false);
  const [importingDonaciones, setImportingDonaciones] = useState(false);
  const fileInputRef = useRef(null); // Para entregas
  const donacionFileInputRef = useRef(null); // Para donaciones
  
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
  const [productos, setProductos] = useState([]);
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

  // Detalle en edición
  const [detalleForm, setDetalleForm] = useState({
    producto: '',
    numero_lote: '',
    cantidad: '',
    fecha_caducidad: '',
    estado_producto: 'bueno',
    notas: '',
  });

  const filtrosActivos = [searchTerm, filtroEstado, filtroTipoDonante, filtroCentro, filtroFechaDesde, filtroFechaHasta].filter(Boolean).length;

  // Cargar catálogos
  const cargarCatalogos = useCallback(async () => {
    try {
      const [prodRes, centrosRes] = await Promise.all([
        productosAPI.getAll({ page_size: 500, activo: true, ordering: 'descripcion' }),
        centrosAPI.getAll({ page_size: 100, activo: true, ordering: 'nombre' }),
      ]);
      setProductos(prodRes.data.results || prodRes.data || []);
      setCentros(centrosRes.data.results || centrosRes.data || []);
    } catch (err) {
      console.error('Error cargando catálogos:', err);
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

  // Descargar plantilla de importación
  const handleDescargarPlantilla = async () => {
    try {
      const response = await salidasDonacionesAPI.plantillaExcel();
      
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'plantilla_entregas_donaciones.xlsx';
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

  // Importar entregas desde Excel
  const handleImportarEntregas = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    setImportingEntregas(true);
    try {
      const formData = new FormData();
      formData.append('archivo', file);
      
      const response = await salidasDonacionesAPI.importarExcel(formData);
      
      const { resultados } = response.data;
      
      if (resultados.exitosos > 0) {
        toast.success(`${resultados.exitosos} entregas importadas correctamente`);
        cargarTodasEntregas();
        cargarInventarioDonaciones(); // Actualizar inventario también
      }
      
      if (resultados.fallidos > 0) {
        toast.error(`${resultados.fallidos} entregas fallaron`);
        // Mostrar errores detallados
        resultados.errores?.forEach((err, idx) => {
          if (idx < 3) { // Mostrar máximo 3 errores
            toast.error(`Fila ${err.fila}: ${err.error}`, { duration: 5000 });
          }
        });
      }
    } catch (err) {
      console.error('Error importando entregas:', err);
      const errorMsg = err.response?.data?.error || 'Error al importar entregas';
      toast.error(errorMsg);
    } finally {
      setImportingEntregas(false);
      // Limpiar input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

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

  useEffect(() => {
    cargarCatalogos();
  }, [cargarCatalogos]);

  useEffect(() => {
    if (activeTab === 'donaciones') {
      cargarDonaciones();
    } else if (activeTab === 'inventario') {
      cargarInventarioDonaciones();
    } else if (activeTab === 'entregas') {
      cargarTodasEntregas();
    }
  }, [activeTab, cargarDonaciones, cargarInventarioDonaciones, cargarTodasEntregas]);

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
      producto: '',
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

  // Agregar detalle al formulario
  const handleAgregarDetalle = () => {
    if (!detalleForm.producto || !detalleForm.cantidad) {
      toast.error('Selecciona un producto y cantidad');
      return;
    }

    const producto = productos.find((p) => p.id === parseInt(detalleForm.producto));
    const nuevoDetalle = {
      tempId: Date.now(),
      producto: parseInt(detalleForm.producto),
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
      producto: '',
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
    if (!formData.donante_nombre || !formData.centro_destino || formData.detalles.length === 0) {
      toast.error('Completa los campos obligatorios y agrega al menos un producto');
      return;
    }

    setActionLoading('guardar');
    try {
      const payload = {
        ...formData,
        centro_destino: parseInt(formData.centro_destino),
        detalles: formData.detalles.map((d) => ({
          producto: d.producto,
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
      destinatario: '',
      motivo: '',
      notas: '',
    });
    setShowSalidaModal(true);
  };

  // Registrar salida de donación
  const handleRegistrarSalida = async () => {
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
      toast.error(err.response?.data?.error || err.response?.data?.cantidad?.[0] || 'Error al registrar entrega');
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
        <div className="flex border-b">
          <button
            onClick={() => setActiveTab('donaciones')}
            className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors border-b-2 -mb-px ${
              activeTab === 'donaciones'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <FaGift /> Donaciones
          </button>
          <button
            onClick={() => setActiveTab('inventario')}
            className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors border-b-2 -mb-px ${
              activeTab === 'inventario'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <FaWarehouse /> Inventario
          </button>
          <button
            onClick={() => setActiveTab('entregas')}
            className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors border-b-2 -mb-px ${
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

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Centro Destino</label>
              <select
                value={filtroCentro}
                onChange={(e) => {
                  setFiltroCentro(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
              >
                <option value="">Todos los centros</option>
                {centros.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre}
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
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Centro Destino</th>
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
      </div>
        </>
      )}

      {/* ========== TAB: INVENTARIO DE DONACIONES ========== */}
      {activeTab === 'inventario' && (
        <>
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
              <button
                onClick={() => cargarInventarioDonaciones()}
                className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-gray-50 transition-colors"
              >
                <FaHistory /> Actualizar
              </button>
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

      {/* ========== TAB: HISTORIAL DE ENTREGAS ========== */}
      {activeTab === 'entregas' && (
        <>
          {/* Barra de búsqueda y acciones entregas */}
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
                
                {/* Botones de Importación - Solo para admin/farmacia */}
                {puede.crear && (
                  <>
                    {/* Descargar Plantilla */}
                    <button
                      onClick={handleDescargarPlantilla}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg border text-blue-700 border-blue-300 hover:bg-blue-50 transition-colors"
                      title="Descargar plantilla Excel"
                    >
                      <FaDownload /> Plantilla
                    </button>
                    
                    {/* Importar Excel */}
                    <label className="flex items-center gap-2 px-4 py-2 rounded-lg border text-purple-700 border-purple-300 hover:bg-purple-50 transition-colors cursor-pointer">
                      {importingEntregas ? (
                        <FaSpinner className="animate-spin" />
                      ) : (
                        <FaFileImport />
                      )}
                      Importar
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".xlsx,.xls"
                        onChange={handleImportarEntregas}
                        disabled={importingEntregas}
                        className="hidden"
                      />
                    </label>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Tabla de entregas */}
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            {loadingEntregas ? (
              <div className="flex items-center justify-center py-20">
                <FaSpinner className="animate-spin text-4xl text-gray-400" />
              </div>
            ) : todasEntregas.length === 0 ? (
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
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Producto</th>
                      <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Cantidad</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Destinatario</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Motivo</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Entregado por</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Donación</th>
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
                        <td className="px-4 py-3 text-sm text-gray-600">{entrega.entregado_por_nombre || '-'}</td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {entrega.detalle_donacion_info?.donacion_numero || '-'}
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
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Documento de Donación</label>
                    <input
                      type="text"
                      value={formData.documento_donacion}
                      onChange={(e) => setFormData({ ...formData, documento_donacion: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                      placeholder="Nº Factura, Carta de Donación, Acta, etc."
                    />
                  </div>
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
                  <FaBox /> Productos Donados
                </h3>

                {/* Formulario para agregar producto */}
                <div className="bg-gray-50 rounded-lg p-4 mb-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3">
                    <div className="lg:col-span-2">
                      <label className="block text-xs font-medium text-gray-600 mb-1">Producto *</label>
                      <select
                        value={detalleForm.producto}
                        onChange={(e) => setDetalleForm({ ...detalleForm, producto: e.target.value })}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary"
                      >
                        <option value="">Seleccionar producto</option>
                        {productos.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.clave} - {p.nombre}
                          </option>
                        ))}
                      </select>
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
                  <span className="text-sm text-gray-500">Centro Destino</span>
                  <p className="font-medium">{viewingDonacion.centro_destino_nombre || '-'}</p>
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
                  <input
                    type="text"
                    value={salidaForm.destinatario}
                    onChange={(e) => setSalidaForm({ ...salidaForm, destinatario: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    placeholder="Nombre del paciente/interno o área"
                  />
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
    </div>
  );
};

export default Donaciones;
