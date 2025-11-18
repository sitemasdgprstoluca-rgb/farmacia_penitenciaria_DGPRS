import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { requisicionesAPI } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { toast } from 'react-toastify';
import { FaArrowLeft, FaPaperPlane, FaCheck, FaTimes, FaTruck, FaDownload } from 'react-icons/fa';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import './RequisicionDetalle.css';

const RequisicionDetalle = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [requisicion, setRequisicion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [cantidadesAutorizadas, setCantidadesAutorizadas] = useState({});
  const [comentario, setComentario] = useState('');

  const isFarmaciaAdmin = user?.rol === 'SUPERUSER' || user?.rol === 'FARMACIA_ADMIN';
  const isCentroUser = user?.rol === 'CENTRO_USER';

  useEffect(() => {
    if (id !== 'nueva') {
      loadRequisicion();
    } else {
      setLoading(false);
      // Modo creación
      setRequisicion({
        estado: 'BORRADOR',
        items: []
      });
    }
  }, [id, loadRequisicion]);

  const loadRequisicion = useCallback(async () => {
    try {
      setLoading(true);
      const response = await requisicionesAPI.get(id);
      setRequisicion(response.data);
      
      // Inicializar cantidades autorizadas
      const cantidades = {};
      response.data.items.forEach(item => {
        cantidades[item.id] = item.cantidad_autorizada || item.cantidad_solicitada;
      });
      setCantidadesAutorizadas(cantidades);
    } catch (error) {
      toast.error('Error al cargar requisición');
      navigate('/requisiciones');
    } finally {
      setLoading(false);
    }
  }, [id, navigate]);

  const handleEnviar = async () => {
    if (!window.confirm('¿Está seguro de enviar esta requisición?')) return;

    try {
      setProcessing(true);
      await requisicionesAPI.enviar(id);
      toast.success('Requisición enviada');
      loadRequisicion();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al enviar requisición');
    } finally {
      setProcessing(false);
    }
  };

  const handleAutorizar = async () => {
    if (!window.confirm('¿Está seguro de autorizar esta requisición?')) return;

    try {
      setProcessing(true);
      const items = requisicion.items.map(item => ({
        id: item.id,
        cantidad_autorizada: cantidadesAutorizadas[item.id] || 0
      }));

      await requisicionesAPI.autorizar(id, { items, comentario });
      toast.success('Requisición autorizada');
      loadRequisicion();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al autorizar requisición');
      if (error.response?.data?.errores) {
        console.error('Errores:', error.response.data.errores);
      }
    } finally {
      setProcessing(false);
    }
  };

  const handleRechazar = async () => {
    const motivo = window.prompt('Ingrese el motivo del rechazo:');
    if (!motivo) return;

    try {
      setProcessing(true);
      await requisicionesAPI.rechazar(id, { comentario: motivo });
      toast.success('Requisición rechazada');
      loadRequisicion();
    } catch (error) {
      toast.error('Error al rechazar requisición');
    } finally {
      setProcessing(false);
    }
  };

  const handleSurtir = async () => {
    if (!window.confirm('¿Está seguro de surtir esta requisición? Esta acción afectará el inventario.')) return;

    try {
      setProcessing(true);
      const response = await requisicionesAPI.surtir(id);
      toast.success(response.data.mensaje);
      loadRequisicion();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al surtir requisición');
      if (error.response?.data?.errores) {
        console.error('Errores:', error.response.data.errores);
      }
    } finally {
      setProcessing(false);
    }
  };

  const handleCantidadChange = (itemId, value) => {
    setCantidadesAutorizadas({
      ...cantidadesAutorizadas,
      [itemId]: parseFloat(value) || 0
    });
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Cargando requisición...</p>
      </div>
    );
  }

  if (!requisicion) {
    return <div className="error-container">Requisición no encontrada</div>;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <button onClick={() => navigate('/requisiciones')} className="btn-back">
          <FaArrowLeft /> Volver
        </button>
        <div className="header-info">
          <h1>Requisición {requisicion.folio || 'Nueva'}</h1>
          {requisicion.folio && (
            <span className={`badge badge-lg ${getEstadoBadge(requisicion.estado)}`}>
              {requisicion.estado_display}
            </span>
          )}
        </div>
        <div className="header-actions">
          {requisicion.estado === 'BORRADOR' && isCentroUser && (
            <button onClick={handleEnviar} className="btn btn-primary" disabled={processing}>
              <FaPaperPlane /> Enviar
            </button>
          )}
          {requisicion.estado === 'ENVIADA' && isFarmaciaAdmin && (
            <>
              <button onClick={handleRechazar} className="btn btn-danger" disabled={processing}>
                <FaTimes /> Rechazar
              </button>
              <button onClick={handleAutorizar} className="btn btn-success" disabled={processing}>
                <FaCheck /> Autorizar
              </button>
            </>
          )}
          {requisicion.estado === 'AUTORIZADA' && isFarmaciaAdmin && (
            <button onClick={handleSurtir} className="btn btn-primary" disabled={processing}>
              <FaTruck /> Surtir
            </button>
          )}
          {requisicion.estado === 'SURTIDA' && (
            <button className="btn btn-secondary">
              <FaDownload /> Descargar PDF
            </button>
          )}
        </div>
      </div>

      <div className="requisicion-content">
        <div className="requisicion-info-card">
          <h3>Información General</h3>
          <div className="info-grid">
            <div className="info-item">
              <label>Centro:</label>
              <span>{requisicion.centro_detalle?.nombre || '-'}</span>
            </div>
            <div className="info-item">
              <label>Solicitante:</label>
              <span>{requisicion.solicitante_nombre || '-'}</span>
            </div>
            <div className="info-item">
              <label>Fecha de solicitud:</label>
              <span>
                {requisicion.created_at 
                  ? format(new Date(requisicion.created_at), 'dd/MMM/yyyy HH:mm', { locale: es })
                  : '-'}
              </span>
            </div>
            {requisicion.fecha_autorizacion && (
              <>
                <div className="info-item">
                  <label>Autorizada por:</label>
                  <span>{requisicion.autorizada_por_nombre}</span>
                </div>
                <div className="info-item">
                  <label>Fecha autorización:</label>
                  <span>
                    {format(new Date(requisicion.fecha_autorizacion), 'dd/MMM/yyyy HH:mm', { locale: es })}
                  </span>
                </div>
              </>
            )}
            {requisicion.comentario_autorizacion && (
              <div className="info-item full-width">
                <label>Comentario:</label>
                <span>{requisicion.comentario_autorizacion}</span>
              </div>
            )}
          </div>
        </div>

        <div className="requisicion-items-card">
          <h3>Items Solicitados</h3>
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Producto</th>
                  <th>Cantidad Solicitada</th>
                  {(requisicion.estado === 'ENVIADA' && isFarmaciaAdmin) && (
                    <th>Cantidad a Autorizar</th>
                  )}
                  {requisicion.estado !== 'BORRADOR' && requisicion.estado !== 'ENVIADA' && (
                    <th>Cantidad Autorizada</th>
                  )}
                  {requisicion.estado !== 'BORRADOR' && requisicion.estado !== 'ENVIADA' && (
                    <th>Diferencia</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {requisicion.items?.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <strong>{item.producto_detalle.clave}</strong>
                      <br />
                      <small>{item.producto_detalle.descripcion}</small>
                    </td>
                    <td>{item.cantidad_solicitada} {item.producto_detalle.unidad_medida}</td>
                    {(requisicion.estado === 'ENVIADA' && isFarmaciaAdmin) && (
                      <td>
                        <input
                          type="number"
                          value={cantidadesAutorizadas[item.id] || 0}
                          onChange={(e) => handleCantidadChange(item.id, e.target.value)}
                          className="form-input input-sm"
                          min="0"
                          max={item.cantidad_solicitada}
                          step="0.01"
                        />
                      </td>
                    )}
                    {requisicion.estado !== 'BORRADOR' && requisicion.estado !== 'ENVIADA' && (
                      <>
                        <td>
                          <strong>{item.cantidad_autorizada || 0}</strong> {item.producto_detalle.unidad_medida}
                        </td>
                        <td>
                          <span className={getDiferenciaClass(item.diferencia)}>
                            {item.diferencia > 0 ? '+' : ''}{item.diferencia || 0}
                          </span>
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {(requisicion.estado === 'ENVIADA' && isFarmaciaAdmin) && (
          <div className="comentario-section">
            <label className="form-label">Comentario de autorización:</label>
            <textarea
              value={comentario}
              onChange={(e) => setComentario(e.target.value)}
              className="form-textarea"
              rows="3"
              placeholder="Ingrese observaciones..."
            />
          </div>
        )}
      </div>
    </div>
  );
};

const getEstadoBadge = (estado) => {
  const badges = {
    BORRADOR: 'badge-secondary',
    ENVIADA: 'badge-info',
    AUTORIZADA: 'badge-success',
    RECHAZADA: 'badge-danger',
    SURTIDA: 'badge-success',
    CANCELADA: 'badge-danger'
  };
  return badges[estado] || 'badge-secondary';
};

const getDiferenciaClass = (diferencia) => {
  if (!diferencia) return '';
  if (diferencia < 0) return 'diferencia-negativa';
  if (diferencia > 0) return 'diferencia-positiva';
  return '';
};

export default RequisicionDetalle;






