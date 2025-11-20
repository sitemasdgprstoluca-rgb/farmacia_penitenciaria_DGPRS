import { useState } from 'react';
import { trazabilidadAPI } from '../services/api';
import { toast } from 'react-hot-toast';
import { FaSearch, FaBox, FaWarehouse, FaHistory } from 'react-icons/fa';
import PageHeader from '../components/PageHeader';

const MOCK_PRODUCTO = {
  codigo: 'MED-001',
  descripcion: 'Paracetamol 500mg tabletas',
  unidad_medida: 'TABLETA',
  stock_actual: 320,
  lotes: [
    {
      numero_lote: 'L-2024-001',
      fecha_caducidad: new Date(Date.now() + 60 * 86400000).toISOString(),
      cantidad_actual: 150,
      estado: 'ACTIVO',
    },
    {
      numero_lote: 'L-2023-112',
      fecha_caducidad: new Date(Date.now() - 15 * 86400000).toISOString(),
      cantidad_actual: 0,
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
  movimientos: Array.from({ length: 5 }).map((_, index) => ({
    id: index + 1,
    fecha: new Date(Date.now() - index * 43200000).toISOString(),
    tipo: index % 2 === 0 ? 'ENTRADA' : 'SALIDA',
    cantidad: 12 + index * 3,
    centro: 'Centro Penitenciario Simulado',
    usuario: 'Operador',
  })),
};

const isDevSession = () => false;

const Trazabilidad = () => {
  const [tipoBusqueda, setTipoBusqueda] = useState('producto');
  const [codigoBusqueda, setCodigoBusqueda] = useState('');
  const [loading, setLoading] = useState(false);
  const [resultados, setResultados] = useState(null);

  const handleBuscar = async (e) => {
    e.preventDefault();

    if (!codigoBusqueda.trim()) {
      toast.error('Ingrese un cídigo para buscar');
      return;
    }

    setLoading(true);
    try {
      if (isDevSession()) {
        setResultados(tipoBusqueda === 'producto' ? MOCK_PRODUCTO : MOCK_LOTE);
        toast.success('Trazabilidad cargada correctamente');
        return;
      }

      let response;
      if (tipoBusqueda === 'producto') {
        response = await trazabilidadAPI.producto(codigoBusqueda);
      } else {
        response = await trazabilidadAPI.lote(codigoBusqueda);
      }

      setResultados(response.data);
      toast.success('Trazabilidad cargada correctamente');
    } catch (error) {
      if (error.response?.status === 404) {
        toast.error(`${tipoBusqueda === 'producto' ? 'Producto' : 'Lote'} no encontrado`);
      } else {
        toast.error('Error al cargar trazabilidad');
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

  const renderInfoGeneral = () => {
    if (!resultados) return null;

    if (tipoBusqueda === 'producto') {
      return (
        <div className="grid gap-4 md:grid-cols-4">
          <div>
            <p className="text-xs text-gray-500">Clave</p>
            <p className="font-semibold">{resultados.codigo}</p>
          </div>
          <div className="md:col-span-2">
            <p className="text-xs text-gray-500">Descripción</p>
            <p className="font-semibold">{resultados.descripcion}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Stock Actual</p>
            <p className="font-semibold">{resultados.stock_actual}</p>
          </div>
        </div>
      );
    }

    return (
      <div className="grid gap-4 md:grid-cols-4">
        <div>
          <p className="text-xs text-gray-500">Nímero de Lote</p>
          <p className="font-semibold">{resultados.numero_lote}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Producto</p>
          <p className="font-semibold">
            {resultados.producto.codigo} - {resultados.producto.descripcion}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Caducidad</p>
          <p className="font-semibold">
            {new Date(resultados.fecha_caducidad).toLocaleDateString()}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Stock actual</p>
          <p className="font-semibold">
            {resultados.cantidad_actual} / {resultados.cantidad_inicial}
          </p>
        </div>
      </div>
    );
  };

  const modoBusquedaLabel = tipoBusqueda === 'producto' ? 'Modo: Producto' : 'Modo: Lote';

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        icon={FaHistory}
        title="Trazabilidad de Inventario"
        subtitle="Consulta el historial completo de movimientos de productos y lotes"
        badge={modoBusquedaLabel}
      />

      <div className="bg-white p-6 rounded-lg shadow mb-6">
        <form onSubmit={handleBuscar}>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-2">Tipo de bísqueda</label>
              <select
                value={tipoBusqueda}
                onChange={(e) => setTipoBusqueda(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="producto">Por Producto (Clave)</option>
                <option value="lote">Por Lote (Nímero)</option>
              </select>
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-2">
                {tipoBusqueda === 'producto' ? 'Clave del Producto' : 'Nímero de Lote'}
              </label>
              <div className="relative">
                <FaSearch className="absolute left-3 top-3 text-gray-400" />
                <input
                  type="text"
                  value={codigoBusqueda}
                  onChange={(e) => setCodigoBusqueda(e.target.value.toUpperCase())}
                  placeholder={tipoBusqueda === 'producto' ? 'MED-001' : 'L-2024-001'}
                  className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
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
          <p className="mt-3 text-gray-600">Buscando información...</p>
        </div>
      )}

      {!loading && !resultados && (
        <div className="text-center py-8 bg-white rounded-lg shadow">
          <p className="text-gray-500">
            Ingresa la clave de un producto o nímero de lote y presiona &quot;Buscar&quot;
          </p>
        </div>
      )}

      {!loading && resultados && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-violet-100 p-3 rounded-lg">
                {tipoBusqueda === 'producto' ? (
                  <FaBox className="text-violet-600 text-2xl" />
                ) : (
                  <FaWarehouse className="text-violet-600 text-2xl" />
                )}
              </div>
              <div>
                <h2 className="text-lg font-bold">
                  Información del {tipoBusqueda === 'producto' ? 'Producto' : 'Lote'}
                </h2>
                <p className="text-sm text-gray-600">
                  Datos generales y estado actual del{' '}
                  {tipoBusqueda === 'producto' ? 'producto' : 'lote'}
                </p>
              </div>
            </div>
            {renderInfoGeneral()}
          </div>

          {tipoBusqueda === 'producto' && resultados.lotes?.length > 0 && (
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
                      <th className="px-4 py-2 text-left">Stock</th>
                      <th className="px-4 py-2 text-left">Estado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {resultados.lotes.map((lote) => (
                      <tr key={lote.numero_lote}>
                        <td className="px-4 py-2 font-semibold">{lote.numero_lote}</td>
                        <td className="px-4 py-2">
                          {new Date(lote.fecha_caducidad).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-2">{lote.cantidad_actual}</td>
                        <td className="px-4 py-2">
                          <span
                            className={`px-2 py-1 text-xs rounded-full ${
                              lote.estado === 'ACTIVO'
                                ? 'bg-emerald-100 text-emerald-700'
                                : 'bg-red-100 text-red-700'
                            }`}
                          >
                            {lote.estado}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {resultados.movimientos?.length > 0 && (
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <FaHistory /> Historial de Movimientos
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left">Fecha</th>
                      <th className="px-4 py-2 text-left">Tipo</th>
                      <th className="px-4 py-2 text-left">Cantidad</th>
                      <th className="px-4 py-2 text-left">Centro</th>
                      <th className="px-4 py-2 text-left">Usuario</th>
                      <th className="px-4 py-2 text-left">Lote</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {resultados.movimientos.map((mov) => (
                      <tr key={mov.id}>
                        <td className="px-4 py-2">
                          {new Date(mov.fecha).toLocaleString()}
                        </td>
                        <td className="px-4 py-2">
                          <span
                            className={`px-2 py-1 text-xs rounded-full ${
                              mov.tipo === 'ENTRADA'
                                ? 'bg-blue-100 text-blue-700'
                                : 'bg-orange-100 text-orange-700'
                            }`}
                          >
                            {mov.tipo}
                          </span>
                        </td>
                        <td className="px-4 py-2 font-semibold">{mov.cantidad}</td>
                        <td className="px-4 py-2">{mov.centro}</td>
                        <td className="px-4 py-2">{mov.usuario}</td>
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






