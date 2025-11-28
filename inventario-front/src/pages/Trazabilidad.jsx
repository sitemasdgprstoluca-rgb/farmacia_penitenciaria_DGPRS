import { useState } from 'react';
import { trazabilidadAPI, productosAPI, lotesAPI, descargarArchivo } from '../services/api';
import { toast } from 'react-hot-toast';
import { FaSearch, FaBox, FaWarehouse, FaHistory, FaExclamationTriangle, FaFilePdf } from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import AutocompleteInput from '../components/AutocompleteInput';
import { usePermissions } from '../hooks/usePermissions';

const MOCK_PRODUCTO = {
  codigo: 'MED-001',
  descripcion: 'Paracetamol 500mg tabletas',
  unidad_medida: 'TABLETA',
  stock_actual: 320,
  stock_minimo: 50,
  alertas: [],
  lotes: [
    {
      numero_lote: 'L-2024-001',
      fecha_caducidad: new Date(Date.now() + 60 * 86400000).toISOString(),
      cantidad_actual: 150,
      cantidad_inicial: 150,
      estado: 'DISPONIBLE',
    },
    {
      numero_lote: 'L-2023-112',
      fecha_caducidad: new Date(Date.now() - 15 * 86400000).toISOString(),
      cantidad_actual: 0,
      cantidad_inicial: 80,
      estado: 'VENCIDO',
    },
  ],
  movimientos: Array.from({ length: 8 }).map((_, index) => ({
    id: index + 1,
    fecha: new Date(Date.now() - index * 86400000).toISOString(),
    tipo: index % 2 === 0 ? 'ENTRADA' : 'SALIDA',
    cantidad: 20 + index * 5,
    centro: 'Centro Penitenciario Simulado',
    usuario: index % 2 === 0 ? 'Farmacia Central' : 'CP Norte',
    lote: index % 2 === 0 ? 'L-2024-001' : 'L-2023-112',
  })),
};

const MOCK_LOTE = {
  numero_lote: 'L-2024-001',
  producto: {
    codigo: 'MED-001',
    descripcion: 'Paracetamol 500mg tabletas',
  },
  fecha_caducidad: new Date(Date.now() + 45 * 86400000).toISOString(),
  cantidad_actual: 150,
  cantidad_inicial: 220,
  proveedor: 'Laboratorio Simulado',
  estado: 'DISPONIBLE',
  movimientos: Array.from({ length: 5 }).map((_, index) => ({
    id: index + 1,
    fecha: new Date(Date.now() - index * 43200000).toISOString(),
    tipo: index % 2 === 0 ? 'ENTRADA' : 'SALIDA',
    cantidad: 12 + index * 3,
    centro: 'Centro Penitenciario Simulado',
    usuario: 'Operador',
    saldo: 200 - index * 20,
  })),
};

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
  proveedor: lote.proveedor,
  // Campos de trazabilidad de contratos
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
      descripcion: data.descripcion,
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
      descripcion: producto.descripcion,
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

  if (data.numero_lote) {
    return {
      numero_lote: data.numero_lote,
      producto: data.producto || {},
      fecha_caducidad: data.fecha_caducidad,
      cantidad_actual: data.cantidad_actual,
      cantidad_inicial: data.cantidad_inicial,
      proveedor: data.proveedor,
      estado: (data.estado || data.estado_caducidad || '').toString().toUpperCase(),
      centro: data.centro,
      movimientos: (data.movimientos || []).map(mapMovimiento),
      alertas: data.alertas || [],
      estadisticas: data.estadisticas || {},
    };
  }

  if (data.lote) {
    return {
      numero_lote: data.lote.numero_lote,
      producto: {
        codigo: data.lote.producto,
        descripcion: data.lote.producto_descripcion,
      },
      fecha_caducidad: data.lote.fecha_caducidad,
      cantidad_actual: data.lote.cantidad_actual,
      cantidad_inicial: data.lote.cantidad_inicial,
      proveedor: data.lote.proveedor,
      estado: (data.lote.estado || data.lote.estado_caducidad || '').toString().toUpperCase(),
      centro: data.lote.centro,
      movimientos: (data.historial || []).map(mapMovimiento),
      alertas: data.alertas || [],
      estadisticas: data.estadisticas || {},
    };
  }

  return data;
};

const isDevSession = () => false;

const Trazabilidad = () => {
  const { getRolPrincipal, permisos } = usePermissions();
  const rolPrincipal = getRolPrincipal();
  // Solo ADMIN y FARMACIA pueden ver campos de contrato (para auditoría)
  const puedeVerContrato = ['ADMIN', 'FARMACIA'].includes(rolPrincipal) || permisos?.isSuperuser;

  const [tipoBusqueda, setTipoBusqueda] = useState('producto');
  const [codigoBusqueda, setCodigoBusqueda] = useState('');
  const [loading, setLoading] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [resultados, setResultados] = useState(null);

  const handleExportarPdf = async () => {
    if (!resultados || tipoBusqueda !== 'producto') {
      toast.error('Primero busque un producto para exportar su trazabilidad');
      return;
    }

    setExportingPdf(true);
    try {
      const response = await trazabilidadAPI.exportarPdf(codigoBusqueda);
      descargarArchivo(response, `trazabilidad_${codigoBusqueda}_${new Date().toISOString().split('T')[0]}.pdf`);
      toast.success('PDF de trazabilidad generado exitosamente');
    } catch (error) {
      console.error('Error al exportar PDF:', error);
      toast.error('Error al generar el PDF de trazabilidad');
    } finally {
      setExportingPdf(false);
    }
  };

  const handleBuscar = async (e) => {
    e.preventDefault();

    if (!codigoBusqueda.trim()) {
      toast.error('Ingrese un codigo para buscar');
      return;
    }

    setLoading(true);
    try {
      const normalizer = tipoBusqueda === 'producto' ? normalizeProductoResponse : normalizeLoteResponse;

      if (isDevSession()) {
        const mock = tipoBusqueda === 'producto' ? normalizeProductoResponse(MOCK_PRODUCTO) : normalizeLoteResponse(MOCK_LOTE);
        setResultados(mock);
        toast.success('Trazabilidad cargada correctamente');
        return;
      }

      const response = tipoBusqueda === 'producto'
        ? await trazabilidadAPI.producto(codigoBusqueda)
        : await trazabilidadAPI.lote(codigoBusqueda);

      setResultados(normalizer(response.data));
      toast.success('Trazabilidad cargada correctamente');
    } catch (error) {
      if (error.response?.status === 404) {
        toast.error(`${tipoBusqueda === 'producto' ? 'Producto' : 'Lote'} no encontrado`);
      } else {
        toast.error(error.response?.data?.error || 'Error al cargar trazabilidad');
      }
      console.error(error);
      setResultados(null);
    } finally {
      setLoading(false);
    }
  };

  const limpiarBusqueda = () => {
    setCodigoBusqueda('');
    setResultados(null);
  };

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
        <p className="text-xs text-gray-500">Descripcion</p>
        <p className="font-semibold">{resultados.descripcion}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Unidad</p>
        <p className="font-semibold">{resultados.unidad_medida}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Inventario actual</p>
        <p className="text-2xl font-bold text-violet-600">{resultados.stock_actual ?? 0}</p>
        {resultados.stock_minimo != null && (
          <p className="text-xs text-gray-500 mt-1">Inv. Mínimo: {resultados.stock_minimo}</p>
        )}
      </div>
    </div>
  );

  const renderInfoLote = () => (
    <div className="grid gap-4 md:grid-cols-4">
      <div>
        <p className="text-xs text-gray-500">Numero de Lote</p>
        <p className="font-semibold">{resultados.numero_lote}</p>
      </div>
      <div className="md:col-span-2">
        <p className="text-xs text-gray-500">Producto</p>
        <p className="font-semibold">
          {resultados.producto?.codigo} - {resultados.producto?.descripcion}
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
        <p className="text-xs text-gray-500">Proveedor</p>
        <p className="font-semibold">{resultados.proveedor || '-'}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Estado</p>
        <p className="font-semibold">{resultados.estado || '-'}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Centro</p>
        <p className="font-semibold">{resultados.centro || '-'}</p>
      </div>
      {/* Campos de trazabilidad de contratos - Solo visible para ADMIN y FARMACIA */}
      {puedeVerContrato && (
        <>
          <div>
            <p className="text-xs text-gray-500">Número de Contrato</p>
            <p className="font-semibold text-blue-600">{resultados.numero_contrato || '-'}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Marca</p>
            <p className="font-semibold">{resultados.marca || '-'}</p>
          </div>
        </>
      )}
    </div>
  );

  const mostrarSaldo = tipoBusqueda === 'lote' && Array.isArray(resultados?.movimientos)
    && resultados.movimientos.some((mov) => mov.saldo !== undefined && mov.saldo !== null);

  const lotesParaMostrar = Array.isArray(resultados?.lotes) ? resultados.lotes : [];
  const movimientosParaMostrar = Array.isArray(resultados?.movimientos) ? resultados.movimientos : [];

  const estadoClass = (estado = '') => {
    const upper = estado.toUpperCase();
    if (upper.includes('VENCIDO') || upper.includes('AGOTADO')) return 'bg-red-100 text-red-700';
    if (upper.includes('CRITICO') || upper.includes('PROXIMO')) return 'bg-amber-100 text-amber-800';
    return 'bg-emerald-100 text-emerald-700';
  };

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        icon={FaHistory}
        title="Trazabilidad"
        subtitle="Consulta el historial completo de productos y lotes"
      />

      <div className="bg-white p-6 rounded-lg shadow">
        <form onSubmit={handleBuscar} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div>
              <label className="block text-sm font-medium mb-2">Buscar por</label>
              <select
                value={tipoBusqueda}
                onChange={(e) => {
                  setTipoBusqueda(e.target.value);
                  setCodigoBusqueda('');
                  setResultados(null);
                }}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="producto">Producto</option>
                <option value="lote">Lote</option>
              </select>
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-2">
                {tipoBusqueda === 'producto' ? 'Clave del producto' : 'Numero de lote'}
              </label>
              {tipoBusqueda === 'producto' ? (
                <AutocompleteInput
                  apiCall={productosAPI.getAll}
                  value={codigoBusqueda}
                  onChange={setCodigoBusqueda}
                  placeholder="MED-001"
                  displayField="clave"
                  searchField="search"
                />
              ) : (
                <AutocompleteInput
                  apiCall={lotesAPI.getAll}
                  value={codigoBusqueda}
                  onChange={setCodigoBusqueda}
                  placeholder="L-2024-001"
                  displayField="numero_lote"
                  searchField="search"
                />
              )}
            </div>

            <div className="flex items-end gap-2">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
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
                className="px-4 py-2 border rounded-lg hover:bg-gray-100"
              >
                Limpiar
              </button>
            </div>
          </div>
        </form>
      </div>

      {loading && (
        <div className="text-center py-8 bg-white rounded-lg shadow">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto" />
          <p className="mt-3 text-gray-600">Buscando informacion...</p>
        </div>
      )}

      {!loading && !resultados && (
        <div className="text-center py-8 bg-white rounded-lg shadow">
          <p className="text-gray-500">
            Ingresa la clave de un producto o numero de lote y presiona "Buscar"
          </p>
        </div>
      )}

      {!loading && resultados && (
        <div className="space-y-6">
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
                    Informacion del {tipoBusqueda === 'producto' ? 'producto' : 'lote'}
                  </h2>
                  <p className="text-sm text-gray-600">
                    Datos generales y estado actual
                  </p>
                </div>
              </div>
              {tipoBusqueda === 'producto' && (
                <button
                  onClick={handleExportarPdf}
                  disabled={exportingPdf}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-white transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ background: 'linear-gradient(135deg, #DC2626 0%, #991B1B 100%)' }}
                >
                  {exportingPdf ? (
                    <>
                      <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                      Generando...
                    </>
                  ) : (
                    <>
                      <FaFilePdf />
                      Exportar PDF
                    </>
                  )}
                </button>
              )}
            </div>
            {tipoBusqueda === 'producto' ? renderInfoProducto() : renderInfoLote()}
          </div>

          {renderAlertas()}

          {tipoBusqueda === 'producto' && lotesParaMostrar.length > 0 && (
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <FaWarehouse /> Lotes asociados
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left">Lote</th>
                      <th className="px-4 py-2 text-left">Caducidad</th>
                      <th className="px-4 py-2 text-left">Inventario</th>
                      {puedeVerContrato && <th className="px-4 py-2 text-left">Contrato</th>}
                      {puedeVerContrato && <th className="px-4 py-2 text-left">Marca</th>}
                      <th className="px-4 py-2 text-left">Estado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {lotesParaMostrar.map((lote) => (
                      <tr key={lote.numero_lote}>
                        <td className="px-4 py-2 font-semibold">{lote.numero_lote}</td>
                        <td className="px-4 py-2">
                          {lote.fecha_caducidad ? new Date(lote.fecha_caducidad).toLocaleDateString() : '-'}
                        </td>
                        <td className="px-4 py-2">{lote.cantidad_actual}</td>
                        {puedeVerContrato && <td className="px-4 py-2 text-gray-600">{lote.numero_contrato || '-'}</td>}
                        {puedeVerContrato && <td className="px-4 py-2 text-gray-600">{lote.marca || '-'}</td>}
                        <td className="px-4 py-2">
                          <span
                            className={`px-2 py-1 text-xs rounded-full ${estadoClass(lote.estado)}`}
                          >
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

          {movimientosParaMostrar.length > 0 && (
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <FaHistory /> Historial de movimientos
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left">Fecha</th>
                      <th className="px-4 py-2 text-left">Tipo</th>
                      <th className="px-4 py-2 text-left">Cantidad</th>
                      {mostrarSaldo && <th className="px-4 py-2 text-left">Saldo</th>}
                      <th className="px-4 py-2 text-left">Centro</th>
                      <th className="px-4 py-2 text-left">Usuario</th>
                      <th className="px-4 py-2 text-left">Lote</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {movimientosParaMostrar.map((mov) => (
                      <tr key={mov.id}>
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
                        {mostrarSaldo && <td className="px-4 py-2">{mov.saldo ?? '-'}</td>}
                        <td className="px-4 py-2">{mov.centro || '-'}</td>
                        <td className="px-4 py-2">{mov.usuario || '-'}</td>
                        <td className="px-4 py-2">{mov.lote || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Trazabilidad;
