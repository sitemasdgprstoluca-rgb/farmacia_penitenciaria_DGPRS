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
  FaCheckCircle,
  FaTimesCircle,
  FaExclamationTriangle,
  FaClock,
  FaUser,
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

// ── Normalización de datos ──────────────────────────────────────────────

// Normalizar nombre de módulo para mostrar
const normalizarModulo = (modelo, accion, endpoint) => {
  if (!modelo) return 'Sistema';
  const upper = (modelo || '').toUpperCase().replace(/\s+/g, '_');
  const MAP = {
    PRODUCTOS: 'Productos', PRODUCTO: 'Productos', CORE_PRODUCTO: 'Productos',
    LOTES: 'Lotes', LOTE: 'Lotes', LOTEPARCIALIDAD: 'Parcialidades',
    REQUISICIONES: 'Requisiciones', MOVIMIENTOS: 'Movimientos',
    DONACIONES: 'Donaciones', PACIENTES: 'Pacientes',
    DISPENSACIONES: 'Dispensaciones', CAJA_CHICA: 'Caja Chica',
    CENTROS: 'Centros', USUARIOS: 'Usuarios', USER: 'Usuarios', USUARIO: 'Usuarios',
    CONFIGURACION: 'Configuración', AUTH: 'Sesión',
    NOTIFICACIONES: 'Notificaciones', TEMA: 'Tema', TEMAGLOBAL: 'Tema',
    IMPORTACION: 'Importación', EXPORTACION: 'Exportación',
    REPORTES: 'Reportes', SISTEMA: 'Sistema',
  };
  if (MAP[upper]) return MAP[upper];
  if (upper === 'OTRO') {
    const a = (accion || '').toUpperCase();
    if (['LOGIN', 'LOGOUT', 'CAMBIO_PASSWORD'].includes(a) || a.includes('PASSWORD') || a.includes('RESET')) return 'Sesión';
    if (endpoint) {
      if (endpoint.includes('producto')) return 'Productos';
      if (endpoint.includes('lote')) return 'Lotes';
      if (endpoint.includes('requisicion')) return 'Requisiciones';
      if (endpoint.includes('movimiento')) return 'Movimientos';
      if (endpoint.includes('donacion')) return 'Donaciones';
      if (endpoint.includes('paciente')) return 'Pacientes';
      if (endpoint.includes('dispensacion')) return 'Dispensaciones';
      if (endpoint.includes('caja')) return 'Caja Chica';
      if (endpoint.includes('user')) return 'Usuarios';
      if (endpoint.includes('centro')) return 'Centros';
      if (endpoint.includes('notificacion')) return 'Notificaciones';
      if (endpoint.includes('reporte')) return 'Reportes';
      if (endpoint.includes('tema')) return 'Tema';
    }
    return 'General';
  }
  return modelo.charAt(0).toUpperCase() + modelo.slice(1).toLowerCase();
};

// Normalizar acción para display
const normalizarAccion = (accion) => {
  if (!accion) return 'Acción';
  const MAP = {
    LOGIN: 'Inicio Sesión', LOGOUT: 'Cierre Sesión',
    CREAR: 'Crear', CREATE: 'Crear',
    ACTUALIZAR: 'Actualizar', UPDATE: 'Actualizar', MODIFICAR: 'Modificar',
    ELIMINAR: 'Eliminar', DELETE: 'Eliminar',
    CONSULTAR: 'Consultar', APROBAR: 'Aprobar',
    RECHAZAR: 'Rechazar', CANCELAR: 'Cancelar',
    RECIBIR: 'Recibir', SURTIR: 'Surtir',
    ENVIAR: 'Enviar', IMPORTAR: 'Importar', EXPORTAR: 'Exportar',
    CAMBIO_PASSWORD: 'Cambio Contraseña',
    OVERRIDE_SOBREENTREGA: 'Sobreentrega',
    LIMPIEZA_DATOS: 'Limpieza Datos',
  };
  const upper = accion.toUpperCase();
  return MAP[upper] || accion.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
};

// Categoría de color por acción
const getAccionColor = (accion) => {
  const u = (accion || '').toUpperCase();
  if (['LOGIN', 'CONSULTAR'].includes(u)) return 'blue';
  if (u === 'LOGOUT') return 'slate';
  if (['CREAR', 'CREATE', 'APROBAR'].includes(u) || u.includes('AUTORIZAR') || u.includes('REGISTRAR')) return 'emerald';
  if (['ACTUALIZAR', 'UPDATE', 'MODIFICAR'].includes(u) || u.includes('ACTUALIZAR') || u.includes('CAMBIAR') || u.includes('PASSWORD')) return 'amber';
  if (['ELIMINAR', 'DELETE', 'LIMPIEZA_DATOS', 'RECHAZAR', 'CANCELAR'].includes(u) || u.includes('RECHAZAR')) return 'red';
  if (['ENVIAR', 'SURTIR', 'DISPENSAR', 'RECIBIR', 'DEVOLVER'].includes(u) || u.includes('ENVIAR')) return 'indigo';
  if (['IMPORTAR', 'EXPORTAR'].includes(u)) return 'violet';
  return 'gray';
};

const COLOR_STYLES = {
  blue:    { bg: 'bg-blue-50',    text: 'text-blue-700',    border: 'border-blue-200',    dot: 'bg-blue-500' },
  slate:   { bg: 'bg-slate-50',   text: 'text-slate-600',   border: 'border-slate-200',   dot: 'bg-slate-400' },
  emerald: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', dot: 'bg-emerald-500' },
  amber:   { bg: 'bg-amber-50',   text: 'text-amber-700',   border: 'border-amber-200',   dot: 'bg-amber-500' },
  red:     { bg: 'bg-red-50',     text: 'text-red-700',     border: 'border-red-200',     dot: 'bg-red-500' },
  indigo:  { bg: 'bg-indigo-50',  text: 'text-indigo-700',  border: 'border-indigo-200',  dot: 'bg-indigo-500' },
  violet:  { bg: 'bg-violet-50',  text: 'text-violet-700',  border: 'border-violet-200',  dot: 'bg-violet-500' },
  gray:    { bg: 'bg-gray-50',    text: 'text-gray-600',    border: 'border-gray-200',    dot: 'bg-gray-400' },
};

const getAccionStyle = (accion) => COLOR_STYLES[getAccionColor(accion)] || COLOR_STYLES.gray;

// Formato relativo de tiempo (compacto)
const tiempoRelativo = (fechaStr) => {
  const fecha = new Date(fechaStr);
  const ahora = new Date();
  const diffMs = ahora - fecha;
  const diffMin  = Math.floor(diffMs / 60000);
  const diffHrs  = Math.floor(diffMs / 3600000);
  const diffDias = Math.floor(diffMs / 86400000);
  if (diffMin < 1) return 'Ahora';
  if (diffMin < 60) return `${diffMin}m`;
  if (diffHrs < 24) return `${diffHrs}h`;
  if (diffDias < 7) return `${diffDias}d`;
  return fecha.toLocaleDateString('es-MX', { day: '2-digit', month: 'short' });
};

// Humanizar nombre de campo para mostrar al usuario
const humanizarCampo = (campo) => {
  const MAP = {
    es_controlado: 'Controlado', nombre: 'Nombre', descripcion: 'Descripción',
    precio: 'Precio', stock: 'Stock', cantidad: 'Cantidad', estado: 'Estado',
    activo: 'Activo', leida: 'Leída', fecha: 'Fecha', usuario: 'Usuario',
    centro: 'Centro', lote: 'Lote', producto: 'Producto', observaciones: 'Observaciones',
    motivo: 'Motivo', tipo: 'Tipo', prioridad: 'Prioridad', monto: 'Monto',
    access: 'Token de acceso', refresh: 'Token de refresco',
    presentacion: 'Presentación', concentracion: 'Concentración',
    principio_activo: 'Principio activo', codigo_barras: 'Código de barras',
    fecha_caducidad: 'Fecha de caducidad', fecha_entrada: 'Fecha entrada',
    cantidad_disponible: 'Cantidad disponible', unidad_medida: 'Unidad de medida',
    numero_lote: 'Número de lote', clave_medicamento: 'Clave medicamento',
    rol_usuario: 'Rol de usuario', is_active: 'Activo', is_staff: 'Staff',
    is_superuser: 'Super Admin', first_name: 'Nombre', last_name: 'Apellido',
    email: 'Correo electrónico', username: 'Usuario',
    // Campos de contexto de requisición
    folio: 'Folio', centro_origen: 'Centro Origen', centro_destino: 'Centro Destino',
    solicitante: 'Solicitante', estado_anterior: 'Estado Anterior', estado_nuevo: 'Estado Nuevo',
    autorizo_admin_centro: 'Autorizó Admin Centro', autorizo_director: 'Autorizó Director',
    recibio_farmacia: 'Recibió Farmacia', autorizo_farmacia: 'Autorizó Farmacia',
    surtio: 'Surtió', lugar_entrega: 'Lugar de Entrega', fecha_entrega: 'Fecha Entrega',
    firma_recepcion: 'Firma Recepción', fecha_surtido: 'Fecha Surtido',
    motivo_rechazo: 'Motivo Rechazo', motivo_devolucion: 'Motivo Devolución',
    motivo_vencimiento: 'Motivo Vencimiento', fecha_limite: 'Fecha Límite',
    autorizador: 'Autorizador', total_productos: 'Total Productos',
  };
  return MAP[campo] || campo.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
};

// Humanizar un valor para mostrar al usuario (ocultar tokens, booleans)
const humanizarValor = (valor) => {
  if (valor === null || valor === undefined) return '—';
  if (valor === true || valor === 'true' || valor === 'True') return 'Sí';
  if (valor === false || valor === 'false' || valor === 'False') return 'No';
  const str = String(valor);
  // Ocultar tokens JWT o cadenas muy largas (>60 chars)
  if (str.length > 60 && (str.includes('eyJ') || str.includes('Token'))) return '(token generado)';
  if (str.length > 80) return str.slice(0, 60) + '…';
  return str;
};

// Descripción legible y específica del evento
const descripcionEvento = (evento) => {
  const { accion, modelo, objeto_repr, datos_nuevos, datos_anteriores, cambios_resumen } = evento;
  const upper = (accion || '').toUpperCase();
  const mod = normalizarModulo(modelo, accion, evento.endpoint);

  // Sesión
  if (upper === 'LOGIN') return 'Inició sesión en el sistema';
  if (upper === 'LOGOUT') return 'Cerró sesión del sistema';
  if (upper === 'CAMBIO_PASSWORD' || upper.includes('PASSWORD')) return 'Cambió su contraseña';

  // Requisiciones: Descripción enriquecida con contexto completo
  if (upper.startsWith('CAMBIAR_ESTADO') && datos_nuevos?.folio) {
    const d = datos_nuevos;
    const ESTADOS_LEGIBLES = {
      pendiente_admin: 'Pendiente Admin', pendiente_director: 'Pendiente Director',
      enviada: 'Enviada', en_revision: 'En Revisión', autorizada: 'Autorizada',
      en_surtido: 'En Surtido', surtida: 'Surtida', entregada: 'Entregada',
      rechazada: 'Rechazada', devuelta: 'Devuelta', vencida: 'Vencida', cancelada: 'Cancelada',
    };
    const from = ESTADOS_LEGIBLES[d.estado_anterior] || d.estado_anterior || '?';
    const to = ESTADOS_LEGIBLES[d.estado_nuevo] || d.estado_nuevo || '?';
    let desc = `Requisición ${d.folio}: ${from} → ${to}`;
    if (d.centro_origen) desc += ` · De: ${d.centro_origen}`;
    if (d.total_productos) desc += ` · ${d.total_productos} producto(s)`;
    return desc;
  }

  // Cambios específicos con resumen
  if (cambios_resumen && cambios_resumen.length > 0) {
    const items = cambios_resumen.slice(0, 2).map(c =>
      `${humanizarCampo(c.campo)}: ${humanizarValor(c.antes)} → ${humanizarValor(c.despues)}`
    );
    const extra = cambios_resumen.length > 2 ? ` y ${cambios_resumen.length - 2} más` : '';
    const prefix = objeto_repr ? `${objeto_repr} — ` : '';
    return `${prefix}${items.join(', ')}${extra}`;
  }

  // Datos nuevos con contexto
  if (datos_nuevos && typeof datos_nuevos === 'object') {
    const keys = Object.keys(datos_nuevos).filter(k => !['access', 'refresh', 'token'].includes(k));
    // Para notificaciones
    if (mod === 'Notificaciones') {
      if (datos_nuevos.leida !== undefined) return `Marcó notificación como ${datos_nuevos.leida ? 'leída' : 'no leída'}`;
      return `Generó una notificación`;
    }
    // Para creación/actualización con muchos campos
    if (keys.length > 5) {
      const nombre = datos_nuevos.nombre || datos_nuevos.descripcion || objeto_repr || '';
      const verbo = ['CREAR', 'CREATE'].includes(upper) ? 'Creó' : 'Modificó';
      return nombre ? `${verbo} ${mod.toLowerCase()}: ${nombre}` : `${verbo} ${keys.length} campos en ${mod}`;
    }
    if (keys.length > 0 && keys.length <= 5) {
      const items = keys.slice(0, 2).map(k => `${humanizarCampo(k)}: ${humanizarValor(datos_nuevos[k])}`);
      const extra = keys.length > 2 ? ` y ${keys.length - 2} más` : '';
      return items.join(', ') + extra;
    }
    // Solo tiene tokens (login/refresh)
    if (Object.keys(datos_nuevos).some(k => ['access', 'refresh'].includes(k))) {
      return 'Renovó token de sesión';
    }
  }

  if (objeto_repr) return objeto_repr;

  return `${normalizarAccion(accion)} en ${mod}`;
};

// Badge de resultado con colores
const ResultadoBadge = ({ resultado }) => {
  const config = {
    success: { bg: 'bg-green-100', text: 'text-green-800', icon: FaCheckCircle, label: 'Exitoso' },
    fail: { bg: 'bg-red-100', text: 'text-red-800', icon: FaTimesCircle, label: 'Fallido' },
    error: { bg: 'bg-red-100', text: 'text-red-800', icon: FaExclamationTriangle, label: 'Error' },
    warning: { bg: 'bg-yellow-100', text: 'text-yellow-800', icon: FaExclamationTriangle, label: 'Alerta' },
  };
  const style = config[resultado] || config.success;
  const Icon = style.icon;
  
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${style.bg} ${style.text}`}>
      <Icon className="w-3 h-3 mr-1" />
      {style.label}
    </span>
  );
};

// Modal de detalle del evento — versión mejorada para responsabilidad
const DetalleModal = ({ evento, onClose }) => {
  if (!evento) return null;

  const aStyle = getAccionStyle(evento.accion);

  // Calcular campos cambiados desde datos_anteriores vs datos_nuevos
  const computedChanges = (() => {
    if (evento.cambios_resumen && evento.cambios_resumen.length > 0) return evento.cambios_resumen;
    const ant = evento.datos_anteriores || {};
    const nue = evento.datos_nuevos || {};
    const allKeys = new Set([...Object.keys(ant), ...Object.keys(nue)]);
    const changes = [];
    allKeys.forEach((k) => {
      const a = ant[k], b = nue[k];
      if (JSON.stringify(a) !== JSON.stringify(b) && b !== undefined) {
        changes.push({ campo: k, antes: a ?? null, despues: b });
      }
    });
    return changes;
  })();

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-start justify-center min-h-screen px-3 py-6 sm:p-0 sm:items-center">
        <div className="fixed inset-0 transition-opacity bg-gray-900/60 backdrop-blur-sm" onClick={onClose} />
        
        <div className="relative w-full max-w-3xl mx-auto bg-white rounded-xl shadow-2xl overflow-hidden">
          {/* Header rojo */}
          <div className="bg-gradient-to-r from-red-700 to-red-500 px-5 py-4 flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white">
                Detalle del Evento #{evento.id}
              </h3>
              <p className="text-xs text-white/80 mt-0.5">
                {new Date(evento.fecha).toLocaleString('es-MX', { dateStyle: 'full', timeStyle: 'medium' })}
                {' · '}{tiempoRelativo(evento.fecha)}
              </p>
            </div>
            <button onClick={onClose} className="text-white/80 hover:text-white p-1.5 rounded-md hover:bg-white/20 transition-colors">
              <FaTimes className="w-5 h-5" />
            </button>
          </div>

          <div className="p-5 space-y-5 max-h-[75vh] overflow-y-auto">
            {/* Resumen del evento en lenguaje natural */}
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <p className="text-sm font-medium text-amber-900">
                <span className="font-bold">{evento.usuario_nombre || 'Sistema'}</span>
                {evento.rol_usuario ? <span className="text-amber-700"> ({evento.rol_usuario})</span> : ''}
                {' realizó '}
                <span className="font-bold">{normalizarAccion(evento.accion).toLowerCase()}</span>
                {' en '}
                <span className="font-bold">{normalizarModulo(evento.modelo, evento.accion, evento.endpoint)}</span>
                {evento.centro_nombre ? <span className="text-amber-700"> — Centro: {evento.centro_nombre}</span> : ''}
              </p>
              <p className="text-xs text-amber-600 mt-1">{descripcionEvento(evento)}</p>
            </div>

            {/* Quién y resultado */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Usuario</p>
                <p className="text-sm font-semibold text-gray-800">{evento.usuario_nombre || 'Sistema'}</p>
                <p className="text-[11px] text-gray-400">{evento.usuario_username || '—'}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Rol</p>
                <p className="text-sm font-semibold text-gray-800">{evento.rol_usuario || '—'}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Centro</p>
                <p className="text-sm font-semibold text-gray-800 truncate" title={evento.centro_nombre}>{evento.centro_nombre || 'Sin centro'}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Resultado</p>
                <ResultadoBadge resultado={evento.resultado} />
              </div>
            </div>

            {/* Qué hizo - con badge de acción */}
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-[10px] uppercase tracking-wider text-gray-400 mb-2">¿Qué hizo?</p>
              <div className="flex items-center gap-3 flex-wrap">
                <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold border ${aStyle.bg} ${aStyle.text} ${aStyle.border}`}>
                  {normalizarAccion(evento.accion)}
                </span>
                <span className="text-sm text-gray-600">
                  en <span className="font-semibold">{normalizarModulo(evento.modelo, evento.accion, evento.endpoint)}</span>
                  {evento.objeto_id && /^\d+$/.test(evento.objeto_id) ? <> — <span className="text-xs bg-gray-200 px-1.5 py-0.5 rounded">Registro #{evento.objeto_id}</span></> : ''}
                </span>
              </div>
              {evento.objeto_repr && (
                <p className="text-xs text-gray-500 mt-2">Elemento: {evento.objeto_repr}</p>
              )}
            </div>

            {/* ============ SECCIÓN ESPECIAL: Contexto de Requisición ============ */}
            {(evento.accion || '').startsWith('cambiar_estado') && evento.datos_nuevos?.folio ? (() => {
              const d = evento.datos_nuevos;
              const productos = Array.isArray(d.productos) ? d.productos : [];
              // Campos informativos (no mostrar en diff)
              const CAMPOS_CONTEXTO = [
                'folio', 'centro_origen', 'centro_destino', 'solicitante',
                'autorizo_admin_centro', 'autorizo_director', 'recibio_farmacia',
                'autorizo_farmacia', 'surtio', 'lugar_entrega', 'fecha_entrega',
                'firma_recepcion', 'fecha_surtido', 'motivo_rechazo', 'motivo_devolucion',
                'motivo_vencimiento', 'fecha_limite', 'autorizador', 'total_productos', 'productos',
              ];
              const actores = [
                { label: 'Solicitante', val: d.solicitante },
                { label: 'Autorizó Admin Centro', val: d.autorizo_admin_centro },
                { label: 'Autorizó Director', val: d.autorizo_director },
                { label: 'Recibió Farmacia', val: d.recibio_farmacia },
                { label: 'Autorizó Farmacia', val: d.autorizo_farmacia },
                { label: 'Surtió', val: d.surtio },
                { label: 'Firma Recepción', val: d.firma_recepcion },
              ].filter(a => a.val);

              // Campos restantes no cubiertos por la vista especial
              const camposExtra = computedChanges.filter(c => !CAMPOS_CONTEXTO.includes(c.campo) && c.campo !== 'estado_anterior' && c.campo !== 'estado_nuevo');

              return (
                <>
                  {/* Transición de estado */}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <p className="text-[10px] uppercase tracking-wider text-blue-400 mb-2">Transición de Estado — Requisición</p>
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className="text-sm font-bold bg-white border border-blue-200 px-3 py-1 rounded-lg text-blue-800">
                        {d.folio}
                      </span>
                      <span className="inline-flex items-center gap-2 text-sm">
                        <span className="px-2 py-0.5 rounded bg-red-100 text-red-700 font-semibold">{d.estado_anterior || '—'}</span>
                        <FaArrowRight className="w-3 h-3 text-gray-400" />
                        <span className="px-2 py-0.5 rounded bg-green-100 text-green-700 font-semibold">{d.estado_nuevo || '—'}</span>
                      </span>
                    </div>
                  </div>

                  {/* Info de la Requisición */}
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-gray-400 mb-2">Datos de la Requisición</p>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      {d.centro_origen && (
                        <div className="bg-gray-50 rounded-lg p-3">
                          <p className="text-[10px] uppercase text-gray-400">Centro Origen</p>
                          <p className="text-sm font-semibold text-gray-800">{d.centro_origen}</p>
                        </div>
                      )}
                      {d.centro_destino && (
                        <div className="bg-gray-50 rounded-lg p-3">
                          <p className="text-[10px] uppercase text-gray-400">Centro Destino</p>
                          <p className="text-sm font-semibold text-gray-800">{d.centro_destino}</p>
                        </div>
                      )}
                      {d.lugar_entrega && (
                        <div className="bg-gray-50 rounded-lg p-3">
                          <p className="text-[10px] uppercase text-gray-400">Lugar Entrega</p>
                          <p className="text-sm font-semibold text-gray-800">{d.lugar_entrega}</p>
                        </div>
                      )}
                      {d.fecha_entrega && (
                        <div className="bg-gray-50 rounded-lg p-3">
                          <p className="text-[10px] uppercase text-gray-400">Fecha Entrega</p>
                          <p className="text-sm font-semibold text-gray-800">{d.fecha_entrega}</p>
                        </div>
                      )}
                      {d.fecha_surtido && (
                        <div className="bg-gray-50 rounded-lg p-3">
                          <p className="text-[10px] uppercase text-gray-400">Fecha Surtido</p>
                          <p className="text-sm font-semibold text-gray-800">{d.fecha_surtido}</p>
                        </div>
                      )}
                      {d.fecha_limite && (
                        <div className="bg-gray-50 rounded-lg p-3">
                          <p className="text-[10px] uppercase text-gray-400">Fecha Límite</p>
                          <p className="text-sm font-semibold text-red-700">{d.fecha_limite}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Motivo rechazo/devolución/vencimiento */}
                  {(d.motivo_rechazo || d.motivo_devolucion || d.motivo_vencimiento) && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                      <p className="text-[10px] uppercase tracking-wider text-red-400 mb-1">
                        {d.motivo_rechazo ? 'Motivo de Rechazo' : d.motivo_devolucion ? 'Motivo de Devolución' : 'Motivo de Vencimiento'}
                      </p>
                      <p className="text-sm text-red-800">{d.motivo_rechazo || d.motivo_devolucion || d.motivo_vencimiento}</p>
                    </div>
                  )}

                  {/* Actores del flujo */}
                  {actores.length > 0 && (
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-gray-400 mb-2">Participantes del Flujo ({actores.length})</p>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {actores.map((a, i) => (
                          <div key={i} className="bg-indigo-50 border border-indigo-100 rounded-lg p-2.5">
                            <p className="text-[10px] uppercase text-indigo-400">{a.label}</p>
                            <p className="text-xs font-semibold text-indigo-800">{a.val}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Tabla de productos */}
                  {productos.length > 0 && (
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-gray-400 mb-2">Productos ({productos.length})</p>
                      <div className="border border-gray-200 rounded-lg overflow-hidden">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="bg-gray-50">
                              <th className="text-left px-3 py-2 text-gray-500 font-medium">#</th>
                              <th className="text-left px-3 py-2 text-gray-500 font-medium">Producto</th>
                              <th className="text-right px-3 py-2 text-gray-500 font-medium">Solicitada</th>
                              <th className="text-right px-3 py-2 text-gray-500 font-medium">Autorizada</th>
                              <th className="text-right px-3 py-2 text-gray-500 font-medium">Surtida</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100">
                            {productos.map((p, i) => (
                              <tr key={i} className="hover:bg-gray-50/50">
                                <td className="px-3 py-1.5 text-gray-400">{i + 1}</td>
                                <td className="px-3 py-1.5 font-medium text-gray-700">{p.producto}</td>
                                <td className="px-3 py-1.5 text-right text-gray-600">{p.solicitada ?? '—'}</td>
                                <td className="px-3 py-1.5 text-right text-blue-600">{p.autorizada ?? '—'}</td>
                                <td className="px-3 py-1.5 text-right text-green-600 font-semibold">{p.surtida ?? '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Campos extra no cubiertos por la vista especial */}
                  {camposExtra.length > 0 && (
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-gray-400 mb-2">Otros Cambios ({camposExtra.length})</p>
                      <div className="border border-gray-200 rounded-lg overflow-hidden">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="bg-gray-50">
                              <th className="text-left px-3 py-2 text-gray-500 font-medium w-1/4">Campo</th>
                              <th className="text-left px-3 py-2 text-red-400 font-medium">Anterior</th>
                              <th className="w-6"></th>
                              <th className="text-left px-3 py-2 text-green-500 font-medium">Nuevo</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100">
                            {camposExtra.map((ch, idx) => (
                              <tr key={idx} className="hover:bg-gray-50/50">
                                <td className="px-3 py-2 font-medium text-gray-700">{humanizarCampo(ch.campo)}</td>
                                <td className="px-3 py-2 text-red-600 bg-red-50/40 break-all">
                                  {ch.antes !== null && ch.antes !== undefined ? humanizarValor(ch.antes) : <span className="italic text-gray-300">vacío</span>}
                                </td>
                                <td className="text-center text-gray-300"><FaArrowRight className="w-3 h-3 mx-auto" /></td>
                                <td className="px-3 py-2 text-green-700 bg-green-50/40 break-all">
                                  {ch.despues !== null && ch.despues !== undefined ? humanizarValor(ch.despues) : <span className="italic text-gray-300">vacío</span>}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </>
              );
            })() : (
              <>
                {/* Cambios Detectados — tabla visual (genérica) */}
                {computedChanges.length > 0 && (
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-gray-400 mb-2">¿Qué cambió? ({computedChanges.length} {computedChanges.length === 1 ? 'campo' : 'campos'})</p>
                    <div className="border border-gray-200 rounded-lg overflow-hidden">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="bg-gray-50">
                            <th className="text-left px-3 py-2 text-gray-500 font-medium w-1/4">Campo</th>
                            <th className="text-left px-3 py-2 text-red-400 font-medium">Valor Anterior</th>
                            <th className="w-6"></th>
                            <th className="text-left px-3 py-2 text-green-500 font-medium">Valor Nuevo</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {computedChanges.map((ch, idx) => (
                            <tr key={idx} className="hover:bg-gray-50/50">
                              <td className="px-3 py-2 font-medium text-gray-700">{humanizarCampo(ch.campo)}</td>
                              <td className="px-3 py-2 text-red-600 bg-red-50/40 break-all">
                                {ch.antes !== null && ch.antes !== undefined ? humanizarValor(ch.antes) : <span className="italic text-gray-300">vacío</span>}
                              </td>
                              <td className="text-center text-gray-300"><FaArrowRight className="w-3 h-3 mx-auto" /></td>
                              <td className="px-3 py-2 text-green-700 bg-green-50/40 break-all">
                                {ch.despues !== null && ch.despues !== undefined ? humanizarValor(ch.despues) : <span className="italic text-gray-300">vacío</span>}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Datos before/after en crudo (si no hubo cambios computados) */}
                {computedChanges.length === 0 && (evento.datos_anteriores || evento.datos_nuevos) && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {evento.datos_anteriores && Object.keys(evento.datos_anteriores).length > 0 && (
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-red-400 mb-1">Datos Anteriores</p>
                        <pre className="p-3 bg-red-50 rounded-lg text-[11px] overflow-auto max-h-48 text-red-800">
                          {JSON.stringify(evento.datos_anteriores, null, 2)}
                        </pre>
                      </div>
                    )}
                    {evento.datos_nuevos && Object.keys(evento.datos_nuevos).length > 0 && (
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-green-500 mb-1">Datos Nuevos</p>
                        <pre className="p-3 bg-green-50 rounded-lg text-[11px] overflow-auto max-h-48 text-green-800">
                          {JSON.stringify(evento.datos_nuevos, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}

            {/* Contexto Técnico */}
            <div>
              <p className="text-[10px] uppercase tracking-wider text-gray-400 mb-2">Información de Conexión</p>
              <div className="bg-gray-50 rounded-lg p-3 grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                <div>
                  <span className="text-gray-400">Dirección IP:</span>{' '}
                  <span className="font-mono text-gray-700">{evento.ip_address || '—'}</span>
                </div>
                <div>
                  <span className="text-gray-400">Tipo solicitud:</span>{' '}
                  <span className="font-mono text-gray-700">{evento.metodo_http || '—'}</span>
                </div>
                <div>
                  <span className="text-gray-400">Código respuesta:</span>{' '}
                  <span className={`font-mono ${(evento.status_code || 0) >= 400 ? 'text-red-600 font-bold' : 'text-green-600'}`}>
                    {evento.status_code || '—'}
                  </span>
                </div>
                <div className="col-span-2 sm:col-span-3">
                  <span className="text-gray-400">Ruta del sistema:</span>{' '}
                  <span className="text-[11px] bg-gray-200/60 px-1.5 py-0.5 rounded text-gray-700 break-all">{evento.endpoint || '—'}</span>
                </div>
                {evento.request_id && (
                  <div className="col-span-2 sm:col-span-3">
                    <span className="text-gray-400">ID de solicitud:</span>{' '}
                    <span className="text-[11px] text-gray-600 break-all">{evento.request_id}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Navegador */}
            {evento.user_agent && (
              <div className="text-[11px] text-gray-400 bg-gray-50 rounded-lg p-2 break-all">
                <span className="font-medium text-gray-500">Navegador:</span> {evento.user_agent}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="border-t px-5 py-3 flex justify-end bg-gray-50">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
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

      {/* Tabla de Eventos — DESKTOP (5 columnas compactas) */}
      <div className="hidden lg:block bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="w-[100px] px-2 py-2.5 text-left text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Cuándo</th>
              <th className="w-[120px] px-2 py-2.5 text-left text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Quién</th>
              <th className="w-[150px] px-2 py-2.5 text-left text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Acción</th>
              <th className="px-2 py-2.5 text-left text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Descripción</th>
              <th className="w-[52px] px-1 py-2.5"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr>
                <td colSpan="5" className="px-4 py-10 text-center">
                  <FaSync className="w-6 h-6 animate-spin text-gray-300 mx-auto" />
                  <p className="mt-2 text-xs text-gray-400">Cargando eventos...</p>
                </td>
              </tr>
            ) : eventos.length === 0 ? (
              <tr>
                <td colSpan="5" className="px-4 py-10 text-center text-gray-400 text-xs">
                  Sin eventos para los filtros seleccionados
                </td>
              </tr>
            ) : (
              eventos.map((evento) => {
                const style = getAccionStyle(evento.accion);
                const modulo = normalizarModulo(evento.modelo, evento.accion, evento.endpoint);
                const accionLabel = normalizarAccion(evento.accion);
                const desc = descripcionEvento(evento);
                const esError = evento.resultado === 'fail' || evento.resultado === 'error';
                return (
                  <tr key={evento.id} className={`hover:bg-gray-50/60 transition-colors ${esError ? 'bg-red-50/30' : ''}`}>
                    {/* Cuándo */}
                    <td className="px-2 py-1.5 align-top">
                      <p className="text-[11px] font-medium text-gray-700 whitespace-nowrap">
                        {new Date(evento.fecha).toLocaleDateString('es-MX', { day: '2-digit', month: '2-digit', year: '2-digit' })}
                        {' '}
                        <span className="text-gray-400">
                          {new Date(evento.fecha).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </p>
                      <p className="text-[10px] text-gray-400">{tiempoRelativo(evento.fecha)}</p>
                    </td>
                    {/* Quién */}
                    <td className="px-2 py-1.5 align-top">
                      <p className="text-[11px] font-medium text-gray-800 truncate" title={evento.usuario_nombre}>
                        {evento.usuario_nombre || 'Sistema'}
                      </p>
                      <p className="text-[10px] text-gray-400 truncate" title={evento.rol_usuario}>
                        {evento.rol_usuario || '—'}
                      </p>
                    </td>
                    {/* Acción + Módulo */}
                    <td className="px-2 py-1.5 align-top">
                      <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold border leading-tight ${style.bg} ${style.text} ${style.border}`}>
                        {accionLabel}
                      </span>
                      <p className="text-[10px] text-gray-500 mt-0.5 truncate" title={modulo}>
                        {modulo}{evento.objeto_id && /^\d+$/.test(evento.objeto_id) ? ` #${evento.objeto_id}` : ''}
                      </p>
                    </td>
                    {/* Descripción */}
                    <td className="px-2 py-1.5 align-top">
                      <p className="text-[11px] text-gray-600 line-clamp-2" title={desc}>{desc}</p>
                    </td>
                    {/* Estado + Ver */}
                    <td className="px-1 py-1.5 align-top">
                      <div className="flex items-center gap-1 justify-center">
                        <span className={`w-2 h-2 rounded-full shrink-0 ${esError ? 'bg-red-500' : 'bg-green-500'}`}
                              title={evento.resultado} />
                        <button
                          onClick={() => verDetalle(evento)}
                          className="p-1 text-gray-400 hover:text-institucional-600 hover:bg-institucional-50 rounded transition-colors"
                          title="Ver detalle"
                        >
                          <FaEye className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>

        {/* Paginación desktop */}
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

      {/* Listado de Eventos — MOBILE / TABLET (<lg) */}
      <div className="lg:hidden space-y-3">
        {loading ? (
          <div className="flex flex-col items-center py-10">
            <FaSync className="w-7 h-7 animate-spin text-gray-300" />
            <p className="mt-2 text-sm text-gray-400">Cargando eventos...</p>
          </div>
        ) : eventos.length === 0 ? (
          <p className="text-center text-gray-400 text-sm py-10">Sin eventos</p>
        ) : (
          eventos.map((evento) => {
            const style = getAccionStyle(evento.accion);
            const modulo = normalizarModulo(evento.modelo, evento.accion, evento.endpoint);
            const accionLabel = normalizarAccion(evento.accion);
            const desc = descripcionEvento(evento);
            return (
              <div
                key={evento.id}
                className="bg-white rounded-lg shadow-sm border border-gray-100 p-4 space-y-2"
              >
                {/* Top row: fecha + badges */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <FaClock className="w-3 h-3" />
                    {new Date(evento.fecha).toLocaleString('es-MX', {
                      day: '2-digit', month: '2-digit', year: '2-digit',
                      hour: '2-digit', minute: '2-digit',
                    })}
                    <span className="text-gray-300">·</span>
                    <span className="text-gray-400">{tiempoRelativo(evento.fecha)}</span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <ResultadoBadge resultado={evento.resultado} />
                    <button
                      onClick={() => verDetalle(evento)}
                      className="p-1 text-institucional-500 hover:bg-institucional-50 rounded"
                    >
                      <FaEye className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Usuario */}
                <div className="flex items-center gap-2 text-sm">
                  <FaUser className="w-3.5 h-3.5 text-gray-300" />
                  <span className="font-medium text-gray-800">{evento.usuario_nombre || 'Sistema'}</span>
                  <span className="text-xs text-gray-400">{evento.rol_usuario || ''}</span>
                </div>

                {/* Acción + módulo */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${style.bg} ${style.text} ${style.border}`}>
                    {accionLabel}
                  </span>
                  <span className="text-xs text-gray-500 flex items-center gap-1">
                    <FaBox className="w-3 h-3 text-gray-300" /> {modulo}
                    {evento.objeto_id && /^\d+$/.test(evento.objeto_id) ? ` #${evento.objeto_id}` : ''}
                  </span>
                </div>

                {/* Descripción */}
                {desc && (
                  <p className="text-xs text-gray-500 bg-gray-50 rounded px-2 py-1 line-clamp-2">{desc}</p>
                )}
              </div>
            );
          })
        )}

        {/* Paginación mobile */}
        <div className="flex items-center justify-between bg-white rounded-lg shadow-sm border border-gray-100 p-3">
          <p className="text-xs text-gray-500">
            {eventos.length} de {totalItems.toLocaleString()}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-2 py-1 text-xs border border-gray-300 rounded disabled:opacity-40 hover:bg-gray-50"
            >
              Ant
            </button>
            <span className="text-xs text-gray-500">{page}/{totalPages}</span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-2 py-1 text-xs border border-gray-300 rounded disabled:opacity-40 hover:bg-gray-50"
            >
              Sig
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
