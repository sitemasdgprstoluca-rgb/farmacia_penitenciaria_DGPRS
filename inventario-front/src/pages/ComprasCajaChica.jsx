/**
 * Módulo: Compras de Caja Chica del Centro
 * 
 * PROPÓSITO:
 * Permitir al centro penitenciario gestionar compras con recursos propios
 * cuando farmacia central NO tiene disponibilidad de un medicamento.
 * 
 * FLUJO:
 * 1. Centro solicita medicamento → Farmacia NO tiene
 * 2. Centro crea solicitud de compra con justificación
 * 3. Se autoriza internamente (administrador/director)
 * 4. Se realiza la compra
 * 5. Se reciben productos y se ingresan al inventario del CENTRO
 * 
 * PERMISOS:
 * - Centro: CRUD completo sobre sus propias compras
 * - Farmacia: Solo lectura (auditoría) para prevenir malas prácticas
 */

import { useState, useEffect, useCallback } from 'react';
import { 
  comprasCajaChicaAPI, 
  detallesComprasCajaChicaAPI,
  productosAPI, 
  centrosAPI 
} from '../services/api';
import { toast } from 'react-hot-toast';
import {
  FaPlus,
  FaEdit,
  FaTrash,
  FaSearch,
  FaFilter,
  FaTimes,
  FaEye,
  FaHistory,
  FaCheck,
  FaBan,
  FaShoppingCart,
  FaClipboardList,
  FaBoxOpen,
  FaExclamationTriangle,
  FaInfoCircle,
  FaMoneyBillWave,
  FaFileInvoice,
  FaCalendarAlt,
  FaUserCheck,
  FaTruck,
} from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import Pagination from '../components/Pagination';
import ConfirmModal from '../components/ConfirmModal';
import { usePermissions } from '../hooks/usePermissions';
import { esFarmaciaAdmin, esCentro } from '../utils/roles';

const PAGE_SIZE = 20;

const ESTADOS_COMPRA = [
  { value: '', label: 'Todos' },
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'autorizada', label: 'Autorizada' },
  { value: 'comprada', label: 'Comprada' },
  { value: 'recibida', label: 'Recibida' },
  { value: 'cancelada', label: 'Cancelada' },
];

const ESTADO_COLORS = {
  pendiente: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  autorizada: 'bg-blue-100 text-blue-800 border-blue-300',
  comprada: 'bg-purple-100 text-purple-800 border-purple-300',
  recibida: 'bg-green-100 text-green-800 border-green-300',
  cancelada: 'bg-red-100 text-red-800 border-red-300',
};

const ESTADO_ICONS = {
  pendiente: FaClipboardList,
  autorizada: FaUserCheck,
  comprada: FaShoppingCart,
  recibida: FaBoxOpen,
  cancelada: FaBan,
};

const ComprasCajaChica = () => {
  const { user, verificarPermiso } = usePermissions();
  
  // Detectar tipo de usuario
  const esUsuarioFarmacia = esFarmaciaAdmin(user);
  const esUsuarioCentro = esCentro(user);
  const esSoloAuditoria = esUsuarioFarmacia; // Farmacia solo puede ver
  
  // Centro del usuario (para filtrado automático)
  const centroUsuario = user?.centro?.id || user?.centro_id;
  
  // Permisos (Centro puede CRUD, Farmacia solo lectura)
  const puedeCrear = esUsuarioCentro && !esSoloAuditoria;
  const puedeEditar = esUsuarioCentro && !esSoloAuditoria;
  const puedeAutorizar = esUsuarioCentro && !esSoloAuditoria;
  const puedeCancelar = esUsuarioCentro && !esSoloAuditoria;

  // Estados principales
  const [compras, setCompras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [resumen, setResumen] = useState(null);
  
  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [centroFiltro, setCentroFiltro] = useState(centroUsuario || '');
  const [estadoFiltro, setEstadoFiltro] = useState('');
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  
  // Listas auxiliares
  const [centros, setCentros] = useState([]);
  const [productos, setProductos] = useState([]);
  
  // Modal de formulario
  const [showModal, setShowModal] = useState(false);
  const [editingCompra, setEditingCompra] = useState(null);
  const [formData, setFormData] = useState({
    centro: centroUsuario || '',
    motivo_compra: '',
    proveedor_nombre: '',
    proveedor_contacto: '',
    observaciones: '',
    requisicion_origen: '',
    detalles: [],
  });
  
  // Detalle actual siendo agregado
  const [currentDetalle, setCurrentDetalle] = useState({
    producto: '',
    descripcion_producto: '',
    cantidad_solicitada: '',
    precio_unitario: '',
    presentacion: '',
    numero_lote: '',
    fecha_caducidad: '',
  });
  
  // Modales
  const [deleteModal, setDeleteModal] = useState({ show: false, compra: null });
  const [cancelModal, setCancelModal] = useState({ show: false, compra: null, motivo: '' });
  const [detailModal, setDetailModal] = useState({ show: false, compra: null });
  const [autorizarModal, setAutorizarModal] = useState({ show: false, compra: null, observaciones: '' });
  const [registrarCompraModal, setRegistrarCompraModal] = useState({ show: false, compra: null });
  const [recibirModal, setRecibirModal] = useState({ show: false, compra: null, detalles: [] });

  // Cargar centros
  useEffect(() => {
    const fetchCentros = async () => {
      try {
        const response = await centrosAPI.getAll({ activo: true, page_size: 100 });
        setCentros(response.data?.results || response.data || []);
      } catch (error) {
        console.error('Error al cargar centros:', error);
      }
    };
    // Solo cargar centros si es usuario de farmacia (para filtrar)
    if (esUsuarioFarmacia) {
      fetchCentros();
    }
  }, [esUsuarioFarmacia]);

  // Cargar productos
  useEffect(() => {
    const fetchProductos = async () => {
      try {
        const response = await productosAPI.getAll({ activo: true, page_size: 500 });
        setProductos(response.data?.results || response.data || []);
      } catch (error) {
        console.error('Error al cargar productos:', error);
      }
    };
    fetchProductos();
  }, []);

  // Cargar compras
  const fetchCompras = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page: currentPage,
        page_size: PAGE_SIZE,
        search: searchTerm || undefined,
        centro: centroFiltro || undefined,
        estado: estadoFiltro || undefined,
        fecha_desde: fechaDesde || undefined,
        fecha_hasta: fechaHasta || undefined,
      };
      
      const response = await comprasCajaChicaAPI.getAll(params);
      const data = response.data;
      
      setCompras(data?.results || data || []);
      setTotalItems(data?.count || data?.length || 0);
    } catch (error) {
      console.error('Error al cargar compras:', error);
      toast.error('Error al cargar compras de caja chica');
      setCompras([]);
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchTerm, centroFiltro, estadoFiltro, fechaDesde, fechaHasta]);

  useEffect(() => {
    fetchCompras();
  }, [fetchCompras]);

  // Cargar resumen
  const fetchResumen = useCallback(async () => {
    try {
      const params = centroFiltro ? { centro: centroFiltro } : {};
      const response = await comprasCajaChicaAPI.resumen(params);
      setResumen(response.data);
    } catch (error) {
      console.error('Error al cargar resumen:', error);
    }
  }, [centroFiltro]);

  useEffect(() => {
    fetchResumen();
  }, [fetchResumen]);

  // Handlers del formulario
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleDetalleChange = (e) => {
    const { name, value } = e.target;
    setCurrentDetalle(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Auto-llenar descripción cuando se selecciona producto
    if (name === 'producto' && value) {
      const producto = productos.find(p => p.id === parseInt(value));
      if (producto) {
        setCurrentDetalle(prev => ({
          ...prev,
          descripcion_producto: producto.nombre,
          presentacion: producto.presentacion || '',
        }));
      }
    }
  };

  // Agregar detalle a la lista
  const handleAddDetalle = () => {
    if (!currentDetalle.descripcion_producto || !currentDetalle.cantidad_solicitada) {
      toast.error('Debe completar al menos la descripción y cantidad');
      return;
    }
    
    const nuevoDetalle = {
      ...currentDetalle,
      id: Date.now(), // ID temporal para key
      importe: (parseFloat(currentDetalle.precio_unitario) || 0) * parseInt(currentDetalle.cantidad_solicitada),
    };
    
    setFormData(prev => ({
      ...prev,
      detalles: [...prev.detalles, nuevoDetalle]
    }));
    
    // Limpiar formulario de detalle
    setCurrentDetalle({
      producto: '',
      descripcion_producto: '',
      cantidad_solicitada: '',
      precio_unitario: '',
      presentacion: '',
      numero_lote: '',
      fecha_caducidad: '',
    });
  };

  // Eliminar detalle de la lista
  const handleRemoveDetalle = (detalleId) => {
    setFormData(prev => ({
      ...prev,
      detalles: prev.detalles.filter(d => d.id !== detalleId)
    }));
  };

  // Calcular total
  const calcularTotal = () => {
    return formData.detalles.reduce((total, detalle) => total + (detalle.importe || 0), 0);
  };

  // Abrir modal para nueva compra
  const handleNew = () => {
    setEditingCompra(null);
    setFormData({
      centro: centroUsuario || '',
      motivo_compra: '',
      proveedor_nombre: '',
      proveedor_contacto: '',
      observaciones: '',
      requisicion_origen: '',
      detalles: [],
    });
    setShowModal(true);
  };

  // Abrir modal para editar compra
  const handleEdit = (compra) => {
    setEditingCompra(compra);
    setFormData({
      centro: compra.centro?.id || compra.centro_id || '',
      motivo_compra: compra.motivo_compra || '',
      proveedor_nombre: compra.proveedor_nombre || '',
      proveedor_contacto: compra.proveedor_contacto || '',
      observaciones: compra.observaciones || '',
      requisicion_origen: compra.requisicion_origen?.id || '',
      detalles: (compra.detalles || []).map(d => ({
        ...d,
        importe: d.precio_unitario * d.cantidad_solicitada,
      })),
    });
    setShowModal(true);
  };

  // Guardar compra
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (formData.detalles.length === 0) {
      toast.error('Debe agregar al menos un producto');
      return;
    }
    
    try {
      const dataToSend = {
        ...formData,
        total: calcularTotal(),
        detalles: formData.detalles.map(d => ({
          producto: d.producto || null,
          descripcion_producto: d.descripcion_producto,
          cantidad_solicitada: parseInt(d.cantidad_solicitada),
          precio_unitario: parseFloat(d.precio_unitario) || 0,
          presentacion: d.presentacion,
          numero_lote: d.numero_lote,
          fecha_caducidad: d.fecha_caducidad || null,
        })),
      };
      
      if (editingCompra) {
        await comprasCajaChicaAPI.update(editingCompra.id, dataToSend);
        toast.success('Compra actualizada correctamente');
      } else {
        await comprasCajaChicaAPI.create(dataToSend);
        toast.success('Solicitud de compra creada correctamente');
      }
      
      setShowModal(false);
      fetchCompras();
      fetchResumen();
    } catch (error) {
      console.error('Error al guardar compra:', error);
      toast.error(error.response?.data?.detail || 'Error al guardar la compra');
    }
  };

  // Eliminar compra
  const handleDelete = async () => {
    if (!deleteModal.compra) return;
    
    try {
      await comprasCajaChicaAPI.delete(deleteModal.compra.id);
      toast.success('Compra eliminada correctamente');
      setDeleteModal({ show: false, compra: null });
      fetchCompras();
      fetchResumen();
    } catch (error) {
      toast.error('Error al eliminar la compra');
    }
  };

  // Autorizar compra
  const handleAutorizar = async () => {
    if (!autorizarModal.compra) return;
    
    try {
      await comprasCajaChicaAPI.autorizar(autorizarModal.compra.id, autorizarModal.observaciones);
      toast.success('Compra autorizada correctamente');
      setAutorizarModal({ show: false, compra: null, observaciones: '' });
      fetchCompras();
      fetchResumen();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al autorizar la compra');
    }
  };

  // Cancelar compra
  const handleCancelar = async () => {
    if (!cancelModal.compra || !cancelModal.motivo) {
      toast.error('Debe proporcionar un motivo de cancelación');
      return;
    }
    
    try {
      await comprasCajaChicaAPI.cancelar(cancelModal.compra.id, cancelModal.motivo);
      toast.success('Compra cancelada correctamente');
      setCancelModal({ show: false, compra: null, motivo: '' });
      fetchCompras();
      fetchResumen();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al cancelar la compra');
    }
  };

  // Ver detalles
  const handleViewDetails = async (compra) => {
    try {
      const response = await comprasCajaChicaAPI.getById(compra.id);
      setDetailModal({ show: true, compra: response.data });
    } catch (error) {
      toast.error('Error al cargar detalles');
    }
  };

  // Limpiar filtros
  const handleClearFilters = () => {
    setSearchTerm('');
    setCentroFiltro(centroUsuario || '');
    setEstadoFiltro('');
    setFechaDesde('');
    setFechaHasta('');
    setCurrentPage(1);
  };

  // Formatear moneda
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency: 'MXN'
    }).format(amount || 0);
  };

  // Formatear fecha
  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('es-MX', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  return (
    <div className="container mx-auto px-4 py-6">
      <PageHeader 
        title="Compras de Caja Chica" 
        subtitle={esSoloAuditoria 
          ? "Auditoría de compras del centro (solo lectura)"
          : "Gestión de compras con recursos propios del centro"
        }
        icon={<FaMoneyBillWave className="text-green-600" />}
      />

      {/* Banner informativo para auditoría */}
      {esSoloAuditoria && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-start gap-3">
          <FaInfoCircle className="text-blue-600 text-xl flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-blue-800">Modo Auditoría</h3>
            <p className="text-blue-700 text-sm">
              Como usuario de farmacia, puede visualizar todas las compras de caja chica 
              de los centros para prevenir malas prácticas, pero no puede modificarlas.
            </p>
          </div>
        </div>
      )}

      {/* Resumen de compras */}
      {resumen && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className="bg-white p-4 rounded-lg shadow border-l-4 border-yellow-400">
            <div className="text-2xl font-bold text-yellow-600">{resumen.pendientes || 0}</div>
            <div className="text-sm text-gray-500">Pendientes</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow border-l-4 border-blue-400">
            <div className="text-2xl font-bold text-blue-600">{resumen.autorizadas || 0}</div>
            <div className="text-sm text-gray-500">Autorizadas</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow border-l-4 border-purple-400">
            <div className="text-2xl font-bold text-purple-600">{resumen.compradas || 0}</div>
            <div className="text-sm text-gray-500">Compradas</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow border-l-4 border-green-400">
            <div className="text-2xl font-bold text-green-600">{resumen.recibidas || 0}</div>
            <div className="text-sm text-gray-500">Recibidas</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow border-l-4 border-gray-400">
            <div className="text-2xl font-bold text-gray-600">{formatCurrency(resumen.monto_total)}</div>
            <div className="text-sm text-gray-500">Monto Total</div>
          </div>
        </div>
      )}

      {/* Barra de acciones */}
      <div className="flex flex-wrap justify-between items-center gap-4 mb-6">
        {/* Búsqueda */}
        <div className="flex-1 min-w-[250px] max-w-md">
          <div className="relative">
            <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por folio, proveedor..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
          </div>
        </div>
        
        {/* Botones */}
        <div className="flex gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
              showFilters ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <FaFilter />
            Filtros
          </button>
          
          {puedeCrear && (
            <button
              onClick={handleNew}
              className="px-4 py-2 bg-green-600 text-white rounded-lg flex items-center gap-2 hover:bg-green-700 transition-colors"
            >
              <FaPlus />
              Nueva Compra
            </button>
          )}
        </div>
      </div>

      {/* Panel de filtros */}
      {showFilters && (
        <div className="bg-gray-50 p-4 rounded-lg mb-6 border">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Centro (solo para farmacia) */}
            {esUsuarioFarmacia && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Centro</label>
                <select
                  value={centroFiltro}
                  onChange={(e) => setCentroFiltro(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
                >
                  <option value="">Todos los centros</option>
                  {centros.map(centro => (
                    <option key={centro.id} value={centro.id}>{centro.nombre}</option>
                  ))}
                </select>
              </div>
            )}
            
            {/* Estado */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
              <select
                value={estadoFiltro}
                onChange={(e) => setEstadoFiltro(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
              >
                {ESTADOS_COMPRA.map(estado => (
                  <option key={estado.value} value={estado.value}>{estado.label}</option>
                ))}
              </select>
            </div>
            
            {/* Fecha desde */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Desde</label>
              <input
                type="date"
                value={fechaDesde}
                onChange={(e) => setFechaDesde(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
              />
            </div>
            
            {/* Fecha hasta */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Hasta</label>
              <input
                type="date"
                value={fechaHasta}
                onChange={(e) => setFechaHasta(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
              />
            </div>
          </div>
          
          <div className="flex justify-end mt-4">
            <button
              onClick={handleClearFilters}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 flex items-center gap-2"
            >
              <FaTimes />
              Limpiar filtros
            </button>
          </div>
        </div>
      )}

      {/* Tabla de compras */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Folio
                </th>
                {esUsuarioFarmacia && (
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Centro
                  </th>
                )}
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Fecha Solicitud
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Proveedor
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Productos
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Estado
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={esUsuarioFarmacia ? 8 : 7} className="px-4 py-8 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-600"></div>
                      <span className="text-gray-500">Cargando...</span>
                    </div>
                  </td>
                </tr>
              ) : compras.length === 0 ? (
                <tr>
                  <td colSpan={esUsuarioFarmacia ? 8 : 7} className="px-4 py-8 text-center text-gray-500">
                    No se encontraron compras de caja chica
                  </td>
                </tr>
              ) : (
                compras.map((compra) => {
                  const EstadoIcon = ESTADO_ICONS[compra.estado] || FaClipboardList;
                  return (
                    <tr key={compra.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="font-mono text-sm font-medium text-gray-900">
                          {compra.folio || '-'}
                        </span>
                      </td>
                      {esUsuarioFarmacia && (
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="text-sm text-gray-700">
                            {compra.centro?.nombre || compra.centro_nombre || '-'}
                          </span>
                        </td>
                      )}
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {formatDate(compra.fecha_solicitud)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                        {compra.proveedor_nombre || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {compra.detalles_count || compra.detalles?.length || 0} productos
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                        {formatCurrency(compra.total)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border ${ESTADO_COLORS[compra.estado] || 'bg-gray-100 text-gray-800'}`}>
                          <EstadoIcon className="text-[10px]" />
                          {compra.estado?.charAt(0).toUpperCase() + compra.estado?.slice(1)}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center">
                        <div className="flex items-center justify-center gap-1">
                          {/* Ver detalles */}
                          <button
                            onClick={() => handleViewDetails(compra)}
                            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                            title="Ver detalles"
                          >
                            <FaEye />
                          </button>
                          
                          {/* Editar (solo pendientes) */}
                          {puedeEditar && compra.estado === 'pendiente' && (
                            <button
                              onClick={() => handleEdit(compra)}
                              className="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg"
                              title="Editar"
                            >
                              <FaEdit />
                            </button>
                          )}
                          
                          {/* Autorizar */}
                          {puedeAutorizar && compra.estado === 'pendiente' && (
                            <button
                              onClick={() => setAutorizarModal({ show: true, compra, observaciones: '' })}
                              className="p-2 text-green-600 hover:bg-green-50 rounded-lg"
                              title="Autorizar"
                            >
                              <FaCheck />
                            </button>
                          )}
                          
                          {/* Cancelar */}
                          {puedeCancelar && !['recibida', 'cancelada'].includes(compra.estado) && (
                            <button
                              onClick={() => setCancelModal({ show: true, compra, motivo: '' })}
                              className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                              title="Cancelar"
                            >
                              <FaBan />
                            </button>
                          )}
                          
                          {/* Eliminar (solo pendientes) */}
                          {puedeEditar && compra.estado === 'pendiente' && (
                            <button
                              onClick={() => setDeleteModal({ show: true, compra })}
                              className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                              title="Eliminar"
                            >
                              <FaTrash />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        
        {/* Paginación */}
        {totalItems > PAGE_SIZE && (
          <div className="px-4 py-3 border-t">
            <Pagination
              currentPage={currentPage}
              totalItems={totalItems}
              pageSize={PAGE_SIZE}
              onPageChange={setCurrentPage}
            />
          </div>
        )}
      </div>

      {/* Modal de formulario */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white px-6 py-4 border-b flex justify-between items-center">
              <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                <FaShoppingCart className="text-green-600" />
                {editingCompra ? 'Editar Solicitud de Compra' : 'Nueva Solicitud de Compra'}
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <FaTimes />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-6">
              {/* Información general */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Motivo de la Compra *
                  </label>
                  <textarea
                    name="motivo_compra"
                    value={formData.motivo_compra}
                    onChange={handleInputChange}
                    required
                    rows={2}
                    placeholder="Ej: Medicamento no disponible en farmacia central"
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Proveedor
                  </label>
                  <input
                    type="text"
                    name="proveedor_nombre"
                    value={formData.proveedor_nombre}
                    onChange={handleInputChange}
                    placeholder="Nombre del proveedor"
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
                  />
                  <input
                    type="text"
                    name="proveedor_contacto"
                    value={formData.proveedor_contacto}
                    onChange={handleInputChange}
                    placeholder="Contacto/teléfono"
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 mt-2"
                  />
                </div>
              </div>
              
              {/* Agregar productos */}
              <div className="border rounded-lg p-4">
                <h3 className="text-lg font-medium text-gray-800 mb-4 flex items-center gap-2">
                  <FaBoxOpen className="text-green-600" />
                  Agregar Productos
                </h3>
                
                <div className="grid grid-cols-1 md:grid-cols-6 gap-3 mb-4">
                  <div className="md:col-span-2">
                    <label className="block text-xs font-medium text-gray-500 mb-1">Producto (opcional)</label>
                    <select
                      name="producto"
                      value={currentDetalle.producto}
                      onChange={handleDetalleChange}
                      className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-green-500"
                    >
                      <option value="">Seleccionar o escribir abajo</option>
                      {productos.map(producto => (
                        <option key={producto.id} value={producto.id}>
                          {producto.clave} - {producto.nombre}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-xs font-medium text-gray-500 mb-1">Descripción *</label>
                    <input
                      type="text"
                      name="descripcion_producto"
                      value={currentDetalle.descripcion_producto}
                      onChange={handleDetalleChange}
                      placeholder="Nombre del medicamento"
                      className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-green-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Cantidad *</label>
                    <input
                      type="number"
                      name="cantidad_solicitada"
                      value={currentDetalle.cantidad_solicitada}
                      onChange={handleDetalleChange}
                      min="1"
                      className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-green-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Precio Unit.</label>
                    <input
                      type="number"
                      name="precio_unitario"
                      value={currentDetalle.precio_unitario}
                      onChange={handleDetalleChange}
                      step="0.01"
                      min="0"
                      className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-green-500"
                    />
                  </div>
                </div>
                
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={handleAddDetalle}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg flex items-center gap-2 hover:bg-green-700"
                  >
                    <FaPlus />
                    Agregar Producto
                  </button>
                </div>
              </div>
              
              {/* Lista de productos agregados */}
              {formData.detalles.length > 0 && (
                <div className="border rounded-lg overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Producto</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Cantidad</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Precio Unit.</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Importe</th>
                        <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">Quitar</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {formData.detalles.map((detalle) => (
                        <tr key={detalle.id}>
                          <td className="px-4 py-2 text-sm">{detalle.descripcion_producto}</td>
                          <td className="px-4 py-2 text-sm">{detalle.cantidad_solicitada}</td>
                          <td className="px-4 py-2 text-sm">{formatCurrency(detalle.precio_unitario)}</td>
                          <td className="px-4 py-2 text-sm font-medium">{formatCurrency(detalle.importe)}</td>
                          <td className="px-4 py-2 text-center">
                            <button
                              type="button"
                              onClick={() => handleRemoveDetalle(detalle.id)}
                              className="text-red-600 hover:text-red-800"
                            >
                              <FaTrash />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="bg-gray-50">
                      <tr>
                        <td colSpan="3" className="px-4 py-2 text-right font-medium">Total:</td>
                        <td className="px-4 py-2 font-bold text-green-600">{formatCurrency(calcularTotal())}</td>
                        <td></td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )}
              
              {/* Observaciones */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Observaciones</label>
                <textarea
                  name="observaciones"
                  value={formData.observaciones}
                  onChange={handleInputChange}
                  rows={2}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
                />
              </div>
              
              {/* Botones */}
              <div className="flex justify-end gap-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2"
                >
                  <FaCheck />
                  {editingCompra ? 'Guardar Cambios' : 'Crear Solicitud'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal de detalles */}
      {detailModal.show && detailModal.compra && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white px-6 py-4 border-b flex justify-between items-center">
              <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                <FaFileInvoice className="text-green-600" />
                Detalle de Compra {detailModal.compra.folio}
              </h2>
              <button
                onClick={() => setDetailModal({ show: false, compra: null })}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <FaTimes />
              </button>
            </div>
            
            <div className="p-6 space-y-6">
              {/* Info general */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div>
                  <span className="text-xs text-gray-500">Centro</span>
                  <p className="font-medium">{detailModal.compra.centro?.nombre || '-'}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Estado</span>
                  <p className={`inline-flex items-center gap-1 px-2 py-1 rounded text-sm ${ESTADO_COLORS[detailModal.compra.estado]}`}>
                    {detailModal.compra.estado}
                  </p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Total</span>
                  <p className="font-bold text-green-600">{formatCurrency(detailModal.compra.total)}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Fecha Solicitud</span>
                  <p className="font-medium">{formatDate(detailModal.compra.fecha_solicitud)}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Proveedor</span>
                  <p className="font-medium">{detailModal.compra.proveedor_nombre || '-'}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Solicitante</span>
                  <p className="font-medium">{detailModal.compra.solicitante?.username || '-'}</p>
                </div>
              </div>
              
              {/* Motivo */}
              <div>
                <span className="text-xs text-gray-500">Motivo de la Compra</span>
                <p className="mt-1 p-3 bg-gray-50 rounded-lg">{detailModal.compra.motivo_compra}</p>
              </div>
              
              {/* Productos */}
              <div>
                <h3 className="font-medium text-gray-800 mb-2">Productos Solicitados</h3>
                <div className="border rounded-lg overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Producto</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Cant. Solic.</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Cant. Comp.</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">P. Unit.</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Importe</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {(detailModal.compra.detalles || []).map((detalle, idx) => (
                        <tr key={idx}>
                          <td className="px-4 py-2 text-sm">{detalle.descripcion_producto}</td>
                          <td className="px-4 py-2 text-sm">{detalle.cantidad_solicitada}</td>
                          <td className="px-4 py-2 text-sm">{detalle.cantidad_comprada || '-'}</td>
                          <td className="px-4 py-2 text-sm">{formatCurrency(detalle.precio_unitario)}</td>
                          <td className="px-4 py-2 text-sm font-medium">{formatCurrency(detalle.importe)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de confirmación de eliminación */}
      <ConfirmModal
        isOpen={deleteModal.show}
        onClose={() => setDeleteModal({ show: false, compra: null })}
        onConfirm={handleDelete}
        title="Eliminar Solicitud de Compra"
        message={`¿Está seguro de eliminar la solicitud ${deleteModal.compra?.folio}? Esta acción no se puede deshacer.`}
        confirmText="Eliminar"
        cancelText="Cancelar"
        type="danger"
      />

      {/* Modal de autorizar */}
      {autorizarModal.show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="px-6 py-4 border-b">
              <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <FaCheck className="text-green-600" />
                Autorizar Compra
              </h2>
            </div>
            <div className="p-6 space-y-4">
              <p>¿Está seguro de autorizar la compra <strong>{autorizarModal.compra?.folio}</strong>?</p>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Observaciones (opcional)</label>
                <textarea
                  value={autorizarModal.observaciones}
                  onChange={(e) => setAutorizarModal(prev => ({ ...prev, observaciones: e.target.value }))}
                  rows={3}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t flex justify-end gap-3">
              <button
                onClick={() => setAutorizarModal({ show: false, compra: null, observaciones: '' })}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                Cancelar
              </button>
              <button
                onClick={handleAutorizar}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Autorizar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de cancelar */}
      {cancelModal.show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="px-6 py-4 border-b">
              <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <FaBan className="text-red-600" />
                Cancelar Compra
              </h2>
            </div>
            <div className="p-6 space-y-4">
              <p>¿Está seguro de cancelar la compra <strong>{cancelModal.compra?.folio}</strong>?</p>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Motivo de cancelación *</label>
                <textarea
                  value={cancelModal.motivo}
                  onChange={(e) => setCancelModal(prev => ({ ...prev, motivo: e.target.value }))}
                  rows={3}
                  required
                  placeholder="Indique el motivo de la cancelación"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-red-500"
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t flex justify-end gap-3">
              <button
                onClick={() => setCancelModal({ show: false, compra: null, motivo: '' })}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                Volver
              </button>
              <button
                onClick={handleCancelar}
                disabled={!cancelModal.motivo}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                Cancelar Compra
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ComprasCajaChica;
