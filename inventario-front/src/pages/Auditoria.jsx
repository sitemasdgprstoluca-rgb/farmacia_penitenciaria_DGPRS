/**
 * Página de Auditoría - ISS-002
 * Muestra el log de acciones del sistema con filtros y exportación
 */
import React, { useEffect, useState, useCallback } from "react";
import { toast } from "react-hot-toast";
import Pagination from "../components/Pagination";
import PageHeader from "../components/PageHeader";
import { auditoriaAPI, usuariosAPI, descargarArchivo } from "../services/api";
import { usePermissions } from "../hooks/usePermissions";
import { FaFilter, FaFileExcel, FaFilePdf, FaSearch, FaHistory, FaUser, FaDatabase, FaCalendarAlt, FaEye } from "react-icons/fa";

const PAGE_SIZE = 25;

// Mapeo de acciones a colores y etiquetas
const ACCIONES_MAP = {
  'CREATE': { label: 'Creación', color: 'bg-green-100 text-green-800' },
  'UPDATE': { label: 'Actualización', color: 'bg-blue-100 text-blue-800' },
  'DELETE': { label: 'Eliminación', color: 'bg-red-100 text-red-800' },
  'LOGIN': { label: 'Inicio de Sesión', color: 'bg-purple-100 text-purple-800' },
  'LOGOUT': { label: 'Cierre de Sesión', color: 'bg-gray-100 text-gray-800' },
  'VIEW': { label: 'Visualización', color: 'bg-yellow-100 text-yellow-800' },
  'EXPORT': { label: 'Exportación', color: 'bg-indigo-100 text-indigo-800' },
  'IMPORT': { label: 'Importación', color: 'bg-pink-100 text-pink-800' },
  'AUTORIZAR': { label: 'Autorización', color: 'bg-emerald-100 text-emerald-800' },
  'RECHAZAR': { label: 'Rechazo', color: 'bg-orange-100 text-orange-800' },
  'SURTIR': { label: 'Surtido', color: 'bg-cyan-100 text-cyan-800' },
};

const getAccionBadge = (accion) => {
  const config = ACCIONES_MAP[accion?.toUpperCase()] || { label: accion, color: 'bg-gray-100 text-gray-800' };
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.color}`}>
      {config.label}
    </span>
  );
};

const Auditoria = () => {
  const { permisos } = usePermissions();
  
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [expandedId, setExpandedId] = useState(null);
  const [exporting, setExporting] = useState(null);
  
  // Filtros
  const [filtros, setFiltros] = useState({
    fecha_inicio: "",
    fecha_fin: "",
    usuario: "",
    accion: "",
    modelo: "",
    search: "",
  });
  
  const [filtrosAplicados, setFiltrosAplicados] = useState({...filtros});
  const [usuarios, setUsuarios] = useState([]);
  const [modelos, setModelos] = useState([]);
  const [showFiltersMenu, setShowFiltersMenu] = useState(false);

  // Cargar catálogos para filtros
  const cargarCatalogos = useCallback(async () => {
    try {
      // Cargar usuarios para filtro
      const usuariosResp = await usuariosAPI.getAll({ page_size: 500, ordering: "username" });
      setUsuarios(usuariosResp.data.results || usuariosResp.data || []);
      
      // Los modelos se podrían cargar del backend o usar lista fija
      setModelos([
        { value: 'User', label: 'Usuario' },
        { value: 'Producto', label: 'Producto' },
        { value: 'Lote', label: 'Lote' },
        { value: 'Requisicion', label: 'Requisición' },
        { value: 'Centro', label: 'Centro' },
        { value: 'Movimiento', label: 'Movimiento' },
      ]);
    } catch (error) {
      console.error("Error cargando catálogos:", error);
    }
  }, []);

  // Cargar logs de auditoría
  const cargarLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page,
        page_size: PAGE_SIZE,
        ordering: "-timestamp",
        ...Object.fromEntries(
          Object.entries(filtrosAplicados).filter(([_, v]) => v !== "")
        ),
      };
      
      const response = await auditoriaAPI.getAll(params);
      const data = response.data;
      
      setLogs(data.results || data || []);
      setTotal(data.count || (data.results ? data.results.length : data.length) || 0);
    } catch (error) {
      console.error("Error cargando logs de auditoría:", error);
      toast.error("Error al cargar logs de auditoría");
    } finally {
      setLoading(false);
    }
  }, [page, filtrosAplicados]);

  useEffect(() => {
    cargarCatalogos();
  }, [cargarCatalogos]);

  useEffect(() => {
    cargarLogs();
  }, [cargarLogs]);

  const handleFiltroChange = (campo, valor) => {
    setFiltros(prev => ({ ...prev, [campo]: valor }));
  };

  const aplicarFiltros = () => {
    setFiltrosAplicados({ ...filtros });
    setPage(1);
    setShowFiltersMenu(false);
  };

  const limpiarFiltros = () => {
    const limpios = {
      fecha_inicio: "",
      fecha_fin: "",
      usuario: "",
      accion: "",
      modelo: "",
      search: "",
    };
    setFiltros(limpios);
    setFiltrosAplicados(limpios);
    setPage(1);
  };

  const handleExportar = async (formato) => {
    if (exporting) return;
    
    setExporting(formato);
    try {
      const params = {
        ...Object.fromEntries(
          Object.entries(filtrosAplicados).filter(([_, v]) => v !== "")
        ),
      };
      
      const response = formato === 'excel' 
        ? await auditoriaAPI.exportar(params)
        : await auditoriaAPI.exportarPdf(params);
      
      const ext = formato === 'excel' ? 'xlsx' : 'pdf';
      const contentType = formato === 'excel' 
        ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        : 'application/pdf';
      
      descargarArchivo(
        response.data,
        `auditoria_${new Date().toISOString().split('T')[0]}.${ext}`,
        contentType
      );
      
      toast.success(`Exportación a ${formato.toUpperCase()} completada`);
    } catch (error) {
      console.error(`Error exportando a ${formato}:`, error);
      toast.error(`Error al exportar a ${formato.toUpperCase()}`);
    } finally {
      setExporting(null);
    }
  };

  const formatFecha = (fecha) => {
    if (!fecha) return "-";
    try {
      return new Date(fecha).toLocaleString("es-MX", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return fecha;
    }
  };

  const toggleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const renderDetalles = (log) => {
    const detalles = log.detalles || {};
    const datosAnteriores = log.datos_anteriores;
    const datosNuevos = log.datos_nuevos;
    
    return (
      <div className="bg-gray-50 p-4 rounded-lg mt-2 text-sm">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Información general */}
          <div>
            <h4 className="font-semibold text-gray-700 mb-2">Información</h4>
            <dl className="space-y-1">
              {log.ip_address && (
                <div className="flex">
                  <dt className="text-gray-500 w-24">IP:</dt>
                  <dd className="text-gray-800">{log.ip_address}</dd>
                </div>
              )}
              {log.objeto_id && (
                <div className="flex">
                  <dt className="text-gray-500 w-24">ID Objeto:</dt>
                  <dd className="text-gray-800">{log.objeto_id}</dd>
                </div>
              )}
              {detalles.objeto_repr && (
                <div className="flex">
                  <dt className="text-gray-500 w-24">Objeto:</dt>
                  <dd className="text-gray-800">{detalles.objeto_repr}</dd>
                </div>
              )}
            </dl>
          </div>
          
          {/* Datos anteriores */}
          {datosAnteriores && Object.keys(datosAnteriores).length > 0 && (
            <div>
              <h4 className="font-semibold text-gray-700 mb-2">Datos Anteriores</h4>
              <pre className="bg-red-50 p-2 rounded text-xs overflow-auto max-h-32">
                {JSON.stringify(datosAnteriores, null, 2)}
              </pre>
            </div>
          )}
          
          {/* Datos nuevos */}
          {datosNuevos && Object.keys(datosNuevos).length > 0 && (
            <div>
              <h4 className="font-semibold text-gray-700 mb-2">Datos Nuevos</h4>
              <pre className="bg-green-50 p-2 rounded text-xs overflow-auto max-h-32">
                {JSON.stringify(datosNuevos, null, 2)}
              </pre>
            </div>
          )}
          
          {/* Detalles adicionales */}
          {Object.keys(detalles).length > 0 && (
            <div className="md:col-span-2">
              <h4 className="font-semibold text-gray-700 mb-2">Detalles Adicionales</h4>
              <pre className="bg-blue-50 p-2 rounded text-xs overflow-auto max-h-32">
                {JSON.stringify(detalles, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    );
  };

  const filtrosActivos = Object.values(filtrosAplicados).filter(v => v !== "").length;

  return (
    <div className="p-4 md:p-6">
      <PageHeader
        title="Auditoría del Sistema"
        icon={<FaHistory className="text-2xl" />}
        subtitle="Registro de acciones y cambios en el sistema"
      />

      {/* Barra de acciones */}
      <div className="bg-white rounded-lg shadow p-4 mb-4">
        <div className="flex flex-wrap gap-3 items-center justify-between">
          {/* Búsqueda rápida */}
          <div className="flex-1 min-w-[200px] max-w-md">
            <div className="relative">
              <FaSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar en logs..."
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-guinda-500 focus:border-guinda-500"
                value={filtros.search}
                onChange={(e) => handleFiltroChange("search", e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && aplicarFiltros()}
              />
            </div>
          </div>
          
          {/* Botones de acción */}
          <div className="flex gap-2">
            {/* Filtros */}
            <div className="relative">
              <button
                onClick={() => setShowFiltersMenu(!showFiltersMenu)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
                  filtrosActivos > 0 
                    ? "bg-guinda-50 border-guinda-300 text-guinda-700" 
                    : "bg-white border-gray-300 text-gray-700 hover:bg-gray-50"
                }`}
              >
                <FaFilter />
                Filtros
                {filtrosActivos > 0 && (
                  <span className="bg-guinda-600 text-white text-xs px-2 py-0.5 rounded-full">
                    {filtrosActivos}
                  </span>
                )}
              </button>
              
              {/* Menú de filtros */}
              {showFiltersMenu && (
                <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border z-50 p-4">
                  <div className="space-y-4">
                    {/* Fecha inicio */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        <FaCalendarAlt className="inline mr-1" /> Desde
                      </label>
                      <input
                        type="date"
                        className="w-full border rounded-lg px-3 py-2"
                        value={filtros.fecha_inicio}
                        onChange={(e) => handleFiltroChange("fecha_inicio", e.target.value)}
                      />
                    </div>
                    
                    {/* Fecha fin */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        <FaCalendarAlt className="inline mr-1" /> Hasta
                      </label>
                      <input
                        type="date"
                        className="w-full border rounded-lg px-3 py-2"
                        value={filtros.fecha_fin}
                        onChange={(e) => handleFiltroChange("fecha_fin", e.target.value)}
                      />
                    </div>
                    
                    {/* Usuario */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        <FaUser className="inline mr-1" /> Usuario
                      </label>
                      <select
                        className="w-full border rounded-lg px-3 py-2"
                        value={filtros.usuario}
                        onChange={(e) => handleFiltroChange("usuario", e.target.value)}
                      >
                        <option value="">Todos</option>
                        {usuarios.map((u) => (
                          <option key={u.id} value={u.id}>
                            {u.username} - {u.first_name} {u.last_name}
                          </option>
                        ))}
                      </select>
                    </div>
                    
                    {/* Acción */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Acción
                      </label>
                      <select
                        className="w-full border rounded-lg px-3 py-2"
                        value={filtros.accion}
                        onChange={(e) => handleFiltroChange("accion", e.target.value)}
                      >
                        <option value="">Todas</option>
                        {Object.entries(ACCIONES_MAP).map(([key, { label }]) => (
                          <option key={key} value={key}>{label}</option>
                        ))}
                      </select>
                    </div>
                    
                    {/* Modelo */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        <FaDatabase className="inline mr-1" /> Modelo
                      </label>
                      <select
                        className="w-full border rounded-lg px-3 py-2"
                        value={filtros.modelo}
                        onChange={(e) => handleFiltroChange("modelo", e.target.value)}
                      >
                        <option value="">Todos</option>
                        {modelos.map((m) => (
                          <option key={m.value} value={m.value}>{m.label}</option>
                        ))}
                      </select>
                    </div>
                    
                    {/* Botones */}
                    <div className="flex gap-2 pt-2 border-t">
                      <button
                        onClick={limpiarFiltros}
                        className="flex-1 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                      >
                        Limpiar
                      </button>
                      <button
                        onClick={aplicarFiltros}
                        className="flex-1 px-4 py-2 bg-guinda-600 text-white rounded-lg hover:bg-guinda-700"
                      >
                        Aplicar
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
            
            {/* Exportar Excel */}
            {permisos?.exportarAuditoria !== false && (
              <button
                onClick={() => handleExportar('excel')}
                disabled={exporting === 'excel'}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                <FaFileExcel />
                {exporting === 'excel' ? 'Exportando...' : 'Excel'}
              </button>
            )}
            
            {/* Exportar PDF */}
            {permisos?.exportarAuditoria !== false && (
              <button
                onClick={() => handleExportar('pdf')}
                disabled={exporting === 'pdf'}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                <FaFilePdf />
                {exporting === 'pdf' ? 'Exportando...' : 'PDF'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Tabla de logs */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-guinda-600 border-t-transparent"></div>
          </div>
        ) : logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500">
            <FaHistory className="text-4xl mb-4 text-gray-300" />
            <p>No se encontraron registros de auditoría</p>
            {filtrosActivos > 0 && (
              <button
                onClick={limpiarFiltros}
                className="mt-2 text-guinda-600 hover:underline"
              >
                Limpiar filtros
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Fecha/Hora
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Usuario
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Acción
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Modelo
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Descripción
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Detalles
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {logs.map((log) => (
                    <React.Fragment key={log.id}>
                      <tr className="hover:bg-gray-50">
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                          {formatFecha(log.timestamp)}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex items-center">
                            <FaUser className="text-gray-400 mr-2" />
                            <span className="text-sm font-medium text-gray-900">
                              {log.usuario_username || log.usuario?.username || 'Sistema'}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          {getAccionBadge(log.accion)}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                          {log.modelo}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">
                          {log.detalles?.objeto_repr || log.objeto_id || '-'}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-center">
                          <button
                            onClick={() => toggleExpand(log.id)}
                            className={`p-2 rounded-full hover:bg-gray-100 ${
                              expandedId === log.id ? 'text-guinda-600 bg-guinda-50' : 'text-gray-400'
                            }`}
                            title="Ver detalles"
                          >
                            <FaEye />
                          </button>
                        </td>
                      </tr>
                      {expandedId === log.id && (
                        <tr>
                          <td colSpan={6} className="px-4 py-2">
                            {renderDetalles(log)}
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
            
            {/* Paginación */}
            <div className="px-4 py-3 border-t">
              <Pagination
                page={page}
                total={total}
                pageSize={PAGE_SIZE}
                onPageChange={setPage}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default Auditoria;
