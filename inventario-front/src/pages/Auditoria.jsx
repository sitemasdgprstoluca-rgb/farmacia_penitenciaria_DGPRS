import { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import {
  FaFileAlt,
  FaSearch,
  FaFilter,
  FaChevronLeft,
  FaChevronRight,
  FaUser,
  FaClock,
  FaDatabase,
} from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import apiClient from '../services/api';
import Pagination from '../components/Pagination';

const MOCK_LOGS = Array.from({ length: 40 }).map((_, index) => {
  const acciones = ['CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT'];
  const modelos = ['Producto', 'Lote', 'Movimiento', 'Requisicion', 'Centro', 'User'];
  return {
    id: index + 1,
    accion: acciones[index % acciones.length],
    modelo: modelos[index % modelos.length],
    usuario: `usuario${(index % 5) + 1}@edomex.gob.mx`,
    detalle: `Acción simulada ${index + 1}`,
    fecha: new Date(Date.now() - index * 3600000).toISOString(),
    ip: `10.0.0.${index + 10}`,
  };
});

const isDevSession = () => false;

const Auditoria = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalLogs, setTotalLogs] = useState(0);
  const [pageSize, setPageSize] = useState(25);

  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [filtroAccion, setFiltroAccion] = useState('');
  const [filtroModelo, setFiltroModelo] = useState('');
  const [filtroUsuario, setFiltroUsuario] = useState('');
  const [filtroFechaInicio, setFiltroFechaInicio] = useState('');
  const [filtroFechaFin, setFiltroFechaFin] = useState('');

  const accionesDisponibles = [
    { value: '', label: 'Todas las acciones' },
    { value: 'CREATE', label: 'Crear' },
    { value: 'UPDATE', label: 'Actualizar' },
    { value: 'DELETE', label: 'Eliminar' },
    { value: 'LOGIN', label: 'Inicio de sesión' },
    { value: 'LOGOUT', label: 'Cierre de sesión' }
  ];

  const modelosDisponibles = [
    { value: '', label: 'Todos los módulos' },
    { value: 'Producto', label: 'Productos' },
    { value: 'Lote', label: 'Lotes' },
    { value: 'Movimiento', label: 'Movimientos' },
    { value: 'Requisicion', label: 'Requisiciones' },
    { value: 'Centro', label: 'Centros' },
    { value: 'User', label: 'Usuarios' }
  ];

  const cargarLogs = useCallback(async () => {
    setLoading(true);
    try {
      if (isDevSession()) {
        let dataset = [...MOCK_LOGS];
        if (searchTerm) {
          const term = searchTerm.toLowerCase();
          dataset = dataset.filter(
            (log) =>
              log.detalle.toLowerCase().includes(term) ||
              log.usuario.toLowerCase().includes(term) ||
              log.modelo.toLowerCase().includes(term)
          );
        }
        if (filtroAccion) dataset = dataset.filter((log) => log.accion === filtroAccion);
        if (filtroModelo) dataset = dataset.filter((log) => log.modelo === filtroModelo);
        if (filtroUsuario) dataset = dataset.filter((log) =>
          log.usuario.toLowerCase().includes(filtroUsuario.toLowerCase())
        );
        if (filtroFechaInicio) {
          const inicio = new Date(filtroFechaInicio);
          dataset = dataset.filter((log) => new Date(log.fecha) >= inicio);
        }
        if (filtroFechaFin) {
          const fin = new Date(filtroFechaFin);
          dataset = dataset.filter((log) => new Date(log.fecha) <= fin);
        }
        const total = dataset.length;
        const inicio = (currentPage - 1) * pageSize;
        const paginados = dataset.slice(inicio, inicio + pageSize);
        setLogs(paginados);
        setTotalLogs(total);
        setTotalPages(Math.max(1, Math.ceil(total / pageSize)));
        return;
      }

      const params = {
        page: currentPage,
        page_size: pageSize
      };

      if (searchTerm) params.search = searchTerm;
      if (filtroAccion) params.accion = filtroAccion;
      if (filtroModelo) params.modelo = filtroModelo;
      if (filtroUsuario) params.usuario = filtroUsuario;
      if (filtroFechaInicio) params.fecha_inicio = filtroFechaInicio;
      if (filtroFechaFin) params.fecha_fin = filtroFechaFin;

      const response = await apiClient.get('/auditoria/', { params });

      setLogs(response.data.results || response.data || []);
      setTotalLogs(response.data.count || 0);
      setTotalPages(Math.ceil((response.data.count || 0) / pageSize));
    } catch (error) {
      console.error('Error al cargar logs:', error);
      toast.error('Error al cargar registros de auditoría');
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [
    currentPage,
    pageSize,
    searchTerm,
    filtroAccion,
    filtroModelo,
    filtroUsuario,
    filtroFechaInicio,
    filtroFechaFin,
  ]);

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      cargarLogs();
    }, 500);

    return () => clearTimeout(delayDebounceFn);
  }, [cargarLogs]);

  const limpiarFiltros = () => {
    setSearchTerm('');
    setFiltroAccion('');
    setFiltroModelo('');
    setFiltroUsuario('');
    setFiltroFechaInicio('');
    setFiltroFechaFin('');
    setCurrentPage(1);
  };

  const formatFecha = (fecha) => {
    return new Date(fecha).toLocaleString('es-MX', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getAccionColor = (accion) => {
    const colores = {
      'CREATE': { bg: '#DCFCE7', text: '#166534', label: 'Crear' },
      'UPDATE': { bg: '#DBEAFE', text: '#1E40AF', label: 'Actualizar' },
      'DELETE': { bg: '#FEE2E2', text: '#991B1B', label: 'Eliminar' },
      'LOGIN': { bg: '#E0E7FF', text: '#3730A3', label: 'Login' },
      'LOGOUT': { bg: '#F3F4F6', text: '#374151', label: 'Logout' }
    };
    return colores[accion] || { bg: '#F3F4F6', text: '#4B5563', label: accion };
  };

  const totalBadge = totalLogs ? `${totalLogs.toLocaleString()} registros` : 'Sin registros';

  const badgeContent = (
    <span className="flex items-center gap-2 rounded-full bg-white/20 px-4 py-1 text-sm font-semibold">
      <FaDatabase />
      {totalBadge}
    </span>
  );

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        icon={FaFileAlt}
        title="Auditoría del Sistema"
        subtitle="Registro de todas las acciones realizadas en el sistema"
        badge={badgeContent}
      />

      {/* Filtros */}
      <div className="bg-white rounded-xl shadow-lg p-6 border-l-4" style={{ borderLeftColor: '#9F2241' }}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold" style={{ color: '#6B1839' }}>
            <FaFilter className="inline mr-2" />
            Filtros de Búsqueda
          </h3>
          <button
            onClick={limpiarFiltros}
            className="px-4 py-2 rounded-lg text-sm font-semibold transition-all hover:scale-105"
            style={{ backgroundColor: '#F3F4F6', color: '#6B7280' }}
          >
            Limpiar Filtros
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Búsqueda general */}
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: '#6B1839' }}>
              Búsqueda General
            </label>
            <div className="relative">
              <FaSearch className="absolute left-3 top-3.5 text-gray-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Buscar en registros..."
                className="w-full pl-10 pr-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none transition-all"
                onFocus={(e) => {
                  e.target.style.borderColor = '#9F2241';
                  e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = '#E5E7EB';
                  e.target.style.boxShadow = 'none';
                }}
              />
            </div>
          </div>

          {/* Acción */}
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: '#6B1839' }}>
              Acción
            </label>
            <select
              value={filtroAccion}
              onChange={(e) => setFiltroAccion(e.target.value)}
              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none transition-all"
              onFocus={(e) => {
                e.target.style.borderColor = '#9F2241';
                e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = '#E5E7EB';
                e.target.style.boxShadow = 'none';
              }}
            >
              {accionesDisponibles.map(a => (
                <option key={a.value} value={a.value}>{a.label}</option>
              ))}
            </select>
          </div>

          {/* Módulo */}
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: '#6B1839' }}>
              Módulo
            </label>
            <select
              value={filtroModelo}
              onChange={(e) => setFiltroModelo(e.target.value)}
              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none transition-all"
              onFocus={(e) => {
                e.target.style.borderColor = '#9F2241';
                e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = '#E5E7EB';
                e.target.style.boxShadow = 'none';
              }}
            >
              {modelosDisponibles.map(m => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          {/* Fecha Inicio */}
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: '#6B1839' }}>
              Fecha Inicio
            </label>
            <input
              type="date"
              value={filtroFechaInicio}
              onChange={(e) => setFiltroFechaInicio(e.target.value)}
              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none transition-all"
              onFocus={(e) => {
                e.target.style.borderColor = '#9F2241';
                e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = '#E5E7EB';
                e.target.style.boxShadow = 'none';
              }}
            />
          </div>

          {/* Fecha Fin */}
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: '#6B1839' }}>
              Fecha Fin
            </label>
            <input
              type="date"
              value={filtroFechaFin}
              onChange={(e) => setFiltroFechaFin(e.target.value)}
              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none transition-all"
              onFocus={(e) => {
                e.target.style.borderColor = '#9F2241';
                e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = '#E5E7EB';
                e.target.style.boxShadow = 'none';
              }}
            />
          </div>

          {/* Registros por página */}
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: '#6B1839' }}>
              Registros por página
            </label>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none transition-all"
              onFocus={(e) => {
                e.target.style.borderColor = '#9F2241';
                e.target.style.boxShadow = '0 0 0 3px rgba(159, 34, 65, 0.1)';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = '#E5E7EB';
                e.target.style.boxShadow = 'none';
              }}
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tabla de Logs */}
      <div className="bg-white rounded-xl shadow-lg overflow-hidden border-l-4" style={{ borderLeftColor: '#9F2241' }}>
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="animate-spin rounded-full h-16 w-16 border-b-4 mx-auto mb-4" style={{ borderColor: '#9F2241' }}></div>
              <p className="text-gray-600 font-semibold">Cargando registros de auditoría...</p>
            </div>
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center py-20">
            <FaFileAlt className="mx-auto text-6xl text-gray-300 mb-4" />
            <p className="text-xl font-semibold text-gray-600">No hay registros de auditoría</p>
            <p className="text-gray-500 mt-2">Los registros aparecerán cuando se realicen acciones en el sistema</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead style={{ background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)' }}>
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-bold text-white uppercase tracking-wider">
                      Fecha/Hora
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-white uppercase tracking-wider">
                      Usuario
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-white uppercase tracking-wider">
                      Acción
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-white uppercase tracking-wider">
                      Módulo
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-white uppercase tracking-wider">
                      Descripción
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-white uppercase tracking-wider">
                      IP
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {logs.map((log, index) => {
                    const accionInfo = getAccionColor(log.accion);
                    return (
                      <tr key={log.id || index} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <FaClock className="text-gray-400" />
                            <span className="text-sm font-medium text-gray-900">
                              {formatFecha(log.fecha)}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <FaUser className="text-gray-400" />
                            <span className="text-sm font-semibold" style={{ color: '#6B1839' }}>
                              {log.usuario_nombre || log.usuario || 'Sistema'}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span 
                            className="px-3 py-1.5 rounded-full text-xs font-bold"
                            style={{ 
                              backgroundColor: accionInfo.bg, 
                              color: accionInfo.text 
                            }}
                          >
                            {accionInfo.label}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className="text-sm font-semibold text-gray-700">
                            {log.modelo || '-'}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className="text-sm text-gray-600">
                            {log.descripcion || log.detalle || '-'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-500">
                          {log.ip_address || '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Paginación */}
            {totalPages > 1 && (
              <Pagination
                page={currentPage}
                totalPages={totalPages}
                totalItems={totalLogs}
                pageSize={pageSize}
                onPageChange={setCurrentPage}
                onPageSizeChange={(size) => {
                  setPageSize(size);
                  setCurrentPage(1);
                }}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default Auditoria;













