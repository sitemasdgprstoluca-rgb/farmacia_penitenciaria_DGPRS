/**
 * ISS-002 FIX: Hook para sincronizar catálogos con el backend
 * Obtiene unidades, categorías y otros catálogos de la API
 * Incluye fallbacks locales para cuando el endpoint no esté disponible
 */
import { useState, useEffect, useCallback } from 'react';
import { catalogosAPI } from '../services/api';

// Fallbacks locales - Se usan si el endpoint no está disponible
const FALLBACK_UNIDADES = [
  'AMPOLLETA',
  'CAJA',
  'CAPSULA',
  'FRASCO',
  'GR',
  'ML',
  'PIEZA',
  'SOBRE',
  'TABLETA',
];

const FALLBACK_CATEGORIAS = [
  'medicamento',
  'material_curacion',
  'equipo_medico',
  'insumo',
];

const FALLBACK_VIAS_ADMINISTRACION = [
  'ORAL',
  'INTRAVENOSA',
  'INTRAMUSCULAR',
  'SUBCUTANEA',
  'TOPICA',
  'INHALATORIA',
  'RECTAL',
  'OFTALMICA',
  'OTICA',
  'NASAL',
];

const FALLBACK_ESTADOS_REQUISICION = [
  'borrador',
  'pendiente',
  'aprobada',
  'en_proceso',
  'surtida_parcial',
  'surtida',
  'rechazada',
  'cancelada',
];

const FALLBACK_TIPOS_MOVIMIENTO = [
  'entrada',
  'salida',
  'ajuste',
  'transferencia',
  'merma',
  'devolucion',
];

// Cache global para evitar múltiples llamadas
let catalogosCache = null;
let catalogosCacheTime = 0;
const CACHE_TTL = 5 * 60 * 1000; // 5 minutos

/**
 * Hook para obtener catálogos del backend
 * @param {Object} options - Opciones de configuración
 * @param {boolean} options.autoLoad - Cargar automáticamente al montar (default: true)
 * @param {boolean} options.useCache - Usar cache global (default: true)
 * @returns {Object} - { catalogos, loading, error, refetch, isFromFallback }
 */
export const useCatalogos = (options = {}) => {
  const { autoLoad = true, useCache = true } = options;

  const [catalogos, setCatalogos] = useState({
    unidades: FALLBACK_UNIDADES,
    categorias: FALLBACK_CATEGORIAS,
    viasAdministracion: FALLBACK_VIAS_ADMINISTRACION,
    estadosRequisicion: FALLBACK_ESTADOS_REQUISICION,
    tiposMovimiento: FALLBACK_TIPOS_MOVIMIENTO,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isFromFallback, setIsFromFallback] = useState(true);

  const fetchCatalogos = useCallback(async (forceRefresh = false) => {
    // Verificar cache si está habilitado
    if (useCache && !forceRefresh && catalogosCache) {
      const now = Date.now();
      if (now - catalogosCacheTime < CACHE_TTL) {
        setCatalogos(catalogosCache);
        setIsFromFallback(false);
        return catalogosCache;
      }
    }

    setLoading(true);
    setError(null);

    try {
      // Intentar obtener todos los catálogos en una sola llamada
      const response = await catalogosAPI.getAll();
      const data = response.data;

      const nuevosCatalogos = {
        unidades: data?.unidades_medida || data?.unidades || FALLBACK_UNIDADES,
        categorias: data?.categorias || FALLBACK_CATEGORIAS,
        viasAdministracion: data?.vias_administracion || FALLBACK_VIAS_ADMINISTRACION,
        estadosRequisicion: data?.estados_requisicion || FALLBACK_ESTADOS_REQUISICION,
        tiposMovimiento: data?.tipos_movimiento || FALLBACK_TIPOS_MOVIMIENTO,
      };

      // Actualizar cache
      catalogosCache = nuevosCatalogos;
      catalogosCacheTime = Date.now();

      setCatalogos(nuevosCatalogos);
      setIsFromFallback(false);
      return nuevosCatalogos;
    } catch (err) {
      // Si el endpoint no existe (404), usar fallbacks silenciosamente
      if (err.response?.status === 404) {
        console.info('[Catálogos] Endpoint no disponible, usando valores locales');
        setIsFromFallback(true);
        return catalogos;
      }

      // Para otros errores, intentar cargar catálogos individualmente
      console.warn('[Catálogos] Error al cargar catálogos, intentando carga individual:', err.message);
      
      try {
        const resultados = await Promise.allSettled([
          catalogosAPI.unidadesMedida(),
          catalogosAPI.categorias(),
          catalogosAPI.viasAdministracion(),
          catalogosAPI.estadosRequisicion(),
          catalogosAPI.tiposMovimiento(),
        ]);

        const nuevosCatalogos = {
          unidades: resultados[0].status === 'fulfilled' 
            ? resultados[0].value.data 
            : FALLBACK_UNIDADES,
          categorias: resultados[1].status === 'fulfilled' 
            ? resultados[1].value.data 
            : FALLBACK_CATEGORIAS,
          viasAdministracion: resultados[2].status === 'fulfilled' 
            ? resultados[2].value.data 
            : FALLBACK_VIAS_ADMINISTRACION,
          estadosRequisicion: resultados[3].status === 'fulfilled' 
            ? resultados[3].value.data 
            : FALLBACK_ESTADOS_REQUISICION,
          tiposMovimiento: resultados[4].status === 'fulfilled' 
            ? resultados[4].value.data 
            : FALLBACK_TIPOS_MOVIMIENTO,
        };

        // Actualizar cache si al menos uno tuvo éxito
        const algunoExitoso = resultados.some(r => r.status === 'fulfilled');
        if (algunoExitoso) {
          catalogosCache = nuevosCatalogos;
          catalogosCacheTime = Date.now();
          setIsFromFallback(false);
        }

        setCatalogos(nuevosCatalogos);
        return nuevosCatalogos;
      } catch (innerErr) {
        console.error('[Catálogos] Error en carga individual:', innerErr);
        setError('Error al cargar catálogos del servidor');
        setIsFromFallback(true);
        return catalogos;
      }
    } finally {
      setLoading(false);
    }
  }, [useCache, catalogos]);

  useEffect(() => {
    if (autoLoad) {
      fetchCatalogos();
    }
  }, [autoLoad]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    catalogos,
    loading,
    error,
    refetch: fetchCatalogos,
    isFromFallback,
    // Acceso directo a cada catálogo
    unidades: catalogos.unidades,
    categorias: catalogos.categorias,
    viasAdministracion: catalogos.viasAdministracion,
    estadosRequisicion: catalogos.estadosRequisicion,
    tiposMovimiento: catalogos.tiposMovimiento,
  };
};

/**
 * Función para invalidar el cache de catálogos
 * Útil cuando se modifica un catálogo desde admin
 */
export const invalidarCacheCatalogos = () => {
  catalogosCache = null;
  catalogosCacheTime = 0;
};

/**
 * Función para obtener catálogos sin usar hook
 * Útil para validaciones fuera de componentes
 */
export const getCatalogosSync = () => {
  if (catalogosCache) {
    return { catalogos: catalogosCache, isFromFallback: false };
  }
  return {
    catalogos: {
      unidades: FALLBACK_UNIDADES,
      categorias: FALLBACK_CATEGORIAS,
      viasAdministracion: FALLBACK_VIAS_ADMINISTRACION,
      estadosRequisicion: FALLBACK_ESTADOS_REQUISICION,
      tiposMovimiento: FALLBACK_TIPOS_MOVIMIENTO,
    },
    isFromFallback: true,
  };
};

export default useCatalogos;
