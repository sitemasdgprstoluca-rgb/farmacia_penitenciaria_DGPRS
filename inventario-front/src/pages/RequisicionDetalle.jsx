import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { requisicionesAPI, hojasRecoleccionAPI, descargarArchivo } from '../services/api';
import { usePermissions } from '../hooks/usePermissions';
import { toast } from 'react-hot-toast';
import {
  FaArrowLeft,
  FaPaperPlane,
  FaCheck,
  FaTimes,
  FaBoxOpen,
  FaBan,
  FaDownload,
  FaClipboardList,
  FaUser,
  FaBuilding,
  FaCalendar,
  FaInfoCircle,
  FaShieldAlt,
  FaPrint,
  FaFileSignature,
  FaFileDownload,
  FaCheckCircle,
  FaEdit,
} from 'react-icons/fa';
import { COLORS } from '../constants/theme';

const RequisicionDetalle = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { permisos, user } = usePermissions();
  
  const [requisicion, setRequisicion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [procesando, setProcesando] = useState(false);
  
  // Hoja de recolección
  const [hojaRecoleccion, setHojaRecoleccion] = useState(null);
  // eslint-disable-next-line no-unused-vars
  const [loadingHoja, setLoadingHoja] = useState(false);
  
  // Para autorización con cantidades editables
  const [modoAutorizar, setModoAutorizar] = useState(false);
  const [detallesEditables, setDetallesEditables] = useState([]);

  const cargarRequisicion = useCallback(async () => {
    try {
      setLoading(true);
      const response = await requisicionesAPI.getById(id);
      const data = response.data?.requisicion || response.data;
      setRequisicion(data);
      
      // Inicializar detalles editables para autorización
      const detalles = data.detalles || [];
      setDetallesEditables(detalles.map(d => ({
        ...d,
        cantidad_autorizada: d.cantidad_autorizada || d.cantidad_solicitada
      })));
      
      // Cargar hoja de recolección si existe
      if (['autorizada', 'parcial', 'surtida'].includes(data.estado)) {
        cargarHojaRecoleccion();
      }
    } catch (error) {
      console.error('Error cargando requisición:', error);
      toast.error('No se pudo cargar la requisición');
      navigate('/requisiciones');
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, navigate]);

  const cargarHojaRecoleccion = async () => {
    try {
      setLoadingHoja(true);
      const response = await hojasRecoleccionAPI.porRequisicion(id);
      if (response.data?.existe) {
        setHojaRecoleccion(response.data.hoja);
      }
    } catch (error) {
      console.error('Error cargando hoja:', error);
    } finally {
      setLoadingHoja(false);
    }
  };

  useEffect(() => {
    if (id) cargarRequisicion();
  }, [id, cargarRequisicion]);

  const getEstadoBadge = (estado) => {
    const badges = {
      borrador: 'bg-gray-200 text-gray-700',
      enviada: 'bg-amber-100 text-amber-700',  // Pendiente - más visible
      autorizada: 'bg-green-100 text-green-700',
      parcial: 'bg-yellow-100 text-yellow-700',
      surtida: 'bg-purple-100 text-purple-700',
      recibida: 'bg-blue-100 text-blue-700',
      rechazada: 'bg-red-100 text-red-600',
      cancelada: 'bg-gray-100 text-gray-600',
    };
    return badges[estado] || 'bg-gray-100 text-gray-800';
  };

  // Labels amigables para los estados
  const getEstadoLabel = (estado) => {
    const labels = {
      borrador: 'BORRADOR',
      enviada: 'PENDIENTE',
      autorizada: 'ACEPTADA',
      parcial: 'PARCIAL',
      rechazada: 'RECHAZADA',
      surtida: 'SURTIDA',
      cancelada: 'CANCELADA',
    };
    return labels[estado] || estado?.toUpperCase();
  };

  const formatFecha = (fecha) => {
    if (!fecha) return 'N/A';
    return new Date(fecha).toLocaleDateString('es-MX', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleEnviar = async () => {
    if (!window.confirm('¿Enviar esta requisición para autorización?')) return;
    try {
      setProcesando(true);
      await requisicionesAPI.enviar(id);
      toast.success('Requisición enviada');
      cargarRequisicion();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al enviar');
    } finally {
      setProcesando(false);
    }
  };

  const iniciarAutorizacion = () => {
    setModoAutorizar(true);
  };

  const cancelarAutorizacion = () => {
    setModoAutorizar(false);
    // Resetear cantidades
    const detalles = requisicion.detalles || [];
    setDetallesEditables(detalles.map(d => ({
      ...d,
      cantidad_autorizada: d.cantidad_autorizada || d.cantidad_solicitada
    })));
  };

  const actualizarCantidadAutorizada = (idx, valor) => {
    // Limitar al máximo entre stock disponible y cantidad solicitada
    const maxCantidad = Math.min(
      detallesEditables[idx].stock_disponible || 9999,
      detallesEditables[idx].cantidad_solicitada
    );
    const cantidad = Math.max(0, Math.min(Number(valor) || 0, maxCantidad));
    setDetallesEditables(prev => {
      const nuevo = [...prev];
      nuevo[idx] = { ...nuevo[idx], cantidad_autorizada: cantidad };
      return nuevo;
    });
  };

  const confirmarAutorizacion = async () => {
    // Validar que al menos un item tenga cantidad > 0
    const totalAutorizado = detallesEditables.reduce((sum, d) => sum + (d.cantidad_autorizada || 0), 0);
    if (totalAutorizado === 0) {
      toast.error('Debe autorizar al menos un producto con cantidad mayor a 0');
      return;
    }
    
    // Verificar si es autorización parcial (algún item con cantidad_autorizada < cantidad_solicitada)
    const esParcial = detallesEditables.some(d => 
      (d.cantidad_autorizada || 0) < (d.cantidad_solicitada || 0)
    );
    
    let observaciones = '';
    if (esParcial) {
      observaciones = prompt(
        'Esta es una autorización PARCIAL.\n\n' +
        'Por favor, indique el motivo de la reducción de cantidades:\n' +
        '(Mínimo 10 caracteres)'
      );
      
      if (observaciones === null) return; // Usuario canceló
      
      const obsTrimmed = (observaciones || '').trim();
      if (obsTrimmed.length < 10) {
        toast.error('Para autorizaciones parciales, debe indicar el motivo (mínimo 10 caracteres)');
        return;
      }
      observaciones = obsTrimmed;
    } else {
      // Confirmación simple para autorización total
      if (!window.confirm('¿Confirmar la autorización TOTAL de esta requisición?')) {
        return;
      }
    }
    
    try {
      setProcesando(true);
      const items = detallesEditables.map(d => ({
        id: d.id,
        cantidad_autorizada: d.cantidad_autorizada
      }));
      await requisicionesAPI.autorizar(id, { items, observaciones });
      toast.success(esParcial ? 'Requisición autorizada parcialmente' : 'Requisición autorizada');
      setModoAutorizar(false);
      cargarRequisicion();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al autorizar');
    } finally {
      setProcesando(false);
    }
  };

  const handleRechazar = async () => {
    const motivo = prompt(
      `Motivo del rechazo para ${requisicion?.folio || 'esta requisición'}:\n` +
      '(Mínimo 10 caracteres)'
    );
    
    // Validar que se ingresó un motivo
    if (motivo === null) return; // Usuario canceló
    
    const motivoTrimmed = (motivo || '').trim();
    if (motivoTrimmed.length < 10) {
      toast.error('El motivo de rechazo debe tener al menos 10 caracteres');
      return;
    }
    
    try {
      setProcesando(true);
      await requisicionesAPI.rechazar(id, { observaciones: motivoTrimmed });
      toast.success('Requisición rechazada');
      cargarRequisicion();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al rechazar');
    } finally {
      setProcesando(false);
    }
  };

  const handleSurtir = async () => {
    if (!window.confirm('¿Marcar esta requisición como surtida? Se descontará el inventario automáticamente.')) return;
    try {
      setProcesando(true);
      await requisicionesAPI.surtir(id);
      toast.success('Requisición surtida - Inventario actualizado');
      cargarRequisicion();
    } catch (error) {
      const errorMsg = error.response?.data?.error || 'Error al surtir';
      const detalles = error.response?.data?.detalles;
      if (detalles && Array.isArray(detalles)) {
        const mensaje = detalles.map(d => `${d.producto}: Requiere ${d.requerido}, Disponible: ${d.disponible}`).join('\n');
        toast.error(`${errorMsg}\n${mensaje}`, { duration: 6000 });
      } else {
        toast.error(errorMsg);
      }
    } finally {
      setProcesando(false);
    }
  };

  const handleCancelar = async () => {
    const motivo = prompt(
      `Motivo de cancelación para ${requisicion?.folio || 'esta requisición'}:\n` +
      '(Obligatorio para auditoría - mínimo 5 caracteres)'
    );
    
    // Validar que se ingresó un motivo
    if (motivo === null) return; // Usuario canceló
    
    const motivoTrimmed = (motivo || '').trim();
    if (motivoTrimmed.length < 5) {
      toast.error('Debe ingresar un motivo de cancelación (mínimo 5 caracteres)');
      return;
    }
    
    try {
      setProcesando(true);
      await requisicionesAPI.cancelar(id, { observaciones: motivoTrimmed });
      toast.success('Requisición cancelada');
      cargarRequisicion();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al cancelar');
    } finally {
      setProcesando(false);
    }
  };

  const handleMarcarRecibida = async () => {
    // Verificar que el usuario pertenece al centro de la requisición
    const centroRequisicion = requisicion?.centro?.id || requisicion?.centro;
    const centroUsuario = user?.centro?.id || user?.centro;
    const esPrivilegiado = user?.is_superuser || permisos?.isFarmaciaAdmin || permisos?.isAdmin;
    
    if (!esPrivilegiado && centroUsuario && centroRequisicion && centroUsuario !== centroRequisicion) {
      toast.error('Solo puede marcar como recibida las requisiciones de su centro');
      return;
    }
    
    // Confirmar antes de proceder
    if (!window.confirm(
      `¿Confirmar recepción de la requisición ${requisicion?.folio || id}?\n\n` +
      'Esta acción indica que los medicamentos fueron entregados físicamente.'
    )) {
      return;
    }
    
    const lugar = prompt('Lugar de entrega/recepción:');
    if (!lugar || !lugar.trim()) {
      toast.error('El lugar de entrega es requerido');
      return;
    }
    const observaciones = prompt('Observaciones de recepción (opcional):') || '';
    
    try {
      setProcesando(true);
      await requisicionesAPI.marcarRecibida(id, { 
        lugar_entrega: lugar.trim(), 
        observaciones_recepcion: observaciones.trim() 
      });
      toast.success('Requisición marcada como recibida');
      cargarRequisicion();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al marcar como recibida');
    } finally {
      setProcesando(false);
    }
  };

  const handleDescargarPDF = async (tipo) => {
    try {
      setProcesando(true);
      let response;
      let nombreArchivo;

      if (tipo === 'aceptacion' && hojaRecoleccion) {
        // Usar la API de hojas de recolección con seguridad
        response = await hojasRecoleccionAPI.descargarPDF(hojaRecoleccion.id);
        nombreArchivo = `Hoja_Recoleccion_${hojaRecoleccion.folio_hoja}.pdf`;
        // Registrar impresión
        try {
          await hojasRecoleccionAPI.registrarImpresion(hojaRecoleccion.id);
        } catch (e) {
          console.warn('No se pudo registrar impresión:', e);
        }
      } else if (tipo === 'aceptacion') {
        // Fallback a la API antigua
        response = await requisicionesAPI.downloadPDFAceptacion(id);
        nombreArchivo = `Hoja_Recoleccion_${requisicion.folio}.pdf`;
      } else {
        response = await requisicionesAPI.downloadPDFRechazo(id);
        nombreArchivo = `requisicion_rechazada_${requisicion.folio}.pdf`;
      }

      const blob = new Blob([response.data], { type: 'application/pdf' });
      descargarArchivo(blob, nombreArchivo);
      toast.success('PDF descargado');
      
      // Recargar hoja para actualizar contadores
      if (tipo === 'aceptacion') {
        cargarHojaRecoleccion();
      }
    } catch (error) {
      toast.error('Error al descargar PDF');
    } finally {
      setProcesando(false);
    }
  };

  // Verificar integridad de la hoja (farmacia)
  const handleVerificarIntegridad = async () => {
    if (!hojaRecoleccion) return;
    try {
      setProcesando(true);
      const response = await hojasRecoleccionAPI.verificarIntegridad(hojaRecoleccion.id);
      if (response.data.es_valido) {
        toast.success('✓ Integridad verificada: El documento no ha sido alterado');
      } else {
        toast.error('⚠ ALERTA: El contenido puede haber sido alterado');
      }
    } catch (error) {
      toast.error('Error al verificar integridad');
    } finally {
      setProcesando(false);
    }
  };

  // Marcar hoja como verificada por farmacia
  // eslint-disable-next-line no-unused-vars
  const handleMarcarVerificada = async () => {
    if (!hojaRecoleccion) return;
    if (!window.confirm('¿Confirmar que la hoja impresa por el centro coincide con lo autorizado?')) return;
    try {
      setProcesando(true);
      await hojasRecoleccionAPI.verificar(hojaRecoleccion.id);
      toast.success('Hoja marcada como verificada');
      cargarHojaRecoleccion();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al verificar hoja');
    } finally {
      setProcesando(false);
    }
  };

  // Detectar si es Farmacia/Admin
  const rolUsuario = (user?.rol || '').toLowerCase();
  const esFarmacia = 
    user?.is_superuser || 
    permisos?.isFarmaciaAdmin || 
    permisos?.isAdmin ||
    permisos?.isSuperuser ||
    rolUsuario === 'admin_sistema' ||
    rolUsuario === 'superusuario' ||
    rolUsuario === 'farmacia' ||
    rolUsuario === 'admin_farmacia';
  
  const puedeEnviar = requisicion?.estado === 'borrador';
  const puedeAutorizar = requisicion?.estado === 'enviada' && esFarmacia;
  const puedeRechazar = requisicion?.estado === 'enviada' && esFarmacia;
  const puedeSurtir = (requisicion?.estado === 'autorizada' || requisicion?.estado === 'parcial') && esFarmacia;
  const puedeMarcarRecibida = requisicion?.estado === 'surtida' && 
    (user?.is_superuser || (user?.centro && requisicion?.centro === user.centro));
  const puedeCancelar = !['surtida', 'cancelada', 'rechazada', 'recibida'].includes(requisicion?.estado);
  const puedeDescargarHoja = ['autorizada', 'parcial', 'surtida', 'recibida'].includes(requisicion?.estado);
  const puedeDescargarRechazo = requisicion?.estado === 'rechazada';
  // eslint-disable-next-line no-unused-vars
  const puedeVerificarHoja = esFarmacia && hojaRecoleccion && hojaRecoleccion.estado !== 'verificada';

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-gray-300" style={{ borderTopColor: COLORS.vino }}></div>
      </div>
    );
  }

  if (!requisicion) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No se encontró la requisición</p>
        <button
          onClick={() => navigate('/requisiciones')}
          className="mt-4 px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
        >
          Volver
        </button>
      </div>
    );
  }

  const detalles = modoAutorizar ? detallesEditables : (requisicion.detalles || []);

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={() => navigate('/requisiciones')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
        >
          <FaArrowLeft /> Volver a requisiciones
        </button>
      </div>

      {/* Información General */}
      <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <FaClipboardList className="text-2xl" style={{ color: COLORS.vino }} />
              <h1 className="text-2xl font-bold" style={{ color: COLORS.vino }}>
                {requisicion.folio}
              </h1>
            </div>
            <span className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${getEstadoBadge(requisicion.estado)}`}>
              {getEstadoLabel(requisicion.estado)}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="flex items-start gap-3">
            <FaBuilding className="text-gray-400 mt-1" />
            <div>
              <p className="text-sm text-gray-500">Centro</p>
              <p className="font-semibold">{requisicion.centro_nombre || requisicion.centro?.nombre || 'N/A'}</p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <FaUser className="text-gray-400 mt-1" />
            <div>
              <p className="text-sm text-gray-500">Solicitante</p>
              <p className="font-semibold">{requisicion.usuario_solicita_nombre || requisicion.usuario_solicita?.username || 'N/A'}</p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <FaCalendar className="text-gray-400 mt-1" />
            <div>
              <p className="text-sm text-gray-500">Fecha Solicitud</p>
              <p className="font-semibold">{formatFecha(requisicion.fecha_solicitud)}</p>
            </div>
          </div>

          {requisicion.usuario_autoriza_nombre && (
            <div className="flex items-start gap-3">
              <FaCheck className="text-green-500 mt-1" />
              <div>
                <p className="text-sm text-gray-500">Autorizado por</p>
                <p className="font-semibold">{requisicion.usuario_autoriza_nombre}</p>
                <p className="text-xs text-gray-400">{formatFecha(requisicion.fecha_autorizacion)}</p>
              </div>
            </div>
          )}
        </div>

        {requisicion.observaciones && (
          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2 text-gray-600 mb-1">
              <FaInfoCircle />
              <span className="text-sm font-semibold">Observaciones</span>
            </div>
            <p className="text-gray-700">{requisicion.observaciones}</p>
          </div>
        )}

        {requisicion.motivo_rechazo && (
          <div className="mt-4 p-3 bg-red-50 rounded-lg border border-red-200">
            <div className="flex items-center gap-2 text-red-600 mb-1">
              <FaTimes />
              <span className="text-sm font-semibold">Motivo de Rechazo</span>
            </div>
            <p className="text-red-700">{requisicion.motivo_rechazo}</p>
          </div>
        )}
      </div>

      {/* Banner de acción para requisiciones pendientes - SOLO FARMACIA/ADMIN */}
      {puedeAutorizar && !modoAutorizar && (
        <div className="bg-gray-50 border border-gray-300 rounded-xl p-4 mb-6 shadow">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg" style={{ backgroundColor: `${COLORS.vino}15` }}>
                <FaClipboardList className="text-xl" style={{ color: COLORS.vino }} />
              </div>
              <div>
                <h3 className="font-bold text-gray-800">Requisición Pendiente de Revisión</h3>
                <p className="text-sm text-gray-600">
                  Revisa las cantidades solicitadas, ajusta según el inventario y acepta o rechaza.
                </p>
              </div>
            </div>
            <button
              onClick={iniciarAutorizacion}
              disabled={procesando}
              className="flex items-center gap-2 px-5 py-3 text-white rounded-lg disabled:opacity-50 font-semibold hover:opacity-90 transition-opacity"
              style={{ backgroundColor: COLORS.vino }}
            >
              <FaEdit /> Revisar Cantidades
            </button>
          </div>
        </div>
      )}

      {/* Tabla de Productos */}
      <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold" style={{ color: COLORS.vino }}>
            Productos Solicitados ({detalles.length})
          </h2>
          {modoAutorizar && (
            <span className="px-3 py-1 border rounded-full text-sm font-semibold" 
              style={{ borderColor: COLORS.vino, color: COLORS.vino }}>
              Modo Edición
            </span>
          )}
        </div>

        {detalles.length === 0 ? (
          <p className="text-center text-gray-500 py-8">No hay productos en esta requisición</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b-2" style={{ borderColor: COLORS.vino }}>
                  <th className="px-3 py-3 text-left text-sm font-semibold text-gray-700">Clave</th>
                  <th className="px-3 py-3 text-left text-sm font-semibold text-gray-700">Producto</th>
                  <th className="px-3 py-3 text-center text-sm font-semibold text-gray-700">Lote</th>
                  <th className="px-3 py-3 text-center text-sm font-semibold text-gray-700">Unidad</th>
                  <th className="px-3 py-3 text-center text-sm font-semibold text-gray-700">Solicitado</th>
                  <th className={`px-3 py-3 text-center text-sm font-semibold ${modoAutorizar ? 'bg-gray-100' : 'text-gray-700'}`}
                    style={{ color: modoAutorizar ? COLORS.vino : undefined }}>
                    Autorizado
                  </th>
                  <th className="px-3 py-3 text-center text-sm font-semibold text-gray-700">Surtido</th>
                  {esFarmacia && (
                    <th className="px-3 py-3 text-center text-sm font-semibold text-gray-700">Stock Lote</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {detalles.map((detalle, idx) => (
                  <tr key={detalle.id || idx} className="border-b border-gray-200 hover:bg-gray-50">
                    <td className="px-3 py-3 text-sm font-mono text-gray-800">
                      {detalle.producto_clave || detalle.producto?.clave || '-'}
                    </td>
                    <td className="px-3 py-3 text-sm text-gray-800">
                      {detalle.producto_descripcion || detalle.producto?.descripcion || detalle.descripcion || '-'}
                    </td>
                    <td className="px-3 py-3 text-center">
                      {detalle.lote_numero ? (
                        <div className="text-sm">
                          <span className="font-mono font-semibold text-gray-800">{detalle.lote_numero}</span>
                          {detalle.lote_caducidad && (
                            <div className="text-xs text-gray-500">Cad: {detalle.lote_caducidad}</div>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-400 text-sm">-</span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-sm text-center text-gray-600">
                      {detalle.producto_unidad || detalle.producto?.unidad_medida || '-'}
                    </td>
                    <td className="px-3 py-3 text-center font-semibold text-gray-800">
                      {detalle.cantidad_solicitada}
                    </td>
                    <td className={`px-3 py-3 text-center ${modoAutorizar ? 'bg-gray-50' : ''}`}>
                      {modoAutorizar ? (
                        <input
                          type="number"
                          min="0"
                          max={detalle.lote_stock || detalle.stock_disponible || detalle.cantidad_solicitada}
                          value={detalle.cantidad_autorizada || 0}
                          onChange={(e) => actualizarCantidadAutorizada(idx, e.target.value)}
                          className="w-20 px-2 py-1 border border-gray-300 rounded text-center font-semibold focus:ring-2 focus:outline-none"
                          style={{ '--tw-ring-color': COLORS.vino }}
                        />
                      ) : (
                        <span className={detalle.cantidad_autorizada > 0 ? 'font-semibold text-gray-800' : 'text-gray-400'}>
                          {detalle.cantidad_autorizada ?? '-'}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-center">
                      <span className={detalle.cantidad_surtida > 0 ? 'font-semibold text-gray-800' : 'text-gray-400'}>
                        {detalle.cantidad_surtida ?? '-'}
                      </span>
                    </td>
                    {esFarmacia && (
                      <td className="px-3 py-3 text-center">
                        <span className={`font-semibold ${
                          (detalle.lote_stock || detalle.stock_disponible || 0) < detalle.cantidad_solicitada 
                            ? 'text-red-600' 
                            : 'text-gray-800'
                        }`}>
                          {detalle.lote_stock ?? detalle.stock_disponible ?? '-'}
                        </span>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Resumen de totales */}
        <div className="mt-4 pt-4 border-t grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-sm text-gray-500">Total Solicitado</p>
            <p className="text-xl font-bold text-gray-800">
              {detalles.reduce((sum, d) => sum + (d.cantidad_solicitada || 0), 0)}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Total Autorizado</p>
            <p className="text-xl font-bold text-gray-800">
              {detalles.reduce((sum, d) => sum + (d.cantidad_autorizada || 0), 0)}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Total Surtido</p>
            <p className="text-xl font-bold text-gray-800">
              {detalles.reduce((sum, d) => sum + (d.cantidad_surtida || 0), 0)}
            </p>
          </div>
        </div>
      </div>

      {/* Hoja de Recolección - Solo visible para requisiciones autorizadas/surtidas/finalizadas */}
      {hojaRecoleccion && (
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6 border-l-4 border-blue-500">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold flex items-center gap-2" style={{ color: COLORS.vino }}>
              <FaFileSignature className="text-blue-500" />
              Hoja de Recolección
            </h2>
            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
              hojaRecoleccion.estado === 'pendiente' ? 'bg-yellow-100 text-yellow-800' :
              hojaRecoleccion.estado === 'impresa' ? 'bg-blue-100 text-blue-800' :
              hojaRecoleccion.estado === 'verificada' ? 'bg-green-100 text-green-800' :
              hojaRecoleccion.estado === 'usada' ? 'bg-gray-100 text-gray-800' :
              'bg-gray-100 text-gray-600'
            }`}>
              {hojaRecoleccion.estado_display || hojaRecoleccion.estado?.toUpperCase()}
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <p className="text-sm text-gray-500">Folio</p>
              <p className="font-mono font-bold">{hojaRecoleccion.folio_hoja}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Generada</p>
              <p className="font-semibold">{formatFecha(hojaRecoleccion.fecha_generacion)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Descargas</p>
              <p className="font-semibold flex items-center gap-1">
                <FaPrint className="text-gray-400" />
                {hojaRecoleccion.veces_descargada || 0}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Hash de Seguridad</p>
              <p className="font-mono text-xs text-gray-600 truncate" title={hojaRecoleccion.hash_contenido}>
                {hojaRecoleccion.hash_contenido?.substring(0, 16)}...
              </p>
            </div>
          </div>

          {/* Verificación de Integridad - Solo para Farmacia */}
          {user?.rol === 'farmacia' && (
            <div className="bg-gray-50 rounded-lg p-4 mt-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FaShieldAlt className="text-blue-500 text-xl" />
                  <div>
                    <p className="font-semibold text-gray-700">Verificación de Integridad</p>
                    <p className="text-xs text-gray-500">
                      Comprueba que la hoja no ha sido alterada después de su generación
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleVerificarIntegridad}
                  disabled={procesando}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  <FaShieldAlt />
                  {procesando ? 'Verificando...' : 'Verificar Integridad'}
                </button>
              </div>
            </div>
          )}

          {/* Botón de descarga */}
          <div className="mt-4 flex justify-end">
            <button
              onClick={() => handleDescargarPDF('aceptacion')}
              disabled={procesando}
              className="flex items-center gap-2 px-4 py-2 text-white rounded-lg disabled:opacity-50 hover:opacity-90 transition-opacity"
              style={{ backgroundColor: COLORS.vino }}
            >
              <FaFileDownload />
              Descargar PDF de Recolección
            </button>
          </div>
        </div>
      )}

      {/* Acciones */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h2 className="text-lg font-bold mb-4" style={{ color: COLORS.vino }}>Acciones</h2>
        
        <div className="flex flex-wrap gap-3">
          {modoAutorizar ? (
            <>
              <button
                onClick={confirmarAutorizacion}
                disabled={procesando}
                className="flex items-center gap-2 px-4 py-2 text-white rounded-lg disabled:opacity-50 hover:opacity-90 transition-opacity"
                style={{ backgroundColor: '#16a34a' }}
              >
                <FaCheck /> Aceptar Requisición
              </button>
              <button
                onClick={cancelarAutorizacion}
                disabled={procesando}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                <FaTimes /> Cancelar Edición
              </button>
            </>
          ) : (
            <>
              {puedeEnviar && (
                <button
                  onClick={handleEnviar}
                  disabled={procesando}
                  className="flex items-center gap-2 px-4 py-2 text-white rounded-lg disabled:opacity-50 hover:opacity-90 transition-opacity"
                  style={{ backgroundColor: COLORS.vino }}
                >
                  <FaPaperPlane /> Enviar para autorización
                </button>
              )}

              {puedeAutorizar && (
                <button
                  onClick={iniciarAutorizacion}
                  disabled={procesando}
                  className="flex items-center gap-2 px-4 py-2 text-white rounded-lg disabled:opacity-50 font-semibold hover:opacity-90 transition-opacity"
                  style={{ backgroundColor: COLORS.vino }}
                >
                  <FaEdit /> Revisar Cantidades
                </button>
              )}

              {puedeRechazar && (
                <button
                  onClick={handleRechazar}
                  disabled={procesando}
                  className="flex items-center gap-2 px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50 transition-colors"
                >
                  <FaTimes /> Rechazar
                </button>
              )}

              {puedeSurtir && (
                <button
                  onClick={handleSurtir}
                  disabled={procesando}
                  className="flex items-center gap-2 px-4 py-2 text-white rounded-lg disabled:opacity-50 hover:opacity-90 transition-opacity"
                  style={{ backgroundColor: COLORS.vino }}
                >
                  <FaBoxOpen /> Surtir y descontar inventario
                </button>
              )}

              {puedeMarcarRecibida && (
                <button
                  onClick={handleMarcarRecibida}
                  disabled={procesando}
                  className="flex items-center gap-2 px-4 py-2 text-white rounded-lg disabled:opacity-50 hover:opacity-90 transition-opacity bg-blue-600 hover:bg-blue-700"
                >
                  <FaCheckCircle /> Confirmar recepción
                </button>
              )}

              {puedeDescargarHoja && (
                <button
                  onClick={() => handleDescargarPDF('aceptacion')}
                  disabled={procesando}
                  className="flex items-center gap-2 px-4 py-2 border text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
                  style={{ borderColor: COLORS.vino, color: COLORS.vino }}
                >
                  <FaDownload /> Hoja de recolección
                </button>
              )}

              {puedeDescargarRechazo && (
                <button
                  onClick={() => handleDescargarPDF('rechazo')}
                  disabled={procesando}
                  className="flex items-center gap-2 px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50 transition-colors"
                >
                  <FaDownload /> PDF de rechazo
                </button>
              )}

              {puedeCancelar && (
                <button
                  onClick={handleCancelar}
                  disabled={procesando}
                  className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
                >
                  <FaBan /> Cancelar requisición
                </button>
              )}
            </>
          )}
        </div>

        {procesando && (
          <div className="mt-4 flex items-center gap-2 text-gray-500">
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-300 border-t-gray-600"></div>
            Procesando...
          </div>
        )}
      </div>
    </div>
  );
};

export default RequisicionDetalle;






