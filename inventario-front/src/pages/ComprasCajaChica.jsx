/**
 * Módulo: Compras de Caja Chica del Centro
 * 
 * PROPÓSITO:
 * Permitir al centro penitenciario gestionar compras con recursos propios
 * cuando farmacia central NO tiene disponibilidad de un medicamento.
 * 
 * FLUJO CON VERIFICACIÓN DE FARMACIA:
 * 1. Centro crea solicitud de compra con justificación (PENDIENTE)
 * 2. Centro envía a Farmacia para verificar stock (ENVIADA_FARMACIA)
 * 3. Farmacia verifica:
 *    - Si NO tiene stock → SIN_STOCK_FARMACIA (continúa flujo)
 *    - Si SÍ tiene stock → RECHAZADA_FARMACIA (debe hacer requisición regular)
 * 4. Centro envía a Admin para autorización (ENVIADA_ADMIN)
 * 5. Admin autoriza (AUTORIZADA_ADMIN)
 * 6. Admin envía a Director (ENVIADA_DIRECTOR)
 * 7. Director autoriza (AUTORIZADA)
 * 8. Se realiza la compra (COMPRADA)
 * 9. Se reciben productos (RECIBIDA)
 * 
 * PERMISOS:
 * - Centro (Médico): CRUD completo, enviar a farmacia, enviar a admin
 * - Farmacia: Verificar stock (confirmar sin stock / rechazar con stock)
 * - Admin: Autorizar, enviar a director
 * - Director: Autorizar final
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
  FaCheckCircle,
  FaWarehouse,
} from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import Pagination from '../components/Pagination';
import ConfirmModal from '../components/ConfirmModal';
import { usePermissions } from '../hooks/usePermissions';
import { esFarmaciaAdmin, esCentro } from '../utils/roles';

const PAGE_SIZE = 20;

// Estados del flujo con verificación de farmacia
const ESTADOS_COMPRA = [
  { value: '', label: 'Todos' },
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'enviada_farmacia', label: 'En Farmacia' },
  { value: 'sin_stock_farmacia', label: 'Sin Stock (Farmacia)' },
  { value: 'rechazada_farmacia', label: 'Hay Stock (Farmacia)' },
  { value: 'enviada_admin', label: 'Enviada a Admin' },
  { value: 'autorizada_admin', label: 'Autorizada Admin' },
  { value: 'enviada_director', label: 'Enviada a Director' },
  { value: 'autorizada', label: 'Autorizada' },
  { value: 'comprada', label: 'Comprada' },
  { value: 'recibida', label: 'Recibida' },
  { value: 'cancelada', label: 'Cancelada' },
  { value: 'rechazada', label: 'Rechazada' },
];

const ESTADO_COLORS = {
  pendiente: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  enviada_farmacia: 'bg-amber-100 text-amber-800 border-amber-300',
  sin_stock_farmacia: 'bg-teal-100 text-teal-800 border-teal-300',
  rechazada_farmacia: 'bg-rose-100 text-rose-800 border-rose-300',
  enviada_admin: 'bg-orange-100 text-orange-800 border-orange-300',
  autorizada_admin: 'bg-cyan-100 text-cyan-800 border-cyan-300',
  enviada_director: 'bg-indigo-100 text-indigo-800 border-indigo-300',
  autorizada: 'bg-blue-100 text-blue-800 border-blue-300',
  comprada: 'bg-purple-100 text-purple-800 border-purple-300',
  recibida: 'bg-green-100 text-green-800 border-green-300',
  cancelada: 'bg-red-100 text-red-800 border-red-300',
  rechazada: 'bg-red-100 text-red-800 border-red-300',
};

const ESTADO_ICONS = {
  pendiente: FaClipboardList,
  enviada_farmacia: FaSearch,
  sin_stock_farmacia: FaCheck,
  rechazada_farmacia: FaExclamationTriangle,
  enviada_admin: FaClipboardList,
  autorizada_admin: FaUserCheck,
  enviada_director: FaClipboardList,
  autorizada: FaUserCheck,
  comprada: FaShoppingCart,
  recibida: FaBoxOpen,
  cancelada: FaBan,
  rechazada: FaBan,
};

const ComprasCajaChica = () => {
  const { user, verificarPermiso } = usePermissions();
  
  // Detectar tipo de usuario y rol
  const esUsuarioFarmacia = esFarmaciaAdmin(user);
  const esUsuarioCentro = esCentro(user);
  const rolUsuario = user?.rol?.toLowerCase() || '';
  
  // Centro del usuario (para filtrado automático)
  const centroUsuario = user?.centro?.id || user?.centro_id;
  
  // Permisos según rol en el flujo con verificación de farmacia
  const puedeCrear = esUsuarioCentro && !esUsuarioFarmacia;
  const puedeEditar = esUsuarioCentro && !esUsuarioFarmacia;
  const esMedico = rolUsuario === 'medico' || rolUsuario === 'centro';
  const esAdmin = rolUsuario === 'administrador_centro' || rolUsuario === 'admin';
  const esDirector = rolUsuario === 'director_centro' || rolUsuario === 'director';
  // Farmacia puede verificar stock (no solo auditar)
  const puedeVerificarStock = esUsuarioFarmacia || rolUsuario === 'admin_farmacia' || user?.is_superuser;
  const puedeCancelar = esUsuarioCentro && !esUsuarioFarmacia;

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
  // Mostrar filtros expandidos por defecto para Farmacia
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
  const [registrarCompraModal, setRegistrarCompraModal] = useState({ 
    show: false, 
    compra: null, 
    fecha_compra: new Date().toISOString().split('T')[0],
    numero_factura: '',
    proveedor_nombre: '',
    proveedor_contacto: '',
    detalles: []
  });
  const [recibirModal, setRecibirModal] = useState({ show: false, compra: null, detalles: [] });
  const [stockRechazoModal, setStockRechazoModal] = useState({ show: false, compra: null, observaciones: '' });

  // Expandir filtros automáticamente para farmacia
  useEffect(() => {
    if (esUsuarioFarmacia) {
      setShowFilters(true);
    }
  }, [esUsuarioFarmacia]);

  // Cargar centros
  useEffect(() => {
    const fetchCentros = async () => {
      try {
        console.log('Cargando centros para usuario farmacia...');
        const response = await centrosAPI.getAll({ activo: true, page_size: 100 });
        const data = response.data?.results || response.data || [];
        console.log('Centros cargados:', data.length);
        setCentros(data);
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
    // Validar campos obligatorios del detalle
    if (!currentDetalle.descripcion_producto?.trim()) {
      toast.error('Debe ingresar la descripción del producto');
      return;
    }
    if (!currentDetalle.cantidad_solicitada || parseInt(currentDetalle.cantidad_solicitada) <= 0) {
      toast.error('Debe ingresar una cantidad válida mayor a 0');
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
  // ISS-SEC FIX: Validar permisos antes de enviar a API (defensa en profundidad)
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // ISS-SEC FIX: Validación de permisos en handler (no solo en UI)
    if (editingCompra) {
      if (!puedeEditar) {
        toast.error('No tienes permisos para editar compras');
        return;
      }
      // Verificar que el estado permite edición
      if (!['pendiente', 'rechazada', 'devuelta', 'rechazada_farmacia'].includes(editingCompra.estado)) {
        toast.error('Esta compra no puede ser editada en su estado actual');
        return;
      }
    } else {
      if (!puedeCrear) {
        toast.error('No tienes permisos para crear compras');
        return;
      }
    }
    
    // Validar motivo de compra (obligatorio)
    if (!formData.motivo_compra?.trim()) {
      toast.error('Debe ingresar el motivo de la compra');
      return;
    }
    
    // Validar que haya al menos un producto
    if (formData.detalles.length === 0) {
      toast.error('Debe agregar al menos un producto');
      return;
    }
    
    // Validar que todos los detalles tengan descripción y cantidad válida
    const detallesInvalidos = formData.detalles.filter(
      d => !d.descripcion_producto?.trim() || !d.cantidad_solicitada || parseInt(d.cantidad_solicitada) <= 0
    );
    if (detallesInvalidos.length > 0) {
      toast.error('Todos los productos deben tener descripción y cantidad válida');
      return;
    }
    
    try {
      const dataToSend = {
        centro: formData.centro || undefined,
        motivo_compra: formData.motivo_compra,
        proveedor_nombre: formData.proveedor_nombre || undefined,
        observaciones: formData.observaciones,
        requisicion_origen: formData.requisicion_origen || undefined,
        // El backend espera 'detalles_write' para crear detalles anidados
        detalles_write: formData.detalles.map(d => ({
          producto: d.producto || null,
          descripcion_producto: d.descripcion_producto,
          cantidad: parseInt(d.cantidad_solicitada) || 1,
          unidad: d.presentacion || 'PIEZA',
          precio_unitario: parseFloat(d.precio_unitario) || 0,
          numero_lote: d.numero_lote || '',
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
    
    const compra = deleteModal.compra;
    const estadoCompra = compra.estado;
    
    // Estados que se consideran "confirmados" (ya pasaron del pendiente)
    const estadosConfirmados = [
      'enviada_farmacia', 'sin_stock_farmacia', 'enviada_admin', 
      'autorizada_admin', 'enviada_director', 'autorizada', 
      'comprada', 'recibida'
    ];
    
    // Si está confirmada, solo admin de farmacia puede eliminar
    if (estadosConfirmados.includes(estadoCompra)) {
      if (!esUsuarioFarmacia && !user?.is_superuser) {
        toast.error('Solo el administrador de farmacia puede eliminar compras confirmadas');
        setDeleteModal({ show: false, compra: null });
        return;
      }
    }
    
    // Si está cancelada o rechazada, no se puede eliminar
    if (['cancelada', 'rechazada', 'rechazada_farmacia'].includes(estadoCompra)) {
      toast.error('No se puede eliminar una compra cancelada o rechazada');
      setDeleteModal({ show: false, compra: null });
      return;
    }
    
    try {
      await comprasCajaChicaAPI.delete(compra.id);
      toast.success('Compra eliminada correctamente');
      setDeleteModal({ show: false, compra: null });
      fetchCompras();
      fetchResumen();
    } catch (error) {
      const errorMsg = error.response?.data?.error || error.response?.data?.detail || 'Error al eliminar la compra';
      toast.error(errorMsg);
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

  // ========== FLUJO MULTINIVEL: ACCIONES ==========
  
  // Validar que la compra tenga todos los datos necesarios
  const validarCompraCompleta = (compra, accion = 'procesar') => {
    const productosCount = compra.detalles_count || compra.detalles?.length || 0;
    const total = parseFloat(compra.total) || 0;
    
    if (productosCount === 0) {
      toast.error(`No se puede ${accion}: La compra no tiene productos`);
      return false;
    }
    if (total <= 0) {
      toast.error(`No se puede ${accion}: La compra no tiene monto total`);
      return false;
    }
    if (!compra.proveedor_nombre || compra.proveedor_nombre.trim() === '' || compra.proveedor_nombre === '-') {
      toast.error(`No se puede ${accion}: Debe especificar el proveedor`);
      return false;
    }
    return true;
  };
  
  // Enviar a Farmacia para verificación de stock (Médico/Centro)
  const handleEnviarFarmacia = async (compra) => {
    if (!validarCompraCompleta(compra, 'enviar a farmacia')) return;
    try {
      await comprasCajaChicaAPI.enviarFarmacia(compra.id);
      toast.success('Solicitud enviada a Farmacia para verificación de stock');
      fetchCompras();
      fetchResumen();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al enviar a farmacia');
    }
  };

  // Confirmar que no hay stock (Farmacia)
  const handleConfirmarSinStock = async (compra, observaciones = '') => {
    try {
      await comprasCajaChicaAPI.confirmarSinStock(compra.id, { observaciones });
      toast.success('Stock verificado - No disponible. Solicitud enviada a administrador');
      fetchCompras();
      fetchResumen();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al confirmar sin stock');
    }
  };

  // Rechazar porque sí hay stock (Farmacia)
  const handleRechazarTieneStock = async (compra, observaciones = '') => {
    if (!observaciones) {
      toast.error('Debe indicar el producto disponible en farmacia');
      return;
    }
    try {
      await comprasCajaChicaAPI.rechazarTieneStock(compra.id, { observaciones });
      toast.success('Solicitud rechazada - Producto disponible en farmacia');
      fetchCompras();
      fetchResumen();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al rechazar');
    }
  };

  // Enviar a Admin (Médico)
  const handleEnviarAdmin = async (compra) => {
    if (!validarCompraCompleta(compra, 'enviar a administrador')) return;
    try {
      await comprasCajaChicaAPI.enviarAdmin(compra.id);
      toast.success('Solicitud enviada al administrador');
      fetchCompras();
      fetchResumen();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al enviar solicitud');
    }
  };

  // Autorizar como Admin
  const handleAutorizarAdmin = async (compra, observaciones = '') => {
    if (!validarCompraCompleta(compra, 'autorizar')) return;
    try {
      await comprasCajaChicaAPI.autorizarAdmin(compra.id, { observaciones });
      toast.success('Solicitud autorizada por administrador');
      fetchCompras();
      fetchResumen();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al autorizar');
    }
  };

  // Enviar a Director (Admin)
  const handleEnviarDirector = async (compra) => {
    if (!validarCompraCompleta(compra, 'enviar a director')) return;
    try {
      await comprasCajaChicaAPI.enviarDirector(compra.id);
      toast.success('Solicitud enviada al director');
      fetchCompras();
      fetchResumen();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al enviar solicitud');
    }
  };

  // Autorizar como Director
  const handleAutorizarDirector = async (compra, observaciones = '') => {
    if (!validarCompraCompleta(compra, 'autorizar')) return;
    try {
      await comprasCajaChicaAPI.autorizarDirector(compra.id, { observaciones });
      toast.success('Solicitud autorizada - Lista para compra');
      fetchCompras();
      fetchResumen();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al autorizar');
    }
  };

  // Rechazar solicitud
  const handleRechazar = async (compra, motivo) => {
    if (!motivo) {
      toast.error('Debe proporcionar un motivo de rechazo');
      return;
    }
    try {
      await comprasCajaChicaAPI.rechazar(compra.id, { motivo });
      toast.success('Solicitud rechazada');
      fetchCompras();
      fetchResumen();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al rechazar');
    }
  };

  // Devolver para corrección
  const handleDevolver = async (compra, observaciones) => {
    try {
      await comprasCajaChicaAPI.devolver(compra.id, { observaciones });
      toast.success('Solicitud devuelta para corrección');
      fetchCompras();
      fetchResumen();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al devolver');
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

  // ========== REGISTRAR COMPRA REALIZADA ==========
  const handleOpenRegistrarCompra = async (compra) => {
    try {
      const response = await comprasCajaChicaAPI.getById(compra.id);
      const compraCompleta = response.data;
      
      setRegistrarCompraModal({
        show: true,
        compra: compraCompleta,
        // ISS-SEC FIX: Usar fecha LOCAL para evitar desfase de zona horaria
        fecha_compra: (() => {
          const hoy = new Date();
          return `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}-${String(hoy.getDate()).padStart(2, '0')}`;
        })(),
        numero_factura: compraCompleta.numero_factura || '',
        proveedor_nombre: compraCompleta.proveedor_nombre || '',
        proveedor_contacto: compraCompleta.proveedor_contacto || '',
        detalles: (compraCompleta.detalles || []).map(d => ({
          ...d,
          cantidad_comprada: d.cantidad_comprada || d.cantidad_solicitada,
          precio_unitario: d.precio_unitario || 0,
          numero_lote: d.numero_lote || '',
          fecha_caducidad: d.fecha_caducidad || '',
        }))
      });
    } catch (error) {
      toast.error('Error al cargar detalles de la compra');
    }
  };

  const handleRegistrarCompra = async () => {
    if (!registrarCompraModal.compra) return;
    
    if (!registrarCompraModal.fecha_compra) {
      toast.error('Debe proporcionar la fecha de compra');
      return;
    }
    
    // ISS-SEC FIX: Validar que todas las cantidades compradas sean > 0
    const detallesInvalidos = registrarCompraModal.detalles.filter(d => {
      const cantidad = parseInt(d.cantidad_comprada);
      return isNaN(cantidad) || cantidad <= 0;
    });
    
    if (detallesInvalidos.length > 0) {
      toast.error(`Todas las cantidades compradas deben ser mayores a 0. ${detallesInvalidos.length} producto(s) con cantidad inválida.`);
      return;
    }
    
    try {
      await comprasCajaChicaAPI.registrarCompra(registrarCompraModal.compra.id, {
        fecha_compra: registrarCompraModal.fecha_compra,
        numero_factura: registrarCompraModal.numero_factura,
        proveedor_nombre: registrarCompraModal.proveedor_nombre,
        proveedor_contacto: registrarCompraModal.proveedor_contacto,
        detalles: registrarCompraModal.detalles.map(d => ({
          id: d.id,
          cantidad_comprada: parseInt(d.cantidad_comprada) || 0,
          precio_unitario: parseFloat(d.precio_unitario) || 0,
          numero_lote: d.numero_lote,
          fecha_caducidad: d.fecha_caducidad || null,
        }))
      });
      
      toast.success('Compra registrada correctamente');
      // ISS-SEC FIX: Usar fecha LOCAL para evitar desfase de zona horaria
      const hoy = new Date();
      const fechaLocal = `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}-${String(hoy.getDate()).padStart(2, '0')}`;
      setRegistrarCompraModal({ 
        show: false, 
        compra: null, 
        fecha_compra: fechaLocal,
        numero_factura: '',
        proveedor_nombre: '',
        proveedor_contacto: '',
        detalles: [] 
      });
      fetchCompras();
      fetchResumen();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al registrar la compra');
    }
  };

  // ========== REGISTRAR RECEPCIÓN ==========
  const handleOpenRecibir = async (compra) => {
    try {
      const response = await comprasCajaChicaAPI.getById(compra.id);
      const compraCompleta = response.data;
      
      setRecibirModal({
        show: true,
        compra: compraCompleta,
        detalles: (compraCompleta.detalles || []).map(d => ({
          ...d,
          cantidad_recibida: d.cantidad_recibida || d.cantidad_comprada || d.cantidad_solicitada,
        }))
      });
    } catch (error) {
      toast.error('Error al cargar detalles de la compra');
    }
  };

  const handleRecibir = async () => {
    if (!recibirModal.compra) return;
    
    // ISS-SEC FIX: Validar que todas las cantidades recibidas sean > 0
    const detallesInvalidos = recibirModal.detalles.filter(d => {
      const cantidad = parseInt(d.cantidad_recibida);
      return isNaN(cantidad) || cantidad <= 0;
    });
    
    if (detallesInvalidos.length > 0) {
      toast.error(`Todas las cantidades recibidas deben ser mayores a 0. ${detallesInvalidos.length} producto(s) con cantidad inválida.`);
      return;
    }
    
    try {
      await comprasCajaChicaAPI.recibir(recibirModal.compra.id, recibirModal.detalles.map(d => ({
        id: d.id,
        cantidad_recibida: parseInt(d.cantidad_recibida) || 0,
      })));
      
      toast.success('Productos recibidos correctamente - Agregados al inventario de caja chica');
      setRecibirModal({ show: false, compra: null, detalles: [] });
      fetchCompras();
      fetchResumen();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al registrar la recepción');
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
    <div className="p-4 md:p-6 space-y-4 md:space-y-6">
      <PageHeader 
        title="Compras de Caja Chica" 
        subtitle={puedeVerificarStock && !esUsuarioCentro
          ? "Verificación de stock para compras del centro"
          : "Gestión de compras con recursos propios del centro"
        }
        icon={FaMoneyBillWave}
      />

      {/* Banner informativo para farmacia */}
      {puedeVerificarStock && !esUsuarioCentro && (
        <div className="p-3 md:p-4 bg-purple-50 border border-purple-200 rounded-xl flex items-start gap-3">
          <FaInfoCircle className="text-purple-600 text-lg md:text-xl flex-shrink-0 mt-0.5" />
          <div className="min-w-0">
            <h3 className="font-semibold text-purple-800 text-sm md:text-base">Verificación de Stock</h3>
            <p className="text-purple-700 text-xs md:text-sm leading-relaxed">
              Como usuario de farmacia, debe verificar la disponibilidad de productos antes 
              de que el centro pueda proceder con compras de caja chica. Si hay stock disponible, 
              rechace la solicitud para que el centro haga una requisición normal.
            </p>
          </div>
        </div>
      )}

      {/* Resumen de compras */}
      {resumen && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 md:gap-4">
          <div className="bg-white p-3 md:p-4 rounded-xl shadow-sm border-l-4 border-yellow-400 hover:shadow-md transition-shadow">
            <div className="text-xl md:text-2xl font-bold text-yellow-600">{resumen.pendientes || 0}</div>
            <div className="text-xs md:text-sm text-gray-500">Pendientes</div>
          </div>
          <div className="bg-white p-3 md:p-4 rounded-xl shadow-sm border-l-4 border-blue-400 hover:shadow-md transition-shadow">
            <div className="text-xl md:text-2xl font-bold text-blue-600">{resumen.autorizadas || 0}</div>
            <div className="text-xs md:text-sm text-gray-500">Autorizadas</div>
          </div>
          <div className="bg-white p-3 md:p-4 rounded-xl shadow-sm border-l-4 border-purple-400 hover:shadow-md transition-shadow">
            <div className="text-xl md:text-2xl font-bold text-purple-600">{resumen.compradas || 0}</div>
            <div className="text-xs md:text-sm text-gray-500">Compradas</div>
          </div>
          <div className="bg-white p-3 md:p-4 rounded-xl shadow-sm border-l-4 border-green-400 hover:shadow-md transition-shadow">
            <div className="text-xl md:text-2xl font-bold text-green-600">{resumen.recibidas || 0}</div>
            <div className="text-xs md:text-sm text-gray-500">Recibidas</div>
          </div>
          <div className="bg-white p-3 md:p-4 rounded-xl shadow-sm border-l-4 border-gray-400 hover:shadow-md transition-shadow col-span-2 sm:col-span-1">
            <div className="text-xl md:text-2xl font-bold text-gray-600">{formatCurrency(resumen.monto_total)}</div>
            <div className="text-xs md:text-sm text-gray-500">Monto Total</div>
          </div>
        </div>
      )}

      {/* Barra de acciones y filtros */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-3 md:p-4">
        {/* Búsqueda y botones */}
        <div className="flex flex-col sm:flex-row gap-3 justify-between items-stretch sm:items-center">
          <div className="relative flex-1 max-w-full sm:max-w-sm">
            <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por folio, proveedor..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
          </div>
          
          <div className="flex gap-2 flex-shrink-0">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`px-3 py-2 rounded-lg flex items-center gap-2 text-sm transition-colors ${
                showFilters ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <FaFilter className="text-xs" />
              <span className="hidden sm:inline">Filtros</span>
            </button>
            
            {puedeCrear && (
              <button
                onClick={handleNew}
                className="px-3 py-2 bg-green-600 text-white rounded-lg flex items-center gap-2 text-sm hover:bg-green-700 transition-colors"
              >
                <FaPlus className="text-xs" />
                <span className="hidden sm:inline">Nueva Compra</span>
              </button>
            )}
          </div>
        </div>

        {/* Panel de filtros colapsable */}
        {showFilters && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {/* Centro (solo para farmacia) */}
              {esUsuarioFarmacia && (
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Centro</label>
                  <select
                    value={centroFiltro}
                    onChange={(e) => setCentroFiltro(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-green-500"
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
                <label className="block text-xs font-medium text-gray-700 mb-1">Estado</label>
                <select
                  value={estadoFiltro}
                  onChange={(e) => setEstadoFiltro(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-green-500"
                >
                  {ESTADOS_COMPRA.map(estado => (
                    <option key={estado.value} value={estado.value}>{estado.label}</option>
                  ))}
                </select>
              </div>
              
              {/* Fecha desde */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Desde</label>
                <input
                  type="date"
                  value={fechaDesde}
                  onChange={(e) => setFechaDesde(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-green-500"
                />
              </div>
              
              {/* Fecha hasta */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Hasta</label>
                <input
                  type="date"
                  value={fechaHasta}
                  onChange={(e) => setFechaHasta(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-green-500"
                />
              </div>
            </div>
            
            <div className="flex justify-end mt-3">
              <button
                onClick={handleClearFilters}
                className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 flex items-center gap-2"
              >
                <FaTimes className="text-xs" />
                Limpiar
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Tabla de compras */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        <div className="w-full overflow-x-auto">
          <table className="w-full min-w-[900px] divide-y divide-gray-200 text-sm">
            <thead className="bg-theme-gradient sticky top-0 z-10">
              <tr>
                <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                  Folio
                </th>
                {esUsuarioFarmacia && (
                  <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white">
                    Centro
                  </th>
                )}
                <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                  Solicitud
                </th>
                <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                  Captura
                </th>
                <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                  Proveedor
                </th>
                <th className="px-3 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                  Productos
                </th>
                <th className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                  Total
                </th>
                <th className="px-3 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                  Estado
                </th>
                <th className="px-3 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan={esUsuarioFarmacia ? 9 : 8} className="px-4 py-8 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-600"></div>
                      <span className="text-gray-500">Cargando...</span>
                    </div>
                  </td>
                </tr>
              ) : compras.length === 0 ? (
                <tr>
                  <td colSpan={esUsuarioFarmacia ? 9 : 8} className="px-4 py-8 text-center text-gray-500">
                    No se encontraron compras de caja chica
                  </td>
                </tr>
              ) : (
                compras.map((compra) => {
                  const EstadoIcon = ESTADO_ICONS[compra.estado] || FaClipboardList;
                  return (
                    <tr key={compra.id} className="hover:bg-gray-50">
                      <td className="px-3 py-2.5 whitespace-nowrap">
                        <span className="font-mono text-xs font-medium text-gray-900">
                          {compra.folio || '-'}
                        </span>
                      </td>
                      {esUsuarioFarmacia && (
                        <td className="px-3 py-2.5">
                          <span className="text-xs text-gray-700 line-clamp-2 max-w-[200px]" title={compra.centro?.nombre || compra.centro_nombre}>
                            {compra.centro?.nombre || compra.centro_nombre || '-'}
                          </span>
                        </td>
                      )}
                      <td className="px-3 py-2.5 whitespace-nowrap text-xs text-gray-600">
                        {formatDate(compra.fecha_solicitud)}
                      </td>
                      <td className="px-3 py-2.5 whitespace-nowrap">
                        <span className="text-xs text-gray-600" title="Fecha de captura del registro">
                          {compra.created_at ? new Date(compra.created_at).toLocaleString('es-MX', {
                            day: '2-digit',
                            month: '2-digit',
                            year: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit'
                          }) : formatDate(compra.fecha_solicitud)}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-xs text-gray-700 max-w-[120px] truncate">
                        {compra.proveedor_nombre || '-'}
                      </td>
                      <td className="px-3 py-2.5 whitespace-nowrap text-xs text-gray-600 text-center">
                        {compra.detalles_count || compra.detalles?.length || 0}
                      </td>
                      <td className="px-3 py-2.5 whitespace-nowrap text-xs font-semibold text-gray-900 text-right">
                        {formatCurrency(compra.total)}
                      </td>
                      <td className="px-3 py-2.5 whitespace-nowrap text-center">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border ${ESTADO_COLORS[compra.estado] || 'bg-gray-100 text-gray-800'}`}>
                          <EstadoIcon className="text-[8px]" />
                          {compra.estado?.replace(/_/g, ' ')?.charAt(0).toUpperCase() + compra.estado?.replace(/_/g, ' ')?.slice(1)}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 whitespace-nowrap text-center">
                        <div className="flex items-center justify-center gap-0.5">
                          {/* Ver detalles */}
                          <button
                            onClick={() => handleViewDetails(compra)}
                            className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg"
                            title="Ver detalles"
                          >
                            <FaEye className="text-xs" />
                          </button>
                          
                          {/* Editar (solo pendientes o rechazadas) */}
                          {puedeEditar && ['pendiente', 'rechazada'].includes(compra.estado) && (
                            <button
                              onClick={() => handleEdit(compra)}
                              className="p-1.5 text-yellow-600 hover:bg-yellow-50 rounded-lg"
                              title="Editar"
                            >
                              <FaEdit className="text-xs" />
                            </button>
                          )}
                          
                          {/* REGISTRAR COMPRA REALIZADA - cuando está autorizada */}
                          {esUsuarioCentro && compra.estado === 'autorizada' && (
                            <button
                              onClick={() => handleOpenRegistrarCompra(compra)}
                              className="p-1.5 text-purple-600 hover:bg-purple-50 rounded-lg"
                              title="Registrar Compra Realizada"
                            >
                              <FaShoppingCart className="text-xs" />
                            </button>
                          )}
                          
                          {/* REGISTRAR RECEPCIÓN - cuando está comprada */}
                          {esUsuarioCentro && compra.estado === 'comprada' && (
                            <button
                              onClick={() => handleOpenRecibir(compra)}
                              className="p-1.5 text-green-600 hover:bg-green-50 rounded-lg"
                              title="Registrar Recepción de Productos"
                            >
                              <FaTruck className="text-xs" />
                            </button>
                          )}
                                                    {/* FLUJO FARMACIA: Enviar a Farmacia para verificar stock (Médico/Centro) */}
                          {esMedico && compra.estado === 'pendiente' && compra.detalles?.length > 0 && (
                            <button
                              onClick={() => handleEnviarFarmacia(compra)}
                              className="p-1.5 text-purple-600 hover:bg-purple-50 rounded-lg"
                              title="Enviar a Farmacia (verificar stock)"
                            >
                              <FaSearch className="text-xs" />
                            </button>
                          )}
                          
                          {/* FLUJO FARMACIA: Confirmar que no hay stock (Farmacia) */}
                          {puedeVerificarStock && compra.estado === 'enviada_farmacia' && (
                            <button
                              onClick={() => handleConfirmarSinStock(compra, 'Verificado - No hay stock disponible')}
                              className="p-1.5 text-green-600 hover:bg-green-50 rounded-lg"
                              title="Confirmar: No hay stock disponible"
                            >
                              <FaCheckCircle className="text-xs" />
                            </button>
                          )}
                          
                          {/* FLUJO FARMACIA: Rechazar porque sí hay stock (Farmacia) */}
                          {puedeVerificarStock && compra.estado === 'enviada_farmacia' && (
                            <button
                              onClick={() => setStockRechazoModal({ show: true, compra, observaciones: '' })}
                              className="p-1.5 text-orange-600 hover:bg-orange-50 rounded-lg"
                              title="Rechazar: Hay stock disponible"
                            >
                              <FaWarehouse className="text-xs" />
                            </button>
                          )}
                          
                          {/* FLUJO MULTINIVEL: Enviar a Admin (tras confirmación de Farmacia) */}
                          {esMedico && compra.estado === 'sin_stock_farmacia' && (
                            <button
                              onClick={() => handleEnviarAdmin(compra)}
                              className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg"
                              title="Enviar a Admin"
                            >
                              <FaCheck className="text-xs" />
                            </button>
                          )}
                          
                          {/* FLUJO MULTINIVEL: Autorizar como Admin */}
                          {esAdmin && compra.estado === 'enviada_admin' && (
                            <button
                              onClick={() => handleAutorizarAdmin(compra)}
                              className="p-1.5 text-green-600 hover:bg-green-50 rounded-lg"
                              title="Autorizar como Admin"
                            >
                              <FaUserCheck className="text-xs" />
                            </button>
                          )}
                          
                          {/* FLUJO MULTINIVEL: Enviar a Director (Admin) */}
                          {esAdmin && compra.estado === 'autorizada_admin' && (
                            <button
                              onClick={() => handleEnviarDirector(compra)}
                              className="p-1.5 text-indigo-600 hover:bg-indigo-50 rounded-lg"
                              title="Enviar a Director"
                            >
                              <FaCheck className="text-xs" />
                            </button>
                          )}
                          
                          {/* FLUJO MULTINIVEL: Autorizar como Director */}
                          {esDirector && compra.estado === 'enviada_director' && (
                            <button
                              onClick={() => handleAutorizarDirector(compra)}
                              className="p-1.5 text-green-600 hover:bg-green-50 rounded-lg"
                              title="Autorizar (Final)"
                            >
                              <FaUserCheck className="text-xs" />
                            </button>
                          )}
                          
                          {/* Cancelar (solo estados anteriores a comprada) */}
                          {/* ISS-SEC FIX: Después de 'comprada' el flujo es irreversible → solo RECIBIDA */}
                          {puedeCancelar && !['comprada', 'recibida', 'cancelada', 'rechazada'].includes(compra.estado) && (
                            <button
                              onClick={() => setCancelModal({ show: true, compra, motivo: '' })}
                              className="p-1.5 text-red-600 hover:bg-red-50 rounded-lg"
                              title="Cancelar"
                            >
                              <FaBan className="text-xs" />
                            </button>
                          )}
                          
                          {/* Eliminar: pendientes para todos, otros estados solo admin farmacia */}
                          {((puedeEditar && compra.estado === 'pendiente') || 
                            ((esUsuarioFarmacia || user?.is_superuser) && 
                             !['cancelada', 'rechazada', 'rechazada_farmacia'].includes(compra.estado))) && (
                            <button
                              onClick={() => setDeleteModal({ show: true, compra })}
                              className="p-1.5 text-red-600 hover:bg-red-50 rounded-lg"
                              title={compra.estado === 'pendiente' ? 'Eliminar' : 'Eliminar (Admin Farmacia)'}
                            >
                              <FaTrash className="text-xs" />
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
        open={deleteModal.show}
        onCancel={() => setDeleteModal({ show: false, compra: null })}
        onConfirm={handleDelete}
        title="Eliminar Solicitud de Compra"
        message={`¿Está seguro de eliminar la solicitud ${deleteModal.compra?.folio}? Esta acción no se puede deshacer.`}
        confirmText="Eliminar"
        tone="danger"
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

      {/* Modal de Registrar Compra Realizada */}
      {registrarCompraModal.show && registrarCompraModal.compra && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white px-6 py-4 border-b flex justify-between items-center">
              <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                <FaShoppingCart className="text-purple-600" />
                Registrar Compra Realizada - {registrarCompraModal.compra.folio}
              </h2>
              <button
                onClick={() => setRegistrarCompraModal({ 
                  show: false, 
                  compra: null, 
                  fecha_compra: new Date().toISOString().split('T')[0],
                  numero_factura: '',
                  proveedor_nombre: '',
                  proveedor_contacto: '',
                  detalles: [] 
                })}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <FaTimes />
              </button>
            </div>
            
            <div className="p-6 space-y-6">
              {/* Info de trazabilidad */}
              <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg">
                <div className="flex items-center gap-2 text-purple-800">
                  <FaInfoCircle />
                  <span className="font-medium">Registro de compra externa</span>
                </div>
                <p className="text-purple-700 text-sm mt-1">
                  Registre los datos de la compra realizada. Esta información quedará guardada para trazabilidad y auditoría.
                </p>
                <p className="text-purple-600 text-xs mt-2">
                  <strong>Fecha de captura:</strong> {new Date().toLocaleString('es-MX')} | 
                  <strong> Usuario:</strong> {user?.nombre || user?.username || 'N/A'}
                </p>
              </div>

              {/* Datos de la compra */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Fecha de Compra *
                  </label>
                  <input
                    type="date"
                    value={registrarCompraModal.fecha_compra}
                    onChange={(e) => setRegistrarCompraModal(prev => ({ ...prev, fecha_compra: e.target.value }))}
                    required
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Número de Factura/Ticket
                  </label>
                  <input
                    type="text"
                    value={registrarCompraModal.numero_factura}
                    onChange={(e) => setRegistrarCompraModal(prev => ({ ...prev, numero_factura: e.target.value }))}
                    placeholder="Ej: FAC-12345"
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Proveedor
                  </label>
                  <input
                    type="text"
                    value={registrarCompraModal.proveedor_nombre}
                    onChange={(e) => setRegistrarCompraModal(prev => ({ ...prev, proveedor_nombre: e.target.value }))}
                    placeholder="Nombre del proveedor"
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Contacto/Teléfono
                  </label>
                  <input
                    type="text"
                    value={registrarCompraModal.proveedor_contacto}
                    onChange={(e) => setRegistrarCompraModal(prev => ({ ...prev, proveedor_contacto: e.target.value }))}
                    placeholder="Contacto del proveedor"
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500"
                  />
                </div>
              </div>
              
              {/* Productos comprados */}
              <div className="border rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-4 py-2 border-b">
                  <h3 className="font-medium text-gray-800">Productos Comprados</h3>
                  <p className="text-xs text-gray-500">Registre las cantidades reales compradas, precios y datos del lote</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Producto</th>
                        <th className="px-3 py-2 text-center text-xs font-medium text-gray-500">Solicitado</th>
                        <th className="px-3 py-2 text-center text-xs font-medium text-gray-500">Comprado *</th>
                        <th className="px-3 py-2 text-center text-xs font-medium text-gray-500">Precio Unit. *</th>
                        <th className="px-3 py-2 text-center text-xs font-medium text-gray-500">Lote</th>
                        <th className="px-3 py-2 text-center text-xs font-medium text-gray-500">Caducidad</th>
                        <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">Importe</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {registrarCompraModal.detalles.map((detalle, index) => (
                        <tr key={detalle.id}>
                          <td className="px-3 py-2 text-sm">{detalle.descripcion_producto}</td>
                          <td className="px-3 py-2 text-center text-sm text-gray-500">{detalle.cantidad_solicitada}</td>
                          <td className="px-3 py-2">
                            <input
                              type="number"
                              min="0"
                              value={detalle.cantidad_comprada}
                              onChange={(e) => {
                                const newDetalles = [...registrarCompraModal.detalles];
                                newDetalles[index].cantidad_comprada = e.target.value;
                                setRegistrarCompraModal(prev => ({ ...prev, detalles: newDetalles }));
                              }}
                              className="w-20 px-2 py-1 border rounded text-center text-sm"
                            />
                          </td>
                          <td className="px-3 py-2">
                            <input
                              type="number"
                              min="0"
                              step="0.01"
                              value={detalle.precio_unitario}
                              onChange={(e) => {
                                const newDetalles = [...registrarCompraModal.detalles];
                                newDetalles[index].precio_unitario = e.target.value;
                                setRegistrarCompraModal(prev => ({ ...prev, detalles: newDetalles }));
                              }}
                              className="w-24 px-2 py-1 border rounded text-center text-sm"
                            />
                          </td>
                          <td className="px-3 py-2">
                            <input
                              type="text"
                              value={detalle.numero_lote || ''}
                              onChange={(e) => {
                                const newDetalles = [...registrarCompraModal.detalles];
                                newDetalles[index].numero_lote = e.target.value;
                                setRegistrarCompraModal(prev => ({ ...prev, detalles: newDetalles }));
                              }}
                              placeholder="Lote"
                              className="w-24 px-2 py-1 border rounded text-sm"
                            />
                          </td>
                          <td className="px-3 py-2">
                            <input
                              type="date"
                              value={detalle.fecha_caducidad || ''}
                              onChange={(e) => {
                                const newDetalles = [...registrarCompraModal.detalles];
                                newDetalles[index].fecha_caducidad = e.target.value;
                                setRegistrarCompraModal(prev => ({ ...prev, detalles: newDetalles }));
                              }}
                              className="w-32 px-2 py-1 border rounded text-sm"
                            />
                          </td>
                          <td className="px-3 py-2 text-right text-sm font-medium">
                            {formatCurrency((parseFloat(detalle.cantidad_comprada) || 0) * (parseFloat(detalle.precio_unitario) || 0))}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="bg-gray-50">
                      <tr>
                        <td colSpan="6" className="px-3 py-2 text-right font-medium">Total:</td>
                        <td className="px-3 py-2 text-right font-bold text-purple-600">
                          {formatCurrency(registrarCompraModal.detalles.reduce((sum, d) => 
                            sum + ((parseFloat(d.cantidad_comprada) || 0) * (parseFloat(d.precio_unitario) || 0)), 0
                          ))}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            </div>
            
            <div className="sticky bottom-0 bg-white px-6 py-4 border-t flex justify-end gap-3">
              <button
                onClick={() => setRegistrarCompraModal({ 
                  show: false, 
                  compra: null, 
                  fecha_compra: new Date().toISOString().split('T')[0],
                  numero_factura: '',
                  proveedor_nombre: '',
                  proveedor_contacto: '',
                  detalles: [] 
                })}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                Cancelar
              </button>
              <button
                onClick={handleRegistrarCompra}
                disabled={!registrarCompraModal.fecha_compra}
                className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
              >
                <FaCheck />
                Registrar Compra
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Recibir Productos */}
      {recibirModal.show && recibirModal.compra && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white px-6 py-4 border-b flex justify-between items-center">
              <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                <FaTruck className="text-green-600" />
                Registrar Recepción - {recibirModal.compra.folio}
              </h2>
              <button
                onClick={() => setRecibirModal({ show: false, compra: null, detalles: [] })}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <FaTimes />
              </button>
            </div>
            
            <div className="p-6 space-y-6">
              {/* Info de trazabilidad */}
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center gap-2 text-green-800">
                  <FaBoxOpen />
                  <span className="font-medium">Recepción de productos</span>
                </div>
                <p className="text-green-700 text-sm mt-1">
                  Confirme las cantidades recibidas. Los productos se agregarán al inventario de caja chica del centro.
                </p>
                <p className="text-green-600 text-xs mt-2">
                  <strong>Fecha de captura:</strong> {new Date().toLocaleString('es-MX')} | 
                  <strong> Usuario:</strong> {user?.nombre || user?.username || 'N/A'}
                </p>
              </div>

              {/* Info de la compra */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Fecha de compra:</span>
                  <span className="ml-2 font-medium">{formatDate(recibirModal.compra.fecha_compra)}</span>
                </div>
                <div>
                  <span className="text-gray-500">Factura:</span>
                  <span className="ml-2 font-medium">{recibirModal.compra.numero_factura || '-'}</span>
                </div>
                <div>
                  <span className="text-gray-500">Proveedor:</span>
                  <span className="ml-2 font-medium">{recibirModal.compra.proveedor_nombre || '-'}</span>
                </div>
                <div>
                  <span className="text-gray-500">Total:</span>
                  <span className="ml-2 font-medium">{formatCurrency(recibirModal.compra.total)}</span>
                </div>
              </div>
              
              {/* Productos a recibir */}
              <div className="border rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-4 py-2 border-b">
                  <h3 className="font-medium text-gray-800">Productos a Recibir</h3>
                </div>
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Producto</th>
                      <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">Lote</th>
                      <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">Comprado</th>
                      <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">Recibido *</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {recibirModal.detalles.map((detalle, index) => (
                      <tr key={detalle.id}>
                        <td className="px-4 py-2 text-sm">{detalle.descripcion_producto}</td>
                        <td className="px-4 py-2 text-center text-sm text-gray-500">{detalle.numero_lote || '-'}</td>
                        <td className="px-4 py-2 text-center text-sm">{detalle.cantidad_comprada}</td>
                        <td className="px-4 py-2 text-center">
                          <input
                            type="number"
                            min="0"
                            value={detalle.cantidad_recibida}
                            onChange={(e) => {
                              const newDetalles = [...recibirModal.detalles];
                              newDetalles[index].cantidad_recibida = e.target.value;
                              setRecibirModal(prev => ({ ...prev, detalles: newDetalles }));
                            }}
                            className="w-20 px-2 py-1 border rounded text-center"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            
            <div className="sticky bottom-0 bg-white px-6 py-4 border-t flex justify-end gap-3">
              <button
                onClick={() => setRecibirModal({ show: false, compra: null, detalles: [] })}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                Cancelar
              </button>
              <button
                onClick={handleRecibir}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2"
              >
                <FaCheckCircle />
                Confirmar Recepción
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de rechazo por stock disponible (Farmacia) */}
      {stockRechazoModal.show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="px-6 py-4 border-b">
              <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <FaWarehouse className="text-orange-600" />
                Producto Disponible en Farmacia
              </h2>
            </div>
            <div className="p-6 space-y-4">
              <div className="p-3 bg-orange-50 border border-orange-200 rounded-lg">
                <p className="text-orange-800">
                  Al confirmar, se notificará al centro que el producto está disponible en farmacia 
                  y deberá realizar una requisición regular en lugar de compra de caja chica.
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-2">
                  <strong>Solicitud:</strong> {stockRechazoModal.compra?.folio}
                </p>
                <p className="text-sm text-gray-600 mb-4">
                  <strong>Producto solicitado:</strong> {stockRechazoModal.compra?.detalles?.[0]?.producto_nombre || 'Ver detalles'}
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Información del producto disponible *
                </label>
                <textarea
                  value={stockRechazoModal.observaciones}
                  onChange={(e) => setStockRechazoModal(prev => ({ ...prev, observaciones: e.target.value }))}
                  rows={3}
                  required
                  placeholder="Indique el producto disponible, cantidad, lote, ubicación, etc."
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500"
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t flex justify-end gap-3">
              <button
                onClick={() => setStockRechazoModal({ show: false, compra: null, observaciones: '' })}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                Cancelar
              </button>
              <button
                onClick={async () => {
                  await handleRechazarTieneStock(stockRechazoModal.compra, stockRechazoModal.observaciones);
                  setStockRechazoModal({ show: false, compra: null, observaciones: '' });
                }}
                disabled={!stockRechazoModal.observaciones}
                className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50"
              >
                Confirmar Stock Disponible
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ComprasCajaChica;
