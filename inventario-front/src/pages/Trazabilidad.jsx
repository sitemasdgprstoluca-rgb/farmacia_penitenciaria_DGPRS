import { useState, useEffect, useCallback, useRef } from 'react';
import { trazabilidadAPI, productosAPI, lotesAPI, centrosAPI, descargarArchivo } from '../services/api';
import { toast } from 'react-hot-toast';
import { FaSearch, FaBox, FaWarehouse, FaHistory, FaExclamationTriangle, FaFilePdf, FaFileExcel, FaBuilding, FaSpinner, FaInfoCircle, FaCalendarAlt, FaDownload } from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import AutocompleteInput from '../components/AutocompleteInput';
import { usePermissions } from '../hooks/usePermissions';

// ============================================
// MAPEO Y NORMALIZACIÓN DE DATOS
// Sincronizado con backend: views_legacy.py trazabilidad_producto/lote
// BD: productos, lotes, movimientos
// ============================================

/**
 * Extraer nombre del centro de forma segura
 * El backend puede enviar: string, objeto {nombre, id}, null, o undefined
 */
const getCentroNombre = (centro, fallback = 'Farmacia Central') => {
  if (!centro) return fallback;
  if (typeof centro === 'string') return centro;
  if (typeof centro === 'object' && centro.nombre) return centro.nombre;
  return fallback;
};

const mapMovimiento = (mov = {}) => ({
  id: mov.id,
  fecha: mov.fecha || mov.fecha_movimiento || mov.fecha_mov || null,
  tipo: (mov.tipo || mov.tipo_movimiento || '').toString().toUpperCase(),
  cantidad: mov.cantidad,
  centro: getCentroNombre(mov.centro || mov.centro_nombre),
  usuario: mov.usuario || mov.usuario_nombre || '',
  lote: mov.lote || mov.lote_numero || '',
  observaciones: mov.observaciones || mov.motivo || '',
  saldo: mov.saldo,
});

const mapLote = (lote = {}) => ({
  id: lote.id,
  numero_lote: lote.numero_lote,
  fecha_caducidad: lote.fecha_caducidad,
  cantidad_actual: lote.cantidad_actual ?? 0,
  cantidad_inicial: lote.cantidad_inicial ?? lote.cantidad_actual ?? 0,
  estado: (lote.estado_caducidad || lote.estado || 'NORMAL').toString().toUpperCase(),
  centro: getCentroNombre(lote.centro),
  numero_contrato: lote.numero_contrato || '',
  marca: lote.marca || '',
  dias_para_caducar: lote.dias_para_caducar,
  precio_unitario: lote.precio_unitario,
});

/**
 * Normaliza respuesta de trazabilidad de PRODUCTO
 * Backend retorna: {codigo, producto: {...}, estadisticas: {...}, lotes: [], movimientos: [], alertas: []}
 */
const normalizeProductoResponse = (data) => {
  if (!data) return null;

  // DEBUG: Log para identificar estructura de datos (remover en producción)
  if (import.meta.env.DEV) {
    console.log('[Trazabilidad] Respuesta producto raw:', data);
  }

  const lotes = Array.isArray(data.lotes) ? data.lotes.map(mapLote) : [];
  const movimientos = Array.isArray(data.movimientos) ? data.movimientos.map(mapMovimiento) : [];

  // Priorizar data.producto si existe (respuesta del backend tiene producto como objeto)
  if (data.producto && typeof data.producto === 'object') {
    const producto = data.producto;
    return {
      tipo: 'producto',
      codigo: producto.clave || producto.codigo || data.codigo || '-',
      nombre: producto.nombre || '',
      descripcion: producto.descripcion || producto.nombre || '',
      presentacion: producto.presentacion || '',
      unidad_medida: producto.unidad_medida || producto.unidad || '-',
      stock_actual: data.estadisticas?.stock_total ?? producto.stock_actual ?? 0,
      stock_minimo: producto.stock_minimo ?? null,
      activo: producto.activo !== false,
      lotes,
      movimientos,
      alertas: data.alertas || [],
      estadisticas: data.estadisticas || {},
    };
  }

  // Fallback: datos directos en la raíz (formato antiguo o alternativo)
  if (data.codigo || data.clave) {
    return {
      tipo: 'producto',
      codigo: data.codigo || data.clave || '-',
      nombre: data.nombre || '',
      descripcion: data.descripcion || data.nombre || '',
      presentacion: data.presentacion || '',
      unidad_medida: data.unidad_medida || data.unidad || '-',
      stock_actual: data.stock_actual ?? data.estadisticas?.stock_total ?? 0,
      stock_minimo: data.stock_minimo ?? data.estadisticas?.stock_minimo ?? null,
      activo: data.activo !== false,
      lotes,
      movimientos,
      alertas: data.alertas || [],
      estadisticas: data.estadisticas || {},
    };
  }

  // Si no hay estructura reconocible, retornar los datos con tipo
  return { ...data, tipo: 'producto' };
};

/**
 * Normaliza respuesta de trazabilidad de LOTE
 * Backend retorna: {id, numero_lote, producto, lote: {...}, estadisticas: {...}, movimientos: [], alertas: []}
 */
const normalizeLoteResponse = (data) => {
  if (!data) return null;

  // DEBUG: Log para identificar estructura de datos (remover en producción)
  if (import.meta.env.DEV) {
    console.log('[Trazabilidad] Respuesta lote raw:', data);
  }

  // El backend envía datos en data.lote para info detallada
  const loteData = data.lote || data;
  const movimientos = Array.isArray(data.movimientos || data.historial) 
    ? (data.movimientos || data.historial).map(mapMovimiento) 
    : [];

  return {
    tipo: 'lote',
    id: data.id || loteData.id,
    numero_lote: loteData.numero_lote || data.numero_lote || '-',
    producto: {
      codigo: loteData.producto || data.producto || '-',
      nombre: loteData.producto_nombre || loteData.producto_descripcion || '',
    },
    fecha_caducidad: loteData.fecha_caducidad,
    dias_para_caducar: loteData.dias_para_caducar,
    cantidad_actual: loteData.cantidad_actual ?? 0,
    cantidad_inicial: loteData.cantidad_inicial ?? 0,
    estado: (loteData.estado_caducidad || loteData.estado || 'NORMAL').toString().toUpperCase(),
    centro: getCentroNombre(loteData.centro),
    numero_contrato: loteData.numero_contrato || '',
    marca: loteData.marca || '',
    precio_unitario: loteData.precio_unitario,
    activo: loteData.activo !== false,
    movimientos,
    alertas: data.alertas || [],
    estadisticas: data.estadisticas || {},
  };
};

// ============================================
// COMPONENTE PRINCIPAL
// ============================================

const Trazabilidad = () => {
  const { getRolPrincipal, permisos, user } = usePermissions();
  const rolPrincipal = getRolPrincipal();
  
  // PERMISOS
  const esAdminOFarmacia = ['ADMIN', 'FARMACIA'].includes(rolPrincipal) || permisos?.isSuperuser;
  const puedeVerContrato = esAdminOFarmacia;
  const esCentroUser = rolPrincipal === 'CENTRO';
  
  // Obtener centro del usuario
  const centroUsuarioNombre = user?.centro?.nombre || user?.centro_nombre || null;

  // Estados principales
  const [codigoBusqueda, setCodigoBusqueda] = useState('');
  const [codigoResultados, setCodigoResultados] = useState('');
  const [loading, setLoading] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [resultados, setResultados] = useState(null);
  
  // Filtro de centro (solo para admin/farmacia)
  const [centros, setCentros] = useState([]);
  const [centroFiltro, setCentroFiltro] = useState('');
  
  // Filtros para exportación global
  const [fechaInicio, setFechaInicio] = useState('');
  const [fechaFin, setFechaFin] = useState('');
  const [exportandoGlobal, setExportandoGlobal] = useState(false);
  
  // Control de debounce
  const debounceRef = useRef(null);
  const lastSearchRef = useRef({ codigo: '', centro: '' });

  // Cargar centros al montar (solo para admin/farmacia)
  useEffect(() => {
    const cargarCentros = async () => {
      if (!esAdminOFarmacia) return;
      
      try {
        const resp = await centrosAPI.getAll({ page_size: 100, ordering: 'nombre', activo: true });
        setCentros(resp.data?.results || resp.data || []);
      } catch (e) {
        console.warn('No se pudieron cargar centros:', e);
      }
    };
    cargarCentros();
  }, [esAdminOFarmacia]);

  // Debounce para el campo de búsqueda
  const handleCodigoBusquedaChange = useCallback((valor) => {
    setCodigoBusqueda(valor);
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
  }, []);

  // Exportar PDF (producto o lote según el tipo de resultado)
  const handleExportarPdf = async () => {
    if (!resultados || !codigoResultados) {
      toast.error('Primero busque un producto o lote para exportar su trazabilidad');
      return;
    }

    const esLote = resultados?.tipo === 'lote';
    setExportingPdf(true);
    try {
      let response;
      let filename;
      
      if (esLote) {
        // Exportar trazabilidad de lote
        response = await trazabilidadAPI.exportarLotePdf(codigoResultados, resultados.id);
        filename = `trazabilidad_lote_${codigoResultados}_${new Date().toISOString().split('T')[0]}.pdf`;
      } else {
        // Exportar trazabilidad de producto
        response = await trazabilidadAPI.exportarPdf(codigoResultados);
        filename = `trazabilidad_producto_${codigoResultados}_${new Date().toISOString().split('T')[0]}.pdf`;
      }
      
      descargarArchivo(response, filename);
      toast.success(`PDF de trazabilidad de ${esLote ? 'lote' : 'producto'} generado`);
    } catch (error) {
      console.error('Error al exportar PDF:', error);
      
      if (error.response?.status === 403) {
        toast.error('No tienes permiso para exportar esta trazabilidad');
      } else if (error.response?.status === 404) {
        toast.error(`${resultados?.tipo === 'lote' ? 'Lote' : 'Producto'} no encontrado para exportar`);
      } else {
        toast.error(error.response?.data?.error || 'Error al generar el PDF');
      }
    } finally {
      setExportingPdf(false);
    }
  };

  // Exportar trazabilidad global de lotes (con filtros de fecha)
  const handleExportarGlobal = async (formato = 'pdf') => {
    if (!esAdminOFarmacia) {
      toast.error('Solo administradores y farmacia pueden exportar reportes globales');
      return;
    }

    setExportandoGlobal(true);
    try {
      const params = {
        formato,
        ...(fechaInicio && { fecha_desde: fechaInicio }),
        ...(fechaFin && { fecha_hasta: fechaFin }),
        ...(centroFiltro && { centro: centroFiltro }),
      };

      const response = await lotesAPI.exportar(params);
      const extension = formato === 'excel' ? 'xlsx' : 'pdf';
      const fechaStr = new Date().toISOString().split('T')[0];
      const filename = `trazabilidad_global_lotes_${fechaStr}.${extension}`;
      
      descargarArchivo(response, filename);
      toast.success(`Reporte global de lotes exportado a ${formato.toUpperCase()}`);
    } catch (error) {
      console.error('Error al exportar reporte global:', error);
      toast.error(error.response?.data?.error || 'Error al generar el reporte global');
    } finally {
      setExportandoGlobal(false);
    }
  };

  const handleBuscar = async (e) => {
    e.preventDefault();

    const codigoTrimmed = codigoBusqueda.trim();
    if (!codigoTrimmed) {
      toast.error('Ingrese clave de producto o número de lote');
      return;
    }

    // Evitar búsquedas duplicadas
    if (lastSearchRef.current.codigo === codigoTrimmed &&
        lastSearchRef.current.centro === centroFiltro &&
        resultados) {
      toast('Ya tienes estos resultados cargados', { icon: 'ℹ️' });
      return;
    }

    setLoading(true);
    try {
      // Preparar parámetros con filtro de centro opcional
      const params = centroFiltro ? { centro: centroFiltro } : {};

      // Intentar primero búsqueda por producto
      try {
        const response = await trazabilidadAPI.producto(codigoTrimmed, params);
        const datosNormalizados = normalizeProductoResponse(response.data);
        
        setResultados(datosNormalizados);
        setCodigoResultados(codigoTrimmed);
        lastSearchRef.current = { codigo: codigoTrimmed, centro: centroFiltro, tipo: 'producto' };
        
        toast.success('Trazabilidad de producto cargada');
        return;
      } catch (errorProducto) {
        // Si no se encuentra producto (404), intentar por lote
        if (errorProducto.response?.status === 404 && esAdminOFarmacia) {
          const responseLote = await trazabilidadAPI.lote(codigoTrimmed, params);
          const datosNormalizados = normalizeLoteResponse(responseLote.data);
          
          setResultados(datosNormalizados);
          setCodigoResultados(codigoTrimmed);
          lastSearchRef.current = { codigo: codigoTrimmed, centro: centroFiltro, tipo: 'lote' };
          
          toast.success('Trazabilidad de lote cargada');
          return;
        }
        // Re-lanzar el error si no es 404 o no es admin
        throw errorProducto;
      }
    } catch (error) {
      if (error.response?.status === 403) {
        toast.error('No tienes permiso para acceder a esta trazabilidad');
      } else if (error.response?.status === 404) {
        toast.error('Producto o lote no encontrado');
      } else {
        toast.error(error.response?.data?.error || 'Error al cargar trazabilidad');
      }
      console.error(error);
      setResultados(null);
      setCodigoResultados('');
    } finally {
      setLoading(false);
    }
  };

  // Limpiar búsqueda
  const limpiarBusqueda = () => {
    if (loading || exportingPdf) {
      toast('Espera a que termine la operación actual', { icon: '⏳' });
      return;
    }
    
    setCodigoBusqueda('');
    setCodigoResultados('');
    setResultados(null);
    setCentroFiltro('');
    lastSearchRef.current = { tipo: '', codigo: '', centro: '' };
    
    // Limpiar debounce pendiente
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
  };

  // ============================================
  // RENDERIZADO DE SECCIONES
  // ============================================

  const renderAlertas = () => {
    if (!resultados?.alertas?.length) return null;

    const badgeClass = (nivel = '') => {
      const valor = nivel.toString().toUpperCase();
      if (valor === 'CRITICO') return 'bg-red-100 text-red-700';
      if (valor === 'ADVERTENCIA') return 'bg-amber-100 text-amber-800';
      return 'bg-blue-100 text-blue-700';
    };

    return (
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <FaExclamationTriangle className="text-amber-500" /> Alertas
        </h3>
        <div className="flex flex-wrap gap-2">
          {resultados.alertas.map((alerta, index) => (
            <span
              key={`${alerta.tipo || 'alerta'}-${index}`}
              className={`px-3 py-1 rounded-full text-xs ${badgeClass(alerta.nivel)}`}
            >
              {alerta.mensaje || alerta.tipo}
            </span>
          ))}
        </div>
      </div>
    );
  };

  const renderInfoProducto = () => (
    <div className="grid gap-4 md:grid-cols-5">
      <div>
        <p className="text-xs text-gray-500">Clave</p>
        <p className="font-semibold">{resultados.codigo || '-'}</p>
      </div>
      <div className="md:col-span-2">
        <p className="text-xs text-gray-500">Descripción</p>
        <p className="font-semibold">{resultados.descripcion || resultados.nombre || '-'}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Unidad</p>
        <p className="font-semibold">{resultados.unidad_medida || '-'}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Presentación</p>
        <p className="font-semibold">{resultados.presentacion || '-'}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Inventario actual</p>
        <p className="text-2xl font-bold text-violet-600">{resultados.stock_actual ?? 0}</p>
      </div>
    </div>
  );

  const renderInfoLote = () => (
    <div className="grid gap-4 md:grid-cols-4">
      <div>
        <p className="text-xs text-gray-500">Número de Lote</p>
        <p className="font-semibold">{resultados.numero_lote || '-'}</p>
      </div>
      <div className="md:col-span-2">
        <p className="text-xs text-gray-500">Producto</p>
        <p className="font-semibold">
          {resultados.producto?.codigo} - {resultados.producto?.nombre || '-'}
        </p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Caducidad</p>
        <p className="font-semibold">
          {resultados.fecha_caducidad ? new Date(resultados.fecha_caducidad).toLocaleDateString() : '-'}
        </p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Cantidad actual</p>
        <p className="text-2xl font-bold text-violet-600">{resultados.cantidad_actual ?? 0}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Cantidad inicial</p>
        <p className="font-semibold">{resultados.cantidad_inicial ?? '-'}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Estado</p>
        <p className="font-semibold">{resultados.estado || '-'}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Centro</p>
        <p className="font-semibold">{resultados.centro || 'Farmacia Central'}</p>
      </div>
      {puedeVerContrato && resultados.numero_contrato && (
        <div>
          <p className="text-xs text-gray-500">Contrato</p>
          <p className="font-semibold text-blue-600">{resultados.numero_contrato}</p>
        </div>
      )}
      {resultados.marca && (
        <div>
          <p className="text-xs text-gray-500">Marca</p>
          <p className="font-semibold">{resultados.marca}</p>
        </div>
      )}
    </div>
  );

  // Determinar si es resultado de producto o lote
  const esResultadoLote = resultados?.tipo === 'lote';

  const lotesParaMostrar = Array.isArray(resultados?.lotes) ? resultados.lotes : [];
  const movimientosParaMostrar = Array.isArray(resultados?.movimientos) 
    ? resultados.movimientos.slice(0, 100) 
    : [];
  const totalMovimientos = resultados?.movimientos?.length || 0;
  
  // Mostrar columna de saldo solo si los movimientos tienen el campo saldo (trazabilidad de lote)
  const mostrarSaldo = esResultadoLote && movimientosParaMostrar.some(mov => mov.saldo !== undefined);

  const estadoClass = (estado = '') => {
    const upper = estado.toUpperCase();
    if (upper.includes('VENCIDO') || upper.includes('AGOTADO')) return 'bg-red-100 text-red-700';
    if (upper.includes('CRITICO') || upper.includes('PROXIMO')) return 'bg-amber-100 text-amber-800';
    return 'bg-emerald-100 text-emerald-700';
  };

  // Badge de contexto para el header
  const badgeContent = esCentroUser && centroUsuarioNombre ? (
    <span className="flex items-center gap-2 rounded-full bg-white/20 px-4 py-1 text-sm font-semibold">
      <FaBuilding />
      {centroUsuarioNombre}
    </span>
  ) : null;

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        icon={FaHistory}
        title="Trazabilidad"
        subtitle={`Consulta el historial completo de productos | Rol: ${rolPrincipal}`}
        badge={badgeContent}
      />

      {/* Banner para usuarios CENTRO indicando filtro automático */}
      {esCentroUser && centroUsuarioNombre && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center gap-3">
          <div className="bg-blue-100 p-2 rounded-lg">
            <FaInfoCircle className="text-blue-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-blue-800">
              Trazabilidad de: {centroUsuarioNombre}
            </p>
            <p className="text-xs text-blue-600">
              Los resultados se filtran automáticamente por tu centro asignado.
            </p>
          </div>
        </div>
      )}

      <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
        <form onSubmit={handleBuscar}>
          {/* Formulario - Búsqueda por producto o lote */}
          <div className="flex flex-wrap items-end gap-4">
            {/* Campo de búsqueda principal */}
            <div className="flex-1 min-w-[300px]">
              <label className="block text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                <FaSearch className="text-violet-500" />
                Buscar por Clave de Producto o Número de Lote
              </label>
              <AutocompleteInput
                apiCall={productosAPI.getAll}
                value={codigoBusqueda}
                onChange={handleCodigoBusquedaChange}
                placeholder="Escribe clave, nombre, descripción o número de lote..."
                displayField="clave"
                secondaryField="nombre"
                searchField="search"
                mode="product"
                minChars={1}
                disabled={loading}
                className="border-2 border-gray-300"
              />
            </div>

            {/* Selector de centro (solo para admin/farmacia) */}
            {esAdminOFarmacia && (
              <div className="w-52">
                <label className="block text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                  <FaBuilding className="text-gray-500" />
                  Centro
                </label>
                <select
                  value={centroFiltro}
                  onChange={(e) => setCentroFiltro(e.target.value)}
                  className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-violet-500 bg-white text-sm font-medium"
                  disabled={loading}
                >
                  <option value="">Todos los centros</option>
                  <option value="central">🏥 Farmacia Central</option>
                  {centros.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nombre}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Botones de acción */}
            <button
              type="submit"
              disabled={loading || !codigoBusqueda.trim()}
              className="bg-violet-600 text-white px-6 py-2.5 rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-all font-semibold shadow-md"
            >
              {loading ? (
                <>
                  <FaSpinner className="animate-spin" />
                  Buscando...
                </>
              ) : (
                <>
                  <FaSearch /> Buscar
                </>
              )}
            </button>
            <button
              type="button"
              onClick={limpiarBusqueda}
              disabled={loading || exportingPdf}
              className="px-5 py-2.5 border-2 border-gray-400 rounded-lg hover:bg-gray-100 hover:border-gray-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-gray-700 font-semibold bg-white shadow-sm"
            >
              Limpiar
            </button>
          </div>
        </form>
      </div>

      {/* Sección de Exportación Global (solo para admin/farmacia) */}
      {esAdminOFarmacia && (
        <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
          <div className="flex items-center gap-3 mb-4">
            <div className="bg-emerald-100 p-2 rounded-lg">
              <FaDownload className="text-emerald-600" />
            </div>
            <div>
              <h3 className="font-bold text-gray-800">Exportación Global de Lotes</h3>
              <p className="text-sm text-gray-600">Descarga trazabilidad de todos los lotes con filtros opcionales</p>
            </div>
          </div>
          
          <div className="flex flex-wrap items-end gap-4">
            {/* Fecha inicio */}
            <div className="w-40">
              <label className="block text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                <FaCalendarAlt className="text-gray-500" />
                Desde
              </label>
              <input
                type="date"
                value={fechaInicio}
                onChange={(e) => setFechaInicio(e.target.value)}
                className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 bg-white text-sm"
                disabled={exportandoGlobal}
              />
            </div>
            
            {/* Fecha fin */}
            <div className="w-40">
              <label className="block text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                <FaCalendarAlt className="text-gray-500" />
                Hasta
              </label>
              <input
                type="date"
                value={fechaFin}
                onChange={(e) => setFechaFin(e.target.value)}
                className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 bg-white text-sm"
                disabled={exportandoGlobal}
              />
            </div>
            
            {/* Selector de centro para exportación global */}
            <div className="w-52">
              <label className="block text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                <FaBuilding className="text-gray-500" />
                Centro
              </label>
              <select
                value={centroFiltro}
                onChange={(e) => setCentroFiltro(e.target.value)}
                className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 bg-white text-sm font-medium"
                disabled={exportandoGlobal}
              >
                <option value="">Todos los centros</option>
                <option value="central">🏥 Farmacia Central</option>
                {centros.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre}
                  </option>
                ))}
              </select>
            </div>

            {/* Botones de exportación */}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => handleExportarGlobal('pdf')}
                disabled={exportandoGlobal}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg font-semibold text-white transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                style={{ background: 'linear-gradient(135deg, #DC2626 0%, #991B1B 100%)' }}
                title="Exportar a PDF"
              >
                {exportandoGlobal ? (
                  <FaSpinner className="animate-spin" />
                ) : (
                  <FaFilePdf />
                )}
                PDF
              </button>
              <button
                type="button"
                onClick={() => handleExportarGlobal('excel')}
                disabled={exportandoGlobal}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg font-semibold text-white transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                style={{ background: 'linear-gradient(135deg, #059669 0%, #047857 100%)' }}
                title="Exportar a Excel"
              >
                {exportandoGlobal ? (
                  <FaSpinner className="animate-spin" />
                ) : (
                  <FaFileExcel />
                )}
                Excel
              </button>
            </div>
          </div>
          
          <p className="text-xs text-gray-500 mt-3">
            💡 Deja las fechas vacías para exportar todos los lotes. El reporte incluye: número de lote, producto, cantidades, caducidad, estado, centro, contrato y marca.
          </p>
        </div>
      )}

      {/* Indicador de código sincronizado */}
      {resultados && codigoResultados && codigoBusqueda !== codigoResultados && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-center gap-2 text-amber-700">
          <FaExclamationTriangle />
          <span className="text-sm">
            Los resultados corresponden a: <strong>{codigoResultados}</strong>. 
            Presiona "Buscar" para actualizar.
          </span>
        </div>
      )}

      {/* Estado de carga */}
      {loading && (
        <div className="text-center py-8 bg-white rounded-lg shadow">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-t-transparent mx-auto spinner-institucional" />
          <p className="mt-3 text-gray-600">Buscando información...</p>
        </div>
      )}

      {/* Estado vacío */}
      {!loading && !resultados && (
        <div className="text-center py-8 bg-white rounded-lg shadow">
          <FaSearch className="text-4xl text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">
            Ingresa la clave de un producto o número de lote y presiona &quot;Buscar&quot;
          </p>
          {!esAdminOFarmacia && (
            <p className="text-xs text-gray-400 mt-2">
              Nota: Los resultados se filtran automáticamente por tu centro asignado
            </p>
          )}
        </div>
      )}

      {/* Resultados */}
      {!loading && resultados && (
        <div className="space-y-6">
          {/* Información principal */}
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="bg-violet-100 p-3 rounded-lg">
                  {esResultadoLote ? (
                    <FaWarehouse className="text-violet-600 text-2xl" />
                  ) : (
                    <FaBox className="text-violet-600 text-2xl" />
                  )}
                </div>
                <div>
                  <h2 className="text-lg font-bold">
                    Información del {esResultadoLote ? 'lote' : 'producto'}
                  </h2>
                  <p className="text-sm text-gray-600">
                    Datos generales y estado actual
                    {codigoResultados && (
                      <span className="ml-2 text-violet-600 font-medium">({codigoResultados})</span>
                    )}
                  </p>
                </div>
              </div>
              
              {/* Botón de exportar PDF */}
              <button
                onClick={handleExportarPdf}
                disabled={exportingPdf || !resultados}
                className="flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-white transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                style={{ background: 'linear-gradient(135deg, #DC2626 0%, #991B1B 100%)' }}
                title="Exportar trazabilidad a PDF"
              >
                {exportingPdf ? (
                  <>
                    <FaSpinner className="animate-spin" />
                    Generando...
                  </>
                ) : (
                  <>
                    <FaFilePdf />
                    Exportar PDF
                  </>
                )}
              </button>
            </div>
            
            {esResultadoLote ? renderInfoLote() : renderInfoProducto()}
          </div>

          {/* Alertas */}
          {renderAlertas()}

          {/* Lotes asociados (solo para productos) */}
          {!esResultadoLote && lotesParaMostrar.length > 0 && (
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <FaWarehouse /> Lotes asociados ({lotesParaMostrar.length})
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left font-semibold">Lote</th>
                      <th className="px-4 py-2 text-left font-semibold">Caducidad</th>
                      <th className="px-4 py-2 text-left font-semibold">Inventario</th>
                      {puedeVerContrato && <th className="px-4 py-2 text-left font-semibold">Contrato</th>}
                      {puedeVerContrato && <th className="px-4 py-2 text-left font-semibold">Marca</th>}
                      <th className="px-4 py-2 text-left font-semibold">Estado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {lotesParaMostrar.map((lote, idx) => (
                      <tr key={lote.id || lote.numero_lote || idx} className="hover:bg-gray-50">
                        <td className="px-4 py-2 font-semibold">{lote.numero_lote || '-'}</td>
                        <td className="px-4 py-2">
                          {lote.fecha_caducidad ? new Date(lote.fecha_caducidad).toLocaleDateString() : '-'}
                        </td>
                        <td className="px-4 py-2">{lote.cantidad_actual}</td>
                        {puedeVerContrato && <td className="px-4 py-2 text-gray-600">{lote.numero_contrato || '-'}</td>}
                        {puedeVerContrato && <td className="px-4 py-2 text-gray-600">{lote.marca || '-'}</td>}
                        <td className="px-4 py-2">
                          <span className={`px-2 py-1 text-xs rounded-full ${estadoClass(lote.estado)}`}>
                            {lote.estado || '-'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Historial de movimientos */}
          {movimientosParaMostrar.length > 0 && (
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <FaHistory /> Historial de movimientos
                {totalMovimientos > 100 && (
                  <span className="text-sm font-normal text-gray-500">
                    (mostrando 100 de {totalMovimientos})
                  </span>
                )}
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left font-semibold">Fecha</th>
                      <th className="px-4 py-2 text-left font-semibold">Tipo</th>
                      <th className="px-4 py-2 text-left font-semibold">Cantidad</th>
                      {mostrarSaldo && <th className="px-4 py-2 text-left font-semibold" title="Cantidad restante del lote después del movimiento">Saldo Lote</th>}
                      <th className="px-4 py-2 text-left font-semibold">Centro</th>
                      <th className="px-4 py-2 text-left font-semibold">Usuario</th>
                      <th className="px-4 py-2 text-left font-semibold">Lote</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {movimientosParaMostrar.map((mov, idx) => (
                      <tr key={mov.id || idx} className="hover:bg-gray-50">
                        <td className="px-4 py-2">
                          {mov.fecha ? new Date(mov.fecha).toLocaleString() : '-'}
                        </td>
                        <td className="px-4 py-2">
                          <span
                            className={`px-2 py-1 text-xs rounded-full ${
                              mov.tipo === 'ENTRADA'
                                ? 'bg-blue-100 text-blue-700'
                                : mov.tipo === 'AJUSTE'
                                  ? 'bg-gray-100 text-gray-700'
                                  : 'bg-orange-100 text-orange-700'
                            }`}
                          >
                            {mov.tipo}
                          </span>
                        </td>
                        <td className="px-4 py-2 font-semibold">{mov.cantidad}</td>
                        {mostrarSaldo && (
                          <td className="px-4 py-2" title="Cantidad del lote después de este movimiento">
                            {mov.saldo ?? '-'}
                          </td>
                        )}
                        <td className="px-4 py-2">{mov.centro || 'Farmacia Central'}</td>
                        <td className="px-4 py-2">{mov.usuario || '-'}</td>
                        <td className="px-4 py-2">{mov.lote || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {totalMovimientos > 100 && (
                <p className="text-xs text-gray-500 mt-3 text-center">
                  Para ver el historial completo, exporta el PDF de trazabilidad
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Trazabilidad;
