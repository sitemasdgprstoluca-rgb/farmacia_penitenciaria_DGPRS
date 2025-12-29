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

  FaLayerGroup,

  FaCalendarAlt

} from 'react-icons/fa';

import { toast } from 'react-hot-toast';

import { productosAPI } from '../services/api';

import { DEV_CONFIG } from '../config/dev';

import { usePermissions } from '../hooks/usePermissions';

import { ProtectedButton } from '../components/ProtectedAction';
import Pagination from '../components/Pagination';
import { ProductosSkeleton } from '../components/skeletons';
import LimpiarInventario from '../components/LimpiarInventario';

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

      className="px-3 py-1 rounded-full text-xs font-semibold"

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

      className="px-3 py-1 rounded-full text-xs font-semibold"

    >

      {label[nivel] || nivel || 'N/D'}

    </span>

  );

};



const DEFAULT_FORM = {
  clave: '',
  nombre: '',
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

const Productos = () => {

  const { user, permisos, getRolPrincipal } = usePermissions();
  
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
  const [actionLoading, setActionLoading] = useState(null); // ID del producto en acción (toggle/delete)

  const [error, setError] = useState(null);

  const [showModal, setShowModal] = useState(false);

  const fileInputRef = useRef(null);

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
    if (data.unidad_medida && !UNIDADES.includes(data.unidad_medida)) {
      errores.unidad_medida = 'Seleccione una unidad válida';
    }

    // Validación adicional local: categoria debe ser de la lista
    if (data.categoria && !CATEGORIAS.includes(data.categoria)) {
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

        await productosAPI.create(dataToSend, hasImage);

        toast.success('Producto creado correctamente');

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



  const handleDelete = async (producto) => {

    if (!puede.eliminar) return;
    if (actionLoading === producto.id) return; // Evitar clics repetidos

    const confirm = window.confirm(
      `¿Confirma ELIMINAR DEFINITIVAMENTE el producto ${producto.clave}?\n\n` +
      `⚠️ Esta acción no se puede deshacer.\n` +
      `Nota: Si el producto tiene lotes asociados, no podrá eliminarse.`
    );

    if (!confirm) return;

    setActionLoading(producto.id);

    try {

      if (isDevSession()) {

        mockProductosRef.current = mockProductosRef.current.filter((item) => item.id !== producto.id);

        toast.success('Producto eliminado (modo demo)');

        applyMockProductos();

        setActionLoading(null); // Limpiar antes de return

        return;

      }

      await productosAPI.delete(producto.id);

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

    } finally {
      setActionLoading(null);
    }

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
      const resumen = response.data?.resumen || {};
      const errores = response.data?.errores || [];

      toast.success(
        `Importación completada. Creados: ${resumen.creados || 0} | Actualizados: ${resumen.actualizados || 0} | Total: ${resumen.total_procesados || 0}`,
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



    return (

      <div className="overflow-x-auto rounded-lg border border-gray-200">

        <table className="min-w-full divide-y divide-gray-200">

          <thead className="bg-theme-gradient">

            <tr>

              {[

                '#',

                'Clave',

                'Nombre',

                'Presentación',

                'Inventario',

                'Lotes',

                'Inv. Mínimo',

                'Estado',

                'Nivel Inv.',

                ...(puede.tieneAcciones ? ['Acciones'] : []),

              ].map((col) => (

                <th key={col} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white">

                  {col}

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

                <td className="px-3 py-3 text-sm font-semibold text-gray-500">{consecutivo}</td>

                <td className="px-4 py-3 text-sm font-semibold text-gray-800">{producto.clave || '-'}</td>

                <td className="px-4 py-3 text-sm text-gray-600">{producto.nombre}</td>

                <td className="px-4 py-3 text-sm text-gray-600">{producto.presentacion || producto.unidad_medida || <span className="text-gray-400 italic text-xs">-</span>}</td>

                <td className="px-4 py-3 text-sm">{formatInventario(producto)}</td>

                <td className="px-4 py-3 text-sm">
                  <button
                    type="button"
                    onClick={() => verLotesProducto(producto)}
                    className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors cursor-pointer"
                    title="Ver detalle de lotes"
                  >
                    <FaLayerGroup className="text-xs" />
                    <span className="font-semibold">{numLotes !== null ? numLotes : '?'}</span>
                  </button>
                </td>

                <td className="px-4 py-3 text-sm">{producto.stock_minimo}</td>

                <td className="px-4 py-3 text-sm">{renderEstadoBadge(estadoInventario.label, estadoInventario.activo)}</td>

                <td className="px-4 py-3 text-sm">{renderStockBadge(nivelStock)}</td>

                {puede.tieneAcciones && (
                <td className="px-4 py-3 text-sm">

                  <div className="flex items-center gap-3">

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

    );

  };



  return (

    <div className="space-y-6 p-4 sm:p-6">

      <div

        className="rounded-2xl p-6 text-white shadow-lg bg-theme-gradient"

      >

        <div className="flex flex-wrap items-center justify-between gap-4">

          <div className="flex items-center gap-4">

            <div className="bg-white/20 p-3 rounded-full">

              <FaBoxOpen size={24} />

            </div>

            <div>

              <h1 className="text-2xl font-bold">Gestión de Productos</h1>

              <p className="text-white/80 text-sm">Total activos: {totalProductos}</p>

            </div>

          </div>

          {filtrosActivos > 0 && (

            <span className="bg-white/20 px-4 py-1 rounded-full text-sm font-semibold">

              {filtrosActivos} filtros activos

            </span>

          )}

          <div className="flex flex-wrap gap-3">
              <ProtectedButton
                permission="exportarProductos"
                type="button"
                onClick={handleExportar}
                disabled={exportLoading}
                className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-50 disabled:cursor-not-allowed bg-theme-gradient"
              >
                {exportLoading ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent inline-block" />
                ) : (
                  <FaDownload />
                )}
                {exportLoading ? 'Exportando...' : 'Exportar'}
              </ProtectedButton>

              <ProtectedButton
                permission="importarProductos"
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={importLoading}
                className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-50 disabled:cursor-not-allowed bg-theme-gradient"
              >
                {importLoading ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent inline-block" />
                ) : (
                  <FaFileUpload />
                )}
                {importLoading ? 'Importando...' : 'Importar'}
              </ProtectedButton>
              
              {/* Botón de descarga de plantilla */}
              <ProtectedButton
                permission="importarProductos"
                type="button"
                onClick={handleDescargarPlantilla}
                className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-theme-primary bg-white/90 hover:bg-white transition"
                title="Descargar plantilla Excel para importación"
              >
                <FaDownload />
                Plantilla
              </ProtectedButton>
              
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls"
                className="hidden"
                style={{ display: 'none' }}
                onChange={handleImportar}
              />

              <ProtectedButton
                permission="crearProducto"
                type="button"
                onClick={() => openModal()}
                className="flex items-center gap-2 rounded-full bg-white/90 px-4 py-2 text-sm font-bold hover:bg-white text-theme-primary"
              >
                <FaPlus />
                Nuevo Producto
              </ProtectedButton>
              
              {/* Botón de limpieza de inventario - SOLO SUPERUSUARIOS */}
              {permisos?.isSuperuser && (
                <LimpiarInventario onLimpiezaCompletada={() => fetchProductos()} />
              )}
          </div>

        </div>

      </div>

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

      <div className="mb-4 flex justify-end">

        <button

          type="button"

          onClick={toggleFiltersMenu}

          aria-expanded={showFiltersMenu}

          aria-haspopup="true"

          className="flex items-center gap-2 rounded-full border border-gray-200 bg-white/90 px-4 py-2 text-sm font-semibold text-gray-700 shadow-sm transition hover:bg-white"

        >

          <FaFilter className="text-theme-primary" />

          {showFiltersMenu ? 'Ocultar filtros' : 'Mostrar filtros'}

          <FaChevronDown className={`transition ${showFiltersMenu ? 'rotate-180' : ''}`} />

        </button>

      </div>



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

                    value={filters.search}

                    onChange={(e) => handleFilterChange('search', e.target.value)}

                    className="w-full border-none bg-transparent text-sm focus:outline-none"

                    placeholder="Buscar por clave o descripción"

                  />

                </div>

              </div>

              <div>

                <label className="text-xs font-semibold text-theme-primary-hover">Estado</label>

                <select

                  value={puede.verSoloActivos ? 'activo' : filters.estado}

                  disabled={puede.verSoloActivos}

                  onChange={(e) => handleFilterChange('estado', e.target.value)}

                  className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 border-theme-primary"

                >

                  <option value="">Todos</option>

                  <option value="activo">Activos</option>

                  <option value="inactivo">Inactivos</option>

                </select>

                {puede.verSoloActivos && <p className="mt-1 text-xs text-gray-500">Su rol solo permite ver activos.</p>}

              </div>

              <div>

                <label className="text-xs font-semibold text-theme-primary-hover">Unidad</label>

                <select

                  value={filters.unidad}

                  onChange={(e) => handleFilterChange('unidad', e.target.value)}

                  className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 border-theme-primary"

                >

                  <option value="">Todas</option>

                  {UNIDADES.map((unidad) => (

                    <option key={unidad} value={unidad}>

                      {unidad}

                    </option>

                  ))}

                </select>

              </div>

              <div>

                <label className="text-xs font-semibold text-theme-primary-hover">Nivel Inventario</label>

                <select

                  value={filters.stock}

                  onChange={(e) => handleFilterChange('stock', e.target.value)}

                  className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 border-theme-primary"

                >

                  {NIVELES_INVENTARIO.map((nivel) => (

                    <option key={nivel.value} value={nivel.value}>

                      {nivel.label}

                    </option>

                  ))}

                </select>

              </div>

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

      {/* Validación explícita de puede.ver para tabla y paginación */}
      {puede.ver ? (
        <>
          {renderTabla()}

          <Pagination
            page={currentPage}
            totalPages={totalPages}
            totalItems={totalProductos}
            pageSize={PAGE_SIZE}
            onPageChange={setCurrentPage}
          />
        </>
      ) : (
        <div className="py-12 text-center bg-white rounded-lg shadow">
          <p className="text-gray-500">No tienes permisos para ver productos.</p>
        </div>
      )}


      {showModal && (

        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">

          <div className="w-full max-w-3xl rounded-2xl bg-white shadow-2xl max-h-[90vh] overflow-y-auto">

            <div

              className="flex items-center justify-between rounded-t-2xl px-6 py-4 text-white bg-theme-gradient sticky top-0"

            >

              <div>

                <h2 className="text-xl font-bold">{editingProduct ? 'Editar producto' : 'Nuevo producto'}</h2>

                <p className="text-sm text-white/80">Complete los campos obligatorios (*)</p>

              </div>

              <span className="text-sm font-semibold">{editingProduct ? editingProduct.clave : 'Nuevo'}</span>

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

            <form onSubmit={handleSubmit} className="space-y-4 px-6 py-6">

              {/* Clave y Descripción */}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">

                <div>

                  <label className="text-xs font-semibold text-theme-primary-hover">Clave *</label>

                  <input

                    type="text"

                    value={formData.clave}

                    onChange={(e) => setFormData({ ...formData, clave: e.target.value.toUpperCase() })}

                    maxLength={50}

                    placeholder="Ej: MED-001"

                    className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 ${formErrors.clave ? 'border-red-500' : 'border-theme-primary'}`}

                  />

                  {formErrors.clave && <p className="text-xs text-red-600">{formErrors.clave}</p>}

                </div>

                <div>

                  <label className="text-xs font-semibold text-theme-primary-hover">Nombre *</label>

                  <input

                    type="text"

                    value={formData.nombre}

                    onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}

                    maxLength={500}

                    placeholder="Ej: Paracetamol 500mg Tabletas"

                    className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 ${formErrors.nombre ? 'border-red-500' : 'border-theme-primary'}`}

                  />

                  {formErrors.nombre && <p className="text-xs text-red-600">{formErrors.nombre}</p>}

                </div>

              </div>

              {/* Unidad y Stock Mínimo */}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>

                  <label className="text-xs font-semibold text-theme-primary-hover">Unidad de Medida *</label>

                  <select

                    value={formData.unidad_medida}

                    onChange={(e) => setFormData({ ...formData, unidad_medida: e.target.value })}

                    className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 ${formErrors.unidad_medida ? 'border-red-500' : 'border-theme-primary'}`}

                  >

                    {UNIDADES.map((unidad) => (

                      <option key={unidad} value={unidad}>                        {unidad}

                      </option>

                    ))}

                  </select>

                  {formErrors.unidad_medida && <p className="text-xs text-red-600">{formErrors.unidad_medida}</p>}

                </div>

                <div>

                  <label className="text-xs font-semibold text-theme-primary-hover">Stock mínimo *</label>

                  <input

                    type="number"

                    min="0"

                    step="1"

                    value={formData.stock_minimo}

                    onChange={(e) => setFormData({ ...formData, stock_minimo: e.target.value })}

                    className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 ${formErrors.stock_minimo ? 'border-red-500' : 'border-theme-primary'}`}

                  />

                  {formErrors.stock_minimo && <p className="text-xs text-red-600">{formErrors.stock_minimo}</p>}

                </div>

              </div>

              {/* Categoría y Descripción */}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <label className="text-xs font-semibold text-theme-primary-hover">Categoría *</label>
                  <select
                    value={formData.categoria}
                    onChange={(e) => setFormData({ ...formData, categoria: e.target.value })}
                    className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 ${formErrors.categoria ? 'border-red-500' : 'border-theme-primary'}`}
                  >
                    {CATEGORIAS.map((cat) => (
                      <option key={cat} value={cat}>
                        {cat.charAt(0).toUpperCase() + cat.slice(1).replace('_', ' ')}
                      </option>
                    ))}
                  </select>
                  {formErrors.categoria && <p className="text-xs text-red-600">{formErrors.categoria}</p>}
                </div>
                <div>
                  <label className="text-xs font-semibold text-theme-primary-hover">Descripción</label>
                  <input
                    type="text"
                    value={formData.descripcion}
                    onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                    maxLength={500}
                    placeholder="Descripción adicional del producto"
                    className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 border-theme-primary"
                  />
                </div>
              </div>

              {/* Datos Farmacéuticos (desplegable) */}
              <details className="rounded-lg border border-gray-200 bg-gray-50">
                <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-theme-primary-hover hover:bg-gray-100">
                  📋 Datos Farmacéuticos (opcional)
                </summary>
                <div className="space-y-4 px-4 pb-4 pt-2">
                  {/* Sustancia Activa y Presentación */}
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div>
                      <label className="text-xs font-semibold text-gray-600">Sustancia Activa</label>
                      <input
                        type="text"
                        value={formData.sustancia_activa}
                        onChange={(e) => setFormData({ ...formData, sustancia_activa: e.target.value })}
                        maxLength={200}
                        placeholder="Ej: Paracetamol"
                        className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 border-gray-300"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-gray-600">Presentación</label>
                      <input
                        type="text"
                        value={formData.presentacion}
                        onChange={(e) => setFormData({ ...formData, presentacion: e.target.value })}
                        maxLength={200}
                        placeholder="Ej: Tabletas, Cápsulas, Jarabe"
                        className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 border-gray-300"
                      />
                    </div>
                  </div>
                  {/* Concentración y Vía de Administración */}
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div>
                      <label className="text-xs font-semibold text-gray-600">Concentración</label>
                      <input
                        type="text"
                        value={formData.concentracion}
                        onChange={(e) => setFormData({ ...formData, concentracion: e.target.value })}
                        maxLength={100}
                        placeholder="Ej: 500mg, 10ml"
                        className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 border-gray-300"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-gray-600">Vía de Administración</label>
                      <select
                        value={formData.via_administracion}
                        onChange={(e) => setFormData({ ...formData, via_administracion: e.target.value })}
                        className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 border-gray-300"
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
                  {/* Checkboxes: Requiere Receta y Es Controlado */}
                  <div className="flex flex-wrap gap-6">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.requiere_receta}
                        onChange={(e) => setFormData({ ...formData, requiere_receta: e.target.checked })}
                        className="h-4 w-4"
                      />
                      <span className="text-sm text-gray-700">Requiere Receta</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.es_controlado}
                        onChange={(e) => setFormData({ ...formData, es_controlado: e.target.checked })}
                        className="h-4 w-4"
                      />
                      <span className="text-sm text-gray-700">Es Controlado</span>
                    </label>
                  </div>
                </div>
              </details>

              {/* Checkbox: activo */}
              <div className="flex items-center gap-2 rounded-lg border px-4 py-3 border-theme-primary">
                <input
                  type="checkbox"
                  checked={formData.activo}
                  onChange={(e) => setFormData({ ...formData, activo: e.target.checked })}
                  className="h-4 w-4"
                />
                <span className="text-sm font-semibold text-gray-700">Producto Activo</span>
              </div>

              {/* Campo de imagen del producto - DESHABILITADO */}
              <div>
                <label className="text-xs font-semibold text-gray-400">Imagen del producto</label>
                <div className="mt-1 flex items-center gap-4 opacity-60 cursor-not-allowed">
                  <div className="flex items-center gap-2 rounded-lg border border-dashed border-gray-300 px-4 py-3 bg-gray-50">
                    <FaFileUpload className="text-gray-400" />
                    <span className="text-sm text-gray-400">Seleccionar imagen</span>
                  </div>
                </div>
                <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-xs text-amber-700 flex items-center gap-1">
                    <span className="font-semibold">⏳ Funcionalidad pendiente:</span>
                    En espera de mejora de almacenamiento para esta funcionalidad.
                  </p>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">

                <button 
                  type="button" 
                  onClick={closeModal} 
                  disabled={savingProduct}
                  className="rounded-lg border px-4 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >

                  Cancelar

                </button>

                <button

                  type="submit"
                  disabled={savingProduct}

                  className="rounded-lg px-5 py-2 text-sm font-semibold text-white disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 bg-theme-gradient"

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

        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">

          <div className="w-full max-w-3xl rounded-2xl bg-white shadow-2xl">

            <div

              className="flex items-center justify-between rounded-t-2xl px-6 py-4 text-white bg-theme-gradient"

            >

              <div>

                <h3 className="text-xl font-bold">Historial de auditoría</h3>

                <p className="text-sm text-white/80">

                  {(auditoriaData?.producto?.clave) || 'Producto'} | {auditoriaData?.producto?.nombre || ''}

                </p>

              </div>

              <button type="button" onClick={cerrarAuditoria} className="text-sm font-semibold text-white/90 hover:text-white">

                Cerrar ✓

              </button>

            </div>

            <div className="max-h-[60vh] overflow-y-auto px-6 py-5 space-y-4">

              {auditoriaLoading ? (

                <p className="text-sm text-gray-500">Cargando historial...</p>

              ) : auditoriaData?.historial?.length ? (

                auditoriaData.historial.map((log) => (

                  <div key={log.id} className="rounded-xl border border-gray-100 bg-gray-50 px-4 py-3">

                    <div className="flex flex-wrap items-center justify-between gap-2">

                      <div>

                        <p className="text-sm font-semibold text-gray-800">{log.accion_display}</p>

                        <p className="text-xs text-gray-500">

                          Responsable: {log.usuario_nombre || 'Sistema'}

                        </p>

                      </div>

                      <span className="text-xs font-semibold text-gray-500">

                        {formatFecha(log.created_at || log.fecha)}

                      </span>

                    </div>

                    {log.cambios && Object.keys(log.cambios).length > 0 && (

                      <pre className="mt-2 overflow-x-auto rounded bg-white p-2 text-xs text-gray-600">

                        {JSON.stringify(log.cambios, null, 2)}

                      </pre>

                    )}

                  </div>

                ))

              ) : (

                <p className="text-sm text-gray-500">No hay cambios registrados para este producto.</p>

              )}

            </div>

          </div>

        </div>

      )}

      {/* Modal de Lotes del Producto */}
      {lotesModalVisible && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-3xl rounded-2xl bg-white shadow-2xl max-h-[85vh] overflow-hidden">
            <div
              className="flex items-center justify-between rounded-t-2xl px-6 py-4 text-white bg-theme-gradient sticky top-0"
            >
              <div>
                <h3 className="text-xl font-bold flex items-center gap-2">
                  <FaLayerGroup />
                  Lotes del Producto
                </h3>
                <p className="text-sm text-white/80">
                  {lotesModalData?.producto?.clave} - {lotesModalData?.producto?.nombre}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold">{lotesModalData?.total_lotes || 0} lotes</p>
                <p className="text-xs text-white/80">Stock total: {lotesModalData?.total_stock || 0} {lotesModalData?.producto?.unidad_medida}</p>
              </div>
            </div>
            <div className="overflow-y-auto max-h-[60vh]">
              {lotesModalLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent"></div>
                  <span className="ml-3 text-gray-600">Cargando lotes...</span>
                </div>
              ) : lotesModalData?.lotes?.length ? (
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Lote</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Cantidad</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Caducidad</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Días Rest.</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Estado</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Ubicación</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-100">
                    {lotesModalData.lotes.map((lote, idx) => {
                      // Semáforo de caducidad
                      const semaforoConfig = {
                        vencido: { bg: 'bg-red-100', text: 'text-red-800', label: 'VENCIDO', icon: '🔴' },
                        critico: { bg: 'bg-orange-100', text: 'text-orange-800', label: 'CRÍTICO', icon: '🟠' },
                        proximo: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'PRÓXIMO', icon: '🟡' },
                        normal: { bg: 'bg-green-100', text: 'text-green-800', label: 'OK', icon: '🟢' },
                        sin_fecha: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'S/F', icon: '⚪' },
                      };
                      const semaforo = semaforoConfig[lote.alerta_caducidad] || semaforoConfig.normal;
                      
                      return (
                        <tr
                          key={lote.id}
                          className={`transition hover:bg-gray-50 ${lote.alerta_caducidad === 'vencido' ? 'bg-red-50' : lote.alerta_caducidad === 'critico' ? 'bg-orange-50' : ''}`}
                        >
                          <td className="px-4 py-3 text-sm font-mono font-semibold text-gray-800">
                            {lote.numero_lote}
                          </td>
                          <td className="px-4 py-3 text-sm font-bold text-gray-900">
                            {lote.cantidad_actual}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600">
                            <div className="flex items-center gap-1">
                              <FaCalendarAlt className="text-gray-400" />
                              {lote.fecha_caducidad 
                                ? new Date(lote.fecha_caducidad).toLocaleDateString('es-MX', { year: 'numeric', month: 'short', day: 'numeric' })
                                : 'Sin fecha'}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm">
                            {lote.dias_para_caducar !== null ? (
                              <span className={`font-semibold ${lote.dias_para_caducar < 0 ? 'text-red-600' : lote.dias_para_caducar <= 30 ? 'text-orange-600' : lote.dias_para_caducar <= 90 ? 'text-yellow-600' : 'text-green-600'}`}>
                                {lote.dias_para_caducar < 0 ? `${Math.abs(lote.dias_para_caducar)} vencido` : `${lote.dias_para_caducar} días`}
                              </span>
                            ) : '-'}
                          </td>
                          <td className="px-4 py-3 text-sm">
                            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold ${semaforo.bg} ${semaforo.text}`}>
                              <span>{semaforo.icon}</span>
                              {semaforo.label}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600">
                            {lote.centro_nombre || 'Almacén Central'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                <div className="py-12 text-center text-gray-500">
                  <FaBoxOpen className="mx-auto text-4xl mb-3 text-gray-300" />
                  <p>Este producto no tiene lotes con stock disponible.</p>
                </div>
              )}
            </div>
            <div className="px-6 py-4 bg-gray-50 border-t flex justify-between items-center">
              <div className="text-xs text-gray-500">
                <span className="inline-flex items-center gap-1 mr-3">🟢 &gt;90 días</span>
                <span className="inline-flex items-center gap-1 mr-3">🟡 31-90 días</span>
                <span className="inline-flex items-center gap-1 mr-3">🟠 1-30 días</span>
                <span className="inline-flex items-center gap-1">🔴 Vencido</span>
              </div>
              <button
                type="button"
                onClick={cerrarLotesModal}
                className="rounded-lg px-4 py-2 text-sm font-semibold text-white bg-theme-gradient hover:opacity-90"
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



export default Productos;



















































