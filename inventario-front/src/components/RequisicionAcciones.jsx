/**
 * FLUJO V2: Componente de botones de acción para requisiciones
 * 
 * Muestra botones contextuales según el estado de la requisición
 * y los permisos del usuario.
 */

import { useState, useMemo } from 'react';
import { 
  FaPaperPlane, 
  FaCheck, 
  FaTimes, 
  FaBoxOpen, 
  FaUndo, 
  FaBan, 
  FaClock,
  FaClipboardCheck,
  FaUserCheck,
  FaUserTie,
  FaWarehouse,
  FaHistory,
  FaSpinner
} from 'react-icons/fa';
import { useRequisicionFlujo } from '../hooks/useRequisicionFlujo';
import { toast } from 'react-hot-toast';

// Mapeo de acciones a íconos
const ICONOS_ACCION = {
  enviar_admin: FaPaperPlane,
  autorizar_admin: FaUserCheck,
  autorizar_director: FaUserTie,
  recibir_farmacia: FaWarehouse,
  autorizar_farmacia: FaClipboardCheck,
  surtir: FaBoxOpen,
  confirmar_entrega: FaCheck,
  devolver: FaUndo,
  reenviar: FaPaperPlane,
  rechazar: FaTimes,
  cancelar: FaBan,
  marcar_vencida: FaClock,
};

// Estilos de color por tipo de acción
const COLORES_ACCION = {
  blue: 'bg-blue-500 hover:bg-blue-600 text-white',
  green: 'bg-green-500 hover:bg-green-600 text-white',
  cyan: 'bg-cyan-500 hover:bg-cyan-600 text-white',
  indigo: 'bg-indigo-500 hover:bg-indigo-600 text-white',
  violet: 'bg-violet-500 hover:bg-violet-600 text-white',
  amber: 'bg-amber-500 hover:bg-amber-600 text-white',
  red: 'bg-red-500 hover:bg-red-600 text-white',
  gray: 'bg-gray-500 hover:bg-gray-600 text-white',
};

/**
 * Botón individual de acción
 */
const AccionButton = ({ 
  accion, 
  onClick, 
  loading, 
  disabled,
  size = 'md' 
}) => {
  const Icon = ICONOS_ACCION[accion.key] || FaCheck;
  const colorClass = COLORES_ACCION[accion.color] || COLORES_ACCION.gray;
  
  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1.5 text-sm',
    lg: 'px-4 py-2 text-base',
  };
  
  return (
    <button
      onClick={onClick}
      disabled={loading || disabled}
      className={`
        inline-flex items-center gap-1.5 rounded-md font-medium
        transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed
        ${colorClass} ${sizeClasses[size]}
      `}
      title={accion.label}
    >
      {loading ? (
        <FaSpinner className="animate-spin" />
      ) : (
        <Icon className="w-3.5 h-3.5" />
      )}
      <span>{accion.label}</span>
    </button>
  );
};

/**
 * Componente principal que muestra todas las acciones disponibles
 * 
 * @param {string} contexto - 'lista' | 'detalle' - En lista, no se muestra autorizar_farmacia
 *                            porque debe pasar por revisión de cantidades primero
 */
export function RequisicionAcciones({ 
  requisicion, 
  onAccionCompletada,
  onVerHistorial,
  mostrarHistorial = true,
  layout = 'horizontal', // 'horizontal' | 'vertical' | 'dropdown'
  size = 'md',
  contexto = 'detalle', // 'lista' | 'detalle'
}) {
  const { 
    getAccionesDisponibles, 
    ejecutarAccion, 
    loading: hookLoading,
    rolUsuario
  } = useRequisicionFlujo();
  
  const [loadingAccion, setLoadingAccion] = useState(null);
  const [modalData, setModalData] = useState(null); // Para modales de confirmación
  
  // ISS-FIX: Filtrar acciones según contexto
  // En la lista NO mostrar autorizar_farmacia porque requiere revisar cantidades primero
  const acciones = useMemo(() => {
    let accionesDisponibles = getAccionesDisponibles(requisicion);
    
    // En contexto de lista, quitar acciones que requieren revisión previa de cantidades
    if (contexto === 'lista') {
      const accionesExcluidasEnLista = ['autorizar_farmacia'];
      accionesDisponibles = accionesDisponibles.filter(
        a => !accionesExcluidasEnLista.includes(a.key)
      );
    }
    
    return accionesDisponibles;
  }, [requisicion, getAccionesDisponibles, contexto]);
  
  const handleAccion = async (accion, datosExtra = {}) => {
    // Si requiere confirmación o datos adicionales, mostrar modal
    if (accion.requiereFechaRecoleccion && !datosExtra.fecha_recoleccion_limite) {
      setModalData({ accion, tipo: 'fecha_recoleccion' });
      return;
    }
    
    if (accion.requiereMotivo && !datosExtra.motivo) {
      setModalData({ accion, tipo: 'motivo' });
      return;
    }
    
    // ISS-FIX: Lugar de entrega automático = Centro solicitante
    if (accion.requiereLugarEntrega && !datosExtra.lugar_entrega) {
      const nombreCentro = requisicion?.centro?.nombre || requisicion?.centro_nombre || 'Centro Penitenciario';
      datosExtra.lugar_entrega = nombreCentro;
    }
    
    // Ejecutar acción
    setLoadingAccion(accion.key);
    
    try {
      const resultado = await ejecutarAccion(accion.key, requisicion.id, datosExtra);
      toast.success(resultado.mensaje || `${accion.label} completado`);
      
      if (onAccionCompletada) {
        onAccionCompletada(resultado);
      }
    } catch (error) {
      const errorMsg = error.response?.data?.error || error.message || 'Error al ejecutar acción';
      toast.error(errorMsg);
    } finally {
      setLoadingAccion(null);
      setModalData(null);
    }
  };
  
  // Mostrar info cuando no hay acciones disponibles
  if (acciones.length === 0) {
    const estadoActual = requisicion?.estado?.toLowerCase() || 'desconocido';
    const estadosFinales = ['entregada', 'rechazada', 'cancelada', 'vencida'];
    
    if (estadosFinales.includes(estadoActual)) {
      return (
        <div className="text-sm text-gray-500 italic">
          Requisición finalizada ({estadoActual})
        </div>
      );
    }
    
    // Mensaje específico para estado devuelta
    if (estadoActual === 'devuelta') {
      return (
        <div className="text-sm text-amber-600 italic">
          Pendiente de corrección por el médico solicitante
        </div>
      );
    }
    
    // Info para estados intermedios sin acciones para este rol
    return (
      <div className="text-sm text-gray-500 italic">
        Estado: {estadoActual} — En proceso por otro rol
      </div>
    );
  }
  
  const layoutClasses = {
    horizontal: 'flex flex-wrap gap-2',
    vertical: 'flex flex-col gap-2',
    dropdown: 'relative',
  };
  
  return (
    <div className={layoutClasses[layout]}>
      {/* Botón de historial */}
      {mostrarHistorial && onVerHistorial && (
        <button
          onClick={onVerHistorial}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md
            bg-gray-100 hover:bg-gray-200 text-gray-700 transition-colors"
          title="Ver historial de cambios"
        >
          <FaHistory className="w-3.5 h-3.5" />
          <span>Historial</span>
        </button>
      )}
      
      {/* Acciones disponibles */}
      {acciones.map((accion) => (
        <AccionButton
          key={accion.key}
          accion={accion}
          onClick={() => handleAccion(accion)}
          loading={loadingAccion === accion.key}
          disabled={hookLoading || loadingAccion !== null}
          size={size}
        />
      ))}
      
      {/* Modal para datos adicionales */}
      {modalData && (
        <ModalDatosAdicionales
          tipo={modalData.tipo}
          accion={modalData.accion}
          onConfirm={(datos) => handleAccion(modalData.accion, datos)}
          onCancel={() => setModalData(null)}
        />
      )}
    </div>
  );
}

/**
 * Modal para capturar datos adicionales requeridos por algunas acciones
 */
function ModalDatosAdicionales({ tipo, accion, onConfirm, onCancel }) {
  const [valor, setValor] = useState('');
  const [fechaRecoleccion, setFechaRecoleccion] = useState('');
  
  const handleSubmit = (e) => {
    e.preventDefault();
    
    let datos = {};
    
    if (tipo === 'fecha_recoleccion') {
      if (!fechaRecoleccion) {
        toast.error('Debe seleccionar una fecha límite de recolección');
        return;
      }
      datos.fecha_recoleccion_limite = fechaRecoleccion;
      if (valor) datos.observaciones = valor;
    } else if (tipo === 'motivo') {
      if (!valor || valor.trim().length < 10) {
        toast.error('El motivo debe tener al menos 10 caracteres');
        return;
      }
      datos.motivo = valor.trim();
    }
    
    onConfirm(datos);
  };
  
  const getTitulo = () => {
    switch (tipo) {
      case 'fecha_recoleccion':
        return 'Asignar Fecha Límite de Recolección';
      case 'motivo':
        if (accion.key === 'devolver') return 'Motivo de Devolución';
        if (accion.key === 'cancelar') return 'Motivo de Cancelación';
        return 'Motivo de Rechazo';
      default:
        return 'Datos Adicionales';
    }
  };
  
  // ISS-FIX: Obtener etiqueta y placeholder según la acción
  const getMotivoLabel = () => {
    switch (accion.key) {
      case 'devolver': return 'Motivo de devolución *';
      case 'cancelar': return 'Motivo de cancelación *';
      default: return 'Motivo de rechazo *';
    }
  };
  
  const getMotivoPlaceholder = () => {
    switch (accion.key) {
      case 'devolver': return 'Explique por qué se devuelve la requisición...';
      case 'cancelar': return 'Explique por qué cancela esta requisición...';
      default: return 'Explique el motivo del rechazo...';
    }
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md mx-4">
        <h3 className="text-lg font-semibold mb-4">{getTitulo()}</h3>
        
        <form onSubmit={handleSubmit}>
          {tipo === 'fecha_recoleccion' && (
            <>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Fecha y hora límite para recolección *
              </label>
              <input
                type="datetime-local"
                value={fechaRecoleccion}
                onChange={(e) => setFechaRecoleccion(e.target.value)}
                min={new Date().toISOString().slice(0, 16)}
                className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 mb-4"
                required
              />
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Observaciones (opcional)
              </label>
              <textarea
                value={valor}
                onChange={(e) => setValor(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
                placeholder="Notas adicionales..."
              />
            </>
          )}
          
          {tipo === 'motivo' && (
            <>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {getMotivoLabel()}
              </label>
              <textarea
                value={valor}
                onChange={(e) => setValor(e.target.value)}
                rows={4}
                className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
                placeholder={getMotivoPlaceholder()}
                required
                minLength={10}
              />
              <p className="text-xs text-gray-500 mt-1">Mínimo 10 caracteres</p>
            </>
          )}
          
          <div className="flex justify-end gap-3 mt-6">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className={`px-4 py-2 rounded-md text-white ${COLORES_ACCION[accion.color]}`}
            >
              {accion.label}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default RequisicionAcciones;
