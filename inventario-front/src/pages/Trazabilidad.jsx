import { useState, useEffect, useCallback, useRef } from 'react';
import { trazabilidadAPI, productosAPI, lotesAPI, centrosAPI, descargarArchivo } from '../services/api';
import { toast } from 'react-hot-toast';
import { FaSearch, FaBox, FaWarehouse, FaHistory, FaExclamationTriangle, FaFilePdf, FaBuilding, FaLock, FaSpinner, FaInfoCircle } from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import AutocompleteInput from '../components/AutocompleteInput';
import { usePermissions } from '../hooks/usePermissions';

// ============================================
// MAPEO Y NORMALIZACIÓN DE DATOS
// ============================================

const mapMovimiento = (mov = {}) => ({
  id: mov.id,
  fecha: mov.fecha || mov.fecha_movimiento || mov.fecha_mov || null,
  tipo: (mov.tipo || mov.tipo_movimiento || '').toString().toUpperCase(),
  cantidad: mov.cantidad,
  centro: mov.centro || mov.centro_nombre || '',
  usuario: mov.usuario || mov.usuario_nombre || '',
  lote: mov.lote || mov.lote_numero || '',
  observaciones: mov.observaciones || '',
  saldo: mov.saldo,
});

const mapLote = (lote = {}) => ({
  numero_lote: lote.numero_lote,
  fecha_caducidad: lote.fecha_caducidad,
  cantidad_actual: lote.cantidad_actual,
  cantidad_inicial: lote.cantidad_inicial ?? lote.cantidad_actual,
  estado: (lote.estado || lote.estado_caducidad || '').toString().toUpperCase(),
  centro: lote.centro,
  numero_contrato: lote.numero_contrato || '',
  marca: lote.marca || '',
});

const normalizeProductoResponse = (data) => {
  if (!data) return null;

  const lotes = Array.isArray(data.lotes) ? data.lotes.map(mapLote) : [];
  const movimientos = Array.isArray(data.movimientos) ? data.movimientos.map(mapMovimiento) : [];

  if (data.codigo) {
    return {
      codigo: data.codigo,
      nombre: data.nombre,
      presentacion: data.presentacion || '',
      unidad_medida: data.unidad_medida,
      stock_actual: data.stock_actual ?? data.estadisticas?.stock_total ?? 0,
      stock_minimo: data.stock_minimo ?? data.estadisticas?.stock_minimo ?? null,
      lotes,
      movimientos,
      alertas: data.alertas || [],
      estadisticas: data.estadisticas || {},
    };
  }

  if (data.producto) {
    const producto = data.producto;
    return {
      codigo: producto.clave || producto.codigo,
      nombre: producto.nombre || producto.descripcion || '',  // Usar nombre o descripcion como fallback
      presentacion: producto.presentacion || '',
      unidad_medida: producto.unidad_medida,
      stock_actual: data.estadisticas?.stock_total ?? producto.stock_actual ?? 0,
      stock_minimo: producto.stock_minimo ?? null,
      lotes,
      movimientos,
      alertas: data.alertas || [],
      estadisticas: data.estadisticas || {},
    };
  }

  return data;
};

const normalizeLoteResponse = (data) => {
  if (!data) return null;

  // Estructura donde data.lote contiene los datos del lote
  if (data.lote) {
    const lote = data.lote;
    return {
      // ISS-FIX: Priorizar data.id (raíz) que siempre viene del backend
      id: data.id || lote.id,
      numero_lote: lote.numero_lote,
      producto: {
        codigo: lote.producto,
        nombre: lote.producto_nombre || lote.producto_descripcion,
      },
      fecha_caducidad: lote.fecha_caducidad,
      cantidad_actual: lote.cantidad_actual,
      cantidad_inicial: lote.cantidad_inicial,
      estado: (lote.estado_caducidad || lote.estado || '').toString().toUpperCase(),
      centro: lote.centro,
      numero_contrato: lote.numero_contrato || '',
      marca: lote.marca || '',
      movimientos: (data.movimientos || data.historial || []).map(mapMovimiento),
      alertas: data.alertas || [],
      estadisticas: data.estadisticas || {},
    };
  }

  // Estructura donde data tiene los campos directamente
  if (data.numero_lote) {
    return {
      id: data.id,  // ISS-FIX: Guardar ID para exportación precisa
      numero_lote: data.numero_lote,
      producto: data.producto || {},
      fecha_caducidad: data.fecha_caducidad,
      cantidad_actual: data.cantidad_actual,
      cantidad_inicial: data.cantidad_inicial,
      estado: (data.estado || data.estado_caducidad || '').toString().toUpperCase(),
      centro: data.centro,
      numero_contrato: data.numero_contrato || '',
      marca: data.marca || '',
      movimientos: (data.movimientos || []).map(mapMovimiento),
      alertas: data.alertas || [],
      estadisticas: data.estadisticas || {},
    };
  }

  return data;
};

// ============================================
// COMPONENTE PRINCIPAL
// ============================================

const Trazabilidad = () => {
  const { getRolPrincipal, permisos, user } = usePermissions();
  const rolPrincipal = getRolPrincipal();
  
  // PERMISOS: Solo ADMIN y FARMACIA pueden buscar por lote y ver contratos
  const esAdminOFarmacia = ['ADMIN', 'FARMACIA'].includes(rolPrincipal) || permisos?.isSuperuser;
  const puedeVerContrato = esAdminOFarmacia;
  const puedeBuscarPorLote = esAdminOFarmacia;
  const esCentroUser = rolPrincipal === 'CENTRO';
  
  // ISS-FIX: Obtener centro del usuario desde el hook en lugar de localStorage
  const centroUsuarioId = user?.centro?.id || user?.centro || user?.centro_id;
  const centroUsuarioNombre = user?.centro?.nombre || user?.centro_nombre || null;

  // Estados principales
  const [tipoBusqueda, setTipoBusqueda] = useState('producto');
  const [codigoBusqueda, setCodigoBusqueda] = useState('');
  const [codigoResultados, setCodigoResultados] = useState(''); // Código sincronizado con resultados
  const [loading, setLoading] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [resultados, setResultados] = useState(null);
  
  // Filtro de centro (solo para admin/farmacia)
  const [centros, setCentros] = useState([]);
  const [centroFiltro, setCentroFiltro] = useState('');
  
  // Control de debounce para evitar múltiples llamadas
  const debounceRef = useRef(null);
  const lastSearchRef = useRef({ tipo: '', codigo: '', centro: '' });

  // Cargar centros al montar (solo para admin/farmacia)
  useEffect(() => {
    const cargarCentros = async () => {
      if (!esAdminOFarmacia) {
        // Usuario de centro: el centro se obtiene del hook usePermissions
        return;
      }
      
      try {
        const resp = await centrosAPI.getAll({ page_size: 100, ordering: 'nombre', activo: true });
        setCentros(resp.data?.results || resp.data || []);
      } catch (e) {
        console.warn('No se pudieron cargar centros:', e);
      }
    };
    cargarCentros();
  }, [esAdminOFarmacia]);

  // Cambiar tipo de búsqueda con validación de permisos
  const handleTipoBusquedaChange = (nuevoTipo) => {
    if (nuevoTipo === 'lote' && !puedeBuscarPorLote) {
      toast.error('Solo administradores y farmacia pueden buscar por lote');
      return;
    }
    setTipoBusqueda(nuevoTipo);
    setCodigoBusqueda('');
    setResultados(null);
    setCodigoResultados('');
  };

  // Debounce para el campo de búsqueda
  const handleCodigoBusquedaChange = useCallback((valor) => {
    setCodigoBusqueda(valor);
    
    // Debounce: no limpiar resultados inmediatamente
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
  }, []);

  // Exportar PDF con código sincronizado
  const handleExportarPdf = async () => {
    if (!resultados || !codigoResultados) {
      toast.error('Primero busque un producto o lote para exportar su trazabilidad');
      return;
    }

    // Validar permisos para lotes
    if (tipoBusqueda === 'lote' && !esAdminOFarmacia) {
      toast.error('No tienes permiso para exportar trazabilidad de lotes');
      return;
    }

    setExportingPdf(true);
    try {
      let response;
      let filename;
      
      // Usar codigoResultados (sincronizado) en lugar de codigoBusqueda
      const codigoParaExportar = codigoResultados;
      
      if (tipoBusqueda === 'producto') {
        response = await trazabilidadAPI.exportarPdf(codigoParaExportar);
        filename = `trazabilidad_producto_${codigoParaExportar}_${new Date().toISOString().split('T')[0]}.pdf`;
      } else {
        // ISS-FIX: Usar lote_id para evitar ambigüedad, SIEMPRE pasar numero_lote como fallback
        const loteId = resultados?.id;
        console.log('[Trazabilidad] Exportando PDF lote:', { codigoParaExportar, loteId, resultados_id: resultados?.id });
        response = await trazabilidadAPI.exportarLotePdf(codigoParaExportar, loteId);
        filename = `trazabilidad_lote_${codigoParaExportar}_${new Date().toISOString().split('T')[0]}.pdf`;
      }
      
      descargarArchivo(response, filename);
      toast.success('PDF de trazabilidad generado exitosamente');
    } catch (error) {
      console.error('Error al exportar PDF:', error);
      
      // Manejo específico de errores
      if (error.response?.status === 403) {
        toast.error('No tienes permiso para exportar esta trazabilidad');
      } else if (error.response?.status === 404) {
        toast.error('El registro no fue encontrado para exportar');
      } else {
        toast.error(error.response?.data?.error || 'Error al generar el PDF de trazabilidad');
      }
    } finally {
      setExportingPdf(false);
    }
  };

  const handleBuscar = async (e) => {
    e.preventDefault();

    const codigoTrimmed = codigoBusqueda.trim();
    if (!codigoTrimmed) {
      toast.error('Ingrese un código para buscar');
      return;
    }

    // Validar permisos para lotes
    if (tipoBusqueda === 'lote' && !puedeBuscarPorLote) {
      toast.error('No tienes permiso para buscar por lote. Solo administradores y farmacia pueden hacerlo.');
      return;
    }

    // Evitar búsquedas duplicadas
    if (lastSearchRef.current.tipo === tipoBusqueda && 
        lastSearchRef.current.codigo === codigoTrimmed &&
        lastSearchRef.current.centro === centroFiltro &&
        resultados) {
      toast('Ya tienes estos resultados cargados', { icon: 'ℹ️' });
      return;
    }

    setLoading(true);
    try {
      const normalizer = tipoBusqueda === 'producto' ? normalizeProductoResponse : normalizeLoteResponse;
      
      // Preparar parámetros con filtro de centro opcional (solo para admin/farmacia)
      const params = centroFiltro ? { centro: centroFiltro } : {};

      const response = tipoBusqueda === 'producto'
        ? await trazabilidadAPI.producto(codigoTrimmed, params)
        : await trazabilidadAPI.lote(codigoTrimmed, params);

      const datosNormalizados = normalizer(response.data);
      setResultados(datosNormalizados);
      setCodigoResultados(codigoTrimmed); // Sincronizar código con resultados
      lastSearchRef.current = { tipo: tipoBusqueda, codigo: codigoTrimmed, centro: centroFiltro };
      
      toast.success('Trazabilidad cargada correctamente');
    } catch (error) {
      // Manejo específico de errores HTTP
      if (error.response?.status === 403) {
        toast.error('No tienes permiso para acceder a esta trazabilidad. Verifica tu rol.');
      } else if (error.response?.status === 404) {
        toast.error(`${tipoBusqueda === 'producto' ? 'Producto' : 'Lote'} no encontrado`);
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

  // Limpiar búsqueda - restablece TODOS los estados
  const limpiarBusqueda = () => {
    // No permitir limpiar mientras hay operaciones activas
    if (loading || exportingPdf) {
      toast('Espera a que termine la operación actual', { icon: '⏳' });
      return;
    }
    
    setCodigoBusqueda('');
    setCodigoResultados('');
    setResultados(null);
    setTipoBusqueda('producto'); // Restablecer a producto (siempre permitido)
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
    <div className="grid gap-4 md:grid-cols-4">
      <div>
        <p className="text-xs text-gray-500">Clave</p>
        <p className="font-semibold">{resultados.codigo}</p>
      </div>
      <div className="md:col-span-2">
        <p className="text-xs text-gray-500">Descripción</p>
        <p className="font-semibold">{resultados.nombre}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Unidad</p>
        <p className="font-semibold">{resultados.unidad_medida}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Inventario actual</p>
        <p className="text-2xl font-bold text-violet-600">{resultados.stock_actual ?? 0}</p>
      </div>
      {resultados.presentacion && (
        <div className="md:col-span-2">
          <p className="text-xs text-gray-500">Presentación</p>
          <p className="font-semibold">{resultados.presentacion}</p>
        </div>
      )}
    </div>
  );

  const renderInfoLote = () => (
    <div className="grid gap-4 md:grid-cols-4">
      <div>
        <p className="text-xs text-gray-500">Número de Lote</p>
        <p className="font-semibold">{resultados.numero_lote}</p>
      </div>
      <div className="md:col-span-2">
        <p className="text-xs text-gray-500">Producto</p>
        <p className="font-semibold">
          {resultados.producto?.codigo} - {resultados.producto?.nombre}
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
        <p className="text-2xl font-bold text-violet-600">{resultados.cantidad_actual}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Cantidad inicial</p>
        <p className="font-semibold">{resultados.cantidad_inicial}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Estado</p>
        <p className="font-semibold">{resultados.estado || '-'}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Centro</p>
        <p className="font-semibold">{resultados.centro || 'Farmacia Central'}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Marca</p>
        <p className="font-semibold">{resultados.marca || '-'}</p>
      </div>
      {/* Campos de trazabilidad de contratos - Solo visible para ADMIN y FARMACIA */}
      {puedeVerContrato && (
        <div>
          <p className="text-xs text-gray-500">Número de Contrato</p>
          <p className="font-semibold text-blue-600">{resultados.numero_contrato || '-'}</p>
        </div>
      )}
    </div>
  );

  const mostrarSaldo = tipoBusqueda === 'lote' && Array.isArray(resultados?.movimientos)
    && resultados.movimientos.some((mov) => mov.saldo !== undefined && mov.saldo !== null);

  const lotesParaMostrar = Array.isArray(resultados?.lotes) ? resultados.lotes : [];
  // Limitar movimientos mostrados para evitar tablas muy pesadas
  const movimientosParaMostrar = Array.isArray(resultados?.movimientos) 
    ? resultados.movimientos.slice(0, 100) 
    : [];
  const totalMovimientos = resultados?.movimientos?.length || 0;

  const estadoClass = (estado = '') => {
    const upper = estado.toUpperCase();
    if (upper.includes('VENCIDO') || upper.includes('AGOTADO')) return 'bg-red-100 text-red-700';
    if (upper.includes('CRITICO') || upper.includes('PROXIMO')) return 'bg-amber-100 text-amber-800';
    return 'bg-emerald-100 text-emerald-700';
  };

  // Badge de contexto para el header - muestra rol y centro si aplica
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
        subtitle={`Consulta el historial completo de productos y lotes | Rol: ${rolPrincipal}`}
        badge={badgeContent}
      />

      {/* ISS-FIX: Banner para usuarios CENTRO indicando filtro automático */}
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

      <div className="bg-white p-6 rounded-lg shadow">
        <form onSubmit={handleBuscar} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-5">
            {/* Selector de tipo de búsqueda */}
            <div>
              <label className="block text-sm font-medium mb-2">Buscar por</label>
              <select
                value={tipoBusqueda}
                onChange={(e) => handleTipoBusquedaChange(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              >
                <option value="producto">📦 Producto</option>
                {puedeBuscarPorLote ? (
                  <option value="lote">🏷️ Lote</option>
                ) : (
                  <option value="lote" disabled>🔒 Lote (requiere permisos)</option>
                )}
              </select>
              {!puedeBuscarPorLote && (
                <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                  <FaLock className="text-gray-400" />
                  Solo Admin/Farmacia
                </p>
              )}
            </div>

            {/* Campo de búsqueda con autocomplete */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-2">
                {tipoBusqueda === 'producto' ? 'Buscar producto (clave, nombre o descripción)' : 'Número de lote'}
              </label>
              {tipoBusqueda === 'producto' ? (
                <AutocompleteInput
                  apiCall={productosAPI.getAll}
                  value={codigoBusqueda}
                  onChange={handleCodigoBusquedaChange}
                  placeholder="Escribe para buscar... Ej: Paracetamol, MED-001"
                  displayField="clave"
                  secondaryField="nombre"
                  searchField="search"
                  mode="product"
                  minChars={1}
                  disabled={loading}
                />
              ) : (
                <AutocompleteInput
                  apiCall={lotesAPI.getAll}
                  value={codigoBusqueda}
                  onChange={handleCodigoBusquedaChange}
                  placeholder="Escribe número de lote... Ej: L-2024-001"
                  displayField="numero_lote"
                  searchField="search"
                  mode="lote"
                  minChars={1}
                  disabled={loading}
                />
              )}
            </div>

            {/* Selector de centro (solo para admin/farmacia) */}
            {esAdminOFarmacia && (
              <div>
                <label className="block text-sm font-medium mb-2">Centro</label>
                <select
                  value={centroFiltro}
                  onChange={(e) => setCentroFiltro(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
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
            <div className="flex items-end gap-2">
              <button
                type="submit"
                disabled={loading || !codigoBusqueda.trim()}
                className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-all"
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
                className="px-4 py-2 border rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                Limpiar
              </button>
            </div>
          </div>

          {/* Indicador de código sincronizado */}
          {resultados && codigoResultados && codigoBusqueda !== codigoResultados && (
            <div className="text-xs text-amber-600 flex items-center gap-1 mt-2">
              <FaExclamationTriangle />
              Los resultados corresponden a: <strong>{codigoResultados}</strong>. 
              Presiona &quot;Buscar&quot; para actualizar con el nuevo código.
            </div>
          )}
        </form>
      </div>

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
                  {tipoBusqueda === 'producto' ? (
                    <FaBox className="text-violet-600 text-2xl" />
                  ) : (
                    <FaWarehouse className="text-violet-600 text-2xl" />
                  )}
                </div>
                <div>
                  <h2 className="text-lg font-bold">
                    Información del {tipoBusqueda === 'producto' ? 'producto' : 'lote'}
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
                disabled={exportingPdf || !resultados || (tipoBusqueda === 'lote' && !esAdminOFarmacia)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-white transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                style={{ background: 'linear-gradient(135deg, #DC2626 0%, #991B1B 100%)' }}
                title={!esAdminOFarmacia && tipoBusqueda === 'lote' ? 'Requiere permisos de Admin/Farmacia' : 'Exportar trazabilidad a PDF'}
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
            
            {tipoBusqueda === 'producto' ? renderInfoProducto() : renderInfoLote()}
          </div>

          {/* Alertas */}
          {renderAlertas()}

          {/* Lotes asociados (solo para productos) */}
          {tipoBusqueda === 'producto' && lotesParaMostrar.length > 0 && (
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
                    {lotesParaMostrar.map((lote) => (
                      <tr key={lote.numero_lote} className="hover:bg-gray-50">
                        <td className="px-4 py-2 font-semibold">{lote.numero_lote}</td>
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
