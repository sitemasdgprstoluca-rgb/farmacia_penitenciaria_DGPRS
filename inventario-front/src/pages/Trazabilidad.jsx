import { useState, useEffect, useCallback, useRef } from 'react';
import { trazabilidadAPI, centrosAPI, productosAPI, descargarArchivo, abrirPdfEnNavegador } from '../services/api';
import { toast } from 'react-hot-toast';
import { FaSearch, FaBox, FaWarehouse, FaHistory, FaExclamationTriangle, FaFilePdf, FaFileExcel, FaBuilding, FaSpinner, FaInfoCircle, FaTimes, FaGlobe, FaCalendarAlt, FaFilter, FaClipboardList, FaChevronDown, FaArrowDown, FaArrowUp } from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import { usePermissions } from '../hooks/usePermissions';

// ============================================
// HELPERS
// ============================================

/**
 * Obtiene el nombre del centro de forma segura
 * Maneja centros como string, objeto, o null
 */
const getCentroNombre = (centro) => {
  if (!centro) return 'Sin centro';
  if (typeof centro === 'string') return centro;
  if (typeof centro === 'object') {
    return centro.nombre || centro.name || `Centro ${centro.id || ''}`;
  }
  return String(centro);
};

// ============================================
// MAPEO Y NORMALIZACIÓN DE DATOS
// ============================================

const mapMovimiento = (mov = {}) => ({
  id: mov.id,
  fecha: mov.fecha || mov.fecha_movimiento || mov.fecha_mov || null,
  tipo: (mov.tipo || mov.tipo_movimiento || '').toString().toUpperCase(),
  cantidad: mov.cantidad,
  centro: getCentroNombre(mov.centro || mov.centro_nombre),
  usuario: mov.usuario || mov.usuario_nombre || '',
  lote: mov.lote || mov.lote_numero || '',
  observaciones: mov.observaciones || '',
  saldo: mov.saldo,
});

const mapLote = (lote = {}) => ({
  numero_lote: lote.numero_lote,
  fecha_caducidad: lote.fecha_caducidad,
  cantidad_actual: lote.cantidad_actual,
  cantidad_inicial: lote.cantidad_inicial ?? lote.cantidad_actual,
  estado: (lote.estado || lote.estado_caducidad || '').toString().toUpperCase(),
  centro: getCentroNombre(lote.centro),
  numero_contrato: lote.numero_contrato || '',
  marca: lote.marca || '',
});

const normalizeProductoResponse = (data) => {
  if (!data) return null;

  const lotes = Array.isArray(data.lotes) ? data.lotes.map(mapLote) : [];
  const movimientos = Array.isArray(data.movimientos) ? data.movimientos.map(mapMovimiento) : [];

  // ISS-FIX: El backend devuelve data.codigo + data.producto con los detalles
  // Priorizar data.producto para obtener nombre/descripción
  if (data.producto) {
    const producto = data.producto;
    return {
      codigo: data.codigo || producto.clave || producto.codigo,
      nombre: producto.nombre || producto.descripcion || '',
      descripcion: producto.descripcion || producto.nombre || '',
      presentacion: producto.presentacion || '',
      unidad_medida: producto.unidad_medida || 'PIEZA',
      precio_unitario: producto.precio_unitario || producto.precio || 0,
      stock_actual: data.estadisticas?.stock_total ?? producto.stock_actual ?? 0,
      stock_minimo: producto.stock_minimo ?? data.estadisticas?.stock_minimo ?? null,
      lotes,
      movimientos,
      alertas: data.alertas || [],
      estadisticas: data.estadisticas || {},
    };
  }

  // Fallback: estructura donde los datos vienen directamente en data
  if (data.codigo) {
    return {
      codigo: data.codigo,
      nombre: data.nombre || data.descripcion || '',
      descripcion: data.descripcion || data.nombre || '',
      presentacion: data.presentacion || '',
      unidad_medida: data.unidad_medida || 'PIEZA',
      precio_unitario: data.precio_unitario || data.precio || 0,
      stock_actual: data.stock_actual ?? data.estadisticas?.stock_total ?? 0,
      stock_minimo: data.stock_minimo ?? data.estadisticas?.stock_minimo ?? null,
      lotes,
      movimientos,
      alertas: data.alertas || [],
      estadisticas: data.estadisticas || {},
    };
  }

  return data;
};

const normalizeLoteResponse = (data) => {
  if (!data) return null;

  // Estructura donde data.lote contiene los datos del lote
  if (data.lote) {
    const lote = data.lote;
    return {
      // ISS-FIX: Priorizar data.id (raíz) que siempre viene del backend
      id: data.id || lote.id,
      numero_lote: lote.numero_lote,
      producto: {
        codigo: lote.producto,
        nombre: lote.producto_nombre || lote.producto_descripcion,
        presentacion: lote.producto_presentacion || '',
      },
      fecha_caducidad: lote.fecha_caducidad,
      cantidad_actual: lote.cantidad_actual,
      cantidad_inicial: lote.cantidad_inicial,
      estado: (lote.estado_caducidad || lote.estado || '').toString().toUpperCase(),
      centro: getCentroNombre(lote.centro),
      numero_contrato: lote.numero_contrato || '',
      marca: lote.marca || '',
      movimientos: (data.movimientos || data.historial || []).map(mapMovimiento),
      alertas: data.alertas || [],
      estadisticas: data.estadisticas || {},
    };
  }

  // Estructura donde data tiene los campos directamente
  if (data.numero_lote) {
    return {
      id: data.id,  // ISS-FIX: Guardar ID para exportación precisa
      numero_lote: data.numero_lote,
      producto: data.producto || {},
      fecha_caducidad: data.fecha_caducidad,
      cantidad_actual: data.cantidad_actual,
      cantidad_inicial: data.cantidad_inicial,
      estado: (data.estado || data.estado_caducidad || '').toString().toUpperCase(),
      centro: data.centro,
      numero_contrato: data.numero_contrato || '',
      marca: data.marca || '',
      movimientos: (data.movimientos || []).map(mapMovimiento),
      alertas: data.alertas || [],
      estadisticas: data.estadisticas || {},
    };
  }

  return data;
};

// ============================================
// COMPONENTE PRINCIPAL
// ============================================

const Trazabilidad = () => {
  const { getRolPrincipal, permisos, user } = usePermissions();
  const rolPrincipal = getRolPrincipal();
  
  // PERMISOS
  const esAdminOFarmacia = ['ADMIN', 'FARMACIA'].includes(rolPrincipal) || permisos?.isSuperuser;
  const puedeVerContrato = esAdminOFarmacia;
  const esCentroUser = rolPrincipal === 'CENTRO';
  
  const centroUsuarioId = user?.centro?.id || user?.centro || user?.centro_id;
  const centroUsuarioNombre = user?.centro?.nombre || user?.centro_nombre || null;

  // Estados principales
  const [terminoBusqueda, setTerminoBusqueda] = useState('');
  const [tipoBusqueda, setTipoBusqueda] = useState(null); // 'producto' o 'lote' - detectado automáticamente
  const [identificadorResultados, setIdentificadorResultados] = useState('');
  const [loading, setLoading] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportingExcel, setExportingExcel] = useState(false);
  const [exportingControl, setExportingControl] = useState(false);
  const [exportingFormatoB, setExportingFormatoB] = useState(false);  // FORMATO OFICIAL B
  const [resultados, setResultados] = useState(null);
  
  // Modo global (reporte de todos los lotes)
  const [modoGlobal, setModoGlobal] = useState(false);
  const [resultadosGlobal, setResultadosGlobal] = useState(null);
  
  // Filtros de fecha
  const [fechaInicio, setFechaInicio] = useState('');
  const [fechaFin, setFechaFin] = useState('');
  const [tipoMovimiento, setTipoMovimiento] = useState('');
  
  // Autocompletado
  const [sugerencias, setSugerencias] = useState([]);
  const [loadingSugerencias, setLoadingSugerencias] = useState(false);
  const [mostrarSugerencias, setMostrarSugerencias] = useState(false);
  const [indiceSugerencia, setIndiceSugerencia] = useState(-1);
  
  // Filtro de centro (solo para admin/farmacia)
  const [centros, setCentros] = useState([]);
  // ISS-FIX: Por defecto 'central' para que solo muestre Almacén Central
  const [centroFiltro, setCentroFiltro] = useState('central');
  
  // Refs
  const debounceRef = useRef(null);
  const inputRef = useRef(null);
  const sugerenciasRef = useRef(null);
  const lastSearchRef = useRef({ termino: '', centro: '', fechaInicio: '', fechaFin: '' });

  // Cargar centros al montar (solo para admin/farmacia)
  useEffect(() => {
    const cargarCentros = async () => {
      if (!esAdminOFarmacia) return;
      try {
        const resp = await centrosAPI.getAll({ page_size: 100, ordering: 'nombre', activo: true });
        setCentros(resp.data?.results || resp.data || []);
      } catch (e) {
        console.warn('No se pudieron cargar centros:', e);
      }
    };
    cargarCentros();
  }, [esAdminOFarmacia]);

  // Cerrar sugerencias al hacer clic fuera
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (
        inputRef.current && !inputRef.current.contains(e.target) &&
        sugerenciasRef.current && !sugerenciasRef.current.contains(e.target)
      ) {
        setMostrarSugerencias(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Búsqueda de autocompletado con debounce
  const buscarSugerencias = useCallback(async (termino) => {
    if (!termino || termino.length < 2) {
      setSugerencias([]);
      return;
    }

    setLoadingSugerencias(true);
    try {
      const params = centroFiltro ? { centro: centroFiltro } : {};
      const response = await trazabilidadAPI.autocomplete(termino, params);
      setSugerencias(response.data?.results || []);
    } catch (error) {
      console.warn('Error en autocompletado:', error);
      setSugerencias([]);
    } finally {
      setLoadingSugerencias(false);
    }
  }, [centroFiltro]);

  // Manejar cambio en el input de búsqueda
  const handleTerminoBusquedaChange = (e) => {
    const valor = e.target.value;
    setTerminoBusqueda(valor);
    setIndiceSugerencia(-1);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    
    if (valor.length >= 2) {
      setMostrarSugerencias(true);
      debounceRef.current = setTimeout(() => {
        buscarSugerencias(valor);
      }, 300);
    } else {
      setSugerencias([]);
      setMostrarSugerencias(false);
    }
  };

  // Seleccionar sugerencia
  const seleccionarSugerencia = (sugerencia) => {
    setTerminoBusqueda(sugerencia.identificador);
    setMostrarSugerencias(false);
    setSugerencias([]);
    // Auto-buscar al seleccionar
    ejecutarBusqueda(sugerencia.identificador, sugerencia.tipo);
  };

  // Manejar teclas en el input
  const handleKeyDown = (e) => {
    if (!mostrarSugerencias || sugerencias.length === 0) {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleBuscar(e);
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setIndiceSugerencia(prev => Math.min(prev + 1, sugerencias.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setIndiceSugerencia(prev => Math.max(prev - 1, -1));
        break;
      case 'Enter':
        e.preventDefault();
        if (indiceSugerencia >= 0 && sugerencias[indiceSugerencia]) {
          seleccionarSugerencia(sugerencias[indiceSugerencia]);
        } else {
          handleBuscar(e);
        }
        break;
      case 'Escape':
        setMostrarSugerencias(false);
        break;
    }
  };

  // Ejecutar búsqueda
  const ejecutarBusqueda = async (termino, tipoForzado = null) => {
    const terminoTrimmed = termino.trim();
    
    // ISS-FIX: Si no hay término pero hay filtros (centro, fechas, tipo), usar búsqueda global
    // Para usuarios de centro, siempre tienen filtro implícito por su centro
    if (!terminoTrimmed) {
      const hayFiltros = centroFiltro || fechaInicio || fechaFin || tipoMovimiento || (esCentroUser && centroUsuarioId);
      if (hayFiltros) {
        // Usar búsqueda global con filtros
        buscarGlobal();
        return;
      } else {
        toast.error('Ingrese un término de búsqueda o seleccione al menos un filtro (centro, fechas o tipo de movimiento)');
        return;
      }
    }

    // Evitar búsquedas duplicadas
    if (lastSearchRef.current.termino === terminoTrimmed &&
        lastSearchRef.current.centro === centroFiltro &&
        resultados) {
      toast('Ya tienes estos resultados cargados', { icon: 'ℹ️' });
      return;
    }

    setLoading(true);
    setMostrarSugerencias(false);
    
    try {
      // Primero detectamos el tipo si no viene forzado
      let tipo = tipoForzado;
      let identificador = terminoTrimmed;
      
      if (!tipo) {
        // Usar búsqueda unificada para detectar el tipo
        try {
          const params = centroFiltro ? { centro: centroFiltro } : {};
          const buscarResp = await trazabilidadAPI.buscar(terminoTrimmed, params);
          tipo = buscarResp.data?.tipo;
          identificador = buscarResp.data?.identificador || terminoTrimmed;
        } catch (error) {
          // Si la búsqueda unificada falla, intentamos como producto
          tipo = 'producto';
        }
      }

      if (!tipo) {
        toast.error('No se encontró producto ni lote con ese término');
        setResultados(null);
        setLoading(false);
        return;
      }

      // Ahora obtenemos los datos completos - incluyendo filtros de fecha
      const params = {};
      if (centroFiltro) params.centro = centroFiltro;
      if (fechaInicio) params.fecha_inicio = fechaInicio;
      if (fechaFin) params.fecha_fin = fechaFin;
      if (tipoMovimiento) params.tipo = tipoMovimiento;
      
      const normalizer = tipo === 'producto' ? normalizeProductoResponse : normalizeLoteResponse;
      
      const response = tipo === 'producto'
        ? await trazabilidadAPI.producto(identificador, params)
        : await trazabilidadAPI.lote(identificador, params);

      const datosNormalizados = normalizer(response.data);
      setResultados(datosNormalizados);
      setTipoBusqueda(tipo);
      setIdentificadorResultados(identificador);
      lastSearchRef.current = { termino: terminoTrimmed, centro: centroFiltro, fechaInicio, fechaFin };
      
      toast.success(`Trazabilidad de ${tipo === 'producto' ? 'producto' : 'lote'} cargada`);
    } catch (error) {
      if (error.response?.status === 403) {
        toast.error('No tienes permiso para acceder a esta trazabilidad');
      } else if (error.response?.status === 404) {
        toast.error('No se encontró el producto o lote');
      } else {
        toast.error(error.response?.data?.error || 'Error al cargar trazabilidad');
      }
      console.error(error);
      setResultados(null);
      setTipoBusqueda(null);
      setIdentificadorResultados('');
    } finally {
      setLoading(false);
    }
  };

  const handleBuscar = (e) => {
    e.preventDefault();
    ejecutarBusqueda(terminoBusqueda);
  };

  // Exportar PDF
  const handleExportarPdf = async () => {
    if (modoGlobal) {
      // Exportar trazabilidad global
      const win = abrirPdfEnNavegador();
      if (!win) return;

      setExportingPdf(true);
      try {
        const params = {};
        if (fechaInicio) params.fecha_inicio = fechaInicio;
        if (fechaFin) params.fecha_fin = fechaFin;
        if (centroFiltro) params.centro = centroFiltro;
        if (tipoMovimiento) params.tipo = tipoMovimiento;
        
        const response = await trazabilidadAPI.exportarGlobalPdf(params);
        abrirPdfEnNavegador(response, win);
        toast.success('PDF global generado exitosamente');
      } catch (error) {
        console.error('Error al exportar PDF global:', error);
        toast.error(error.response?.data?.error || 'Error al generar PDF');
      } finally {
        setExportingPdf(false);
      }
      return;
    }
    
    if (!resultados || !identificadorResultados) {
      toast.error('Primero busque un producto o lote para exportar');
      return;
    }

    if (tipoBusqueda === 'lote' && !esAdminOFarmacia) {
      toast.error('No tienes permiso para exportar trazabilidad de lotes');
      return;
    }

    const win = abrirPdfEnNavegador();
    if (!win) return;

    setExportingPdf(true);
    try {
      let response;
      
      // Preparar parámetros con filtros de fecha
      const params = {};
      if (fechaInicio) params.fecha_inicio = fechaInicio;
      if (fechaFin) params.fecha_fin = fechaFin;
      if (centroFiltro) params.centro = centroFiltro;
      
      if (tipoBusqueda === 'producto') {
        response = await trazabilidadAPI.exportarPdf(identificadorResultados, params);
      } else {
        const loteId = resultados?.id;
        response = await trazabilidadAPI.exportarLotePdf(identificadorResultados, loteId, params);
      }
      
      abrirPdfEnNavegador(response, win);
      toast.success('PDF generado exitosamente');
    } catch (error) {
      console.error('Error al exportar PDF:', error);
      if (error.response?.status === 403) {
        toast.error('No tienes permiso para exportar');
      } else if (error.response?.status === 404) {
        toast.error('Registro no encontrado');
      } else {
        toast.error(error.response?.data?.error || 'Error al generar PDF');
      }
    } finally {
      setExportingPdf(false);
    }
  };

  // Exportar Excel
  const handleExportarExcel = async () => {
    if (modoGlobal) {
      // Exportar trazabilidad global
      setExportingExcel(true);
      try {
        const params = {};
        if (fechaInicio) params.fecha_inicio = fechaInicio;
        if (fechaFin) params.fecha_fin = fechaFin;
        if (centroFiltro) params.centro = centroFiltro;
        if (tipoMovimiento) params.tipo = tipoMovimiento;
        
        const response = await trazabilidadAPI.exportarGlobalExcel(params);
        const filename = `trazabilidad_global_${new Date().toISOString().split('T')[0]}.xlsx`;
        descargarArchivo(response, filename);
        toast.success('Excel global generado exitosamente');
      } catch (error) {
        console.error('Error al exportar Excel global:', error);
        toast.error(error.response?.data?.error || 'Error al generar Excel');
      } finally {
        setExportingExcel(false);
      }
      return;
    }
    
    if (!resultados || !identificadorResultados) {
      toast.error('Primero busque un producto o lote para exportar');
      return;
    }

    if (tipoBusqueda === 'lote' && !esAdminOFarmacia) {
      toast.error('No tienes permiso para exportar trazabilidad de lotes');
      return;
    }

    setExportingExcel(true);
    try {
      let response;
      let filename;
      
      // Preparar parámetros con filtros de fecha
      const params = {};
      if (fechaInicio) params.fecha_inicio = fechaInicio;
      if (fechaFin) params.fecha_fin = fechaFin;
      if (centroFiltro) params.centro = centroFiltro;
      
      if (tipoBusqueda === 'producto') {
        response = await trazabilidadAPI.exportarExcel(identificadorResultados, params);
        filename = `trazabilidad_producto_${identificadorResultados}_${new Date().toISOString().split('T')[0]}.xlsx`;
      } else {
        const loteId = resultados?.id;
        response = await trazabilidadAPI.exportarLoteExcel(identificadorResultados, loteId, params);
        filename = `trazabilidad_lote_${identificadorResultados}_${new Date().toISOString().split('T')[0]}.xlsx`;
      }
      
      descargarArchivo(response, filename);
      toast.success('Excel generado exitosamente');
    } catch (error) {
      console.error('Error al exportar Excel:', error);
      if (error.response?.status === 403) {
        toast.error('No tienes permiso para exportar');
      } else if (error.response?.status === 404) {
        toast.error('Registro no encontrado');
      } else {
        toast.error(error.response?.data?.error || 'Error al generar Excel');
      }
    } finally {
      setExportingExcel(false);
    }
  };

  // ========== FORMATO OFICIAL B: Tarjeta de Entradas/Salidas ==========
  // Solo disponible cuando se consulta un lote específico
  const handleExportarFormatoB = async () => {
    if (tipoBusqueda !== 'lote') {
      toast.error('El Formato B solo está disponible para consultas de lote específico');
      return;
    }
    
    if (!resultados || !identificadorResultados) {
      toast.error('Primero busque un lote para exportar');
      return;
    }

    if (!esAdminOFarmacia) {
      toast.error('No tienes permiso para exportar el Formato B oficial');
      return;
    }

    const win = abrirPdfEnNavegador();
    if (!win) return;

    setExportingFormatoB(true);
    try {
      const loteId = resultados?.id;
      
      // Preparar parámetros: formato_b + filtros
      const params = { formato: 'formato_b' };
      if (fechaInicio) params.fecha_inicio = fechaInicio;
      if (fechaFin) params.fecha_fin = fechaFin;
      if (centroFiltro) params.centro = centroFiltro;
      
      // Usar la misma API pero con parámetro de formato especial
      const response = await trazabilidadAPI.exportarLotePdf(identificadorResultados, loteId, params);
      
      abrirPdfEnNavegador(response, win);
      toast.success('📋 Formato B (Tarjeta Entradas/Salidas) generado exitosamente');
    } catch (error) {
      console.error('Error al exportar Formato B:', error);
      if (error.response?.status === 403) {
        toast.error('No tienes permiso para exportar');
      } else if (error.response?.status === 404) {
        toast.error('Lote no encontrado');
      } else {
        toast.error(error.response?.data?.error || 'Error al generar Formato B');
      }
    } finally {
      setExportingFormatoB(false);
    }
  };

  // Exportar Control de Inventarios (formato licitación)
  const handleExportarControlInventarios = async () => {
    if (!esAdminOFarmacia) {
      toast.error('Solo administradores y farmacia pueden exportar este formato');
      return;
    }
    
    setExportingControl(true);
    try {
      const response = await trazabilidadAPI.exportarControlInventarios();
      const filename = `Control_Inventarios_Almacen_Central_${new Date().toISOString().split('T')[0]}.xlsx`;
      descargarArchivo(response, filename);
      toast.success('Control de inventarios exportado exitosamente');
    } catch (error) {
      console.error('Error al exportar control de inventarios:', error);
      toast.error(error.response?.data?.error || 'Error al generar el archivo');
    } finally {
      setExportingControl(false);
    }
  };

  // Buscar trazabilidad global
  const buscarGlobal = async () => {
    // Solo admin/farmacia pueden acceder a trazabilidad global (alineado con backend)
    if (!esAdminOFarmacia) {
      toast.error('No tienes permiso para ver trazabilidad global');
      return;
    }
    
    setLoading(true);
    setModoGlobal(true);
    setResultados(null);
    setTipoBusqueda(null);
    
    try {
      const params = {};
      if (fechaInicio) params.fecha_inicio = fechaInicio;
      if (fechaFin) params.fecha_fin = fechaFin;
      if (tipoMovimiento) params.tipo = tipoMovimiento;
      
      // FILTRO DE CENTRO - Lógica clara:
      // - 'central': Solo Farmacia Central (centro=null en BD)
      // - 'todos': Ver todos los movimientos de todos los centros
      // - ID numérico: Centro específico
      if (centroFiltro) {
        params.centro = centroFiltro;
      } else {
        // ISS-FIX: Enviar 'central' por defecto para admin/farmacia
        params.centro = 'central';
      }
      
      const response = await trazabilidadAPI.global(params);
      setResultadosGlobal(response.data);
      
      // Mensaje informativo según el filtro
      const centroMsg = centroFiltro === 'todos' 
        ? '(todos los centros)' 
        : centroFiltro 
          ? `(centro seleccionado)` 
          : '(Farmacia Central)';
      toast.success(`Trazabilidad cargada ${centroMsg}: ${response.data?.total_movimientos || 0} movimientos`);
    } catch (error) {
      console.error('Error al cargar trazabilidad global:', error);
      toast.error(error.response?.data?.error || 'Error al cargar trazabilidad global');
      setResultadosGlobal(null);
    } finally {
      setLoading(false);
    }
  };

  // Limpiar búsqueda
  const limpiarBusqueda = () => {
    if (loading || exportingPdf || exportingExcel) {
      toast('Espera a que termine la operación', { icon: '⏳' });
      return;
    }
    
    setTerminoBusqueda('');
    setIdentificadorResultados('');
    setResultados(null);
    setResultadosGlobal(null);
    setTipoBusqueda(null);
    setCentroFiltro('');
    setFechaInicio('');
    setFechaFin('');
    setTipoMovimiento('');
    setModoGlobal(false);
    setSugerencias([]);
    setMostrarSugerencias(false);
    lastSearchRef.current = { termino: '', centro: '', fechaInicio: '', fechaFin: '' };
    
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
  };

  // ============================================
  // RENDERIZADO DE SECCIONES
  // ============================================

  const renderAlertas = () => {
    if (!resultados?.alertas?.length) return null;

    const badgeClass = (nivel = '') => {
      const valor = nivel.toString().toUpperCase();
      if (valor === 'CRITICO') return 'bg-red-100 text-red-700';
      if (valor === 'ADVERTENCIA') return 'bg-amber-100 text-amber-800';
      return 'bg-blue-100 text-blue-700';
    };

    return (
      <div className="bg-white rounded-2xl shadow-lg border border-amber-200/50 p-5">
        <h3 className="text-sm font-bold mb-3 flex items-center gap-2 text-amber-700">
          <div className="w-7 h-7 rounded-lg bg-amber-100 flex items-center justify-center">
            <FaExclamationTriangle className="text-amber-500 text-xs" />
          </div>
          Alertas
        </h3>
        <div className="flex flex-wrap gap-2">
          {resultados.alertas.map((alerta, index) => (
            <span
              key={`${alerta.tipo || 'alerta'}-${index}`}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${badgeClass(alerta.nivel)}`}
            >
              {alerta.mensaje || alerta.tipo}
            </span>
          ))}
        </div>
      </div>
    );
  };

  const renderInfoProducto = () => (
    <div className="grid gap-4 md:grid-cols-4">
      <div className="bg-gray-50 rounded-xl p-3">
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Clave</p>
        <p className="font-bold text-gray-800">{resultados.codigo}</p>
      </div>
      <div className="md:col-span-2 bg-gray-50 rounded-xl p-3">
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Nombre / Descripción</p>
        <p className="font-bold text-gray-800">{resultados.nombre || resultados.descripcion}</p>
      </div>
      <div className="bg-gray-50 rounded-xl p-3">
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Unidad</p>
        <p className="font-bold text-gray-800">{resultados.unidad_medida || 'PIEZA'}</p>
      </div>
      {resultados.presentacion && (
        <div className="md:col-span-2 bg-gray-50 rounded-xl p-3">
          <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Presentación</p>
          <p className="font-bold text-gray-800">{resultados.presentacion}</p>
        </div>
      )}
      {resultados.precio_unitario > 0 && (
        <div className="bg-green-50 rounded-xl p-3 border border-green-200/40">
          <p className="text-[10px] font-bold uppercase tracking-wider text-green-600 mb-1">Precio Unitario</p>
          <p className="font-bold text-green-700">${parseFloat(resultados.precio_unitario).toFixed(2)}</p>
        </div>
      )}
      <div className="bg-gradient-to-br from-[var(--color-primary)]/5 to-[var(--color-primary)]/10 rounded-xl p-3 border border-[var(--color-primary)]/15">
        <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-primary)] mb-1">Inventario actual</p>
        <p className="text-2xl font-black text-[var(--color-primary)]">{resultados.stock_actual ?? 0}</p>
        {resultados.stock_minimo != null && (
          <p className="text-[10px] text-gray-500 mt-1 font-medium">Inv. Mínimo: {resultados.stock_minimo}</p>
        )}
      </div>
    </div>
  );

  const renderInfoLote = () => (
    <div className="grid gap-4 md:grid-cols-4">
      <div className="bg-gray-50 rounded-xl p-3">
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Número de Lote</p>
        <p className="font-bold text-gray-800">{resultados.numero_lote}</p>
      </div>
      <div className="md:col-span-2 bg-gray-50 rounded-xl p-3">
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Producto</p>
        <p className="font-bold text-gray-800">
          {resultados.producto?.codigo} - {resultados.producto?.nombre}
        </p>
        {resultados.producto?.presentacion && (
          <p className="text-xs text-gray-500 mt-1">Presentación: {resultados.producto.presentacion}</p>
        )}
      </div>
      <div className="bg-gray-50 rounded-xl p-3">
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Caducidad</p>
        <p className="font-bold text-gray-800">
          {resultados.fecha_caducidad ? new Date(resultados.fecha_caducidad).toLocaleDateString() : '-'}
        </p>
      </div>
      <div className="bg-gradient-to-br from-[var(--color-primary)]/5 to-[var(--color-primary)]/10 rounded-xl p-3 border border-[var(--color-primary)]/15">
        <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-primary)] mb-1">Cantidad actual</p>
        <p className="text-2xl font-black text-[var(--color-primary)]">{resultados.cantidad_actual}</p>
      </div>
      <div className="bg-gray-50 rounded-xl p-3">
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Cantidad inicial</p>
        <p className="font-bold text-gray-800">{resultados.cantidad_inicial}</p>
      </div>
      <div className="bg-gray-50 rounded-xl p-3">
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Estado</p>
        <p className="font-bold text-gray-800">{resultados.estado || '-'}</p>
      </div>
      <div className="bg-gray-50 rounded-xl p-3">
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Centro</p>
        <p className="font-bold text-gray-800">{resultados.centro || 'Farmacia Central'}</p>
      </div>
      <div className="bg-gray-50 rounded-xl p-3">
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Marca</p>
        <p className="font-bold text-gray-800">{resultados.marca || '-'}</p>
      </div>
      {puedeVerContrato && (
        <div className="bg-blue-50 rounded-xl p-3 border border-blue-200/40">
          <p className="text-[10px] font-bold uppercase tracking-wider text-blue-600 mb-1">Número de Contrato</p>
          <p className="font-bold text-blue-700">{resultados.numero_contrato || '-'}</p>
        </div>
      )}
    </div>
  );

  const mostrarSaldo = tipoBusqueda === 'lote' && Array.isArray(resultados?.movimientos)
    && resultados.movimientos.some((mov) => mov.saldo !== undefined && mov.saldo !== null);

  const lotesParaMostrar = Array.isArray(resultados?.lotes) ? resultados.lotes : [];
  // Limitar movimientos mostrados para evitar tablas muy pesadas
  const movimientosParaMostrar = Array.isArray(resultados?.movimientos) 
    ? resultados.movimientos.slice(0, 100) 
    : [];
  const totalMovimientos = resultados?.movimientos?.length || 0;

  const estadoClass = (estado = '') => {
    const upper = estado.toUpperCase();
    if (upper.includes('VENCIDO') || upper.includes('AGOTADO')) return 'bg-red-100 text-red-700';
    if (upper.includes('CRITICO') || upper.includes('PROXIMO')) return 'bg-amber-100 text-amber-800';
    return 'bg-emerald-100 text-emerald-700';
  };

  // Badge de contexto para el header - muestra rol y centro si aplica
  const badgeContent = esCentroUser && centroUsuarioNombre ? (
    <span className="flex items-center gap-2 rounded-full bg-primary/10 text-theme-primary px-4 py-1 text-sm font-semibold">
      <FaBuilding />
      {centroUsuarioNombre}
    </span>
  ) : null;

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        icon={FaHistory}
        title="Trazabilidad"
        subtitle={`Consulta el historial completo de productos y lotes | Rol: ${rolPrincipal}`}
        badge={badgeContent}
      />

      {/* ISS-FIX: Banner para usuarios CENTRO indicando filtro automático */}
      {esCentroUser && centroUsuarioNombre && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200/60 rounded-xl p-4 flex items-center gap-3 shadow-sm">
          <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
            <FaBuilding className="text-blue-600" />
          </div>
          <div>
            <p className="text-sm font-bold text-blue-800">
              Trazabilidad de: {centroUsuarioNombre}
            </p>
            <p className="text-xs text-blue-600/70">
              Los resultados se filtran automáticamente por tu centro asignado.
            </p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
        {/* Header del panel de búsqueda */}
        <div className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-hover)] px-6 py-4 text-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/15 backdrop-blur-sm flex items-center justify-center">
              <FaSearch className="text-lg" />
            </div>
            <div>
              <h2 className="text-base font-bold tracking-wide">Consulta de Trazabilidad</h2>
              <p className="text-xs text-white/70">Busca por clave, nombre de producto o número de lote</p>
            </div>
          </div>
        </div>

        <form onSubmit={handleBuscar} className="p-6 space-y-5">
          
          {/* Fila 1: Campos de entrada (Buscador y Centro) */}
          <div className="grid gap-4 md:grid-cols-3 items-end">
            
            {/* Buscador unificado */}
            <div className={`${esAdminOFarmacia ? 'md:col-span-2' : 'md:col-span-3'} relative`}>
              <label className="label-elevated">
                Buscar por lote, producto o clave
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  {loadingSugerencias ? (
                    <FaSpinner className="animate-spin text-[var(--color-primary)]" />
                  ) : (
                    <FaSearch className="text-gray-400" />
                  )}
                </div>
                <input
                  ref={inputRef}
                  type="text"
                  value={terminoBusqueda}
                  onChange={handleTerminoBusquedaChange}
                  onKeyDown={handleKeyDown}
                  onFocus={() => terminoBusqueda.length >= 2 && setMostrarSugerencias(true)}
                  placeholder="Ej: L-2024-001, MED-001, Paracetamol..."
                  className="input-elevated !pl-10 !pr-10"
                  disabled={loading}
                  autoComplete="off"
                />
                {terminoBusqueda && (
                  <button
                    type="button"
                    onClick={() => {
                      setTerminoBusqueda('');
                      setSugerencias([]);
                      setMostrarSugerencias(false);
                    }}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-gray-400 hover:text-[var(--color-primary)] transition-colors"
                  >
                    <FaTimes />
                  </button>
                )}
              </div>
              
              {/* Lista de sugerencias - elevated */}
              {mostrarSugerencias && sugerencias.length > 0 && (
                <div
                  ref={sugerenciasRef}
                  className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-xl shadow-xl max-h-60 overflow-auto"
                  style={{ boxShadow: '0 10px 40px rgba(147,32,67,0.12)' }}
                >
                  {sugerencias.map((sug, idx) => (
                    <button
                      key={`${sug.tipo}-${sug.id}`}
                      type="button"
                      onClick={() => seleccionarSugerencia(sug)}
                      className={`w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center gap-3 transition-colors border-b border-gray-50 last:border-0 ${
                        idx === indiceSugerencia ? 'bg-[var(--color-primary)]/5' : ''
                      }`}
                    >
                      <span className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm ${
                        sug.tipo === 'producto' ? 'bg-blue-100 text-blue-600' : 'bg-purple-100 text-purple-600'
                      }`}>
                        {sug.tipo === 'producto' ? '📦' : '🏷️'}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-sm truncate text-gray-800">{sug.display?.replace(/^[📦🏷️]\s*/, '') || sug.identificador}</p>
                        {sug.secundario && (
                          <p className="text-xs text-gray-500 truncate">{sug.secundario}</p>
                        )}
                      </div>
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-lg ${
                        sug.tipo === 'producto' ? 'bg-blue-50 text-blue-700' : 'bg-purple-50 text-purple-700'
                      }`}>
                        {sug.tipo === 'producto' ? 'Producto' : 'Lote'}
                      </span>
                    </button>
                  ))}
                </div>
              )}
              
              {mostrarSugerencias && terminoBusqueda.length >= 2 && sugerencias.length === 0 && !loadingSugerencias && (
                <div className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-xl shadow-xl p-4 text-center text-gray-500 text-sm">
                  No se encontraron coincidencias
                </div>
              )}
            </div>

            {/* Selector de centro (solo para admin/farmacia) */}
            {esAdminOFarmacia && (
              <div className="md:col-span-1">
                <label className="label-elevated flex items-center gap-1.5">
                  <FaBuilding className="text-[var(--color-primary)]" />
                  Centro
                  <span className="text-[10px] text-gray-400 font-normal lowercase">(para reportes)</span>
                </label>
                <select
                  value={centroFiltro}
                  onChange={(e) => setCentroFiltro(e.target.value)}
                  className="input-elevated"
                  disabled={loading}
                >
                  <option value="">🏥 Farmacia Central (por defecto)</option>
                  <option value="todos">🌐 Todos los Centros (consolidado)</option>
                  <optgroup label="── Centros Penitenciarios ──">
                    {centros.map((c) => (
                      <option key={c.id} value={c.id}>
                        🏢 {c.nombre}
                      </option>
                    ))}
                  </optgroup>
                </select>
              </div>
            )}
          </div>

          {/* Fila 2: Botones de Acción */}
          <div className="flex items-center justify-center gap-3 py-3 border-b border-gray-100 pb-5">
              <button
                type="submit"
                disabled={loading || !terminoBusqueda.trim()}
                className="btn-elevated-primary flex items-center justify-center gap-2 min-w-[220px] !px-8 !py-2.5"
                title="Buscar trazabilidad de un producto o lote específico"
              >
                {loading && !modoGlobal ? (
                  <>
                    <FaSpinner className="animate-spin" />
                    Buscando...
                  </>
                ) : (
                  <>
                    <FaSearch /> Buscar Producto/Lote
                  </>
                )}
              </button>
              
              <button
                type="button"
                onClick={limpiarBusqueda}
                disabled={loading || exportingPdf || exportingExcel}
                className="btn-elevated-cancel min-w-[120px] !px-6 !py-2.5"
              >
                Limpiar
              </button>
          </div>

          {/* Fila 3: Filtros de Fecha y Tipo */}
          <div className="section-elevated !p-5">
            <div className="section-elevated-title flex items-center gap-2">
              <FaFilter className="text-[var(--color-primary)]" />
              Filtros avanzados
            </div>
            <div className="flex flex-wrap items-end gap-4 justify-center mt-3">
              {/* Fecha inicio */}
              <div className="min-w-[160px]">
                <label className="label-elevated flex items-center gap-1">
                  <FaCalendarAlt className="text-[var(--color-primary)] text-[10px]" />
                  Fecha inicio
                </label>
                <input
                  type="date"
                  value={fechaInicio}
                  onChange={(e) => setFechaInicio(e.target.value)}
                  className="input-elevated"
                  disabled={loading}
                />
              </div>
              
              {/* Fecha fin */}
              <div className="min-w-[160px]">
                <label className="label-elevated flex items-center gap-1">
                  <FaCalendarAlt className="text-[var(--color-primary)] text-[10px]" />
                  Fecha fin
                </label>
                <input
                  type="date"
                  value={fechaFin}
                  onChange={(e) => setFechaFin(e.target.value)}
                  className="input-elevated"
                  disabled={loading}
                />
              </div>
              
              {/* Tipo movimiento */}
              <div className="min-w-[160px]">
                <label className="label-elevated flex items-center gap-1">
                  <FaFilter className="text-[var(--color-primary)] text-[10px]" />
                  Tipo movimiento
                </label>
                <select
                  value={tipoMovimiento}
                  onChange={(e) => setTipoMovimiento(e.target.value)}
                  className="input-elevated"
                  disabled={loading}
                >
                  <option value="">Todos</option>
                  <option value="entrada">📥 Entrada</option>
                  <option value="salida">📤 Salida</option>
                </select>
              </div>
              
              {/* Botón Reporte Global */}
              {esAdminOFarmacia && (
                <div className="flex flex-col items-center gap-1.5">
                  <button
                    type="button"
                    onClick={buscarGlobal}
                    disabled={loading}
                    className="flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm text-white transition-all shadow-md hover:shadow-lg hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
                    style={{ background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%)' }}
                    title="Ver todos los movimientos del sistema (filtrados por centro/fechas seleccionadas)"
                  >
                    {loading && modoGlobal ? (
                      <>
                        <FaSpinner className="animate-spin" />
                        Cargando...
                      </>
                    ) : (
                      <>
                        <FaGlobe />
                        Ver Movimientos
                      </>
                    )}
                  </button>
                  <span className="text-[10px] text-[var(--color-primary)] font-medium">
                    {centroFiltro === 'todos' 
                      ? '🌐 Todos los centros' 
                      : centroFiltro 
                        ? `🏢 ${centros.find(c => String(c.id) === String(centroFiltro))?.nombre || 'Centro seleccionado'}`
                        : '🏥 Farmacia Central'}
                  </span>
                </div>
              )}
            </div>
            
            {/* Indicador de filtros activos */}
            {(fechaInicio || fechaFin || tipoMovimiento) && (
              <div className="mt-4 pt-3 border-t border-gray-200 flex items-center justify-center">
                <div className="flex items-center gap-4">
                  <p className="text-xs text-[var(--color-primary)] font-semibold flex items-center gap-1.5">
                    <span className="w-2 h-2 bg-[var(--color-primary)] rounded-full animate-pulse"></span>
                    Filtros activos — se aplicarán a búsquedas y exportaciones
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      setFechaInicio('');
                      setFechaFin('');
                      setTipoMovimiento('');
                    }}
                    className="text-xs text-gray-500 hover:text-red-600 flex items-center gap-1 border-l pl-4 border-gray-300 transition-colors"
                  >
                    <FaTimes className="text-[10px]" /> Limpiar filtros
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Botón Control de Inventarios */}
          {esAdminOFarmacia && (
            <div className="flex flex-col items-center gap-2 pt-1">
              <button
                type="button"
                onClick={handleExportarControlInventarios}
                disabled={exportingControl || loading}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm text-white transition-all hover:shadow-lg hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-none shadow-md min-w-[300px] justify-center"
                style={{ background: 'linear-gradient(135deg, #047857 0%, #065f46 100%)' }}
                title="Exportar Control de Inventarios del Almacén Central (Formato Licitación)"
              >
                {exportingControl ? (
                  <>
                    <FaSpinner className="animate-spin" />
                    Generando...
                  </>
                ) : (
                  <>
                    <FaClipboardList />
                    📊 Exportar Control de Inventarios
                  </>
                )}
              </button>
              <span className="text-[10px] text-gray-400 text-center">
                Formato oficial &quot;Control de Inventarios del Almacén Central de Medicamentos&quot;
              </span>
            </div>
          )}

          {/* Indicador de tipo detectado */}
          {resultados && tipoBusqueda && !modoGlobal && (
            <div className="text-xs text-gray-500 flex items-center gap-2 flex-wrap bg-gray-50 rounded-xl px-4 py-2.5">
              <span className={`px-2.5 py-1 rounded-lg font-bold text-[10px] uppercase tracking-wider ${
                tipoBusqueda === 'producto' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'
              }`}>
                {tipoBusqueda === 'producto' ? '📦 Producto' : '🏷️ Lote'}
              </span>
              <span>Resultados para: <strong className="text-gray-700">{identificadorResultados}</strong></span>
              {(fechaInicio || fechaFin) && (
                <span className="text-[var(--color-primary)]">
                  | Período: {fechaInicio || '---'} a {fechaFin || 'hoy'}
                </span>
              )}
              {tipoMovimiento && (
                <span className="text-[var(--color-primary)]">
                  | Tipo: {tipoMovimiento}
                </span>
              )}
            </div>
          )}
          
          {/* Indicador de modo global */}
          {modoGlobal && resultadosGlobal && (
            <div className="bg-[var(--color-primary)]/5 border border-[var(--color-primary)]/20 rounded-xl p-4 flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <span className="px-3 py-1.5 rounded-lg bg-[var(--color-primary)]/10 text-[var(--color-primary)] font-bold text-sm">
                  {centroFiltro === 'todos' ? '🌐 Todos los Centros' : 
                   centroFiltro ? `🏢 Centro: ${centros.find(c => c.id.toString() === centroFiltro)?.nombre || centroFiltro}` : 
                   '🏥 Farmacia Central'}
                </span>
                <span className="text-sm text-gray-700">
                  <strong>{resultadosGlobal.total_movimientos}</strong> movimientos encontrados
                </span>
                {(fechaInicio || fechaFin) && (
                  <span className="text-sm text-gray-500">
                    | {fechaInicio || '---'} a {fechaFin || 'hoy'}
                  </span>
                )}
              </div>
              <span className="text-[10px] text-[var(--color-primary)] bg-[var(--color-primary)]/10 px-3 py-1.5 rounded-lg font-medium">
                {centroFiltro === 'todos' ? 'Datos combinados de todos los centros' : 
                 centroFiltro ? 'Solo datos de este centro' : 
                 'Solo datos de Farmacia Central'}
              </span>
            </div>
          )}
        </form>
      </div>

      {/* Estado de carga */}
      {loading && (
        <div className="text-center py-12 bg-white rounded-2xl shadow-lg border border-gray-100">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-t-transparent mx-auto spinner-institucional" />
          <p className="mt-4 text-gray-600 font-medium">Buscando información...</p>
          <p className="text-xs text-gray-400 mt-1">Consultando movimientos del sistema</p>
        </div>
      )}

      {/* Estado vacío */}
      {!loading && !resultados && !modoGlobal && (
        <div className="text-center py-14 bg-white rounded-2xl shadow-lg border border-gray-100">
          <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-4">
            <FaSearch className="text-2xl text-gray-400" />
          </div>
          <p className="text-gray-600 font-medium">
            Ingresa la clave de un producto, número de lote o nombre y presiona &quot;Buscar&quot;
          </p>
          <p className="text-xs text-gray-400 mt-2">
            El sistema detectará automáticamente si buscas un producto o un lote
          </p>
          {esAdminOFarmacia && (
            <p className="text-xs text-[var(--color-primary)] mt-3 font-medium">
              También puedes usar &quot;Ver Movimientos&quot; en los filtros avanzados para ver todo los movimientos
            </p>
          )}
        </div>
      )}

      {/* Resultados Globales */}
      {!loading && modoGlobal && resultadosGlobal && (
        <div className="space-y-6">
          {/* Header con estadísticas y exportación */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
            {/* Header del panel */}
            <div className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-hover)] px-6 py-4 text-white flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-white/15 backdrop-blur-sm flex items-center justify-center">
                  {centroFiltro === 'todos' ? (
                    <FaGlobe className="text-lg" />
                  ) : centroFiltro ? (
                    <FaBuilding className="text-lg" />
                  ) : (
                    <FaWarehouse className="text-lg" />
                  )}
                </div>
                <div>
                  <h2 className="text-base font-bold tracking-wide">
                    {centroFiltro === 'todos' ? 'Trazabilidad — Todos los Centros' : 
                     centroFiltro ? `Trazabilidad — ${centros.find(c => c.id.toString() === centroFiltro)?.nombre || 'Centro'}` : 
                     'Trazabilidad — Farmacia Central'}
                  </h2>
                  <p className="text-xs text-white/70">
                    {centroFiltro === 'todos' 
                      ? 'Movimientos combinados de todos los centros del sistema' 
                      : centroFiltro 
                        ? 'Movimientos específicos de este centro penitenciario'
                        : 'Movimientos del almacén central de medicamentos'}
                  </p>
                </div>
              </div>
              
              {/* Botones de exportar */}
              <div className="flex gap-2">
                <button
                  onClick={handleExportarExcel}
                  disabled={exportingExcel}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-sm text-white transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 bg-white/15 backdrop-blur-sm hover:bg-white/25"
                  title="Exportar a Excel"
                >
                  {exportingExcel ? (
                    <><FaSpinner className="animate-spin" /> Generando...</>
                  ) : (
                    <><FaFileExcel /> Excel</>
                  )}
                </button>
                <button
                  onClick={handleExportarPdf}
                  disabled={exportingPdf}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-sm text-white transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 bg-white/15 backdrop-blur-sm hover:bg-white/25"
                  title="Exportar a PDF"
                >
                  {exportingPdf ? (
                    <><FaSpinner className="animate-spin" /> Generando...</>
                  ) : (
                    <><FaFilePdf /> PDF</>
                  )}
                </button>
              </div>
            </div>
            
            {/* Estadísticas */}
            <div className="grid gap-4 md:grid-cols-5 p-6">
              <div className="bg-gradient-to-br from-blue-50 to-blue-100/50 p-4 rounded-xl border border-blue-200/40 text-center">
                <p className="text-[10px] font-bold uppercase tracking-wider text-blue-600 mb-1">Total Movimientos</p>
                <p className="text-2xl font-black text-blue-700">{resultadosGlobal.total_movimientos}</p>
              </div>
              <div className="bg-gradient-to-br from-green-50 to-green-100/50 p-4 rounded-xl border border-green-200/40 text-center">
                <p className="text-[10px] font-bold uppercase tracking-wider text-green-600 mb-1">Entradas</p>
                <p className="text-2xl font-black text-green-700">{resultadosGlobal.estadisticas?.total_entradas || 0}</p>
              </div>
              <div className="bg-gradient-to-br from-orange-50 to-orange-100/50 p-4 rounded-xl border border-orange-200/40 text-center">
                <p className="text-[10px] font-bold uppercase tracking-wider text-orange-600 mb-1">Salidas</p>
                <p className="text-2xl font-black text-orange-700">{resultadosGlobal.estadisticas?.total_salidas || 0}</p>
              </div>
              <div className="bg-gradient-to-br from-gray-50 to-gray-100/50 p-4 rounded-xl border border-gray-200/40 text-center">
                <p className="text-[10px] font-bold uppercase tracking-wider text-gray-600 mb-1">Lotes únicos</p>
                <p className="text-2xl font-black text-gray-700">{resultadosGlobal.estadisticas?.lotes_unicos || 0}</p>
              </div>
              <div className="bg-gradient-to-br from-[var(--color-primary)]/5 to-[var(--color-primary)]/10 p-4 rounded-xl border border-[var(--color-primary)]/15 text-center">
                <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-primary)] mb-1">Productos únicos</p>
                <p className="text-2xl font-black text-[var(--color-primary)]">{resultadosGlobal.estadisticas?.productos_unicos || 0}</p>
              </div>
            </div>
          </div>

          {/* Tabla de movimientos globales */}
          {resultadosGlobal.movimientos?.length > 0 && (
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                <h3 className="text-base font-bold flex items-center gap-2 text-gray-800">
                  <FaHistory className="text-[var(--color-primary)]" /> Movimientos
                  <span className="text-xs font-normal text-gray-400 bg-gray-100 px-2.5 py-1 rounded-lg">
                    {Math.min(resultadosGlobal.movimientos.length, 500)} de {resultadosGlobal.total_movimientos}
                  </span>
                </h3>
              </div>
              
              {/* Vista móvil: tarjetas */}
              <div className="lg:hidden space-y-3 p-4">
                {resultadosGlobal.movimientos.slice(0, 50).map((mov, idx) => (
                  <div key={mov.id || idx} className="p-4 border border-gray-200/60 rounded-xl bg-gradient-to-br from-white to-gray-50/50 hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between gap-2 mb-2.5">
                      <span className={`px-2.5 py-1 rounded-lg text-xs font-bold uppercase tracking-wider ${
                        mov.tipo === 'entrada' ? 'bg-green-100 text-green-700' :
                        mov.tipo === 'salida' ? 'bg-red-100 text-red-700' :
                        mov.tipo === 'ajuste' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {mov.tipo}
                      </span>
                      <span className="text-[10px] text-gray-500 font-medium">{mov.fecha_str || '-'}</span>
                    </div>
                    <div className="text-sm font-bold text-gray-900 truncate">{mov.producto_nombre || mov.producto || '-'}</div>
                    <div className="grid grid-cols-2 gap-1.5 text-xs text-gray-600 mt-2">
                      <div>Lote: <span className="font-medium text-gray-800">{mov.numero_lote || '-'}</span></div>
                      <div>Cant: <span className="font-bold text-gray-800">{mov.cantidad || 0}</span></div>
                      <div>Centro: <span className="font-medium">{mov.centro_nombre || '-'}</span></div>
                      <div>Usuario: <span className="font-medium">{mov.usuario_nombre || '-'}</span></div>
                    </div>
                  </div>
                ))}
                {resultadosGlobal.movimientos.length > 50 && (
                  <p className="text-[10px] text-gray-400 text-center py-3 font-medium">
                    Mostrando 50 de {resultadosGlobal.movimientos.length}. Usa escritorio para ver más.
                  </p>
                )}
              </div>
              
              {/* Vista desktop: tabla */}
              <div className="hidden lg:block w-full overflow-x-auto table-soft">
                <table className="w-full min-w-[700px] divide-y divide-gray-200 text-sm">
                  <thead className="thead-soft sticky top-0 z-10">
                    <tr>
                      <th className="px-3 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Fecha</th>
                      <th className="px-3 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Tipo</th>
                      <th className="px-3 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Producto</th>
                      <th className="px-3 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Lote</th>
                      <th className="px-3 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Cantidad</th>
                      <th className="px-3 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Centro</th>
                      <th className="px-3 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Usuario</th>
                      <th className="px-3 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">No. Expediente</th>
                      <th className="px-3 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Observaciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {resultadosGlobal.movimientos.slice(0, 100).map((mov, idx) => (
                      <tr key={mov.id || idx} className="hover:bg-gray-50/80 transition-colors">
                        <td className="px-3 py-2.5 text-xs text-gray-600">{mov.fecha_str || '-'}</td>
                        <td className="px-3 py-2.5">
                          <span
                            className={`px-2 py-1 text-[10px] font-bold uppercase tracking-wider rounded-lg ${
                              mov.tipo === 'ENTRADA'
                                ? 'bg-blue-100 text-blue-700'
                                : mov.tipo === 'AJUSTE'
                                  ? 'bg-gray-100 text-gray-700'
                                  : 'bg-orange-100 text-orange-700'
                            }`}
                          >
                            {mov.tipo}
                            {mov.subtipo_salida && (
                              <span className="ml-1 opacity-75">/{mov.subtipo_salida?.slice(0, 8)}</span>
                            )}
                          </span>
                        </td>
                        <td className="px-3 py-2.5">
                          <span className="font-bold text-xs text-gray-800">{mov.producto_clave}</span>
                          <br />
                          <span className="text-xs text-gray-500">{mov.producto_nombre?.slice(0, 25)}</span>
                        </td>
                        <td className="px-3 py-2.5 font-mono text-xs text-gray-700">{mov.lote}</td>
                        <td className="px-3 py-2.5 font-bold text-xs text-gray-800">{mov.cantidad}</td>
                        <td className="px-3 py-2.5 text-xs text-gray-600">{mov.centro?.slice(0, 20)}</td>
                        <td className="px-3 py-2.5 text-xs text-gray-600">{mov.usuario?.slice(0, 15)}</td>
                        <td className="px-3 py-2.5 text-xs font-semibold text-blue-700">{mov.numero_expediente || '-'}</td>
                        <td className="px-3 py-2.5 text-xs text-gray-500 max-w-[150px] truncate" title={mov.observaciones}>
                          {mov.observaciones?.slice(0, 40) || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {resultadosGlobal.movimientos.length > 100 && (
                <p className="text-[10px] text-gray-400 mt-3 text-center py-3 font-medium">
                  Para ver todos los movimientos, exporta a Excel o PDF
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Resultados individuales */}
      {!loading && resultados && !modoGlobal && (
        <div className="space-y-6">
          {/* Información principal */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-hover)] px-6 py-4 text-white flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-white/15 backdrop-blur-sm flex items-center justify-center">
                  {tipoBusqueda === 'producto' ? (
                    <FaBox className="text-lg" />
                  ) : (
                    <FaWarehouse className="text-lg" />
                  )}
                </div>
                <div>
                  <h2 className="text-base font-bold tracking-wide">
                    Información del {tipoBusqueda === 'producto' ? 'producto' : 'lote'}
                  </h2>
                  <p className="text-xs text-white/70">
                    Datos generales y estado actual
                    {identificadorResultados && (
                      <span className="ml-2 bg-white/15 px-2 py-0.5 rounded-lg text-white font-medium">({identificadorResultados})</span>
                    )}
                  </p>
                </div>
              </div>
              
              {/* Botones de exportar */}
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={handleExportarExcel}
                  disabled={exportingExcel || !resultados || (tipoBusqueda === 'lote' && !esAdminOFarmacia)}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-sm text-white transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 bg-white/15 backdrop-blur-sm hover:bg-white/25"
                  title={!esAdminOFarmacia && tipoBusqueda === 'lote' ? 'Requiere permisos de Admin/Farmacia' : 'Exportar a Excel'}
                >
                  {exportingExcel ? (
                    <><FaSpinner className="animate-spin" /> Generando...</>
                  ) : (
                    <><FaFileExcel /> Excel</>
                  )}
                </button>
                <button
                  onClick={handleExportarPdf}
                  disabled={exportingPdf || !resultados || (tipoBusqueda === 'lote' && !esAdminOFarmacia)}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-sm text-white transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 bg-white/15 backdrop-blur-sm hover:bg-white/25"
                  title={!esAdminOFarmacia && tipoBusqueda === 'lote' ? 'Requiere permisos de Admin/Farmacia' : 'Exportar a PDF'}
                >
                  {exportingPdf ? (
                    <><FaSpinner className="animate-spin" /> Generando...</>
                  ) : (
                    <><FaFilePdf /> PDF</>
                  )}
                </button>
                {/* FORMATO OFICIAL B: Solo para lotes */}
                {tipoBusqueda === 'lote' && esAdminOFarmacia && (
                  <button
                    onClick={handleExportarFormatoB}
                    disabled={exportingFormatoB || !resultados}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-sm text-white transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 bg-white/15 backdrop-blur-sm hover:bg-white/25"
                    title="Formato Oficial B - Tarjeta de Entradas/Salidas"
                  >
                    {exportingFormatoB ? (
                      <><FaSpinner className="animate-spin" /> Generando...</>
                    ) : (
                      <><FaClipboardList /> Formato B</>
                    )}
                  </button>
                )}
              </div>
            </div>
            
            <div className="p-6">
              {tipoBusqueda === 'producto' ? renderInfoProducto() : renderInfoLote()}
            </div>
          </div>

          {/* Alertas */}
          {renderAlertas()}

          {/* Lotes asociados (solo para productos) */}
          {tipoBusqueda === 'producto' && lotesParaMostrar.length > 0 && (
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100">
                <h3 className="text-base font-bold flex items-center gap-2 text-gray-800">
                  <FaWarehouse className="text-[var(--color-primary)]" /> Lotes asociados
                  <span className="text-xs font-normal text-gray-400 bg-gray-100 px-2.5 py-1 rounded-lg">{lotesParaMostrar.length}</span>
                </h3>
              </div>
              
              {/* Vista móvil: tarjetas */}
              <div className="lg:hidden space-y-3 p-4">
                {lotesParaMostrar.map((lote) => (
                  <div key={lote.numero_lote} className="p-4 border border-gray-200/60 rounded-xl bg-gradient-to-br from-white to-gray-50/50 hover:shadow-md transition-shadow">
                    <div className="flex items-center justify-between gap-2 mb-2.5">
                      <span className="font-bold text-gray-900">{lote.numero_lote}</span>
                      <span className={`px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-lg ${estadoClass(lote.estado)}`}>
                        {lote.estado || '-'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-gray-500 text-xs">Caducidad:</span>
                        <span className="ml-1 font-medium">{lote.fecha_caducidad ? new Date(lote.fecha_caducidad).toLocaleDateString() : '-'}</span>
                      </div>
                      <div>
                        <span className="text-gray-500 text-xs">Inv:</span>
                        <span className="ml-1 font-bold text-gray-800">{lote.cantidad_actual}</span>
                      </div>
                      {puedeVerContrato && lote.numero_contrato && (
                        <div className="col-span-2 text-xs text-gray-600 bg-gray-50 rounded-lg px-2 py-1">
                          Contrato: {lote.numero_contrato} {lote.marca && `| ${lote.marca}`}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Vista desktop: tabla */}
              <div className="hidden lg:block w-full overflow-x-auto table-soft">
                <table className="w-full min-w-[600px] divide-y divide-gray-200 text-sm">
                  <thead className="thead-soft sticky top-0 z-10">
                    <tr>
                      <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Lote</th>
                      <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Caducidad</th>
                      <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Inventario</th>
                      {puedeVerContrato && <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Contrato</th>}
                      {puedeVerContrato && <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Marca</th>}
                      <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Estado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {lotesParaMostrar.map((lote) => (
                      <tr key={lote.numero_lote} className="hover:bg-gray-50/80 transition-colors">
                        <td className="px-4 py-2.5 font-bold text-gray-800">{lote.numero_lote}</td>
                        <td className="px-4 py-2.5 text-gray-600">
                          {lote.fecha_caducidad ? new Date(lote.fecha_caducidad).toLocaleDateString() : '-'}
                        </td>
                        <td className="px-4 py-2.5 font-bold text-gray-800">{lote.cantidad_actual}</td>
                        {puedeVerContrato && <td className="px-4 py-2.5 text-gray-600">{lote.numero_contrato || '-'}</td>}
                        {puedeVerContrato && <td className="px-4 py-2.5 text-gray-600">{lote.marca || '-'}</td>}
                        <td className="px-4 py-2.5">
                          <span className={`px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-lg ${estadoClass(lote.estado)}`}>
                            {lote.estado || '-'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Historial de movimientos */}
          {movimientosParaMostrar.length > 0 && (
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                <h3 className="text-base font-bold flex items-center gap-2 text-gray-800">
                  <FaHistory className="text-[var(--color-primary)]" /> Historial de movimientos
                  {totalMovimientos > 100 && (
                    <span className="text-xs font-normal text-gray-400 bg-gray-100 px-2.5 py-1 rounded-lg">
                      100 de {totalMovimientos}
                    </span>
                  )}
                </h3>
              </div>
              
              {/* Vista móvil: tarjetas */}
              <div className="lg:hidden space-y-3 p-4">
                {movimientosParaMostrar.slice(0, 50).map((mov, idx) => (
                  <div key={mov.id || idx} className="p-4 border border-gray-200/60 rounded-xl bg-gradient-to-br from-white to-gray-50/50 hover:shadow-md transition-shadow">
                    <div className="flex items-center justify-between gap-2 mb-2.5">
                      <span className={`px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-lg ${
                        mov.tipo === 'ENTRADA' ? 'bg-blue-100 text-blue-700' :
                        mov.tipo === 'SALIDA' ? 'bg-red-100 text-red-700' :
                        mov.tipo === 'AJUSTE' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {mov.tipo}
                      </span>
                      <span className="text-[10px] text-gray-500 font-medium">{mov.fecha ? new Date(mov.fecha).toLocaleString() : '-'}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="font-bold text-gray-800">Cantidad: {mov.cantidad}</div>
                      {mostrarSaldo && <div>Saldo: <span className="font-medium">{mov.saldo_lote ?? '-'}</span></div>}
                      <div className="text-gray-600 text-xs">Centro: <span className="font-medium">{mov.centro_nombre || '-'}</span></div>
                      <div className="text-gray-600 text-xs">Usuario: <span className="font-medium">{mov.usuario_nombre || '-'}</span></div>
                      <div className="col-span-2 text-xs font-mono text-gray-500 bg-gray-50 rounded-lg px-2 py-1">Lote: {mov.numero_lote || '-'}</div>
                    </div>
                  </div>
                ))}
                {movimientosParaMostrar.length > 50 && (
                  <p className="text-[10px] text-gray-400 text-center py-3 font-medium">
                    Mostrando 50 de {movimientosParaMostrar.length}. Usa escritorio para ver más.
                  </p>
                )}
              </div>
              
              {/* Vista desktop: tabla */}
              <div className="hidden lg:block w-full overflow-x-auto table-soft">
                <table className="w-full min-w-[650px] divide-y divide-gray-200 text-sm">
                  <thead className="thead-soft sticky top-0 z-10">
                    <tr>
                      <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Fecha</th>
                      <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Tipo</th>
                      <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Cantidad</th>
                      {mostrarSaldo && <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap" title="Cantidad restante del lote después del movimiento">Saldo Lote</th>}
                      <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Centro</th>
                      <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Usuario</th>
                      <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-white whitespace-nowrap">Lote</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {movimientosParaMostrar.map((mov, idx) => (
                      <tr key={mov.id || idx} className="hover:bg-gray-50/80 transition-colors">
                        <td className="px-4 py-2.5 text-gray-600">
                          {mov.fecha ? new Date(mov.fecha).toLocaleString() : '-'}
                        </td>
                        <td className="px-4 py-2.5">
                          <span
                            className={`px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-lg ${
                              mov.tipo === 'ENTRADA'
                                ? 'bg-blue-100 text-blue-700'
                                : mov.tipo === 'AJUSTE'
                                  ? 'bg-gray-100 text-gray-700'
                                  : 'bg-orange-100 text-orange-700'
                            }`}
                          >
                            {mov.tipo}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 font-bold text-gray-800">{mov.cantidad}</td>
                        {mostrarSaldo && (
                          <td className="px-4 py-2.5 font-medium text-gray-700" title="Cantidad del lote después de este movimiento">
                            {mov.saldo ?? '-'}
                          </td>
                        )}
                        <td className="px-4 py-2.5 text-gray-600">{mov.centro || 'Farmacia Central'}</td>
                        <td className="px-4 py-2.5 text-gray-600">{mov.usuario || '-'}</td>
                        <td className="px-4 py-2.5 font-mono text-gray-700">{mov.lote || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {totalMovimientos > 100 && (
                <p className="text-[10px] text-gray-400 mt-3 text-center py-3 font-medium">
                  Para ver el historial completo, exporta el PDF de trazabilidad
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Trazabilidad;
