/**
 * ISS-RES-001 FIX (audit-final): Helpers para filtrado y manejo de requisiciones.
 * 
 * Centraliza lógica de filtrado para evitar duplicación en componentes.
 */

/**
 * Filtros iniciales para requisiciones
 */
export const FILTROS_INICIALES = {
    estado: '',
    fechaInicio: '',
    fechaFin: '',
    search: '',
    centro: '',
    prioridad: '',
};

/**
 * Filtra la lista de requisiciones según los criterios proporcionados
 * 
 * @param {Array} requisiciones - Lista completa de requisiciones
 * @param {Object} filtros - Estado actual de filtros
 * @returns {Array} Lista filtrada
 */
export const filtrarRequisiciones = (requisiciones, filtros) => {
    if (!requisiciones || !Array.isArray(requisiciones)) {
        return [];
    }
    
    return requisiciones.filter(req => {
        // Filtro por estado
        if (filtros.estado) {
            const estadoReq = (req.estado || '').toLowerCase();
            const estadoFiltro = filtros.estado.toLowerCase();
            if (estadoReq !== estadoFiltro) return false;
        }

        // Filtro por búsqueda (número, centro o solicitante)
        if (filtros.search) {
            const searchTerm = filtros.search.toLowerCase();
            const numeroMatch = (req.numero || '').toLowerCase().includes(searchTerm);
            const centroMatch = (req.centro?.nombre || req.centro_destino?.nombre || '').toLowerCase().includes(searchTerm);
            const solicitanteMatch = (req.solicitante?.username || req.solicitante?.first_name || '').toLowerCase().includes(searchTerm);
            if (!numeroMatch && !centroMatch && !solicitanteMatch) return false;
        }

        // Filtro por centro específico
        if (filtros.centro) {
            const centroId = req.centro_id || req.centro?.id || req.centro_destino_id;
            if (centroId !== parseInt(filtros.centro)) return false;
        }

        // Filtro por prioridad
        if (filtros.prioridad) {
            const prioridadReq = (req.prioridad || 'normal').toLowerCase();
            if (prioridadReq !== filtros.prioridad.toLowerCase()) return false;
        }

        // Filtro por fechas
        if (filtros.fechaInicio) {
            const fechaReq = new Date(req.fecha_solicitud || req.created_at);
            const fechaInicio = new Date(filtros.fechaInicio);
            fechaInicio.setHours(0, 0, 0, 0);
            if (fechaReq < fechaInicio) return false;
        }
        
        if (filtros.fechaFin) {
            const fechaReq = new Date(req.fecha_solicitud || req.created_at);
            const fechaFin = new Date(filtros.fechaFin);
            // Ajustar fin al final del día
            fechaFin.setHours(23, 59, 59, 999);
            if (fechaReq > fechaFin) return false;
        }

        return true;
    });
};

/**
 * Ordena requisiciones por fecha (más recientes primero)
 * 
 * @param {Array} requisiciones - Lista de requisiciones
 * @param {string} campo - Campo de fecha a usar ('fecha_solicitud', 'created_at', etc.)
 * @param {string} orden - 'asc' o 'desc'
 * @returns {Array} Lista ordenada
 */
export const ordenarRequisiciones = (requisiciones, campo = 'fecha_solicitud', orden = 'desc') => {
    if (!requisiciones || !Array.isArray(requisiciones)) {
        return [];
    }
    
    return [...requisiciones].sort((a, b) => {
        const fechaA = new Date(a[campo] || a.created_at);
        const fechaB = new Date(b[campo] || b.created_at);
        
        if (orden === 'desc') {
            return fechaB - fechaA;
        }
        return fechaA - fechaB;
    });
};

/**
 * Agrupa requisiciones por estado
 * 
 * @param {Array} requisiciones - Lista de requisiciones
 * @returns {Object} Objeto con estados como keys y arrays como values
 */
export const agruparPorEstado = (requisiciones) => {
    if (!requisiciones || !Array.isArray(requisiciones)) {
        return {};
    }
    
    return requisiciones.reduce((acc, req) => {
        const estado = (req.estado || 'sin_estado').toLowerCase();
        if (!acc[estado]) {
            acc[estado] = [];
        }
        acc[estado].push(req);
        return acc;
    }, {});
};

/**
 * Calcula estadísticas de requisiciones
 * 
 * @param {Array} requisiciones - Lista de requisiciones
 * @returns {Object} Estadísticas
 */
export const calcularEstadisticas = (requisiciones) => {
    if (!requisiciones || !Array.isArray(requisiciones)) {
        return {
            total: 0,
            pendientes: 0,
            enProceso: 0,
            completadas: 0,
            rechazadas: 0,
        };
    }
    
    const estadosPendientes = ['borrador', 'pendiente_admin', 'pendiente_director', 'enviada'];
    const estadosEnProceso = ['en_revision', 'autorizada', 'en_surtido', 'parcial'];
    const estadosCompletados = ['surtida', 'entregada'];
    const estadosRechazados = ['rechazada', 'cancelada', 'vencida'];
    
    return {
        total: requisiciones.length,
        pendientes: requisiciones.filter(r => estadosPendientes.includes((r.estado || '').toLowerCase())).length,
        enProceso: requisiciones.filter(r => estadosEnProceso.includes((r.estado || '').toLowerCase())).length,
        completadas: requisiciones.filter(r => estadosCompletados.includes((r.estado || '').toLowerCase())).length,
        rechazadas: requisiciones.filter(r => estadosRechazados.includes((r.estado || '').toLowerCase())).length,
    };
};

/**
 * Verifica si una requisición puede ser editada
 * 
 * @param {Object} requisicion - Requisición
 * @returns {boolean}
 */
export const puedeEditar = (requisicion) => {
    const estadosEditables = ['borrador', 'devuelta'];
    return estadosEditables.includes((requisicion?.estado || '').toLowerCase());
};

/**
 * Verifica si una requisición puede ser cancelada
 * 
 * @param {Object} requisicion - Requisición
 * @returns {boolean}
 */
export const puedeCancelar = (requisicion) => {
    const estadosNoCancelables = ['surtida', 'entregada', 'cancelada', 'rechazada', 'vencida'];
    return !estadosNoCancelables.includes((requisicion?.estado || '').toLowerCase());
};

/**
 * Formatea el número de requisición para mostrar
 * 
 * @param {Object} requisicion - Requisición
 * @returns {string} Número formateado
 */
export const formatearNumero = (requisicion) => {
    if (!requisicion) return 'N/A';
    return requisicion.numero || `REQ-${requisicion.id}`;
};
