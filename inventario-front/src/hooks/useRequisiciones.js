/**
 * ISS-001 FIX: Hook para gestión de requisiciones
 * Extrae lógica de negocio de Requisiciones.jsx para mejor mantenibilidad
 * 
 * Este hook centraliza:
 * - Carga y paginación de requisiciones
 * - Filtros por estado, fechas, solicitante
 * - Transiciones de estado
 * - Validaciones de negocio
 */
import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { toast } from 'react-hot-toast';
import { requisicionesAPI } from '../services/api';
import { normalizarRequisicion, ESTADOS_REQUISICION } from '../utils/dtoContracts';
import { 
  esTransicionValida, 
  obtenerSiguienteEstado,
  obtenerAccionesPermitidas,
  ACCIONES_REQUISICION,
} from './useRequisicionEstado';

/**
 * Estados de carga posibles
 */
export const LOAD_STATES = {
  IDLE: 'idle',
  LOADING: 'loading',
  SUCCESS: 'success',
  ERROR: 'error',
};

/**
 * Hook principal para gestión de requisiciones
 * @param {Object} options - Opciones de configuración
 * @param {number} options.pageSize - Tamaño de página (default: 20)
 * @param {boolean} options.autoLoad - Cargar al montar (default: true)
 * @param {Object} options.permisos - Permisos del usuario actual
 * @returns {Object} Estado y métodos del hook
 */
export const useRequisiciones = (options = {}) => {
  const { pageSize = 20, autoLoad = true, permisos = {} } = options;

  // Estado de requisiciones
  const [requisiciones, setRequisiciones] = useState([]);
  const [loadState, setLoadState] = useState(LOAD_STATES.IDLE);
  const [error, setError] = useState(null);

  // Requisición seleccionada para detalle
  const [selectedRequisicion, setSelectedRequisicion] = useState(null);

  // Paginación
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);

  // Filtros
  const [filters, setFilters] = useState({
    search: '',
    estado: '',
    fechaDesde: '',
    fechaHasta: '',
    solicitante: '',
    centro: '',
  });

  // Ref para cancelar peticiones
  const abortControllerRef = useRef(null);

  /**
   * Carga requisiciones con filtros actuales
   */
  const fetchRequisiciones = useCallback(async (overrideFilters = null) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setLoadState(LOAD_STATES.LOADING);
    setError(null);

    const currentFilters = overrideFilters || filters;

    try {
      const params = {
        page,
        page_size: pageSize,
      };

      if (currentFilters.search) params.search = currentFilters.search;
      if (currentFilters.estado) params.estado = currentFilters.estado;
      if (currentFilters.fechaDesde) params.fecha_desde = currentFilters.fechaDesde;
      if (currentFilters.fechaHasta) params.fecha_hasta = currentFilters.fechaHasta;
      if (currentFilters.solicitante) params.solicitante = currentFilters.solicitante;
      if (currentFilters.centro) params.centro = currentFilters.centro;

      const response = await requisicionesAPI.getAll(params);
      
      let data = response.data;
      let items = [];
      let total = 0;

      if (Array.isArray(data)) {
        items = data.map(normalizarRequisicion);
        total = data.length;
      } else if (data.results) {
        items = data.results.map(normalizarRequisicion);
        total = data.count || items.length;
      }

      setRequisiciones(items);
      setTotalItems(total);
      setTotalPages(Math.ceil(total / pageSize));
      setLoadState(LOAD_STATES.SUCCESS);

    } catch (err) {
      if (err.name === 'AbortError') return;
      
      console.error('[useRequisiciones] Error:', err);
      setError(err.message || 'Error al cargar requisiciones');
      setLoadState(LOAD_STATES.ERROR);
      
      if (err.response?.status !== 401) {
        toast.error('Error al cargar requisiciones');
      }
    }
  }, [page, pageSize, filters]);

  /**
   * Carga detalle de una requisición
   */
  const fetchDetalleRequisicion = useCallback(async (id) => {
    try {
      const response = await requisicionesAPI.getById(id);
      const requisicion = normalizarRequisicion(response.data);
      setSelectedRequisicion(requisicion);
      return { success: true, data: requisicion };
    } catch (err) {
      toast.error('Error al cargar detalle de requisición');
      return { success: false, error: err.message };
    }
  }, []);

  /**
   * Actualiza filtros y recarga
   */
  const updateFilters = useCallback((newFilters) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
    setPage(1);
  }, []);

  /**
   * Ejecuta una transición de estado
   */
  const ejecutarTransicion = useCallback(async (requisicionId, accion, datos = {}) => {
    // Buscar requisición
    const requisicion = requisiciones.find(r => r.id === requisicionId) || selectedRequisicion;
    
    if (!requisicion) {
      toast.error('Requisición no encontrada');
      return { success: false, error: 'Requisición no encontrada' };
    }

    // Validar que la transición sea válida
    if (!esTransicionValida(requisicion.estado, accion)) {
      toast.error(`No se puede ${accion} una requisición en estado ${requisicion.estado}`);
      return { success: false, error: 'Transición no válida' };
    }

    const nuevoEstado = obtenerSiguienteEstado(requisicion.estado, accion);

    try {
      let response;

      switch (accion) {
        case ACCIONES_REQUISICION.ENVIAR:
          response = await requisicionesAPI.enviar(requisicionId);
          break;
        case ACCIONES_REQUISICION.APROBAR:
          response = await requisicionesAPI.aprobar(requisicionId, datos);
          break;
        case ACCIONES_REQUISICION.RECHAZAR:
          response = await requisicionesAPI.rechazar(requisicionId, datos);
          break;
        case ACCIONES_REQUISICION.SURTIR:
          response = await requisicionesAPI.surtir(requisicionId, datos);
          break;
        case ACCIONES_REQUISICION.SURTIR_PARCIAL:
          response = await requisicionesAPI.surtirParcial(requisicionId, datos);
          break;
        case ACCIONES_REQUISICION.CANCELAR:
          response = await requisicionesAPI.cancelar(requisicionId, datos);
          break;
        default:
          throw new Error(`Acción desconocida: ${accion}`);
      }

      // Actualizar en lista local
      if (nuevoEstado) {
        setRequisiciones(prev => prev.map(r => 
          r.id === requisicionId ? { ...r, estado: nuevoEstado } : r
        ));

        if (selectedRequisicion?.id === requisicionId) {
          setSelectedRequisicion(prev => ({ ...prev, estado: nuevoEstado }));
        }
      }

      toast.success(`Requisición ${accion} exitosamente`);
      return { success: true, data: response?.data };

    } catch (err) {
      const errorMsg = err.response?.data?.detail || 
                       err.response?.data?.message ||
                       `Error al ${accion} requisición`;
      toast.error(errorMsg);
      return { success: false, error: errorMsg };
    }
  }, [requisiciones, selectedRequisicion]);

  /**
   * Enviar requisición (borrador -> pendiente)
   */
  const enviarRequisicion = useCallback((id) => {
    return ejecutarTransicion(id, ACCIONES_REQUISICION.ENVIAR);
  }, [ejecutarTransicion]);

  /**
   * Aprobar requisición
   */
  const aprobarRequisicion = useCallback((id, observaciones) => {
    return ejecutarTransicion(id, ACCIONES_REQUISICION.APROBAR, { observaciones });
  }, [ejecutarTransicion]);

  /**
   * Rechazar requisición
   */
  const rechazarRequisicion = useCallback((id, motivo) => {
    return ejecutarTransicion(id, ACCIONES_REQUISICION.RECHAZAR, { motivo });
  }, [ejecutarTransicion]);

  /**
   * Surtir requisición completa
   */
  const surtirRequisicion = useCallback((id, detallesSurtido) => {
    return ejecutarTransicion(id, ACCIONES_REQUISICION.SURTIR, { detalles: detallesSurtido });
  }, [ejecutarTransicion]);

  /**
   * Cancelar requisición
   */
  const cancelarRequisicion = useCallback((id, motivo) => {
    return ejecutarTransicion(id, ACCIONES_REQUISICION.CANCELAR, { motivo });
  }, [ejecutarTransicion]);

  /**
   * Crear nueva requisición
   */
  const crearRequisicion = useCallback(async (datos) => {
    try {
      const response = await requisicionesAPI.create(datos);
      toast.success('Requisición creada exitosamente');
      await fetchRequisiciones();
      return { success: true, data: normalizarRequisicion(response.data) };
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Error al crear requisición';
      toast.error(errorMsg);
      return { success: false, error: errorMsg };
    }
  }, [fetchRequisiciones]);

  /**
   * Actualizar requisición (solo en borrador)
   */
  const actualizarRequisicion = useCallback(async (id, datos) => {
    const requisicion = requisiciones.find(r => r.id === id);
    
    if (requisicion && requisicion.estado !== ESTADOS_REQUISICION.BORRADOR) {
      toast.error('Solo se pueden editar requisiciones en borrador');
      return { success: false, error: 'No editable' };
    }

    try {
      const response = await requisicionesAPI.update(id, datos);
      
      setRequisiciones(prev => prev.map(r => 
        r.id === id ? normalizarRequisicion(response.data) : r
      ));
      
      toast.success('Requisición actualizada');
      return { success: true, data: response.data };
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Error al actualizar';
      toast.error(errorMsg);
      return { success: false, error: errorMsg };
    }
  }, [requisiciones]);

  /**
   * Eliminar requisición (solo borradores)
   */
  const eliminarRequisicion = useCallback(async (id) => {
    const requisicion = requisiciones.find(r => r.id === id);
    
    if (requisicion && requisicion.estado !== ESTADOS_REQUISICION.BORRADOR) {
      toast.error('Solo se pueden eliminar requisiciones en borrador');
      return { success: false, error: 'No eliminable' };
    }

    try {
      await requisicionesAPI.delete(id);
      setRequisiciones(prev => prev.filter(r => r.id !== id));
      setTotalItems(prev => prev - 1);
      toast.success('Requisición eliminada');
      return { success: true };
    } catch (err) {
      toast.error('Error al eliminar requisición');
      return { success: false };
    }
  }, [requisiciones]);

  /**
   * Obtiene acciones permitidas para una requisición
   */
  const getAccionesPermitidas = useCallback((requisicion) => {
    if (!requisicion) return [];
    return obtenerAccionesPermitidas(requisicion.estado, permisos, {
      esCreador: requisicion.solicitante_id === permisos.userId,
    });
  }, [permisos]);

  /**
   * Estadísticas por estado
   */
  const estadisticas = useMemo(() => {
    const stats = {
      total: requisiciones.length,
      [ESTADOS_REQUISICION.BORRADOR]: 0,
      [ESTADOS_REQUISICION.PENDIENTE]: 0,
      [ESTADOS_REQUISICION.APROBADA]: 0,
      [ESTADOS_REQUISICION.EN_PROCESO]: 0,
      [ESTADOS_REQUISICION.SURTIDA_PARCIAL]: 0,
      [ESTADOS_REQUISICION.SURTIDA]: 0,
      [ESTADOS_REQUISICION.RECHAZADA]: 0,
      [ESTADOS_REQUISICION.CANCELADA]: 0,
    };

    requisiciones.forEach(r => {
      if (stats[r.estado] !== undefined) {
        stats[r.estado]++;
      }
    });

    return stats;
  }, [requisiciones]);

  // Cargar al montar
  useEffect(() => {
    if (autoLoad) {
      fetchRequisiciones();
    }

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [autoLoad]); // eslint-disable-line react-hooks/exhaustive-deps

  // Recargar cuando cambian filtros o página
  useEffect(() => {
    if (loadState !== LOAD_STATES.IDLE) {
      fetchRequisiciones();
    }
  }, [page, filters]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    // Estado
    requisiciones,
    selectedRequisicion,
    loadState,
    isLoading: loadState === LOAD_STATES.LOADING,
    error,
    
    // Paginación
    page,
    totalPages,
    totalItems,
    setPage,
    
    // Filtros
    filters,
    updateFilters,
    
    // Selección
    setSelectedRequisicion,
    fetchDetalleRequisicion,
    
    // CRUD
    crearRequisicion,
    actualizarRequisicion,
    eliminarRequisicion,
    refetch: fetchRequisiciones,
    
    // Transiciones
    enviarRequisicion,
    aprobarRequisicion,
    rechazarRequisicion,
    surtirRequisicion,
    cancelarRequisicion,
    ejecutarTransicion,
    getAccionesPermitidas,
    
    // Estadísticas
    estadisticas,
    
    // Constantes exportadas para uso en componentes
    ESTADOS: ESTADOS_REQUISICION,
    ACCIONES: ACCIONES_REQUISICION,
  };
};

export default useRequisiciones;
