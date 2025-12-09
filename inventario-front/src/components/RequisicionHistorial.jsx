/**
 * FLUJO V2: Componente para mostrar el historial de cambios de estado
 * 
 * Muestra una línea de tiempo con todos los cambios de estado,
 * usuarios responsables y fechas.
 */

import { useState, useEffect } from 'react';
import { requisicionesAPI } from '../services/api';
import { formatters } from '../constants';
import { EstadoBadge } from './EstadoBadge';
import { 
  FaHistory, 
  FaUser, 
  FaCalendar, 
  FaArrowRight,
  FaSpinner,
  FaTimes,
  FaInfoCircle
} from 'react-icons/fa';

/**
 * Componente de historial de requisición
 */
export function RequisicionHistorial({ 
  requisicionId, 
  onClose,
  isModal = true 
}) {
  const [historial, setHistorial] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const cargarHistorial = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await requisicionesAPI.getHistorial(requisicionId);
        setHistorial(response.data);
      } catch (err) {
        setError(err.response?.data?.error || 'Error al cargar historial');
      } finally {
        setLoading(false);
      }
    };
    
    if (requisicionId) {
      cargarHistorial();
    }
  }, [requisicionId]);
  
  const contenido = (
    <div className="p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <FaHistory className="text-gray-500" />
          <h3 className="text-lg font-semibold">
            Historial de Cambios
          </h3>
          {historial && (
            <span className="text-sm text-gray-500">
              ({historial.total_cambios} cambios)
            </span>
          )}
        </div>
        {isModal && onClose && (
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <FaTimes className="w-5 h-5 text-gray-500" />
          </button>
        )}
      </div>
      
      {/* Información de la requisición */}
      {historial && (
        <div className="flex items-center gap-4 mb-6 p-3 bg-gray-50 rounded-lg">
          <span className="font-medium">{historial.folio}</span>
          <span className="text-gray-400">→</span>
          <span className="text-sm text-gray-600">Estado actual:</span>
          <EstadoBadge estado={historial.estado_actual} />
        </div>
      )}
      
      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <FaSpinner className="animate-spin text-blue-500 w-8 h-8" />
        </div>
      )}
      
      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}
      
      {/* Timeline */}
      {historial && historial.historial && (
        <div className="relative">
          {/* Línea vertical */}
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />
          
          {/* Eventos */}
          <div className="space-y-6">
            {historial.historial.map((evento, index) => (
              <div key={evento.id} className="relative flex gap-4">
                {/* Punto en la línea */}
                <div className={`
                  relative z-10 w-8 h-8 rounded-full flex items-center justify-center
                  ${index === historial.historial.length - 1 
                    ? 'bg-blue-500 text-white' 
                    : 'bg-white border-2 border-gray-300'
                  }
                `}>
                  <span className="text-xs font-medium">
                    {historial.historial.length - index}
                  </span>
                </div>
                
                {/* Contenido del evento */}
                <div className="flex-1 pb-4">
                  <div className="bg-white border rounded-lg p-4 shadow-sm">
                    {/* Transición de estados */}
                    <div className="flex items-center gap-2 mb-2">
                      {evento.estado_anterior && (
                        <>
                          <EstadoBadge estado={evento.estado_anterior} />
                          <FaArrowRight className="text-gray-400 w-3 h-3" />
                        </>
                      )}
                      <EstadoBadge estado={evento.estado_nuevo} />
                    </div>
                    
                    {/* Acción */}
                    <div className="text-sm font-medium text-gray-700 mb-2">
                      {evento.accion_display}
                    </div>
                    
                    {/* Metadata */}
                    <div className="flex flex-wrap gap-4 text-xs text-gray-500">
                      <div className="flex items-center gap-1">
                        <FaUser className="w-3 h-3" />
                        <span>{evento.usuario || 'Sistema'}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <FaCalendar className="w-3 h-3" />
                        <span>{formatters.datetime(evento.fecha_cambio)}</span>
                      </div>
                    </div>
                    
                    {/* Motivo u observaciones */}
                    {(evento.motivo || evento.observaciones) && (
                      <div className="mt-3 p-2 bg-gray-50 rounded text-sm text-gray-600">
                        <div className="flex items-start gap-2">
                          <FaInfoCircle className="w-4 h-4 text-gray-400 mt-0.5" />
                          <span>{evento.motivo || evento.observaciones}</span>
                        </div>
                      </div>
                    )}
                    
                    {/* Datos adicionales */}
                    {evento.datos_adicionales && Object.keys(evento.datos_adicionales).length > 0 && (
                      <details className="mt-2">
                        <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">
                          Ver detalles técnicos
                        </summary>
                        <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-auto">
                          {JSON.stringify(evento.datos_adicionales, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Sin historial */}
      {historial && (!historial.historial || historial.historial.length === 0) && (
        <div className="text-center py-12 text-gray-500">
          <FaHistory className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p>No hay cambios registrados</p>
        </div>
      )}
    </div>
  );
  
  if (isModal) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-auto">
          {contenido}
        </div>
      </div>
    );
  }
  
  return contenido;
}

export default RequisicionHistorial;
