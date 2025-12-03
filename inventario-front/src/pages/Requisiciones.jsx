import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  requisicionesAPI,
  productosAPI,
  centrosAPI,
  lotesAPI,
  descargarArchivo,
} from '../services/api';
import { usePermissions } from '../hooks/usePermissions';
import { ProtectedButton } from '../components/ProtectedAction';
import ConfirmModal from '../components/ConfirmModal';
import InputModal from '../components/InputModal';
import PageHeader from '../components/PageHeader';
import Pagination from '../components/Pagination';
import { toast } from 'react-hot-toast';
import {
  FaPlus,
  FaEye,
  FaPaperPlane,
  FaTimes,
  FaBoxOpen,
  FaBan,
  FaDownload,
  FaEdit,
  FaTrash,
  FaClipboardList,
  FaSearch,
  FaShoppingCart,
  FaMinus,
  FaExclamationTriangle,
} from 'react-icons/fa';
import { COLORS } from '../constants/theme';

const PAGE_SIZE = 10;

const Requisiciones = () => {
  const navigate = useNavigate();
  const { permisos, user, getRolPrincipal } = usePermissions();
  
  // Calcular rol y si puede ver todos los centros
  const rolPrincipal = getRolPrincipal();
  const esAdminOFarmacia = rolPrincipal === 'ADMIN' || rolPrincipal === 'FARMACIA';
  
  // Flag para saber si ya se determinó el centro del usuario (evita carga prematura)
  // Para admin/farmacia siempre está listo; para usuarios de centro, esperar hidratación
  const [centroResuelto, setCentroResuelto] = useState(() => esAdminOFarmacia);
  // Flag para indicar error de configuración (usuario sin centro asignado)
  const [errorCentroNoAsignado, setErrorCentroNoAsignado] = useState(false);
  
  const [requisiciones, setRequisiciones] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(null); // Loading específico por acción (evita bloquear todo)
  const [isSubmitting, setIsSubmitting] = useState(false);
  // Para usuarios de centro, pre-llenar con su centro; para admin/farmacia iniciar vacío
  // IMPORTANTE: usar 'PENDING' como valor especial para usuarios de centro sin hidratar
  const [filtroCentro, setFiltroCentro] = useState(() => 
    esAdminOFarmacia ? '' : (user?.centro?.id?.toString() || 'PENDING')
  );
  const [filtroEstado, setFiltroEstado] = useState('');
  const [grupoEstado, setGrupoEstado] = useState('todas');
  const [searchTerm, setSearchTerm] = useState('');
  const [filtroFechaDesde, setFiltroFechaDesde] = useState(''); // Nuevo filtro fecha desde
  const [filtroFechaHasta, setFiltroFechaHasta] = useState(''); // Nuevo filtro fecha hasta
  const [fechaError, setFechaError] = useState(''); // Error de validación de fechas
  const [currentPage, setCurrentPage] = useState(1);
  const [totalRequisiciones, setTotalRequisiciones] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [resumenEstados, setResumenEstados] = useState({ por_estado: {}, por_grupo: {} });

  // Modal create/edit
  const [showModal, setShowModal] = useState(false);
  const [editRequisicion, setEditRequisicion] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  
  // Modales de confirmación para acciones críticas
  const [confirmEnviar, setConfirmEnviar] = useState(null); // {id, folio}
  const [confirmSurtir, setConfirmSurtir] = useState(null); // {id, folio}
  const [inputRechazo, setInputRechazo] = useState(null); // {id, folio}
  const [inputCancelar, setInputCancelar] = useState(null); // {id, folio}
  
  const [productos, setProductos] = useState([]);
  const [centros, setCentros] = useState([]);
  
  // Estado para catálogo precargado
  const [catalogoLotes, setCatalogoLotes] = useState([]); // Todos los lotes con stock
  const [loadingCatalogo, setLoadingCatalogo] = useState(false);
  const [catalogoBusqueda, setCatalogoBusqueda] = useState('');
  const [vistaCarrito, setVistaCarrito] = useState(false); // Toggle entre catálogo y carrito
  
  // Mantener compatibilidad con código existente (eliminar después)
  const [productoBusqueda, setProductoBusqueda] = useState('');
  const [productoSeleccionado, setProductoSeleccionado] = useState(null);
  const [lotesProducto, setLotesProducto] = useState([]);
  // eslint-disable-next-line no-unused-vars
  const [loadingLotes, setLoadingLotes] = useState(false);
  
  const [form, setForm] = useState({
    centro: '',
    items: [],
    comentario: '',
  });

  const filtrosActivos = [searchTerm, filtroEstado, filtroCentro, filtroFechaDesde, filtroFechaHasta].filter(Boolean).length;

  const stateTabs = [
    { key: 'todas', label: 'Todas' },
    { key: 'pendientes', label: 'Pendientes' },
    { key: 'aceptadas_parciales', label: 'Autorizadas' },
    { key: 'surtidas', label: 'Surtidas' },
    { key: 'rechazadas_canceladas', label: 'Rechazadas' },
  ];

  // Caché para evitar recargas innecesarias del catálogo
  const [catalogoCargado, setCatalogoCargado] = useState(false);

  const resetForm = useCallback(() => {
    setForm({
      centro: user?.centro?.id || '',
      items: [],
      comentario: '',
    });
    setProductoBusqueda('');
    setProductoSeleccionado(null);
    setLotesProducto([]);
    setCatalogoBusqueda('');
    setVistaCarrito(false);
    // Limpiar caché para forzar recarga al reabrir
    setCatalogoCargado(false);
  }, [user?.centro?.id]);
  
  // Cargar catálogo de lotes con stock - con caché y paginación optimizada
  const cargarCatalogoLotes = useCallback(async (forzarRecarga = false) => {
    // Si ya está cargado y no se fuerza, no recargar
    if (catalogoCargado && !forzarRecarga && catalogoLotes.length > 0) {
      return;
    }
    
    setLoadingCatalogo(true);
    try {
      // Cargar lotes disponibles con stock > 0, no vencidos
      // Paginación limitada para evitar cargas masivas
      const params = {
        stock_min: 1,
        solo_disponibles: 'true',  // Solo lotes disponibles y no vencidos
        ordering: 'producto__descripcion,fecha_caducidad',
        page_size: 200, // Límite razonable por página
      };
      
      // CRÍTICO: Filtrar lotes según el rol del usuario
      if (permisos.isFarmaciaAdmin || permisos.isAdmin) {
        // Admin/Farmacia ven lotes de farmacia central
        params.centro = 'central';
      } else if (user?.centro?.id) {
        // Usuarios de centro SOLO ven lotes de su centro (aislamiento de datos)
        params.centro = user.centro.id;
      } else {
        // Sin centro definido, no cargar lotes (seguridad)
        console.warn('Usuario sin centro definido, no se cargan lotes');
        setCatalogoLotes([]);
        setLoadingCatalogo(false);
        return;
      }
      
      const resp = await lotesAPI.getAll(params);
      const lotes = resp.data.results || resp.data || [];
      setCatalogoLotes(lotes);
      setCatalogoCargado(true);
    } catch (error) {
      console.error('Error cargando catálogo de lotes:', error);
      setCatalogoLotes([]);
    } finally {
      setLoadingCatalogo(false);
    }
  }, [permisos.isFarmaciaAdmin, permisos.isAdmin, user?.centro?.id, catalogoCargado, catalogoLotes.length]);

  const cargarCatalogos = useCallback(async () => {
    try {
      const [prodResp, centrosResp] = await Promise.all([
        productosAPI.getAll({ page_size: 500, ordering: 'descripcion' }),
        centrosAPI.getAll({ page_size: 100, ordering: 'nombre' }),
      ]);
      setProductos(prodResp.data.results || prodResp.data);
      setCentros(centrosResp.data.results || centrosResp.data);
    } catch (error) {
      console.error('Error cargando catálogos', error);
    }
  }, []);

  const cargarRequisiciones = useCallback(async () => {
    // BLOQUEAR carga si el centro del usuario no está resuelto
    // Esto previene que usuarios de centro vean datos de otros centros
    if (!centroResuelto || filtroCentro === 'PENDING') {
      return;
    }
    // Validar rango de fechas antes de buscar
    if (filtroFechaDesde && filtroFechaHasta && filtroFechaDesde > filtroFechaHasta) {
      // No cargar si hay error de rango de fechas
      return;
    }
    setLoading(true);
    try {
      const params = {
        page: currentPage,
        page_size: PAGE_SIZE,
        ordering: '-fecha_solicitud',
      };
      if (filtroEstado) params.estado = filtroEstado;
      if (grupoEstado && grupoEstado !== 'todas') params.grupo_estado = grupoEstado;
      if (searchTerm) params.search = searchTerm;
      // Solo aplicar filtro de centro si no es PENDING (ya validado arriba pero por claridad)
      if (filtroCentro && filtroCentro !== 'PENDING') params.centro = filtroCentro;
      if (filtroFechaDesde) params.fecha_desde = filtroFechaDesde;
      if (filtroFechaHasta) params.fecha_hasta = filtroFechaHasta;

      const response = await requisicionesAPI.getAll(params);
      const results = response.data.results || response.data;
      const orderedResults = [...results].sort(
        (a, b) => new Date(b.fecha_solicitud) - new Date(a.fecha_solicitud),
      );
      setRequisiciones(orderedResults);
      const total = response.data.count || results.length;
      setTotalRequisiciones(total);
      setTotalPages(Math.max(1, Math.ceil(total / PAGE_SIZE)));
    } catch (error) {
      toast.error('Error al cargar requisiciones');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [currentPage, filtroEstado, grupoEstado, searchTerm, filtroCentro, filtroFechaDesde, filtroFechaHasta, centroResuelto]);

  const cargarResumenEstados = useCallback(async () => {
    try {
      // Enviar filtro de centro para que el resumen sea consistente
      const params = {};
      if (filtroCentro) {
        params.centro = filtroCentro;
      }
      const resumen = await requisicionesAPI.resumenEstados(params);
      setResumenEstados(resumen.data || { por_estado: {}, por_grupo: {} });
    } catch (error) {
      console.warn('No fue posible cargar resumen de estados', error);
    }
  }, [filtroCentro]);

  useEffect(() => {
    setCurrentPage(1);
  }, [filtroEstado, searchTerm, grupoEstado, filtroCentro, filtroFechaDesde, filtroFechaHasta]);

  // Sincronizar filtroCentro cuando el usuario se hidrata (carga tardía)
  // Esto evita que usuarios de centro vean requisiciones de otros centros antes de cargar su perfil
  // CRÍTICO: Marcar centroResuelto una vez que tengamos el centro del usuario
  useEffect(() => {
    if (esAdminOFarmacia) {
      // Admin/Farmacia siempre pueden cargar (sin filtro obligatorio)
      setCentroResuelto(true);
      setErrorCentroNoAsignado(false);
    } else if (user?.centro?.id) {
      // Usuario de centro: aplicar filtro con su centro
      const centroId = user.centro.id.toString();
      setFiltroCentro(centroId);
      setCentroResuelto(true);
      setErrorCentroNoAsignado(false);
    } else if (user && !user.centro?.id) {
      // Usuario autenticado pero SIN centro asignado - error de configuración
      // Marcar como resuelto para evitar spinner infinito, pero con error
      setCentroResuelto(true);
      setErrorCentroNoAsignado(true);
      setFiltroCentro(''); // Limpiar PENDING
      console.error('Usuario sin centro asignado:', user.username || user.email);
    }
    // Si user aún no está cargado, mantener PENDING y centroResuelto=false
  }, [user, esAdminOFarmacia]);

  useEffect(() => {
    cargarRequisiciones();
    cargarResumenEstados();
  }, [cargarRequisiciones, cargarResumenEstados]);

  useEffect(() => {
    cargarCatalogos();
    resetForm();
  }, [cargarCatalogos, resetForm]);

  const puedeEditar = (requisicion) => {
    // Primero validar permiso fino
    if (!permisos.editarRequisicion) return false;
    if (requisicion.estado !== 'borrador') return false;
    if (permisos.isFarmaciaAdmin) return true;
    if (permisos.isCentroUser) {
      const userCentro = user?.centro?.id;
      return requisicion.centro === userCentro;
    }
    return false;
  };

  // Validar permiso fino de enviar además de las condiciones de edición
  const puedeEnviar = (req) => permisos.enviarRequisicion && puedeEditar(req) && req.estado === 'borrador';

  // Validar si puede cancelar - similar a puedeEditar pero sin restricción de estado borrador
  const puedeCancelar = (requisicion) => {
    // Estados finales no se pueden cancelar
    if (['surtida', 'cancelada', 'rechazada'].includes(requisicion.estado)) return false;
    // Validar permiso fino
    if (!permisos.cancelarRequisicion) return false;
    // Admin/Farmacia pueden cancelar cualquiera
    if (permisos.isFarmaciaAdmin) return true;
    // Usuario de centro solo puede cancelar las de su centro
    if (permisos.isCentroUser) {
      const userCentro = user?.centro?.id;
      return requisicion.centro === userCentro;
    }
    return false;
  };

  // Validar si puede descargar PDF - debe tener permiso Y pertenecer al centro (si es usuario de centro)
  const puedeDescargarPDF = (requisicion) => {
    // Primero validar permiso fino
    if (!permisos.descargarHojaRecoleccion) return false;
    // Admin/Farmacia pueden descargar cualquier PDF
    if (permisos.isFarmaciaAdmin) return true;
    // Vista puede descargar cualquier PDF (solo consulta)
    if (permisos.isVistaUser) return true;
    // Usuario de centro solo puede descargar PDFs de su centro
    if (permisos.isCentroUser) {
      const userCentro = user?.centro?.id;
      return requisicion.centro === userCentro;
    }
    return false;
  };

  const getEstadoBadge = (estado) => {
    const badges = {
      borrador: 'bg-gray-100 text-gray-700 border border-gray-300',
      enviada: 'bg-amber-50 text-amber-700 border border-amber-300',
      autorizada: 'bg-green-50 text-green-700 border border-green-300',
      parcial: 'bg-green-50 text-green-700 border border-green-300', // Tratamos parcial como autorizada
      rechazada: 'bg-red-50 text-red-700 border border-red-300',
      surtida: 'bg-purple-50 text-purple-700 border border-purple-300',
      recibida: 'bg-blue-50 text-blue-700 border border-blue-300',
      cancelada: 'bg-gray-50 text-gray-500 border border-gray-200',
    };
    return badges[estado] || 'bg-gray-100 text-gray-700 border border-gray-300';
  };

  // Labels amigables para los estados
  const getEstadoLabel = (estado) => {
    const labels = {
      borrador: 'BORRADOR',
      enviada: 'PENDIENTE',
      autorizada: 'AUTORIZADA',
      parcial: 'AUTORIZADA',  // Simplificamos parcial como autorizada
      rechazada: 'RECHAZADA',
      surtida: 'SURTIDA',
      recibida: 'RECIBIDA',
      cancelada: 'CANCELADA',
    };
    return labels[estado] || estado?.toUpperCase();
  };

  const abrirModalCrear = () => {
    // Validar permisos antes de abrir
    if (!permisos?.crearRequisicion) {
      toast.error('No tienes permisos para crear requisiciones');
      return;
    }
    resetForm();
    setEditRequisicion(null);
    cargarCatalogoLotes(); // Cargar catálogo al abrir
    setShowModal(true);
  };

  const abrirModalEditar = (req) => {
    // Validar permisos antes de abrir
    if (!permisos?.editarRequisicion) {
      toast.error('No tienes permisos para editar requisiciones');
      return;
    }
    // Solo permitir editar borradores propios o cualquier borrador si es admin/farmacia
    if (req.estado !== 'borrador' && req.estado !== 'BORRADOR') {
      toast.error('Solo se pueden editar requisiciones en estado borrador');
      return;
    }
    const items = (req.detalles || req.items || []).map((d) => ({
      producto: d.producto || d.producto_id,
      producto_clave: d.producto_clave || d.producto?.clave,
      descripcion: d.producto_descripcion || d.descripcion || d.producto_nombre,
      cantidad_solicitada: d.cantidad_solicitada || d.cantidad || 1,
      lote: d.lote || d.lote_id || null,
      lote_numero: d.lote_numero || d.lote?.numero_lote || null,
      lote_caducidad: d.lote_caducidad || d.lote?.fecha_caducidad || null,
      stock_disponible: d.lote_stock ?? d.stock_disponible ?? null,
    }));
    setForm({
      centro: req.centro || req.centro_id || user?.centro?.id || '',
      items,
      comentario: req.comentario || req.observaciones || '',
    });
    setEditRequisicion(req);
    cargarCatalogoLotes(); // Cargar catálogo al editar
    setShowModal(true);

    // Cargar stock actualizado para los items existentes
    const fetchStockPromises = items.map(item => {
      if (item.lote) {
        return lotesAPI.get(item.lote).then(resp => ({
          loteId: item.lote,
          stock_actual: resp.data.stock_actual ?? resp.data.cantidad_actual ?? 0,
        })).catch(() => null);
      }
      return Promise.resolve(null);
    });

    Promise.all(fetchStockPromises).then(stocks => {
      const stockMap = stocks.reduce((acc, s) => {
        if (s) acc[s.loteId] = s.stock_actual;
        return acc;
      }, {});

      setForm(prevForm => ({
        ...prevForm,
        items: prevForm.items.map(item => ({
          ...item,
          stock_disponible: stockMap[item.lote] ?? item.stock_disponible,
        })),
      }));
    });
  };

  // Cuando se selecciona un producto, cargar sus lotes disponibles
  // eslint-disable-next-line no-unused-vars
  const seleccionarProducto = async (productoId) => {
    const prod = productos.find((p) => p.id === Number(productoId));
    if (!prod) return;
    
    setProductoSeleccionado(prod);
    setLoadingLotes(true);
    
    try {
      const resp = await lotesAPI.getAll({ producto: productoId, stock_min: 1, ordering: 'fecha_caducidad' });
      const lotes = resp.data.results || resp.data || [];
      setLotesProducto(lotes);
    } catch (error) {
      console.error('Error cargando lotes:', error);
      setLotesProducto([]);
    } finally {
      setLoadingLotes(false);
    }
  };

  // Agregar item con lote seleccionado (viejo método - mantener compatibilidad)
  // eslint-disable-next-line no-unused-vars
  const agregarItemConLote = (loteId) => {
    if (!productoSeleccionado) return;
    const lote = lotesProducto.find((l) => l.id === Number(loteId));
    if (!lote) return;
    
    // Verificar si ya existe este lote en la requisición
    const existe = form.items.find((i) => i.lote === lote.id);
    if (existe) {
      toast.error('Este lote ya está en la requisición');
      return;
    }
    
    setForm((prev) => ({
      ...prev,
      items: [
        ...prev.items,
        {
          producto: productoSeleccionado.id,
          producto_clave: productoSeleccionado.clave,
          descripcion: productoSeleccionado.descripcion,
          lote: lote.id,
          lote_numero: lote.numero_lote,
          lote_caducidad: lote.fecha_caducidad,
          stock_disponible: lote.stock_actual ?? lote.cantidad_actual,
          cantidad_solicitada: 1,
        },
      ],
    }));
    
    // Limpiar selección
    setProductoSeleccionado(null);
    setLotesProducto([]);
    setProductoBusqueda('');
  };

  // ==========================================
  // NUEVO: Funciones para catálogo precargado
  // ==========================================
  
  // Agregar lote desde el catálogo precargado
  const agregarDesdeCatalogo = (lote) => {
    // Verificar si ya existe este lote en la requisición
    const existe = form.items.find((i) => i.lote === lote.id);
    if (existe) {
      toast.error('Este lote ya está en la requisición');
      return;
    }
    
    const stockDisponible = lote.stock_actual ?? lote.cantidad_actual ?? 0;
    
    setForm((prev) => ({
      ...prev,
      items: [
        ...prev.items,
        {
          producto: lote.producto || lote.producto_id,
          producto_clave: lote.producto_clave,
          descripcion: lote.producto_descripcion || lote.producto_nombre,
          lote: lote.id,
          lote_numero: lote.numero_lote,
          lote_caducidad: lote.fecha_caducidad,
          stock_disponible: stockDisponible,
          cantidad_solicitada: 1,
        },
      ],
    }));
    
    toast.success(`${lote.producto_clave} agregado`);
  };
  
  // Verificar si un lote ya está en el carrito
  const loteEnCarrito = (loteId) => {
    return form.items.some((i) => i.lote === loteId);
  };
  
  // Obtener cantidad en carrito para un lote
  const getCantidadEnCarrito = (loteId) => {
    const item = form.items.find((i) => i.lote === loteId);
    return item?.cantidad_solicitada || 0;
  };
  
  // Incrementar cantidad desde catálogo
  const incrementarCantidad = (loteId) => {
    const itemIndex = form.items.findIndex((i) => i.lote === loteId);
    if (itemIndex === -1) return;
    
    const item = form.items[itemIndex];
    const maxCantidad = item.stock_disponible || 9999;
    
    if (item.cantidad_solicitada >= maxCantidad) {
      toast.error('Inventario máximo alcanzado');
      return;
    }
    
    setForm((prev) => {
      const items = [...prev.items];
      items[itemIndex] = { ...items[itemIndex], cantidad_solicitada: items[itemIndex].cantidad_solicitada + 1 };
      return { ...prev, items };
    });
  };
  
  // Decrementar cantidad desde catálogo
  const decrementarCantidad = (loteId) => {
    const itemIndex = form.items.findIndex((i) => i.lote === loteId);
    if (itemIndex === -1) return;
    
    const item = form.items[itemIndex];
    
    if (item.cantidad_solicitada <= 1) {
      // Quitar del carrito si llega a 0
      setForm((prev) => ({
        ...prev,
        items: prev.items.filter((i) => i.lote !== loteId),
      }));
      return;
    }
    
    setForm((prev) => {
      const items = [...prev.items];
      items[itemIndex] = { ...items[itemIndex], cantidad_solicitada: items[itemIndex].cantidad_solicitada - 1 };
      return { ...prev, items };
    });
  };
  
  // Filtrar catálogo por búsqueda
  const catalogoFiltrado = useMemo(() => {
    if (!catalogoBusqueda.trim()) return catalogoLotes;
    
    const busqueda = catalogoBusqueda.toLowerCase();
    return catalogoLotes.filter((lote) => 
      lote.producto_clave?.toLowerCase().includes(busqueda) ||
      lote.producto_descripcion?.toLowerCase().includes(busqueda) ||
      lote.producto_nombre?.toLowerCase().includes(busqueda) ||
      lote.numero_lote?.toLowerCase().includes(busqueda)
    );
  }, [catalogoLotes, catalogoBusqueda]);
  
  // Agrupar lotes por producto para mejor visualización
  const catalogoAgrupado = useMemo(() => {
    const grupos = {};
    catalogoFiltrado.forEach((lote) => {
      const key = lote.producto || lote.producto_id;
      if (!grupos[key]) {
        grupos[key] = {
          producto_id: key,
          producto_clave: lote.producto_clave,
          producto_descripcion: lote.producto_descripcion || lote.producto_nombre,
          lotes: [],
        };
      }
      grupos[key].lotes.push(lote);
    });
    return Object.values(grupos);
  }, [catalogoFiltrado]);
  
  // Total de items en carrito
  const totalItemsCarrito = form.items.reduce((sum, item) => sum + item.cantidad_solicitada, 0);

  // eslint-disable-next-line no-unused-vars
  const cancelarSeleccionProducto = () => {
    setProductoSeleccionado(null);
    setLotesProducto([]);
  };

  const actualizarCantidad = (idx, value) => {
    const item = form.items[idx];
    const maxCantidad = item.stock_disponible || 9999;
    const cantidad = Math.min(Math.max(1, Number(value) || 1), maxCantidad);
    setForm((prev) => {
      const items = [...prev.items];
      items[idx] = { ...items[idx], cantidad_solicitada: cantidad };
      return { ...prev, items };
    });
  };

  const eliminarItem = (idx) => {
    setForm((prev) => {
      const items = prev.items.filter((_, i) => i !== idx);
      return { ...prev, items };
    });
  };

  const guardarRequisicion = async (enviar = false) => {
    if (isSubmitting) return; // Prevenir doble envío
    
    // Validar permisos antes de continuar
    const esEdicion = !!editRequisicion;
    if (esEdicion && !permisos?.editarRequisicion) {
      toast.error('No tienes permisos para editar requisiciones');
      return;
    }
    if (!esEdicion && !permisos?.crearRequisicion) {
      toast.error('No tienes permisos para crear requisiciones');
      return;
    }
    if (enviar && !permisos?.enviarRequisicion) {
      toast.error('No tienes permisos para enviar requisiciones');
      return;
    }
    
    if (!form.items.length) {
      toast.error('Agrega al menos un producto');
      return;
    }
    if (form.items.some((i) => !i.lote)) {
      toast.error('Selecciona el lote para cada producto solicitado');
      return;
    }
    setIsSubmitting(true);
    try {
      const payload = {
        centro: form.centro || user?.centro?.id || null,
        detalles: form.items.map((i) => ({
          producto: i.producto,
          lote: i.lote || null,
          cantidad_solicitada: i.cantidad_solicitada,
        })),
        comentario: form.comentario,
      };
      let resp;
      if (editRequisicion) {
        resp = await requisicionesAPI.update(editRequisicion.id, payload);
      } else {
        resp = await requisicionesAPI.create(payload);
      }
      const reqId = resp?.data?.id || editRequisicion?.id;
      if (enviar && reqId) {
        await requisicionesAPI.enviar(reqId);
      }
      toast.success(editRequisicion ? 'Requisición actualizada' : 'Requisición creada');
      setShowModal(false);
      setEditRequisicion(null);
      resetForm();
      cargarRequisiciones();
      cargarResumenEstados();
    } catch (error) {
      console.error(error);
      toast.error('No se pudo guardar la requisición');
    } finally {
      setIsSubmitting(false);
    }
  };

  const confirmarEliminar = (req) => setConfirmDelete(req);

  const eliminarRequisicion = async () => {
    if (!confirmDelete || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await requisicionesAPI.delete(confirmDelete.id);
      toast.success('Requisición eliminada');
      setConfirmDelete(null);
      cargarRequisiciones();
      cargarResumenEstados();
    } catch (error) {
      console.error(error);
      toast.error('No se pudo eliminar la requisición');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handler para abrir modal de confirmación de envío
  const handleEnviar = (id, folio) => {
    if (isSubmitting) return;
    setConfirmEnviar({ id, folio });
  };
  
  // Ejecutar envío después de confirmar
  const ejecutarEnviar = async () => {
    if (!confirmEnviar || isSubmitting) return;
    const { id } = confirmEnviar;
    
    setIsSubmitting(true);
    setActionLoading(id);
    setConfirmEnviar(null);
    try {
      await requisicionesAPI.enviar(id);
      toast.success('Requisición enviada correctamente');
      cargarRequisiciones();
      cargarResumenEstados();
    } catch (error) {
      const errorMsg = error.response?.data?.error || error.response?.data?.mensaje || 'Error al enviar requisición';
      toast.error(errorMsg);
    } finally {
      setIsSubmitting(false);
      setActionLoading(null);
    }
  };

  // Handler para abrir modal de rechazo con input
  const handleRechazar = (id, folio) => {
    if (isSubmitting) return;
    setInputRechazo({ id, folio });
  };
  
  // Ejecutar rechazo con motivo
  const ejecutarRechazo = async (motivo) => {
    if (!inputRechazo || isSubmitting) return;
    const { id } = inputRechazo;
    
    setIsSubmitting(true);
    setActionLoading(id);
    setInputRechazo(null);
    try {
      await requisicionesAPI.rechazar(id, { observaciones: motivo });
      toast.success('Requisición rechazada');
      cargarRequisiciones();
      cargarResumenEstados();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al rechazar');
    } finally {
      setIsSubmitting(false);
      setActionLoading(null);
    }
  };

  // Handler para abrir modal de confirmación de surtido
  const handleSurtir = (id, folio) => {
    if (isSubmitting) return;
    setConfirmSurtir({ id, folio });
  };
  
  // Ejecutar surtido después de confirmar
  const ejecutarSurtir = async () => {
    if (!confirmSurtir || isSubmitting) return;
    const { id } = confirmSurtir;
    
    setIsSubmitting(true);
    setActionLoading(id);
    setConfirmSurtir(null);
    try {
      await requisicionesAPI.surtir(id);
      toast.success('Requisición surtida correctamente');
      cargarRequisiciones();
      cargarResumenEstados();
    } catch (error) {
      const errorData = error.response?.data;
      let errorMsg = 'Error al surtir requisición';
      if (errorData?.faltantes) {
        errorMsg = `Stock insuficiente en ${errorData.faltantes.length} producto(s)`;
      } else if (errorData?.error) {
        errorMsg = errorData.error;
      }
      toast.error(errorMsg);
    } finally {
      setIsSubmitting(false);
      setActionLoading(null);
    }
  };

  // Handler para abrir modal de cancelación con input
  const handleCancelar = (id, folio) => {
    if (isSubmitting) return;
    setInputCancelar({ id, folio });
  };
  
  // Ejecutar cancelación con motivo
  const ejecutarCancelar = async (motivo) => {
    if (!inputCancelar || isSubmitting) return;
    const { id } = inputCancelar;
    
    setIsSubmitting(true);
    setActionLoading(id);
    setInputCancelar(null);
    try {
      await requisicionesAPI.cancelar(id, { observaciones: motivo });
      toast.success('Requisición cancelada');
      cargarRequisiciones();
      cargarResumenEstados();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al cancelar');
    } finally {
      setIsSubmitting(false);
      setActionLoading(null);
    }
  };

  const handleDescargarPDF = async (id, tipo, folio) => {
    if (actionLoading === `pdf-${id}`) return; // Evitar doble clic
    
    setActionLoading(`pdf-${id}`);
    try {
      let response;
      let nombreArchivo;

      if (tipo === 'aceptacion') {
        response = await requisicionesAPI.downloadPDFAceptacion(id);
        nombreArchivo = `Hoja_Recoleccion_${folio || id}.pdf`;
      } else {
        response = await requisicionesAPI.downloadPDFRechazo(id);
        nombreArchivo = `requisicion_rechazada_${folio || id}.pdf`;
      }

      descargarArchivo(response.data, nombreArchivo);
      toast.success('PDF descargado correctamente');
    } catch (error) {
      console.error('Error al descargar PDF:', error);
      const message = error.response?.data?.error || error.message || 'Error al descargar PDF';
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  };

  const headerActions = (
    <ProtectedButton
      permission="crearRequisicion"
      onClick={abrirModalCrear}
      type="button"
      disabled={errorCentroNoAsignado || !centroResuelto}
      className="flex items-center gap-2 rounded-full bg-white/90 px-4 py-2 text-sm font-bold hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed"
      style={{ color: COLORS.vino }}
      title={errorCentroNoAsignado ? 'No tienes un centro asignado' : undefined}
    >
      <FaPlus /> Nueva Requisición
    </ProtectedButton>
  );

  // eslint-disable-next-line no-unused-vars
  const productosFiltrados = productos.filter((p) =>
    p.descripcion?.toLowerCase().includes(productoBusqueda.toLowerCase()) ||
    p.clave?.toLowerCase().includes(productoBusqueda.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        icon={FaClipboardList}
        title="Requisiciones"
        subtitle={`Total: ${totalRequisiciones} | Página ${currentPage} de ${totalPages} | Rol: ${getRolPrincipal()}`}
        badge={filtrosActivos ? `${filtrosActivos} filtros activos` : null}
        actions={headerActions}
      />

      <div className="flex flex-wrap gap-3">
        {stateTabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setGrupoEstado(tab.key)}
            className={`px-4 py-2 rounded-full text-sm font-semibold transition ${
              grupoEstado === tab.key ? 'text-white' : 'text-gray-700 border border-gray-200 bg-white'
            }`}
            style={
              grupoEstado === tab.key
                ? { background: `linear-gradient(135deg, ${COLORS.vino}, ${COLORS.guinda})` }
                : {}
            }
          >
            {tab.label}
            {resumenEstados.por_grupo?.[tab.key] ? ` (${resumenEstados.por_grupo[tab.key]})` : ''}
          </button>
        ))}
      </div>

      {/* Filtros */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <input
            type="text"
            placeholder="Buscar por folio..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          />

          <select
            value={filtroEstado}
            onChange={(e) => setFiltroEstado(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todos los estados</option>
            <option value="borrador">Borrador</option>
            <option value="enviada">Pendiente</option>
            <option value="autorizada">Autorizada</option>
            <option value="rechazada">Rechazada</option>
            <option value="surtida">Surtida</option>
          </select>

          {/* Solo mostrar filtro de centro para farmacia/admin */}
          {(permisos.isFarmaciaAdmin || permisos.isAdmin) && (
            <select
              value={filtroCentro}
              onChange={(e) => setFiltroCentro(e.target.value)}
              className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos los centros</option>
              {centros.map((c) => (
                <option key={c.id} value={c.id}>{c.nombre}</option>
              ))}
            </select>
          )}

          <div className="flex flex-col gap-1">
            <div className="flex gap-2 items-center">
              <input
                type="date"
                value={filtroFechaDesde}
                onChange={(e) => {
                  const desde = e.target.value;
                  // Validar orden cronológico antes de actualizar
                  if (desde && filtroFechaHasta && desde > filtroFechaHasta) {
                    setFechaError('La fecha "desde" no puede ser posterior a "hasta"');
                    return; // No actualizar estado con rango inválido
                  }
                  setFechaError('');
                  setFiltroFechaDesde(desde);
                }}
                max={filtroFechaHasta || undefined}
                className={`px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 flex-1 ${
                  fechaError ? 'border-red-400' : ''
                }`}
                title="Fecha desde"
              />
              <span className="text-gray-400">a</span>
              <input
                type="date"
                value={filtroFechaHasta}
                onChange={(e) => {
                  const hasta = e.target.value;
                  // Validar orden cronológico antes de actualizar
                  if (filtroFechaDesde && hasta && filtroFechaDesde > hasta) {
                    setFechaError('La fecha "hasta" no puede ser anterior a "desde"');
                    return; // No actualizar estado con rango inválido
                  }
                  setFechaError('');
                  setFiltroFechaHasta(hasta);
                }}
                min={filtroFechaDesde || undefined}
                className={`px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 flex-1 ${
                  fechaError ? 'border-red-400' : ''
                }`}
                title="Fecha hasta"
              />
            </div>
            {fechaError && (
              <span className="text-xs text-red-500">{fechaError}</span>
            )}
          </div>
        </div>
        
        {/* Botón limpiar filtros - NO borra filtroCentro para usuarios de centro */}
        {(searchTerm || filtroEstado || (esAdminOFarmacia && filtroCentro) || filtroFechaDesde || filtroFechaHasta || (grupoEstado && grupoEstado !== 'todas')) && (
          <button
            onClick={() => {
              setSearchTerm('');
              setFiltroEstado('');
              // Solo limpiar centro si el usuario puede ver todos los centros
              if (esAdminOFarmacia) {
                setFiltroCentro('');
              }
              setFiltroFechaDesde('');
              setFiltroFechaHasta('');
              setFechaError('');
              setGrupoEstado('todas');
            }}
            className="mt-3 text-sm text-blue-600 hover:text-blue-800 underline"
          >
            Limpiar todos los filtros
          </button>
        )}
      </div>

      {/* Mensaje de error si usuario no tiene centro asignado */}
      {errorCentroNoAsignado && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <FaExclamationTriangle className="text-red-500 text-4xl mx-auto mb-3" />
          <h3 className="text-lg font-bold text-red-700 mb-2">Sin centro asignado</h3>
          <p className="text-red-600 mb-4">
            Tu cuenta de usuario no tiene un centro penitenciario asignado. 
            Contacta al administrador del sistema para que te asigne un centro.
          </p>
          <p className="text-sm text-gray-500">
            Sin un centro asignado no es posible ver ni crear requisiciones.
          </p>
        </div>
      )}

      {/* Lista de Requisiciones */}
      {!errorCentroNoAsignado && (
      <div className="grid grid-cols-1 gap-4">
        {loading || !centroResuelto ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-10 w-10 border-4 border-t-transparent mx-auto" style={{ borderColor: '#9F224133', borderTopColor: '#9F2241' }} />
            <p className="mt-3 text-gray-600">
              {!centroResuelto ? 'Verificando permisos...' : 'Cargando requisiciones...'}
            </p>
          </div>
        ) : requisiciones.length === 0 ? (
          <div className="text-center py-8 bg-white rounded-lg shadow">
            <p className="text-gray-500">No hay requisiciones</p>
          </div>
        ) : (
          requisiciones.map((req) => {
            const totalProductos = req.total_items ?? req.total_productos ?? req.items?.length ?? 0;
            return (
              <div key={req.id} className="bg-white p-6 rounded-lg shadow">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-lg font-bold text-gray-800">{req.folio}</h3>
                    <p className="text-sm text-gray-600">
                      Centro: {req.centro_nombre} | Solicitante: {req.usuario_solicita_nombre || 'N/D'}
                    </p>
                    <p className="text-xs text-gray-500">
                      Fecha: {new Date(req.fecha_solicitud).toLocaleDateString()}
                    </p>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${getEstadoBadge(req.estado)}`}>
                    {getEstadoLabel(req.estado)}
                  </span>
                </div>

                <div className="mb-4">
                  <p className="text-sm">
                    <strong>Productos:</strong> {totalProductos}
                  </p>
                  {req.observaciones && (
                    <p className="text-sm text-gray-600 mt-1">
                      <strong>Observaciones:</strong> {req.observaciones}
                    </p>
                  )}
                  {req.motivo_rechazo && (
                    <p className="text-sm text-red-600 mt-1">
                      <strong>Motivo de rechazo:</strong> {req.motivo_rechazo}
                    </p>
                  )}
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => navigate(`/requisiciones/${req.id}`)}
                    className="bg-gray-100 text-gray-700 px-3 py-1 rounded text-sm flex items-center gap-1 hover:bg-gray-200"
                  >
                    <FaEye /> Ver detalle
                  </button>

                  {puedeEditar(req) && (
                    <button
                      onClick={() => abrirModalEditar(req)}
                      disabled={isSubmitting || actionLoading === req.id}
                      className="bg-gray-100 text-gray-700 px-3 py-1 rounded text-sm flex items-center gap-1 hover:bg-gray-200 border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <FaEdit /> Editar
                    </button>
                  )}

                  {puedeEnviar(req) && (
                    <button
                      onClick={() => handleEnviar(req.id, req.folio)}
                      disabled={isSubmitting || actionLoading === req.id}
                      className="bg-gray-700 text-white px-3 py-1 rounded text-sm flex items-center gap-1 hover:bg-gray-800 disabled:opacity-50"
                    >
                      <FaPaperPlane /> Enviar
                    </button>
                  )}

                  {/* Botón para Revisar y Ajustar - SOLO farmacia/admin con permiso */}
                  {req.estado === 'enviada' && esAdminOFarmacia && permisos.autorizarRequisicion && (
                    <button
                      onClick={() => navigate(`/requisiciones/${req.id}`)}
                      className="text-white px-3 py-1 rounded text-sm font-semibold flex items-center gap-1 hover:opacity-90"
                      style={{ backgroundColor: COLORS.vino }}
                    >
                      <FaEdit /> Revisar
                    </button>
                  )}

                  {req.estado === 'enviada' && esAdminOFarmacia && permisos.rechazarRequisicion && (
                    <button
                      onClick={() => handleRechazar(req.id, req.folio)}
                      disabled={isSubmitting || actionLoading === req.id}
                      className="bg-red-100 text-red-700 px-3 py-1 rounded text-sm flex items-center gap-1 hover:bg-red-200 border border-red-300 disabled:opacity-50"
                    >
                      <FaTimes /> Rechazar
                    </button>
                  )}

                  {req.estado === 'autorizada' && esAdminOFarmacia && permisos.surtirRequisicion && (
                    <button
                      onClick={() => handleSurtir(req.id, req.folio)}
                      disabled={isSubmitting || actionLoading === req.id}
                      className="text-white px-3 py-1 rounded text-sm flex items-center gap-1 hover:opacity-90 disabled:opacity-50"
                      style={{ backgroundColor: COLORS.vino }}
                    >
                      <FaBoxOpen /> Surtir
                    </button>
                  )}

                  {['autorizada', 'parcial', 'surtida'].includes(req.estado) &&
                    puedeDescargarPDF(req) && (
                      <button
                        onClick={() => handleDescargarPDF(req.id, 'aceptacion', req.folio)}
                        disabled={actionLoading === `pdf-${req.id}`}
                        className="bg-green-100 text-green-700 px-3 py-1 rounded text-sm flex items-center gap-1 hover:bg-green-200 border border-green-300 font-semibold disabled:opacity-50"
                      >
                        {actionLoading === `pdf-${req.id}` ? (
                          <div className="animate-spin rounded-full h-4 w-4 border-2 border-green-700 border-t-transparent" />
                        ) : (
                          <><FaDownload /> 📄 Hoja Oficial</>
                        )}
                      </button>
                    )}

                  {req.estado === 'rechazada' && puedeDescargarPDF(req) && (
                    <button
                      onClick={() => handleDescargarPDF(req.id, 'rechazo', req.folio)}
                      disabled={actionLoading === `pdf-${req.id}`}
                      className="bg-red-100 text-red-700 px-3 py-1 rounded text-sm flex items-center gap-1 hover:bg-red-200 border border-red-300 font-semibold disabled:opacity-50"
                    >
                      {actionLoading === `pdf-${req.id}` ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-red-700 border-t-transparent" />
                      ) : (
                        <><FaDownload /> 📄 Notificación</>
                      )}
                    </button>
                  )}

                  {puedeCancelar(req) && (
                    <button
                      onClick={() => handleCancelar(req.id, req.folio)}
                      disabled={isSubmitting || actionLoading === req.id}
                      className="bg-gray-100 text-gray-600 px-3 py-1 rounded text-sm flex items-center gap-1 hover:bg-gray-200 border border-gray-300 disabled:opacity-50"
                    >
                      <FaBan /> Cancelar
                    </button>
                  )}

                  {puedeEditar(req) && permisos.eliminarRequisicion && (
                    <button
                      onClick={() => confirmarEliminar(req)}
                      disabled={isSubmitting || actionLoading === req.id}
                      className="border border-red-300 text-red-600 px-3 py-1 rounded text-sm flex items-center gap-1 hover:bg-red-50 transition-colors disabled:opacity-50"
                    >
                      <FaTrash /> Eliminar
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
      )}

      {!loading && !errorCentroNoAsignado && totalRequisiciones > 0 && (
        <div className="mt-6">
          <Pagination
            page={currentPage}
            totalPages={totalPages}
            totalItems={totalRequisiciones}
            pageSize={PAGE_SIZE}
            onPageChange={setCurrentPage}
          />
        </div>
      )}

      {/* Modal crear/editar - NUEVO DISEÑO CON CATÁLOGO PRECARGADO */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-40 px-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-6xl w-full relative max-h-[95vh] flex flex-col">
            {/* Header del modal */}
            <div className="p-4 border-b flex items-center justify-between flex-shrink-0">
              <div>
                <h2 className="text-xl font-bold" style={{ color: COLORS.vino }}>
                  {editRequisicion ? 'Editar requisición' : 'Nueva requisición'}
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  Selecciona los productos y cantidades que necesitas
                </p>
              </div>
              
              {/* Toggle Catálogo / Carrito */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setVistaCarrito(false)}
                  className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all ${
                    !vistaCarrito 
                      ? 'text-white' 
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                  style={!vistaCarrito ? { backgroundColor: COLORS.vino } : {}}
                >
                  <FaSearch /> Catálogo
                </button>
                <button
                  onClick={() => setVistaCarrito(true)}
                  className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all relative ${
                    vistaCarrito 
                      ? 'text-white' 
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                  style={vistaCarrito ? { backgroundColor: COLORS.vino } : {}}
                >
                  <FaShoppingCart /> 
                  Mi Pedido
                  {form.items.length > 0 && (
                    <span className={`ml-1 px-2 py-0.5 rounded-full text-xs font-bold ${
                      vistaCarrito ? 'bg-white text-gray-800' : 'bg-red-500 text-white'
                    }`}>
                      {form.items.length}
                    </span>
                  )}
                </button>
              </div>
            </div>

            {/* Contenido principal */}
            <div className="flex-1 overflow-hidden flex flex-col p-4">
              {/* Datos del centro y comentario */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4 flex-shrink-0">
                {(permisos.isFarmaciaAdmin || permisos.isAdmin) && (
                  <div>
                    <label className="block text-sm font-semibold mb-1">Centro solicitante</label>
                    <select
                      value={form.centro}
                      onChange={(e) => setForm((prev) => ({ ...prev, centro: e.target.value }))}
                      className="w-full border rounded-lg px-3 py-2"
                    >
                      <option value="">Seleccione centro</option>
                      {centros.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.nombre}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                <div>
                  <label className="block text-sm font-semibold mb-1">Comentario (opcional)</label>
                  <input
                    type="text"
                    value={form.comentario}
                    onChange={(e) => setForm((prev) => ({ ...prev, comentario: e.target.value }))}
                    placeholder="Notas adicionales..."
                    className="w-full border rounded-lg px-3 py-2"
                  />
                </div>
              </div>

              {/* Vista de Catálogo */}
              {!vistaCarrito ? (
                <div className="flex-1 flex flex-col min-h-0">
                  {/* Buscador del catálogo */}
                  <div className="mb-4 flex-shrink-0">
                    <div className="relative">
                      <FaSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                      <input
                        type="text"
                        placeholder="Buscar por clave, descripción o número de lote..."
                        value={catalogoBusqueda}
                        onChange={(e) => setCatalogoBusqueda(e.target.value)}
                        className="w-full border rounded-lg pl-10 pr-4 py-3 text-sm"
                        autoFocus
                      />
                      {catalogoBusqueda && (
                        <button
                          onClick={() => setCatalogoBusqueda('')}
                          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                        >
                          <FaTimes />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Lista del catálogo */}
                  <div className="flex-1 overflow-y-auto border rounded-lg">
                    {loadingCatalogo ? (
                      <div className="flex items-center justify-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-4 border-t-transparent mr-3" style={{ borderColor: '#9F224133', borderTopColor: '#9F2241' }} />
                        <span className="text-gray-500">Cargando catálogo...</span>
                      </div>
                    ) : catalogoAgrupado.length === 0 ? (
                      <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                        <FaExclamationTriangle className="text-4xl mb-3 text-amber-400" />
                        <p className="font-semibold">No se encontraron productos</p>
                        <p className="text-sm">Intenta con otra búsqueda</p>
                      </div>
                    ) : (
                      <table className="w-full text-sm">
                        <thead className="bg-gray-100 sticky top-0">
                          <tr>
                            <th className="text-left px-4 py-3 font-semibold">Clave</th>
                            <th className="text-left px-4 py-3 font-semibold">Descripción</th>
                            <th className="text-left px-4 py-3 font-semibold">Lote</th>
                            <th className="text-center px-4 py-3 font-semibold">Caducidad</th>
                            <th className="text-center px-4 py-3 font-semibold">Inventario</th>
                            <th className="text-center px-4 py-3 font-semibold w-40">Cantidad</th>
                          </tr>
                        </thead>
                        <tbody>
                          {catalogoAgrupado.map((grupo) => (
                            grupo.lotes.map((lote, loteIdx) => {
                              const enCarrito = loteEnCarrito(lote.id);
                              const cantidadCarrito = getCantidadEnCarrito(lote.id);
                              const stockDisponible = lote.stock_actual ?? lote.cantidad_actual ?? 0;
                              const fechaCad = lote.fecha_caducidad;
                              const esCaducidadProxima = fechaCad && new Date(fechaCad) <= new Date(Date.now() + 90 * 24 * 60 * 60 * 1000);
                              
                              return (
                                <tr 
                                  key={lote.id} 
                                  className={`border-t hover:bg-gray-50 transition-colors ${
                                    enCarrito ? 'bg-green-50' : ''
                                  }`}
                                >
                                  {loteIdx === 0 ? (
                                    <>
                                      <td 
                                        className="px-4 py-3 font-bold align-top"
                                        style={{ color: COLORS.vino }}
                                        rowSpan={grupo.lotes.length}
                                      >
                                        {grupo.producto_clave}
                                      </td>
                                      <td 
                                        className="px-4 py-3 align-top"
                                        rowSpan={grupo.lotes.length}
                                      >
                                        <span className="line-clamp-2">{grupo.producto_descripcion}</span>
                                      </td>
                                    </>
                                  ) : null}
                                  <td className="px-4 py-3">
                                    <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                                      {lote.numero_lote}
                                    </span>
                                  </td>
                                  <td className={`px-4 py-3 text-center text-xs ${
                                    esCaducidadProxima ? 'text-amber-600 font-semibold' : 'text-gray-500'
                                  }`}>
                                    {fechaCad || '-'}
                                  </td>
                                  <td className="px-4 py-3 text-center">
                                    <span className={`font-bold ${
                                      stockDisponible < 10 ? 'text-red-600' : 
                                      stockDisponible < 50 ? 'text-amber-600' : 'text-green-600'
                                    }`}>
                                      {stockDisponible}
                                    </span>
                                  </td>
                                  <td className="px-4 py-3 text-center">
                                    {enCarrito ? (
                                      <div className="flex items-center justify-center gap-1">
                                        <button
                                          onClick={() => decrementarCantidad(lote.id)}
                                          className="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center text-gray-700 transition-colors"
                                        >
                                          <FaMinus className="text-xs" />
                                        </button>
                                        <span className="w-12 text-center font-bold text-green-700">
                                          {cantidadCarrito}
                                        </span>
                                        <button
                                          onClick={() => incrementarCantidad(lote.id)}
                                          disabled={cantidadCarrito >= stockDisponible}
                                          className="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center text-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                          <FaPlus className="text-xs" />
                                        </button>
                                      </div>
                                    ) : (
                                      <button
                                        onClick={() => agregarDesdeCatalogo(lote)}
                                        disabled={stockDisponible <= 0}
                                        className="px-4 py-1.5 rounded-lg text-white text-xs font-semibold hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 mx-auto"
                                        style={{ backgroundColor: COLORS.vino }}
                                      >
                                        <FaPlus /> Agregar
                                      </button>
                                    )}
                                  </td>
                                </tr>
                              );
                            })
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                  
                  {/* Info del catálogo */}
                  <div className="mt-2 flex items-center justify-between text-xs text-gray-500 flex-shrink-0">
                    <span>
                      {catalogoAgrupado.length} productos · {catalogoFiltrado.length} lotes disponibles
                    </span>
                    {form.items.length > 0 && (
                      <button
                        onClick={() => setVistaCarrito(true)}
                        className="flex items-center gap-1 text-green-600 font-semibold hover:text-green-700"
                      >
                        <FaShoppingCart /> Ver mi pedido ({form.items.length} productos, {totalItemsCarrito} unidades)
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                /* Vista del Carrito / Pedido */
                <div className="flex-1 flex flex-col min-h-0">
                  {form.items.length === 0 ? (
                    <div className="flex-1 flex flex-col items-center justify-center text-gray-500 py-12">
                      <FaShoppingCart className="text-6xl mb-4 text-gray-300" />
                      <p className="font-semibold text-lg">Tu pedido está vacío</p>
                      <p className="text-sm mb-4">Agrega productos desde el catálogo</p>
                      <button
                        onClick={() => setVistaCarrito(false)}
                        className="px-4 py-2 rounded-lg text-white font-semibold"
                        style={{ backgroundColor: COLORS.vino }}
                      >
                        <FaSearch className="inline mr-2" /> Ir al catálogo
                      </button>
                    </div>
                  ) : (
                    <>
                      {/* Tabla del carrito */}
                      <div className="flex-1 overflow-y-auto border rounded-lg">
                        <table className="w-full text-sm">
                          <thead className="bg-gray-100 sticky top-0">
                            <tr>
                              <th className="text-left px-4 py-3 font-semibold">Producto</th>
                              <th className="text-left px-4 py-3 font-semibold">Lote</th>
                              <th className="text-center px-4 py-3 font-semibold">Caducidad</th>
                              <th className="text-center px-4 py-3 font-semibold">Inv. Disp.</th>
                              <th className="text-center px-4 py-3 font-semibold">Cantidad</th>
                              <th className="text-center px-4 py-3 font-semibold w-24">Quitar</th>
                            </tr>
                          </thead>
                          <tbody>
                            {form.items.map((item, idx) => (
                              <tr key={`${item.lote}-${idx}`} className="border-t hover:bg-gray-50">
                                <td className="px-4 py-3">
                                  <div>
                                    <span className="font-bold text-sm" style={{ color: COLORS.vino }}>
                                      {item.producto_clave}
                                    </span>
                                    <p className="text-sm text-gray-600 line-clamp-1">{item.descripcion}</p>
                                  </div>
                                </td>
                                <td className="px-4 py-3">
                                  <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                                    {item.lote_numero || '-'}
                                  </span>
                                </td>
                                <td className="px-4 py-3 text-center text-xs text-gray-500">
                                  {item.lote_caducidad || '-'}
                                </td>
                                <td className="px-4 py-3 text-center font-semibold">
                                  {item.stock_disponible || '-'}
                                </td>
                                <td className="px-4 py-3 text-center">
                                  <div className="flex items-center justify-center gap-1">
                                    <button
                                      onClick={() => {
                                        if (item.cantidad_solicitada <= 1) {
                                          eliminarItem(idx);
                                        } else {
                                          actualizarCantidad(idx, item.cantidad_solicitada - 1);
                                        }
                                      }}
                                      className="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center"
                                    >
                                      <FaMinus className="text-xs" />
                                    </button>
                                    <input
                                      type="number"
                                      min="1"
                                      max={item.stock_disponible || 9999}
                                      value={item.cantidad_solicitada}
                                      onChange={(e) => actualizarCantidad(idx, e.target.value)}
                                      className="w-16 border rounded px-2 py-1 text-center font-bold"
                                    />
                                    <button
                                      onClick={() => actualizarCantidad(idx, item.cantidad_solicitada + 1)}
                                      disabled={item.cantidad_solicitada >= (item.stock_disponible || 9999)}
                                      className="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center disabled:opacity-50"
                                    >
                                      <FaPlus className="text-xs" />
                                    </button>
                                  </div>
                                </td>
                                <td className="px-4 py-3 text-center">
                                  <button
                                    onClick={() => eliminarItem(idx)}
                                    className="text-red-600 hover:text-red-800 p-2 rounded hover:bg-red-50 transition-colors"
                                    title="Quitar del pedido"
                                  >
                                    <FaTrash />
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      {/* Resumen del pedido */}
                      <div className="mt-4 bg-gray-50 rounded-lg p-4 flex items-center justify-between flex-shrink-0">
                        <div>
                          <p className="text-sm text-gray-600">
                            <strong>{form.items.length}</strong> productos diferentes · 
                            <strong className="ml-1">{totalItemsCarrito}</strong> unidades totales
                          </p>
                        </div>
                        <button
                          onClick={() => setVistaCarrito(false)}
                          className="text-sm text-gray-600 hover:text-gray-800 flex items-center gap-1"
                        >
                          <FaPlus /> Agregar más productos
                        </button>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Footer con botones de acción */}
            <div className="p-4 border-t flex justify-between items-center flex-shrink-0 bg-gray-50">
              <button
                onClick={() => {
                  setShowModal(false);
                  resetForm();
                }}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-lg border text-gray-700 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancelar
              </button>
              
              <div className="flex gap-3">
                {/* Botón guardar borrador - requiere permiso crear/editar y centro seleccionado */}
                <button
                  type="button"
                  onClick={() => guardarRequisicion(false)}
                  disabled={
                    isSubmitting || 
                    form.items.length === 0 ||
                    (editRequisicion ? !permisos?.editarRequisicion : !permisos?.crearRequisicion) ||
                    ((permisos.isFarmaciaAdmin || permisos.isAdmin) && !form.centro)
                  }
                  title={
                    (permisos.isFarmaciaAdmin || permisos.isAdmin) && !form.centro
                      ? 'Debe seleccionar un centro solicitante'
                      : (editRequisicion 
                          ? (!permisos?.editarRequisicion ? 'No tienes permisos para editar' : '')
                          : (!permisos?.crearRequisicion ? 'No tienes permisos para crear' : ''))
                  }
                  className="px-5 py-2 rounded-lg border-2 font-semibold hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  style={{ borderColor: COLORS.vino, color: COLORS.vino }}
                >
                  {isSubmitting ? 'Guardando...' : 'Guardar borrador'}
                </button>
                {/* Botón guardar y enviar - requiere permiso crear/editar + enviar + centro */}
                <button
                  type="button"
                  onClick={() => guardarRequisicion(true)}
                  disabled={
                    isSubmitting || 
                    form.items.length === 0 ||
                    !permisos?.enviarRequisicion ||
                    (editRequisicion ? !permisos?.editarRequisicion : !permisos?.crearRequisicion) ||
                    ((permisos.isFarmaciaAdmin || permisos.isAdmin) && !form.centro)
                  }
                  title={
                    (permisos.isFarmaciaAdmin || permisos.isAdmin) && !form.centro
                      ? 'Debe seleccionar un centro solicitante'
                      : (!permisos?.enviarRequisicion 
                          ? 'No tienes permisos para enviar requisiciones' 
                          : (editRequisicion 
                              ? (!permisos?.editarRequisicion ? 'No tienes permisos para editar' : '')
                              : (!permisos?.crearRequisicion ? 'No tienes permisos para crear' : '')))
                  }
                  className="px-5 py-2 rounded-lg text-white font-semibold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  style={{ backgroundColor: COLORS.vino }}
                >
                  <FaPaperPlane />
                  {isSubmitting ? 'Enviando...' : 'Guardar y enviar'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Confirmación eliminar */}
      {confirmDelete && (
        <ConfirmModal
          open={!!confirmDelete}
          title="Eliminar requisición"
          message={`¿Deseas eliminar la requisición ${confirmDelete.folio || confirmDelete.id}?`}
          onCancel={() => setConfirmDelete(null)}
          onConfirm={eliminarRequisicion}
          loading={isSubmitting}
        />
      )}
      
      {/* Modal confirmación enviar */}
      <ConfirmModal
        open={!!confirmEnviar}
        title="Enviar requisición"
        message={`¿Confirma ENVIAR la requisición ${confirmEnviar?.folio || confirmEnviar?.id}? Una vez enviada, no podrá modificarla y quedará pendiente de autorización.`}
        confirmText="Enviar"
        onCancel={() => setConfirmEnviar(null)}
        onConfirm={ejecutarEnviar}
        loading={isSubmitting}
        tone="info"
      />
      
      {/* Modal confirmación surtir */}
      <ConfirmModal
        open={!!confirmSurtir}
        title="Surtir requisición"
        message={`¿Confirma SURTIR la requisición ${confirmSurtir?.folio || confirmSurtir?.id}? ⚠️ Esta acción descontará el inventario de los lotes. Asegúrese de que el stock esté disponible.`}
        confirmText="Surtir"
        onCancel={() => setConfirmSurtir(null)}
        onConfirm={ejecutarSurtir}
        loading={isSubmitting}
        tone="danger"
      />
      
      {/* Modal input rechazo */}
      <InputModal
        open={!!inputRechazo}
        title="Rechazar requisición"
        message={`Ingrese el motivo del rechazo para ${inputRechazo?.folio || 'la requisición'}:`}
        placeholder="Escriba el motivo del rechazo..."
        confirmText="Rechazar"
        minLength={10}
        onCancel={() => setInputRechazo(null)}
        onConfirm={ejecutarRechazo}
        loading={isSubmitting}
        tone="danger"
      />
      
      {/* Modal input cancelar */}
      <InputModal
        open={!!inputCancelar}
        title="Cancelar requisición"
        message={`Ingrese el motivo de cancelación para ${inputCancelar?.folio || 'la requisición'} (obligatorio para auditoría):`}
        placeholder="Escriba el motivo de la cancelación..."
        confirmText="Cancelar requisición"
        minLength={5}
        onCancel={() => setInputCancelar(null)}
        onConfirm={ejecutarCancelar}
        loading={isSubmitting}
        tone="danger"
      />
    </div>
  );
};

export default Requisiciones;
