/**
 * ISS-034: Memoización de gráficos.
 * 
 * Hooks y utilidades para optimizar el rendimiento
 * de gráficos y visualizaciones en el dashboard.
 */

import { useMemo, useCallback, useRef, useEffect, useState } from 'react';

// === UTILIDADES DE CACHE ===

/**
 * Cache LRU simple para datos de gráficos.
 */
class LRUCache {
  constructor(maxSize = 50) {
    this.maxSize = maxSize;
    this.cache = new Map();
  }

  get(key) {
    if (!this.cache.has(key)) return undefined;
    
    // Mover al final (más reciente)
    const value = this.cache.get(key);
    this.cache.delete(key);
    this.cache.set(key, value);
    return value;
  }

  set(key, value) {
    if (this.cache.has(key)) {
      this.cache.delete(key);
    } else if (this.cache.size >= this.maxSize) {
      // Eliminar el más antiguo (primero)
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
    this.cache.set(key, value);
  }

  has(key) {
    return this.cache.has(key);
  }

  clear() {
    this.cache.clear();
  }

  size() {
    return this.cache.size;
  }
}

// Cache global para datos de gráficos
const chartDataCache = new LRUCache(100);

/**
 * Genera una clave de cache basada en parámetros.
 */
function generateCacheKey(prefix, params) {
  const sortedParams = Object.keys(params)
    .sort()
    .map(k => `${k}:${JSON.stringify(params[k])}`)
    .join('|');
  return `${prefix}:${sortedParams}`;
}


// === HOOKS DE MEMOIZACIÓN ===

/**
 * ISS-034: Hook para memoizar datos de gráficos con cache.
 * 
 * @param {Function} computeFn - Función que calcula los datos del gráfico
 * @param {Array} deps - Dependencias para recalcular
 * @param {Object} options - Opciones de configuración
 */
export function useMemoizedChartData(computeFn, deps, options = {}) {
  const {
    cacheKey = null,
    enableCache = true,
    ttl = 5 * 60 * 1000, // 5 minutos por defecto
    onCompute = null
  } = options;

  const cacheKeyRef = useRef(null);
  const timestampRef = useRef(0);

  return useMemo(() => {
    const now = Date.now();
    const key = cacheKey || generateCacheKey('chart', { deps: deps.map(String) });

    // Verificar cache
    if (enableCache && key === cacheKeyRef.current) {
      if (now - timestampRef.current < ttl) {
        const cached = chartDataCache.get(key);
        if (cached !== undefined) {
          return cached;
        }
      }
    }

    // Calcular nuevos datos
    const startTime = performance.now();
    const data = computeFn();
    const computeTime = performance.now() - startTime;

    if (onCompute) {
      onCompute({ computeTime, cacheHit: false });
    }

    // Guardar en cache
    if (enableCache) {
      chartDataCache.set(key, data);
      cacheKeyRef.current = key;
      timestampRef.current = now;
    }

    return data;
  }, deps);
}


/**
 * ISS-034: Hook para datos de serie temporal con agregación.
 * 
 * @param {Array} rawData - Datos crudos
 * @param {Object} config - Configuración de agregación
 */
export function useAggregatedTimeSeriesData(rawData, config = {}) {
  const {
    dateField = 'fecha',
    valueField = 'valor',
    aggregation = 'sum', // 'sum' | 'avg' | 'count' | 'max' | 'min'
    groupBy = 'day', // 'hour' | 'day' | 'week' | 'month'
    fillGaps = true
  } = config;

  return useMemoizedChartData(() => {
    if (!rawData || rawData.length === 0) return [];

    // Agrupar datos por período
    const grouped = {};
    
    rawData.forEach(item => {
      const date = new Date(item[dateField]);
      const key = getDateKey(date, groupBy);
      
      if (!grouped[key]) {
        grouped[key] = { date: key, values: [] };
      }
      grouped[key].values.push(Number(item[valueField]) || 0);
    });

    // Aplicar agregación
    const aggregated = Object.values(grouped).map(group => ({
      date: group.date,
      value: aggregate(group.values, aggregation)
    }));

    // Ordenar por fecha
    aggregated.sort((a, b) => new Date(a.date) - new Date(b.date));

    // Llenar huecos si es necesario
    if (fillGaps && aggregated.length > 1) {
      return fillDateGaps(aggregated, groupBy);
    }

    return aggregated;
  }, [rawData, dateField, valueField, aggregation, groupBy, fillGaps], {
    cacheKey: `timeseries:${aggregation}:${groupBy}`
  });
}


/**
 * ISS-034: Hook para datos de gráfico de barras con agrupación.
 */
export function useBarChartData(data, config = {}) {
  const {
    categoryField = 'categoria',
    valueField = 'valor',
    sortBy = 'value', // 'value' | 'category' | 'none'
    sortOrder = 'desc',
    limit = null,
    otherLabel = 'Otros'
  } = config;

  return useMemoizedChartData(() => {
    if (!data || data.length === 0) return [];

    // Agrupar por categoría
    const grouped = {};
    
    data.forEach(item => {
      const category = item[categoryField] || 'Sin categoría';
      if (!grouped[category]) {
        grouped[category] = 0;
      }
      grouped[category] += Number(item[valueField]) || 0;
    });

    // Convertir a array
    let result = Object.entries(grouped).map(([category, value]) => ({
      category,
      value
    }));

    // Ordenar
    if (sortBy === 'value') {
      result.sort((a, b) => sortOrder === 'desc' ? b.value - a.value : a.value - b.value);
    } else if (sortBy === 'category') {
      result.sort((a, b) => sortOrder === 'desc' 
        ? b.category.localeCompare(a.category)
        : a.category.localeCompare(b.category)
      );
    }

    // Limitar y agrupar resto en "Otros"
    if (limit && result.length > limit) {
      const top = result.slice(0, limit);
      const others = result.slice(limit);
      const othersValue = others.reduce((sum, item) => sum + item.value, 0);
      
      if (othersValue > 0) {
        top.push({ category: otherLabel, value: othersValue });
      }
      result = top;
    }

    return result;
  }, [data, categoryField, valueField, sortBy, sortOrder, limit]);
}


/**
 * ISS-034: Hook para datos de gráfico circular/donut.
 */
export function usePieChartData(data, config = {}) {
  const {
    categoryField = 'categoria',
    valueField = 'valor',
    minPercentage = 1, // Mínimo % para mostrar (agrupa menores en "Otros")
    otherLabel = 'Otros',
    colors = null
  } = config;

  return useMemoizedChartData(() => {
    if (!data || data.length === 0) return { slices: [], total: 0 };

    // Calcular total
    const total = data.reduce((sum, item) => sum + (Number(item[valueField]) || 0), 0);
    
    if (total === 0) return { slices: [], total: 0 };

    // Crear slices con porcentajes
    let slices = data.map(item => {
      const value = Number(item[valueField]) || 0;
      const percentage = (value / total) * 100;
      
      return {
        category: item[categoryField] || 'Sin categoría',
        value,
        percentage: Math.round(percentage * 10) / 10
      };
    });

    // Ordenar por valor descendente
    slices.sort((a, b) => b.value - a.value);

    // Agrupar menores en "Otros"
    if (minPercentage > 0) {
      const significant = slices.filter(s => s.percentage >= minPercentage);
      const others = slices.filter(s => s.percentage < minPercentage);
      
      if (others.length > 0) {
        const othersValue = others.reduce((sum, s) => sum + s.value, 0);
        const othersPercentage = (othersValue / total) * 100;
        
        significant.push({
          category: otherLabel,
          value: othersValue,
          percentage: Math.round(othersPercentage * 10) / 10
        });
      }
      
      slices = significant;
    }

    // Asignar colores
    const defaultColors = [
      '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
      '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1'
    ];
    
    slices = slices.map((slice, index) => ({
      ...slice,
      color: colors?.[index] || defaultColors[index % defaultColors.length]
    }));

    return { slices, total };
  }, [data, categoryField, valueField, minPercentage]);
}


/**
 * ISS-034: Hook para estadísticas con comparación temporal.
 */
export function useStatsWithComparison(currentData, previousData, config = {}) {
  const {
    valueField = 'valor',
    metrics = ['sum', 'avg', 'count']
  } = config;

  return useMemoizedChartData(() => {
    const calculateMetrics = (data) => {
      if (!data || data.length === 0) {
        return { sum: 0, avg: 0, count: 0, min: 0, max: 0 };
      }

      const values = data.map(item => Number(item[valueField]) || 0);
      const sum = values.reduce((a, b) => a + b, 0);
      
      return {
        sum,
        avg: sum / values.length,
        count: values.length,
        min: Math.min(...values),
        max: Math.max(...values)
      };
    };

    const current = calculateMetrics(currentData);
    const previous = calculateMetrics(previousData);

    // Calcular cambios porcentuales
    const changes = {};
    metrics.forEach(metric => {
      const currentVal = current[metric];
      const previousVal = previous[metric];
      
      if (previousVal === 0) {
        changes[metric] = currentVal > 0 ? 100 : 0;
      } else {
        changes[metric] = ((currentVal - previousVal) / previousVal) * 100;
      }
    });

    return {
      current,
      previous,
      changes,
      trend: changes.sum > 0 ? 'up' : changes.sum < 0 ? 'down' : 'stable'
    };
  }, [currentData, previousData, valueField, metrics.join(',')]);
}


// === FUNCIONES AUXILIARES ===

function getDateKey(date, groupBy) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hour = String(date.getHours()).padStart(2, '0');

  switch (groupBy) {
    case 'hour':
      return `${year}-${month}-${day}T${hour}:00`;
    case 'day':
      return `${year}-${month}-${day}`;
    case 'week':
      const weekStart = new Date(date);
      weekStart.setDate(date.getDate() - date.getDay());
      return weekStart.toISOString().split('T')[0];
    case 'month':
      return `${year}-${month}`;
    default:
      return `${year}-${month}-${day}`;
  }
}

function aggregate(values, method) {
  if (values.length === 0) return 0;
  
  switch (method) {
    case 'sum':
      return values.reduce((a, b) => a + b, 0);
    case 'avg':
      return values.reduce((a, b) => a + b, 0) / values.length;
    case 'count':
      return values.length;
    case 'max':
      return Math.max(...values);
    case 'min':
      return Math.min(...values);
    default:
      return values.reduce((a, b) => a + b, 0);
  }
}

function fillDateGaps(data, groupBy) {
  if (data.length < 2) return data;

  const filled = [];
  const startDate = new Date(data[0].date);
  const endDate = new Date(data[data.length - 1].date);
  const dataMap = new Map(data.map(d => [d.date, d.value]));

  let currentDate = new Date(startDate);
  
  while (currentDate <= endDate) {
    const key = getDateKey(currentDate, groupBy);
    filled.push({
      date: key,
      value: dataMap.get(key) || 0
    });

    // Avanzar al siguiente período
    switch (groupBy) {
      case 'hour':
        currentDate.setHours(currentDate.getHours() + 1);
        break;
      case 'day':
        currentDate.setDate(currentDate.getDate() + 1);
        break;
      case 'week':
        currentDate.setDate(currentDate.getDate() + 7);
        break;
      case 'month':
        currentDate.setMonth(currentDate.getMonth() + 1);
        break;
      default:
        currentDate.setDate(currentDate.getDate() + 1);
    }
  }

  return filled;
}


// === HOOKS ADICIONALES ===

/**
 * ISS-034: Hook para detectar si los datos han cambiado significativamente.
 */
export function useDataChangeDetection(data, threshold = 0.05) {
  const previousDataRef = useRef(null);
  const [hasSignificantChange, setHasSignificantChange] = useState(false);

  useEffect(() => {
    if (!data || !previousDataRef.current) {
      previousDataRef.current = data;
      return;
    }

    // Comparar datos
    const currentSum = Array.isArray(data) 
      ? data.reduce((sum, item) => sum + (Number(item.value || item.cantidad || 0)), 0)
      : 0;
    
    const previousSum = Array.isArray(previousDataRef.current)
      ? previousDataRef.current.reduce((sum, item) => sum + (Number(item.value || item.cantidad || 0)), 0)
      : 0;

    const change = previousSum === 0 
      ? (currentSum > 0 ? 1 : 0)
      : Math.abs(currentSum - previousSum) / previousSum;

    setHasSignificantChange(change >= threshold);
    previousDataRef.current = data;
  }, [data, threshold]);

  return hasSignificantChange;
}


/**
 * ISS-034: Hook para limpiar cache al desmontar.
 */
export function useChartCacheCleanup(cacheKeys = []) {
  useEffect(() => {
    return () => {
      cacheKeys.forEach(key => {
        // Limpiar entradas específicas si se proporcionan keys
        if (chartDataCache.has(key)) {
          chartDataCache.cache.delete(key);
        }
      });
    };
  }, []);
}


/**
 * Limpiar toda la cache de gráficos (útil al cambiar de página/contexto).
 */
export function clearChartCache() {
  chartDataCache.clear();
}


/**
 * Obtener estadísticas de la cache.
 */
export function getChartCacheStats() {
  return {
    size: chartDataCache.size(),
    maxSize: chartDataCache.maxSize
  };
}


export default {
  useMemoizedChartData,
  useAggregatedTimeSeriesData,
  useBarChartData,
  usePieChartData,
  useStatsWithComparison,
  useDataChangeDetection,
  useChartCacheCleanup,
  clearChartCache,
  getChartCacheStats
};
