import { useEffect, useState } from "react";
import { toast } from "react-hot-toast";
import BarcodeScannerInput from "../components/BarcodeScannerInput";
import { movimientosAPI } from "../services/api";

const Movimientos = () => {
  const [movimientos, setMovimientos] = useState([]);
  const [codigoBarras, setCodigoBarras] = useState("");
  const [tipo, setTipo] = useState("entrada");
  const [cantidad, setCantidad] = useState("");
  const [documento, setDocumento] = useState("");
  const [loading, setLoading] = useState(true);

  const cargarMovimientos = async () => {
    setLoading(true);
    try {
      const response = await movimientosAPI.getAll({ limit: 50, ordering: "-fecha_movimiento" });
      const data = response.data?.results || response.data || [];
      setMovimientos(Array.isArray(data) ? data : []);
    } catch (err) {
      toast.error(err.response?.data?.detail || "No se pudieron cargar los movimientos");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarMovimientos();
  }, []);

  const registrar = async () => {
    if (!codigoBarras) {
      toast.error("Escanea o escribe un codigo de barras");
      return;
    }
    if (!cantidad || Number(cantidad) <= 0) {
      toast.error("Ingresa una cantidad valida");
      return;
    }

    try {
      await movimientosAPI.registrarPorCodigo({
        codigo_barras: codigoBarras,
        cantidad: Number(cantidad),
        tipo,
        documento_referencia: documento,
      });
      toast.success("Movimiento registrado");
      setCantidad("");
      setDocumento("");
      setCodigoBarras("");
      cargarMovimientos();
    } catch (err) {
      toast.error(err.response?.data?.error || err.response?.data?.detail || "No se pudo registrar");
    }
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-bold text-gray-900">Movimientos</h1>
          <p className="text-gray-600">Registro rapido de movimientos usando codigo de barras</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
            <h2 className="text-xl font-semibold text-gray-800">Nuevo movimiento</h2>

            <div className="space-y-2">
              <label className="text-sm font-semibold text-gray-700">Codigo de barras</label>
              <BarcodeScannerInput onCodigoDetectado={setCodigoBarras} />
              {codigoBarras && (
                <p className="text-xs text-green-700">Codigo listo: {codigoBarras}</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-semibold text-gray-700">Tipo</label>
              <select
                value={tipo}
                onChange={(e) => setTipo(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="entrada">Entrada</option>
                <option value="salida">Salida</option>
                <option value="ajuste">Ajuste</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-semibold text-gray-700">Cantidad</label>
              <input
                type="number"
                min="1"
                value={cantidad}
                onChange={(e) => setCantidad(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Cantidad"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-semibold text-gray-700">Documento / razon</label>
              <input
                type="text"
                value={documento}
                onChange={(e) => setDocumento(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Ej: FAC-001"
              />
            </div>

            <button
              onClick={registrar}
              className="w-full px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 transition"
            >
              Registrar movimiento
            </button>
          </div>

          <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-800">Ultimos movimientos</h3>
              <button
                onClick={cargarMovimientos}
                className="text-sm text-blue-600 hover:text-blue-800"
                disabled={loading}
              >
                Recargar
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-100 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold">Producto</th>
                    <th className="px-4 py-3 text-left font-semibold">Tipo</th>
                    <th className="px-4 py-3 text-right font-semibold">Cantidad</th>
                    <th className="px-4 py-3 text-left font-semibold">Documento</th>
                    <th className="px-4 py-3 text-left font-semibold">Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {!movimientos.length ? (
                    <tr>
                      <td colSpan="5" className="px-4 py-6 text-center text-gray-500">
                        {loading ? "Cargando..." : "Sin movimientos"}
                      </td>
                    </tr>
                  ) : (
                    movimientos.map((mov) => (
                      <tr key={mov.id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="px-4 py-3 text-gray-800">{mov.producto_nombre || mov.producto || ""}</td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-1 rounded text-xs font-semibold ${
                              mov.tipo === "entrada"
                                ? "bg-green-100 text-green-800"
                                : mov.tipo === "salida"
                                ? "bg-red-100 text-red-800"
                                : "bg-yellow-100 text-yellow-800"
                            }`}
                          >
                            {mov.tipo}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right font-semibold text-gray-900">{mov.cantidad}</td>
                        <td className="px-4 py-3 text-gray-700">{mov.documento_referencia || mov.razon || ""}</td>
                        <td className="px-4 py-3 text-gray-600">
                          {mov.fecha_movimiento
                            ? new Date(mov.fecha_movimiento).toLocaleString()
                            : ""}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Movimientos;
