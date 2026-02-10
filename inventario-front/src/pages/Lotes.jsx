import { useState, useEffect, useCallback } from 'react';
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
  FaChevronDown
} from 'react-icons/fa';
import { DEV_CONFIG } from '../config/dev';
import PageHeader from '../components/PageHeader';
import { COLORS, SECONDARY_GRADIENT } from '../constants/theme';
import Pagination from '../components/Pagination';
import { LotesSkeleton } from '../components/skeletons';
import { usePermissions } from '../hooks/usePermissions';
import { puedeVerGlobal as checkPuedeVerGlobal, esFarmaciaAdmin as checkEsFarmaciaAdmin } from '../utils/roles';

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
  
  // Permisos específicos para acciones - usar permisos finos del backend
  const esFarmaciaAdmin = checkEsFarmaciaAdmin(user);
  const puede = {
    // Usar permisos finos si existen, sino fallback al rol
    crear: permisos?.crearLote === true || (esFarmaciaAdmin && permisos?.crearLote !== false),
    editar: permisos?.editarLote === true || (esFarmaciaAdmin && permisos?.editarLote !== false),
    eliminar: permisos?.eliminarLote === true || (esFarmaciaAdmin && permisos?.eliminarLote !== false),
    exportar: permisos?.exportarLotes === true || (esFarmaciaAdmin && permisos?.exportarLotes !== false) || (rolPrincipal === 'VISTA' && permisos?.exportarLotes !== false),
    importar: permisos?.importarLotes === true || (esFarmaciaAdmin && permisos?.importarLotes !== false),
    verDocumento: true, // Todos pueden ver
    subirDocumento: permisos?.crearLote === true || (esFarmaciaAdmin && permisos?.crearLote !== false),
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
    cantidad_contrato: '',    // ISS-INV-001: Total según contrato (obligatorio)
    cantidad_inicial: '',      // Se auto-calcula desde cantidad_contrato
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

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      cargarLotes();
    }, 500);

    return () => clearTimeout(delayDebounceFn);
  }, [cargarLotes]);

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
    
    // Validar cantidad del contrato (obligatoria)
    if (!formData.cantidad_contrato || formData.cantidad_contrato.toString().trim() === '') {
      toast.error('La cantidad del contrato es obligatoria');
      return;
    }
    const cantidadContrato = parseInt(formData.cantidad_contrato, 10);
    if (isNaN(cantidadContrato) || cantidadContrato <= 0) {
      toast.error('La cantidad del contrato debe ser un número mayor a cero');
      return;
    }

    // cantidad_inicial: cantidad realmente recibida (puede ser parcial vs contrato)
    const cantidadInicial = parseInt(formData.cantidad_inicial, 10);
    
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
    if (!editingLote && cantidadInicial === 0) {
      toast.error('La cantidad inicial debe ser mayor a cero');
      return;
    }
    
    // Validación: cantidad_inicial no puede superar cantidad_contrato
    if (!editingLote && cantidadInicial > cantidadContrato) {
      toast.error('La cantidad inicial recibida no puede superar la cantidad del contrato');
      return;
    }
    
    // ISS-INV-001: cantidad_contrato ya validada arriba
    let cantContratoFinal = cantidadContrato;
    
    // Parsear precio si existe (campo real: precio_unitario)
    const precioUnitario = formData.precio_unitario ? parseFloat(formData.precio_unitario) : null;
    if (formData.precio_unitario && (isNaN(precioUnitario) || precioUnitario < 0)) {
      toast.error('El precio unitario debe ser un número válido y no negativo');
      return;
    }
    
    setSavingLote(true);
    
    try {
      // NOTA: La presentación es propiedad del PRODUCTO, no del lote
      // El campo presentacion_producto es solo lectura y NO se actualiza desde aquí
      // Si necesita otra presentación, debe crear un nuevo producto
      
      const dataToSend = {
        ...formData,
        cantidad_inicial: cantidadInicial,
        cantidad_contrato: cantContratoFinal,  // ISS-INV-001: Cantidad del contrato
        precio_unitario: precioUnitario,
      };
      
      // Remover presentacion_producto ya que no es campo del modelo Lote
      delete dataToSend.presentacion_producto;
      
      // CANTIDAD INICIAL: Solo se establece al crear, nunca al editar
      // Para reabastecer un lote existente, usar Movimientos → Entrada
      if (!editingLote) {
        dataToSend.cantidad_actual = cantidadInicial;
      } else {
        // En edición, NO enviar cantidad_inicial para evitar inconsistencias
        delete dataToSend.cantidad_inicial;
      }
      // Si no hay centro explícito y el usuario tiene uno asignado, usarlo
      if (!dataToSend.centro && centroUsuario && !puedeVerGlobal) {
        dataToSend.centro = centroUsuario;
      }
      
      // Limpiar campos vacíos para evitar enviar strings vacíos
      // ISS-SEC FIX: EXCEPTO fecha_caducidad que es obligatoria
      Object.keys(dataToSend).forEach(key => {
        if (dataToSend[key] === '' && key !== 'fecha_caducidad') {
          dataToSend[key] = null;
        }
      });
      
      if (editingLote) {
        await lotesAPI.update(editingLote.id, dataToSend);
        toast.success('Lote actualizado correctamente');
      } else {
        await lotesAPI.create(dataToSend);
        toast.success('Lote creado correctamente');
      }
      
      setShowModal(false);
      resetForm();
      cargarLotes();
    } catch (error) {
      // Extraer mensajes de error detallados del backend
      const respData = error.response?.data;
      let errorMsg = 'Error al guardar lote';
      
      if (respData) {
        // Priorizar detalles específicos de validación
        if (respData.detalles) {
          const detalles = respData.detalles;
          // detalles puede ser un objeto { campo: ["msg"] } o { campo: "msg" }
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
      console.error(error);
    } finally {
      setSavingLote(false);
    }
  };

  const handleEdit = (lote) => {
    setEditingLote(lote);
    // Obtener presentación del producto si está disponible
    const productoInfo = lote.producto_info || {};
    const presentacionProducto = productoInfo.presentacion || lote.presentacion || '';
    setFormData({
      producto: lote.producto,
      presentacion_producto: presentacionProducto,
      numero_lote: lote.numero_lote,
      fecha_fabricacion: lote.fecha_fabricacion || '',
      fecha_caducidad: lote.fecha_caducidad,
      cantidad_inicial: lote.cantidad_inicial,
      cantidad_contrato: lote.cantidad_contrato || '',  // ISS-INV-001: Cantidad del contrato
      precio_unitario: lote.precio_unitario || lote.precio_compra || '',
      numero_contrato: lote.numero_contrato || '',
      marca: lote.marca || '',
      ubicacion: lote.ubicacion || '',
      centro: lote.centro || ''
    });
    setShowModal(true);
  };

  const handleDelete = async (id, lote) => {
    if (!puede.eliminar) {
      toast.error('No tiene permisos para eliminar lotes');
      return;
    }
    
    if (actionLoading === id) return; // Evitar múltiples clics
    
    const confirmMsg = `¿Está seguro de DESACTIVAR el lote ${lote?.numero_lote || id}?\n\n` +
      `⚠️ El lote quedará marcado como eliminado (soft delete).\n` +
      `Nota: Esta acción es reversible por un administrador.`;
    
    if (!window.confirm(confirmMsg)) return;
    
    try {
      setActionLoading(id);
      await lotesAPI.delete(id);
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
    } finally {
      setActionLoading(null);
    }
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

  const handleEliminarDocumento = async (docId) => {
    if (!puede.subirDocumento) {
      toast.error('No tiene permisos para eliminar documentos');
      return;
    }
    
    if (!window.confirm('¿Está seguro de eliminar el documento?')) return;
    
    try {
      setActionLoading(selectedLoteDoc.id);
      await lotesAPI.eliminarDocumento(selectedLoteDoc.id, docId);
      toast.success('Documento eliminado');
      // Recargar documentos del modal
      const response = await lotesAPI.listarDocumentos(selectedLoteDoc.id);
      setSelectedLoteDoc(prev => ({
        ...prev,
        documentos_cargados: response.data.documentos || [],
        tiene_documentos: (response.data.documentos || []).length > 0
      }));
      cargarLotes();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al eliminar documento');
    } finally {
      setActionLoading(null);
    }
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
      precio_unitario: '',
      numero_contrato: '',
      marca: '',
      ubicacion: '',
      centro: ''
    });
    setEditingLote(null);
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
      // Forzar filtro de centro para usuarios sin permisos globales
      const centroParaExportar = !puedeVerGlobal ? (centroUsuario?.toString() || filtroCentro) : filtroCentro;
      if (centroParaExportar) params.centro = centroParaExportar;
      
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
      // Forzar filtro de centro para usuarios sin permisos globales
      const centroParaExportar = !puedeVerGlobal ? (centroUsuario?.toString() || filtroCentro) : filtroCentro;
      if (centroParaExportar) params.centro = centroParaExportar;
      
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
  
  try {
    setImportLoading(true);
    const response = await lotesAPI.importar(formData);
    const resumen = response.data?.resumen || response.data || {};
    const errores = response.data?.errores || [];

    // Función para traducir errores técnicos a mensajes amigables
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
      
      return str;
    };

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
    toast.error(error.response?.data?.error || 'Error al importar lotes');
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
        subtitle={`Total: ${totalLotes} lotes | Página ${currentPage} de ${totalPages}`}
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
                <label className="text-xs font-semibold text-theme-primary-hover">Búsqueda</label>
                <div
                  className="mt-1 flex items-center rounded-lg border px-3 py-2 focus-within:ring-2 border-theme-primary"
                >
                  <FaFilter className="mr-2 text-gray-400" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full border-none bg-transparent text-sm focus:outline-none"
                    placeholder="Buscar por número de lote, producto..."
                  />
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
              <col className="w-20" /> {/* Acciones */}
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
                  <td colSpan="8" className="text-center py-8 text-gray-500">
                    No hay lotes registrados
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
                      <div>{new Date(lote.fecha_caducidad).toLocaleDateString()}</div>
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
                    {/* ISS-INV-001: Columna de Inventario mejorada con info de contrato */}
                    <td className="px-3 py-2 text-xs">
                      <div className={`font-bold text-base ${lote.cantidad_actual === 0 ? 'text-red-600' : 'text-green-700'}`}>
                        {lote.cantidad_actual}
                      </div>
                      {/* Mostrar "de X" con la referencia correcta: contrato si existe, sino inicial */}
                      <div className="text-gray-500">
                        de {lote.cantidad_contrato || lote.cantidad_inicial}
                      </div>
                      {/* Mostrar desglose si contrato difiere de inicial (entrega parcial) */}
                      {lote.cantidad_contrato && lote.cantidad_contrato !== lote.cantidad_inicial && (
                        <div className="mt-1 text-xs">
                          <div className="text-blue-600" title={`Contrato: ${lote.cantidad_contrato} | Recibido: ${lote.cantidad_inicial}`}>
                            📄 Contrato: {lote.cantidad_contrato}
                          </div>
                          <div className="text-indigo-600" title={`Recibido inicialmente: ${lote.cantidad_inicial} unidades`}>
                            📦 Recibido: {lote.cantidad_inicial}
                          </div>
                          {lote.cantidad_contrato > lote.cantidad_inicial && (
                            <div className="text-orange-600" title={`Pendiente por recibir: ${lote.cantidad_contrato - lote.cantidad_inicial} unidades`}>
                              ⏳ Pendiente: {lote.cantidad_contrato - lote.cantidad_inicial}
                            </div>
                          )}
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
              
                <div className="grid grid-cols-2 gap-4">
                  {/* ISS-INV-001: Cantidad del Contrato (OBLIGATORIO) */}
                  <div>
                    <label className="block text-sm font-bold mb-2 text-theme-primary-hover">
                      CANTIDAD CONTRATO <span className="text-red-600">*</span>
                    </label>
                    <input
                      type="number"
                      min="1"
                      value={formData.cantidad_contrato}
                      onChange={(e) => !editingLote && setFormData({...formData, cantidad_contrato: e.target.value})}
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
                      required
                      disabled={editingLote}
                      readOnly={editingLote}
                      placeholder="Total según contrato"
                    />
                    <p className="text-xs text-gray-500 italic mt-1">
                      {editingLote 
                        ? 'No editable. Cantidad total establecida por contrato' 
                        : 'Total de unidades que establece el contrato de adquisición'}
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
                      placeholder="Cantidad recibida"
                    />
                    <p className="text-xs text-gray-500 italic mt-1">
                      {editingLote 
                        ? 'No editable. Use Movimientos → Entrada para reabastecer' 
                        : 'Unidades realmente recibidas (puede ser parcial del contrato)'}
                    </p>
                  </div>
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

                {/* Fecha de Fabricación y Ubicación */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-bold mb-2 text-theme-primary-hover">
                      FECHA DE FABRICACIÓN {editingLote?.tiene_movimientos && <span className="text-red-500 text-xs">🔒</span>}
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
                      disabled={editingLote?.tiene_movimientos}
                      readOnly={editingLote?.tiene_movimientos}
                      max={new Date().toISOString().split('T')[0]}
                    />
                    <p className="text-xs text-gray-500 italic mt-1">
                      {editingLote?.tiene_movimientos ? '🔒 No editable' : 'Opcional - Fecha de manufactura del lote'}
                    </p>
                  </div>
                  
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
                </div>

                {/* CAMPOS DE TRAZABILIDAD DE CONTRATOS - Solo visible para ADMIN y FARMACIA */}
                {puedeVerContrato && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-bold mb-2 text-theme-primary-hover">
                      NÚMERO DE CONTRATO {editingLote?.tiene_movimientos && <span className="text-orange-500 text-xs">🔒</span>}
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
                      placeholder="Ej: CONT-2025-001"
                      maxLength={100}
                    />
                    <p className="text-xs text-gray-400 mt-1">
                      {editingLote?.tiene_movimientos 
                        ? '🔒 No editable - Campo auditable con movimientos' 
                        : 'Para trazabilidad de adquisiciones'}
                    </p>
                  </div>

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

      {/* Modal Importar */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl w-full max-w-md overflow-hidden shadow-2xl">
            <div className="px-6 py-4 bg-theme-gradient rounded-t-2xl flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">Importar Lotes desde Excel</h2>
              <button onClick={() => setShowImportModal(false)} className="text-white/70 hover:text-white">
                <FaTimes size={24} />
              </button>
            </div>
            
            <div className="p-6">
              <div className="mb-4">
                <p className="text-sm text-gray-600 mb-2">
                  El archivo debe contener las siguientes columnas:
                </p>
                <ul className="text-sm text-gray-600 list-disc list-inside space-y-1">
                  <li><strong>Clave Producto</strong> - Requerido</li>
                  <li><strong>Nombre Producto</strong> - Requerido (debe coincidir con clave)</li>
                  <li><strong>Número Lote</strong> - Requerido</li>
                  <li><strong>Fecha Caducidad</strong> (YYYY-MM-DD) - Requerido</li>
                  <li><strong>Cantidad Inicial</strong> - Requerido (unidades recibidas)</li>
                  <li><strong className="text-blue-600">Cantidad Contrato</strong> - Opcional (total según contrato)</li>
                  <li>Fecha Fabricación (opcional, YYYY-MM-DD)</li>
                  <li>Precio Unitario (opcional, default = 0)</li>
                  <li>Número Contrato (opcional)</li>
                  <li>Marca (opcional)</li>
                </ul>
                <div className="mt-3 p-2 bg-blue-50 rounded-lg border border-blue-200">
                  <p className="text-xs text-blue-700 font-medium">📦 Entregas Parciales:</p>
                  <p className="text-xs text-blue-600 mt-1">
                    Si el contrato dice 100 pero llegaron 80: use Cantidad Inicial=80, Cantidad Contrato=100.
                    El sistema calculará automáticamente las unidades pendientes.
                  </p>
                  <p className="text-xs text-blue-600 mt-1">
                    Para completar entregas, reimporte con mismos datos clave y el sistema sumará las cantidades.
                  </p>
                </div>
                <p className="text-xs text-amber-600 mt-2">
                  Nota: Clave y Nombre del producto deben coincidir con el catálogo. Descargue la plantilla para ver el formato correcto.
                </p>
                {/* Botón de descarga de plantilla */}
                <button
                  onClick={handleDescargarPlantilla}
                  className="mt-3 flex items-center gap-2 text-sm text-theme-primary hover:text-theme-secondary transition"
                >
                  <FaDownload />
                  Descargar plantilla de ejemplo
                </button>
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">
                  Seleccionar archivo Excel (.xlsx, .xls)
                </label>
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleImportar}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-theme-primary disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={importLoading}
                />
              </div>
              
              {importLoading && (
                <div className="mb-4 text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-4 border-t-transparent spinner-institucional mx-auto"></div>
                  <p className="text-sm text-gray-600 mt-2">Procesando archivo...</p>
                </div>
              )}
              
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setShowImportModal(false)}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={importLoading}
                >
                  Cerrar
                </button>
              </div>
            </div>
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
                          {doc.fecha_documento ? ` • ${new Date(doc.fecha_documento).toLocaleDateString()}` : ''}
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
    </div>
  );
};

export default Lotes;










