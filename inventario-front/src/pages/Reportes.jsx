import { useEffect, useMemo, useState } from "react";
import { toast } from "react-hot-toast";
import { reportesAPI, descargarArchivo } from "../services/api";

const baseFilters = {
  tipo: "inventario",
  estado: "",
  dias: 30,
  fechaInicio: "",
  fechaFin: "",
};

const Reportes = () => {
  const [filtros, setFiltros] = useState(baseFilters);
  const [datos, setDatos] = useState([]);
  const [resumen, setResumen] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const columnas = useMemo(() => {
    if (!datos.length) return [];
    return Object.keys(datos[0]);
  }, [datos]);

  const cargarReporte = async () => {
    setLoading(true);
    setError("");

    try {
      let response;
      if (filtros.tipo === "inventario") {
        response = await reportesAPI.inventario({});
      } else if (filtros.tipo === "caducidades") {
        response = await reportesAPI.caducidades({ dias: filtros.dias });
      } else if (filtros.tipo === "requisiciones") {
        response = await reportesAPI.requisiciones({
          estado: filtros.estado || "",
          fecha_inicio: filtros.fechaInicio || undefined,
          fecha_fin: filtros.fechaFin || undefined,
        });
      } else {
        throw new Error("Tipo de reporte no soportado");
      }

      const payload = response.data || {};
      setDatos(payload.datos || payload || []);
      setResumen(payload.resumen || null);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Error al cargar reporte";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarReporte();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtros.tipo, filtros.estado, filtros.dias, filtros.fechaInicio, filtros.fechaFin]);

  const exportarExcel = async () => {
    if (filtros.tipo !== "inventario") {
      toast.error("Solo el reporte de inventario puede exportarse a Excel");
      return;
    }

    try {
      const response = await reportesAPI.exportarInventarioExcel({});
      descargarArchivo(response, `reporte_inventario_${new Date().toISOString().split("T")[0]}.xlsx`);
      toast.success("Excel generado");
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Error al exportar";
      toast.error(msg);
    }
  };

  const handleFiltro = (name, value) => {
    setFiltros((prev) => ({ ...prev, [name]: value }));
  };

  const limpiarFiltros = () => setFiltros(baseFilters);

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-bold text-gray-900">Reportes</h1>
          <p className="text-gray-600">Consulta y exporta informacion clave del inventario</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="space-y-1">
              <label className="text-sm font-semibold text-gray-700">Tipo de reporte</label>
              <select
                value={filtros.tipo}
                onChange={(e) => handleFiltro("tipo", e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="inventario">Inventario</option>
                <option value="caducidades">Caducidades</option>
                <option value="requisiciones">Requisiciones</option>
              </select>
            </div>

            {filtros.tipo === "caducidades" && (
              <div className="space-y-1">
                <label className="text-sm font-semibold text-gray-700">Dias proximos</label>
                <input
                  type="number"
                  min="1"
                  value={filtros.dias}
                  onChange={(e) => handleFiltro("dias", Number(e.target.value) || 1)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            )}

            {filtros.tipo === "requisiciones" && (
              <>
                <div className="space-y-1">
                  <label className="text-sm font-semibold text-gray-700">Estado</label>
                  <select
                    value={filtros.estado}
                    onChange={(e) => handleFiltro("estado", e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Todos</option>
                    <option value="borrador">Borrador</option>
                    <option value="enviada">Enviada</option>
                    <option value="autorizada">Autorizada</option>
                    <option value="rechazada">Rechazada</option>
                    <option value="surtida">Surtida</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-semibold text-gray-700">Desde</label>
                  <input
                    type="date"
                    value={filtros.fechaInicio}
                    onChange={(e) => handleFiltro("fechaInicio", e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-semibold text-gray-700">Hasta</label>
                  <input
                    type="date"
                    value={filtros.fechaFin}
                    onChange={(e) => handleFiltro("fechaFin", e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </>
            )}
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={cargarReporte}
              disabled={loading}
              className="px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 transition disabled:opacity-60"
            >
              {loading ? "Cargando..." : "Aplicar filtros"}
            </button>
            <button
              onClick={limpiarFiltros}
              disabled={loading}
              className="px-4 py-2 rounded-lg bg-gray-200 text-gray-800 font-semibold hover:bg-gray-300 transition disabled:opacity-60"
            >
              Limpiar
            </button>
            <button
              onClick={exportarExcel}
              disabled={loading || filtros.tipo !== "inventario"}
              className="px-4 py-2 rounded-lg bg-green-600 text-white font-semibold hover:bg-green-700 transition disabled:opacity-60"
            >
              Exportar Excel
            </button>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
              {error}
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-100 border-b border-gray-200">
                <tr>
                  {columnas.map((col) => (
                    <th key={col} className="px-4 py-3 text-left font-semibold text-gray-700">
                      {col.replace(/_/g, " ").toUpperCase()}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {!datos.length ? (
                  <tr>
                    <td colSpan={columnas.length || 1} className="px-4 py-6 text-center text-gray-500">
                      No hay datos para mostrar
                    </td>
                  </tr>
                ) : (
                  datos.map((fila, idx) => (
                    <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                      {columnas.map((col) => (
                        <td key={col} className="px-4 py-3 text-gray-800">
                          {typeof fila[col] === "object" && fila[col] !== null
                            ? JSON.stringify(fila[col])
                            : fila[col]}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {resumen && (
            <div className="bg-gray-50 border-t border-gray-200 px-4 py-3 text-sm text-gray-700">
              {Object.entries(resumen).map(([k, v]) => (
                <span key={k} className="mr-4">
                  <span className="font-semibold">{k.replace(/_/g, " ")}:</span> {v}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Reportes;
