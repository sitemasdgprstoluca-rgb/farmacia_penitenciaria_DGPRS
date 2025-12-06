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

  FaBoxOpen

} from 'react-icons/fa';

import { toast } from 'react-hot-toast';

import { productosAPI } from '../services/api';

import { DEV_CONFIG } from '../config/dev';

import { usePermissions } from '../hooks/usePermissions';

import { ProtectedButton } from '../components/ProtectedAction';
import Pagination from '../components/Pagination';

import { COLORS } from '../constants/theme';

import { createExcelReport } from '../utils/reportExport';

import { hasAccessToken } from '../services/tokenManager';



const UNIDADES = [

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



const getInventarioDisponible = (producto) => {

  const numericCandidates = [

    producto.stock_actual,

    producto.stock_total,

    producto.inventario_total,

    producto.inventario,

    producto.existencias,

    producto.stock_disponible,

    producto.cantidad_disponible,

    producto.cantidad_total

  ];



  for (const candidate of numericCandidates) {

    if (typeof candidate === 'number' && !Number.isNaN(candidate)) {

      return candidate;

    }

  }



  if (typeof producto.stock === 'number') {

    return producto.stock;

  }



  const parsed = Number(producto.stock_actual ?? producto.stock_total ?? producto.stock);

  return Number.isNaN(parsed) ? 0 : parsed;

};



const formatInventario = (producto) => {

  const valor = getInventarioDisponible(producto);

  if (typeof valor === 'number' && !Number.isNaN(valor)) {

    return valor.toLocaleString('es-MX');

  }

  return valor || '-';

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

  descripcion: '',

  unidad_medida: 'PIEZA',

  precio_unitario: '',

  stock_minimo: '10',

  activo: true,

  imagen: null,

  imagenPreview: null,

};



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

    descripcion: baseNames[id % baseNames.length],

    unidad_medida: UNIDADES[id % UNIDADES.length],

    precio_unitario: (10 + id * 0.75).toFixed(2),

    stock_minimo: String(25 + (id % 6) * 5),

    stock_actual: 120 + (id % 8) * 15,

    activo: id % 9 !== 0,

    alerta_stock: alertas[id % alertas.length],

    creado_por: 'admin@edomex.gob.mx',

    created_at: new Date(Date.now() - id * 86400000).toISOString(),

  };

});



const Productos = () => {

  const { user, permisos, getRolPrincipal } = usePermissions();

  const rolPrincipal = getRolPrincipal(); // ADMIN | FARMACIA | CENTRO | VISTA | SIN_ROL
  const esAdmin = rolPrincipal === 'ADMIN';
  const esFarmacia = rolPrincipal === 'FARMACIA';
  const esFarmaciaAdmin = esAdmin || esFarmacia; // Admin o Farmacia pueden gestionar productos
  const esCentroUser = rolPrincipal === 'CENTRO';
  const esVistaUser = rolPrincipal === 'VISTA';
  
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

        const descripcion = normalizeText(producto.descripcion);

        return clave.includes(term) || descripcion.includes(term);

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

    console.log('📦 Cargando productos...');

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



  const validarFormulario = (data) => {

    const errors = {};

    // Validar clave: 3-50 caracteres, solo alfanumérico con guiones y guiones bajos
    const claveRegex = /^[A-Za-z0-9\-_]+$/;
    if (!data.clave || data.clave.length < 3 || data.clave.length > 50) {
      errors.clave = 'La clave debe tener entre 3 y 50 caracteres';
    } else if (!claveRegex.test(data.clave)) {
      errors.clave = 'La clave solo puede contener letras, números, guiones y guiones bajos';
    }

    if (!data.descripcion || data.descripcion.length < 5 || data.descripcion.length > 300) {

      errors.descripcion = 'La descripción debe tener entre 5 y 300 caracteres';

    }

    if (!data.precio_unitario || Number(data.precio_unitario) < 0.01) {

      errors.precio_unitario = 'El precio debe ser mayor o igual a 0.01';

    }

    if (data.stock_minimo === '' || Number(data.stock_minimo) < 0) {

      errors.stock_minimo = 'El inventario mínimo no puede ser negativo';

    }

    if (!UNIDADES.includes(data.unidad_medida)) {

      errors.unidad_medida = 'Seleccione una unidad válida';

    }

    return errors;

  };



  const openModal = (producto = null) => {

    if (producto) {

      setEditingProduct(producto);

      setFormData({

        clave: producto.clave,

        descripcion: producto.descripcion,

        unidad_medida: producto.unidad_medida,

        precio_unitario: producto.precio_unitario,

        stock_minimo: producto.stock_minimo,

        activo: producto.activo,

        imagen: null,

        imagenPreview: producto.imagen_url || null,

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
      const precioVal = parseFloat(formData.precio_unitario);
      
      // Usar FormData si hay imagen, de lo contrario JSON normal
      let dataToSend;
      let hasImage = formData.imagen instanceof File;
      
      if (hasImage) {
        dataToSend = new FormData();
        dataToSend.append('clave', formData.clave);
        dataToSend.append('descripcion', formData.descripcion);
        dataToSend.append('unidad_medida', formData.unidad_medida);
        dataToSend.append('precio_unitario', isNaN(precioVal) || precioVal < 0.01 ? 0.01 : precioVal);
        dataToSend.append('stock_minimo', parseInt(formData.stock_minimo, 10) || 0);
        dataToSend.append('activo', formData.activo);
        dataToSend.append('imagen', formData.imagen);
      } else {
        dataToSend = {
          clave: formData.clave,
          descripcion: formData.descripcion,
          unidad_medida: formData.unidad_medida,
          precio_unitario: isNaN(precioVal) || precioVal < 0.01 ? 0.01 : precioVal,
          stock_minimo: parseInt(formData.stock_minimo, 10) || 0,
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

      toast.error(err.response?.data?.error || 'Error al guardar producto');

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

            { header: 'Descripción', key: 'descripcion', width: 40 },

            { header: 'Unidad', key: 'unidad_medida', width: 12 },

            { header: 'Precio', value: (row) => Number(row.precio_unitario).toFixed(2), width: 12 },

            { header: 'Inventario', value: (row) => getInventarioDisponible(row), width: 16 },

            { header: 'Inv. Mínimo', key: 'stock_minimo', width: 16 },

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
            descripcion: `Producto importado ${idx + 1}`,
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




  // eslint-disable-next-line no-unused-vars
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

      return (

        <div className="py-12 text-center">

          <div className="animate-spin mx-auto mb-3 h-10 w-10 border-4 border-t-transparent spinner-institucional rounded-full" />

          <p className="text-sm text-gray-600">Cargando productos...</p>

        </div>

      );

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

                'Descripción',

                'Unidad',

                'Precio',

                'Inventario',

                'Inv. Mínimo',

                'Estado',

                'Nivel Inv.',

                'Creado por',

                'Acciones',

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

              return (

              <tr

                key={producto.id}

                className={`transition ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-gray-100`}

              >

                <td className="px-3 py-3 text-sm font-semibold text-gray-500">{consecutivo}</td>

                <td className="px-4 py-3 text-sm font-semibold text-gray-800">{producto.clave}</td>

                <td className="px-4 py-3 text-sm text-gray-600">{producto.descripcion}</td>

                <td className="px-4 py-3 text-sm">{producto.unidad_medida}</td>

                <td className="px-4 py-3 text-sm font-semibold">${Number(producto.precio_unitario).toFixed(2)}</td>

                <td className="px-4 py-3 text-sm">{formatInventario(producto)}</td>

                <td className="px-4 py-3 text-sm">{producto.stock_minimo}</td>

                <td className="px-4 py-3 text-sm">{renderEstadoBadge(estadoInventario.label, estadoInventario.activo)}</td>

                <td className="px-4 py-3 text-sm">{renderStockBadge(nivelStock)}</td>

                <td className="px-4 py-3 text-sm">{producto.creado_por || '-'}</td>

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

                  </div>

                </td>

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
          </div>

        </div>

      </div>



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

          <div className="w-full max-w-2xl rounded-2xl bg-white shadow-2xl">

            <div

              className="flex items-center justify-between rounded-t-2xl px-6 py-4 text-white bg-theme-gradient"

            >

              <div>

                <h2 className="text-xl font-bold">{editingProduct ? 'Editar producto' : 'Nuevo producto'}</h2>

                <p className="text-sm text-white/80">Complete los campos obligatorios</p>

              </div>

              <span className="text-sm font-semibold">{editingProduct ? editingProduct.clave : 'Nuevo'}</span>

            </div>

            <form onSubmit={handleSubmit} className="space-y-4 px-6 py-6">

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">

                <div>

                  <label className="text-xs font-semibold text-theme-primary-hover">Clave *</label>

                  <input

                    type="text"

                    value={formData.clave}

                    onChange={(e) => setFormData({ ...formData, clave: e.target.value.toUpperCase() })}

                    maxLength={50}

                    className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 ${formErrors.clave ? 'border-red-500' : 'border-theme-primary'}`}

                  />

                  {formErrors.clave && <p className="text-xs text-red-600">{formErrors.clave}</p>}

                </div>

                <div>

                  <label className="text-xs font-semibold text-theme-primary-hover">Unidad *</label>

                  <select

                    value={formData.unidad_medida}

                    onChange={(e) => setFormData({ ...formData, unidad_medida: e.target.value })}

                    className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 ${formErrors.unidad_medida ? 'border-red-500' : 'border-theme-primary'}`}

                  >

                    {UNIDADES.map((unidad) => (

                      <option key={unidad} value={unidad}>

                        {unidad}

                      </option>

                    ))}

                  </select>

                  {formErrors.unidad_medida && <p className="text-xs text-red-600">{formErrors.unidad_medida}</p>}

                </div>

              </div>

              <div>

                <label className="text-xs font-semibold text-theme-primary-hover">Descripción *</label>

                <textarea

                  value={formData.descripcion}

                  onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}

                  rows={3}

                  maxLength={300}

                  className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 ${formErrors.descripcion ? 'border-red-500' : 'border-theme-primary'}`}

                />

                <div className="flex justify-between text-xs text-gray-500">

                  <span>{formErrors.descripcion || ''}</span>

                  <span>{formData.descripcion.length}/300</span>

                </div>

              </div>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">

                <div>

                  <label className="text-xs font-semibold text-theme-primary-hover">Precio unitario *</label>

                  <input

                    type="number"

                    min="0.01"

                    step="0.01"

                    value={formData.precio_unitario}

                    onChange={(e) => setFormData({ ...formData, precio_unitario: e.target.value })}

                    className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 ${formErrors.precio_unitario ? 'border-red-500' : 'border-theme-primary'}`}

                  />

                  {formErrors.precio_unitario && <p className="text-xs text-red-600">{formErrors.precio_unitario}</p>}

                </div>

                <div>

                  <label className="text-xs font-semibold text-theme-primary-hover">Inventario mínimo *</label>

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

              {/* Campo de imagen del producto */}

              <div>

                <label className="text-xs font-semibold text-theme-primary-hover">Imagen del producto</label>

                <div className="mt-1 flex items-center gap-4">

                  {(formData.imagenPreview || formData.imagen) && (

                    <div className="relative">

                      <img

                        src={formData.imagen ? URL.createObjectURL(formData.imagen) : formData.imagenPreview}

                        alt="Preview"

                        className="h-20 w-20 rounded-lg object-cover border border-gray-300"

                      />

                      <button

                        type="button"

                        onClick={() => setFormData({ ...formData, imagen: null, imagenPreview: null })}

                        className="absolute -top-2 -right-2 rounded-full bg-red-500 text-white p-1 text-xs hover:bg-red-600"

                      >

                        ✕

                      </button>

                    </div>

                  )}

                  <label className="cursor-pointer flex items-center gap-2 rounded-lg border border-dashed border-gray-400 px-4 py-3 hover:border-theme-primary hover:bg-gray-50">

                    <FaFileUpload className="text-gray-500" />

                    <span className="text-sm text-gray-600">

                      {formData.imagen ? 'Cambiar imagen' : 'Seleccionar imagen'}

                    </span>

                    <input

                      type="file"

                      accept="image/jpeg,image/png,image/webp"

                      className="hidden"

                      onChange={(e) => {

                        const file = e.target.files?.[0];

                        if (file) {

                          if (file.size > 2 * 1024 * 1024) {

                            toast.error('La imagen no puede exceder 2MB');

                            return;

                          }

                          setFormData({ ...formData, imagen: file, imagenPreview: null });

                        }

                      }}

                    />

                  </label>

                </div>

                <p className="text-xs text-gray-500 mt-1">JPG, PNG o WebP. Máximo 2MB.</p>

              </div>

              <div className="flex items-center gap-2 rounded-lg border px-4 py-3 border-theme-primary">

                <input

                  type="checkbox"

                  checked={formData.activo}

                  onChange={(e) => setFormData({ ...formData, activo: e.target.checked })}

                  className="h-4 w-4"

                />

                <span className="text-sm font-semibold text-gray-700">Producto Activo</span>

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

                  {(auditoriaData?.producto?.clave) || 'Producto'} | {auditoriaData?.producto?.descripcion || ''}

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

    </div>

  );

};



export default Productos;



















































