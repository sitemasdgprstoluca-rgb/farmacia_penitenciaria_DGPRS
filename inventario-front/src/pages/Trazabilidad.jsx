import { useState, useEffect, useCallback, useRef } from 'react';
import { trazabilidadAPI, centrosAPI, productosAPI, descargarArchivo } from '../services/api';
import { toast } from 'react-hot-toast';
import { FaSearch, FaBox, FaWarehouse, FaHistory, FaExclamationTriangle, FaFilePdf, FaFileExcel, FaBuilding, FaSpinner, FaInfoCircle, FaTimes, FaGlobe, FaCalendarAlt, FaFilter, FaClipboardList } from 'react-icons/fa';
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
  const [centroFiltro, setCentroFiltro] = useState('');
  
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
      setExportingPdf(true);
      try {
        const params = {};
        if (fechaInicio) params.fecha_inicio = fechaInicio;
        if (fechaFin) params.fecha_fin = fechaFin;
        if (centroFiltro) params.centro = centroFiltro;
        if (tipoMovimiento) params.tipo = tipoMovimiento;
        
        const response = await trazabilidadAPI.exportarGlobalPdf(params);
        const filename = `trazabilidad_global_${new Date().toISOString().split('T')[0]}.pdf`;
        descargarArchivo(response, filename);
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

    setExportingPdf(true);
    try {
      let response;
      let filename;
      
      // Preparar parámetros con filtros de fecha
      const params = {};
      if (fechaInicio) params.fecha_inicio = fechaInicio;
      if (fechaFin) params.fecha_fin = fechaFin;
      if (centroFiltro) params.centro = centroFiltro;
      
      if (tipoBusqueda === 'producto') {
        response = await trazabilidadAPI.exportarPdf(identificadorResultados, params);
        filename = `trazabilidad_producto_${identificadorResultados}_${new Date().toISOString().split('T')[0]}.pdf`;
      } else {
        const loteId = resultados?.id;
        response = await trazabilidadAPI.exportarLotePdf(identificadorResultados, loteId, params);
        filename = `trazabilidad_lote_${identificadorResultados}_${new Date().toISOString().split('T')[0]}.pdf`;
      }
      
      descargarArchivo(response, filename);
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
      // - vacío/undefined: Backend usa 'central' (Farmacia Central) por defecto
      // - 'todos': Ver todos los movimientos de todos los centros
      // - ID numérico: Centro específico
      if (centroFiltro) {
        params.centro = centroFiltro;
      }
      // Si no hay centroFiltro, el backend asume 'central' por defecto
      
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
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <FaExclamationTriangle className="text-amber-500" /> Alertas
        </h3>
        <div className="flex flex-wrap gap-2">
          {resultados.alertas.map((alerta, index) => (
            <span
              key={`${alerta.tipo || 'alerta'}-${index}`}
              className={`px-3 py-1 rounded-full text-xs ${badgeClass(alerta.nivel)}`}
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
      <div>
        <p className="text-xs text-gray-500">Clave</p>
        <p className="font-semibold">{resultados.codigo}</p>
      </div>
      <div className="md:col-span-2">
        <p className="text-xs text-gray-500">Nombre / Descripción</p>
        <p className="font-semibold">{resultados.nombre || resultados.descripcion}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Unidad</p>
        <p className="font-semibold">{resultados.unidad_medida || 'PIEZA'}</p>
      </div>
      {/* Presentación - forma farmacéutica */}
      {resultados.presentacion && (
        <div className="md:col-span-2">
          <p className="text-xs text-gray-500">Presentación</p>
          <p className="font-semibold">{resultados.presentacion}</p>
        </div>
      )}
      {/* Precio unitario */}
      {resultados.precio_unitario > 0 && (
        <div>
          <p className="text-xs text-gray-500">Precio Unitario</p>
          <p className="font-semibold text-green-600">${parseFloat(resultados.precio_unitario).toFixed(2)}</p>
        </div>
      )}
      <div>
        <p className="text-xs text-gray-500">Inventario actual</p>
        <p className="text-2xl font-bold text-violet-600">{resultados.stock_actual ?? 0}</p>
        {resultados.stock_minimo != null && (
          <p className="text-xs text-gray-500 mt-1">Inv. Mínimo: {resultados.stock_minimo}</p>
        )}
      </div>
    </div>
  );

  const renderInfoLote = () => (
    <div className="grid gap-4 md:grid-cols-4">
      <div>
        <p className="text-xs text-gray-500">Número de Lote</p>
        <p className="font-semibold">{resultados.numero_lote}</p>
      </div>
      <div className="md:col-span-2">
        <p className="text-xs text-gray-500">Producto</p>
        <p className="font-semibold">
          {resultados.producto?.codigo} - {resultados.producto?.nombre}
        </p>
        {resultados.producto?.presentacion && (
          <p className="text-xs text-gray-500 mt-1">Presentación: {resultados.producto.presentacion}</p>
        )}
      </div>
      <div>
        <p className="text-xs text-gray-500">Caducidad</p>
        <p className="font-semibold">
          {resultados.fecha_caducidad ? new Date(resultados.fecha_caducidad).toLocaleDateString() : '-'}
        </p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Cantidad actual</p>
        <p className="text-2xl font-bold text-violet-600">{resultados.cantidad_actual}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Cantidad inicial</p>
        <p className="font-semibold">{resultados.cantidad_inicial}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Estado</p>
        <p className="font-semibold">{resultados.estado || '-'}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Centro</p>
        <p className="font-semibold">{resultados.centro || 'Farmacia Central'}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500">Marca</p>
        <p className="font-semibold">{resultados.marca || '-'}</p>
      </div>
      {/* Campos de trazabilidad de contratos - Solo visible para ADMIN y FARMACIA */}
      {puedeVerContrato && (
        <div>
          <p className="text-xs text-gray-500">Número de Contrato</p>
          <p className="font-semibold text-blue-600">{resultados.numero_contrato || '-'}</p>
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
    <span className="flex items-center gap-2 rounded-full bg-white/20 px-4 py-1 text-sm font-semibold">
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
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center gap-3">
          <div className="bg-blue-100 p-2 rounded-lg">
            <FaInfoCircle className="text-blue-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-blue-800">
              Trazabilidad de: {centroUsuarioNombre}
            </p>
            <p className="text-xs text-blue-600">
              Los resultados se filtran automáticamente por tu centro asignado.
            </p>
          </div>
        </div>
      )}

      <div className="bg-white p-6 rounded-lg shadow">
        <form onSubmit={handleBuscar} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            {/* Buscador unificado */}
            <div className="md:col-span-2 relative">
              <label className="block text-sm font-medium mb-2">
                Buscar por lote, producto o clave
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  {loadingSugerencias ? (
                    <FaSpinner className="animate-spin text-gray-400" />
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
                  className="w-full pl-10 pr-10 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                  >
                    <FaTimes />
                  </button>
                )}
              </div>
              
              {/* Lista de sugerencias */}
              {mostrarSugerencias && sugerencias.length > 0 && (
                <div
                  ref={sugerenciasRef}
                  className="absolute z-50 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-60 overflow-auto"
                >
                  {sugerencias.map((sug, idx) => (
                    <button
                      key={`${sug.tipo}-${sug.id}`}
                      type="button"
                      onClick={() => seleccionarSugerencia(sug)}
                      className={`w-full px-4 py-2 text-left hover:bg-gray-100 flex items-center gap-3 ${
                        idx === indiceSugerencia ? 'bg-blue-50' : ''
                      }`}
                    >
                      <span className="text-lg">{sug.tipo === 'producto' ? '📦' : '🏷️'}</span>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">{sug.display?.replace(/^[📦🏷️]\s*/, '') || sug.identificador}</p>
                        {sug.secundario && (
                          <p className="text-xs text-gray-500 truncate">{sug.secundario}</p>
                        )}
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        sug.tipo === 'producto' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'
                      }`}>
                        {sug.tipo === 'producto' ? 'Producto' : 'Lote'}
                      </span>
                    </button>
                  ))}
                </div>
              )}
              
              {mostrarSugerencias && terminoBusqueda.length >= 2 && sugerencias.length === 0 && !loadingSugerencias && (
                <div className="absolute z-50 w-full mt-1 bg-white border rounded-lg shadow-lg p-3 text-center text-gray-500 text-sm">
                  No se encontraron coincidencias
                </div>
              )}
            </div>

            {/* Selector de centro (solo para admin/farmacia) - Con opciones claras y organizadas */}
            {esAdminOFarmacia && (
              <div>
                <label className="block text-sm font-medium mb-2">
                  Filtrar por Centro
                  <span className="ml-1 text-xs text-gray-400 font-normal">(reportes y exportaciones)</span>
                </label>
                <select
                  value={centroFiltro}
                  onChange={(e) => setCentroFiltro(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
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
                <p className="text-xs text-gray-500 mt-1">
                  {centroFiltro === 'todos' 
                    ? '📊 Verás movimientos de TODOS los centros combinados'
                    : centroFiltro 
                      ? '🏢 Verás solo movimientos de este centro específico'
                      : '🏥 Verás solo movimientos de Farmacia Central'}
                </p>
              </div>
            )}

            {/* Botones de acción - ISS-UX: Separados y mejor etiquetados */}
            <div className="flex items-end gap-2">
              <button
                type="submit"
                disabled={loading || !terminoBusqueda.trim()}
                className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-all"
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
                className="px-4 py-2 border rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                Limpiar
              </button>
            </div>
          </div>

          {/* Filtros de fecha y tipo - SIEMPRE VISIBLES */}
          <div className="bg-gradient-to-r from-gray-50 to-blue-50 p-4 rounded-xl border border-gray-200">
            <div className="flex flex-wrap items-end gap-4">
              {/* Fecha inicio */}
              <div className="flex-1 min-w-[140px]">
                <label className="block text-xs font-semibold mb-1.5 text-gray-600">
                  <FaCalendarAlt className="inline mr-1 text-blue-500" />
                  Fecha inicio
                </label>
                <input
                  type="date"
                  value={fechaInicio}
                  onChange={(e) => setFechaInicio(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white"
                  disabled={loading}
                />
              </div>
              
              {/* Fecha fin */}
              <div className="flex-1 min-w-[140px]">
                <label className="block text-xs font-semibold mb-1.5 text-gray-600">
                  <FaCalendarAlt className="inline mr-1 text-blue-500" />
                  Fecha fin
                </label>
                <input
                  type="date"
                  value={fechaFin}
                  onChange={(e) => setFechaFin(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white"
                  disabled={loading}
                />
              </div>
              
              {/* Tipo movimiento */}
              <div className="flex-1 min-w-[140px]">
                <label className="block text-xs font-semibold mb-1.5 text-gray-600">
                  <FaFilter className="inline mr-1 text-purple-500" />
                  Tipo movimiento
                </label>
                <select
                  value={tipoMovimiento}
                  onChange={(e) => setTipoMovimiento(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white"
                  disabled={loading}
                >
                  <option value="">Todos</option>
                  <option value="entrada">📥 Entrada</option>
                  <option value="salida">📤 Salida</option>
                </select>
              </div>
              
              {/* Botón Reporte Global - ISS-UX: Mejor etiquetado y tooltip */}
              {esAdminOFarmacia && (
                <div className="flex-shrink-0">
                  <button
                    type="button"
                    onClick={buscarGlobal}
                    disabled={loading}
                    className="bg-gradient-to-r from-purple-600 to-purple-700 text-white px-5 py-2 rounded-lg hover:from-purple-700 hover:to-purple-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-all shadow-md hover:shadow-lg"
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
                        Ver Todos los Movimientos
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
            
            {/* Indicador de filtros activos */}
            {(fechaInicio || fechaFin || tipoMovimiento) && (
              <div className="mt-3 pt-3 border-t border-gray-200 flex items-center justify-between">
                <p className="text-xs text-blue-600 font-medium flex items-center gap-1">
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                  Filtros activos - se aplicarán a búsquedas y exportaciones
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setFechaInicio('');
                    setFechaFin('');
                    setTipoMovimiento('');
                  }}
                  className="text-xs text-gray-500 hover:text-red-600 flex items-center gap-1"
                >
                  <FaTimes className="text-[10px]" /> Limpiar filtros
                </button>
              </div>
            )}
          </div>

          {/* Botón Control de Inventarios */}
          {esAdminOFarmacia && (
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleExportarControlInventarios}
                disabled={exportingControl || loading}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg font-semibold text-white transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 shadow-md"
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
                    📊 Exportar Control de Inventarios (Formato Licitación)
                  </>
                )}
              </button>
              <span className="text-xs text-gray-500">
                Genera el Excel con el formato oficial de &quot;Control de Inventarios del Almacén Central de Medicamentos&quot;
              </span>
            </div>
          )}

          {/* Indicador de tipo detectado */}
          {resultados && tipoBusqueda && !modoGlobal && (
            <div className="text-xs text-gray-500 flex items-center gap-2 flex-wrap">
              <span className={`px-2 py-0.5 rounded-full ${
                tipoBusqueda === 'producto' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'
              }`}>
                {tipoBusqueda === 'producto' ? '📦 Producto' : '🏷️ Lote'}
              </span>
              <span>Resultados para: <strong>{identificadorResultados}</strong></span>
              {(fechaInicio || fechaFin) && (
                <span className="text-blue-600">
                  | Período: {fechaInicio || '---'} a {fechaFin || 'hoy'}
                </span>
              )}
              {tipoMovimiento && (
                <span className="text-blue-600">
                  | Tipo: {tipoMovimiento}
                </span>
              )}
            </div>
          )}
          
          {/* Indicador de modo global - Muestra claramente qué centro se está viendo */}
          {modoGlobal && resultadosGlobal && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="px-3 py-1 rounded-full bg-purple-100 text-purple-700 font-semibold text-sm">
                  {centroFiltro === 'todos' ? '🌐 Todos los Centros' : 
                   centroFiltro ? `🏢 Centro: ${centros.find(c => c.id.toString() === centroFiltro)?.nombre || centroFiltro}` : 
                   '🏥 Farmacia Central'}
                </span>
                <span className="text-sm text-purple-700">
                  <strong>{resultadosGlobal.total_movimientos}</strong> movimientos encontrados
                </span>
                {(fechaInicio || fechaFin) && (
                  <span className="text-sm text-purple-600">
                    | {fechaInicio || '---'} a {fechaFin || 'hoy'}
                  </span>
                )}
              </div>
              <span className="text-xs text-purple-500 bg-purple-100 px-2 py-1 rounded">
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
        <div className="text-center py-8 bg-white rounded-lg shadow">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-t-transparent mx-auto spinner-institucional" />
          <p className="mt-3 text-gray-600">Buscando información...</p>
        </div>
      )}

      {/* Estado vacío */}
      {!loading && !resultados && !modoGlobal && (
        <div className="text-center py-8 bg-white rounded-lg shadow">
          <FaSearch className="text-4xl text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">
            Ingresa la clave de un producto, número de lote o nombre y presiona &quot;Buscar&quot;
          </p>
          <p className="text-xs text-gray-400 mt-2">
            El sistema detectará automáticamente si buscas un producto o un lote
          </p>
          {esAdminOFarmacia && (
            <p className="text-xs text-purple-500 mt-2">
              También puedes usar &quot;Reporte Global&quot; en los filtros avanzados para ver todos los movimientos
            </p>
          )}
        </div>
      )}

      {/* Resultados Globales */}
      {!loading && modoGlobal && resultadosGlobal && (
        <div className="space-y-6">
          {/* Header con estadísticas y exportación */}
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className={`p-3 rounded-lg ${
                  centroFiltro === 'todos' ? 'bg-indigo-100' : 
                  centroFiltro ? 'bg-blue-100' : 'bg-purple-100'
                }`}>
                  {centroFiltro === 'todos' ? (
                    <FaGlobe className="text-indigo-600 text-2xl" />
                  ) : centroFiltro ? (
                    <FaBuilding className="text-blue-600 text-2xl" />
                  ) : (
                    <FaWarehouse className="text-purple-600 text-2xl" />
                  )}
                </div>
                <div>
                  <h2 className="text-lg font-bold">
                    {centroFiltro === 'todos' ? 'Trazabilidad - Todos los Centros' : 
                     centroFiltro ? `Trazabilidad - ${centros.find(c => c.id.toString() === centroFiltro)?.nombre || 'Centro'}` : 
                     'Trazabilidad - Farmacia Central'}
                  </h2>
                  <p className="text-sm text-gray-600">
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
                  className="flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-white transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                  style={{ background: 'linear-gradient(135deg, #059669 0%, #047857 100%)' }}
                  title="Exportar a Excel"
                >
                  {exportingExcel ? (
                    <>
                      <FaSpinner className="animate-spin" />
                      Generando...
                    </>
                  ) : (
                    <>
                      <FaFileExcel />
                      Excel
                    </>
                  )}
                </button>
                <button
                  onClick={handleExportarPdf}
                  disabled={exportingPdf}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-white transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                  style={{ background: 'linear-gradient(135deg, #DC2626 0%, #991B1B 100%)' }}
                  title="Exportar a PDF"
                >
                  {exportingPdf ? (
                    <>
                      <FaSpinner className="animate-spin" />
                      Generando...
                    </>
                  ) : (
                    <>
                      <FaFilePdf />
                      PDF
                    </>
                  )}
                </button>
              </div>
            </div>
            
            {/* Estadísticas */}
            <div className="grid gap-4 md:grid-cols-5">
              <div className="bg-blue-50 p-3 rounded-lg text-center">
                <p className="text-xs text-blue-600">Total Movimientos</p>
                <p className="text-2xl font-bold text-blue-700">{resultadosGlobal.total_movimientos}</p>
              </div>
              <div className="bg-green-50 p-3 rounded-lg text-center">
                <p className="text-xs text-green-600">Entradas</p>
                <p className="text-2xl font-bold text-green-700">{resultadosGlobal.estadisticas?.total_entradas || 0}</p>
              </div>
              <div className="bg-orange-50 p-3 rounded-lg text-center">
                <p className="text-xs text-orange-600">Salidas</p>
                <p className="text-2xl font-bold text-orange-700">{resultadosGlobal.estadisticas?.total_salidas || 0}</p>
              </div>
              <div className="bg-gray-50 p-3 rounded-lg text-center">
                <p className="text-xs text-gray-600">Lotes únicos</p>
                <p className="text-2xl font-bold text-gray-700">{resultadosGlobal.estadisticas?.lotes_unicos || 0}</p>
              </div>
              <div className="bg-purple-50 p-3 rounded-lg text-center">
                <p className="text-xs text-purple-600">Productos únicos</p>
                <p className="text-2xl font-bold text-purple-700">{resultadosGlobal.estadisticas?.productos_unicos || 0}</p>
              </div>
            </div>
          </div>

          {/* Tabla de movimientos globales */}
          {resultadosGlobal.movimientos?.length > 0 && (
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <FaHistory /> Movimientos
                <span className="text-sm font-normal text-gray-500">
                  (mostrando {Math.min(resultadosGlobal.movimientos.length, 500)} de {resultadosGlobal.total_movimientos})
                </span>
              </h3>
              <div className="w-full overflow-x-auto rounded-lg border border-gray-200 shadow-md">
                <table className="w-full min-w-[1100px] divide-y divide-gray-200 text-sm">
                  <thead className="bg-theme-gradient sticky top-0 z-10">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Fecha</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Tipo</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Producto</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Lote</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Cantidad</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Centro</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Usuario</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">No. Expediente</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Observaciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {resultadosGlobal.movimientos.slice(0, 100).map((mov, idx) => (
                      <tr key={mov.id || idx} className="hover:bg-gray-50">
                        <td className="px-3 py-2 text-xs">{mov.fecha_str || '-'}</td>
                        <td className="px-3 py-2">
                          <span
                            className={`px-2 py-1 text-xs rounded-full ${
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
                        <td className="px-3 py-2">
                          <span className="font-medium text-xs">{mov.producto_clave}</span>
                          <br />
                          <span className="text-xs text-gray-500">{mov.producto_nombre?.slice(0, 25)}</span>
                        </td>
                        <td className="px-3 py-2 font-mono text-xs">{mov.lote}</td>
                        <td className="px-3 py-2 font-semibold text-xs">{mov.cantidad}</td>
                        <td className="px-3 py-2 text-xs">{mov.centro?.slice(0, 20)}</td>
                        <td className="px-3 py-2 text-xs">{mov.usuario?.slice(0, 15)}</td>
                        <td className="px-3 py-2 text-xs font-medium text-blue-700">{mov.numero_expediente || '-'}</td>
                        <td className="px-3 py-2 text-xs text-gray-600 max-w-[150px] truncate" title={mov.observaciones}>
                          {mov.observaciones?.slice(0, 40) || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {resultadosGlobal.movimientos.length > 100 && (
                <p className="text-xs text-gray-500 mt-3 text-center">
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
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="bg-violet-100 p-3 rounded-lg">
                  {tipoBusqueda === 'producto' ? (
                    <FaBox className="text-violet-600 text-2xl" />
                  ) : (
                    <FaWarehouse className="text-violet-600 text-2xl" />
                  )}
                </div>
                <div>
                  <h2 className="text-lg font-bold">
                    Información del {tipoBusqueda === 'producto' ? 'producto' : 'lote'}
                  </h2>
                  <p className="text-sm text-gray-600">
                    Datos generales y estado actual
                    {identificadorResultados && (
                      <span className="ml-2 text-violet-600 font-medium">({identificadorResultados})</span>
                    )}
                  </p>
                </div>
              </div>
              
              {/* Botones de exportar */}
              <div className="flex gap-2">
                <button
                  onClick={handleExportarExcel}
                  disabled={exportingExcel || !resultados || (tipoBusqueda === 'lote' && !esAdminOFarmacia)}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-white transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                  style={{ background: 'linear-gradient(135deg, #059669 0%, #047857 100%)' }}
                  title={!esAdminOFarmacia && tipoBusqueda === 'lote' ? 'Requiere permisos de Admin/Farmacia' : 'Exportar a Excel'}
                >
                  {exportingExcel ? (
                    <>
                      <FaSpinner className="animate-spin" />
                      Generando...
                    </>
                  ) : (
                    <>
                      <FaFileExcel />
                      Excel
                    </>
                  )}
                </button>
                <button
                  onClick={handleExportarPdf}
                  disabled={exportingPdf || !resultados || (tipoBusqueda === 'lote' && !esAdminOFarmacia)}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-white transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                  style={{ background: 'linear-gradient(135deg, #DC2626 0%, #991B1B 100%)' }}
                  title={!esAdminOFarmacia && tipoBusqueda === 'lote' ? 'Requiere permisos de Admin/Farmacia' : 'Exportar a PDF'}
                >
                  {exportingPdf ? (
                    <>
                      <FaSpinner className="animate-spin" />
                      Generando...
                    </>
                  ) : (
                    <>
                      <FaFilePdf />
                      PDF
                    </>
                  )}
                </button>
              </div>
            </div>
            
            {tipoBusqueda === 'producto' ? renderInfoProducto() : renderInfoLote()}
          </div>

          {/* Alertas */}
          {renderAlertas()}

          {/* Lotes asociados (solo para productos) */}
          {tipoBusqueda === 'producto' && lotesParaMostrar.length > 0 && (
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <FaWarehouse /> Lotes asociados ({lotesParaMostrar.length})
              </h3>
              <div className="w-full overflow-x-auto rounded-lg border border-gray-200 shadow-md">
                <table className="w-full min-w-[800px] divide-y divide-gray-200 text-sm">
                  <thead className="bg-theme-gradient sticky top-0 z-10">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Lote</th>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Caducidad</th>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Inventario</th>
                      {puedeVerContrato && <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Contrato</th>}
                      {puedeVerContrato && <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Marca</th>}
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Estado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {lotesParaMostrar.map((lote) => (
                      <tr key={lote.numero_lote} className="hover:bg-gray-50">
                        <td className="px-4 py-2 font-semibold">{lote.numero_lote}</td>
                        <td className="px-4 py-2">
                          {lote.fecha_caducidad ? new Date(lote.fecha_caducidad).toLocaleDateString() : '-'}
                        </td>
                        <td className="px-4 py-2">{lote.cantidad_actual}</td>
                        {puedeVerContrato && <td className="px-4 py-2 text-gray-600">{lote.numero_contrato || '-'}</td>}
                        {puedeVerContrato && <td className="px-4 py-2 text-gray-600">{lote.marca || '-'}</td>}
                        <td className="px-4 py-2">
                          <span className={`px-2 py-1 text-xs rounded-full ${estadoClass(lote.estado)}`}>
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
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <FaHistory /> Historial de movimientos
                {totalMovimientos > 100 && (
                  <span className="text-sm font-normal text-gray-500">
                    (mostrando 100 de {totalMovimientos})
                  </span>
                )}
              </h3>
              <div className="w-full overflow-x-auto rounded-lg border border-gray-200 shadow-md">
                <table className="w-full min-w-[900px] divide-y divide-gray-200 text-sm">
                  <thead className="bg-theme-gradient sticky top-0 z-10">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Fecha</th>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Tipo</th>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Cantidad</th>
                      {mostrarSaldo && <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap" title="Cantidad restante del lote después del movimiento">Saldo Lote</th>}
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Centro</th>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Usuario</th>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Lote</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {movimientosParaMostrar.map((mov, idx) => (
                      <tr key={mov.id || idx} className="hover:bg-gray-50">
                        <td className="px-4 py-2">
                          {mov.fecha ? new Date(mov.fecha).toLocaleString() : '-'}
                        </td>
                        <td className="px-4 py-2">
                          <span
                            className={`px-2 py-1 text-xs rounded-full ${
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
                        <td className="px-4 py-2 font-semibold">{mov.cantidad}</td>
                        {mostrarSaldo && (
                          <td className="px-4 py-2" title="Cantidad del lote después de este movimiento">
                            {mov.saldo ?? '-'}
                          </td>
                        )}
                        <td className="px-4 py-2">{mov.centro || 'Farmacia Central'}</td>
                        <td className="px-4 py-2">{mov.usuario || '-'}</td>
                        <td className="px-4 py-2">{mov.lote || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {totalMovimientos > 100 && (
                <p className="text-xs text-gray-500 mt-3 text-center">
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
