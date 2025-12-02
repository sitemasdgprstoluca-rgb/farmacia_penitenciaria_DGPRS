import { useState, useEffect, useCallback } from 'react';
import { lotesAPI, productosAPI, centrosAPI } from '../services/api';
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
  FaTimes
} from 'react-icons/fa';
import { DEV_CONFIG } from '../config/dev';
import PageHeader from '../components/PageHeader';
import { COLORS, PRIMARY_GRADIENT, SECONDARY_GRADIENT } from '../constants/theme';
import Pagination from '../components/Pagination';
import { usePermissions } from '../hooks/usePermissions';

const MOCK_PRODUCTOS = Array.from({ length: 40 }).map((_, index) => ({
  id: index + 1,
  clave: `MED-${String(index + 1).padStart(3, '0')}`,
  descripcion: `Producto simulado ${index + 1}`,
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
    producto_descripcion: producto.descripcion,
    numero_lote: `L-${202300 + index}`,
    fecha_caducidad: fecha.toISOString(),
    dias_para_caducar: diasParaCaducar,
    alerta_caducidad: alerta,
    cantidad_inicial: cantidadInicial,
    cantidad_actual: cantidadActual,
    porcentaje_consumido: Math.round(
      (1 - cantidadActual / cantidadInicial) * 100,
    ),
    proveedor: `Proveedor ${index % 6 + 1}`,
    observaciones: '',
    activo: index % 9 !== 0,
  };
};

const MOCK_LOTES = Array.from({ length: 60 }).map((_, index) =>
  createMockLote(index),
);

const Lotes = () => {
  const { getRolPrincipal, permisos } = usePermissions();
  const rolPrincipal = getRolPrincipal();
  const puedeVerGlobal = ['ADMIN', 'FARMACIA', 'VISTA'].includes(rolPrincipal) || permisos?.isSuperuser;
  // Solo ADMIN y FARMACIA pueden ver campos de contrato (para auditoría)
  const puedeVerContrato = ['ADMIN', 'FARMACIA'].includes(rolPrincipal) || permisos?.isSuperuser;
  
  // Permisos específicos para acciones
  const esFarmaciaAdmin = ['ADMIN', 'FARMACIA'].includes(rolPrincipal) || permisos?.isSuperuser;
  const puede = {
    crear: esFarmaciaAdmin,
    editar: esFarmaciaAdmin,
    eliminar: esFarmaciaAdmin,
    exportar: esFarmaciaAdmin,
    importar: esFarmaciaAdmin,
    verDocumento: true, // Todos pueden ver
    subirDocumento: esFarmaciaAdmin,
  };
  
  const [lotes, setLotes] = useState([]);
  const [productos, setProductos] = useState([]);
  const [centros, setCentros] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showDocModal, setShowDocModal] = useState(false);
  const [selectedLoteDoc, setSelectedLoteDoc] = useState(null);
  const [editingLote, setEditingLote] = useState(null);
  
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
  const [filtroActivo, setFiltroActivo] = useState('');
  const [filtroCentro, setFiltroCentro] = useState('');
  
  const [formData, setFormData] = useState({
    producto: '',
    numero_lote: '',
    fecha_caducidad: '',
    cantidad_inicial: '',
    precio_compra: '',
    proveedor: '',
    factura: '',
    numero_contrato: '',
    marca: '',
    observaciones: ''
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
          lote.producto_descripcion.toLowerCase().includes(term)
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
      if (filtroCentro) params.centro = filtroCentro;

      const response = await lotesAPI.getAll(params);
      setLotes(response.data.results || response.data);
      setTotalLotes(response.data.count || 0);
      setTotalPages(Math.ceil((response.data.count || 0) / pageSize));
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
  }, [applyMockLotes, currentPage, filtroActivo, filtroCaducidad, filtroConStock, filtroProducto, filtroCentro, pageSize, searchTerm]);

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      cargarLotes();
    }, 500);

    return () => clearTimeout(delayDebounceFn);
  }, [cargarLotes]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const dataToSend = {
        ...formData,
        cantidad_actual: formData.cantidad_inicial, // Inicializar igual a inicial
      };
      
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
      const errorMsg = error.response?.data?.numero_lote?.[0] || 
                       error.response?.data?.error || 
                       'Error al guardar lote';
      toast.error(errorMsg);
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (lote) => {
    setEditingLote(lote);
    setFormData({
      producto: lote.producto,
      numero_lote: lote.numero_lote,
      fecha_caducidad: lote.fecha_caducidad,
      cantidad_inicial: lote.cantidad_inicial,
      precio_compra: lote.precio_compra || '',
      proveedor: lote.proveedor || '',
      factura: lote.factura || '',
      numero_contrato: lote.numero_contrato || '',
      marca: lote.marca || '',
      observaciones: lote.observaciones || ''
    });
    setShowModal(true);
  };

  const handleDelete = async (id, lote) => {
    if (!puede.eliminar) {
      toast.error('No tiene permisos para eliminar lotes');
      return;
    }
    
    if (loading) return; // Evitar múltiples clics
    
    const confirmMsg = `¿Está seguro de DESACTIVAR el lote ${lote?.numero_lote || id}?\n\n` +
      `⚠️ El lote quedará marcado como eliminado (soft delete).\n` +
      `Nota: Esta acción es reversible por un administrador.`;
    
    if (!window.confirm(confirmMsg)) return;
    
    try {
      setLoading(true);
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
      setLoading(false);
    }
  };

  const handleDocumentoModal = (lote) => {
    setSelectedLoteDoc(lote);
    setShowDocModal(true);
  };

  const handleSubirDocumento = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
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
    formData.append('nombre', file.name);
    
    try {
      setLoading(true);
      await lotesAPI.subirDocumento(selectedLoteDoc.id, formData);
      toast.success('Documento subido correctamente');
      setShowDocModal(false);
      cargarLotes();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al subir documento');
    } finally {
      setLoading(false);
    }
  };

  const handleEliminarDocumento = async () => {
    if (!window.confirm('¿Está seguro de eliminar el documento?')) return;
    
    try {
      setLoading(true);
      await lotesAPI.eliminarDocumento(selectedLoteDoc.id);
      toast.success('Documento eliminado');
      setShowDocModal(false);
      cargarLotes();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al eliminar documento');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      producto: '',
      numero_lote: '',
      fecha_caducidad: '',
      cantidad_inicial: '',
      precio_compra: '',
      proveedor: '',
      factura: '',
      numero_contrato: '',
      marca: '',
      observaciones: ''
    });
    setEditingLote(null);
  };

  const limpiarFiltros = () => {
    setSearchTerm('');
    setFiltroProducto('');
    setFiltroCaducidad('');
    setFiltroConStock('');
    setFiltroActivo('');
    setFiltroCentro('');
    setCurrentPage(1);
  };

  const handleExportar = async () => {
    if (!puede.exportar) {
      toast.error('No tiene permisos para exportar');
      return;
    }
    
    try {
      setLoading(true);
      // Enviar TODOS los filtros activos para que el Excel coincida con la vista
      const params = {};
      if (searchTerm) params.search = searchTerm;
      if (filtroProducto) params.producto = filtroProducto;
      if (filtroCaducidad) params.caducidad = filtroCaducidad;
      if (filtroConStock) params.con_stock = filtroConStock;
      if (filtroActivo) params.activo = filtroActivo;
      if (filtroCentro) params.centro = filtroCentro;
      
      const response = await lotesAPI.exportar(params);
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `lotes_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('Lotes exportados correctamente');
    } catch (error) {
      toast.error('Error al exportar lotes');
    } finally {
      setLoading(false);
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
  
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    setLoading(true);
    const response = await lotesAPI.importar(formData);
    const resumen = response.data?.resumen || {};
    const errores = response.data?.errores || [];

    toast.success(
      `Importación completada: ${resumen.exitos || 0} filas correctas de ${resumen.total || 0}`
    );
    
    if (errores.length) {
      console.warn('Errores en importación de lotes:', errores);
      // Mostrar primeros 3 errores al usuario
      const primeros = errores.slice(0, 3);
      primeros.forEach((err, idx) => {
        const msg = typeof err === 'string' ? err : `Fila ${err.fila || idx + 1}: ${err.error || err.mensaje || JSON.stringify(err)}`;
        toast.error(msg, { duration: 5000 });
      });
      if (errores.length > 3) {
        toast.error(`... y ${errores.length - 3} errores más. Revise la consola.`, { duration: 5000 });
      }
    }
    
    setShowImportModal(false);
    cargarLotes();
  } catch (error) {
    toast.error(error.response?.data?.error || 'Error al importar lotes');
  } finally {
    setLoading(false);
    e.target.value = '';
    }
  };

  const getAlertaClass = (alerta) => {
    const classes = {
      vencido: 'bg-red-100 text-red-800 font-bold',
      critico: 'bg-orange-100 text-orange-800 font-bold',
      proximo: 'bg-yellow-100 text-yellow-800',
      normal: 'bg-green-100 text-green-800'
    };
    return classes[alerta] || 'bg-gray-100 text-gray-800';
  };

  const getAlertaIcon = (alerta) => {
    if (alerta === 'vencido' || alerta === 'critico') {
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
    <>
      {puede.exportar && (
        <button
          type="button"
          onClick={handleExportar}
          disabled={loading}
          className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-50"
          style={{
            background: PRIMARY_GRADIENT,
            border: '1px solid rgba(255,255,255,0.4)'
          }}
        >
          <FaFileExcel /> Exportar
        </button>
      )}
      {puede.importar && (
        <button
          type="button"
          onClick={() => setShowImportModal(true)}
          disabled={loading}
          className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-50"
          style={{
            background: SECONDARY_GRADIENT,
            border: '1px solid rgba(255,255,255,0.4)'
          }}
        >
          <FaFileUpload /> Importar
        </button>
      )}
      {puede.crear && (
        <button
          type="button"
          onClick={() => setShowModal(true)}
          disabled={loading}
          className="flex items-center gap-2 rounded-full bg-white/90 px-4 py-2 text-sm font-bold hover:bg-white disabled:opacity-50"
          style={{ color: COLORS.vino }}
        >
          <FaPlus /> Nuevo Lote
        </button>
      )}
    </>
  );

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        icon={FaWarehouse}
        title="Gestión de Lotes"
        subtitle={`Total: ${totalLotes} lotes | Página ${currentPage} de ${totalPages}`}
        badge={filtrosActivos ? `${filtrosActivos} filtros activos` : null}
        actions={headerActions}
      />

      {/* Filtros */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
          <div className="md:col-span-2">
            <input
              type="text"
              placeholder="Buscar por número de lote, producto..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <select
            value={filtroProducto}
            onChange={(e) => setFiltroProducto(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todos los productos</option>
            {productos.map(p => (
              <option key={p.id} value={p.id}>
                {p.clave} - {p.descripcion.substring(0, 30)}
              </option>
            ))}
          </select>
          
          <select
            value={filtroCaducidad}
            onChange={(e) => setFiltroCaducidad(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            {nivelCaducidad.map(n => (
              <option key={n.value} value={n.value}>{n.label}</option>
            ))}
          </select>

          <select
            value={filtroConStock}
            onChange={(e) => setFiltroConStock(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todos</option>
            <option value="con_stock">Con Inventario</option>
            <option value="sin_stock">Sin Inventario</option>
          </select>
          
          {/* Selector de Centro - solo para admin/farmacia/vista */}
          {puedeVerGlobal && (
            <select
              value={filtroCentro}
              onChange={(e) => setFiltroCentro(e.target.value)}
              className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos los centros</option>
              <option value="central">Farmacia Central</option>
              {centros.map(c => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          )}
          
          <button
            onClick={limpiarFiltros}
            className="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 flex items-center justify-center gap-2"
          >
            <FaFilter /> Limpiar
          </button>
        </div>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">#</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Producto</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Número Lote</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Caducidad</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Días</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Alerta</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Inventario</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan="8" className="text-center py-8">
                    <div className="flex justify-center items-center">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                      <span className="ml-2">Cargando lotes...</span>
                    </div>
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
                  <tr key={lote.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {(currentPage - 1) * pageSize + index + 1}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <div className="font-medium text-blue-600">{lote.producto_clave}</div>
                      <div 
                        className="text-gray-500 text-xs cursor-help relative group"
                        title={lote.producto_descripcion}
                      >
                        {lote.producto_descripcion?.substring(0, 40)}{lote.producto_descripcion?.length > 40 ? '...' : ''}
                        {/* Tooltip on hover */}
                        <div className="absolute z-50 hidden group-hover:block bg-gray-900 text-white text-xs rounded-lg py-2 px-3 -top-2 left-0 transform -translate-y-full w-64 shadow-lg">
                          <p className="font-semibold mb-1">Descripción completa:</p>
                          <p>{lote.producto_descripcion}</p>
                          <div className="absolute bottom-0 left-4 transform translate-y-1/2 rotate-45 w-2 h-2 bg-gray-900"></div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono font-bold">
                      {lote.numero_lote}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {new Date(lote.fecha_caducidad).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {lote.dias_para_caducar}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs rounded-full ${getAlertaClass(lote.alerta_caducidad)}`}>
                        {getAlertaIcon(lote.alerta_caducidad)}
                        {lote.alerta_caducidad?.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={lote.cantidad_actual === 0 ? 'text-red-600 font-bold' : ''}>
                        {lote.cantidad_actual} / {lote.cantidad_inicial}
                      </span>
                      <div className="text-xs text-gray-500">
                        ({lote.porcentaje_consumido}% usado)
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2 flex items-center gap-1">
                      {/* Botón PDF - visible para todos, subir solo farmacia */}
                      <button
                        onClick={() => handleDocumentoModal(lote)}
                        disabled={loading}
                        className={`p-1 rounded disabled:opacity-50 ${lote.documento_url ? 'text-green-600 hover:text-green-800 hover:bg-green-50' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-50'}`}
                        title={lote.documento_url ? `Ver: ${lote.documento_nombre || 'documento.pdf'}` : (puede.subirDocumento ? 'Subir documento PDF' : 'Sin documento')}
                      >
                        <FaFilePdf className="text-lg" />
                      </button>
                      {/* Botón Editar - solo farmacia/admin */}
                      {puede.editar && (
                        <button
                          onClick={() => handleEdit(lote)}
                          disabled={loading}
                          className="p-1 rounded text-blue-600 hover:text-blue-800 hover:bg-blue-50 disabled:opacity-50"
                          title="Editar"
                        >
                          <FaEdit className="text-lg" />
                        </button>
                      )}
                      {/* Botón Eliminar - solo farmacia/admin */}
                      {puede.eliminar && (
                        <button
                          onClick={() => handleDelete(lote.id, lote)}
                          disabled={loading}
                          className="p-1 rounded text-red-600 hover:text-red-800 hover:bg-red-50 disabled:opacity-50"
                          title="Desactivar lote"
                        >
                          <FaTrash className="text-lg" />
                        </button>
                      )}
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
            <div className="px-6 py-4 border-b-4 flex items-center justify-between" style={{ 
              background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)',
              borderBottomColor: '#9F2241'
            }}>
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
                {/* Producto */}
                <div>
                  <label className="block text-sm font-bold mb-2" style={{ color: '#6B1839' }}>
                    PRODUCTO <span className="text-red-600">*</span>
                  </label>
                  <select
                    value={formData.producto}
                    onChange={(e) => setFormData({...formData, producto: e.target.value})}
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
                        {p.clave} - {p.descripcion}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 italic mt-1">No se puede cambiar el producto de un lote existente</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  {/* Código de Lote */}
                  <div>
                    <label className="block text-sm font-bold mb-2" style={{ color: '#6B1839' }}>
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
                    <p className="text-xs text-gray-500 italic mt-1">Se convertirá a mayúsculas automáticamente</p>
                  </div>
                  
                  {/* Fecha Caducidad */}
                  <div>
                    <label className="block text-sm font-bold mb-2" style={{ color: '#6B1839' }}>
                      FECHA DE CADUCIDAD <span className="text-red-600">*</span>
                    </label>
                    <input
                      type="date"
                      value={formData.fecha_caducidad}
                      onChange={(e) => setFormData({...formData, fecha_caducidad: e.target.value})}
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
                      min={new Date().toISOString().split('T')[0]}
                    />
                    {formData.fecha_caducidad && (
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
                  {/* Cantidad Actual */}
                  <div>
                    <label className="block text-sm font-bold mb-2" style={{ color: '#6B1839' }}>
                      CANTIDAD ACTUAL <span className="text-red-600">*</span>
                    </label>
                    <input
                      type="number"
                      min="1"
                      value={formData.cantidad_inicial}
                      onChange={(e) => setFormData({...formData, cantidad_inicial: e.target.value})}
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
                      placeholder="0"
                    />
                    <p className="text-xs text-gray-500 italic mt-1">Cantidad actual en inventario</p>
                  </div>
                  
                  {/* Precio de Compra */}
                  <div>
                    <label className="block text-sm font-bold mb-2" style={{ color: '#6B1839' }}>
                      PRECIO DE COMPRA
                    </label>
                    <div className="relative">
                      <span className="absolute left-4 top-3.5 font-bold" style={{ color: '#6B7280' }}>$</span>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={formData.precio_compra}
                        onChange={(e) => setFormData({...formData, precio_compra: e.target.value})}
                        className="w-full pl-8 pr-4 py-3 border-2 border-gray-200 rounded-xl transition-all focus:outline-none"
                        onFocus={(e) => {
                          e.target.style.borderColor = '#9F2241';
                          e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
                        }}
                        onBlur={(e) => {
                          e.target.style.borderColor = '#E5E7EB';
                          e.target.style.boxShadow = 'none';
                        }}
                        placeholder="0.00"
                      />
                    </div>
                  </div>
                </div>
              
                <div>
                  <label className="block text-sm font-bold mb-2" style={{ color: '#6B1839' }}>
                    PROVEEDOR
                  </label>
                  <input
                    type="text"
                    value={formData.proveedor}
                    onChange={(e) => setFormData({...formData, proveedor: e.target.value})}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl transition-all focus:outline-none"
                    onFocus={(e) => {
                      e.target.style.borderColor = '#9F2241';
                      e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = '#E5E7EB';
                      e.target.style.boxShadow = 'none';
                    }}
                    placeholder="Nombre del proveedor (opcional)"
                    maxLength={200}
                  />
                  <p className="text-xs text-gray-400 mt-1">0/200 caracteres</p>
                </div>

                {/* CAMPOS DE TRAZABILIDAD DE CONTRATOS - Solo visible para ADMIN y FARMACIA */}
                {puedeVerContrato && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-bold mb-2" style={{ color: '#6B1839' }}>
                      NÚMERO DE CONTRATO
                    </label>
                    <input
                      type="text"
                      value={formData.numero_contrato}
                      onChange={(e) => setFormData({...formData, numero_contrato: e.target.value})}
                      className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl transition-all focus:outline-none"
                      onFocus={(e) => {
                        e.target.style.borderColor = '#9F2241';
                        e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
                      }}
                      onBlur={(e) => {
                        e.target.style.borderColor = '#E5E7EB';
                        e.target.style.boxShadow = 'none';
                      }}
                      placeholder="Ej: CONT-2025-001"
                      maxLength={100}
                    />
                    <p className="text-xs text-gray-400 mt-1">Para trazabilidad de adquisiciones</p>
                  </div>

                  <div>
                    <label className="block text-sm font-bold mb-2" style={{ color: '#6B1839' }}>
                      MARCA
                    </label>
                    <input
                      type="text"
                      value={formData.marca}
                      onChange={(e) => setFormData({...formData, marca: e.target.value})}
                      className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl transition-all focus:outline-none"
                      onFocus={(e) => {
                        e.target.style.borderColor = '#9F2241';
                        e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
                      }}
                      onBlur={(e) => {
                        e.target.style.borderColor = '#E5E7EB';
                        e.target.style.boxShadow = 'none';
                      }}
                      placeholder="Ej: Bayer, Pfizer, Genérico"
                      maxLength={150}
                    />
                    <p className="text-xs text-gray-400 mt-1">Marca del medicamento</p>
                  </div>
                </div>
                )}

                {/* Lote activo checkbox */}
                <div className="flex items-center gap-3 p-4 rounded-xl" style={{ backgroundColor: '#FEF9F2', border: '2px solid #E5E7EB' }}>
                  <input
                    type="checkbox"
                    checked={true}
                    className="w-5 h-5 rounded"
                    style={{ accentColor: '#9F2241' }}
                    disabled
                  />
                  <div>
                    <label className="font-bold text-sm" style={{ color: '#6B1839' }}>Lote activo</label>
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
                  className="px-6 py-3 rounded-xl font-bold transition-all transform hover:scale-105"
                  style={{ 
                    background: 'linear-gradient(135deg, #6B7280 0%, #4B5563 100%)',
                    color: 'white'
                  }}
                  disabled={loading}
                >
                  CANCELAR
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-8 py-3 rounded-xl font-bold transition-all transform hover:scale-105 shadow-lg disabled:opacity-50"
                  style={{ 
                    background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)',
                    color: 'white'
                  }}
                >
                  {loading ? 'GUARDANDO...' : '-o" GUARDAR LOTE'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Importar */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Importar Lotes desde Excel</h2>
            
            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-2">
                El archivo debe contener las siguientes columnas:
              </p>
              <ul className="text-sm text-gray-600 list-disc list-inside">
                <li>Producto (Clave o ID)</li>
                <li>Número Lote</li>
                <li>Fecha Caducidad (YYYY-MM-DD)</li>
                <li>Cantidad</li>
                <li>Precio Compra (opcional)</li>
                <li>Proveedor (opcional)</li>
                <li>Factura (opcional)</li>
                <li>Número Contrato (opcional)</li>
                <li>Marca (opcional)</li>
              </ul>
            </div>
            
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">
                Seleccionar archivo Excel (.xlsx, .xls)
              </label>
              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={handleImportar}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              />
            </div>
            
            {loading && (
              <div className="mb-4 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="text-sm text-gray-600 mt-2">Procesando archivo...</p>
              </div>
            )}
            
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowImportModal(false)}
                className="px-4 py-2 border rounded-lg hover:bg-gray-100"
                disabled={loading}
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Documento */}
      {showDocModal && selectedLoteDoc && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full">
            <div className="p-6 border-b flex justify-between items-center" style={{ background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)' }}>
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                <FaFilePdf /> Documento del Lote
              </h3>
              <button
                onClick={() => setShowDocModal(false)}
                className="text-white hover:text-gray-200"
              >
                <FaTimes className="text-xl" />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <div className="text-sm text-gray-600">
                <p><strong>Lote:</strong> {selectedLoteDoc.numero_lote}</p>
                <p><strong>Producto:</strong> {selectedLoteDoc.producto_descripcion}</p>
              </div>
              
              {selectedLoteDoc.documento_url ? (
                <div className="space-y-3">
                  <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm text-green-800 font-medium">
                      ✓ Documento actual: {selectedLoteDoc.documento_nombre || 'documento.pdf'}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <a
                      href={selectedLoteDoc.documento_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      <FaDownload /> Ver documento
                    </a>
                    <button
                      onClick={handleEliminarDocumento}
                      disabled={loading}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                    >
                      <FaTrash />
                    </button>
                  </div>
                </div>
              ) : (
                <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-center">
                  <p className="text-sm text-gray-600 mb-3">No hay documento adjunto</p>
                </div>
              )}
              
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  {selectedLoteDoc.documento_url ? 'Reemplazar documento' : 'Subir documento'}
                </label>
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleSubirDocumento}
                  disabled={loading}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
                <p className="text-xs text-gray-500 mt-1">Solo archivos PDF, máximo 10MB</p>
              </div>
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











