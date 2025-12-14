/**
 * ISS-002 FIX: Hook para sincronizar catálogos con el backend
 * Obtiene unidades, categorías y otros catálogos de la API
 * Incluye fallbacks locales para cuando el endpoint no esté disponible
 * 
 * NOTA: Los fallbacks deben coincidir con backend/core/constants.py
 */
import { useState, useEffect, useCallback } from 'react';
import { catalogosAPI } from '../services/api';

// Fallbacks locales - ALINEADOS con backend/core/constants.py
// Si modificas estos valores, actualiza también el backend
const FALLBACK_UNIDADES = [
  'PIEZA',
  'CAJA',
  'FRASCO',
  'SOBRE',
  'AMPOLLETA',
  'TABLETA',
  'CAPSULA',
  'ML',
  'GR',
];

const FALLBACK_CATEGORIAS = [
  'medicamento',
  'material_curacion',
  'insumo',
  'equipo',
  'otro',
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
  // Flujo V2 - estados jerárquicos (alineado con backend)
  'borrador',
  'pendiente_admin',
  'pendiente_director',
  'enviada',
  'en_revision',
  'autorizada',
  'en_surtido',
  'surtida',
  'entregada',
  'rechazada',
  'vencida',
  'cancelada',
  'devuelta',
  'parcial',  // Legacy - surtido parcial
];

const FALLBACK_TIPOS_MOVIMIENTO = [
  'entrada',
  'salida',
  'transferencia',
  'ajuste_positivo',
  'ajuste_negativo',
  'devolucion',
  'merma',
  'caducidad',
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

      // ISS-002 FIX: Normalizar respuesta del backend
      // El backend puede enviar [{value, label}] o [string]
      // Siempre extraer solo los values para compatibilidad con formularios
      const normalizar = (arr) => {
        if (!arr || !Array.isArray(arr)) return null;
        // Si es array de objetos, extraer value; si es array de strings, usar directo
        return arr.map(item => typeof item === 'object' ? item.value : item);
      };

      const nuevosCatalogos = {
        unidades: normalizar(data?.unidades_medida) || normalizar(data?.unidades) || FALLBACK_UNIDADES,
        categorias: normalizar(data?.categorias) || FALLBACK_CATEGORIAS,
        viasAdministracion: normalizar(data?.vias_administracion) || FALLBACK_VIAS_ADMINISTRACION,
        estadosRequisicion: normalizar(data?.estados_requisicion) || FALLBACK_ESTADOS_REQUISICION,
        tiposMovimiento: normalizar(data?.tipos_movimiento) || FALLBACK_TIPOS_MOVIMIENTO,
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

        // ISS-002 FIX: Normalizar respuestas individuales también
        const normalizarResultado = (resultado, fallback) => {
          if (resultado.status !== 'fulfilled') return fallback;
          const data = resultado.value.data;
          // Extraer del objeto {catalogo_key: [...]} si viene así
          const arr = Array.isArray(data) ? data : Object.values(data)[0];
          if (!arr || !Array.isArray(arr)) return fallback;
          return arr.map(item => typeof item === 'object' ? item.value : item);
        };

        const nuevosCatalogos = {
          unidades: normalizarResultado(resultados[0], FALLBACK_UNIDADES),
          categorias: normalizarResultado(resultados[1], FALLBACK_CATEGORIAS),
          viasAdministracion: normalizarResultado(resultados[2], FALLBACK_VIAS_ADMINISTRACION),
          estadosRequisicion: normalizarResultado(resultados[3], FALLBACK_ESTADOS_REQUISICION),
          tiposMovimiento: normalizarResultado(resultados[4], FALLBACK_TIPOS_MOVIMIENTO),
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
