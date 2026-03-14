import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { requisicionesAPI, hojasRecoleccionAPI, descargarArchivo, lotesAPI } from '../services/api';
import { usePermissions } from '../hooks/usePermissions';
import { useConfirmation } from '../hooks/useConfirmation';
import { useSafeAction } from '../hooks/useSafeAction';
import { useRealtimeSync } from '../hooks/useRealtimeSync';
import { getEstadoBadgeClasses, getEstadoLabel } from '../components/EstadoBadge';
import RequisicionHistorial from '../components/RequisicionHistorial';
import { RequisicionAcciones } from '../components/RequisicionAcciones';
import { toast } from 'react-hot-toast';
import InputModal from '../components/InputModal';
import ConfirmModal from '../components/ConfirmModal';
import TwoStepConfirmModal from '../components/TwoStepConfirmModal';
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
  FaExclamationTriangle,
  FaPlus,
  FaTrash,
  FaSearch,
  FaSave,
  FaMinus,
  FaUserShield,
} from 'react-icons/fa';
import { COLORS } from '../constants/theme';

const RequisicionDetalle = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { permisos, user } = usePermissions();
  
  const [requisicion, setRequisicion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [procesando, setProcesando] = useState(false);
  
  // Modales para acciones con validación de permisos
  const [showEnviarModal, setShowEnviarModal] = useState(false);
  const [showAutorizarModal, setShowAutorizarModal] = useState(false);
  const [showAutorizarParcialModal, setShowAutorizarParcialModal] = useState(false);
  // eslint-disable-next-line no-unused-vars
  const [autorizarObservaciones, setAutorizarObservaciones] = useState('');
  const [showRechazarModal, setShowRechazarModal] = useState(false);
  const [showCancelarModal, setShowCancelarModal] = useState(false);
  const [showSurtirModal, setShowSurtirModal] = useState(false);
  // ISS-FIX: Modal para fecha de recolección
  const [showFechaRecoleccionModal, setShowFechaRecoleccionModal] = useState(false);
  const [fechaRecoleccion, setFechaRecoleccion] = useState('');
  const [esParcialPendiente, setEsParcialPendiente] = useState(false);
  
  // ISS-SEC: Hook de confirmación en 2 pasos
  const {
    confirmState,
    requestDeleteConfirmation,
    executeWithConfirmation,
    cancelConfirmation
  } = useConfirmation();
  
  // Hoja de recolección
  const [hojaRecoleccion, setHojaRecoleccion] = useState(null);
  // eslint-disable-next-line no-unused-vars
  const [loadingHoja, setLoadingHoja] = useState(false);
  
  // FLUJO V2: Historial de estados
  const [showHistorial, setShowHistorial] = useState(false);
  
  // Para autorización con cantidades editables
  const [modoAutorizar, setModoAutorizar] = useState(false);
  const [detallesEditables, setDetallesEditables] = useState([]);

  // MODO EDICIÓN DE PRODUCTOS (para médico cuando devuelta/borrador)
  const [modoEdicionProductos, setModoEdicionProductos] = useState(false);
  const [productosEditables, setProductosEditables] = useState([]);
  const [catalogoLotes, setCatalogoLotes] = useState([]);
  const [loadingCatalogo, setLoadingCatalogo] = useState(false);
  const [catalogoBusqueda, setCatalogoBusqueda] = useState('');
  const [showAgregarProducto, setShowAgregarProducto] = useState(false);
  const [guardandoCambios, setGuardandoCambios] = useState(false);
  const { getRequestId: getDetalleRequestId, resetRequestId: resetDetalleRequestId } = useSafeAction();
  
  // Refs para búsqueda con debounce y cancelación
  const searchTimeoutRef = useRef(null);
  const abortControllerRef = useRef(null);
  // ISS-FIX: Ref para guardar observaciones inmediatamente (evitar problemas de async state)
  const observacionesParcialRef = useRef('');

  // Detectar si viene en modo editar desde URL
  const modoEditarURL = searchParams.get('modo') === 'editar';

  // ISS-SEGURIDAD: Determinar si es Admin/Farmacia para mostrar información sensible
  const rolActualGlobal = (user?.rol_efectivo || user?.rol || '').toLowerCase();
  const esAdminOFarmacia = user?.is_superuser || 
    ['admin', 'admin_farmacia', 'admin_sistema', 'superusuario', 'farmacia'].includes(rolActualGlobal);

  // ISS-SEC FIX: Calcular flags de rol fuera del callback para incluirlas en deps
  const esFarmaciaRol = user?.is_superuser || 
    ['farmacia', 'admin_farmacia', 'admin_sistema', 'superusuario'].includes(rolActualGlobal);
  const esCentroRol = ['medico', 'centro', 'usuario_centro'].includes(rolActualGlobal);

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
        // FIX: Usar ?? en lugar de || para preservar 0 como valor válido
        cantidad_autorizada: d.cantidad_autorizada ?? d.cantidad_solicitada,
        motivo_ajuste: d.motivo_ajuste || ''  // MEJORA FLUJO 3: Inicializar motivo_ajuste
      })));
      
      // Cargar hoja de recolección si existe
      // ISS-DB-002: Estados que permiten ver hoja de recolección
      // ISS-HOJA-V2: Médico puede ver hoja en 'autorizada' para llevarla a firmar
      // Después de surtida, centro ve versión simplificada con sello
      // ISS-SEC FIX: Usar flags de rol calculadas fuera del callback para evitar stale closure
      
      // Farmacia: siempre puede ver hoja en estos estados
      // Centro: puede ver hoja en 'autorizada' (para firmas) y 'surtida' (consulta con sello)
      const estadosHojaFarmacia = ['autorizada', 'en_surtido', 'parcial', 'surtida', 'entregada'];
      const estadosHojaCentro = ['autorizada', 'surtida', 'entregada'];
      
      if ((esFarmaciaRol && estadosHojaFarmacia.includes(data.estado)) ||
          (esCentroRol && estadosHojaCentro.includes(data.estado))) {
        cargarHojaRecoleccion();
      }
    } catch (error) {
      console.error('Error cargando requisición:', error);
      toast.error('No se pudo cargar la requisición');
      navigate('/requisiciones');
    } finally {
      setLoading(false);
    }
  // ISS-SEC FIX: Incluir flags de rol en deps para recargar cuando user cambie
  }, [id, navigate, esFarmaciaRol, esCentroRol]);

  // ── Sincronización multi-usuario en tiempo real ──────────────────────────
  // Cuando otra sesión cambia el estado de CUALQUIER requisición,
  // esta página recarga los datos de la requisición actual.
  // El refetch es barato y el DRF aplica permisos normales.
  useRealtimeSync('requisicion', cargarRequisicion, { debounceMs: 600 });

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

  // Detectar modo edición desde URL y activar cuando requisición carga
  // SEGURIDAD: Validar permisos Y que sea el solicitante antes de activar modo edición
  useEffect(() => {
    if (modoEditarURL && requisicion && ['borrador', 'devuelta'].includes(requisicion.estado)) {
      // Verificar permiso antes de activar modo edición
      if (!permisos?.editarRequisicion) {
        toast.error('No tienes permisos para editar requisiciones');
        searchParams.delete('modo');
        setSearchParams(searchParams);
        return;
      }
      // ISS-FIX: Verificar que sea el solicitante original o superuser
      const _solId = requisicion?.solicitante_id ||
                     requisicion?.solicitante?.id ||
                     (typeof requisicion?.solicitante === 'number' ? requisicion.solicitante : null);
      const _esSol = _solId && user?.id && String(_solId) === String(user?.id);
      if (!_esSol && !user?.is_superuser) {
        // No es el solicitante, no activar edición y limpiar URL
        searchParams.delete('modo');
        setSearchParams(searchParams);
        return;
      }
      iniciarEdicionProductos();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modoEditarURL, requisicion?.id, requisicion?.estado, permisos?.editarRequisicion, user?.id]);

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
    // ISS-OWNERSHIP: Solo el receptor puede entrar en modo autorización
    if (otroGestiona) {
      toast.error(`Solo ${receptorNombre || 'el receptor'} puede autorizar esta requisición`);
      return;
    }
    // Reinicializar cantidades clampeadas al stock disponible.
    // Si stock < solicitada → se autoriza el stock máximo (requiere motivo_ajuste).
    // Si stock >= solicitada → se autoriza la cantidad solicitada completa.
    // Si ya existe cantidad_autorizada guardada → se respeta.
    const detallesBase = requisicion?.detalles || [];
    setDetallesEditables(detallesBase.map(d => {
      const stockDisponible = d.stock_disponible ?? d.lote_stock ?? 0;
      const cantidadSolicitada = d.cantidad_solicitada || 0;
      const yaAutorizada = d.cantidad_autorizada !== null && d.cantidad_autorizada !== undefined;
      const cantidadInicial = yaAutorizada
        ? d.cantidad_autorizada
        : (stockDisponible > 0 && stockDisponible < cantidadSolicitada
            ? stockDisponible
            : cantidadSolicitada);
      return {
        ...d,
        cantidad_autorizada: cantidadInicial,
        motivo_ajuste: d.motivo_ajuste || '',
      };
    }));
    setModoAutorizar(true);
  };

  const cancelarAutorizacion = () => {
    setModoAutorizar(false);
    // Resetear cantidades y motivos
    const detalles = requisicion.detalles || [];
    setDetallesEditables(detalles.map(d => ({
      ...d,
      // FIX: Usar ?? en lugar de || para preservar 0 como valor válido
      cantidad_autorizada: d.cantidad_autorizada ?? d.cantidad_solicitada,
      motivo_ajuste: d.motivo_ajuste || ''  // MEJORA FLUJO 3
    })));
  };

  const actualizarCantidadAutorizada = (idx, valor) => {
    const detalle = detallesEditables[idx];
    const stockDisponible = detalle.stock_disponible ?? detalle.lote_stock ?? 0;
    const cantidadSolicitada = detalle.cantidad_solicitada || 0;
    
    // ⚠️ VALIDACIÓN CRÍTICA: No permitir más de lo disponible en stock
    const maxCantidad = Math.min(stockDisponible, cantidadSolicitada);
    const cantidadIngresada = Number(valor) || 0;
    const cantidad = Math.max(0, Math.min(cantidadIngresada, maxCantidad));
    
    // Mostrar warning si intenta exceder el stock
    if (cantidadIngresada > stockDisponible) {
      toast.error(
        `No puede autorizar más de lo disponible en stock (${stockDisponible} unidades)`
      );
    }
    
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
    
    // ⚠️ AVISO informativo: items que podrían exceder stock
    // No se bloquea aquí — el backend valida el stock real en Supabase.
    // El frontend puede tener datos de stock incompletos (lotes sin centro=NULL,
    // columna activo aún no migrada, etc.). El backend rechaza con error claro.
    const itemsExcedenStock = detallesEditables.filter(d => {
      const stockDisponible = d.stock_disponible ?? d.lote_stock ?? 0;
      // Solo avisar cuando tenemos dato de stock confiable (> 0)
      if (!stockDisponible) return false;
      return (d.cantidad_autorizada || 0) > stockDisponible;
    });

    if (itemsExcedenStock.length > 0) {
      const listaProd = itemsExcedenStock.map(d => {
        const stock = d.stock_disponible ?? d.lote_stock ?? 0;
        return `• ${d.producto_nombre || d.producto_clave}: autorizas ${d.cantidad_autorizada}, stock visible ${stock}`;
      }).join('\n');
      // Solo advertencia — continúa al modal de confirmación
      toast(`⚠️ Aviso de stock:\n${listaProd}\n\nEl sistema verificará el stock real al confirmar.`,
        { duration: 6000, icon: '⚠️' });
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
  
  // Ejecutar autorización total - ahora solo muestra modal de fecha
  const ejecutarAutorizacionTotal = async () => {
    setShowAutorizarModal(false);
    setEsParcialPendiente(false);
    // ISS-FIX: Mostrar modal para pedir fecha de recolección
    setFechaRecoleccion('');
    setShowFechaRecoleccionModal(true);
  };
  
  // Ejecutar autorización parcial con observaciones
  const ejecutarAutorizacionParcial = async (observacionesParam) => {
    // MEJORA FLUJO 3: Validar que todos los items con cantidad reducida tengan motivo
    const itemsSinMotivo = detallesEditables.filter(d => 
      d.cantidad_autorizada < d.cantidad_solicitada && (!d.motivo_ajuste || d.motivo_ajuste.trim().length < 10)
    );
    
    if (itemsSinMotivo.length > 0) {
      toast.error(`Debe indicar el motivo del ajuste (mín. 10 caracteres) para: ${itemsSinMotivo.map(i => i.producto_clave || i.producto?.clave).join(', ')}`);
      return;
    }
    
    // ISS-FIX: Guardar observaciones en ref (inmediato, sin esperar setState)
    observacionesParcialRef.current = observacionesParam || '';
    setAutorizarObservaciones(observacionesParam || '');
    setShowAutorizarParcialModal(false);
    setEsParcialPendiente(true);
    // ISS-FIX: Mostrar modal para pedir fecha de recolección
    setFechaRecoleccion('');
    setShowFechaRecoleccionModal(true);
  };
  
  // ISS-FIX: Ejecutar autorización con fecha de recolección
  const ejecutarAutorizacionConFecha = async () => {
    if (!fechaRecoleccion) {
      toast.error('Debe seleccionar una fecha límite de recolección');
      return;
    }
    
    try {
      setProcesando(true);
      setShowFechaRecoleccionModal(false);
      
      // Preparar items con cantidades autorizadas
      const items = detallesEditables.map(d => ({
        id: d.id,
        cantidad_autorizada: d.cantidad_autorizada,
        motivo_ajuste: d.cantidad_autorizada < d.cantidad_solicitada ? d.motivo_ajuste : null
      }));
      
      // ISS-FIX: Usar ref para obtener observaciones (más confiable que estado async)
      const observacionesParaEnviar = observacionesParcialRef.current || autorizarObservaciones || '';
      
      // Usar endpoint correcto: autorizarFarmacia con fecha
      // Asegurar formato con segundos para compatibilidad con Django parse_datetime
      const fechaConSegundos = fechaRecoleccion.length === 16 ? fechaRecoleccion + ':00' : fechaRecoleccion;
      await requisicionesAPI.autorizarFarmacia(id, {
        items,
        fecha_recoleccion_limite: fechaConSegundos,
        observaciones: observacionesParaEnviar
      });
      
      // Limpiar ref después de usar
      observacionesParcialRef.current = '';
      
      toast.success(esParcialPendiente ? 'Requisición autorizada parcialmente' : 'Requisición autorizada');
      setModoAutorizar(false);
      cargarRequisicion();
    } catch (error) {
      console.error('Error al autorizar requisición:', error.response?.data);
      const status = error.response?.status;
      const errorData = error.response?.data;

      if (status === 403) {
        // Ownership check: el backend indica quién es el receptor
        const msg = errorData?.error || 'No tienes permiso para autorizar esta requisición';
        toast.error(msg, { duration: 7000 });
        // Recargar para reflejar el nombre del receptor en el banner
        cargarRequisicion();
      } else if (status === 400 || status === 409) {
        // Stock insuficiente u otro error de validación
        if (errorData?.detalles_stock && Array.isArray(errorData.detalles_stock)) {
          const lineas = errorData.detalles_stock.map(d =>
            `• ${d.producto || d.producto_clave || 'Producto'}: disponible ${d.disponible ?? d.stock_disponible ?? '?'}, requerido ${d.requerido ?? d.cantidad_autorizada ?? d.cantidad_solicitada ?? '?'}`
          ).join('\n');
          toast.error(`❌ ${errorData.error || 'Stock insuficiente'}\n\n${lineas}`, { duration: 10000 });
        } else if (errorData?.stock_disponible !== undefined || errorData?.detalle) {
          toast.error(`❌ ${errorData.error}\n\n${errorData.detalle || ''}`, { duration: 8000 });
        } else {
          toast.error(errorData?.error || errorData?.mensaje || 'Error al validar stock disponible');
        }
      } else {
        toast.error(errorData?.error || 'Error al autorizar');
      }
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
      toast.success('✅ Requisición surtida y entregada - Inventario actualizado');
      cargarRequisicion();
    } catch (error) {
      const errorMsg = error.response?.data?.error || 'Error al surtir';
      const detalles = error.response?.data?.detalles_stock || error.response?.data?.detalles;
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

  // Ejecutar confirmación de recepción directamente (sin modal)
  const iniciarConfirmarRecepcion = async () => {
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
    
    // Ejecutar directamente sin mostrar modal
    try {
      setProcesando(true);
      
      // ISS-FIX: Lugar de entrega automático = Centro solicitante
      const nombreCentro = requisicion?.centro?.nombre || requisicion?.centro_nombre || 'Centro Penitenciario';
      
      await requisicionesAPI.marcarRecibida(id, { 
        lugar_entrega: nombreCentro, 
        observaciones_recepcion: '' 
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

      if (tipo === 'aceptacion') {
        const estadoActual = (requisicion?.estado || '').toLowerCase().trim();
        
        // REQUISICIONES SURTIDAS/ENTREGADAS: SIEMPRE usar Recibo de Salida
        if (['surtida', 'parcial', 'entregada', 'recibida'].includes(estadoActual)) {
          response = await requisicionesAPI.downloadReciboSalida(id);
          nombreArchivo = `Recibo_Salida_${requisicion.folio}.pdf`;
          toast.success('Recibo de Salida descargado');
        } 
        // AUTORIZADAS: usar hoja de recolección
        else if (hojaRecoleccion) {
          response = await hojasRecoleccionAPI.descargarPDF(hojaRecoleccion.id);
          nombreArchivo = `Hoja_Recoleccion_${hojaRecoleccion.folio_hoja}.pdf`;
          try {
            await hojasRecoleccionAPI.registrarImpresion(hojaRecoleccion.id);
          } catch (e) {
            console.warn('No se pudo registrar impresión:', e);
          }
        } else {
          response = await requisicionesAPI.downloadPDFAceptacion(id);
          nombreArchivo = `Hoja_Recoleccion_${requisicion.folio}.pdf`;
        }
      } else {
        response = await requisicionesAPI.downloadPDFRechazo(id);
        nombreArchivo = `requisicion_rechazada_${requisicion.folio}.pdf`;
      }

      const blob = new Blob([response.data], { type: 'application/pdf' });
      descargarArchivo(blob, nombreArchivo);
      
      if (tipo === 'aceptacion' && hojaRecoleccion) {
        cargarHojaRecoleccion();
      }
    } catch (error) {
      toast.error('Error al descargar PDF');
    } finally {
      setProcesando(false);
    }
  };

  // Función para descargar Recibo de Salida (documento oficial de entrega)
  const handleDescargarReciboSalida = async () => {
    if (!['surtida', 'parcial', 'entregada'].includes(requisicion?.estado)) {
      toast.error('El recibo de salida solo está disponible para requisiciones surtidas/entregadas');
      return;
    }
    
    try {
      setProcesando(true);
      const response = await requisicionesAPI.downloadReciboSalida(id);
      const blob = new Blob([response.data], { type: 'application/pdf' });
      descargarArchivo(blob, `Recibo_Salida_${requisicion.folio}.pdf`);
      toast.success('Recibo de salida descargado correctamente');
    } catch (error) {
      console.error('Error al descargar recibo de salida:', error);
      toast.error('Error al descargar recibo de salida');
    } finally {
      setProcesando(false);
    }
  };

  // ============ FUNCIONES PARA MODO EDICIÓN DE PRODUCTOS ============
  
  // Buscar lotes en servidor con término de búsqueda
  const buscarLotesServidor = useCallback(async (termino = '') => {
    // Cancelar petición anterior si existe
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    
    setLoadingCatalogo(true);
    try {
      const params = {
        stock_min: 1,
        solo_disponibles: 'true',
        ordering: 'producto__nombre,fecha_caducidad',
        page_size: 500,
        para_requisicion: 'true',  // Asegurar que es string 'true' para el backend
        activo: 'true',
        centro: 'central',  // Forzar búsqueda en almacén central
      };
      
      // Agregar término de búsqueda si existe
      if (termino.trim()) {
        params.search = termino.trim();
      }
      
      const response = await lotesAPI.getAll(params, { 
        signal: abortControllerRef.current.signal 
      });
      const lotes = response.data?.results || response.data || [];
      
      // Filtrar solo lotes con stock > 0 (por si el backend no filtra correctamente)
      const lotesConStock = lotes.filter(l => (l.cantidad_actual || 0) > 0);
      console.log('Lotes cargados:', lotesConStock.length, 'de', lotes.length, 'Búsqueda:', termino);
      setCatalogoLotes(lotesConStock);
    } catch (error) {
      // Ignorar errores de cancelación
      if (error.name === 'CanceledError' || error.name === 'AbortError' || error.code === 'ERR_CANCELED') {
        return;
      }
      console.error('Error cargando catálogo:', error);
      toast.error('No se pudo cargar el catálogo de productos');
    } finally {
      setLoadingCatalogo(false);
    }
  }, []);
  
  // Cargar catálogo inicial
  const cargarCatalogoLotes = useCallback(async () => {
    await buscarLotesServidor('');
  }, [buscarLotesServidor]);
  
  // Handler de búsqueda con debounce
  const handleCatalogoBusquedaChange = useCallback((valor) => {
    setCatalogoBusqueda(valor);
    
    // Cancelar timeout anterior
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    
    // Debounce de 300ms
    searchTimeoutRef.current = setTimeout(() => {
      buscarLotesServidor(valor);
    }, 300);
  }, [buscarLotesServidor]);
  
  // Cleanup al desmontar
  useEffect(() => {
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Iniciar modo edición
  const iniciarEdicionProductos = () => {
    // SEGURIDAD: Validar permisos antes de permitir edición
    if (!permisos?.editarRequisicion) {
      toast.error('No tienes permisos para editar requisiciones');
      return;
    }

    if (!requisicion || !['borrador', 'devuelta'].includes(requisicion.estado)) {
      toast.error('Solo se puede editar en estado borrador o devuelta');
      return;
    }

    // ISS-FIX: Solo el solicitante original (o superuser) puede editar
    const _solId = requisicion?.solicitante_id ||
                   requisicion?.solicitante?.id ||
                   (typeof requisicion?.solicitante === 'number' ? requisicion.solicitante : null);
    const _esSol = _solId && user?.id && String(_solId) === String(user?.id);
    if (!_esSol && !user?.is_superuser) {
      toast.error('Solo el médico solicitante puede editar esta requisición');
      return;
    }
    
    // Copiar detalles a productosEditables
    const detalles = requisicion.detalles || [];
    console.log('Detalles de requisición:', detalles);
    
    setProductosEditables(detalles.map(d => {
      // El serializer devuelve 'producto' como ID directo, o como objeto {id, nombre, clave}
      const productoId = typeof d.producto === 'object' ? d.producto?.id : d.producto;
      const loteId = typeof d.lote === 'object' ? d.lote?.id : d.lote;
      
      return {
        id: d.id,
        lote_id: loteId || d.lote_id,
        producto_id: productoId || d.producto_id,
        producto_clave: d.producto?.clave || d.producto_clave,
        producto_nombre: d.producto?.nombre || d.producto_nombre || d.producto_descripcion,
        numero_lote: d.lote?.numero_lote || d.lote_numero,
        cantidad_solicitada: d.cantidad_solicitada,
        stock_disponible: d.stock_disponible ?? d.lote?.cantidad_actual ?? d.lote_stock ?? 0,
        esNuevo: false
      };
    }));
    
    setModoEdicionProductos(true);
    cargarCatalogoLotes();
  };

  // Cancelar edición de productos
  const cancelarEdicionProductos = () => {
    setModoEdicionProductos(false);
    setProductosEditables([]);
    setShowAgregarProducto(false);
    setCatalogoBusqueda('');
    // Limpiar parámetro de URL
    searchParams.delete('modo');
    setSearchParams(searchParams);
  };

  // Actualizar cantidad de un producto
  const actualizarCantidadProducto = (idx, valor) => {
    const cantidad = Math.max(1, Number(valor) || 1);
    setProductosEditables(prev => {
      const nuevo = [...prev];
      nuevo[idx] = { ...nuevo[idx], cantidad_solicitada: cantidad };
      return nuevo;
    });
  };

  // Eliminar producto de la lista
  const eliminarProducto = (idx) => {
    if (productosEditables.length <= 1) {
      toast.error('La requisición debe tener al menos un producto');
      return;
    }
    setProductosEditables(prev => prev.filter((_, i) => i !== idx));
    toast.success('Producto eliminado de la lista');
  };

  // Agregar producto del catálogo
  const agregarProductoDeCatalogo = (lote) => {
    // Verificar si ya está en la lista
    const yaExiste = productosEditables.some(p => p.lote_id === lote.id);
    if (yaExiste) {
      toast.error('Este lote ya está en la requisición');
      return;
    }
    
    const nuevoProducto = {
      id: null, // Nuevo, sin ID
      lote_id: lote.id,
      producto_id: lote.producto?.id || lote.producto_id || lote.producto,
      producto_clave: lote.producto?.clave || lote.producto_clave,
      producto_nombre: lote.producto?.nombre || lote.producto_nombre,
      numero_lote: lote.numero_lote,
      cantidad_solicitada: 1,
      stock_disponible: lote.cantidad_actual || lote.stock_actual || lote.stock_disponible || 0,
      esNuevo: true
    };
    
    setProductosEditables(prev => [...prev, nuevoProducto]);
    setShowAgregarProducto(false);
    setCatalogoBusqueda('');
    toast.success(`Producto ${nuevoProducto.producto_clave} agregado`);
  };

  // Guardar cambios de edición
  const guardarCambiosProductos = async () => {
    // SEGURIDAD: Validar permisos antes de enviar actualización
    if (!permisos?.editarRequisicion) {
      toast.error('No tienes permisos para editar requisiciones');
      setModoEdicionProductos(false);
      return;
    }
    
    if (productosEditables.length === 0) {
      toast.error('La requisición debe tener al menos un producto');
      return;
    }
    
    // Validar que todas las cantidades sean válidas
    const invalidos = productosEditables.filter(p => !p.cantidad_solicitada || p.cantidad_solicitada < 1);
    if (invalidos.length > 0) {
      toast.error('Todas las cantidades deben ser mayores a 0');
      return;
    }
    
    try {
      setGuardandoCambios(true);
      
      // Preparar datos para el backend
      // El backend espera 'producto' (ID del producto) y opcionalmente 'lote_id'
      const detallesParaEnviar = productosEditables.map(p => {
        const item = {
          producto: p.producto_id,
          cantidad_solicitada: parseInt(p.cantidad_solicitada, 10),
        };
        // Solo incluir lote_id si existe
        if (p.lote_id) {
          item.lote_id = p.lote_id;
        }
        return item;
      });
      
      console.log('Enviando detalles:', detallesParaEnviar);
      
      await requisicionesAPI.update(id, {
        detalles: detallesParaEnviar,
        client_request_id: getDetalleRequestId(),
      });
      
      toast.success('Cambios guardados correctamente');
      resetDetalleRequestId();
      setModoEdicionProductos(false);
      setShowAgregarProducto(false);
      // Limpiar parámetro de URL
      searchParams.delete('modo');
      setSearchParams(searchParams);
      // Recargar requisición
      cargarRequisicion();
    } catch (error) {
      console.error('Error guardando cambios:', error);
      const errorMsg = error.response?.data?.error || 
                       error.response?.data?.detail ||
                       (typeof error.response?.data === 'string' ? error.response.data : null) ||
                       'Error al guardar los cambios';
      toast.error(errorMsg);
    } finally {
      setGuardandoCambios(false);
    }
  };

  // El catálogo ya viene filtrado del servidor, usarlo directamente
  const catalogoFiltrado = catalogoLotes;

  // ============ FIN FUNCIONES MODO EDICIÓN ============

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

  // ISS-SEC: Función auxiliar para ejecutar verificación de hoja
  const executeVerificarHoja = async () => {
    try {
      setProcesando(true);
      await hojasRecoleccionAPI.verificar(hojaRecoleccion.id);
      toast.success('Hoja marcada como verificada');
      cargarHojaRecoleccion();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al verificar hoja');
      throw error;
    } finally {
      setProcesando(false);
    }
  };

  // ISS-SEC: Marcar hoja como verificada por farmacia - con confirmación en 2 pasos
  // eslint-disable-next-line no-unused-vars
  const handleMarcarVerificada = () => {
    if (!hojaRecoleccion) return;
    
    requestDeleteConfirmation({
      title: 'Verificar Hoja de Recolección',
      message: '¿Confirmar que la hoja impresa por el centro coincide exactamente con lo autorizado digitalmente?',
      itemInfo: {
        'Requisición': `#${requisicion?.numero_requisicion || id}`,
        'Centro': requisicion?.centro_nombre || 'N/A'
      },
      onConfirm: executeVerificarHoja,
      isCritical: false,
      confirmText: 'Confirmar verificación'
    });
  };

  // Detectar si es Farmacia/Admin
  // ISS-DIRECTOR FIX: Usar rol_efectivo del backend que incluye inferencia de rol
  const rolUsuario = (user?.rol_efectivo || user?.rol || '').toLowerCase();
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
  
  // Editar: SOLO el médico solicitante puede editar/corregir en borrador o devuelta
  // ISS-FIX-PERMISOS: Admin y Director de centro NO pueden editar, solo el médico que creó la requisición
  // El solicitante puede venir como:
  // - solicitante_id (número)
  // - solicitante.id (objeto)
  // - solicitante (número directamente)
  const solicitanteId = requisicion?.solicitante_id || 
                        requisicion?.solicitante?.id || 
                        (typeof requisicion?.solicitante === 'number' ? requisicion.solicitante : null);
  const esSolicitante = solicitanteId && user?.id && String(solicitanteId) === String(user?.id);
  
  // ISS-FIX: Verificar si es médico (rol que puede editar sus propias requisiciones)
  const esMedico = ['medico', 'centro', 'usuario_centro'].includes(rolUsuario);
  
  // Puede editar si:
  // 1. Estado es borrador o devuelta
  // 2. Es el solicitante original Y es médico, O es superusuario
  // 3. Tiene acceso al centro
  // 4. Tiene permiso de editar requisiciones
  const puedeEditar = ['borrador', 'devuelta'].includes(requisicion?.estado) && 
    tieneAccesoPorCentro &&
    permisos?.editarRequisicion &&
    ((esSolicitante && esMedico) || user?.is_superuser);
    
  // Validar AMBOS: rol de farmacia Y permiso fino correspondiente
  // ISS-DB-002: Estados alineados con BD Supabase
  // ISS-FLUJO-FIX: Farmacia solo puede autorizar en 'en_revision' (después de recibir)
  // El flujo correcto es: enviada → recibir → en_revision → revisar cantidades → autorizar
  // ISS-OWNERSHIP: Verificar si otro usuario de farmacia ya está gestionando esta requisición
  const receptorId = requisicion?.receptor_farmacia || requisicion?.receptor_farmacia_id;
  const receptorNombre = requisicion?.receptor_farmacia_nombre;
  const autorizadorId = requisicion?.autorizador_farmacia || requisicion?.autorizador_farmacia_id;
  const autorizadorNombre = requisicion?.autorizador_farmacia_nombre;
  const esReceptor = !receptorId || user?.is_superuser || String(receptorId) === String(user?.id);
  const esAutorizador = !autorizadorId || user?.is_superuser || String(autorizadorId) === String(user?.id);
  // Otro usuario de farmacia está gestionando (no soy yo)
  const otroGestiona = esFarmacia && receptorId && !esReceptor;
  const otroAutorizo = esFarmacia && autorizadorId && !esAutorizador;

  // puedeAutorizar controla si SE MUESTRA el banner de autorización.
  // La restricción de receptor se aplica en iniciarAutorizacion() (bloquea al no-receptor)
  // y en el backend (403 si receptor_farmacia_id != request.user.id).
  const puedeAutorizar = requisicion?.estado === 'en_revision' && esFarmacia && permisos?.autorizarRequisicion;
  // En enviada: cualquier farmacia puede rechazar (nadie ha tomado posesión aún).
  // En en_revision: solo el receptor puede rechazar (mismo criterio que autorizar).
  const puedeRechazar =
    esFarmacia && permisos?.rechazarRequisicion &&
    (
      requisicion?.estado === 'enviada' ||
      (requisicion?.estado === 'en_revision' && esReceptor)
    );
  // ISS-FIX-SURTIR: Solo desde 'autorizada' - surtir SIEMPRE termina en 'entregada'
  // esAutorizador no se verifica aquí: el backend no tiene ownership check en surtir,
  // cualquier farmacia con permiso puede surtir una requisición autorizada.
  const puedeSurtir = requisicion?.estado === 'autorizada' && esFarmacia && permisos?.surtirRequisicion;
  
  // ISS-FIX-SURTIR: Ya no hay estado intermedio 'surtida' - el surtido va directo a 'entregada'
  // puedeMarcarRecibida ya no es necesario porque el surtido completa automáticamente
  const puedeMarcarRecibida = false; // Deshabilitado - flujo simplificado
  
  // Cancelar: validar centro para usuarios no privilegiados
  // ISS-DB-002: Estados terminales
  const puedeCancelar = !['surtida', 'cancelada', 'rechazada', 'entregada'].includes(requisicion?.estado) && 
    permisos?.cancelarRequisicion &&
    tieneAccesoPorCentro; // Usuarios de centro solo pueden cancelar las suyas
    
  // Descargas: validar centro para usuarios no privilegiados (aislamiento de datos)
  // ISS-DB-002: Estados que permiten descarga
  // ISS-HOJA-V2: Lógica de descarga según rol y estado:
  // - Médico/Centro en 'autorizada': Descarga hoja con firmas vacías para llevar a firmar
  // - Médico/Centro en 'surtida/entregada': Descarga hoja de CONSULTA con sello "SURTIDA"
  // - Farmacia: Siempre puede descargar hoja completa
  // ISS-HOJA-FIX: Solo médico y centro (NO admin ni director) pueden descargar hoja
  const rolParaHoja = (user?.rol_efectivo || user?.rol || '').toLowerCase();
  const esCentroParaHoja = ['medico', 'centro', 'usuario_centro'].includes(rolParaHoja) && tieneAccesoPorCentro;
  const esCentro = !esFarmacia && tieneAccesoPorCentro;
  const estadoAutorizada = requisicion?.estado === 'autorizada';
  const estadoSurtidaOEntregada = ['surtida', 'entregada'].includes(requisicion?.estado);
  
  // Centro: puede descargar en autorizada (para firmas) o surtida/entregada (consulta)
  // ISS-HOJA-FIX: Solo médico y centro (NO admin ni director)
  const puedeDescargarHojaCentro = esCentroParaHoja && 
    permisos?.descargarHojaRecoleccion &&
    (estadoAutorizada || estadoSurtidaOEntregada);
  
  // Farmacia: puede descargar en cualquier estado permitido
  const puedeDescargarHojaFarmacia = esFarmacia && 
    permisos?.descargarHojaRecoleccion &&
    ['autorizada', 'en_surtido', 'parcial', 'surtida', 'entregada'].includes(requisicion?.estado);
  
  const puedeDescargarHoja = puedeDescargarHojaCentro || puedeDescargarHojaFarmacia;
    
  const puedeDescargarRechazo = requisicion?.estado === 'rechazada' && 
    permisos?.descargarHojaRecoleccion &&
    tieneAccesoPorCentro; // Usuarios de centro solo descargan rechazos de su centro
  
  // Recibo de Salida: disponible para requisiciones surtidas/entregadas
  const puedeDescargarReciboSalida = ['surtida', 'parcial', 'entregada'].includes(requisicion?.estado) &&
    (esFarmacia || tieneAccesoPorCentro);
    
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

          {/* FLUJO V2: Fecha límite de recolección - visible para centros */}
          {requisicion.fecha_recoleccion_limite && (
            <div className="flex items-start gap-3">
              <FaCalendar className="text-orange-500 mt-1" />
              <div>
                <p className="text-sm text-gray-500">Fecha Límite Recolección</p>
                <p className="font-semibold text-orange-600">
                  {formatFecha(requisicion.fecha_recoleccion_limite)}
                </p>
                <p className="text-xs text-gray-400">
                  {new Date(requisicion.fecha_recoleccion_limite) < new Date() 
                    ? '⚠️ Plazo vencido' 
                    : '✓ Dentro del plazo'}
                </p>
              </div>
            </div>
          )}
        </div>

        {requisicion.observaciones && (
          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2 text-gray-600 mb-1">
              <FaInfoCircle />
              <span className="text-sm font-semibold">Observaciones del Centro</span>
            </div>
            <p className="text-gray-700">{requisicion.observaciones}</p>
          </div>
        )}

        {/* FLUJO V2: Observaciones de farmacia - Prominente cuando hay ajustes */}
        {requisicion.observaciones_farmacia && (
          <div className="mt-4 p-4 bg-amber-50 rounded-lg border-2 border-amber-400 shadow-md">
            <div className="flex items-center gap-2 text-amber-700 mb-2">
              <FaExclamationTriangle className="text-amber-500 text-xl" />
              <span className="font-bold text-lg">📋 Observaciones de Farmacia Central</span>
            </div>
            <p className="text-amber-800 font-medium text-base">{requisicion.observaciones_farmacia}</p>
            <p className="text-amber-600 text-sm mt-2 italic">
              Revise los motivos de ajuste en cada producto para más detalle.
            </p>
          </div>
        )}

        {/* BANNER PROMINENTE: Motivo de devolución */}
        {requisicion.estado === 'devuelta' && requisicion.motivo_devolucion && (
          <div className="mt-4 p-4 bg-amber-50 rounded-lg border-2 border-amber-400 shadow-md">
            <div className="flex items-center gap-2 text-amber-700 mb-2">
              <FaExclamationTriangle className="text-amber-500 text-xl" />
              <span className="font-bold text-lg">⚠️ Requisición Devuelta para Corrección</span>
            </div>
            <p className="text-amber-800 font-medium text-base">{requisicion.motivo_devolucion}</p>
            <p className="text-amber-600 text-sm mt-2 italic">Realice las correcciones indicadas y vuelva a enviar la requisición.</p>
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

        {/* ISS-FIX: Mostrar motivo de cancelación */}
        {requisicion.estado === 'cancelada' && (
          <div className="mt-4 p-4 bg-gray-100 rounded-lg border-2 border-gray-400 shadow-md">
            <div className="flex items-center gap-2 text-gray-700 mb-2">
              <FaTimes className="text-gray-500 text-xl" />
              <span className="font-bold text-lg">🚫 Requisición Cancelada</span>
            </div>
            {requisicion.notas?.startsWith('[CANCELADA]') ? (
              <p className="text-gray-800 font-medium text-base">{requisicion.notas.replace('[CANCELADA] ', '')}</p>
            ) : (
              <p className="text-gray-600 italic">Motivo no registrado. Consulte el historial para más detalles.</p>
            )}
            <p className="text-gray-500 text-sm mt-2 italic">Puede revisar el historial de cambios para ver quién canceló esta requisición.</p>
          </div>
        )}

        {requisicion.motivo_vencimiento && (
          <div className="mt-4 p-3 bg-red-50 rounded-lg border border-red-200">
            <div className="flex items-center gap-2 text-red-600 mb-1">
              <FaCalendar />
              <span className="text-sm font-semibold">Motivo de Vencimiento</span>
            </div>
            <p className="text-red-700">{requisicion.motivo_vencimiento}</p>
            {requisicion.fecha_vencimiento && (
              <p className="text-xs text-red-600 mt-1">
                Marcada como vencida el {formatFecha(requisicion.fecha_vencimiento)}
              </p>
            )}
          </div>
        )}
      </div>

      {/* ── Banner contextual de autorización ── SOLO FARMACIA/ADMIN ────────── */}
      {puedeAutorizar && !modoAutorizar && (() => {
        // Pre-calcular ítems con stock insuficiente (cantidad solicitada > disponible)
        const itemsStockInsuficiente = detallesEditables.filter(d => {
          const stock = d.stock_disponible ?? d.lote_stock ?? 0;
          return (d.cantidad_solicitada || 0) > stock;
        });

        if (otroGestiona) {
          // ── Caso: otro usuario de farmacia recibió la requisición ──────────
          return (
            <div className="border border-amber-300 bg-amber-50 rounded-xl p-5 mb-6 shadow-sm">
              <div className="flex items-start gap-4">
                <div className="p-2 rounded-lg bg-amber-100 shrink-0 mt-0.5">
                  <FaUserShield className="text-xl text-amber-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-bold text-amber-800 text-sm mb-1">
                    Recibida por: <span className="font-semibold">{receptorNombre || `Usuario #${receptorId}`}</span>
                  </h3>
                  <p className="text-xs text-amber-700 mb-3">
                    Solo el usuario receptor puede confirmar la autorización. Tu rol en esta etapa:
                  </p>
                  <ul className="text-xs text-amber-700 space-y-1">
                    <li className="flex items-center gap-1.5"><FaCheck className="text-green-600 shrink-0" /> Puedes ver las cantidades solicitadas en la tabla de abajo</li>
                    <li className="flex items-center gap-1.5"><FaTimes className="text-red-500 shrink-0" /> No puedes rechazarla — acción exclusiva del receptor</li>
                    <li className="flex items-center gap-1.5"><FaTimes className="text-red-500 shrink-0" /> No puedes autorizarla — la confirma {receptorNombre || 'el receptor'}</li>
                  </ul>
                </div>
              </div>
            </div>
          );
        }

        if (itemsStockInsuficiente.length > 0) {
          // ── Caso: hay ítems con stock insuficiente ────────────────────────
          return (
            <div className="border border-blue-300 bg-blue-50 rounded-xl p-5 mb-6 shadow-sm">
              <div className="flex items-start gap-4">
                <div className="p-2 rounded-lg bg-blue-100 shrink-0 mt-0.5">
                  <FaExclamationTriangle className="text-xl text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-bold text-blue-800 text-sm mb-1">
                    Revisión necesaria — {itemsStockInsuficiente.length} producto{itemsStockInsuficiente.length > 1 ? 's' : ''} con stock insuficiente
                  </h3>
                  <p className="text-xs text-blue-700 mb-2">
                    Deberás ajustar las cantidades autorizadas antes de confirmar:
                  </p>
                  <ul className="text-xs text-blue-700 space-y-0.5 mb-4">
                    {itemsStockInsuficiente.map((d, i) => {
                      const stock = d.stock_disponible ?? d.lote_stock ?? 0;
                      return (
                        <li key={i} className="flex items-center gap-1">
                          <span className="text-red-500 font-bold">·</span>
                          <strong>{d.producto_nombre || d.producto_clave}</strong>:
                          solicitado <span className="font-semibold">{d.cantidad_solicitada}</span>,
                          disponible <span className="font-semibold text-red-600">{stock}</span>
                        </li>
                      );
                    })}
                  </ul>
                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      onClick={iniciarAutorizacion}
                      disabled={procesando}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg disabled:opacity-50 font-medium transition-colors"
                    >
                      <FaEdit /> Revisar Cantidades
                    </button>
                    <span className="text-xs text-blue-600">· Para rechazar directamente usa el botón "Rechazar" al pie</span>
                  </div>
                </div>
              </div>
            </div>
          );
        }

        // ── Caso normal: stock OK, usuario es receptor ────────────────────
        return (
          <div className="border border-gray-200 bg-white rounded-xl p-5 mb-6 shadow-sm">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="p-2 rounded-lg bg-green-50 shrink-0">
                  <FaClipboardList className="text-xl text-green-600" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-800 text-sm">Requisición Pendiente de Revisión</h3>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Stock disponible para todos los productos. Revisa, ajusta si es necesario y confirma.
                    <span className="ml-2 text-gray-400">· Para rechazar directamente usa el botón "Rechazar" al pie.</span>
                  </p>
                </div>
              </div>
              <button
                onClick={iniciarAutorizacion}
                disabled={procesando}
                className="shrink-0 inline-flex items-center gap-2 px-5 py-2.5 text-white rounded-lg disabled:opacity-50 font-semibold hover:opacity-90 transition-opacity bg-theme-primary text-sm"
              >
                <FaEdit /> Revisar Cantidades
              </button>
            </div>
          </div>
        );
      })()}

      {/* Banner informativo cuando la requisición ya está autorizada por otro */}
      {otroAutorizo && requisicion?.estado === 'autorizada' && (
        <div className="border border-amber-300 bg-amber-50 rounded-xl p-4 mb-6 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-100 shrink-0">
              <FaUserShield className="text-xl text-amber-600" />
            </div>
            <div>
              <h3 className="font-bold text-amber-800 text-sm">
                Autorizada por: <span>{autorizadorNombre || `Usuario #${autorizadorId}`}</span>
              </h3>
              <p className="text-xs text-amber-700 mt-0.5">
                Cualquier usuario de farmacia puede proceder con el surtido.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Tabla de Productos */}
      <div className="bg-white rounded-xl shadow-lg p-4 sm:p-6 mb-6 overflow-hidden">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-theme-primary">
            Productos Solicitados ({modoEdicionProductos ? productosEditables.length : detalles.length})
          </h2>
          <div className="flex items-center gap-2">
            {modoAutorizar && (
              <span className="px-3 py-1 border rounded-full text-sm font-semibold border-theme-primary text-theme-primary">
                Modo Autorización
              </span>
            )}
            {modoEdicionProductos && (
              <span className="px-3 py-1 border rounded-full text-sm font-semibold border-amber-500 text-amber-600 bg-amber-50">
                ✏️ Modo Edición
              </span>
            )}
            {/* Botón para iniciar edición si puede editar y no está editando */}
            {puedeEditar && !modoEdicionProductos && !modoAutorizar && (
              <button
                onClick={iniciarEdicionProductos}
                className="flex items-center gap-2 px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors font-medium"
              >
                <FaEdit /> Editar Productos
              </button>
            )}
          </div>
        </div>

        {/* MODO EDICIÓN DE PRODUCTOS */}
        {modoEdicionProductos ? (
          <>
            {/* Vista móvil: tarjetas editables */}
            <div className="lg:hidden space-y-3">
              {productosEditables.map((prod, idx) => (
                <div key={prod.id || `nuevo-${idx}`} className={`p-4 rounded-lg border shadow-sm ${prod.esNuevo ? 'bg-green-50 border-green-200' : 'bg-white border-gray-200'}`}>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-gray-900 truncate">{prod.producto_nombre || '-'}</div>
                      <div className="text-xs text-gray-500">
                        Clave: {prod.producto_clave || '-'} {prod.esNuevo && <span className="text-green-600">(Nuevo)</span>}
                      </div>
                    </div>
                    <button
                      onClick={() => eliminarProducto(idx)}
                      className="p-2 text-red-500 hover:bg-red-100 rounded-lg"
                    >
                      <FaTrash size={14} />
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm mb-3">
                    <div>
                      <span className="text-gray-500">Lote:</span>
                      <span className="ml-1 font-mono">{prod.numero_lote || '-'}</span>
                    </div>
                    {esAdminOFarmacia && (
                      <div>
                        <span className="text-gray-500">Stock:</span>
                        <span className={`ml-1 font-semibold ${prod.stock_disponible < prod.cantidad_solicitada ? 'text-red-600' : 'text-green-600'}`}>
                          {prod.stock_disponible ?? 0}
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center justify-center gap-2 pt-2 border-t border-gray-100">
                    <span className="text-sm text-gray-600">Cantidad:</span>
                    <button
                      onClick={() => actualizarCantidadProducto(idx, prod.cantidad_solicitada - 1)}
                      className="p-2 text-gray-500 hover:text-red-500 bg-gray-100 rounded-lg"
                      disabled={prod.cantidad_solicitada <= 1}
                    >
                      <FaMinus size={12} />
                    </button>
                    <input
                      type="number"
                      min="1"
                      value={prod.cantidad_solicitada}
                      onChange={(e) => actualizarCantidadProducto(idx, e.target.value)}
                      className="w-16 px-2 py-2 border border-gray-300 rounded-lg text-center font-semibold"
                    />
                    <button
                      onClick={() => actualizarCantidadProducto(idx, prod.cantidad_solicitada + 1)}
                      className="p-2 text-gray-500 hover:text-green-500 bg-gray-100 rounded-lg"
                    >
                      <FaPlus size={12} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            
            {/* Vista desktop: tabla editable */}
            <div className="hidden lg:block w-full overflow-x-auto rounded-lg border border-amber-200 shadow-md -mx-2 sm:mx-0">
              <table className="w-full min-w-[600px] border-collapse table-fixed">
                <thead className="bg-amber-500">
                  <tr>
                    <th className="w-20 px-2 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white">Clave</th>
                    <th className="w-auto px-2 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white">Producto</th>
                    <th className="w-24 px-2 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white">Lote</th>
                    {/* ISS-SEGURIDAD: Solo Admin/Farmacia ve el stock disponible */}
                    {esAdminOFarmacia && (
                      <th className="w-16 px-2 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white">Stock</th>
                    )}
                    <th className="w-28 px-2 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white">Cantidad</th>
                    <th className="w-16 px-2 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {productosEditables.map((prod, idx) => (
                    <tr key={prod.id || `nuevo-${idx}`} className={`border-b border-gray-200 ${prod.esNuevo ? 'bg-green-50' : 'hover:bg-gray-50'}`}>
                      <td className="px-2 py-2 text-sm font-mono text-gray-800 truncate">
                        {prod.producto_clave || '-'}
                        {prod.esNuevo && <span className="ml-1 text-xs text-green-600">(+)</span>}
                      </td>
                      <td className="px-2 py-2 text-sm text-gray-800 truncate" title={prod.producto_nombre}>
                        {prod.producto_nombre || '-'}
                      </td>
                      <td className="px-2 py-2 text-center text-xs font-mono truncate">
                        {prod.numero_lote || '-'}
                      </td>
                      {/* ISS-SEGURIDAD: Solo Admin/Farmacia ve el stock disponible */}
                      {esAdminOFarmacia && (
                        <td className="px-2 py-2 text-center">
                          <span className={`font-semibold text-sm ${prod.stock_disponible < prod.cantidad_solicitada ? 'text-red-600' : 'text-green-600'}`}>
                            {prod.stock_disponible ?? 0}
                          </span>
                        </td>
                      )}
                      <td className="px-2 py-2 text-center">
                        <div className="flex items-center justify-center gap-0.5">
                          <button
                            onClick={() => actualizarCantidadProducto(idx, prod.cantidad_solicitada - 1)}
                            className="p-1 text-gray-500 hover:text-red-500 transition-colors"
                            disabled={prod.cantidad_solicitada <= 1}
                          >
                            <FaMinus size={10} />
                          </button>
                          <input
                            type="number"
                            min="1"
                            value={prod.cantidad_solicitada}
                            onChange={(e) => actualizarCantidadProducto(idx, e.target.value)}
                            className="w-14 px-1 py-1 border border-gray-300 rounded text-center text-sm font-semibold focus:ring-2 focus:outline-none focus:ring-amber-400"
                          />
                          <button
                            onClick={() => actualizarCantidadProducto(idx, prod.cantidad_solicitada + 1)}
                            className="p-1 text-gray-500 hover:text-green-500 transition-colors"
                          >
                            <FaPlus size={10} />
                          </button>
                        </div>
                      </td>
                      <td className="px-2 py-2 text-center">
                        <button
                          onClick={() => eliminarProducto(idx)}
                          className="p-1.5 text-red-500 hover:bg-red-100 rounded transition-colors"
                          title="Eliminar"
                        >
                          <FaTrash size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Botón agregar producto */}
            <div className="mt-4">
              {!showAgregarProducto ? (
                <button
                  onClick={() => setShowAgregarProducto(true)}
                  className="flex items-center gap-2 px-4 py-2 border-2 border-dashed border-green-400 text-green-600 rounded-lg hover:bg-green-50 transition-colors font-medium"
                >
                  <FaPlus /> Agregar Producto
                </button>
              ) : (
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-gray-700 flex items-center gap-2">
                      <FaSearch className="text-gray-400" />
                      Buscar en Catálogo de Lotes
                    </h3>
                    <button
                      onClick={() => { setShowAgregarProducto(false); setCatalogoBusqueda(''); }}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <FaTimes />
                    </button>
                  </div>
                  
                  <input
                    type="text"
                    placeholder="Buscar por clave, nombre o número de lote..."
                    value={catalogoBusqueda}
                    onChange={(e) => handleCatalogoBusquedaChange(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:outline-none focus:ring-green-400 mb-3"
                    autoFocus
                  />

                  {loadingCatalogo ? (
                    <div className="flex items-center justify-center py-4">
                      <div className="animate-spin rounded-full h-6 w-6 border-2 border-t-transparent border-green-500"></div>
                      <span className="ml-2 text-gray-500">Buscando...</span>
                    </div>
                  ) : catalogoBusqueda.trim() ? (
                    <div className="max-h-60 overflow-y-auto border rounded-lg">
                      {catalogoFiltrado.length === 0 ? (
                        <p className="text-center text-gray-500 py-4">No se encontraron productos con "{catalogoBusqueda}"</p>
                      ) : (
                        catalogoFiltrado.slice(0, 20).map(lote => (
                          <div
                            key={lote.id}
                            className="flex items-center justify-between p-3 border-b last:border-b-0 hover:bg-green-50 cursor-pointer"
                            onClick={() => agregarProductoDeCatalogo(lote)}
                          >
                            <div>
                              <span className="font-mono font-semibold text-gray-800">{lote.producto?.clave || lote.producto_clave}</span>
                              <span className="mx-2 text-gray-400">-</span>
                              <span className="text-gray-700">{lote.producto?.nombre || lote.producto_nombre}</span>
                              <span className="ml-2 text-xs text-gray-500">Lote: {lote.numero_lote}</span>
                            </div>
                            <div className="flex items-center gap-3">
                              {/* ISS-SEGURIDAD: Solo Admin/Farmacia ve el stock */}
                              {esAdminOFarmacia && (
                                <span className={`text-sm font-semibold ${(lote.cantidad_actual || lote.stock_actual || 0) > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                  Stock: {lote.cantidad_actual || lote.stock_actual || 0}
                                </span>
                              )}
                              <FaPlus className="text-green-500" />
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  ) : (
                    <p className="text-center text-gray-400 py-4 text-sm">Escriba para buscar productos disponibles</p>
                  )}
                </div>
              )}
            </div>

            {/* Botones de acción */}
            <div className="mt-6 flex items-center justify-end gap-3 pt-4 border-t">
              <button
                onClick={cancelarEdicionProductos}
                disabled={guardandoCambios}
                className="flex items-center gap-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium disabled:opacity-50"
              >
                <FaTimes /> Cancelar
              </button>
              <button
                onClick={guardarCambiosProductos}
                disabled={guardandoCambios || productosEditables.length === 0}
                className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-semibold disabled:opacity-50"
              >
                {guardandoCambios ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-t-transparent border-white"></div>
                    Guardando...
                  </>
                ) : (
                  <>
                    <FaSave /> Guardar Cambios
                  </>
                )}
              </button>
            </div>
          </>
        ) : detalles.length === 0 ? (
          <p className="text-center text-gray-500 py-8">No hay productos en esta requisición</p>
        ) : (
          <div className="w-full overflow-x-auto -mx-4 sm:mx-0 px-4 sm:px-0">
            <div className="inline-block min-w-full align-middle">
              <div className="overflow-hidden table-soft">
                <table className="min-w-full border-collapse text-xs">
                  <thead className="thead-soft">
                    <tr>
                      <th className="px-2 py-2 text-left text-[10px] font-semibold uppercase text-white whitespace-nowrap">Clave</th>
                      <th className="px-2 py-2 text-left text-[10px] font-semibold uppercase text-white">Producto</th>
                      <th className="px-2 py-2 text-left text-[10px] font-semibold uppercase text-white">Presentación</th>
                      <th className="px-2 py-2 text-center text-[10px] font-semibold uppercase text-white whitespace-nowrap">Lote</th>
                      <th className="px-2 py-2 text-center text-[10px] font-semibold uppercase text-white whitespace-nowrap">Unidad</th>
                      {/* EXISTENCIAS CENTRO: Solo visible para usuarios del centro (no farmacia) */}
                      {esCentro && (
                        <th className="px-2 py-2 text-center text-[10px] font-semibold uppercase text-white bg-emerald-600 whitespace-nowrap">
                          Exist. Centro
                        </th>
                      )}
                      {/* ISS-UI-FIX: Mostrar Inventario Almacén y Centro para tomar decisiones */}
                      {(modoAutorizar || esFarmacia) && (
                        <>
                          <th className="px-1 py-2 text-center text-[10px] font-semibold uppercase text-white bg-blue-600 whitespace-nowrap">
                            Inv. Alm.
                          </th>
                          <th className="px-1 py-2 text-center text-[10px] font-semibold uppercase text-white bg-purple-600 whitespace-nowrap">
                            Inv. Cen.
                          </th>
                        </>
                      )}
                      <th className="px-1 py-2 text-center text-[10px] font-semibold uppercase text-white whitespace-nowrap">Solic.</th>
                      <th className={`px-1 py-2 text-center text-[10px] font-semibold uppercase whitespace-nowrap ${modoAutorizar ? 'bg-green-600 text-white' : 'text-white'}`}>
                        Autoriz.
                      </th>
                      {/* MEJORA FLUJO 3: Columna para motivo de ajuste - visible también cuando hay ajustes */}
                      {(modoAutorizar || detalles.some(d => d.cantidad_autorizada < d.cantidad_solicitada && d.motivo_ajuste)) && (
                        <th className="px-2 py-2 text-left text-[10px] font-semibold uppercase bg-amber-500 text-white">
                          Motivo Ajuste
                        </th>
                      )}
                      <th className="px-1 py-2 text-center text-[10px] font-semibold uppercase text-white whitespace-nowrap">Surtido</th>
                    </tr>
                  </thead>
              <tbody>
                {detalles.map((detalle, idx) => (
                  <tr key={detalle.id || idx} className="border-b border-gray-200 hover:bg-gray-50">
                    <td className="px-2 py-2 text-xs font-mono font-semibold text-gray-800">
                      {detalle.producto_clave || detalle.producto?.clave || '-'}
                    </td>
                    <td className="px-2 py-2 text-xs text-gray-800">
                      {detalle.producto_nombre || detalle.producto?.nombre || detalle.nombre || '-'}
                    </td>
                    <td className="px-2 py-2 text-xs text-gray-600">
                      {detalle.producto_presentacion || detalle.producto?.presentacion || '—'}
                    </td>
                    <td className="px-2 py-2 text-center text-xs">
                      {detalle.lote_numero ? (
                        <div>
                          <span className="font-mono font-semibold text-gray-700">{detalle.lote_numero}</span>
                          {detalle.lote_caducidad && (
                            <div className="text-gray-500 text-[10px]">Cad: {detalle.lote_caducidad}</div>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-2 py-2 text-xs text-center text-gray-600">
                      {detalle.producto_unidad || detalle.producto?.unidad_medida || '-'}
                    </td>
                    {/* EXISTENCIAS CENTRO: Solo visible para usuarios del centro (no farmacia) */}
                    {esCentro && (
                      <td className="px-2 py-2 text-center bg-emerald-50">
                        <span className={`font-bold text-xs ${
                          (detalle.stock_centro || 0) > 0 ? 'text-emerald-700' : 'text-gray-400'
                        }`}>
                          {detalle.stock_centro ?? 0}
                        </span>
                      </td>
                    )}
                    {/* ISS-UI-FIX: Inventario Almacén y Centro visible en modo autorización */}
                    {(modoAutorizar || esFarmacia) && (
                      <>
                        <td className="px-2 py-2 text-center bg-blue-50">
                          <span className={`font-bold ${
                            (detalle.stock_disponible ?? detalle.lote_stock ?? 0) < detalle.cantidad_solicitada
                              ? 'text-red-600'
                              : (detalle.stock_disponible ?? detalle.lote_stock ?? 0) === 0
                                ? 'text-red-600'
                                : 'text-green-600'
                          }`}>
                            {detalle.stock_disponible ?? detalle.lote_stock ?? 0}
                          </span>
                        </td>
                        <td className="px-2 py-2 text-center bg-purple-50">
                          <span className={`font-bold ${
                            (detalle.stock_centro || 0) > 0 ? 'text-purple-600' : 'text-gray-400'
                          }`}>
                            {detalle.stock_centro ?? 0}
                          </span>
                        </td>
                      </>
                    )}
                    <td className="px-2 py-2 text-center font-bold text-gray-800">
                      {detalle.cantidad_solicitada}
                    </td>
                    <td className={`px-2 py-2 text-center ${modoAutorizar ? 'bg-green-50' : ''}`}>
                      {modoAutorizar ? (
                        <input
                          type="number"
                          min="0"
                          max={detalle.stock_disponible ?? detalle.lote_stock ?? detalle.cantidad_solicitada}
                          value={detalle.cantidad_autorizada || 0}
                          onChange={(e) => actualizarCantidadAutorizada(idx, e.target.value)}
                          className="w-14 px-1 py-1 border border-gray-300 rounded text-center font-bold text-xs focus:ring-2 focus:outline-none focus:ring-green-400"
                        />
                      ) : (
                        <span className={detalle.cantidad_autorizada > 0 ? 'font-semibold text-gray-800' : 'text-gray-400'}>
                          {detalle.cantidad_autorizada ?? '-'}
                        </span>
                      )}
                    </td>
                    {/* MEJORA FLUJO 3: Input de motivo de ajuste cuando se reduce cantidad */}
                    {(modoAutorizar || detalles.some(d => d.cantidad_autorizada < d.cantidad_solicitada && d.motivo_ajuste)) && (
                      <td className="px-1 py-2 bg-amber-50">
                        {modoAutorizar ? (
                          // Modo edición: input para ingresar motivo
                          detalle.cantidad_autorizada < detalle.cantidad_solicitada ? (
                            <input
                              type="text"
                              placeholder="Motivo..."
                              value={detalle.motivo_ajuste || ''}
                              onChange={(e) => actualizarMotivoAjuste(idx, e.target.value)}
                              className={`w-full px-1 py-1 text-xs border rounded focus:outline-none ${
                                detalle.motivo_ajuste && detalle.motivo_ajuste.length >= 10
                                  ? 'border-green-400 bg-green-50'
                                  : 'border-amber-400'
                              }`}
                            />
                          ) : (
                            <span className="text-gray-400 text-xs">-</span>
                          )
                        ) : (
                          // Modo lectura: mostrar motivo guardado con mejor formato
                          detalle.cantidad_autorizada < detalle.cantidad_solicitada && detalle.motivo_ajuste ? (
                            <div className="max-w-[200px]" title={detalle.motivo_ajuste}>
                              <span className="text-xs text-amber-700 font-medium truncate block">
                                ⚠️ {detalle.motivo_ajuste}
                              </span>
                            </div>
                          ) : (
                            <span className="text-gray-400 text-xs">-</span>
                          )
                        )}
                      </td>
                    )}
                    <td className="px-2 py-2 text-center">
                      <span className={detalle.cantidad_surtida > 0 ? 'font-semibold text-gray-800' : 'text-gray-400'}>
                        {detalle.cantidad_surtida ?? 0}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
              </div>
            </div>
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

      {/* Hoja de Recolección - Solo visible para FARMACIA (no admin_centro/director_centro) */}
      {/* ISS-HOJA-FIX: Admin/Director centro NO deben ver la hoja - solo farmacia la maneja */}
      {hojaRecoleccion && esFarmacia && (
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
          {/* ISS-DIRECTOR FIX: Usar rol_efectivo o rol */}
          {(user?.rol_efectivo || user?.rol) === 'farmacia' && (
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
          {/* FLUJO V2: Texto diferente según estado */}
          {puedeDescargarHoja && (
            <div className="mt-4 flex justify-end">
              <button
                onClick={() => handleDescargarPDF('aceptacion')}
                disabled={procesando}
                className={`flex items-center gap-2 px-4 py-2 text-white rounded-lg disabled:opacity-50 hover:opacity-90 transition-opacity ${requisicion?.estado === 'entregada' ? 'bg-green-600' : 'bg-theme-primary'}`}
              >
                <FaFileDownload />
                {requisicion?.estado === 'entregada' ? 'Recibo de Salida' : 'Descargar PDF de Recolección'}
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

      {/* Acciones - FLUJO V2: Usar componente centralizado */}
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
              {/* Botón EDITAR prominente para requisiciones devueltas */}
              {puedeEditar && (
                <button
                  onClick={() => navigate(`/requisiciones/${requisicion.id}?modo=editar`)}
                  disabled={procesando}
                  className="flex items-center gap-2 px-6 py-3 bg-amber-500 hover:bg-amber-600 text-white rounded-lg disabled:opacity-50 transition-colors font-semibold shadow-md"
                >
                  <FaEdit className="text-lg" /> 
                  {requisicion?.estado === 'devuelta' ? 'Corregir' : 'Editar'}
                </button>
              )}

              {/* FLUJO V2: Acciones del flujo según rol y estado */}
              <RequisicionAcciones
                requisicion={requisicion}
                onAccionCompletada={() => cargarRequisicion()}
                mostrarHistorial={false}
                size="lg"
              />

              {/* Acciones adicionales que no están en el flujo V2 */}
              {/* FLUJO V2: Botón con texto según estado */}
              {puedeDescargarHoja && (
                <button
                  onClick={() => handleDescargarPDF('aceptacion')}
                  disabled={procesando}
                  className={`flex items-center gap-2 px-4 py-2 border rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors ${requisicion?.estado === 'entregada' ? 'border-green-500 text-green-600' : 'border-theme-primary text-theme-primary'}`}
                >
                  <FaDownload /> {requisicion?.estado === 'entregada' ? 'Recibo de Entrega' : 'Hoja de recolección'}
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
              
              {/* Recibo de Salida: Documento oficial para requisiciones surtidas (NO entregadas, ya que ese usa el botón principal) */}
              {puedeDescargarReciboSalida && requisicion?.estado !== 'entregada' && (
                <button
                  onClick={handleDescargarReciboSalida}
                  disabled={procesando}
                  className="flex items-center gap-2 px-4 py-2 border border-purple-400 text-purple-600 rounded-lg hover:bg-purple-50 disabled:opacity-50 transition-colors"
                  title="Descargar el Recibo de Salida oficial para el control de entregas"
                >
                  <FaDownload /> Recibo de Salida
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
      {/* MEJORA FLUJO 3: Ahora permite agregar observación general además del motivo por item */}
      <InputModal
        open={showAutorizarParcialModal}
        onCancel={() => setShowAutorizarParcialModal(false)}
        onConfirm={(observaciones) => ejecutarAutorizacionParcial(observaciones)}
        title="Confirmar autorización parcial"
        message="Ha reducido las cantidades de algunos productos. Puede agregar una observación general que el Centro verá (opcional). Verifique que indicó el motivo en cada producto."
        placeholder="Observación general para el Centro (ej: Stock insuficiente, próxima reposición en X días...)"
        minLength={0}
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

      {/* Modal de confirmación para surtir y entregar */}
      <ConfirmModal
        open={showSurtirModal}
        onCancel={() => setShowSurtirModal(false)}
        onConfirm={ejecutarSurtir}
        title="Surtir y Entregar"
        message={`¿Surtir y entregar la requisición ${requisicion?.folio || ''}? Se descontará el inventario de farmacia y se agregará al centro destino automáticamente.`}
        confirmText="Surtir y Entregar"
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

      {/* ISS-FIX: Modal para fecha límite de recolección */}
      {showFechaRecoleccionModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-semibold mb-4 text-theme-primary">
              Asignar Fecha Límite de Recolección
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Seleccione la fecha y hora límite para que el centro recoja los productos autorizados.
            </p>
            
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Fecha y hora límite *
            </label>
            <input
              type="datetime-local"
              value={fechaRecoleccion}
              onChange={(e) => setFechaRecoleccion(e.target.value)}
              min={new Date().toISOString().slice(0, 16)}
              className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-theme-primary mb-4"
            />
            
            <div className="flex justify-end gap-3 mt-6">
              <button
                type="button"
                onClick={() => {
                  setShowFechaRecoleccionModal(false);
                  setFechaRecoleccion('');
                }}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 border border-gray-300 rounded-lg"
              >
                Cancelar
              </button>
              <button
                onClick={ejecutarAutorizacionConFecha}
                disabled={!fechaRecoleccion || procesando}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                {procesando ? 'Autorizando...' : 'Autorizar Requisición'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de confirmación en dos pasos */}
      <TwoStepConfirmModal
        isOpen={confirmState.isOpen}
        onClose={cancelConfirmation}
        onConfirm={() => executeWithConfirmation(confirmState.onConfirm)}
        title={confirmState.title}
        message={confirmState.message}
        itemInfo={confirmState.itemInfo}
        confirmText={confirmState.confirmText}
        cancelText={confirmState.cancelText}
        actionType={confirmState.actionType}
        isCritical={confirmState.isCritical}
        confirmPhrase={confirmState.confirmPhrase}
        isLoading={confirmState.isLoading}
      />
    </div>
  );
};

export default RequisicionDetalle;






