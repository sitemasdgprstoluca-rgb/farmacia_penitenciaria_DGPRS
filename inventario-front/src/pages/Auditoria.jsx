import { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import {
  FaFileAlt,
  FaSearch,
  FaFilter,
  FaUser,
  FaClock,
  FaDatabase,
  FaDownload,
  FaEye,
  FaTimes,
  FaInfoCircle,
  FaFilePdf,
} from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import apiClient, { auditoriaAPI, descargarArchivo } from '../services/api';
import Pagination from '../components/Pagination';
import ExcelJS from 'exceljs';

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

// Conectar a datos reales del backend
const isDevSession = () => false;

const Auditoria = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalLogs, setTotalLogs] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  
  // Modal de detalle
  const [showDetalleModal, setShowDetalleModal] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);

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
    { value: 'crear', label: 'Crear' },
    { value: 'UPDATE', label: 'Actualizar' },
    { value: 'actualizar', label: 'Actualizar' },
    { value: 'DELETE', label: 'Eliminar' },
    { value: 'eliminar', label: 'Eliminar' },
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

  // Exportar a Excel
  const handleExportar = async () => {
    setExporting(true);
    try {
      // Obtener todos los datos con los filtros actuales (sin paginación)
      const params = { page_size: 10000 };
      if (searchTerm) params.search = searchTerm;
      if (filtroAccion) params.accion = filtroAccion;
      if (filtroModelo) params.modelo = filtroModelo;
      if (filtroUsuario) params.usuario = filtroUsuario;
      if (filtroFechaInicio) params.fecha_inicio = filtroFechaInicio;
      if (filtroFechaFin) params.fecha_fin = filtroFechaFin;

      const response = await apiClient.get('/auditoria/', { params });
      const datos = response.data.results || response.data || [];

      if (datos.length === 0) {
        toast.error('No hay datos para exportar');
        return;
      }

      // Crear workbook con ExcelJS
      const workbook = new ExcelJS.Workbook();
      workbook.created = new Date();
      const sheet = workbook.addWorksheet('Auditoría');

      // Definir columnas
      sheet.columns = [
        { header: 'ID', key: 'id', width: 8 },
        { header: 'Fecha/Hora', key: 'fecha', width: 22 },
        { header: 'Usuario', key: 'usuario', width: 20 },
        { header: 'Acción', key: 'accion', width: 12 },
        { header: 'Módulo', key: 'modelo', width: 15 },
        { header: 'Objeto', key: 'objeto', width: 25 },
        { header: 'Descripción', key: 'descripcion', width: 40 },
        { header: 'IP', key: 'ip', width: 15 },
        { header: 'Cambios', key: 'cambios', width: 50 },
      ];

      // Estilo del encabezado
      sheet.getRow(1).eachCell((cell) => {
        cell.fill = {
          type: 'pattern',
          pattern: 'solid',
          fgColor: { argb: 'FF9F2241' },
        };
        cell.font = { bold: true, color: { argb: 'FFFFFFFF' } };
        cell.alignment = { horizontal: 'center', vertical: 'middle' };
      });

      // Agregar datos
      datos.forEach((log) => {
        sheet.addRow({
          id: log.id,
          fecha: formatFecha(log.fecha),
          usuario: log.usuario_nombre || 'Sistema',
          accion: getAccionColor(log.accion).label,
          modelo: log.modelo || '-',
          objeto: log.objeto_repr || '-',
          descripcion: log.descripcion || '-',
          ip: log.ip_address || '-',
          cambios: log.cambios ? JSON.stringify(log.cambios, null, 2) : '-',
        });
      });

      // Generar y descargar archivo
      const buffer = await workbook.xlsx.writeBuffer();
      const blob = new Blob([buffer], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const fecha = new Date().toISOString().split('T')[0];
      link.download = `auditoria_${fecha}.xlsx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success(`Exportados ${datos.length} registros`);
    } catch (error) {
      console.error('Error al exportar:', error);
      toast.error('Error al exportar los datos');
    } finally {
      setExporting(false);
    }
  };

  // Exportar PDF con fondo institucional
  const handleExportarPdf = async () => {
    if (logs.length === 0) {
      toast.error('No hay registros para exportar');
      return;
    }
    
    setExportingPdf(true);
    try {
      const params = {
        search: searchTerm,
        accion: filtroAccion,
        modelo: filtroModelo,
        usuario: filtroUsuario,
        fecha_inicio: filtroFechaInicio,
        fecha_fin: filtroFechaFin,
        page_size: 500, // Exportar más registros en PDF
      };
      
      const response = await auditoriaAPI.exportarPdf(params);
      descargarArchivo(response, `auditoria_${new Date().toISOString().split('T')[0]}.pdf`);
      toast.success('PDF generado exitosamente');
    } catch (error) {
      console.error('Error al exportar PDF:', error);
      toast.error('Error al generar el PDF');
    } finally {
      setExportingPdf(false);
    }
  };

  // Ver detalle de un log
  const handleVerDetalle = (log) => {
    setSelectedLog(log);
    setShowDetalleModal(true);
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
    const accionUpper = (accion || '').toUpperCase();
    const colores = {
      'CREATE': { bg: '#DCFCE7', text: '#166534', label: 'Crear' },
      'CREAR': { bg: '#DCFCE7', text: '#166534', label: 'Crear' },
      'UPDATE': { bg: '#DBEAFE', text: '#1E40AF', label: 'Actualizar' },
      'ACTUALIZAR': { bg: '#DBEAFE', text: '#1E40AF', label: 'Actualizar' },
      'DELETE': { bg: '#FEE2E2', text: '#991B1B', label: 'Eliminar' },
      'ELIMINAR': { bg: '#FEE2E2', text: '#991B1B', label: 'Eliminar' },
      'LOGIN': { bg: '#E0E7FF', text: '#3730A3', label: 'Login' },
      'LOGOUT': { bg: '#F3F4F6', text: '#374151', label: 'Logout' },
      'AUTORIZAR': { bg: '#FEF3C7', text: '#92400E', label: 'Autorizar' },
      'RECHAZAR': { bg: '#FEE2E2', text: '#991B1B', label: 'Rechazar' },
      'SURTIR': { bg: '#D1FAE5', text: '#065F46', label: 'Surtir' },
    };
    return colores[accionUpper] || { bg: '#F3F4F6', text: '#4B5563', label: accion };
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
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <PageHeader
          icon={FaFileAlt}
          title="Auditoría del Sistema"
          subtitle="Registro de todas las acciones realizadas en el sistema"
          badge={badgeContent}
        />
        
        {/* Botones Exportar */}
        <div className="flex gap-2">
          <button
            onClick={handleExportarPdf}
            disabled={exportingPdf || loading || logs.length === 0}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg font-semibold text-white transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
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
          <button
            onClick={handleExportar}
            disabled={exporting || loading || logs.length === 0}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg font-semibold text-white transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)' }}
          >
            {exporting ? (
              <>
                <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                Exportando...
              </>
            ) : (
              <>
                <FaDownload />
                Exportar Excel
              </>
            )}
          </button>
        </div>
      </div>

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
              <div className="animate-spin rounded-full h-16 w-16 border-4 border-t-transparent mx-auto mb-4" style={{ borderColor: '#9F224133', borderTopColor: '#9F2241' }}></div>
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
                    <th className="px-6 py-4 text-center text-xs font-bold text-white uppercase tracking-wider">
                      Detalle
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
                        <td className="px-6 py-4 text-center">
                          <button
                            onClick={() => handleVerDetalle(log)}
                            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                            title="Ver detalle"
                          >
                            <FaEye className="text-gray-500 hover:text-blue-600" />
                          </button>
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

      {/* Modal de Detalle */}
      {showDetalleModal && selectedLog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
            {/* Header del Modal */}
            <div 
              className="px-6 py-4 flex items-center justify-between"
              style={{ background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)' }}
            >
              <div className="flex items-center gap-3 text-white">
                <FaInfoCircle className="text-xl" />
                <h3 className="text-lg font-bold">Detalle del Registro de Auditoría</h3>
              </div>
              <button
                onClick={() => setShowDetalleModal(false)}
                className="text-white/80 hover:text-white transition-colors"
              >
                <FaTimes className="text-xl" />
              </button>
            </div>

            {/* Contenido del Modal */}
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
              <div className="space-y-4">
                {/* Info básica */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase font-semibold mb-1">ID</p>
                    <p className="font-bold text-gray-900">{selectedLog.id}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Fecha/Hora</p>
                    <p className="font-bold text-gray-900">{formatFecha(selectedLog.fecha)}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Usuario</p>
                    <p className="font-bold" style={{ color: '#6B1839' }}>
                      {selectedLog.usuario_nombre || selectedLog.usuario || 'Sistema'}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Acción</p>
                    <span 
                      className="px-3 py-1.5 rounded-full text-xs font-bold inline-block"
                      style={{ 
                        backgroundColor: getAccionColor(selectedLog.accion).bg, 
                        color: getAccionColor(selectedLog.accion).text 
                      }}
                    >
                      {getAccionColor(selectedLog.accion).label}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Módulo</p>
                    <p className="font-bold text-gray-900">{selectedLog.modelo || '-'}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase font-semibold mb-1">IP</p>
                    <p className="font-mono text-gray-900">{selectedLog.ip_address || '-'}</p>
                  </div>
                </div>

                {selectedLog.objeto_repr && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Objeto Afectado</p>
                    <p className="font-bold text-gray-900">{selectedLog.objeto_repr}</p>
                    {selectedLog.objeto_id && (
                      <p className="text-xs text-gray-500 mt-1">ID: {selectedLog.objeto_id}</p>
                    )}
                  </div>
                )}

                {selectedLog.descripcion && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Descripción</p>
                    <p className="text-gray-900">{selectedLog.descripcion}</p>
                  </div>
                )}

                {/* Cambios realizados */}
                {selectedLog.cambios && Object.keys(selectedLog.cambios).length > 0 && (
                  <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                    <p className="text-xs text-blue-700 uppercase font-semibold mb-3 flex items-center gap-2">
                      <FaInfoCircle />
                      Cambios Realizados
                    </p>
                    <div className="bg-white rounded-lg p-3 overflow-x-auto">
                      <pre className="text-xs font-mono text-gray-700 whitespace-pre-wrap">
                        {JSON.stringify(selectedLog.cambios, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </div>

              {/* Botón cerrar */}
              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setShowDetalleModal(false)}
                  className="px-6 py-2.5 rounded-lg font-semibold text-white transition-all hover:scale-105"
                  style={{ background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)' }}
                >
                  Cerrar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Auditoria;













