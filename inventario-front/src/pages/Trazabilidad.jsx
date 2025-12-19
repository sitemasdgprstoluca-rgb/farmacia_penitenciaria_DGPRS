import { useState, useEffect, useCallback, useRef } from 'react';
import { trazabilidadAPI, productosAPI, centrosAPI, descargarArchivo } from '../services/api';
import { toast } from 'react-hot-toast';
import { FaSearch, FaBox, FaWarehouse, FaHistory, FaExclamationTriangle, FaFilePdf, FaBuilding, FaSpinner, FaInfoCircle } from 'react-icons/fa';
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
      nombre: data.nombre || data.descripcion || '',
      descripcion: data.descripcion || data.nombre || '',
      presentacion: data.presentacion || '',
      unidad_medida: data.unidad_medida || data.unidad || '-',
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
      nombre: producto.nombre || producto.descripcion || '',
      descripcion: producto.descripcion || producto.nombre || '',
      presentacion: producto.presentacion || '',
      unidad_medida: producto.unidad_medida || producto.unidad || '-',
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

  // Exportar PDF
  const handleExportarPdf = async () => {
    if (!resultados || !codigoResultados) {
      toast.error('Primero busque un producto para exportar su trazabilidad');
      return;
    }

    setExportingPdf(true);
    try {
      const response = await trazabilidadAPI.exportarPdf(codigoResultados);
      const filename = `trazabilidad_${codigoResultados}_${new Date().toISOString().split('T')[0]}.pdf`;
      
      descargarArchivo(response, filename);
      toast.success('PDF de trazabilidad generado exitosamente');
    } catch (error) {
      console.error('Error al exportar PDF:', error);
      
      if (error.response?.status === 403) {
        toast.error('No tienes permiso para exportar esta trazabilidad');
      } else if (error.response?.status === 404) {
        toast.error('Producto no encontrado para exportar');
      } else {
        toast.error(error.response?.data?.error || 'Error al generar el PDF');
      }
    } finally {
      setExportingPdf(false);
    }
  };

  const handleBuscar = async (e) => {
    e.preventDefault();

    const codigoTrimmed = codigoBusqueda.trim();
    if (!codigoTrimmed) {
      toast.error('Ingrese clave, nombre o descripción del producto');
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

      const response = await trazabilidadAPI.producto(codigoTrimmed, params);
      const datosNormalizados = normalizeProductoResponse(response.data);
      
      setResultados(datosNormalizados);
      setCodigoResultados(codigoTrimmed);
      lastSearchRef.current = { codigo: codigoTrimmed, centro: centroFiltro };
      
      toast.success('Trazabilidad cargada correctamente');
    } catch (error) {
      if (error.response?.status === 403) {
        toast.error('No tienes permiso para acceder a esta trazabilidad');
      } else if (error.response?.status === 404) {
        toast.error('Producto no encontrado');
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

  const lotesParaMostrar = Array.isArray(resultados?.lotes) ? resultados.lotes : [];
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
          {/* Formulario simplificado - Solo búsqueda por producto */}
          <div className="flex flex-wrap items-end gap-4">
            {/* Campo de búsqueda principal */}
            <div className="flex-1 min-w-[300px]">
              <label className="block text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                <FaBox className="text-violet-500" />
                Buscar Producto
              </label>
              <AutocompleteInput
                apiCall={productosAPI.getAll}
                  value={codigoBusqueda}
                onChange={handleCodigoBusquedaChange}
                placeholder="Escribe clave, nombre o descripción del producto..."
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
            Ingresa la clave de un producto y presiona &quot;Buscar&quot;
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
                  <FaBox className="text-violet-600 text-2xl" />
                </div>
                <div>
                  <h2 className="text-lg font-bold">
                    Información del producto
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
            
            {renderInfoProducto()}
          </div>

          {/* Alertas */}
          {renderAlertas()}

          {/* Lotes asociados */}
          {lotesParaMostrar.length > 0 && (
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
