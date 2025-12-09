import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { requisicionesAPI, hojasRecoleccionAPI, descargarArchivo } from '../services/api';
import { usePermissions } from '../hooks/usePermissions';
import { getEstadoBadgeClasses, getEstadoLabel } from '../components/EstadoBadge';
import RequisicionHistorial from '../components/RequisicionHistorial';
import { toast } from 'react-hot-toast';
import InputModal from '../components/InputModal';
import ConfirmModal from '../components/ConfirmModal';
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
  FaHistory,
} from 'react-icons/fa';
import { COLORS } from '../constants/theme';

const RequisicionDetalle = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { permisos, user } = usePermissions();
  
  const [requisicion, setRequisicion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [procesando, setProcesando] = useState(false);
  
  // Modal para confirmar recepción
  // eslint-disable-next-line no-unused-vars
  const [showRecepcionModal, setShowRecepcionModal] = useState(false);
  const [recepcionData, setRecepcionData] = useState({ lugar: '', observaciones: '' });
  const [showConfirmRecepcion, setShowConfirmRecepcion] = useState(false);
  
  // Modales para acciones con validación de permisos
  const [showEnviarModal, setShowEnviarModal] = useState(false);
  const [showAutorizarModal, setShowAutorizarModal] = useState(false);
  const [showAutorizarParcialModal, setShowAutorizarParcialModal] = useState(false);
  // eslint-disable-next-line no-unused-vars
  const [autorizarObservaciones, setAutorizarObservaciones] = useState('');
  const [showRechazarModal, setShowRechazarModal] = useState(false);
  const [showCancelarModal, setShowCancelarModal] = useState(false);
  const [showSurtirModal, setShowSurtirModal] = useState(false);
  
  // Hoja de recolección
  const [hojaRecoleccion, setHojaRecoleccion] = useState(null);
  // eslint-disable-next-line no-unused-vars
  const [loadingHoja, setLoadingHoja] = useState(false);
  
  // FLUJO V2: Historial de estados
  const [showHistorial, setShowHistorial] = useState(false);
  
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
        cantidad_autorizada: d.cantidad_autorizada || d.cantidad_solicitada,
        motivo_ajuste: d.motivo_ajuste || ''  // MEJORA FLUJO 3: Inicializar motivo_ajuste
      })));
      
      // Cargar hoja de recolección si existe
      // ISS-DB-002: Estados que permiten ver hoja de recolección
      if (['autorizada', 'en_surtido', 'parcial', 'surtida'].includes(data.estado)) {
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

  // FLUJO V2: Usa helpers compartidos para colores de badge y labels
  const getEstadoBadge = (estado) => getEstadoBadgeClasses(estado);

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

  // Iniciar envío con validación de permisos
  const iniciarEnviar = () => {
    if (!permisos?.enviarRequisicion) {
      toast.error('No tienes permisos para enviar requisiciones');
      return;
    }
    setShowEnviarModal(true);
  };

  const handleEnviar = async () => {
    // Doble validación de permisos (defensa en profundidad)
    if (!permisos?.enviarRequisicion) {
      toast.error('No tienes permisos para enviar requisiciones');
      setShowEnviarModal(false);
      return;
    }
    try {
      setProcesando(true);
      setShowEnviarModal(false);
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
    // Validación interna de permisos (no depender solo del renderizado condicional)
    if (!permisos?.autorizarRequisicion) {
      toast.error('No tienes permisos para autorizar requisiciones');
      return;
    }
    setModoAutorizar(true);
  };

  const cancelarAutorizacion = () => {
    setModoAutorizar(false);
    // Resetear cantidades y motivos
    const detalles = requisicion.detalles || [];
    setDetallesEditables(detalles.map(d => ({
      ...d,
      cantidad_autorizada: d.cantidad_autorizada || d.cantidad_solicitada,
      motivo_ajuste: d.motivo_ajuste || ''  // MEJORA FLUJO 3
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

  // MEJORA FLUJO 3: Función para actualizar motivo_ajuste por item
  const actualizarMotivoAjuste = (idx, motivo) => {
    setDetallesEditables(prev => {
      const nuevo = [...prev];
      nuevo[idx] = { ...nuevo[idx], motivo_ajuste: motivo };
      return nuevo;
    });
  };

  const confirmarAutorizacion = async () => {
    // Doble validación de permisos (defensa en profundidad)
    if (!permisos?.autorizarRequisicion) {
      toast.error('No tienes permisos para autorizar requisiciones');
      return;
    }
    
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
    
    if (esParcial) {
      // Mostrar modal para ingresar observaciones de autorización parcial
      setAutorizarObservaciones('');
      setShowAutorizarParcialModal(true);
    } else {
      // Mostrar modal de confirmación para autorización total
      setShowAutorizarModal(true);
    }
  };
  
  // Ejecutar autorización total
  const ejecutarAutorizacionTotal = async () => {
    try {
      setProcesando(true);
      setShowAutorizarModal(false);
      // MEJORA FLUJO 3: Incluir motivo_ajuste por cada item
      const items = detallesEditables.map(d => ({
        id: d.id,
        cantidad_autorizada: d.cantidad_autorizada,
        motivo_ajuste: d.cantidad_autorizada < d.cantidad_solicitada ? d.motivo_ajuste : null
      }));
      await requisicionesAPI.autorizar(id, { items, observaciones: '' });
      toast.success('Requisición autorizada');
      setModoAutorizar(false);
      cargarRequisicion();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al autorizar');
    } finally {
      setProcesando(false);
    }
  };
  
  // Ejecutar autorización parcial con observaciones
  const ejecutarAutorizacionParcial = async () => {
    // MEJORA FLUJO 3: Validar que todos los items con cantidad reducida tengan motivo
    const itemsSinMotivo = detallesEditables.filter(d => 
      d.cantidad_autorizada < d.cantidad_solicitada && (!d.motivo_ajuste || d.motivo_ajuste.trim().length < 10)
    );
    
    if (itemsSinMotivo.length > 0) {
      toast.error(`Debe indicar el motivo del ajuste (mín. 10 caracteres) para: ${itemsSinMotivo.map(i => i.producto_clave || i.producto?.clave).join(', ')}`);
      return;
    }
    
    try {
      setProcesando(true);
      setShowAutorizarParcialModal(false);
      // MEJORA FLUJO 3: Incluir motivo_ajuste por cada item
      const items = detallesEditables.map(d => ({
        id: d.id,
        cantidad_autorizada: d.cantidad_autorizada,
        motivo_ajuste: d.cantidad_autorizada < d.cantidad_solicitada ? d.motivo_ajuste : null
      }));
      await requisicionesAPI.autorizar(id, { items });
      toast.success('Requisición autorizada parcialmente');
      setModoAutorizar(false);
      cargarRequisicion();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al autorizar');
    } finally {
      setProcesando(false);
    }
  };

  // Iniciar rechazo con validación de permisos
  const iniciarRechazar = () => {
    if (!permisos?.rechazarRequisicion) {
      toast.error('No tienes permisos para rechazar requisiciones');
      return;
    }
    setShowRechazarModal(true);
  };

  // Ejecutar rechazo con motivo del modal
  const ejecutarRechazar = async (motivo) => {
    // Doble validación de permisos (defensa en profundidad)
    if (!permisos?.rechazarRequisicion) {
      toast.error('No tienes permisos para rechazar requisiciones');
      setShowRechazarModal(false);
      return;
    }
    
    const motivoTrimmed = (motivo || '').trim();
    if (motivoTrimmed.length < 10) {
      toast.error('El motivo de rechazo debe tener al menos 10 caracteres');
      return;
    }
    
    try {
      setProcesando(true);
      setShowRechazarModal(false);
      await requisicionesAPI.rechazar(id, { observaciones: motivoTrimmed });
      toast.success('Requisición rechazada');
      cargarRequisicion();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al rechazar');
    } finally {
      setProcesando(false);
    }
  };

  // Iniciar surtido con validación de permisos
  const iniciarSurtir = () => {
    if (!permisos?.surtirRequisicion) {
      toast.error('No tienes permisos para surtir requisiciones');
      return;
    }
    setShowSurtirModal(true);
  };

  // Ejecutar surtido después de confirmación en modal
  const ejecutarSurtir = async () => {
    // Doble validación de permisos (defensa en profundidad)
    if (!permisos?.surtirRequisicion) {
      toast.error('No tienes permisos para surtir requisiciones');
      setShowSurtirModal(false);
      return;
    }
    
    setShowSurtirModal(false);
    
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

  // Iniciar cancelación con validación de permisos
  const iniciarCancelar = () => {
    if (!permisos?.cancelarRequisicion) {
      toast.error('No tienes permisos para cancelar requisiciones');
      return;
    }
    setShowCancelarModal(true);
  };

  // Ejecutar cancelación después de confirmación en modal
  const ejecutarCancelar = async (motivo) => {
    // Doble validación de permisos (defensa en profundidad)
    if (!permisos?.cancelarRequisicion) {
      toast.error('No tienes permisos para cancelar requisiciones');
      setShowCancelarModal(false);
      return;
    }
    
    const motivoTrimmed = (motivo || '').trim();
    if (motivoTrimmed.length < 5) {
      toast.error('Debe ingresar un motivo de cancelación (mínimo 5 caracteres)');
      return;
    }
    
    setShowCancelarModal(false);
    
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

  // Iniciar flujo de confirmación de recepción con modal
  const iniciarConfirmarRecepcion = () => {
    // Validación interna de permisos (no depender solo del renderizado)
    if (!permisos?.confirmarRecepcion) {
      toast.error('No tienes permisos para confirmar recepción');
      return;
    }
    
    const centroRequisicion = requisicion?.centro?.id || requisicion?.centro;
    const centroUsuario = user?.centro?.id || user?.centro;
    const esPrivilegiado = user?.is_superuser || permisos?.isFarmaciaAdmin || permisos?.isAdmin;
    
    if (!esPrivilegiado && centroUsuario && centroRequisicion && String(centroUsuario) !== String(centroRequisicion)) {
      toast.error('Solo puede marcar como recibida las requisiciones de su centro');
      return;
    }
    
    setRecepcionData({ lugar: '', observaciones: '' });
    setShowConfirmRecepcion(true);
  };

  // Ejecutar confirmación de recepción
  const ejecutarConfirmarRecepcion = async () => {
    if (!recepcionData.lugar.trim()) {
      toast.error('El lugar de entrega es requerido');
      return;
    }
    
    try {
      setProcesando(true);
      setShowConfirmRecepcion(false);
      await requisicionesAPI.marcarRecibida(id, { 
        lugar_entrega: recepcionData.lugar.trim(), 
        observaciones_recepcion: recepcionData.observaciones.trim() 
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
    // Validar permisos y acceso por centro antes de descargar
    if (!permisos?.descargarHojaRecoleccion) {
      toast.error('No tienes permisos para descargar documentos');
      return;
    }
    if (!tieneAccesoPorCentro) {
      toast.error('No tienes acceso a documentos de este centro');
      return;
    }
    
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
  
  // Calcular acceso por centro ANTES de usarlo en permisos
  // Usuarios de centro solo pueden operar sobre requisiciones de su propio centro
  // Admin/Farmacia pueden operar sobre cualquier requisición
  const centroRequisicion = requisicion?.centro?.id || requisicion?.centro;
  const centroUsuario = user?.centro?.id || user?.centro;
  const esMismoCentro = centroUsuario && centroRequisicion && String(centroUsuario) === String(centroRequisicion);
  const tieneAccesoPorCentro = esFarmacia || user?.is_superuser || esMismoCentro;
  
  // Enviar: usuarios de centro solo pueden enviar borradores de su centro
  const puedeEnviar = requisicion?.estado === 'borrador' && 
    permisos?.enviarRequisicion && 
    tieneAccesoPorCentro;
    
  // Validar AMBOS: rol de farmacia Y permiso fino correspondiente
  // ISS-DB-002: Estados alineados con BD Supabase
  const puedeAutorizar = requisicion?.estado === 'enviada' && esFarmacia && permisos?.autorizarRequisicion;
  const puedeRechazar = requisicion?.estado === 'enviada' && esFarmacia && permisos?.rechazarRequisicion;
  const puedeSurtir = (requisicion?.estado === 'autorizada' || requisicion?.estado === 'parcial') && esFarmacia && permisos?.surtirRequisicion;
  
  // puedeMarcarRecibida: estado surtida + (superuser O del mismo centro) + tener permiso específico confirmarRecepcion
  // Se valida tanto el centro como el permiso fino para evitar acciones no autorizadas
  const puedeMarcarRecibida = requisicion?.estado === 'surtida' && 
    tieneAccesoPorCentro &&
    permisos?.confirmarRecepcion === true; // Debe tener permiso específico de confirmar recepción
  
  // Cancelar: validar centro para usuarios no privilegiados
  // ISS-DB-002: Estados terminales
  const puedeCancelar = !['surtida', 'cancelada', 'rechazada', 'entregada'].includes(requisicion?.estado) && 
    permisos?.cancelarRequisicion &&
    tieneAccesoPorCentro; // Usuarios de centro solo pueden cancelar las suyas
    
  // Descargas: validar centro para usuarios no privilegiados (aislamiento de datos)
  // ISS-DB-002: Estados que permiten descarga
  const puedeDescargarHoja = ['autorizada', 'en_surtido', 'parcial', 'surtida', 'entregada'].includes(requisicion?.estado) && 
    permisos?.descargarHojaRecoleccion &&
    tieneAccesoPorCentro; // Usuarios de centro solo descargan hojas de su centro
    
  const puedeDescargarRechazo = requisicion?.estado === 'rechazada' && 
    permisos?.descargarHojaRecoleccion &&
    tieneAccesoPorCentro; // Usuarios de centro solo descargan rechazos de su centro
    
  // eslint-disable-next-line no-unused-vars
  const puedeVerificarHoja = esFarmacia && hojaRecoleccion && hojaRecoleccion.estado !== 'verificada';

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-t-transparent spinner-institucional"></div>
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
              <FaClipboardList className="text-2xl text-theme-primary" />
              <h1 className="text-2xl font-bold text-theme-primary">
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
              <div className="p-2 rounded-lg bg-theme-primary/10">
                <FaClipboardList className="text-xl text-theme-primary" />
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
              className="flex items-center gap-2 px-5 py-3 text-white rounded-lg disabled:opacity-50 font-semibold hover:opacity-90 transition-opacity bg-theme-primary"
            >
              <FaEdit /> Revisar Cantidades
            </button>
          </div>
        </div>
      )}

      {/* Tabla de Productos */}
      <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-theme-primary">
            Productos Solicitados ({detalles.length})
          </h2>
          {modoAutorizar && (
            <span className="px-3 py-1 border rounded-full text-sm font-semibold border-theme-primary text-theme-primary">
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
                <tr className="border-b-2 border-theme-primary">
                  <th className="px-3 py-3 text-left text-sm font-semibold text-gray-700">Clave</th>
                  <th className="px-3 py-3 text-left text-sm font-semibold text-gray-700">Producto</th>
                  <th className="px-3 py-3 text-center text-sm font-semibold text-gray-700">Lote</th>
                  <th className="px-3 py-3 text-center text-sm font-semibold text-gray-700">Unidad</th>
                  <th className="px-3 py-3 text-center text-sm font-semibold text-gray-700">Solicitado</th>
                  <th className={`px-3 py-3 text-center text-sm font-semibold ${modoAutorizar ? 'bg-gray-100 text-theme-primary' : 'text-gray-700'}`}>
                    Autorizado
                  </th>
                  {/* MEJORA FLUJO 3: Columna para motivo de ajuste */}
                  {modoAutorizar && (
                    <th className="px-3 py-3 text-left text-sm font-semibold bg-amber-50 text-amber-700 min-w-[200px]">
                      Motivo Ajuste
                    </th>
                  )}
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
                      {detalle.producto_nombre || detalle.producto?.nombre || detalle.nombre || '-'}
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
                          className="w-20 px-2 py-1 border border-gray-300 rounded text-center font-semibold focus:ring-2 focus:outline-none ring-theme-primary focus:ring-theme-primary"
                        />
                      ) : (
                        <span className={detalle.cantidad_autorizada > 0 ? 'font-semibold text-gray-800' : 'text-gray-400'}>
                          {detalle.cantidad_autorizada ?? '-'}
                        </span>
                      )}
                    </td>
                    {/* MEJORA FLUJO 3: Input de motivo de ajuste cuando se reduce cantidad */}
                    {modoAutorizar && (
                      <td className="px-3 py-3 bg-amber-50">
                        {detalle.cantidad_autorizada < detalle.cantidad_solicitada ? (
                          <input
                            type="text"
                            placeholder="Motivo del ajuste (mín. 10 chars)..."
                            value={detalle.motivo_ajuste || ''}
                            onChange={(e) => actualizarMotivoAjuste(idx, e.target.value)}
                            className={`w-full px-2 py-1 text-sm border rounded focus:ring-2 focus:outline-none ${
                              detalle.motivo_ajuste && detalle.motivo_ajuste.length >= 10
                                ? 'border-green-300 ring-green-200'
                                : 'border-amber-300 ring-amber-200'
                            }`}
                          />
                        ) : (
                          <span className="text-gray-400 text-sm italic">-</span>
                        )}
                      </td>
                    )}
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
            <h2 className="text-lg font-bold flex items-center gap-2 text-theme-primary">
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

          {/* Botón de descarga - Solo si tiene permiso y acceso por centro */}
          {puedeDescargarHoja && (
            <div className="mt-4 flex justify-end">
              <button
                onClick={() => handleDescargarPDF('aceptacion')}
                disabled={procesando}
                className="flex items-center gap-2 px-4 py-2 text-white rounded-lg disabled:opacity-50 hover:opacity-90 transition-opacity bg-theme-primary"
              >
                <FaFileDownload />
                Descargar PDF de Recolección
              </button>
            </div>
          )}
        </div>
      )}

      {/* FLUJO V2: Historial de Estados */}
      <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold flex items-center gap-2 text-theme-primary">
            <FaHistory className="text-gray-500" />
            Historial de Estados
          </h2>
          <button
            onClick={() => setShowHistorial(!showHistorial)}
            className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
          >
            {showHistorial ? 'Ocultar' : 'Mostrar'} historial
          </button>
        </div>
        
        {showHistorial && (
          <RequisicionHistorial 
            requisicionId={requisicion.id}
            isModal={false}
          />
        )}
        
        {!showHistorial && (
          <p className="text-gray-500 text-sm italic">
            Haz clic en "Mostrar historial" para ver todos los cambios de estado de esta requisición.
          </p>
        )}
      </div>

      {/* Acciones */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h2 className="text-lg font-bold mb-4 text-theme-primary">Acciones</h2>
        
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
                  onClick={iniciarEnviar}
                  disabled={procesando}
                  className="flex items-center gap-2 px-4 py-2 text-white rounded-lg disabled:opacity-50 hover:opacity-90 transition-opacity bg-theme-primary"
                >
                  <FaPaperPlane /> Enviar para autorización
                </button>
              )}

              {puedeAutorizar && (
                <button
                  onClick={iniciarAutorizacion}
                  disabled={procesando}
                  className="flex items-center gap-2 px-4 py-2 text-white rounded-lg disabled:opacity-50 font-semibold hover:opacity-90 transition-opacity bg-theme-primary"
                >
                  <FaEdit /> Revisar Cantidades
                </button>
              )}

              {puedeRechazar && (
                <button
                  onClick={iniciarRechazar}
                  disabled={procesando}
                  className="flex items-center gap-2 px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50 transition-colors"
                >
                  <FaTimes /> Rechazar
                </button>
              )}

              {puedeSurtir && (
                <button
                  onClick={iniciarSurtir}
                  disabled={procesando}
                  className="flex items-center gap-2 px-4 py-2 text-white rounded-lg disabled:opacity-50 hover:opacity-90 transition-opacity bg-theme-primary"
                >
                  <FaBoxOpen /> Surtir y descontar inventario
                </button>
              )}

              {puedeMarcarRecibida && (
                <button
                  onClick={iniciarConfirmarRecepcion}
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
                  className="flex items-center gap-2 px-4 py-2 border text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors border-theme-primary text-theme-primary"
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
                  onClick={iniciarCancelar}
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
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-t-transparent spinner-institucional"></div>
            Procesando...
          </div>
        )}
      </div>

      {/* Modal de confirmación para enviar */}
      <ConfirmModal
        open={showEnviarModal}
        onCancel={() => setShowEnviarModal(false)}
        onConfirm={handleEnviar}
        title="Enviar requisición"
        message={`¿Confirma que desea enviar la requisición ${requisicion?.folio || ''} para autorización?`}
        confirmText="Enviar"
        cancelText="Cancelar"
        tone="info"
      />

      {/* Modal de confirmación para autorización total */}
      <ConfirmModal
        open={showAutorizarModal}
        onCancel={() => setShowAutorizarModal(false)}
        onConfirm={ejecutarAutorizacionTotal}
        title="Autorizar requisición"
        message={`¿Confirma que desea autorizar COMPLETAMENTE la requisición ${requisicion?.folio || ''}? Se aprobarán todas las cantidades solicitadas.`}
        confirmText="Autorizar"
        cancelText="Cancelar"
        tone="info"
      />

      {/* Modal de confirmación para autorización parcial */}
      {/* MEJORA FLUJO 3: El motivo ahora se captura por item en la tabla */}
      <ConfirmModal
        open={showAutorizarParcialModal}
        onCancel={() => setShowAutorizarParcialModal(false)}
        onConfirm={ejecutarAutorizacionParcial}
        title="Confirmar autorización parcial"
        message="Ha reducido las cantidades de algunos productos. Verifique que ha indicado el motivo de cada ajuste en la columna correspondiente."
        confirmText="Confirmar Autorización"
        cancelText="Revisar"
        tone="warning"
      />

      {/* Modal de input para rechazar */}
      <InputModal
        open={showRechazarModal}
        onCancel={() => setShowRechazarModal(false)}
        onConfirm={ejecutarRechazar}
        title="Rechazar requisición"
        message="Ingrese el motivo del rechazo (obligatorio para auditoría)"
        placeholder="Motivo del rechazo (mínimo 10 caracteres)"
        minLength={10}
        confirmText="Rechazar"
        cancelText="Cancelar"
        tone="danger"
      />

      {/* Modal de confirmación para surtir */}
      <ConfirmModal
        open={showSurtirModal}
        onCancel={() => setShowSurtirModal(false)}
        onConfirm={ejecutarSurtir}
        title="Surtir requisición"
        message={`¿Marcar la requisición ${requisicion?.folio || ''} como surtida? Se descontará el inventario automáticamente.`}
        confirmText="Surtir"
        cancelText="Cancelar"
        tone="info"
      />

      {/* Modal de input para cancelar */}
      <InputModal
        open={showCancelarModal}
        onCancel={() => setShowCancelarModal(false)}
        onConfirm={ejecutarCancelar}
        title="Cancelar requisición"
        message="Ingrese el motivo de cancelación (obligatorio para auditoría)"
        placeholder="Motivo de cancelación (mínimo 5 caracteres)"
        minLength={5}
        confirmText="Cancelar requisición"
        cancelText="Volver"
        tone="danger"
      />

      {/* Modal de confirmación de recepción */}
      {showConfirmRecepcion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => !procesando && setShowConfirmRecepcion(false)} />
          <div className="relative w-full max-w-md bg-white rounded-lg shadow-xl p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <FaCheckCircle className="text-blue-600" />
              Confirmar recepción - {requisicion?.folio}
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Esta acción indica que los medicamentos fueron entregados físicamente.
            </p>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Lugar de entrega/recepción <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={recepcionData.lugar}
                  onChange={(e) => setRecepcionData(prev => ({ ...prev, lugar: e.target.value }))}
                  placeholder="Ej: Almacén central, Farmacia del centro..."
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  disabled={procesando}
                  autoFocus
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">
                  Observaciones (opcional)
                </label>
                <textarea
                  value={recepcionData.observaciones}
                  onChange={(e) => setRecepcionData(prev => ({ ...prev, observaciones: e.target.value }))}
                  placeholder="Observaciones adicionales..."
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  rows={3}
                  disabled={procesando}
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowConfirmRecepcion(false)}
                disabled={procesando}
                className="px-4 py-2 border rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                onClick={ejecutarConfirmarRecepcion}
                disabled={procesando || !recepcionData.lugar.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
              >
                {procesando ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                    Procesando...
                  </>
                ) : (
                  <>
                    <FaCheckCircle /> Confirmar recepción
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RequisicionDetalle;






