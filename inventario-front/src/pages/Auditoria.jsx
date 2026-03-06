/**
 * Panel de Auditoría - SUPER ADMIN
 * 
 * Trazabilidad completa de todas las acciones del sistema.
 * ACCESO EXCLUSIVO: Solo usuarios con is_superuser=True
 * 
 * Características:
 * - Tabla paginada con todos los eventos del sistema
 * - Filtros por: fecha, usuario, centro, módulo, acción, resultado
 * - Vista detalle con before/after de los cambios
 * - Estadísticas de actividad
 * - Exportación a Excel y PDF
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { usePermissions } from '../hooks/usePermissions';
import { auditoriaAPI, centrosAPI } from '../services/api';
import toast from 'react-hot-toast';

// Hook para debounce
const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value);
  
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    
    return () => clearTimeout(handler);
  }, [value, delay]);
  
  return debouncedValue;
};
import {
  FaShieldAlt,
  FaFilter,
  FaSync,
  FaFileDownload,
  FaEye,
  FaTimes,
  FaChartBar,
  FaExclamationTriangle,
  FaCheckCircle,
  FaTimesCircle,
  FaClock,
  FaUser,
  FaBuilding,
  FaBox,
  FaArrowRight,
} from 'react-icons/fa';

// Constantes para el módulo
const RESULTADOS = [
  { value: '', label: 'Todos' },
  { value: 'success', label: 'Exitoso', color: 'green' },
  { value: 'fail', label: 'Fallido', color: 'red' },
  { value: 'error', label: 'Error', color: 'red' },
  { value: 'warning', label: 'Advertencia', color: 'yellow' },
];

const METODOS_HTTP = [
  { value: '', label: 'Todos' },
  { value: 'GET', label: 'GET (Consulta)' },
  { value: 'POST', label: 'POST (Crear)' },
  { value: 'PUT', label: 'PUT (Actualizar)' },
  { value: 'PATCH', label: 'PATCH (Modificar)' },
  { value: 'DELETE', label: 'DELETE (Eliminar)' },
];

// Badge de resultado con colores
const ResultadoBadge = ({ resultado }) => {
  const config = {
    success: { bg: 'bg-green-100', text: 'text-green-800', icon: FaCheckCircle },
    fail: { bg: 'bg-red-100', text: 'text-red-800', icon: FaTimesCircle },
    error: { bg: 'bg-red-100', text: 'text-red-800', icon: FaExclamationTriangle },
    warning: { bg: 'bg-yellow-100', text: 'text-yellow-800', icon: FaExclamationTriangle },
  };
  const style = config[resultado] || config.success;
  const Icon = style.icon;
  
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${style.bg} ${style.text}`}>
      <Icon className="w-3 h-3 mr-1" />
      {resultado}
    </span>
  );
};

// Modal de detalle del evento
const DetalleModal = ({ evento, onClose }) => {
  if (!evento) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:p-0">
        <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" onClick={onClose} />
        
        <div className="relative inline-block w-full max-w-4xl p-6 overflow-hidden text-left align-middle transition-all transform bg-white rounded-lg shadow-xl">
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                Detalle del Evento #{evento.id}
              </h3>
              <p className="text-sm text-gray-500">
                {new Date(evento.fecha).toLocaleString('es-MX')}
              </p>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <FaTimes className="w-6 h-6" />
            </button>
          </div>

          {/* Content */}
          <div className="mt-4 space-y-6">
            {/* Info General */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-gray-500">Usuario</p>
                <p className="font-medium">{evento.usuario_nombre || 'Sistema'}</p>
                <p className="text-xs text-gray-400">{evento.usuario_username}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Rol</p>
                <p className="font-medium">{evento.rol_usuario || '-'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Centro</p>
                <p className="font-medium">{evento.centro_nombre || 'N/A'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Resultado</p>
                <ResultadoBadge resultado={evento.resultado} />
              </div>
            </div>

            {/* Acción y Módulo */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
              <div>
                <p className="text-xs text-gray-500">Acción</p>
                <p className="font-semibold text-institucional-800">{evento.accion}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Módulo</p>
                <p className="font-medium">{evento.modelo}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Objeto ID</p>
                <p className="font-mono text-sm">{evento.objeto_id || '-'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Status Code</p>
                <p className={`font-mono ${evento.status_code >= 400 ? 'text-red-600' : 'text-green-600'}`}>
                  {evento.status_code}
                </p>
              </div>
            </div>

            {/* Contexto Técnico */}
            <div className="p-4 bg-gray-100 rounded-lg">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Contexto Técnico</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-gray-500">IP:</span> {evento.ip_address || '-'}
                </div>
                <div>
                  <span className="text-gray-500">Método:</span> {evento.metodo_http || '-'}
                </div>
                <div className="md:col-span-2">
                  <span className="text-gray-500">Endpoint:</span> <code className="text-xs bg-gray-200 px-1 rounded">{evento.endpoint || '-'}</code>
                </div>
                {evento.request_id && (
                  <div className="md:col-span-2">
                    <span className="text-gray-500">Request ID:</span> <code className="text-xs">{evento.request_id}</code>
                  </div>
                )}
                {evento.idempotency_key && (
                  <div className="md:col-span-2">
                    <span className="text-gray-500">Idempotency Key:</span> <code className="text-xs">{evento.idempotency_key}</code>
                  </div>
                )}
              </div>
            </div>

            {/* User Agent */}
            {evento.user_agent && (
              <div className="text-xs text-gray-400 truncate">
                <span className="font-medium">User-Agent:</span> {evento.user_agent}
              </div>
            )}

            {/* Before / After */}
            {(evento.datos_anteriores || evento.datos_nuevos) && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {evento.datos_anteriores && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                      <span className="text-red-600">← Antes</span>
                    </h4>
                    <pre className="p-3 bg-red-50 rounded-lg text-xs overflow-auto max-h-64">
                      {JSON.stringify(evento.datos_anteriores, null, 2)}
                    </pre>
                  </div>
                )}
                {evento.datos_nuevos && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                      <span className="text-green-600">Después →</span>
                    </h4>
                    <pre className="p-3 bg-green-50 rounded-lg text-xs overflow-auto max-h-64">
                      {JSON.stringify(evento.datos_nuevos, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* Resumen de Cambios */}
            {evento.cambios_resumen && evento.cambios_resumen.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Cambios Detectados</h4>
                <div className="space-y-2">
                  {evento.cambios_resumen.map((cambio, idx) => (
                    <div key={idx} className="flex items-center gap-2 p-2 bg-gray-50 rounded text-sm">
                      <span className="font-medium text-gray-600">{cambio.campo}:</span>
                      <span className="text-red-500 line-through">{JSON.stringify(cambio.antes)}</span>
                      <FaArrowRight className="w-4 h-4 text-gray-400" />
                      <span className="text-green-600">{JSON.stringify(cambio.despues)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Detalles Adicionales */}
            {evento.detalles && Object.keys(evento.detalles).length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Detalles Adicionales</h4>
                <pre className="p-3 bg-gray-50 rounded-lg text-xs overflow-auto max-h-32">
                  {JSON.stringify(evento.detalles, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="mt-6 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-white rounded-md bg-institucional-600 hover:bg-institucional-700"
            >
              Cerrar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Componente de Estadísticas
const StatsCard = ({ stats }) => {
  if (!stats) return null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div className="bg-white p-4 rounded-lg shadow border-l-4 border-institucional-600">
        <p className="text-sm text-gray-500">Total Eventos (30d)</p>
        <p className="text-2xl font-bold text-gray-900">{stats.total_eventos?.toLocaleString()}</p>
      </div>
      <div className="bg-white p-4 rounded-lg shadow border-l-4 border-red-500">
        <p className="text-sm text-gray-500">Eventos Críticos</p>
        <p className="text-2xl font-bold text-red-600">{stats.eventos_criticos?.toLocaleString()}</p>
      </div>
      <div className="bg-white p-4 rounded-lg shadow border-l-4 border-green-500">
        <p className="text-sm text-gray-500">Módulo Más Activo</p>
        <p className="text-lg font-semibold text-gray-900">
          {stats.eventos_por_modulo?.[0]?.modelo || '-'}
        </p>
      </div>
      <div className="bg-white p-4 rounded-lg shadow border-l-4 border-blue-500">
        <p className="text-sm text-gray-500">Usuario Más Activo</p>
        <p className="text-lg font-semibold text-gray-900">
          {stats.usuarios_activos?.[0]?.usuario__username || '-'}
        </p>
      </div>
    </div>
  );
};

// Componente Principal
export default function Auditoria() {
  const { permisos, user } = usePermissions();
  const [eventos, setEventos] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mostrarFiltros, setMostrarFiltros] = useState(false);
  const [eventoSeleccionado, setEventoSeleccionado] = useState(null);
  const [cargandoDetalle, setCargandoDetalle] = useState(false);
  
  // Paginación
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  
  // Filtros inmediatos (selects)
  const [filtrosSelect, setFiltrosSelect] = useState({
    centro: '',
    modulo: '',
    accion: '',
    resultado: '',
    metodo: '',
  });
  
  // Filtros con debounce (texto y fechas)
  const [filtrosTexto, setFiltrosTexto] = useState({
    fecha_inicio: '',
    fecha_fin: '',
    usuario: '',
    objeto_id: '',
  });
  
  // Aplicar debounce a filtros de texto (500ms)
  const debouncedFiltrosTexto = useDebounce(filtrosTexto, 500);
  
  // Combinar filtros para enviar al API
  const filtrosCombinados = { ...filtrosSelect, ...debouncedFiltrosTexto };
  
  // Opciones para filtros
  const [centros, setCentros] = useState([]);
  const [modulos, setModulos] = useState([]);
  const [acciones, setAcciones] = useState([]);

  // Verificar acceso (solo SUPER ADMIN)
  const esSuperAdmin = user?.is_superuser === true;
  
  // Referencia para evitar llamadas duplicadas
  const isFirstRender = useRef(true);

  // Cargar datos iniciales
  useEffect(() => {
    if (esSuperAdmin) {
      cargarOpciones();
      cargarStats();
    }
  }, [esSuperAdmin]);

  // Cargar eventos cuando cambie página
  useEffect(() => {
    if (esSuperAdmin) {
      cargarEventos();
    }
  }, [page, esSuperAdmin]);
  
  // Cargar eventos cuando cambien los filtros (con reset de página)
  useEffect(() => {
    if (esSuperAdmin && !isFirstRender.current) {
      setPage(1); // Resetear a página 1 cuando cambian filtros
      cargarEventos();
    }
    isFirstRender.current = false;
  }, [filtrosSelect, debouncedFiltrosTexto]);

  const cargarOpciones = async () => {
    try {
      const [centrosRes, modulosRes, accionesRes] = await Promise.all([
        centrosAPI.getAll(),
        auditoriaAPI.getModulos(),
        auditoriaAPI.getAcciones(),
      ]);
      setCentros(centrosRes.data?.results || centrosRes.data || []);
      setModulos(modulosRes.data || []);
      setAcciones(accionesRes.data || []);
    } catch (error) {
      console.error('Error cargando opciones de filtros:', error);
    }
  };

  const cargarStats = async () => {
    try {
      const response = await auditoriaAPI.getStats();
      setStats(response.data);
    } catch (error) {
      console.error('Error cargando estadísticas:', error);
    }
  };

  const cargarEventos = async () => {
    setLoading(true);
    try {
      // Construir params solo con valores no vacíos
      const params = { page };
      Object.entries(filtrosCombinados).forEach(([key, value]) => {
        if (value && value.trim && value.trim()) {
          params[key] = value.trim();
        } else if (value) {
          params[key] = value;
        }
      });

      const response = await auditoriaAPI.getAll(params);
      setEventos(response.data?.results || []);
      setTotalItems(response.data?.count || 0);
      setTotalPages(Math.ceil((response.data?.count || 0) / 50));
    } catch (error) {
      console.error('Error cargando eventos:', error);
      if (error.response?.status === 403) {
        toast.error('Acceso denegado. Solo SUPER ADMIN puede acceder.');
      } else if (error.response?.status !== 200) {
        // Solo mostrar error si no es un problema de red transitorio
        toast.error('Error al cargar auditoría');
      }
    } finally {
      setLoading(false);
    }
  };

  const verDetalle = async (evento) => {
    setCargandoDetalle(true);
    try {
      const response = await auditoriaAPI.getById(evento.id);
      setEventoSeleccionado(response.data);
    } catch (error) {
      console.error('Error cargando detalle:', error);
      // Usar datos básicos si falla
      setEventoSeleccionado(evento);
    } finally {
      setCargandoDetalle(false);
    }
  };

  const limpiarFiltros = () => {
    setFiltrosSelect({
      centro: '',
      modulo: '',
      accion: '',
      resultado: '',
      metodo: '',
    });
    setFiltrosTexto({
      fecha_inicio: '',
      fecha_fin: '',
      usuario: '',
      objeto_id: '',
    });
    setPage(1);
  };

  const exportarExcel = async () => {
    try {
      toast.loading('Generando Excel...');
      const response = await auditoriaAPI.exportar(filtrosCombinados);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Auditoria_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.dismiss();
      toast.success('Excel descargado');
    } catch (error) {
      toast.dismiss();
      toast.error('Error al exportar');
    }
  };

  const exportarPdf = async () => {
    try {
      toast.loading('Generando PDF...');
      const response = await auditoriaAPI.exportarPdf(filtrosCombinados);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Auditoria_${new Date().toISOString().split('T')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.dismiss();
      toast.success('PDF descargado');
    } catch (error) {
      toast.dismiss();
      toast.error('Error al exportar');
    }
  };

  // Si no es SUPER ADMIN, mostrar acceso denegado
  if (!esSuperAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-center p-8 bg-white rounded-lg shadow-lg">
          <FaExclamationTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Acceso Restringido</h1>
          <p className="text-gray-600 mb-4">
            El Panel de Auditoría es exclusivo para SUPER ADMIN.
          </p>
          <p className="text-sm text-gray-500">
            Si necesitas acceso, contacta al administrador del sistema.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-full">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
        <div className="flex items-center gap-3">
          <FaShieldAlt className="w-8 h-8 text-institucional-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Panel de Auditoría</h1>
            <p className="text-sm text-gray-500">Trazabilidad completa del sistema</p>
          </div>
        </div>
        
        <div className="flex items-center gap-2 mt-4 md:mt-0">
          <button
            onClick={() => setMostrarFiltros(!mostrarFiltros)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
              mostrarFiltros ? 'bg-institucional-100 border-institucional-300' : 'bg-white border-gray-300'
            }`}
          >
            <FaFilter className="w-5 h-5" />
            Filtros
          </button>
          <button
            onClick={cargarEventos}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <FaSync className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </button>
          <button
            onClick={exportarExcel}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            <FaFileDownload className="w-5 h-5" />
            Excel
          </button>
          <button
            onClick={exportarPdf}
            className="flex items-center gap-2 px-4 py-2 bg-institucional-600 text-white rounded-lg hover:bg-institucional-700"
          >
            <FaFileDownload className="w-5 h-5" />
            PDF
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <StatsCard stats={stats} />

      {/* Filtros */}
      {mostrarFiltros && (
        <div className="bg-white p-4 rounded-lg shadow mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-5 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Fecha Inicio</label>
              <input
                type="date"
                value={filtrosTexto.fecha_inicio}
                onChange={(e) => setFiltrosTexto({...filtrosTexto, fecha_inicio: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Fecha Fin</label>
              <input
                type="date"
                value={filtrosTexto.fecha_fin}
                onChange={(e) => setFiltrosTexto({...filtrosTexto, fecha_fin: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Usuario</label>
              <input
                type="text"
                value={filtrosTexto.usuario}
                onChange={(e) => setFiltrosTexto({...filtrosTexto, usuario: e.target.value})}
                placeholder="Buscar usuario..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Centro</label>
              <select
                value={filtrosSelect.centro}
                onChange={(e) => setFiltrosSelect({...filtrosSelect, centro: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              >
                <option value="">Todos</option>
                {centros.map(c => (
                  <option key={c.id} value={c.id}>{c.nombre}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Módulo</label>
              <select
                value={filtrosSelect.modulo}
                onChange={(e) => setFiltrosSelect({...filtrosSelect, modulo: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              >
                <option value="">Todos</option>
                {modulos.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Acción</label>
              <select
                value={filtrosSelect.accion}
                onChange={(e) => setFiltrosSelect({...filtrosSelect, accion: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              >
                <option value="">Todas</option>
                {acciones.map(a => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Resultado</label>
              <select
                value={filtrosSelect.resultado}
                onChange={(e) => setFiltrosSelect({...filtrosSelect, resultado: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              >
                {RESULTADOS.map(r => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Método HTTP</label>
              <select
                value={filtrosSelect.metodo}
                onChange={(e) => setFiltrosSelect({...filtrosSelect, metodo: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              >
                {METODOS_HTTP.map(m => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">ID Objeto</label>
              <input
                type="text"
                value={filtrosTexto.objeto_id}
                onChange={(e) => setFiltrosTexto({...filtrosTexto, objeto_id: e.target.value})}
                placeholder="ID específico..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={limpiarFiltros}
                className="w-full px-4 py-2 text-sm text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200"
              >
                Limpiar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tabla de Eventos */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Usuario</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Centro</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acción</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Módulo</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Objeto</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Resultado</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">IP</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Detalle</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan="9" className="px-4 py-8 text-center">
                    <FaSync className="w-8 h-8 animate-spin text-gray-400 mx-auto" />
                    <p className="mt-2 text-gray-500">Cargando eventos...</p>
                  </td>
                </tr>
              ) : eventos.length === 0 ? (
                <tr>
                  <td colSpan="9" className="px-4 py-8 text-center text-gray-500">
                    No se encontraron eventos con los filtros seleccionados
                  </td>
                </tr>
              ) : (
                eventos.map((evento) => (
                  <tr key={evento.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      <div className="flex items-center gap-1">
                        <FaClock className="w-4 h-4 text-gray-400" />
                        {new Date(evento.fecha).toLocaleString('es-MX', {
                          day: '2-digit',
                          month: '2-digit',
                          year: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <FaUser className="w-4 h-4 text-gray-400" />
                        <div>
                          <p className="text-sm font-medium text-gray-900">{evento.usuario_nombre || 'Sistema'}</p>
                          <p className="text-xs text-gray-500">{evento.rol_usuario}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {evento.centro_nombre || '-'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-medium rounded bg-institucional-100 text-institucional-800">
                        {evento.accion}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-1">
                        <FaBox className="w-4 h-4 text-gray-400" />
                        <span className="text-sm text-gray-900">{evento.modelo}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                        {evento.objeto_id || '-'}
                      </code>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <ResultadoBadge resultado={evento.resultado} />
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500 font-mono">
                      {evento.ip_address || '-'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-center">
                      <button
                        onClick={() => verDetalle(evento)}
                        className="p-1 text-institucional-600 hover:text-institucional-800 hover:bg-institucional-50 rounded"
                        title="Ver detalle"
                      >
                        <FaEye className="w-5 h-5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Paginación */}
        <div className="px-4 py-3 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
          <p className="text-sm text-gray-700">
            Mostrando <span className="font-medium">{eventos.length}</span> de{' '}
            <span className="font-medium">{totalItems.toLocaleString()}</span> eventos
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 text-sm border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
            >
              Anterior
            </button>
            <span className="px-3 py-1 text-sm">
              Página {page} de {totalPages}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1 text-sm border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
            >
              Siguiente
            </button>
          </div>
        </div>
      </div>

      {/* Modal de Detalle */}
      {eventoSeleccionado && (
        <DetalleModal
          evento={eventoSeleccionado}
          onClose={() => setEventoSeleccionado(null)}
        />
      )}
    </div>
  );
}
