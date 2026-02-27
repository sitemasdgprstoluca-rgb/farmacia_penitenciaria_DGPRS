import { useState, useEffect, useCallback, useRef } from 'react';
import { lotesAPI, productosAPI, centrosAPI, abrirPdfEnNavegador } from '../services/api';
import { toast } from 'react-hot-toast';
import { hasAccessToken } from '../services/tokenManager';
import {
  FaPlus,
  FaEdit,
  FaTrash,
  FaFileExcel,
  FaFileUpload,
  FaExclamationTriangle,
  FaFilter,
  FaWarehouse,
  FaFilePdf,
  FaDownload,
  FaTimes,
  FaChevronDown,
  FaHistory,
  FaBoxes,
  FaCheck
} from 'react-icons/fa';
import { DEV_CONFIG } from '../config/dev';
import PageHeader from '../components/PageHeader';
import { COLORS, SECONDARY_GRADIENT } from '../constants/theme';
import Pagination from '../components/Pagination';
import { LotesSkeleton } from '../components/skeletons';
import { usePermissions } from '../hooks/usePermissions';
import { puedeVerGlobal as checkPuedeVerGlobal, esFarmaciaAdmin as checkEsFarmaciaAdmin } from '../utils/roles';
// ISS-SEC: Componentes para confirmación en 2 pasos
import TwoStepConfirmModal from '../components/TwoStepConfirmModal';
import { useConfirmation } from '../hooks/useConfirmation';
// ISS-IMPORT: Componente moderno de importación
import ImportadorModerno from '../components/ImportadorModerno';

// Formatear fecha YYYY-MM-DD sin conversión de timezone
// Evita el bug de restar 1 día cuando JavaScript interpreta "2027-06-01" como UTC medianoche
const formatFecha = (fechaStr) => {
  if (!fechaStr) return '';
  const [year, month, day] = fechaStr.split('-');
  return `${day}/${month}/${year}`;
};

const MOCK_PRODUCTOS = Array.from({ length: 40 }).map((_, index) => ({
  id: index + 1,
  clave: `MED-${String(index + 1).padStart(3, '0')}`,
  nombre: `Producto simulado ${index + 1}`,
}));

const createMockLote = (index) => {
  const producto = MOCK_PRODUCTOS[index % MOCK_PRODUCTOS.length];
  const diferenciaDias = -20 + index * 3;
  const fecha = new Date();
  fecha.setDate(fecha.getDate() + diferenciaDias);
  const diasParaCaducar = Math.ceil((fecha.getTime() - Date.now()) / 86400000);
  let alerta = 'normal';
  if (diasParaCaducar < 0) alerta = 'vencido';
  else if (diasParaCaducar <= 7) alerta = 'critico';
  else if (diasParaCaducar <= 30) alerta = 'proximo';

  const cantidadInicial = 100 + (index % 4) * 50;
  const cantidadActual = Math.max(0, cantidadInicial - (index % 5) * 20);

  return {
    id: index + 1,
    producto: producto.id,
    producto_clave: producto.clave,
    producto_nombre: producto.nombre,
    numero_lote: `L-${202300 + index}`,
    fecha_caducidad: fecha.toISOString(),
    dias_para_caducar: diasParaCaducar,
    alerta_caducidad: alerta,
    cantidad_inicial: cantidadInicial,
    cantidad_actual: cantidadActual,
    porcentaje_consumido: Math.round(
      (1 - cantidadActual / cantidadInicial) * 100,
    ),
    marca: `Marca ${index % 6 + 1}`,
    observaciones: '',
    activo: index % 9 !== 0,
  };
};

const MOCK_LOTES = Array.from({ length: 60 }).map((_, index) =>
  createMockLote(index),
);

const Lotes = () => {
  const { getRolPrincipal, permisos, user } = usePermissions();
  const rolPrincipal = getRolPrincipal();
  // FRONT-006 FIX: Usar lógica centralizada de roles
  const puedeVerGlobal = checkPuedeVerGlobal(user, permisos);
  // Centro del usuario para forzar filtro si no tiene permisos globales
  const centroUsuario = user?.centro?.id || user?.centro || user?.centro_id;
  // Solo ADMIN y FARMACIA pueden ver campos de contrato (para auditoría)
  const puedeVerContrato = checkEsFarmaciaAdmin(user);
  
  // ISS-SEC: Hook para confirmación en 2 pasos
  const {
    confirmState,
    requestDeleteConfirmation,
    requestSaveConfirmation,
    executeWithConfirmation,
    cancelConfirmation,
  } = useConfirmation();
  
  // Permisos específicos para acciones - usar permisos finos del backend
  const esFarmaciaAdmin = checkEsFarmaciaAdmin(user);
  // P0-2 FIX: Solo admin/farmacia pueden autorizar sobre-entregas (mismo criterio que backend)
  const puedeOverrideSobreentrega = esFarmaciaAdmin;
  const puede = {
    // Usar permisos finos si existen, sino fallback al rol
    crear: permisos?.crearLote === true || (esFarmaciaAdmin && permisos?.crearLote !== false),
    editar: permisos?.editarLote === true || (esFarmaciaAdmin && permisos?.editarLote !== false),
    eliminar: permisos?.eliminarLote === true || (esFarmaciaAdmin && permisos?.eliminarLote !== false),
    exportar: permisos?.exportarLotes === true || (esFarmaciaAdmin && permisos?.exportarLotes !== false) || (rolPrincipal === 'VISTA' && permisos?.exportarLotes !== false),
    importar: permisos?.importarLotes === true || (esFarmaciaAdmin && permisos?.importarLotes !== false),
    verDocumento: true, // Todos pueden ver
    subirDocumento: permisos?.crearLote === true || (esFarmaciaAdmin && permisos?.crearLote !== false),
    // P0-2: Override de sobre-entrega requiere rol admin/farmacia
    overrideSobreentrega: puedeOverrideSobreentrega,
  };
  
  const [lotes, setLotes] = useState([]);
  const [productos, setProductos] = useState([]);
  const [centros, setCentros] = useState([]);
  const [loading, setLoading] = useState(false); // Solo para carga de tabla
  const [savingLote, setSavingLote] = useState(false); // Para guardar en modal
  const [exportLoading, setExportLoading] = useState(false); // Para exportar Excel
  const [exportPdfLoading, setExportPdfLoading] = useState(false); // Para exportar PDF
  const [importLoading, setImportLoading] = useState(false); // Para importar
  const [actionLoading, setActionLoading] = useState(null); // ID del lote en acción (delete/doc)
  const [showModal, setShowModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showDocModal, setShowDocModal] = useState(false);
  const [selectedLoteDoc, setSelectedLoteDoc] = useState(null);
  const [editingLote, setEditingLote] = useState(null);
  const [showFiltersMenu, setShowFiltersMenu] = useState(false);
  // Modal de Parcialidades (entregas parciales)
  const [showParcialidadesModal, setShowParcialidadesModal] = useState(false);
  const [selectedLoteParcialidades, setSelectedLoteParcialidades] = useState(null);
  const [parcialidadesData, setParcialidadesData] = useState({ parcialidades: [], resumen: {}, contrato_lote: {} });
  const [loadingParcialidades, setLoadingParcialidades] = useState(false);
  const [exportingEntregas, setExportingEntregas] = useState(null); // 'pdf' o 'excel'
  const [nuevaParcialidad, setNuevaParcialidad] = useState({ fecha_entrega: '', cantidad: '', notas: '' });
  // Override para sobre-entregas (contrato cumplido)
  const [requiereOverride, setRequiereOverride] = useState(false);
  const [motivoOverride, setMotivoOverride] = useState('');
  const [infoContratoCumplido, setInfoContratoCumplido] = useState(null);
  // ISS-SEC: Doble confirmación para agregar entregas (modifica inventario)
  const [confirmarEntrega, setConfirmarEntrega] = useState({ show: false, forceOverride: false });
  // Auto-completado de Contrato Global
  const [cargandoCCG, setCargandoCCG] = useState(false);
  const [ccgAutoCompletado, setCcgAutoCompletado] = useState(false);
  const ccgTimerRef = useRef(null);

  // Paginación
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalLotes, setTotalLotes] = useState(0);
  const pageSize = 25;
  
  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [filtroProducto, setFiltroProducto] = useState('');
  const [filtroCaducidad, setFiltroCaducidad] = useState('');
  const [filtroConStock, setFiltroConStock] = useState('');
  // ISS-FIX: CENTRO/MEDICO solo ven lotes activos por defecto (con stock)
  // FARMACIA/ADMIN pueden ver todos (incluidos sin stock) para gestión completa
  const [filtroActivo, setFiltroActivo] = useState(() => {
    return puedeVerGlobal ? '' : 'true';  // Centro/Medico: solo activos por defecto
  });
  // Usuarios sin permisos globales siempre deben filtrar por su centro
  // CORREGIDO: Usar contexto de autenticación (centroUsuario) en lugar de localStorage
  // para evitar desincronización en cambios de sesión
  const [filtroCentro, setFiltroCentro] = useState(() => {
    // Inicializar vacío - el useEffect se encargará de forzar el centro correcto
    // según el contexto de autenticación actual
    return '';
  });
  
  // Estado para detectar usuario sin centro asignado (error de configuración)
  const [errorSinCentro, setErrorSinCentro] = useState(false);
  
  // ISS-DB: Campos alineados con tabla lotes de Supabase
  // Campos reales: numero_lote, producto_id, cantidad_inicial, cantidad_actual, cantidad_contrato,
  // fecha_fabricacion, fecha_caducidad, precio_unitario, numero_contrato, marca, ubicacion, centro_id, activo
  const [formData, setFormData] = useState({
    producto: '',
    presentacion_producto: '', // Campo solo lectura - presentación viene del producto
    numero_lote: '',
    fecha_fabricacion: '',    // Campo real en DB
    fecha_caducidad: '',
    cantidad_contrato: '',    // ISS-INV-001: Total según contrato por lote (OPCIONAL)
    cantidad_contrato_global: '', // ISS-INV-003: Total contrato para toda la clave de producto
    cantidad_inicial: '',      // Unidades realmente recibidas (obligatorio)
    precio_unitario: '',      // Nombre real en DB (antes precio_compra)
    numero_contrato: '',
    marca: '',
    ubicacion: '',            // Campo real en DB
    centro: ''                // Solo editable por admin/farmacia
  });

  const nivelCaducidad = [
    { value: '', label: 'Todas las caducidades' },
    { value: 'vencido', label: '🔴 Vencidos' },
    { value: 'critico', label: '🔴 Crítico (< 3 meses)' },
    { value: 'proximo', label: '🟡 Próximo (3-6 meses)' },
    { value: 'normal', label: '🟢 Normal (> 6 meses)' }
  ];

  useEffect(() => {
    cargarProductos();
    if (puedeVerGlobal) {
      cargarCentros();
    }
  }, [puedeVerGlobal]);

  // Forzar filtro de centro para usuarios sin permisos globales
  // IMPORTANTE: Si el usuario no tiene permiso global Y no tiene centro, bloquear acceso
  useEffect(() => {
    if (puedeVerGlobal) {
      // Usuarios con permisos globales pueden ver todo, no hay error
      setErrorSinCentro(false);
    } else if (centroUsuario) {
      // Usuario de centro con centro asignado - aplicar filtro
      setFiltroCentro(centroUsuario.toString());
      setErrorSinCentro(false);
    } else if (user && !centroUsuario) {
      // Usuario autenticado pero SIN centro asignado - ERROR de configuración
      // Esto previene que vea todos los lotes
      setErrorSinCentro(true);
      console.error('Usuario sin centro asignado intentando acceder a Lotes:', user?.username);
    }
  }, [puedeVerGlobal, centroUsuario, user]);

  const cargarCentros = async () => {
    try {
      const response = await centrosAPI.getAll({ page_size: 100, ordering: 'nombre', activo: true });
      setCentros(response.data.results || response.data || []);
    } catch (error) {
      console.error('Error al cargar centros:', error);
    }
  };

  // =========================================================================
  // AUTO-FILL CCG: cuando producto + numero_contrato están listos,
  // buscar lotes existentes del mismo contrato y heredar cantidad_contrato_global
  // =========================================================================
  useEffect(() => {
    if (editingLote) return; // No auto-completar en edición
    const producto = formData.producto;
    const contrato = formData.numero_contrato?.trim();
    if (!producto || !contrato || contrato.length < 3) {
      setCcgAutoCompletado(false);
      return;
    }
    // Debounce: esperar 500ms desde la última tecla antes de consultar
    clearTimeout(ccgTimerRef.current);
    ccgTimerRef.current = setTimeout(async () => {
      try {
        setCargandoCCG(true);
        const resp = await lotesAPI.getAll({
          producto,
          numero_contrato: contrato,
          activo: true,
          page_size: 1,
        });
        const primerLote = (resp.data.results || resp.data || [])[0];
        if (primerLote?.cantidad_contrato_global != null) {
          setFormData(prev => ({
            ...prev,
            cantidad_contrato_global: primerLote.cantidad_contrato_global,
          }));
          setCcgAutoCompletado(true);
        } else {
          // Contratonuevo sin CCG registrado: limpiar si era auto-completado antes
          setCcgAutoCompletado(prev => {
            if (prev) setFormData(f => ({ ...f, cantidad_contrato_global: '' }));
            return false;
          });
        }
      } catch {
        setCcgAutoCompletado(false);
      } finally {
        setCargandoCCG(false);
      }
    }, 500);
    return () => clearTimeout(ccgTimerRef.current);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formData.numero_contrato, formData.producto, editingLote]);

  const cargarProductos = async () => {
    try {
      if (DEV_CONFIG.MOCKS_ENABLED && !hasAccessToken()) {
        setProductos(MOCK_PRODUCTOS);
        return;
      }

      const response = await productosAPI.getAll({ activo: true, page_size: 1000 });
      setProductos(response.data.results || response.data);
    } catch (error) {
      if (DEV_CONFIG.MOCKS_ENABLED) {
        setProductos(MOCK_PRODUCTOS);
        return;
      }
      console.error('Error al cargar productos:', error);
    }
  };

  const applyMockLotes = useCallback(() => {
    let data = [...MOCK_LOTES];

    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      data = data.filter(
        (lote) =>
          lote.numero_lote.toLowerCase().includes(term) ||
          lote.producto_clave.toLowerCase().includes(term) ||
          lote.producto_nombre.toLowerCase().includes(term)
      );
    }
    if (filtroProducto) data = data.filter((lote) => String(lote.producto) === String(filtroProducto));
    if (filtroCaducidad) data = data.filter((lote) => lote.alerta_caducidad === filtroCaducidad);
    if (filtroConStock) {
      data = data.filter((lote) =>
        filtroConStock === 'con_stock' ? lote.cantidad_actual > 0 : lote.cantidad_actual === 0
      );
    }
    if (filtroActivo) data = data.filter((lote) => String(lote.activo) === filtroActivo);

    const total = data.length;
    const start = (currentPage - 1) * pageSize;
    const results = data.slice(start, start + pageSize);
    setLotes(results);
    setTotalLotes(total);
    setTotalPages(Math.max(1, Math.ceil(total / pageSize)));
    setLoading(false);
  }, [currentPage, filtroActivo, filtroCaducidad, filtroConStock, filtroProducto, pageSize, searchTerm]);

  const cargarLotes = useCallback(async () => {
    // SEGURIDAD: Bloquear carga si usuario sin permisos globales no tiene centro
    if (errorSinCentro) {
      setLotes([]);
      setTotalLotes(0);
      setTotalPages(1);
      setLoading(false);
      return;
    }
    
    setLoading(true);
    try {
      if (DEV_CONFIG.ENABLED && !hasAccessToken()) {
        applyMockLotes();
        return;
      }

      const params = {
        page: currentPage,
        page_size: pageSize
      };

      if (searchTerm) params.search = searchTerm;
      if (filtroProducto) params.producto = filtroProducto;
      if (filtroCaducidad) params.caducidad = filtroCaducidad;
      if (filtroConStock) params.con_stock = filtroConStock;
      if (filtroActivo) params.activo = filtroActivo;
      
      // TRAZABILIDAD: Admin/Farmacia ven lotes CONSOLIDADOS (únicos, sin duplicados)
      // Usuarios de centro ven solo sus lotes (no consolidados)
      if (puedeVerGlobal) {
        // Usar endpoint consolidado para admin/farmacia
        // IMPORTANTE: Siempre respetar el filtro de centro seleccionado
        // Admin/farmacia ven lotes con stock=0 (backend ya maneja esto)
        if (filtroCentro === 'todos') {
          // Sin parámetro centro = ver todo consolidado
        } else if (filtroCentro) {
          // Un centro específico por ID
          params.centro = filtroCentro;
        } else {
          // Vacío = Farmacia Central por defecto
          params.centro = 'central';
        }
        const response = await lotesAPI.getConsolidados(params);
        setLotes(response.data.results || response.data);
        setTotalLotes(response.data.count || 0);
        setTotalPages(response.data.total_pages || Math.ceil((response.data.count || 0) / pageSize));
      } else {
        // Usuarios de centro: ver lotes normales de su centro
        const centroParaCargar = centroUsuario?.toString() || filtroCentro;
        // SEGURIDAD: Si no tiene permiso global y no hay centro, NO cargar
        if (!puedeVerGlobal && !centroParaCargar) {
          console.warn('Usuario sin centro intentando cargar lotes - bloqueado');
          setLotes([]);
          setLoading(false);
          return;
        }
        if (centroParaCargar) params.centro = centroParaCargar;

        const response = await lotesAPI.getAll(params);
        setLotes(response.data.results || response.data);
        setTotalLotes(response.data.count || 0);
        setTotalPages(Math.ceil((response.data.count || 0) / pageSize));
      }
    } catch (error) {
      if (DEV_CONFIG.ENABLED) {
        applyMockLotes();
        return;
      }
      toast.error('Error al cargar lotes');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [applyMockLotes, currentPage, filtroActivo, filtroCaducidad, filtroConStock, filtroProducto, filtroCentro, pageSize, searchTerm, puedeVerGlobal, centroUsuario, errorSinCentro]);

  // Debounce para búsqueda y filtros - aplica delay solo a searchTerm
  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      cargarLotes();
    }, searchTerm ? 300 : 0); // 300ms delay solo cuando hay búsqueda activa

    return () => clearTimeout(delayDebounceFn);
  }, [currentPage, filtroActivo, filtroCaducidad, filtroConStock, filtroProducto, filtroCentro, pageSize, searchTerm, puedeVerGlobal, centroUsuario, errorSinCentro]);
  // Nota: NO incluir cargarLotes como dependencia para evitar re-renders innecesarios

  // Escuchar evento de limpieza de inventario para refrescar Lotes
  useEffect(() => {
    const handleInventarioLimpiado = (event) => {
      console.log('🧹 Inventario limpiado, refrescando Lotes...', event.detail);
      cargarLotes();
    };
    
    window.addEventListener('inventarioLimpiado', handleInventarioLimpiado);
    
    return () => {
      window.removeEventListener('inventarioLimpiado', handleInventarioLimpiado);
    };
  }, [cargarLotes]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // ISS-SEC FIX: Validar fecha_caducidad obligatoria en CREACIÓN y EDICIÓN
    // No se permiten lotes sin fecha de caducidad (usar 2099-12-31 para insumos sin vencimiento)
    if (!formData.fecha_caducidad) {
      toast.error('La fecha de caducidad es obligatoria. Para insumos sin caducidad, usar 2099-12-31');
      return;
    }

    // NÚMERO DE CONTRATO obligatorio para Farmacia/Admin
    if (puedeVerContrato && !editingLote && !formData.numero_contrato?.trim()) {
      toast.error('El número de contrato es obligatorio');
      return;
    }

    // FECHA DE ENTREGA obligatoria en creación
    if (!editingLote && !formData.fecha_fabricacion) {
      toast.error('La fecha de entrega es obligatoria');
      return;
    }

    // Validar que la fecha de caducidad no esté más de 8 años en el futuro
    const fechaCaducidad = new Date(formData.fecha_caducidad);
    const fechaActual = new Date();
    const fechaMaxima = new Date();
    fechaMaxima.setFullYear(fechaMaxima.getFullYear() + 8);
    
    if (fechaCaducidad > fechaMaxima) {
      const maxFechaStr = fechaMaxima.toLocaleDateString('es-MX');
      const caducidadStr = fechaCaducidad.toLocaleDateString('es-MX');
      toast.error(`Fecha de caducidad muy lejana (${caducidadStr}). Máximo 8 años desde hoy (${maxFechaStr}). Verifique el formato (DD/MM/AAAA).`);
      return;
    }
    
    // Validar cantidad del contrato (OPCIONAL - puede ser vacía/null)
    // Si se proporciona, debe ser un número no negativo
    let cantidadContrato = null;
    if (formData.cantidad_contrato !== '' && formData.cantidad_contrato !== null && formData.cantidad_contrato !== undefined) {
      cantidadContrato = parseInt(formData.cantidad_contrato, 10);
      if (isNaN(cantidadContrato) || cantidadContrato < 0) {
        toast.error('La cantidad del contrato debe ser un número no negativo');
        return;
      }
      if (cantidadContrato === 0) {
        cantidadContrato = null; // Tratar 0 como sin definir
      }
    }

    // cantidad_inicial: cantidad realmente recibida (puede ser parcial vs contrato)
    // Solo se valida al CREAR lotes nuevos. En edición, cantidad_inicial no se modifica.
    let cantidadInicial = null;
    if (!editingLote) {
      cantidadInicial = parseInt(formData.cantidad_inicial, 10);
      
      // Validación: cantidad debe ser un número válido
      if (isNaN(cantidadInicial)) {
        toast.error('La cantidad inicial debe ser un número válido');
        return;
      }
      
      // Validación: cantidad no puede ser negativa
      if (cantidadInicial < 0) {
        toast.error('La cantidad inicial no puede ser negativa');
        return;
      }
      
      // Validación: cantidad no puede ser cero para nuevos lotes
      if (cantidadInicial === 0) {
        toast.error('La cantidad inicial debe ser mayor a cero');
        return;
      }
      
      // Advertencia: cantidad_inicial supera cantidad_contrato (permitido pero se notifica)
      if (cantidadContrato !== null && cantidadInicial > cantidadContrato) {
        toast('⚠️ La cantidad inicial excede el contrato del lote. Se registrará como sobreentrega.', {
          icon: '⚠️',
          duration: 5000,
          style: { background: '#fef3cd', color: '#856404' }
        });
        // No bloquear - permitir la operación
      }
    }
    
    // ISS-INV-002: cantidad_contrato es opcional, puede ser null
    let cantContratoFinal = cantidadContrato;
    
    // Parsear precio si existe (campo real: precio_unitario)
    // Si no hay precio, usar 0 como default (requerido por backend)
    const precioUnitario = formData.precio_unitario ? parseFloat(formData.precio_unitario) : 0;
    if (formData.precio_unitario && (isNaN(precioUnitario) || precioUnitario < 0)) {
      toast.error('El precio unitario debe ser un número válido y no negativo');
      return;
    }
    
    // =====================================================================
    // ISS-SEC: Construir payload limpio según modo (crear vs editar)
    // NUNCA enviar cantidad_actual (read_only en backend)
    // NUNCA enviar cantidad_inicial en edición
    // =====================================================================
    const dataToSend = {};
    
    // Campos siempre enviados
    dataToSend.producto = formData.producto;
    dataToSend.numero_lote = formData.numero_lote;
    dataToSend.fecha_caducidad = formData.fecha_caducidad;
    dataToSend.precio_unitario = precioUnitario;
    
    // Campos opcionales (solo si tienen valor)
    if (formData.fecha_fabricacion) dataToSend.fecha_fabricacion = formData.fecha_fabricacion;
    if (formData.numero_contrato) dataToSend.numero_contrato = formData.numero_contrato;
    if (formData.marca) dataToSend.marca = formData.marca;
    if (formData.ubicacion) dataToSend.ubicacion = formData.ubicacion;
    // Enviar centro explícitamente: null = Farmacia Central (FK nullable en BD)
    // NUNCA omitir: backend necesita saber que es null, no que falta el campo
    dataToSend.centro = formData.centro || null;
    
    // ISS-FIX: SIEMPRE enviar cantidad_contrato al backend
    // El backend valida permisos y rechaza si no es farmacia/admin
    dataToSend.cantidad_contrato = cantContratoFinal;
    
    // ISS-INV-003: cantidad_contrato_global también enviado siempre (backend valida)
    if (formData.cantidad_contrato_global) {
      dataToSend.cantidad_contrato_global = parseInt(formData.cantidad_contrato_global) || null;
    }
    
    if (!editingLote) {
      // CREAR: incluir cantidad_inicial (backend calcula cantidad_actual = cantidad_inicial)
      dataToSend.cantidad_inicial = cantidadInicial;
    }
    // En edición: NO enviar cantidad_inicial ni cantidad_actual (blindado en backend)
    
    // Si no hay centro explícito y el usuario tiene uno asignado, usarlo
    if (!dataToSend.centro && centroUsuario && !puedeVerGlobal) {
      dataToSend.centro = centroUsuario;
    }
    
    // =====================================================================
    // ISS-SEC: Doble confirmación para crear/editar lotes
    // El backend exige confirmed=true para operaciones de escritura
    // =====================================================================
    const ejecutarGuardado = async () => {
      setSavingLote(true);
      try {
        let respData;
        if (editingLote) {
          // PATCH con confirmed=true (doble confirmación)
          const resp = await lotesAPI.update(editingLote.id, { ...dataToSend, confirmed: true });
          respData = resp.data || resp;
          toast.success('Lote actualizado correctamente');
        } else {
          const resp = await lotesAPI.create(dataToSend);
          respData = resp.data || resp;
          toast.success('Lote creado correctamente');
        }
        
        // ISS-INV-001: Mostrar alerta si se excedió el contrato del lote (sobreentrega)
        if (respData?.alerta_contrato_lote) {
          setTimeout(() => {
            toast(respData.alerta_contrato_lote, { icon: '⚠️', duration: 8000 });
          }, 300);
        }

        // ISS-INV-003: Mostrar alerta si se excedió el contrato global
        if (respData?.alerta_contrato_global) {
          setTimeout(() => {
            toast(respData.alerta_contrato_global, { icon: '⚠️', duration: 8000 });
          }, 500);
        }

        // AUTO-SUFIJO: Informar si el número de lote fue renombrado automáticamente
        if (!editingLote && respData?.numero_lote_auto_asignado) {
          setTimeout(() => {
            const { original, asignado } = respData.numero_lote_auto_asignado;
            toast(
              `El número "${original}" ya existía. El lote fue guardado como "${asignado}".`,
              { icon: 'ℹ️', duration: 10000 }
            );
          }, 800);
        }
        
        setShowModal(false);
        resetForm();
        cargarLotes();
      } catch (error) {
        // Extraer mensajes de error detallados del backend
        const respData = error.response?.data;
        let errorMsg = 'Error al guardar lote';
        
        // ISS-SEC: Manejar respuesta 409 (confirmación requerida)
        if (error.response?.status === 409 && respData?.code === 'CONFIRMATION_REQUIRED') {
          // El backend pide confirmación — reenviar con confirmed=true
          try {
            if (editingLote) {
              await lotesAPI.update(editingLote.id, { ...dataToSend, confirmed: true });
            } else {
              await lotesAPI.create({ ...dataToSend, confirmed: true });
            }
            toast.success(editingLote ? 'Lote actualizado correctamente' : 'Lote creado correctamente');
            setShowModal(false);
            resetForm();
            cargarLotes();
            return;
          } catch (retryError) {
            const retryData = retryError.response?.data;
            errorMsg = retryData?.error || retryData?.mensaje || 'Error al confirmar operación';
          }
        } else if (respData) {
          if (respData.detalles) {
            const detalles = respData.detalles;
            const mensajes = [];
            if (typeof detalles === 'object' && !Array.isArray(detalles)) {
              Object.entries(detalles).forEach(([campo, msgs]) => {
                const campoLabel = campo === '__all__' || campo === 'non_field_errors' ? '' : `${campo}: `;
                if (Array.isArray(msgs)) {
                  msgs.forEach(m => mensajes.push(`${campoLabel}${typeof m === 'object' ? m.message || JSON.stringify(m) : m}`));
                } else if (typeof msgs === 'string') {
                  mensajes.push(`${campoLabel}${msgs}`);
                } else if (typeof msgs === 'object' && msgs.message) {
                  mensajes.push(`${campoLabel}${msgs.message}`);
                }
              });
            } else if (Array.isArray(detalles)) {
              detalles.forEach(m => mensajes.push(typeof m === 'string' ? m : JSON.stringify(m)));
            }
            errorMsg = mensajes.length > 0 ? mensajes.join(' | ') : (respData.error || errorMsg);
          } else if (respData.numero_lote?.[0]) {
            errorMsg = respData.numero_lote[0];
          } else if (respData.error) {
            errorMsg = respData.error;
          } else if (respData.mensaje) {
            errorMsg = respData.mensaje;
          }
        }
        
        toast.error(errorMsg);
        // DEBUG: Log completo del error para diagnóstico
        console.error('Error al guardar lote:', error);
        console.error('Respuesta del servidor:', error.response?.data);
        console.error('Datos enviados:', dataToSend);
      } finally {
        setSavingLote(false);
      }
    };

    // ISS-SEC: Para edición, usar doble confirmación visual
    if (editingLote) {
      requestSaveConfirmation({
        title: 'Confirmar Actualización de Lote',
        message: `¿Está seguro de actualizar el lote ${editingLote.numero_lote}?`,
        warnings: [
          'Los cambios quedarán registrados en auditoría',
          'La cantidad inicial y cantidad actual NO se modifican desde aquí',
        ],
        itemInfo: {
          'Lote': editingLote.numero_lote,
          'Producto': editingLote.producto_nombre || 'N/A',
        },
        confirmText: 'Sí, Actualizar',
        cancelText: 'Cancelar',
        tone: 'warning',
        onConfirm: ejecutarGuardado,
      });
    } else {
      // Para creación, ejecutar directamente (ya se validó arriba)
      ejecutarGuardado();
    }
  };

  const handleEdit = async (lote) => {
    // Obtener datos más recientes del servidor para asegurar campos actualizados
    try {
      const response = await lotesAPI.getById(lote.id);
      const loteActualizado = response.data;
      
      setEditingLote(loteActualizado);
      
      // Obtener presentación del producto si está disponible
      const productoInfo = loteActualizado.producto_info || {};
      const presentacionProducto = productoInfo.presentacion || loteActualizado.presentacion || '';
      
      // Usar ultima_fecha_entrega (de parcialidades) o fecha_fabricacion (legacy)
      // IMPORTANTE: Asegurar formato YYYY-MM-DD para input type="date"
      const formatearFechaParaInput = (fecha) => {
        if (!fecha) return '';
        // Si ya está en formato YYYY-MM-DD, usar directamente
        if (typeof fecha === 'string' && /^\d{4}-\d{2}-\d{2}/.test(fecha)) {
          return fecha.substring(0, 10); // Tomar solo YYYY-MM-DD
        }
        // Si es otro formato, intentar convertir
        try {
          const d = new Date(fecha);
          if (!isNaN(d.getTime())) {
            return d.toISOString().split('T')[0];
          }
        } catch (e) {
          console.warn('Error parseando fecha:', fecha, e);
        }
        return '';
      };
      
      // DEBUG: Ver valores de fecha
      console.log('Lote actualizado:', {
        id: loteActualizado.id,
        fecha_fabricacion: loteActualizado.fecha_fabricacion,
        ultima_fecha_entrega: loteActualizado.ultima_fecha_entrega
      });
      
      const fechaEntrega = formatearFechaParaInput(loteActualizado.ultima_fecha_entrega) || 
                           formatearFechaParaInput(loteActualizado.fecha_fabricacion) || '';
      
      console.log('Fecha entrega formateada:', fechaEntrega);
      
      setFormData({
        producto: loteActualizado.producto,
        presentacion_producto: presentacionProducto,
        numero_lote: loteActualizado.numero_lote,
        fecha_fabricacion: fechaEntrega,
        fecha_caducidad: formatearFechaParaInput(loteActualizado.fecha_caducidad),
        cantidad_inicial: loteActualizado.cantidad_inicial,
        cantidad_contrato: loteActualizado.cantidad_contrato || '',
        cantidad_contrato_global: loteActualizado.cantidad_contrato_global || '',
        precio_unitario: loteActualizado.precio_unitario || loteActualizado.precio_compra || '',
        numero_contrato: loteActualizado.numero_contrato || '',
        marca: loteActualizado.marca || '',
        ubicacion: loteActualizado.ubicacion || '',
        centro: loteActualizado.centro || ''
      });
      setShowModal(true);
    } catch (error) {
      console.error('Error al obtener lote:', error);
      toast.error('Error al cargar datos del lote');
    }
  };

  // ISS-SEC: Función auxiliar para ejecutar eliminación de lote con confirmación
  const executeDeleteLote = async ({ confirmed, actionData }) => {
    const { id } = actionData;
    try {
      setActionLoading(id);
      await lotesAPI.delete(id, { confirmed });
      toast.success('Lote desactivado correctamente');
      cargarLotes();
    } catch (error) {
      const errorData = error.response?.data;
      let errorMsg = 'Error al eliminar lote';
      if (errorData?.razon) {
        errorMsg = `${errorData.error}: ${errorData.razon}`;
      } else if (errorData?.error) {
        errorMsg = errorData.error;
      }
      toast.error(errorMsg);
      throw error; // Re-lanzar para que el modal maneje el estado
    } finally {
      setActionLoading(null);
    }
  };

  // ISS-SEC: handleDelete ahora inicia el flujo de confirmación en 2 pasos
  const handleDelete = (id, lote) => {
    if (!puede.eliminar) {
      toast.error('No tiene permisos para eliminar lotes');
      return;
    }
    
    if (actionLoading === id) return; // Evitar múltiples clics
    
    // Solicitar confirmación en 2 pasos
    requestDeleteConfirmation({
      title: 'Confirmar Desactivación de Lote',
      message: `¿Está seguro de DESACTIVAR el lote?`,
      warnings: [
        'El lote quedará marcado como eliminado (soft delete)',
        'Los movimientos asociados se conservarán para auditoría',
        'Esta acción es reversible por un administrador'
      ],
      itemInfo: {
        'Número de Lote': lote?.numero_lote || id,
        'Producto': lote?.producto_nombre || lote?.producto_clave || 'N/A',
        'Stock Actual': lote?.cantidad_actual ?? 'N/A'
      },
      confirmText: 'Sí, Desactivar',
      cancelText: 'Cancelar',
      tone: 'warning', // warning porque es soft delete (reversible)
      onConfirm: executeDeleteLote,
      actionData: { id }
    });
  };

  const handleDocumentoModal = async (lote) => {
    setSelectedLoteDoc(lote);
    setShowDocModal(true);
    // Cargar documentos del lote
    try {
      const response = await lotesAPI.listarDocumentos(lote.id);
      setSelectedLoteDoc(prev => ({
        ...prev,
        documentos_cargados: response.data.documentos || []
      }));
    } catch (error) {
      console.error('Error al cargar documentos:', error);
    }
  };

  // =========================================================================
  // PARCIALIDADES - Historial de entregas parciales
  // =========================================================================
  const handleParcialidadesModal = async (lote) => {
    setSelectedLoteParcialidades(lote);
    setShowParcialidadesModal(true);
    setNuevaParcialidad({ fecha_entrega: '', cantidad: '', notas: '' });
    
    // Cargar parcialidades del lote
    try {
      setLoadingParcialidades(true);
      const response = await lotesAPI.listarParcialidades(lote.id);
      setParcialidadesData(response.data);
    } catch (error) {
      console.error('Error al cargar parcialidades:', error);
      toast.error('Error al cargar historial de entregas');
      setParcialidadesData({ parcialidades: [], resumen: {}, contrato_lote: {} });
    } finally {
      setLoadingParcialidades(false);
    }
  };

  // ISS-SEC: Paso 1 - Solicitar confirmación antes de agregar entrega
  const solicitarConfirmacionEntrega = (forceOverride = false) => {
    if (!nuevaParcialidad.fecha_entrega || !nuevaParcialidad.cantidad) {
      toast.error('Fecha y cantidad son obligatorios');
      return;
    }
    
    const cantidad = parseInt(nuevaParcialidad.cantidad, 10);
    if (isNaN(cantidad) || cantidad <= 0) {
      toast.error('La cantidad debe ser un número positivo');
      return;
    }
    
    // Si requiere override, validar motivo
    if (forceOverride && (!motivoOverride || motivoOverride.trim().length < 10)) {
      toast.error('Debe proporcionar un motivo detallado (mínimo 10 caracteres)');
      return;
    }
    
    // Mostrar modal de confirmación
    setConfirmarEntrega({ show: true, forceOverride });
  };

  // ISS-SEC: Paso 2 - Ejecutar registro de entrega después de confirmación
  const handleAgregarParcialidad = async (forceOverride = false) => {
    // Cerrar modal de confirmación
    setConfirmarEntrega({ show: false, forceOverride: false });
    
    const cantidad = parseInt(nuevaParcialidad.cantidad, 10);
    
    try {
      setLoadingParcialidades(true);
      
      const payload = {
        fecha_entrega: nuevaParcialidad.fecha_entrega,
        cantidad: cantidad,
        notas: nuevaParcialidad.notas || 'Entrega manual'
      };
      
      // Si es override, agregar campos adicionales
      if (forceOverride) {
        payload.override = true;
        payload.motivo_override = motivoOverride.trim();
      }
      
      const response = await lotesAPI.agregarParcialidad(selectedLoteParcialidades.id, payload);
      
      // Limpiar estado de override
      setRequiereOverride(false);
      setMotivoOverride('');
      setInfoContratoCumplido(null);
      
      // Mostrar advertencias si hay sobre-entrega
      if (response.data.advertencia) {
        toast(response.data.advertencia, { icon: '⚠️', duration: 6000 });
      }
      
      // Mostrar info si se completó el contrato
      if (response.data.info) {
        toast.success(response.data.info, { duration: 5000 });
      }
      
      // Mostrar estado del contrato
      const estadoLote = response.data.estado_contrato?.lote?.estado;
      const estadoGlobal = response.data.estado_contrato?.global?.estado;
      
      if (estadoLote === 'SOBREENTREGA') {
        toast('⚠️ Sobre-entrega registrada y auditada', { duration: 5000 });
      } else if (estadoLote === 'CUMPLIDO' && estadoGlobal === 'CUMPLIDO') {
        toast.success('¡Entrega registrada! Contratos de lote y global CUMPLIDOS');
      } else if (estadoLote === 'CUMPLIDO') {
        toast.success('¡Entrega registrada! Contrato de lote CUMPLIDO');
      } else if (estadoGlobal === 'CUMPLIDO') {
        toast.success('¡Entrega registrada! Contrato global CUMPLIDO');
      } else {
        toast.success('Entrega registrada correctamente');
      }
      
      // Recargar parcialidades
      const reloadResponse = await lotesAPI.listarParcialidades(selectedLoteParcialidades.id);
      setParcialidadesData(reloadResponse.data);
      setNuevaParcialidad({ fecha_entrega: '', cantidad: '', notas: '' });
      
      // Recargar lotes para actualizar métricas en tabla
      cargarLotes();
    } catch (error) {
      console.error('Error al agregar parcialidad:', error);
      
      // Detectar error 409: contrato cumplido, requiere override
      if (error.response?.status === 409 && error.response?.data?.requiere_override) {
        setRequiereOverride(true);
        setInfoContratoCumplido({
          estado: error.response.data.estado_actual,
          total_entregado: error.response.data.total_entregado,
          cantidad_contrato: error.response.data.cantidad_contrato,
          mensaje: error.response.data.mensaje
        });
        toast('⚠️ Contrato cumplido - Se requiere autorización', { icon: '🔒', duration: 5000 });
      } else {
        const errorMsg = error.response?.data?.mensaje || error.response?.data?.error || 'Error al registrar entrega';
        toast.error(typeof errorMsg === 'object' ? JSON.stringify(errorMsg) : errorMsg);
      }
    } finally {
      setLoadingParcialidades(false);
    }
  };

  // ISS-SEC: Eliminar parcialidad con doble confirmación
  const handleEliminarParcialidad = async (parcialidad) => {
    requestDeleteConfirmation({
      title: 'Eliminar Entrega',
      message: `¿Está seguro de eliminar esta entrega de ${parcialidad.cantidad?.toLocaleString()} unidades?`,
      warnings: [
        'Esta acción restará del inventario',
        `Fecha de entrega: ${new Date(parcialidad.fecha_entrega).toLocaleDateString('es-MX')}`,
        parcialidad.notas ? `Notas: ${parcialidad.notas}` : null,
      ].filter(Boolean),
      itemInfo: {
        nombre: `Entrega #${parcialidad.id}`,
        descripcion: `${parcialidad.cantidad?.toLocaleString()} unidades del lote ${selectedLoteParcialidades?.numero_lote}`,
      },
      onConfirm: async () => {
        try {
          setLoadingParcialidades(true);
          await lotesAPI.eliminarParcialidad(selectedLoteParcialidades.id, parcialidad.id);
          toast.success('Entrega eliminada correctamente');
          
          // Recargar parcialidades
          const response = await lotesAPI.listarParcialidades(selectedLoteParcialidades.id);
          setParcialidadesData(response.data);
          
          // Recargar lotes para actualizar métricas en tabla
          cargarLotes();
        } catch (error) {
          console.error('Error al eliminar parcialidad:', error);
          const errorMsg = error.response?.data?.error || 'Error al eliminar entrega';
          toast.error(errorMsg);
          throw error; // Re-lanzar para que el modal maneje el estado
        } finally {
          setLoadingParcialidades(false);
        }
      },
    });
  };

  // Exportar historial de entregas a PDF o Excel
  const handleExportarEntregas = async (formato) => {
    if (!selectedLoteParcialidades?.id) return;
    
    try {
      setExportingEntregas(formato);
      
      const response = formato === 'pdf' 
        ? await lotesAPI.exportarEntregasPdf(selectedLoteParcialidades.id)
        : await lotesAPI.exportarEntregasExcel(selectedLoteParcialidades.id);
      
      // Crear URL temporal y descargar
      const blob = new Blob([response.data], { 
        type: formato === 'pdf' 
          ? 'application/pdf' 
          : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Entregas_${selectedLoteParcialidades.numero_lote}_${new Date().toISOString().split('T')[0]}.${formato === 'pdf' ? 'pdf' : 'xlsx'}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success(`Reporte ${formato.toUpperCase()} descargado correctamente`);
    } catch (error) {
      console.error(`Error exportando entregas a ${formato}:`, error);
      toast.error(`Error al exportar a ${formato.toUpperCase()}`);
    } finally {
      setExportingEntregas(null);
    }
  };

  const handleSubirDocumento = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    if (!puede.subirDocumento) {
      toast.error('No tiene permisos para subir documentos');
      return;
    }
    
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast.error('Solo se permiten archivos PDF');
      return;
    }
    
    if (file.size > 10 * 1024 * 1024) {
      toast.error('El archivo no puede superar los 10MB');
      return;
    }
    
    const formData = new FormData();
    formData.append('documento', file);
    formData.append('tipo_documento', 'contrato'); // Tipo por defecto
    
    try {
      setActionLoading(selectedLoteDoc.id);
      await lotesAPI.subirDocumento(selectedLoteDoc.id, formData);
      toast.success('Documento subido correctamente');
      // Recargar documentos del modal
      const response = await lotesAPI.listarDocumentos(selectedLoteDoc.id);
      setSelectedLoteDoc(prev => ({
        ...prev,
        documentos_cargados: response.data.documentos || [],
        tiene_documentos: true
      }));
      cargarLotes();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al subir documento');
    } finally {
      setActionLoading(null);
      e.target.value = ''; // Limpiar input
    }
  };

  // ISS-SEC: Función auxiliar para ejecutar eliminación de documento con confirmación
  const executeDeleteDocumento = async ({ confirmed, actionData }) => {
    const { docId, loteId } = actionData;
    try {
      setActionLoading(loteId);
      await lotesAPI.eliminarDocumento(loteId, docId, { confirmed });
      toast.success('Documento eliminado');
      // Recargar documentos del modal
      const response = await lotesAPI.listarDocumentos(loteId);
      setSelectedLoteDoc(prev => ({
        ...prev,
        documentos_cargados: response.data.documentos || [],
        tiene_documentos: (response.data.documentos || []).length > 0
      }));
      cargarLotes();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al eliminar documento');
      throw error;
    } finally {
      setActionLoading(null);
    }
  };

  // ISS-SEC: handleEliminarDocumento ahora usa confirmación en 2 pasos
  const handleEliminarDocumento = (docId) => {
    if (!puede.subirDocumento) {
      toast.error('No tiene permisos para eliminar documentos');
      return;
    }
    
    const doc = selectedLoteDoc?.documentos_cargados?.find(d => d.id === docId);
    
    requestDeleteConfirmation({
      title: 'Confirmar Eliminación de Documento',
      message: '¿Está seguro de eliminar este documento?',
      warnings: [
        'El archivo será eliminado permanentemente',
        'Esta acción no se puede deshacer'
      ],
      itemInfo: {
        'Tipo': doc?.tipo_documento || 'Documento',
        'Archivo': doc?.nombre_archivo || docId,
        'Lote': selectedLoteDoc?.numero_lote || 'N/A'
      },
      confirmText: 'Sí, Eliminar',
      cancelText: 'Cancelar',
      tone: 'danger',
      onConfirm: executeDeleteDocumento,
      actionData: { docId, loteId: selectedLoteDoc.id }
    });
  };

  const resetForm = () => {
    setFormData({
      producto: '',
      presentacion_producto: '',
      numero_lote: '',
      fecha_fabricacion: '',
      fecha_caducidad: '',
      cantidad_inicial: '',
      cantidad_contrato: '',  // ISS-INV-001: Cantidad del contrato
      cantidad_contrato_global: '',
      precio_unitario: '',
      numero_contrato: '',
      marca: '',
      ubicacion: '',
      centro: ''
    });
    setEditingLote(null);
    setCcgAutoCompletado(false);
    setCargandoCCG(false);
  };

  const limpiarFiltros = () => {
    setSearchTerm('');
    setFiltroProducto('');
    setFiltroCaducidad('');
    setFiltroConStock('');
    // ISS-FIX: CENTRO/MEDICO mantienen filtro activo=true al limpiar
    setFiltroActivo(puedeVerGlobal ? '' : 'true');
    // Si no puede ver global, mantener filtro de su centro
    if (puedeVerGlobal) {
      setFiltroCentro('');
    } else {
      setFiltroCentro(centroUsuario?.toString() || '');
    }
    setCurrentPage(1);
  };

  const handleExportar = async () => {
    if (!puede.exportar) {
      toast.error('No tiene permisos para exportar');
      return;
    }
    
    if (exportLoading) return; // Evitar múltiples clics
    
    try {
      setExportLoading(true);
      // Enviar TODOS los filtros activos para que el Excel coincida con la vista
      const params = {};
      if (searchTerm) params.search = searchTerm;
      if (filtroProducto) params.producto = filtroProducto;
      if (filtroCaducidad) params.caducidad = filtroCaducidad;
      if (filtroConStock) params.con_stock = filtroConStock;
      if (filtroActivo) params.activo = filtroActivo;
      // ISS-FIX: Usar misma lógica de centro que cargarLotes
      // Admin/farmacia: por defecto solo exportar Farmacia Central
      // Para exportar centros, usar Reportes > Inventario > elegir centro
      if (!puedeVerGlobal) {
        params.centro = centroUsuario?.toString() || filtroCentro || '';
      } else if (filtroCentro === 'todos') {
        // Sin filtro = exportar todo
      } else if (filtroCentro) {
        params.centro = filtroCentro;
      } else {
        params.centro = 'central'; // Default: solo Farmacia Central
      }
      
      const response = await lotesAPI.exportar(params);
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `lotes_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      // Liberar recursos del ObjectURL para evitar memory leaks
      window.URL.revokeObjectURL(url);
      
      toast.success('Lotes exportados correctamente');
    } catch (error) {
      toast.error('Error al exportar lotes');
    } finally {
      setExportLoading(false);
    }
  };

  // Handler para exportar a PDF (reporte de inventario)
  const handleExportarPdf = async () => {
    if (!puede.exportar) {
      toast.error('No tiene permisos para exportar');
      return;
    }
    
    if (exportPdfLoading) return;

    const win = abrirPdfEnNavegador(); // Pre-abrir pestaña (preserva user-gesture)
    if (!win) return;
    
    try {
      setExportPdfLoading(true);
      // Enviar TODOS los filtros activos para que el PDF coincida con la vista
      const params = {};
      if (searchTerm) params.search = searchTerm;
      if (filtroProducto) params.producto = filtroProducto;
      if (filtroCaducidad) params.caducidad = filtroCaducidad;
      if (filtroConStock) params.con_stock = filtroConStock;
      if (filtroActivo) params.activo = filtroActivo;
      // ISS-FIX: Usar misma lógica de centro que cargarLotes
      if (!puedeVerGlobal) {
        params.centro = centroUsuario?.toString() || filtroCentro || '';
      } else if (filtroCentro === 'todos') {
        // Sin filtro = exportar todo
      } else if (filtroCentro) {
        params.centro = filtroCentro;
      } else {
        params.centro = 'central';
      }
      
      const response = await lotesAPI.exportarPdf(params);
      
      if (abrirPdfEnNavegador(response.data, win)) {
        toast.success('PDF de inventario generado correctamente');
      }
    } catch (error) {
      toast.error('Error al generar PDF');
    } finally {
      setExportPdfLoading(false);
    }
  };

  // Handler para descargar plantilla de importación
  const handleDescargarPlantilla = async () => {
    try {
      const response = await lotesAPI.plantilla();
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'Plantilla_Lotes.xlsx');
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

const handleImportar = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  
  // Validar extensión
  const extension = file.name.split('.').pop()?.toLowerCase();
  if (!['xlsx', 'xls'].includes(extension)) {
    toast.error('Solo se permiten archivos Excel (.xlsx, .xls)');
    e.target.value = '';
    return;
  }
  
  // Validar tamaño (máx 10MB)
  const maxSize = 10 * 1024 * 1024;
  if (file.size > maxSize) {
    toast.error(`El archivo excede el tamaño máximo de 10MB (${(file.size / 1024 / 1024).toFixed(2)}MB)`);
    e.target.value = '';
    return;
  }
  
  if (!puede.importar) {
    toast.error('No tiene permisos para importar');
    e.target.value = '';
    return;
  }
  
  // Validar que usuarios de centro tengan centro asignado
  if (!puedeVerGlobal && !centroUsuario) {
    toast.error('No tiene un centro asignado. No puede importar lotes.');
    e.target.value = '';
    return;
  }
  
  const formData = new FormData();
  formData.append('file', file);
  // Incluir centro del usuario para trazabilidad si no tiene permisos globales
  if (!puedeVerGlobal && centroUsuario) {
    formData.append('centro', centroUsuario);
  }

  // Función para traducir errores técnicos a mensajes amigables (fuera del try para usar en catch)
  const traducirError = (errorStr) => {
    if (!errorStr) return 'Error desconocido';
    const str = String(errorStr);
    
    // Errores de fecha de caducidad
    if (str.includes('fecha de caducidad debe ser posterior a la fecha de fabricación')) {
      return '⚠️ La fecha de caducidad es anterior a la fabricación (dato incorrecto en Excel)';
    }
    if (str.includes('No se puede registrar un lote ya vencido') || str.includes('lote ya vencido')) {
      return '⚠️ Lote ya vencido - no se puede registrar inventario caducado';
    }
    if (str.includes('Fecha de caducidad invalida')) {
      return '⚠️ Formato de fecha inválido (use YYYY-MM-DD o DD/MM/YYYY)';
    }
    
    // Errores de producto y validación clave+nombre
    if (str.includes('Producto no encontrado') || str.includes('no encontrada en catálogo') || str.includes('no encontrada en el catálogo')) {
      return '⚠️ Producto no existe en el catálogo - verifique la clave';
    }
    if (str.includes('Producto y numero de lote son obligatorios')) {
      return '⚠️ Faltan datos obligatorios (Producto o Número de Lote)';
    }
    if (str.includes('DISCREPANCIA')) {
      return '⚠️ Clave y nombre no coinciden - verifique que ambos correspondan al mismo producto';
    }
    if (str.includes('Clave de producto es OBLIGATORIA')) {
      return '⚠️ Falta la clave del producto (columna obligatoria)';
    }
    if (str.includes('Nombre de producto es OBLIGATORIO')) {
      return '⚠️ Falta el nombre del producto (columna obligatoria)';
    }
    
    // Errores de cantidad
    if (str.includes('Cantidades invalidas')) {
      return '⚠️ Cantidad inválida - debe ser un número positivo';
    }
    if (str.includes('Cantidad Inicial es 0') || str.includes('Cantidad Inicial debe ser mayor a 0')) {
      return '⚠️ Cantidad recibida es 0 - importe cuando llegue la primera entrega';
    }
    
    // Errores de columnas faltantes
    if (str.includes('Columnas faltantes')) {
      return '⚠️ El archivo no tiene las columnas requeridas - descargue la plantilla actualizada';
    }
    
    return str;
  };
  
  try {
    setImportLoading(true);
    const response = await lotesAPI.importar(formData);
    const resumen = response.data?.resumen || response.data || {};
    const errores = response.data?.errores || [];

    // Mostrar resultado principal
    const totalExitos = resumen.creados || resumen.registros_exitosos || 0;
    if (totalExitos > 0) {
      toast.success(
        `✅ Importación completada: ${totalExitos} lotes importados correctamente`,
        { duration: 4000 }
      );
    } else if (!errores.length) {
      toast('Importación completada. No se crearon ni actualizaron lotes.', { icon: 'ℹ️', duration: 4000 });
    }
    
    // ISS-FIX: Mostrar nota sobre filas de centros omitidas
    if (resumen.omitidos_centro > 0) {
      toast(
        `ℹ️ ${resumen.omitidos_centro} fila(s) omitida(s) porque pertenecen a centros penitenciarios. Solo se importan lotes de Farmacia Central.`,
        { icon: '🏥', duration: 6000 }
      );
    }
    
    // ISS-IMPORT-CONSOLIDATION: Mostrar nota sobre filas consolidadas (parcialidades)
    if (resumen.consolidados_archivo > 0) {
      toast(
        `📦 ${resumen.consolidados_archivo} fila(s) consolidada(s) automáticamente (parcialidades con mismo lote+producto+caducidad se sumaron).`,
        { icon: '🔗', duration: 6000 }
      );
    }
    
    if (errores.length) {
      console.warn('Errores en importación de lotes:', errores);
      
      // Mostrar alerta general si hay errores (persistente hasta cerrar manualmente)
      toast(
        (t) => (
          <div className="flex items-start gap-2">
            <span className="flex-1">⚠️ {errores.length} fila(s) no se importaron por datos inválidos en el Excel. Corrija y vuelva a importar.</span>
            <button
              onClick={() => toast.dismiss(t.id)}
              className="ml-2 text-gray-500 hover:text-gray-700 font-bold text-lg leading-none"
              aria-label="Cerrar"
            >
              ×
            </button>
          </div>
        ),
        { 
          icon: '📋', 
          duration: Infinity,
        }
      );
      
      // Mostrar detalles de los primeros 5 errores (persistentes con botón de cerrar)
      const primeros = errores.slice(0, 5);
      primeros.forEach((err) => {
        const fila = err.fila || '?';
        const errorMsg = traducirError(err.error || err.mensaje);
        toast.error(
          (t) => (
            <div className="flex items-start gap-2">
              <span className="flex-1">Fila {fila}: {errorMsg}</span>
              <button
                onClick={() => toast.dismiss(t.id)}
                className="ml-2 text-gray-500 hover:text-gray-700 font-bold text-lg leading-none"
                aria-label="Cerrar"
              >
                ×
              </button>
            </div>
          ),
          { 
            duration: Infinity,
          }
        );
      });
      
      if (errores.length > 5) {
        toast(
          (t) => (
            <div className="flex items-start gap-2">
              <span className="flex-1">📝 Hay {errores.length - 5} errores más. Ver consola (F12) para detalles completos.</span>
              <button
                onClick={() => toast.dismiss(t.id)}
                className="ml-2 text-gray-500 hover:text-gray-700 font-bold text-lg leading-none"
                aria-label="Cerrar"
              >
                ×
              </button>
            </div>
          ),
          { 
            icon: 'ℹ️', 
            duration: Infinity,
          }
        );
      }
    }
    
    setShowImportModal(false);
    cargarLotes();
  } catch (error) {
    const data = error.response?.data;
    if (data) {
      // Si el servidor devolvió errores detallados (resultado de importación fallida)
      const errores = data.errores || [];
      const errorMsg = data.error || data.mensaje || 'Error al importar lotes';
      toast.error(errorMsg, { duration: 6000 });
      
      // Mostrar detalles de los primeros errores si existen
      if (errores.length > 0) {
        const primeros = errores.slice(0, 5);
        primeros.forEach((err) => {
          const fila = err.fila || '?';
          const errorDetalle = traducirError(err.error || err.mensaje);
          toast.error(
            (t) => (
              <div className="flex items-start gap-2">
                <span className="flex-1">Fila {fila}: {errorDetalle}</span>
                <button
                  onClick={() => toast.dismiss(t.id)}
                  className="ml-2 text-gray-500 hover:text-gray-700 font-bold text-lg leading-none"
                  aria-label="Cerrar"
                >
                  ×
                </button>
              </div>
            ),
            { duration: Infinity }
          );
        });
        if (errores.length > 5) {
          toast(`📝 Hay ${errores.length - 5} errores más. Ver consola (F12) para detalles.`, { icon: 'ℹ️', duration: 8000 });
        }
        console.warn('Errores en importación de lotes:', errores);
      }
    } else {
      toast.error('Error de conexión al importar lotes. Verifique su conexión a internet.');
    }
  } finally {
    setImportLoading(false);
    e.target.value = '';
    }
  };

  const getAlertaClass = (alerta) => {
    const classes = {
      vencido: 'bg-gradient-to-r from-red-500 to-red-600 text-white font-bold shadow-sm ring-1 ring-red-600/20',
      critico: 'bg-gradient-to-r from-orange-400 to-orange-500 text-white font-bold shadow-sm ring-1 ring-orange-500/20',
      proximo: 'bg-gradient-to-r from-amber-300 to-yellow-400 text-amber-900 font-semibold shadow-sm ring-1 ring-yellow-500/20',
      normal: 'bg-gradient-to-r from-emerald-400 to-green-500 text-white font-medium shadow-sm ring-1 ring-green-500/20'
    };
    return classes[alerta] || 'bg-gray-100 text-gray-800';
  };

  const getAlertaIcon = (alerta) => {
    if (alerta === 'vencido') {
      return <FaExclamationTriangle className="inline mr-1 animate-pulse" />;
    }
    if (alerta === 'critico') {
      return <FaExclamationTriangle className="inline mr-1" />;
    }
    return null;
  };

  const filtrosActivos = [
    searchTerm,
    filtroProducto,
    filtroCaducidad,
    filtroConStock,
    filtroActivo
  ].filter(Boolean).length;

  const headerActions = (
    <div className="flex flex-wrap gap-3">
      {puede.exportar && (
        <button
          type="button"
          onClick={handleExportar}
          disabled={exportLoading}
          className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-50 disabled:cursor-not-allowed bg-theme-gradient"
        >
          {exportLoading ? (
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
          ) : (
            <FaDownload />
          )}
          {exportLoading ? 'Exportando...' : 'Exportar'}
        </button>
      )}
      {puede.importar && (
        <>
          {/* Botón Importar */}
          <button
            type="button"
            onClick={() => setShowImportModal(true)}
            disabled={importLoading}
            className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-50 disabled:cursor-not-allowed bg-theme-gradient"
          >
            {importLoading ? (
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
            ) : (
              <FaFileUpload />
            )}
            {importLoading ? 'Importando...' : 'Importar'}
          </button>
          
          {/* Botón Plantilla */}
          <button
            type="button"
            onClick={handleDescargarPlantilla}
            className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-theme-primary bg-white/90 hover:bg-white transition"
            title="Descargar plantilla Excel para importar lotes"
          >
            <FaDownload />
            Plantilla
          </button>
        </>
      )}
      {puede.crear && (
        <button
          type="button"
          onClick={() => setShowModal(true)}
          disabled={savingLote}
          className="flex items-center gap-2 rounded-full bg-white/90 px-4 py-2 text-sm font-bold hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed text-theme-primary"
        >
          <FaPlus /> Nuevo Lote
        </button>
      )}
    </div>
  );

  // Mostrar error si el usuario no tiene centro asignado
  if (errorSinCentro) {
    return (
      <div className="p-6 space-y-6">
        <PageHeader
          icon={FaWarehouse}
          title="Gestión de Lotes"
          subtitle="Error de configuración"
        />
        <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
            <FaExclamationTriangle className="w-8 h-8 text-red-500" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900">Centro no asignado</h2>
          <p className="text-gray-600 text-center max-w-md">
            Tu cuenta no tiene un centro penitenciario asignado. 
            Contacta al administrador para que configure tu perfil correctamente.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        icon={FaWarehouse}
        title="Gestión de Lotes"
        subtitle={
          searchTerm 
            ? `🔍 ${totalLotes} resultado${totalLotes !== 1 ? 's' : ''} para "${searchTerm}" | Página ${currentPage} de ${totalPages}`
            : `Total: ${totalLotes} lotes | Página ${currentPage} de ${totalPages}`
        }
        badge={filtrosActivos ? `${filtrosActivos} filtros activos` : null}
        actions={headerActions}
      />

      {/* Indicador de centro forzado para usuarios sin permisos globales */}
      {!puedeVerGlobal && centroUsuario && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-2">
          <span className="text-blue-600 font-medium">📍 Mostrando lotes de tu centro asignado</span>
        </div>
      )}

      {/* Botón toggle filtros */}
      <div className="mb-4 flex justify-end">
        <button
          type="button"
          onClick={() => setShowFiltersMenu(!showFiltersMenu)}
          aria-expanded={showFiltersMenu}
          aria-haspopup="true"
          className="flex items-center gap-2 rounded-full border border-gray-200 bg-white/90 px-4 py-2 text-sm font-semibold text-gray-700 shadow-sm transition hover:bg-white"
        >
          <FaFilter className="text-theme-primary" />
          {showFiltersMenu ? 'Ocultar filtros' : 'Mostrar filtros'}
          <FaChevronDown className={`transition ${showFiltersMenu ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Panel de filtros colapsable */}
      {showFiltersMenu && (
        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
          <div
            className="flex items-center gap-3 px-5 py-3 border-b-[3px] border-theme-primary bg-gray-50"
          >
            <div className="bg-white p-2 rounded-lg">
              <FaFilter className="text-theme-primary" />
            </div>
            <div>
              <p className="text-sm font-semibold text-theme-primary-hover">Filtros avanzados</p>
              <p className="text-xs text-gray-500">Aplique criterios sin ocupar espacio en pantalla</p>
            </div>
          </div>

          <div className="space-y-3 px-5 py-3">
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-6">
              <div className="lg:col-span-2">
                <label className="text-xs font-semibold text-theme-primary-hover">
                  Búsqueda Rápida
                  <span className="ml-1 text-xs font-normal text-gray-500">(Clave, Lote, Nombre)</span>
                </label>
                <div
                  className="mt-1 flex items-center rounded-lg border px-3 py-2 focus-within:ring-2 border-theme-primary focus-within:border-theme-primary-hover transition-all"
                >
                  <FaFilter className="mr-2 text-theme-primary" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full border-none bg-transparent text-sm focus:outline-none"
                    placeholder="Ej: 6994, KETOCONAZOL, LOT-2026..."
                  />
                  {searchTerm && (
                    <button
                      onClick={() => setSearchTerm('')}
                      className="ml-2 text-gray-400 hover:text-gray-600 transition-colors"
                      title="Limpiar búsqueda"
                    >
                      <FaTimes size={14} />
                    </button>
                  )}
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold text-theme-primary-hover">Producto</label>
                <select
                  value={filtroProducto}
                  onChange={(e) => setFiltroProducto(e.target.value)}
                  className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 border-theme-primary"
                >
                  <option value="">Todos los productos</option>
                  {productos.map(p => (
                    <option key={p.id} value={p.id}>
                      {p.clave} - {p.nombre?.substring(0, 30)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-theme-primary-hover">Caducidad</label>
                <select
                  value={filtroCaducidad}
                  onChange={(e) => setFiltroCaducidad(e.target.value)}
                  className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 border-theme-primary"
                >
                  {nivelCaducidad.map(n => (
                    <option key={n.value} value={n.value}>{n.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-theme-primary-hover">Inventario</label>
                <select
                  value={filtroConStock}
                  onChange={(e) => setFiltroConStock(e.target.value)}
                  className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 border-theme-primary"
                >
                  <option value="">Todos</option>
                  <option value="con_stock">Con Inventario</option>
                  <option value="sin_stock">Sin Inventario</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-theme-primary-hover">Estado</label>
                <select
                  value={filtroActivo}
                  onChange={(e) => setFiltroActivo(e.target.value)}
                  className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 border-theme-primary"
                >
                  <option value="">Todos</option>
                  <option value="true">Activos</option>
                  <option value="false">Inactivos</option>
                </select>
              </div>
              {/* Selector de Centro - solo para admin/farmacia/vista */}
              {puedeVerGlobal && (
                <div>
                  <label className="text-xs font-semibold text-theme-primary-hover">Centro</label>
                  <select
                    value={filtroCentro}
                    onChange={(e) => setFiltroCentro(e.target.value)}
                    className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 border-theme-primary"
                  >
                    <option value="">Almacén Central</option>
                    <option value="todos">Todos (consolidado)</option>
                    {centros.map(c => (
                      <option key={c.id} value={c.id}>
                        {c.nombre}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="flex items-end">
                <button
                  type="button"
                  onClick={limpiarFiltros}
                  className="w-full rounded-lg border px-3 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-50"
                >
                  Limpiar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Indicador de búsqueda activa */}
      {searchTerm && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-blue-600 font-medium">
              🔍 Buscando: "{searchTerm}"
            </span>
            <span className="text-blue-500 text-sm">
              ({totalLotes} resultado{totalLotes !== 1 ? 's' : ''})
            </span>
          </div>
          <button
            onClick={() => setSearchTerm('')}
            className="text-blue-600 hover:text-blue-800 font-medium text-sm underline"
          >
            Limpiar búsqueda
          </button>
        </div>
      )}

      {/* Contenedor Tabla + Paginación */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
        {/* Tabla */}
        <div className="w-full overflow-x-auto">
          <table className="w-full min-w-[900px] divide-y divide-gray-200 table-fixed">
            <colgroup>
              <col className="w-10" /> {/* # */}
              <col className="w-32" /> {/* Producto */}
              <col className="w-24" /> {/* Lote */}
              <col className="w-24" /> {/* Caducidad */}
              <col className="w-16" /> {/* Alerta */}
              <col className="w-32" /> {/* Marca / Lab */}
              <col className="w-24" /> {/* Inventario */}
              <col className="w-24" /> {/* Acciones */}
            </colgroup>
            <thead className="bg-theme-gradient sticky top-0 z-10">
            <tr>
              {['#', 'Producto', 'Lote', 'Caducidad', 'Alerta', 'Marca / Lab', 'Inventario', 'Acciones'].map((col) => (
                <th key={col} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan="8" className="p-0">
                    <LotesSkeleton />
                  </td>
                </tr>
              ) : lotes.length === 0 ? (
                <tr>
                  <td colSpan="8" className="text-center py-12">
                    {searchTerm ? (
                      <div className="space-y-3">
                        <div className="text-gray-600 text-lg">
                          🔍 No se encontraron resultados para "<span className="font-semibold text-gray-800">{searchTerm}</span>"
                        </div>
                        <div className="text-sm text-gray-500">
                          La búsqueda incluye: número de lote, clave del producto y nombre del producto
                        </div>
                        <button
                          onClick={() => setSearchTerm('')}
                          className="mt-3 text-sm text-theme-primary hover:text-theme-primary-hover font-medium underline"
                        >
                          Limpiar búsqueda
                        </button>
                      </div>
                    ) : (
                      <div className="text-gray-500">
                        No hay lotes registrados
                      </div>
                    )}
                  </td>
                </tr>
              ) : (
                lotes.map((lote, index) => (
                  <tr key={lote.id} className={`transition ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-gray-100`}>
                    <td className="px-4 py-3 text-sm font-semibold text-gray-500">
                      {(currentPage - 1) * pageSize + index + 1}
                    </td>
                    <td className="px-3 py-2 text-sm">
                      <div className="font-semibold text-gray-800 text-xs">{lote.producto_clave}</div>
                      <div className="text-gray-500 text-xs truncate max-w-[120px]" title={lote.producto_nombre}>
                        {lote.producto_nombre?.substring(0, 20)}{lote.producto_nombre?.length > 20 ? '...' : ''}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-xs font-mono font-bold text-gray-800">
                      {lote.numero_lote}
                    </td>
                    <td className="px-3 py-2 text-xs">
                      <div>{formatFecha(lote.fecha_caducidad)}</div>
                      <div className="text-gray-500">{lote.dias_para_caducar}d</div>
                    </td>
                    <td className="px-3 py-2">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-full ${getAlertaClass(lote.alerta_caducidad)}`}>
                        {getAlertaIcon(lote.alerta_caducidad)}
                        <span>
                          {lote.alerta_caducidad === 'vencido' ? '⛔ Vencido' :
                           lote.alerta_caducidad === 'critico' ? '🔥 <90d' :
                           lote.alerta_caducidad === 'proximo' ? '⏰ <180d' : '✓ OK'}
                        </span>
                      </span>
                    </td>
                    {/* Marca / Laboratorio */}
                    <td className="px-3 py-2 text-xs">
                      {lote.marca ? (
                        <span className="text-gray-700 truncate max-w-[120px]" title={lote.marca}>
                          {lote.marca.length > 20 ? lote.marca.substring(0, 20) + '...' : lote.marca}
                        </span>
                      ) : (
                        <span className="text-gray-400 italic">Sin marca</span>
                      )}
                    </td>
                    {/* ISS-INV-003: Columna de Inventario - Diseño limpio con tooltip */}
                    <td className="px-4 py-3 text-sm">
                      {/* Inventario actual del lote */}
                      <div className="flex items-baseline gap-1">
                        <span className={`text-lg font-semibold tabular-nums ${
                          lote.cantidad_actual === 0 
                            ? 'text-red-500' 
                            : lote.cantidad_actual < (lote.cantidad_inicial * 0.2) 
                              ? 'text-amber-500' 
                              : 'text-slate-700'
                        }`}>
                          {lote.cantidad_actual?.toLocaleString()}
                        </span>
                        <span className="text-slate-400 text-xs">
                          / {(lote.cantidad_contrato ?? lote.cantidad_inicial)?.toLocaleString()}
                        </span>
                      </div>
                      
                      {/* Badge de contrato con tooltip nativo (title) - Nunca se corta */}
                      {lote.cantidad_contrato_global != null && (
                        <div 
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs cursor-help mt-1 ${
                            lote.cantidad_pendiente_global <= 0 
                              ? 'bg-emerald-50 text-emerald-700' 
                              : lote.cantidad_pendiente_global < 0 
                                ? 'bg-rose-50 text-rose-700'
                                : 'bg-amber-50 text-amber-700'
                          }`}
                          title={[
                            `📋 Contrato Global${lote.numero_contrato ? ` (${lote.numero_contrato})` : ''}`,
                            `━━━━━━━━━━━━━━━━━━━━`,
                            `📦 Contratado: ${lote.cantidad_contrato_global?.toLocaleString()}`,
                            `📊 En inventario: ${lote.total_inventario_global?.toLocaleString()}`,
                            `━━━━━━━━━━━━━━━━━━━━`,
                            lote.cantidad_pendiente_global > 0 
                              ? `⏳ Pendiente: ${lote.cantidad_pendiente_global.toLocaleString()}`
                              : lote.cantidad_pendiente_global < 0
                                ? `✨ Excedente: +${Math.abs(lote.cantidad_pendiente_global).toLocaleString()}`
                                : '✅ Contrato completo'
                          ].join('\n')}
                        >
                          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          <span className="font-medium">
                            {lote.cantidad_pendiente_global > 0 
                              ? `-${lote.cantidad_pendiente_global.toLocaleString()}`
                              : lote.cantidad_pendiente_global < 0
                                ? `+${Math.abs(lote.cantidad_pendiente_global).toLocaleString()}`
                                : '✓ OK'
                            }
                          </span>
                        </div>
                      )}
                      
                      {/* Solo número de contrato si no hay contrato global */}
                      {!lote.cantidad_contrato_global && lote.numero_contrato && (
                        <div className="mt-1 text-xs text-indigo-600 truncate max-w-[120px]" title={lote.numero_contrato}>
                          📋 {lote.numero_contrato}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      <div className="flex items-center gap-3">
                        {/* Botón PDF - visible para todos, subir solo farmacia */}
                        <button
                          onClick={() => handleDocumentoModal(lote)}
                          disabled={actionLoading === lote.id}
                          className={`disabled:opacity-50 disabled:cursor-not-allowed ${lote.tiene_documentos ? 'text-green-600 hover:text-green-800' : 'text-gray-400 hover:text-gray-600'}`}
                          title={lote.tiene_documentos ? 'Ver documentos' : (puede.subirDocumento ? 'Subir documento PDF' : 'Sin documentos')}
                        >
                          {actionLoading === lote.id ? (
                            <div className="animate-spin rounded-full h-4 w-4 border-2 border-current border-t-transparent" />
                          ) : (
                            <FaFilePdf />
                          )}
                        </button>
                        {/* Botón Parcialidades - Historial de Entregas */}
                        <button
                          onClick={() => handleParcialidadesModal(lote)}
                          disabled={loadingParcialidades}
                          className={`disabled:opacity-50 disabled:cursor-not-allowed ${
                            lote.num_entregas > 0 
                              ? 'text-purple-600 hover:text-purple-800' 
                              : 'text-gray-400 hover:text-gray-600'
                          }`}
                          title={`Historial de entregas (${lote.num_entregas || 0} entregas, ${lote.total_parcialidades || 0} unidades)`}
                        >
                          <FaHistory />
                        </button>
                        {/* Botón Editar - solo farmacia/admin */}
                        {puede.editar && (
                          <button
                            onClick={() => handleEdit(lote)}
                            disabled={actionLoading === lote.id}
                            className="text-blue-600 hover:text-blue-800 disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Editar"
                          >
                            <FaEdit />
                          </button>
                        )}
                        {/* Botón Eliminar - solo farmacia/admin */}
                        {puede.eliminar && (
                          <button
                            onClick={() => handleDelete(lote.id, lote)}
                            disabled={actionLoading === lote.id}
                            className="text-red-600 hover:text-red-800 disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Desactivar lote"
                          >
                            {actionLoading === lote.id ? (
                              <div className="animate-spin rounded-full h-4 w-4 border-2 border-current border-t-transparent" />
                            ) : (
                              <FaTrash />
                            )}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Paginación */}
        {totalPages > 1 && (
          <Pagination
            page={currentPage}
            totalPages={totalPages}
            totalItems={totalLotes}
            pageSize={pageSize}
            onPageChange={setCurrentPage}
          />
        )}
      </div>

      {/* Modal Crear/Editar */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden shadow-2xl">
            {/* Header del modal con gradiente institucional */}
            <div className="px-6 py-4 border-b-4 flex items-center justify-between modal-header-theme">
              <h2 className="text-2xl font-bold text-white">
                {editingLote ? 'EDITAR LOTE' : 'NUEVO LOTE'}
              </h2>
              <button 
                onClick={() => { setShowModal(false); resetForm(); }}
                className="text-white hover:text-pink-200 transition-colors text-2xl font-bold"
              >
                --
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="overflow-y-auto max-h-[calc(90vh-140px)]">
              <div className="p-6 space-y-5">
                {/* Banner de advertencia si el lote tiene movimientos */}
                {editingLote?.tiene_movimientos && (
                  <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg">
                    <div className="flex items-start">
                      <span className="text-red-500 text-xl mr-3">🔒</span>
                      <div>
                        <p className="text-red-800 font-semibold">Lote bloqueado - Movimientos registrados</p>
                        <p className="text-red-700 text-sm mt-1">
                          <strong>Este lote no puede ser editado</strong> porque ya tiene movimientos de inventario registrados.
                          Esto preserva la integridad y trazabilidad del sistema.
                        </p>
                        <p className="text-red-600 text-xs mt-2">
                          Para modificar el inventario, use <strong>Movimientos → Entrada/Salida</strong>.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Producto */}
                <div>
                  <label className="block text-sm font-bold mb-2 text-theme-primary-hover">
                    PRODUCTO <span className="text-red-600">*</span>
                  </label>
                  <select
                    value={formData.producto}
                    onChange={(e) => {
                      const productoId = e.target.value;
                      const productoSeleccionado = productos.find(p => String(p.id) === String(productoId));
                      setFormData({
                        ...formData, 
                        producto: productoId,
                        // Auto-rellenar presentación del producto si existe
                        presentacion_producto: productoSeleccionado?.presentacion || ''
                      });
                    }}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl transition-all focus:outline-none"
                    style={{
                      '--tw-ring-color': 'rgba(159, 34, 65, 0.2)'
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = '#9F2241';
                      e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = '#E5E7EB';
                      e.target.style.boxShadow = 'none';
                    }}
                    required
                    disabled={editingLote}
                  >
                    <option value="">Seleccione un producto</option>
                    {productos.map(p => (
                      <option key={p.id} value={p.id}>
                        {p.clave} - {p.nombre}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 italic mt-1">No se puede cambiar el producto de un lote existente</p>
                </div>

                {/* Presentación del Producto - SOLO LECTURA */}
                <div>
                  <label className="block text-sm font-bold mb-2 text-theme-primary-hover">
                    PRESENTACIÓN DEL PRODUCTO
                  </label>
                  <input
                    type="text"
                    value={formData.presentacion_producto}
                    readOnly
                    disabled
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl bg-gray-100 text-gray-700 cursor-not-allowed"
                    placeholder="La presentación se obtiene del producto seleccionado"
                  />
                  <p className="text-xs text-gray-500 italic mt-1">
                    <strong>Nota:</strong> La presentación es propiedad del PRODUCTO. Si necesita otra presentación, cree un nuevo producto.
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  {/* Código de Lote */}
                  <div>
                    <label className="block text-sm font-bold mb-2 text-theme-primary-hover">
                      CÓDIGO DE LOTE <span className="text-red-600">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.numero_lote}
                      onChange={(e) => setFormData({...formData, numero_lote: e.target.value.toUpperCase()})}
                      className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl transition-all focus:outline-none"
                      onFocus={(e) => {
                        e.target.style.borderColor = '#9F2241';
                        e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
                      }}
                      onBlur={(e) => {
                        e.target.style.borderColor = '#E5E7EB';
                        e.target.style.boxShadow = 'none';
                      }}
                      required
                      disabled={editingLote}
                      minLength={3}
                      maxLength={100}
                      placeholder="Ingrese el código del lote"
                    />
                    <p className="text-xs text-gray-500 italic mt-1">
                      {editingLote ? 'No editable - Identificador único del lote' : 'Se convertirá a mayúsculas automáticamente'}
                    </p>
                  </div>
                  
                  {/* Fecha Caducidad - BLOQUEADA SI TIENE MOVIMIENTOS */}
                  <div>
                    <label className="block text-sm font-bold mb-2 text-theme-primary-hover">
                      FECHA DE CADUCIDAD {!(editingLote?.tiene_movimientos) && <span className="text-red-600">*</span>}
                    </label>
                    <input
                      type="date"
                      value={formData.fecha_caducidad}
                      onChange={(e) => !(editingLote?.tiene_movimientos) && setFormData({...formData, fecha_caducidad: e.target.value})}
                      className={`w-full px-4 py-3 border-2 rounded-xl transition-all focus:outline-none ${
                        editingLote?.tiene_movimientos 
                          ? 'border-gray-200 bg-gray-100 text-gray-600 cursor-not-allowed' 
                          : 'border-gray-200'
                      }`}
                      onFocus={(e) => {
                        if (!(editingLote?.tiene_movimientos)) {
                          e.target.style.borderColor = '#9F2241';
                          e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
                        }
                      }}
                      onBlur={(e) => {
                        e.target.style.borderColor = '#E5E7EB';
                        e.target.style.boxShadow = 'none';
                      }}
                      required={!(editingLote?.tiene_movimientos)}
                      disabled={editingLote?.tiene_movimientos}
                      readOnly={editingLote?.tiene_movimientos}
                      min={new Date().toISOString().split('T')[0]}
                    />
                    {editingLote?.tiene_movimientos ? (
                      <p className="text-xs text-orange-600 italic mt-1">
                        🔒 No editable - Lote con movimientos registrados
                      </p>
                    ) : formData.fecha_caducidad && (
                      <p className="text-xs font-bold mt-1" style={{ color: '#D97706' }}>
                        {(() => {
                          const dias = Math.ceil((new Date(formData.fecha_caducidad) - new Date()) / (1000 * 60 * 60 * 24));
                          return dias < 0 ? '-s  Vencido' : `Caduca en ${dias} días`;
                        })()}
                      </p>
                    )}
                  </div>
                </div>

                {/* CAMPOS OBLIGATORIOS: Número de Contrato y Fecha de Entrega */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {puedeVerContrato ? (
                    <div>
                      <label className="block text-sm font-bold mb-2 text-theme-primary-hover">
                        NÚMERO DE CONTRATO {!editingLote && <span className="text-red-600">*</span>}{editingLote?.tiene_movimientos && <span className="text-orange-500 text-xs">🔒</span>}
                      </label>
                      <input
                        type="text"
                        value={formData.numero_contrato}
                        onChange={(e) => !(editingLote?.tiene_movimientos) && setFormData({...formData, numero_contrato: e.target.value})}
                        className={`w-full px-4 py-3 border-2 rounded-xl transition-all focus:outline-none ${
                          editingLote?.tiene_movimientos
                            ? 'border-gray-200 bg-gray-100 text-gray-600 cursor-not-allowed'
                            : 'border-gray-200'
                        }`}
                        onFocus={(e) => {
                          if (!(editingLote?.tiene_movimientos)) {
                            e.target.style.borderColor = '#9F2241';
                            e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
                          }
                        }}
                        onBlur={(e) => {
                          e.target.style.borderColor = '#E5E7EB';
                          e.target.style.boxShadow = 'none';
                        }}
                        disabled={editingLote?.tiene_movimientos}
                        readOnly={editingLote?.tiene_movimientos}
                        placeholder="Ej: CB/A/37/2025"
                        maxLength={100}
                      />
                      <p className="text-xs text-gray-400 mt-1">
                        {editingLote?.tiene_movimientos
                          ? '🔒 No editable - Campo auditable con movimientos'
                          : 'Requerido para trazabilidad de adquisiciones'}
                      </p>
                    </div>
                  ) : (
                    <div />
                  )}

                  <div>
                    <label className="block text-sm font-bold mb-2 text-theme-primary-hover">
                      FECHA DE ENTREGA {!editingLote && <span className="text-red-600">*</span>}{editingLote?.tiene_movimientos && <span className="text-red-500 text-xs">🔒</span>}
                    </label>
                    <input
                      type="date"
                      value={formData.fecha_fabricacion}
                      onChange={(e) => !(editingLote?.tiene_movimientos) && setFormData({...formData, fecha_fabricacion: e.target.value})}
                      className={`w-full px-4 py-3 border-2 rounded-xl transition-all focus:outline-none ${
                        editingLote?.tiene_movimientos
                          ? 'border-gray-200 bg-gray-100 text-gray-600 cursor-not-allowed'
                          : 'border-gray-200'
                      }`}
                      onFocus={(e) => {
                        if (!(editingLote?.tiene_movimientos)) {
                          e.target.style.borderColor = '#9F2241';
                          e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
                        }
                      }}
                      onBlur={(e) => {
                        e.target.style.borderColor = '#E5E7EB';
                        e.target.style.boxShadow = 'none';
                      }}
                      required={!editingLote}
                      disabled={editingLote?.tiene_movimientos}
                      readOnly={editingLote?.tiene_movimientos}
                      max={new Date().toISOString().split('T')[0]}
                    />
                    <p className="text-xs text-gray-500 italic mt-1">
                      {editingLote?.tiene_movimientos ? '🔒 No editable' : 'Fecha de entrega del lote'}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 items-start">
                  {/* Columna izquierda: CANTIDAD CONTRATO LOTE + CANTIDAD INICIAL apilados */}
                  <div className="flex flex-col gap-4">
                  {/* ISS-INV-002: Cantidad del Contrato LOTE (solo para este lote específico) */}
                  <div>
                    <label className="block text-sm font-bold mb-2 text-theme-primary-hover">
                      📦 CANTIDAD CONTRATO LOTE
                      <span className="text-gray-500 text-xs ml-2 font-normal">(Solo para este lote)</span>
                    </label>
                    <input
                      type="number"
                      min="0"
                      value={formData.cantidad_contrato}
                      onChange={(e) => setFormData({...formData, cantidad_contrato: e.target.value})}
                      className="w-full px-4 py-3 border-2 rounded-xl transition-all focus:outline-none border-gray-200"
                      onFocus={(e) => {
                        e.target.style.borderColor = '#9F2241';
                        e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
                      }}
                      onBlur={(e) => {
                        e.target.style.borderColor = '#E5E7EB';
                        e.target.style.boxShadow = 'none';
                      }}
                      placeholder={formData.cantidad_contrato === '' || formData.cantidad_contrato === null ? 'Sin definir (opcional)' : 'Total para este lote'}
                    />
                    <p className="text-xs text-gray-500 italic mt-1">
                      Opcional. Cantidad acordada solo para este lote
                    </p>
                  </div>
                  
                  {/* Cantidad Inicial - cantidad realmente recibida (puede ser parcial) */}
                  <div>
                    <label className="block text-sm font-bold mb-2 text-theme-primary-hover">
                      CANTIDAD INICIAL {!editingLote && <span className="text-red-600">*</span>}
                      {editingLote && <span className="text-red-500 text-xs ml-1">🔒</span>}
                    </label>
                    <input
                      type="number"
                      min="1"
                      value={formData.cantidad_inicial}
                      onChange={(e) => !editingLote && setFormData({...formData, cantidad_inicial: e.target.value})}
                      className={`w-full px-4 py-3 border-2 rounded-xl transition-all focus:outline-none ${
                        editingLote 
                          ? 'border-gray-200 bg-gray-100 text-gray-600 cursor-not-allowed' 
                          : 'border-gray-200'
                      }`}
                      onFocus={(e) => {
                        if (!editingLote) {
                          e.target.style.borderColor = '#9F2241';
                          e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
                        }
                      }}
                      onBlur={(e) => {
                        e.target.style.borderColor = '#E5E7EB';
                        e.target.style.boxShadow = 'none';
                      }}
                      required={!editingLote}
                      disabled={editingLote}
                      readOnly={editingLote}
                      placeholder="Cantidad de la primera entrega"
                    />
                    <p className="text-xs text-gray-500 italic mt-1">
                      {editingLote 
                        ? '🔒 Inmutable. Para reabastecer use Movimientos → Entrada' 
                        : 'Cantidad de la primera entrega que se registra al crear el lote'}
                    </p>
                  </div>
                  </div>{/* fin columna izquierda */}
                  
                  {/* ISS-INV-003: Columna derecha - Contrato Global */}
                  {esFarmaciaAdmin && (
                    <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                      <div className="flex items-center justify-between mb-3">
                        <label className="text-sm font-semibold text-slate-700">
                          Contrato Global
                        </label>
                        <span className="text-xs text-slate-500">Aplica a todos los lotes</span>
                      </div>
                      
                      <input
                        type="number"
                        min="0"
                        value={formData.cantidad_contrato_global}
                        onChange={(e) => {
                          setCcgAutoCompletado(false);
                          setFormData({...formData, cantidad_contrato_global: e.target.value});
                        }}
                        className={`w-full px-4 py-2.5 border rounded-lg text-base transition-all focus:outline-none ${
                          ccgAutoCompletado
                            ? 'border-emerald-400 bg-emerald-50 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100'
                            : 'border-slate-300 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100'
                        }`}
                        placeholder={cargandoCCG ? 'Buscando...' : 'Ej: 1000'}
                        disabled={cargandoCCG}
                      />
                      {cargandoCCG && (
                        <div className="mt-1 flex items-center gap-1.5 text-xs text-slate-500">
                          <div className="animate-spin rounded-full h-3 w-3 border-2 border-slate-400 border-t-transparent" />
                          Buscando contrato global existente...
                        </div>
                      )}
                      {!cargandoCCG && ccgAutoCompletado && formData.cantidad_contrato_global && (
                        <div className="mt-1 flex items-center gap-1.5 text-xs text-emerald-700">
                          <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                          </svg>
                          Auto-completado desde contrato existente
                        </div>
                      )}
                      
                      {/* Estado del contrato - Solo si hay datos */}
                      {editingLote && editingLote.cantidad_contrato_global != null && (
                        <div className="mt-3 grid grid-cols-3 gap-3">
                          <div className="bg-white rounded-lg p-2.5 border border-slate-100 text-center">
                            <div className="text-xs text-slate-500 mb-0.5">Contratado</div>
                            <div className="text-base font-bold text-slate-800">{editingLote.cantidad_contrato_global?.toLocaleString()}</div>
                          </div>
                          <div className="bg-white rounded-lg p-2.5 border border-slate-100 text-center">
                            <div className="text-xs text-slate-500 mb-0.5">Inventario</div>
                            <div className="text-base font-bold text-indigo-600">{(editingLote.total_inventario_global ?? 0)?.toLocaleString()}</div>
                          </div>
                          <div className={`rounded-lg p-2.5 text-center ${
                            editingLote.cantidad_pendiente_global > 0 
                              ? 'bg-amber-50 border border-amber-200' 
                              : editingLote.cantidad_pendiente_global < 0 
                                ? 'bg-rose-50 border border-rose-200'
                                : 'bg-emerald-50 border border-emerald-200'
                          }`}>
                            <div className="text-xs text-slate-500 mb-0.5">
                              {editingLote.cantidad_pendiente_global > 0 ? 'Pendiente' : editingLote.cantidad_pendiente_global < 0 ? 'Excedente' : 'Estado'}
                            </div>
                            <div className={`text-base font-bold ${
                              editingLote.cantidad_pendiente_global > 0 
                                ? 'text-amber-600' 
                                : editingLote.cantidad_pendiente_global < 0 
                                  ? 'text-rose-600'
                                  : 'text-emerald-600'
                            }`}>
                              {editingLote.cantidad_pendiente_global > 0 
                                ? editingLote.cantidad_pendiente_global?.toLocaleString()
                                : editingLote.cantidad_pendiente_global < 0
                                  ? `+${Math.abs(editingLote.cantidad_pendiente_global)?.toLocaleString()}`
                                  : '✓'}
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {/* Nota breve */}
                      <p className="text-xs text-slate-500 mt-2">
                        Total contratado para esta clave. El sistema calcula automáticamente pendientes.
                      </p>
                      
                      {/* Advertencia si falta número de contrato */}
                      {!formData.numero_contrato && formData.cantidad_contrato_global && (
                        <div className="mt-2 flex items-center gap-2 text-xs text-amber-700 bg-amber-50 p-2 rounded-lg">
                          <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>
                          <span>Especifique el número de contrato para propagar correctamente</span>
                        </div>
                      )}
                      
                      {/* Confirmación de aplicación */}
                      {formData.numero_contrato && formData.cantidad_contrato_global && (
                        <div className="mt-2 flex items-center gap-2 text-xs text-emerald-700 bg-emerald-50 p-2 rounded-lg">
                          <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          <span>Se aplicará a lotes con contrato <strong>{formData.numero_contrato}</strong></span>
                        </div>
                      )}
                    </div>
                  )}
                  
                </div>

                {/* Precio Unitario */}
                <div className="grid grid-cols-2 gap-4">
                  {/* Precio Unitario (nombre real en DB) */}
                  <div>
                    <label className="block text-sm font-bold mb-2 text-theme-primary-hover">
                      PRECIO UNITARIO {editingLote?.tiene_movimientos && <span className="text-red-500 text-xs">🔒</span>}
                    </label>
                    <div className="relative">
                      <span className="absolute left-4 top-3.5 font-bold" style={{ color: '#6B7280' }}>$</span>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={formData.precio_unitario}
                        onChange={(e) => !(editingLote?.tiene_movimientos) && setFormData({...formData, precio_unitario: e.target.value})}
                        className={`w-full pl-8 pr-4 py-3 border-2 rounded-xl transition-all focus:outline-none ${
                          editingLote?.tiene_movimientos 
                            ? 'border-gray-200 bg-gray-100 text-gray-600 cursor-not-allowed' 
                            : 'border-gray-200'
                        }`}
                        onFocus={(e) => {
                          if (!(editingLote?.tiene_movimientos)) {
                            e.target.style.borderColor = '#9F2241';
                            e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
                          }
                        }}
                        onBlur={(e) => {
                          e.target.style.borderColor = '#E5E7EB';
                          e.target.style.boxShadow = 'none';
                        }}
                        disabled={editingLote?.tiene_movimientos}
                        readOnly={editingLote?.tiene_movimientos}
                        placeholder="0.00"
                      />
                    </div>
                  </div>
                </div>

                {/* Ubicación */}
                <div>
                  <label className="block text-sm font-bold mb-2 text-theme-primary-hover">
                    UBICACIÓN {editingLote?.tiene_movimientos && <span className="text-red-500 text-xs">🔒</span>}
                  </label>
                  <input
                    type="text"
                    value={formData.ubicacion}
                    onChange={(e) => !(editingLote?.tiene_movimientos) && setFormData({...formData, ubicacion: e.target.value})}
                    className={`w-full px-4 py-3 border-2 rounded-xl transition-all focus:outline-none ${
                      editingLote?.tiene_movimientos
                        ? 'border-gray-200 bg-gray-100 text-gray-600 cursor-not-allowed'
                        : 'border-gray-200'
                    }`}
                    onFocus={(e) => {
                      if (!(editingLote?.tiene_movimientos)) {
                        e.target.style.borderColor = '#9F2241';
                        e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
                      }
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = '#E5E7EB';
                      e.target.style.boxShadow = 'none';
                    }}
                    disabled={editingLote?.tiene_movimientos}
                    readOnly={editingLote?.tiene_movimientos}
                    placeholder="Ej: Estante A, Anaquel 3"
                    maxLength={100}
                  />
                  <p className="text-xs text-gray-500 italic mt-1">
                    {editingLote?.tiene_movimientos ? '🔒 No editable' : 'Ubicación física del lote en almacén'}
                  </p>
                </div>

                {/* Marca / Laboratorio - Solo Admin/Farmacia */}
                {puedeVerContrato && (
                <div>
                  <label className="block text-sm font-bold mb-2 text-theme-primary-hover">
                    MARCA / LABORATORIO {editingLote?.tiene_movimientos && <span className="text-red-500 text-xs">🔒</span>}
                  </label>
                  <input
                    type="text"
                    value={formData.marca}
                    onChange={(e) => !(editingLote?.tiene_movimientos) && setFormData({...formData, marca: e.target.value})}
                    className={`w-full px-4 py-3 border-2 rounded-xl transition-all focus:outline-none ${
                      editingLote?.tiene_movimientos
                        ? 'border-gray-200 bg-gray-100 text-gray-600 cursor-not-allowed'
                        : 'border-gray-200'
                    }`}
                    onFocus={(e) => {
                      if (!(editingLote?.tiene_movimientos)) {
                        e.target.style.borderColor = '#9F2241';
                        e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
                      }
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = '#E5E7EB';
                      e.target.style.boxShadow = 'none';
                    }}
                    disabled={editingLote?.tiene_movimientos}
                    readOnly={editingLote?.tiene_movimientos}
                    placeholder="Ej: Bayer, Pfizer, Genérico"
                    maxLength={150}
                  />
                  <p className="text-xs text-gray-400 mt-1">
                    {editingLote?.tiene_movimientos ? '🔒 No editable' : 'Marca o laboratorio del lote'}
                  </p>
                </div>
                )}

                {/* Lote activo checkbox */}
                <div className="flex items-center gap-3 p-4 rounded-xl" style={{ backgroundColor: '#FEF9F2', border: '2px solid #E5E7EB' }}>
                  <input
                    type="checkbox"
                    checked={true}
                    className="w-5 h-5 rounded"
                    style={{ accentColor: 'var(--color-primary)' }}
                    disabled
                  />
                  <div>
                    <label className="font-bold text-sm text-theme-primary-hover">Lote activo</label>
                    <p className="text-xs text-gray-600">Los lotes inactivos no estarín disponibles para salidas</p>
                  </div>
                </div>

                {/* Alerta de proximidad a caducidad */}
                {formData.fecha_caducidad && (() => {
                  const dias = Math.ceil((new Date(formData.fecha_caducidad) - new Date()) / (1000 * 60 * 60 * 24));
                  return dias <= 19 && (
                    <div className="flex items-start gap-3 p-4 rounded-xl" style={{ backgroundColor: '#FEF3C7', border: '2px solid #F59E0B' }}>
                      <FaExclamationTriangle className="text-xl mt-0.5" style={{ color: '#F59E0B' }} />
                      <div>
                        <p className="font-bold text-sm" style={{ color: '#92400E' }}>-s  Atención:</p>
                        <p className="text-sm" style={{ color: '#78350F' }}>Este lote está príximo a caducar en {dias} días</p>
                      </div>
                    </div>
                  );
                })()}
              </div>

              {/* Footer con botones */}
              <div className="px-6 py-4 border-t-2 bg-gray-50 flex justify-between gap-3">
                <button
                  type="button"
                  onClick={() => { setShowModal(false); resetForm(); }}
                  className="px-6 py-3 rounded-xl font-bold transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ 
                    background: 'linear-gradient(135deg, #6B7280 0%, #4B5563 100%)',
                    color: 'white'
                  }}
                  disabled={savingLote}
                >
                  CANCELAR
                </button>
                <button
                  type="submit"
                  disabled={savingLote}
                  className="px-8 py-3 rounded-xl font-bold transition-all transform hover:scale-105 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed text-white bg-theme-gradient flex items-center gap-2"
                >
                  {savingLote && (
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  )}
                  {savingLote ? 'GUARDANDO...' : 'GUARDAR LOTE'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Importar - Usando ImportadorModerno */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="relative w-full max-w-4xl my-8">
            <ImportadorModerno
              tipo="lotes"
              onCerrar={() => setShowImportModal(false)}
              onImportar={async (formData) => {
                setImportLoading(true);
                try {
                  // Incluir centro del usuario para trazabilidad si no tiene permisos globales
                  if (!puedeVerGlobal && centroUsuario) {
                    formData.append('centro', centroUsuario);
                  }
                  const response = await lotesAPI.importar(formData);
                  // Recargar lotes después de importar
                  await cargarLotes();
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

      {/* Modal de Documentos */}
      {showDocModal && selectedLoteDoc && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-6 border-b flex justify-between items-center bg-theme-gradient">
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                <FaFilePdf /> Documentos del Lote
              </h3>
              <button
                onClick={() => setShowDocModal(false)}
                className="text-white hover:text-gray-200"
              >
                <FaTimes className="text-xl" />
              </button>
            </div>
            
            <div className="p-6 space-y-4 overflow-y-auto flex-1">
              <div className="text-sm text-gray-600 border-b pb-3">
                <p><strong>Lote:</strong> {selectedLoteDoc.numero_lote}</p>
                <p><strong>Producto:</strong> {selectedLoteDoc.producto_nombre}</p>
              </div>
              
              {/* Lista de documentos existentes */}
              {selectedLoteDoc.documentos_cargados && selectedLoteDoc.documentos_cargados.length > 0 ? (
                <div className="space-y-2">
                  <h4 className="text-sm font-semibold text-gray-700">
                    Documentos adjuntos ({selectedLoteDoc.documentos_cargados.length})
                  </h4>
                  {selectedLoteDoc.documentos_cargados.map((doc) => (
                    <div key={doc.id} className="p-3 bg-green-50 border border-green-200 rounded-lg flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-green-800 font-medium truncate">
                          📄 {doc.nombre_archivo || 'documento.pdf'}
                        </p>
                        <p className="text-xs text-gray-500">
                          {doc.tipo_documento} {doc.numero_documento ? `• ${doc.numero_documento}` : ''}
                          {doc.fecha_documento ? ` • ${formatFecha(doc.fecha_documento)}` : ''}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 ml-2">
                        {doc.archivo && (
                          <a
                            href={doc.archivo}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-2 text-blue-600 hover:text-blue-800"
                            title="Ver documento"
                          >
                            <FaDownload />
                          </a>
                        )}
                        {puede.subirDocumento && (
                          <button
                            onClick={() => handleEliminarDocumento(doc.id)}
                            disabled={actionLoading === selectedLoteDoc.id}
                            className="p-2 text-red-600 hover:text-red-800 disabled:opacity-50"
                            title="Eliminar documento"
                          >
                            <FaTrash />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-center">
                  <p className="text-sm text-gray-600">No hay documentos adjuntos</p>
                </div>
              )}
              
              {/* Input de subida - DESHABILITADO (Mejora de almacenamiento pendiente) */}
              {puede.subirDocumento && (
                <div className="border-t pt-4">
                  <label className="block text-sm font-semibold text-gray-400 mb-2">
                    Agregar nuevo documento
                  </label>
                  <div className="w-full px-3 py-2 border border-gray-200 rounded-lg bg-gray-50 cursor-not-allowed opacity-60">
                    <span className="text-sm text-gray-400">Seleccionar archivo PDF</span>
                  </div>
                  <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded-lg">
                    <p className="text-xs text-amber-700 flex items-center gap-1">
                      <span className="font-semibold">⏳ Funcionalidad pendiente:</span>
                      En espera de mejora de almacenamiento para esta funcionalidad.
                    </p>
                  </div>
                </div>
              )}
            </div>
            
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end">
              <button
                onClick={() => setShowDocModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100"
                disabled={loading}
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Parcialidades - Historial de Entregas */}
      {showParcialidadesModal && selectedLoteParcialidades && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* HEADER - Mejorado con botones de exportar */}
            <div className="p-5 border-b bg-gradient-to-r from-primary to-[#6B1839]">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    <FaBoxes /> Historial de Entregas
                  </h3>
                  <p className="text-white/80 text-sm mt-1">
                    Lote: <span className="font-semibold">{selectedLoteParcialidades.numero_lote}</span>
                  </p>
                </div>
                {/* Botones de exportar y cerrar */}
                <div className="flex items-center gap-2">
                  {/* Exportar PDF */}
                  <button
                    onClick={() => handleExportarEntregas('pdf')}
                    disabled={exportingEntregas === 'pdf' || !parcialidadesData.parcialidades?.length}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                      exportingEntregas === 'pdf' 
                        ? 'bg-white/30 cursor-wait' 
                        : parcialidadesData.parcialidades?.length
                          ? 'bg-white/20 hover:bg-white/30 text-white'
                          : 'bg-white/10 text-white/50 cursor-not-allowed'
                    }`}
                    title="Exportar a PDF"
                  >
                    {exportingEntregas === 'pdf' ? (
                      <span className="animate-spin">⏳</span>
                    ) : (
                      <FaFilePdf />
                    )}
                    PDF
                  </button>
                  {/* Exportar Excel */}
                  <button
                    onClick={() => handleExportarEntregas('excel')}
                    disabled={exportingEntregas === 'excel' || !parcialidadesData.parcialidades?.length}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                      exportingEntregas === 'excel' 
                        ? 'bg-white/30 cursor-wait' 
                        : parcialidadesData.parcialidades?.length
                          ? 'bg-white/20 hover:bg-white/30 text-white'
                          : 'bg-white/10 text-white/50 cursor-not-allowed'
                    }`}
                    title="Exportar a Excel"
                  >
                    {exportingEntregas === 'excel' ? (
                      <span className="animate-spin">⏳</span>
                    ) : (
                      <FaFileExcel />
                    )}
                    Excel
                  </button>
                  {/* Cerrar */}
                  <button
                    onClick={() => {
                      setShowParcialidadesModal(false);
                      setSelectedLoteParcialidades(null);
                      setParcialidadesData({ parcialidades: [], resumen: {}, contrato_lote: {} });
                      setRequiereOverride(false);
                      setMotivoOverride('');
                      setInfoContratoCumplido(null);
                    }}
                    className="text-white hover:text-gray-200 p-1 ml-2"
                  >
                    <FaTimes className="text-xl" />
                  </button>
                </div>
              </div>
            </div>
            
            <div className="p-5 space-y-4 overflow-y-auto flex-1">
              {/* INFORMACIÓN DEL LOTE - Rediseñado como tarjetas */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-gray-50 rounded-lg p-3 border">
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Producto</p>
                  <p className="text-sm font-semibold text-gray-800 truncate" title={selectedLoteParcialidades.producto_nombre}>
                    {selectedLoteParcialidades.producto_nombre || 'N/A'}
                  </p>
                  <p className="text-xs text-gray-500">{selectedLoteParcialidades.producto_clave || ''}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3 border">
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Contrato</p>
                  <p className="text-sm font-semibold text-gray-800">
                    {selectedLoteParcialidades.numero_contrato || 'Sin contrato'}
                  </p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3 border">
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Caducidad</p>
                  <p className="text-sm font-semibold text-gray-800">
                    {selectedLoteParcialidades.fecha_caducidad 
                      ? new Date(selectedLoteParcialidades.fecha_caducidad).toLocaleDateString('es-MX')
                      : 'N/A'}
                  </p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3 border">
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Fecha Entrega</p>
                  <p className="text-sm font-semibold text-gray-800">
                    {/* Prioridad: lote_info del backend > fecha_fabricacion del lote > resumen > primera parcialidad */}
                    {parcialidadesData.lote_info?.fecha_fabricacion 
                      ? new Date(parcialidadesData.lote_info.fecha_fabricacion).toLocaleDateString('es-MX')
                      : parcialidadesData.resumen?.fecha_entrega
                        ? new Date(parcialidadesData.resumen.fecha_entrega).toLocaleDateString('es-MX')
                        : selectedLoteParcialidades.fecha_fabricacion 
                          ? new Date(selectedLoteParcialidades.fecha_fabricacion).toLocaleDateString('es-MX')
                          : parcialidadesData.resumen?.primera_entrega
                            ? new Date(parcialidadesData.resumen.primera_entrega).toLocaleDateString('es-MX')
                            : 'Sin fecha'}
                  </p>
                </div>
              </div>

              {/* ESTADO DE CONTRATOS - Rediseñado con dos columnas claras */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Contrato del Lote */}
                <div className={`rounded-xl border-2 p-4 ${
                  (parcialidadesData.contrato_lote?.estado === 'CUMPLIDO' || parcialidadesData.contrato_lote?.estado === 'cumplido')
                    ? 'bg-green-50 border-green-400' 
                    : parcialidadesData.contrato_lote?.estado === 'SOBREENTREGA'
                      ? 'bg-red-50 border-red-400'
                      : (parcialidadesData.contrato_lote?.estado === 'PARCIAL' || parcialidadesData.contrato_lote?.estado === 'parcial')
                        ? 'bg-amber-50 border-amber-400'
                        : 'bg-gray-50 border-gray-300'
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-bold text-gray-700">📦 Contrato del Lote</h4>
                    <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                      (parcialidadesData.contrato_lote?.estado === 'CUMPLIDO' || parcialidadesData.contrato_lote?.estado === 'cumplido')
                        ? 'bg-green-200 text-green-800' 
                        : parcialidadesData.contrato_lote?.estado === 'SOBREENTREGA'
                          ? 'bg-red-200 text-red-800'
                          : (parcialidadesData.contrato_lote?.estado === 'PARCIAL' || parcialidadesData.contrato_lote?.estado === 'parcial')
                            ? 'bg-amber-200 text-amber-800'
                            : 'bg-gray-200 text-gray-700'
                    }`}>
                      {parcialidadesData.contrato_lote?.estado?.toUpperCase() || 'SIN CONTRATO'}
                    </span>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Contratado:</span>
                      <span className="font-semibold">
                        {(parcialidadesData.contrato_lote?.cantidad_contrato || selectedLoteParcialidades.cantidad_contrato)?.toLocaleString() || 'N/A'}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Entregado:</span>
                      <span className="font-semibold text-primary">
                        {parcialidadesData.contrato_lote?.total_entregado?.toLocaleString() || 0}
                      </span>
                    </div>
                    {parcialidadesData.contrato_lote?.cantidad_contrato > 0 && (
                      <>
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                          <div 
                            className={`h-2 rounded-full transition-all ${
                              parcialidadesData.contrato_lote?.porcentaje >= 100 ? 'bg-green-500' : 'bg-primary'
                            }`}
                            style={{ width: `${Math.min(100, parcialidadesData.contrato_lote?.porcentaje || 0)}%` }}
                          ></div>
                        </div>
                        <p className="text-xs text-center text-gray-500">
                          {parcialidadesData.contrato_lote?.porcentaje?.toFixed(1) || 0}% completado
                        </p>
                      </>
                    )}
                    {parcialidadesData.contrato_lote?.excedente > 0 && (
                      <p className="text-xs text-red-600 font-semibold mt-1">
                        ⚠️ Excedente: +{parcialidadesData.contrato_lote.excedente?.toLocaleString()}
                      </p>
                    )}
                    {parcialidadesData.contrato_lote?.pendiente > 0 && (
                      <p className="text-xs text-amber-600 font-semibold mt-1">
                        ⏳ Pendiente: {parcialidadesData.contrato_lote.pendiente?.toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>

                {/* Contrato Global */}
                <div className={`rounded-xl border-2 p-4 ${
                  parcialidadesData.contrato_global
                    ? (parcialidadesData.contrato_global.estado === 'CUMPLIDO' || parcialidadesData.contrato_global.estado === 'cumplido')
                      ? 'bg-green-50 border-green-400' 
                      : parcialidadesData.contrato_global.estado === 'SOBREENTREGA'
                        ? 'bg-red-50 border-red-400'
                        : 'bg-blue-50 border-blue-400'
                    : 'bg-gray-100 border-gray-300'
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-bold text-gray-700">🌐 Contrato Global</h4>
                    {parcialidadesData.contrato_global ? (
                      <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                        (parcialidadesData.contrato_global.estado === 'CUMPLIDO' || parcialidadesData.contrato_global.estado === 'cumplido')
                          ? 'bg-green-200 text-green-800' 
                          : parcialidadesData.contrato_global.estado === 'SOBREENTREGA'
                            ? 'bg-red-200 text-red-800'
                            : 'bg-blue-200 text-blue-800'
                      }`}>
                        {parcialidadesData.contrato_global.estado?.toUpperCase() || 'PARCIAL'}
                      </span>
                    ) : (
                      <span className="px-2 py-1 rounded-full text-xs font-bold bg-gray-200 text-gray-600">
                        N/A
                      </span>
                    )}
                  </div>
                  {parcialidadesData.contrato_global ? (
                    <div className="space-y-2">
                      <p className="text-xs text-gray-500 italic">
                        Total para clave {selectedLoteParcialidades.producto_clave || 'del producto'}
                      </p>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Contratado:</span>
                        <span className="font-semibold">
                          {parcialidadesData.contrato_global.cantidad_contrato_global?.toLocaleString() || 'N/A'}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Entregado (todos lotes):</span>
                        <span className="font-semibold text-blue-600">
                          {parcialidadesData.contrato_global.total_entregado?.toLocaleString() || 0}
                        </span>
                      </div>
                      {parcialidadesData.contrato_global.cantidad_contrato_global > 0 && (
                        <>
                          <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                            <div 
                              className={`h-2 rounded-full transition-all ${
                                parcialidadesData.contrato_global.porcentaje >= 100 ? 'bg-green-500' : 'bg-blue-500'
                              }`}
                              style={{ width: `${Math.min(100, parcialidadesData.contrato_global.porcentaje || 0)}%` }}
                            ></div>
                          </div>
                          <p className="text-xs text-center text-gray-500">
                            {parcialidadesData.contrato_global.porcentaje?.toFixed(1) || 0}% completado
                          </p>
                        </>
                      )}
                      <p className="text-xs text-gray-500 mt-1">
                        📊 {parcialidadesData.contrato_global.num_lotes || 1} lote(s) en este contrato
                      </p>
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 italic">
                      Este lote no tiene contrato global definido
                    </p>
                  )}
                </div>
              </div>
              
              {/* LISTA DE ENTREGAS - Mejorada */}
              {loadingParcialidades ? (
                <div className="flex justify-center p-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary border-t-transparent"></div>
                </div>
              ) : parcialidadesData.parcialidades?.length > 0 ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-bold text-gray-700 flex items-center gap-2">
                      📋 Entregas registradas ({parcialidadesData.parcialidades.length})
                    </h4>
                    <div className="text-right">
                      <span className="text-lg font-bold text-primary">
                        {parcialidadesData.parcialidades.reduce((sum, p) => sum + (p.cantidad || 0), 0).toLocaleString()}
                      </span>
                      <span className="text-sm text-gray-500 ml-1">unidades total</span>
                    </div>
                  </div>
                  
                  {/* Tabla de entregas */}
                  <div className="border rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-100">
                        <tr>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600">Fecha</th>
                          <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600">Cantidad</th>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600">Notas</th>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600">Usuario</th>
                          {puede.editar && <th className="px-3 py-2 text-center text-xs font-semibold text-gray-600">Acción</th>}
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {parcialidadesData.parcialidades.map((parcialidad, idx) => (
                          <tr key={parcialidad.id} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                            <td className="px-3 py-2">
                              <span className="font-medium">
                                {parcialidad.fecha_entrega 
                                  ? new Date(parcialidad.fecha_entrega).toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' })
                                  : 'Sin fecha'}
                              </span>
                            </td>
                            <td className="px-3 py-2 text-right">
                              <span className="font-bold text-primary">
                                {parcialidad.cantidad?.toLocaleString()}
                              </span>
                            </td>
                            <td className="px-3 py-2 text-gray-600 max-w-[150px] truncate" title={parcialidad.notas}>
                              {parcialidad.notas || '-'}
                            </td>
                            <td className="px-3 py-2 text-gray-500 text-xs">
                              {parcialidad.usuario_nombre || 'Sistema'}
                            </td>
                            {puede.editar && (
                              <td className="px-3 py-2 text-center">
                                <button
                                  onClick={() => handleEliminarParcialidad(parcialidad)}
                                  disabled={loadingParcialidades}
                                  className="p-1.5 text-red-500 hover:text-red-700 hover:bg-red-50 rounded disabled:opacity-50"
                                  title="Eliminar entrega"
                                >
                                  <FaTrash className="text-xs" />
                                </button>
                              </td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="p-6 bg-gray-50 border-2 border-dashed border-gray-300 rounded-xl text-center">
                  <FaBoxes className="text-4xl text-gray-300 mx-auto mb-2" />
                  <p className="text-gray-600 font-medium">No hay entregas registradas</p>
                  <p className="text-xs text-gray-400 mt-1">Registra la primera entrega usando el formulario</p>
                </div>
              )}
              
              {/* Formulario para agregar nueva parcialidad */}
              {puede.editar && (
                <div className="border-t pt-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">Registrar nueva entrega</h4>
                  
                  {/* Advertencia si requiere override (contrato cumplido) */}
                  {requiereOverride && infoContratoCumplido && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-300 rounded-lg">
                      <p className="text-sm font-semibold text-red-800 flex items-center gap-2">
                        🔒 Contrato {infoContratoCumplido.estado}
                      </p>
                      <p className="text-xs text-red-700 mt-1">
                        {infoContratoCumplido.mensaje}
                      </p>
                      <p className="text-xs text-gray-600 mt-1">
                        Total entregado: {infoContratoCumplido.total_entregado?.toLocaleString()} / Contrato: {infoContratoCumplido.cantidad_contrato?.toLocaleString()}
                      </p>
                      {/* P0-2 FIX: Mostrar mensaje si usuario NO puede hacer override */}
                      {!puede.overrideSobreentrega && (
                        <div className="mt-2 p-2 bg-yellow-100 border border-yellow-400 rounded">
                          <p className="text-xs text-yellow-800 font-semibold flex items-center gap-1">
                            ⚠️ Solo administradores o personal de farmacia pueden autorizar sobre-entregas.
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Fecha de entrega *</label>
                      <input
                        type="date"
                        value={nuevaParcialidad.fecha_entrega}
                        onChange={(e) => setNuevaParcialidad(prev => ({ ...prev, fecha_entrega: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary focus:border-primary"
                        max={new Date().toISOString().split('T')[0]}
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Cantidad entregada *</label>
                      <input
                        type="number"
                        value={nuevaParcialidad.cantidad}
                        onChange={(e) => setNuevaParcialidad(prev => ({ ...prev, cantidad: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary focus:border-primary"
                        placeholder="0"
                        min="1"
                      />
                    </div>
                  </div>
                  <div className="mt-3">
                    <label className="block text-xs text-gray-600 mb-1">Notas (opcional)</label>
                    <input
                      type="text"
                      value={nuevaParcialidad.notas}
                      onChange={(e) => setNuevaParcialidad(prev => ({ ...prev, notas: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary focus:border-primary"
                      placeholder="Ej: Entrega parcial según factura #123"
                      maxLength={200}
                    />
                  </div>
                  
                  {/* Campo de motivo de override - solo visible cuando se requiere Y usuario tiene permiso */}
                  {requiereOverride && puede.overrideSobreentrega && (
                    <div className="mt-3">
                      <label className="block text-xs text-red-600 mb-1 font-semibold">
                        Motivo de sobre-entrega * (mín. 10 caracteres)
                      </label>
                      <textarea
                        value={motivoOverride}
                        onChange={(e) => setMotivoOverride(e.target.value)}
                        className="w-full px-3 py-2 border border-red-300 rounded-lg text-sm focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50"
                        placeholder="Ej: Sobre-entrega autorizada por Director de Farmacia según oficio OF-2024-XXX debido a ajuste de contrato..."
                        rows={2}
                        maxLength={500}
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        {motivoOverride.length}/500 caracteres (mínimo 10)
                      </p>
                    </div>
                  )}
                  
                  {/* Botón de submit - cambia según si es override o no */}
                  {requiereOverride ? (
                    <div className="mt-3 flex gap-2">
                      <button
                        onClick={() => {
                          setRequiereOverride(false);
                          setMotivoOverride('');
                          setInfoContratoCumplido(null);
                        }}
                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100"
                      >
                        Cancelar
                      </button>
                      {/* P0-2 FIX: Botón de override solo visible si tiene permiso */}
                      {puede.overrideSobreentrega && (
                        <button
                          onClick={() => solicitarConfirmacionEntrega(true)}
                          disabled={loadingParcialidades || !nuevaParcialidad.fecha_entrega || !nuevaParcialidad.cantidad || motivoOverride.trim().length < 10}
                          className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                          {loadingParcialidades ? (
                            <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                          ) : (
                            <>
                              <FaExclamationTriangle className="text-sm" />
                              Autorizar Sobre-entrega
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  ) : (
                    <button
                      onClick={() => solicitarConfirmacionEntrega(false)}
                      disabled={loadingParcialidades || !nuevaParcialidad.fecha_entrega || !nuevaParcialidad.cantidad}
                      className="mt-3 w-full px-4 py-2 bg-primary text-white rounded-lg hover:bg-[#6B1839] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {loadingParcialidades ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                      ) : (
                        <>
                          <FaPlus className="text-sm" />
                          Registrar Entrega
                        </>
                      )}
                    </button>
                  )}
                </div>
              )}
            </div>
            
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end">
              <button
                onClick={() => {
                  setShowParcialidadesModal(false);
                  setSelectedLoteParcialidades(null);
                  setParcialidadesData({ parcialidades: [], resumen: {}, contrato_lote: {} });
                }}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* ISS-SEC: Modal de confirmación para registrar entrega (doble confirmación) */}
      {confirmarEntrega.show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60]">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
            <div className="bg-gradient-to-r from-primary to-[#6B1839] text-white px-6 py-4">
              <h3 className="text-lg font-bold flex items-center gap-2">
                <FaBoxes /> Confirmar Registro de Entrega
              </h3>
            </div>
            
            <div className="p-6 space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm text-blue-800 font-medium mb-2">
                  ¿Está seguro de registrar esta entrega?
                </p>
                <p className="text-xs text-blue-600">
                  Esta acción sumará unidades al inventario del lote.
                </p>
              </div>
              
              {/* Resumen de la entrega */}
              <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Lote:</span>
                  <span className="font-semibold">{selectedLoteParcialidades?.numero_lote}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Producto:</span>
                  <span className="font-semibold truncate max-w-[200px]">
                    {selectedLoteParcialidades?.producto_nombre}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Fecha de entrega:</span>
                  <span className="font-semibold">
                    {nuevaParcialidad.fecha_entrega ? new Date(nuevaParcialidad.fecha_entrega).toLocaleDateString('es-MX') : '-'}
                  </span>
                </div>
                <div className="flex justify-between text-sm border-t pt-2 mt-2">
                  <span className="text-gray-600">Cantidad a registrar:</span>
                  <span className="font-bold text-lg text-primary">
                    +{parseInt(nuevaParcialidad.cantidad || 0).toLocaleString()} uds
                  </span>
                </div>
                {nuevaParcialidad.notas && (
                  <div className="text-xs text-gray-500 mt-2">
                    <span className="font-medium">Notas:</span> {nuevaParcialidad.notas}
                  </div>
                )}
              </div>
              
              {/* Advertencia para sobre-entregas */}
              {confirmarEntrega.forceOverride && (
                <div className="bg-red-50 border border-red-300 rounded-lg p-3">
                  <p className="text-sm font-semibold text-red-800 flex items-center gap-2">
                    <FaExclamationTriangle /> Sobre-entrega Autorizada
                  </p>
                  <p className="text-xs text-red-700 mt-1">
                    Esta entrega excede el contrato y quedará registrada en auditoría.
                  </p>
                </div>
              )}
              
              {/* Impacto en inventario */}
              <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                <p className="text-xs text-green-800">
                  <strong>Impacto:</strong> El inventario del lote aumentará en{' '}
                  <span className="font-bold">{parseInt(nuevaParcialidad.cantidad || 0).toLocaleString()}</span> unidades.
                </p>
              </div>
            </div>
            
            <div className="px-6 py-4 border-t bg-gray-50 flex gap-3">
              <button
                onClick={() => setConfirmarEntrega({ show: false, forceOverride: false })}
                className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-100 font-medium"
              >
                Cancelar
              </button>
              <button
                onClick={() => handleAgregarParcialidad(confirmarEntrega.forceOverride)}
                disabled={loadingParcialidades}
                className={`flex-1 px-4 py-2.5 rounded-lg font-medium flex items-center justify-center gap-2 ${
                  confirmarEntrega.forceOverride
                    ? 'bg-red-600 text-white hover:bg-red-700'
                    : 'bg-primary text-white hover:bg-[#6B1839]'
                } disabled:opacity-50`}
              >
                {loadingParcialidades ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                ) : (
                  <>
                    <FaCheck />
                    Confirmar Entrega
                  </>
                )}
              </button>
            </div>
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

export default Lotes;










