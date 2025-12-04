/**
 * ISS-008: UX de lotes vencidos.
 * 
 * Componentes y utilidades para mejorar la experiencia
 * de usuario al manejar lotes vencidos o próximos a vencer.
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { toast } from 'react-hot-toast';

// === CONSTANTES ===

export const ALERTA_CADUCIDAD = {
  VENCIDO: 'vencido',
  CRITICO: 'critico',    // <= 7 días
  PROXIMO: 'proximo',    // <= 30 días
  NORMAL: 'normal'       // > 30 días
};

export const ALERTA_CONFIG = {
  [ALERTA_CADUCIDAD.VENCIDO]: {
    color: 'bg-red-100 text-red-800 border-red-300',
    icon: '⛔',
    label: 'VENCIDO',
    bgClass: 'bg-red-50',
    borderClass: 'border-red-500',
    textClass: 'text-red-700',
    badgeClass: 'bg-red-600 text-white',
    priority: 4
  },
  [ALERTA_CADUCIDAD.CRITICO]: {
    color: 'bg-orange-100 text-orange-800 border-orange-300',
    icon: '⚠️',
    label: 'Crítico',
    bgClass: 'bg-orange-50',
    borderClass: 'border-orange-500',
    textClass: 'text-orange-700',
    badgeClass: 'bg-orange-500 text-white',
    priority: 3
  },
  [ALERTA_CADUCIDAD.PROXIMO]: {
    color: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    icon: '📅',
    label: 'Próximo',
    bgClass: 'bg-yellow-50',
    borderClass: 'border-yellow-400',
    textClass: 'text-yellow-700',
    badgeClass: 'bg-yellow-500 text-white',
    priority: 2
  },
  [ALERTA_CADUCIDAD.NORMAL]: {
    color: 'bg-green-100 text-green-800 border-green-300',
    icon: '✓',
    label: 'Normal',
    bgClass: 'bg-green-50',
    borderClass: 'border-green-400',
    textClass: 'text-green-700',
    badgeClass: 'bg-green-500 text-white',
    priority: 1
  }
};


// === UTILIDADES ===

/**
 * Calcula el nivel de alerta basado en fecha de caducidad.
 * @param {string|Date} fechaCaducidad - Fecha de caducidad
 * @returns {string} Nivel de alerta
 */
export function calcularAlertaCaducidad(fechaCaducidad) {
  if (!fechaCaducidad) return ALERTA_CADUCIDAD.NORMAL;
  
  const fecha = new Date(fechaCaducidad);
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  
  const diasRestantes = Math.ceil((fecha - hoy) / (1000 * 60 * 60 * 24));
  
  if (diasRestantes < 0) return ALERTA_CADUCIDAD.VENCIDO;
  if (diasRestantes <= 7) return ALERTA_CADUCIDAD.CRITICO;
  if (diasRestantes <= 30) return ALERTA_CADUCIDAD.PROXIMO;
  return ALERTA_CADUCIDAD.NORMAL;
}

/**
 * Calcula días restantes hasta caducidad.
 * @param {string|Date} fechaCaducidad - Fecha de caducidad
 * @returns {number} Días restantes (negativo si vencido)
 */
export function diasParaCaducar(fechaCaducidad) {
  if (!fechaCaducidad) return 999;
  
  const fecha = new Date(fechaCaducidad);
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  
  return Math.ceil((fecha - hoy) / (1000 * 60 * 60 * 24));
}

/**
 * Formatea mensaje de caducidad amigable.
 * @param {string|Date} fechaCaducidad - Fecha de caducidad
 * @returns {string} Mensaje formateado
 */
export function formatearMensajeCaducidad(fechaCaducidad) {
  const dias = diasParaCaducar(fechaCaducidad);
  
  if (dias < 0) {
    return `Venció hace ${Math.abs(dias)} día${Math.abs(dias) !== 1 ? 's' : ''}`;
  }
  if (dias === 0) {
    return 'Vence hoy';
  }
  if (dias === 1) {
    return 'Vence mañana';
  }
  if (dias <= 7) {
    return `Vence en ${dias} días`;
  }
  if (dias <= 30) {
    return `Vence en ${dias} días`;
  }
  
  const fecha = new Date(fechaCaducidad);
  return `Vence el ${fecha.toLocaleDateString('es-MX')}`;
}


// === HOOKS ===

/**
 * ISS-008: Hook para manejar alertas de lotes vencidos.
 * @param {Array} lotes - Lista de lotes
 * @param {Object} options - Opciones de configuración
 */
export function useLotesVencidosAlert(lotes, options = {}) {
  const {
    mostrarNotificacion = true,
    autoRefresh = false,
    refreshInterval = 60000 // 1 minuto
  } = options;
  
  const [alertasMostradas, setAlertasMostradas] = useState(new Set());
  
  // Agrupar lotes por nivel de alerta
  const lotesAgrupados = useMemo(() => {
    const grupos = {
      vencidos: [],
      criticos: [],
      proximos: [],
      normales: []
    };
    
    (lotes || []).forEach(lote => {
      const alerta = calcularAlertaCaducidad(lote.fecha_caducidad);
      
      switch (alerta) {
        case ALERTA_CADUCIDAD.VENCIDO:
          grupos.vencidos.push(lote);
          break;
        case ALERTA_CADUCIDAD.CRITICO:
          grupos.criticos.push(lote);
          break;
        case ALERTA_CADUCIDAD.PROXIMO:
          grupos.proximos.push(lote);
          break;
        default:
          grupos.normales.push(lote);
      }
    });
    
    return grupos;
  }, [lotes]);
  
  // Estadísticas
  const estadisticas = useMemo(() => ({
    totalLotes: (lotes || []).length,
    vencidos: lotesAgrupados.vencidos.length,
    criticos: lotesAgrupados.criticos.length,
    proximos: lotesAgrupados.proximos.length,
    normales: lotesAgrupados.normales.length,
    porcentajeRiesgo: (lotes || []).length > 0 
      ? Math.round(
          ((lotesAgrupados.vencidos.length + lotesAgrupados.criticos.length) / 
          (lotes || []).length) * 100
        )
      : 0
  }), [lotes, lotesAgrupados]);
  
  // Mostrar notificaciones de alerta
  useEffect(() => {
    if (!mostrarNotificacion) return;
    
    const nuevosVencidos = lotesAgrupados.vencidos.filter(
      lote => !alertasMostradas.has(`vencido-${lote.id}`)
    );
    
    const nuevosCriticos = lotesAgrupados.criticos.filter(
      lote => !alertasMostradas.has(`critico-${lote.id}`)
    );
    
    if (nuevosVencidos.length > 0) {
      toast.error(
        `⛔ ${nuevosVencidos.length} lote(s) VENCIDO(S) detectado(s)`,
        { duration: 5000 }
      );
      
      nuevosVencidos.forEach(lote => {
        setAlertasMostradas(prev => new Set([...prev, `vencido-${lote.id}`]));
      });
    }
    
    if (nuevosCriticos.length > 0) {
      toast(
        `⚠️ ${nuevosCriticos.length} lote(s) próximo(s) a vencer (≤7 días)`,
        { icon: '⚠️', duration: 4000 }
      );
      
      nuevosCriticos.forEach(lote => {
        setAlertasMostradas(prev => new Set([...prev, `critico-${lote.id}`]));
      });
    }
  }, [lotesAgrupados, mostrarNotificacion, alertasMostradas]);
  
  // Función para verificar si un lote está vencido
  const estaVencido = useCallback((lote) => {
    return calcularAlertaCaducidad(lote?.fecha_caducidad) === ALERTA_CADUCIDAD.VENCIDO;
  }, []);
  
  // Función para verificar si un lote requiere atención
  const requiereAtencion = useCallback((lote) => {
    const alerta = calcularAlertaCaducidad(lote?.fecha_caducidad);
    return alerta === ALERTA_CADUCIDAD.VENCIDO || alerta === ALERTA_CADUCIDAD.CRITICO;
  }, []);
  
  return {
    lotesAgrupados,
    estadisticas,
    estaVencido,
    requiereAtencion,
    hayAlertasCriticas: estadisticas.vencidos > 0 || estadisticas.criticos > 0
  };
}


/**
 * ISS-008: Hook para ordenar lotes priorizando los que requieren atención.
 * @param {Array} lotes - Lista de lotes
 * @param {string} ordenBase - Orden base ('fecha_caducidad' | 'cantidad' | 'producto')
 */
export function useLotesOrdenados(lotes, ordenBase = 'fecha_caducidad') {
  return useMemo(() => {
    if (!lotes || !Array.isArray(lotes)) return [];
    
    return [...lotes].sort((a, b) => {
      const alertaA = ALERTA_CONFIG[calcularAlertaCaducidad(a.fecha_caducidad)].priority;
      const alertaB = ALERTA_CONFIG[calcularAlertaCaducidad(b.fecha_caducidad)].priority;
      
      // Primero por prioridad de alerta (mayor prioridad primero)
      if (alertaA !== alertaB) {
        return alertaB - alertaA;
      }
      
      // Luego por el orden base
      switch (ordenBase) {
        case 'fecha_caducidad':
          return new Date(a.fecha_caducidad) - new Date(b.fecha_caducidad);
        case 'cantidad':
          return a.cantidad_actual - b.cantidad_actual;
        case 'producto':
          return (a.producto?.clave || '').localeCompare(b.producto?.clave || '');
        default:
          return 0;
      }
    });
  }, [lotes, ordenBase]);
}


// === COMPONENTES ===

/**
 * ISS-008: Badge de estado de caducidad.
 */
export function BadgeCaducidad({ fechaCaducidad, showDays = true, className = '' }) {
  const alerta = calcularAlertaCaducidad(fechaCaducidad);
  const config = ALERTA_CONFIG[alerta];
  const dias = diasParaCaducar(fechaCaducidad);
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color} ${className}`}>
      <span className="mr-1">{config.icon}</span>
      {showDays ? (
        dias < 0 ? `Venció hace ${Math.abs(dias)}d` :
        dias === 0 ? 'Vence hoy' :
        dias <= 30 ? `${dias}d restantes` :
        config.label
      ) : config.label}
    </span>
  );
}

/**
 * ISS-008: Indicador visual de alerta para filas de tabla.
 */
export function IndicadorAlertaLote({ lote }) {
  const alerta = calcularAlertaCaducidad(lote?.fecha_caducidad);
  const config = ALERTA_CONFIG[alerta];
  
  if (alerta === ALERTA_CADUCIDAD.NORMAL) return null;
  
  return (
    <div 
      className={`absolute left-0 top-0 bottom-0 w-1 ${config.borderClass.replace('border-', 'bg-')}`}
      title={formatearMensajeCaducidad(lote?.fecha_caducidad)}
    />
  );
}

/**
 * ISS-008: Panel de resumen de lotes por estado.
 */
export function ResumenLotesCaducidad({ estadisticas }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div className="bg-red-50 rounded-lg p-4 border border-red-200">
        <div className="flex items-center">
          <span className="text-2xl mr-2">⛔</span>
          <div>
            <p className="text-sm text-red-600 font-medium">Vencidos</p>
            <p className="text-2xl font-bold text-red-700">{estadisticas.vencidos}</p>
          </div>
        </div>
      </div>
      
      <div className="bg-orange-50 rounded-lg p-4 border border-orange-200">
        <div className="flex items-center">
          <span className="text-2xl mr-2">⚠️</span>
          <div>
            <p className="text-sm text-orange-600 font-medium">Críticos (≤7d)</p>
            <p className="text-2xl font-bold text-orange-700">{estadisticas.criticos}</p>
          </div>
        </div>
      </div>
      
      <div className="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
        <div className="flex items-center">
          <span className="text-2xl mr-2">📅</span>
          <div>
            <p className="text-sm text-yellow-600 font-medium">Próximos (≤30d)</p>
            <p className="text-2xl font-bold text-yellow-700">{estadisticas.proximos}</p>
          </div>
        </div>
      </div>
      
      <div className="bg-green-50 rounded-lg p-4 border border-green-200">
        <div className="flex items-center">
          <span className="text-2xl mr-2">✓</span>
          <div>
            <p className="text-sm text-green-600 font-medium">En orden</p>
            <p className="text-2xl font-bold text-green-700">{estadisticas.normales}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * ISS-008: Modal de confirmación para operaciones con lotes vencidos.
 */
export function ConfirmacionLoteVencido({ 
  lote, 
  accion, 
  onConfirm, 
  onCancel,
  isOpen 
}) {
  if (!isOpen || !lote) return null;
  
  const dias = diasParaCaducar(lote.fecha_caducidad);
  const mensaje = formatearMensajeCaducidad(lote.fecha_caducidad);
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 overflow-hidden">
        <div className="bg-red-50 px-6 py-4 border-b border-red-200">
          <h3 className="text-lg font-semibold text-red-800 flex items-center">
            <span className="mr-2">⚠️</span>
            Advertencia: Lote {dias < 0 ? 'Vencido' : 'Próximo a Vencer'}
          </h3>
        </div>
        
        <div className="px-6 py-4">
          <div className="mb-4">
            <p className="text-gray-700">
              El lote <strong>{lote.numero_lote}</strong> {mensaje.toLowerCase()}.
            </p>
          </div>
          
          <div className="bg-gray-50 rounded-lg p-3 mb-4">
            <dl className="grid grid-cols-2 gap-2 text-sm">
              <dt className="text-gray-500">Producto:</dt>
              <dd className="font-medium">{lote.producto?.descripcion || lote.producto?.clave}</dd>
              <dt className="text-gray-500">Fecha caducidad:</dt>
              <dd className="font-medium">{new Date(lote.fecha_caducidad).toLocaleDateString('es-MX')}</dd>
              <dt className="text-gray-500">Cantidad actual:</dt>
              <dd className="font-medium">{lote.cantidad_actual} unidades</dd>
            </dl>
          </div>
          
          <p className="text-sm text-gray-600">
            ¿Está seguro que desea {accion} este lote?
            {dias < 0 && (
              <span className="block mt-2 text-red-600 font-medium">
                Este producto ya no debería ser utilizado.
              </span>
            )}
          </p>
        </div>
        
        <div className="px-6 py-4 bg-gray-50 flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            onClick={() => onConfirm(lote)}
            className={`px-4 py-2 text-white rounded-lg ${
              dias < 0 
                ? 'bg-red-600 hover:bg-red-700' 
                : 'bg-orange-500 hover:bg-orange-600'
            }`}
          >
            Confirmar {accion}
          </button>
        </div>
      </div>
    </div>
  );
}

export default {
  ALERTA_CADUCIDAD,
  ALERTA_CONFIG,
  calcularAlertaCaducidad,
  diasParaCaducar,
  formatearMensajeCaducidad,
  useLotesVencidosAlert,
  useLotesOrdenados,
  BadgeCaducidad,
  IndicadorAlertaLote,
  ResumenLotesCaducidad,
  ConfirmacionLoteVencido
};
