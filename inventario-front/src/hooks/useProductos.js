/**
 * ISS-001 FIX: Hook para gestión de productos
 * Extrae lógica de negocio de Productos.jsx para mejor mantenibilidad
 * 
 * Este hook centraliza:
 * - Carga y paginación de productos
 * - Filtros y búsqueda
 * - CRUD de productos
 * - Cálculo de niveles de stock
 */
import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { toast } from 'react-hot-toast';
import { productosAPI } from '../services/api';
import { getStockProducto } from '../utils/dtoContracts';
import { validarProducto, normalizarProducto } from '../utils/validation';

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
 * Niveles de stock disponibles para filtrar
 */
export const NIVELES_STOCK = [
  { value: '', label: 'Todos los niveles' },
  { value: 'sin_stock', label: 'Sin Stock', color: 'red' },
  { value: 'critico', label: 'Crítico', color: 'orange' },
  { value: 'bajo', label: 'Bajo', color: 'yellow' },
  { value: 'normal', label: 'Normal', color: 'green' },
  { value: 'alto', label: 'Alto', color: 'blue' },
];

/**
 * Calcula el nivel de stock de un producto
 * @param {Object} producto - Producto a evaluar
 * @returns {string} Nivel de stock
 */
export const calcularNivelStock = (producto) => {
  const inventario = getStockProducto(producto);
  const minimo = Number(producto.stock_minimo) || 0;
  
  if (inventario <= 0) return 'sin_stock';
  
  if (minimo <= 0) {
    if (inventario < 25) return 'bajo';
    if (inventario < 100) return 'normal';
    return 'alto';
  }
  
  const ratio = inventario / minimo;
  if (ratio < 0.5) return 'critico';
  if (ratio < 1) return 'bajo';
  if (ratio <= 2) return 'normal';
  return 'alto';
};

/**
 * Normaliza texto para búsqueda (quita acentos, minúsculas)
 */
const normalizeText = (text) =>
  text
    ? text
        .toString()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
    : '';

/**
 * Hook principal para gestión de productos
 * @param {Object} options - Opciones de configuración
 * @param {number} options.pageSize - Tamaño de página (default: 20)
 * @param {boolean} options.autoLoad - Cargar al montar (default: true)
 * @returns {Object} Estado y métodos del hook
 */
export const useProductos = (options = {}) => {
  const { pageSize = 20, autoLoad = true } = options;

  // Estado de productos
  const [productos, setProductos] = useState([]);
  const [loadState, setLoadState] = useState(LOAD_STATES.IDLE);
  const [error, setError] = useState(null);

  // Paginación
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);

  // Filtros
  const [filters, setFilters] = useState({
    search: '',
    categoria: '',
    nivelStock: '',
    activo: 'true', // 'true', 'false', ''
  });

  // Ref para cancelar peticiones
  const abortControllerRef = useRef(null);

  /**
   * Carga productos con filtros actuales
   */
  const fetchProductos = useCallback(async (overrideFilters = null) => {
    // Cancelar petición anterior
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

      if (currentFilters.search) {
        params.search = currentFilters.search;
      }
      if (currentFilters.categoria) {
        params.categoria = currentFilters.categoria;
      }
      if (currentFilters.activo !== '') {
        params.activo = currentFilters.activo;
      }

      // ISS-SEC FIX: Pass AbortController signal to cancel stale requests
      const response = await productosAPI.getAll(params, {
        signal: abortControllerRef.current.signal
      });
      
      let data = response.data;
      let items = [];
      let total = 0;

      // Manejar respuesta paginada o array directo
      if (Array.isArray(data)) {
        items = data;
        total = data.length;
      } else if (data.results) {
        items = data.results;
        total = data.count || items.length;
      } else if (data.data) {
        items = data.data;
        total = data.total || items.length;
      }

      // Aplicar filtro de nivel de stock en cliente (si backend no lo soporta)
      if (currentFilters.nivelStock) {
        items = items.filter(p => calcularNivelStock(p) === currentFilters.nivelStock);
        total = items.length;
      }

      setProductos(items);
      setTotalItems(total);
      setTotalPages(Math.ceil(total / pageSize));
      setLoadState(LOAD_STATES.SUCCESS);

    } catch (err) {
      if (err.name === 'AbortError') {
        return; // Petición cancelada, ignorar
      }
      
      console.error('[useProductos] Error:', err);
      setError(err.message || 'Error al cargar productos');
      setLoadState(LOAD_STATES.ERROR);
      
      if (err.response?.status !== 401) {
        toast.error('Error al cargar productos');
      }
    }
  }, [page, pageSize, filters]);

  /**
   * Actualiza filtros y recarga
   */
  const updateFilters = useCallback((newFilters) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
    setPage(1); // Reset a primera página
  }, []);

  /**
   * Crea un nuevo producto
   */
  const crearProducto = useCallback(async (data) => {
    const { valido, errores, primerError } = validarProducto(data, false);
    
    if (!valido) {
      toast.error(primerError || 'Datos inválidos');
      return { success: false, errores };
    }

    try {
      const normalized = normalizarProducto(data);
      const response = await productosAPI.create(normalized);
      toast.success('Producto creado exitosamente');
      await fetchProductos();
      return { success: true, data: response.data };
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 
                       err.response?.data?.message ||
                       'Error al crear producto';
      toast.error(errorMsg);
      return { success: false, error: errorMsg };
    }
  }, [fetchProductos]);

  /**
   * Actualiza un producto existente
   */
  const actualizarProducto = useCallback(async (id, data) => {
    const { valido, errores, primerError } = validarProducto(data, true);
    
    if (!valido) {
      toast.error(primerError || 'Datos inválidos');
      return { success: false, errores };
    }

    try {
      const normalized = normalizarProducto(data);
      const response = await productosAPI.update(id, normalized);
      toast.success('Producto actualizado exitosamente');
      
      // Actualizar en lista local
      setProductos(prev => prev.map(p => 
        p.id === id ? { ...p, ...response.data } : p
      ));
      
      return { success: true, data: response.data };
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 
                       err.response?.data?.message ||
                       'Error al actualizar producto';
      toast.error(errorMsg);
      return { success: false, error: errorMsg };
    }
  }, []);

  /**
   * Elimina un producto
   */
  const eliminarProducto = useCallback(async (id) => {
    try {
      await productosAPI.delete(id);
      toast.success('Producto eliminado');
      
      // Remover de lista local
      setProductos(prev => prev.filter(p => p.id !== id));
      setTotalItems(prev => prev - 1);
      
      return { success: true };
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Error al eliminar producto';
      toast.error(errorMsg);
      return { success: false, error: errorMsg };
    }
  }, []);

  /**
   * Cambia el estado activo de un producto
   */
  const toggleActivo = useCallback(async (id, nuevoEstado) => {
    try {
      await productosAPI.update(id, { activo: nuevoEstado });
      
      setProductos(prev => prev.map(p => 
        p.id === id ? { ...p, activo: nuevoEstado } : p
      ));
      
      toast.success(nuevoEstado ? 'Producto activado' : 'Producto desactivado');
      return { success: true };
    } catch (err) {
      toast.error('Error al cambiar estado');
      return { success: false };
    }
  }, []);

  /**
   * Búsqueda de productos
   */
  const buscar = useCallback((termino) => {
    updateFilters({ search: termino });
  }, [updateFilters]);

  /**
   * Productos filtrados por búsqueda local (para filtrado rápido)
   */
  const productosFiltrados = useMemo(() => {
    if (!filters.search) return productos;
    
    const searchNorm = normalizeText(filters.search);
    return productos.filter(p => {
      const nombre = normalizeText(p.nombre);
      const clave = normalizeText(p.clave);
      const sustancia = normalizeText(p.sustancia_activa);
      
      return nombre.includes(searchNorm) ||
             clave.includes(searchNorm) ||
             sustancia.includes(searchNorm);
    });
  }, [productos, filters.search]);

  /**
   * Estadísticas rápidas
   */
  const estadisticas = useMemo(() => {
    const stats = {
      total: productos.length,
      activos: 0,
      sinStock: 0,
      critico: 0,
      bajo: 0,
      normal: 0,
      alto: 0,
    };

    productos.forEach(p => {
      if (p.activo) stats.activos++;
      const nivel = calcularNivelStock(p);
      if (nivel === 'sin_stock') stats.sinStock++;
      else if (nivel === 'critico') stats.critico++;
      else if (nivel === 'bajo') stats.bajo++;
      else if (nivel === 'normal') stats.normal++;
      else if (nivel === 'alto') stats.alto++;
    });

    return stats;
  }, [productos]);

  // Cargar al montar si autoLoad está habilitado
  useEffect(() => {
    if (autoLoad) {
      fetchProductos();
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
      fetchProductos();
    }
  }, [page, filters]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    // Estado
    productos,
    productosFiltrados,
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
    buscar,
    
    // CRUD
    crearProducto,
    actualizarProducto,
    eliminarProducto,
    toggleActivo,
    refetch: fetchProductos,
    
    // Estadísticas
    estadisticas,
    
    // Helpers
    calcularNivelStock,
  };
};

export default useProductos;
