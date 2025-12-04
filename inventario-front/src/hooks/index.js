/**
 * Hooks personalizados - Farmacia Penitenciaria
 * 
 * Centraliza las exportaciones de todos los hooks del proyecto.
 */

export { useAuth } from './useAuth';
export { useFormValidation, useFieldValidation } from './useFormValidation';
export { useInactivityLogout } from './useInactivityLogout';
export { usePermissions } from './usePermissions';
export { useTheme } from './useTheme';

// Sprint 3: ISS-008 - UX para lotes vencidos
export { 
  useLotesVencidosAlert, 
  BadgeCaducidad, 
  AlertaLotesVencidos, 
  TablaLotesConCaducidad,
  ALERTA_CADUCIDAD 
} from './useLotesVencidos';

// Sprint 3: ISS-034 - Memoización de gráficos
export {
  useMemoizedChartData,
  useAggregatedTimeSeriesData,
  useBarChartData,
  usePieChartData,
  useStatsWithComparison,
  useDataChangeDetection,
  useChartCacheCleanup,
  clearChartCache,
  getChartCacheStats
} from './useChartMemoization';
