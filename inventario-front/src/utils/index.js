/**
 * Utilidades del Frontend - Farmacia Penitenciaria
 * 
 * Este archivo centraliza todas las exportaciones de utilidades
 * para facilitar las importaciones en otros módulos.
 * 
 * @example
 * import { validators, handleApiCall, showError, exportReport } from '@/utils';
 */

// Validaciones
export {
    validators,
    validationSchemas,
    validateField,
    validateForm,
    validateSchema,
    sanitizeInput,
    getFieldError,
    hasErrors,
    combineValidators
} from './validation';

// Manejo de errores
export {
    parseApiError,
    showError,
    showSuccess,
    showWarning,
    showInfo,
    handleApiCall,
    withErrorHandling,
    ERROR_TYPES,
    ErrorBoundaryFallback
} from './errorHandler';

// Exportación de reportes
export {
    createExcelReport,
    generarReporteInventarioDev,
    generarReporteMovimientosDev,
    generarReporteCaducidadesDev
} from './reportExport';
