import { useState, useEffect, useCallback } from 'react';
import { requisicionesAPI } from '../services/api';
import { usePermissions } from '../hooks/usePermissions';
import { ProtectedButton } from '../components/ProtectedAction';
import { toast } from 'react-hot-toast';
import {
  FaPlus, FaEye, FaPaperPlane, FaCheck, FaTimes,
  FaBoxOpen, FaBan, FaDownload, FaEdit, FaTrash,
  FaClipboardList
} from 'react-icons/fa';
import { DEV_CONFIG } from '../config/dev';
import PageHeader from '../components/PageHeader';
import { COLORS } from '../constants/theme';

const MOCK_REQUISICIONES = Array.from({ length: 20 }).map((_, index) => {
  const estados = ['borrador', 'enviada', 'autorizada', 'rechazada', 'surtida', 'cancelada'];
  const estado = estados[index % estados.length];
  const baseFolio = `REQ-${202400 + index}`;

  return {
    id: index + 1,
    folio: baseFolio,
    centro: 1,
    centro_nombre: 'Centro Penitenciario Simulado',
    usuario_solicita_nombre: estado === 'borrador' ? 'Usuario Centro' : 'Administrador',
    fecha_solicitud: new Date(Date.now() - index * 86400000).toISOString(),
    estado,
    total_items: 3 + (index % 4),
    total_solicitado: 150 + index * 5,
    total_autorizado: estado === 'autorizada' ? 140 + index * 5 : null,
    comentario: estado === 'rechazada' ? 'Faltan datos' : '',
    items: [
      { id: 1, producto_clave: 'MED-001', descripcion: 'Medicamento 1' },
      { id: 2, producto_clave: 'MED-012', descripcion: 'Medicamento 2' },
    ],
  };
});

const Requisiciones = () => {
  const [requisiciones, setRequisiciones] = useState([]);
  const [loading, setLoading] = useState(false);
  const { permisos, user, getRolPrincipal } = usePermissions();

  const [filtroEstado, setFiltroEstado] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const PAGE_SIZE = 10;
  const [currentPage, setCurrentPage] = useState(1);
  const [totalRequisiciones, setTotalRequisiciones] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  const applyMockRequisiciones = useCallback(() => {
    let data = [...MOCK_REQUISICIONES].sort(
      (a, b) => new Date(b.fecha_solicitud) - new Date(a.fecha_solicitud),
    );

    if (filtroEstado) data = data.filter((req) => req.estado === filtroEstado);
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      data = data.filter((req) => req.folio.toLowerCase().includes(term));
    }

    const total = data.length;
    const start = (currentPage - 1) * PAGE_SIZE;
    const sliced = data.slice(start, start + PAGE_SIZE);

    setRequisiciones(sliced);
    setTotalRequisiciones(total);
    setTotalPages(Math.max(1, Math.ceil(total / PAGE_SIZE)));
    setLoading(false);
  }, [PAGE_SIZE, currentPage, filtroEstado, searchTerm]);

  const cargarRequisiciones = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      if ((!token && DEV_CONFIG.ENABLED) || token === 'dev-token') {
        applyMockRequisiciones();
        return;
      }

      const params = {
        page: currentPage,
        page_size: PAGE_SIZE,
        ordering: '-fecha_solicitud',
      };
      if (filtroEstado) params.estado = filtroEstado;
      if (searchTerm) params.search = searchTerm;

      const response = await requisicionesAPI.getAll(params);
      const results = response.data.results || response.data;
      const orderedResults = [...results].sort(
        (a, b) => new Date(b.fecha_solicitud) - new Date(a.fecha_solicitud),
      );
      setRequisiciones(orderedResults);
      const total = response.data.count || results.length;
      setTotalRequisiciones(total);
      setTotalPages(Math.max(1, Math.ceil(total / PAGE_SIZE)));
    } catch (error) {
      if (DEV_CONFIG.ENABLED || localStorage.getItem('token') === 'dev-token') {
        applyMockRequisiciones();
        return;
      }
      toast.error('Error al cargar requisiciones');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [PAGE_SIZE, applyMockRequisiciones, currentPage, filtroEstado, searchTerm]);

  useEffect(() => {
    setCurrentPage(1);
  }, [filtroEstado, searchTerm]);

  useEffect(() => {
    cargarRequisiciones();
  }, [cargarRequisiciones]);

  const puedeEditar = (requisicion) => {
    // Solo en BORRADOR y si es su requisición o es FARMACIA_ADMIN
    if (requisicion.estado !== 'borrador') return false;
    if (permisos.isFarmaciaAdmin) return true;
    if (permisos.isCentroUser) {
      const userCentro = user?.centro?.id || user?.profile?.centro?.id;
      return requisicion.centro === userCentro;
    }
    return false;
  };

  const puedeEnviar = (requisicion) => puedeEditar(requisicion) && requisicion.estado === 'borrador';

  const handleEnviar = async (id) => {
    if (!window.confirm('¿Enviar requisición? No podrás editarla después.')) return;
    try {
      await requisicionesAPI.enviar(id);
      toast.success('Requisición enviada correctamente');
      cargarRequisiciones();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al enviar requisición');
    }
  };

  const handleAutorizar = async (id) => {
    if (!window.confirm('¿Autorizar requisición?')) return;
    try {
      await requisicionesAPI.autorizar(id, {});
      toast.success('Requisición autorizada');
      cargarRequisiciones();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al autorizar');
    }
  };

  const handleRechazar = async (id) => {
    const motivo = prompt('Motivo del rechazo:');
    if (!motivo) return;
    try {
      await requisicionesAPI.rechazar(id, { motivo });
      toast.success('Requisición rechazada');
      cargarRequisiciones();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al rechazar');
    }
  };

  const handleSurtir = async (id) => {
    if (!window.confirm('¿Marcar como surtida? Se descontará del inventario.')) return;
    try {
      await requisicionesAPI.surtir(id);
      toast.success('Requisición surtida correctamente');
      cargarRequisiciones();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al surtir');
    }
  };

  const handleCancelar = async (id) => {
    if (!window.confirm('¿Cancelar requisición?')) return;
    try {
      await requisicionesAPI.cancelar(id);
      toast.success('Requisición cancelada');
      cargarRequisiciones();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al cancelar');
    }
  };

  const handleDescargarHoja = async (id, folio) => {
    try {
      const response = await requisicionesAPI.getHojaRecoleccion(id);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Hoja_Recoleccion_${folio}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Hoja de recolección descargada');
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al descargar hoja');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Eliminar esta requisición?')) return;
    try {
      await requisicionesAPI.delete(id);
      toast.success('Requisición eliminada correctamente');
      cargarRequisiciones();
    } catch (error) {
      toast.error(error.response?.data?.error || 'No se pudo eliminar la requisición');
    }
  };

  const getEstadoBadge = (estado) => {
    const badges = {
      borrador: 'bg-gray-100 text-gray-800',
      enviada: 'bg-blue-100 text-blue-800',
      autorizada: 'bg-green-100 text-green-800',
      parcial: 'bg-yellow-100 text-yellow-800',
      rechazada: 'bg-red-100 text-red-800',
      surtida: 'bg-purple-100 text-purple-800',
      cancelada: 'bg-gray-100 text-gray-600'
    };
    return badges[estado] || 'bg-gray-100 text-gray-800';
  };

  const filtrosActivos = [searchTerm, filtroEstado].filter(Boolean).length;

  const headerActions = (
    <ProtectedButton
      permission="crearRequisicion"
      onClick={() => (window.location.href = '/requisiciones/nueva')}
      type="button"
      className="flex items-center gap-2 rounded-full bg-white/90 px-4 py-2 text-sm font-bold hover:bg-white"
      style={{ color: COLORS.vino }}
    >
      <FaPlus /> Nueva Requisición
    </ProtectedButton>
  );

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        icon={FaClipboardList}
        title="Requisiciones"
        subtitle={`Total: ${totalRequisiciones} | Página ${currentPage} de ${totalPages} | Rol: ${getRolPrincipal()}`}
        badge={filtrosActivos ? `${filtrosActivos} filtros activos` : null}
        actions={headerActions}
      />

      {/* Filtros */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input
            type="text"
            placeholder="Buscar por folio..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          />

          <select
            value={filtroEstado}
            onChange={(e) => setFiltroEstado(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todos los estados</option>
            <option value="borrador">Borrador</option>
            <option value="enviada">Enviada</option>
            <option value="autorizada">Autorizada</option>
            <option value="parcial">Parcial</option>
            <option value="rechazada">Rechazada</option>
            <option value="surtida">Surtida</option>
            <option value="cancelada">Cancelada</option>
          </select>
        </div>
      </div>

      {/* Lista de Requisiciones */}
      <div className="grid grid-cols-1 gap-4">
        {loading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-2">Cargando requisiciones...</p>
          </div>
        ) : requisiciones.length === 0 ? (
          <div className="text-center py-8 bg-white rounded-lg shadow">
            <p className="text-gray-500">No hay requisiciones</p>
          </div>
        ) : (
          requisiciones.map((req, index) => {
            const totalProductos = req.total_items ?? req.total_productos ?? req.items?.length ?? 0;
            return (
              <div key={req.id || index} className="bg-white p-6 rounded-lg shadow">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-lg font-bold text-gray-800">{req.folio}</h3>
                    <p className="text-sm text-gray-600">
                      Centro: {req.centro_nombre} | Solicitante: {req.usuario_solicita_nombre || 'N/D'}
                    </p>
                    <p className="text-xs text-gray-500">
                      Fecha: {new Date(req.fecha_solicitud).toLocaleDateString()}
                    </p>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${getEstadoBadge(req.estado)}`}>
                    {req.estado.toUpperCase()}
                  </span>
                </div>

                <div className="mb-4">
                  <p className="text-sm">
                    <strong>Productos:</strong> {totalProductos}
                  </p>
                  {req.observaciones && (
                    <p className="text-sm text-gray-600 mt-1">
                      <strong>Observaciones:</strong> {req.observaciones}
                    </p>
                  )}
                  {req.motivo_rechazo && (
                    <p className="text-sm text-red-600 mt-1">
                      <strong>Motivo de rechazo:</strong> {req.motivo_rechazo}
                    </p>
                  )}
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => (window.location.href = `/requisiciones/${req.id}`)}
                    className="bg-gray-100 text-gray-700 px-3 py-1 rounded text-sm flex items-center gap-1 hover:bg-gray-200"
                  >
                    <FaEye /> Ver detalle
                  </button>

                  {puedeEditar(req) && (
                    <button
                      onClick={() => (window.location.href = `/requisiciones/${req.id}/editar`)}
                      className="bg-blue-100 text-blue-700 px-3 py-1 rounded text-sm flex items-center gap-1 hover:bg-blue-200"
                    >
                      <FaEdit /> Editar
                    </button>
                  )}

                  {puedeEnviar(req) && (
                    <button
                      onClick={() => handleEnviar(req.id)}
                      className="bg-green-100 text-green-700 px-3 py-1 rounded text-sm flex items-center gap-1 hover:bg-green-200"
                    >
                      <FaPaperPlane /> Enviar
                    </button>
                  )}

                  {req.estado === 'enviada' && permisos.autorizarRequisicion && (
                    <button
                      onClick={() => handleAutorizar(req.id)}
                      className="bg-green-600 text-white px-3 py-1 rounded text-sm flex items-center gap-1 hover:bg-green-700"
                    >
                      <FaCheck /> Autorizar
                    </button>
                  )}

                  {req.estado === 'enviada' && permisos.rechazarRequisicion && (
                    <button
                      onClick={() => handleRechazar(req.id)}
                      className="bg-red-600 text-white px-3 py-1 rounded text-sm flex items-center gap-1 hover:bg-red-700"
                    >
                      <FaTimes /> Rechazar
                    </button>
                  )}

                  {req.estado === 'autorizada' && permisos.surtirRequisicion && (
                    <button
                      onClick={() => handleSurtir(req.id)}
                      className="bg-purple-600 text-white px-3 py-1 rounded text-sm flex items-center gap-1 hover:bg-purple-700"
                    >
                      <FaBoxOpen /> Marcar surtida
                    </button>
                  )}

                  {(req.estado === 'autorizada' || req.estado === 'surtida') && permisos.descargarHojaRecoleccion && (
                    <button
                      onClick={() => handleDescargarHoja(req.id, req.folio)}
                      className="bg-blue-600 text-white px-3 py-1 rounded text-sm flex items-center gap-1 hover:bg-blue-700"
                    >
                      <FaDownload /> Hoja de recolección
                    </button>
                  )}

                  {!['surtida', 'cancelada'].includes(req.estado) && (
                    <button
                      onClick={() => handleCancelar(req.id)}
                      className="bg-gray-600 text-white px-3 py-1 rounded text-sm flex items-center gap-1 hover:bg-gray-700"
                    >
                      <FaBan /> Cancelar
                    </button>
                  )}

                  {puedeEditar(req) && permisos.eliminarRequisicion && (
                    <button
                      onClick={() => handleDelete(req.id)}
                      className="bg-red-600 text-white px-3 py-1 rounded text-sm flex items-center gap-1 hover:bg-red-700"
                    >
                      <FaTrash /> Eliminar
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {!loading && totalRequisiciones > 0 && (
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mt-6">
          <p className="text-sm text-gray-600">
            Mostrando {totalRequisiciones === 0 ? 0 : (currentPage - 1) * PAGE_SIZE + 1}-
            {Math.min(currentPage * PAGE_SIZE, totalRequisiciones)} de {totalRequisiciones} requisiciones
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 border rounded disabled:opacity-50"
            >
              Anterior
            </button>
            <span className="text-sm text-gray-700">
              Página {currentPage} de {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 border rounded disabled:opacity-50"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Requisiciones;
