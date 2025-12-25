/**
 * Componente SalidaMasiva - Solo para Farmacia Central
 * Permite seleccionar múltiples productos/lotes de un catálogo visual
 * y procesarlos de una vez con generación de hoja de entrega para firma.
 * 
 * MEJORADO: Ahora muestra catálogo completo de productos disponibles
 * similar a Requisiciones, con selección visual y cantidades ajustables.
 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { toast } from 'react-hot-toast';
import {
  FaPlus,
  FaMinus,
  FaTrash,
  FaSearch,
  FaTruck,
  FaFileDownload,
  FaSpinner,
  FaBox,
  FaClipboardList,
  FaCheckCircle,
  FaBuilding,
  FaTimes,
  FaShoppingCart,
  FaArrowLeft,
  FaExclamationTriangle,
} from 'react-icons/fa';
import { salidaMasivaAPI, centrosAPI, descargarArchivo } from '../services/api';

const SalidaMasiva = ({ onClose, onSuccess }) => {
  // Estado del formulario
  const [centroDestino, setCentroDestino] = useState('');
  const [observaciones, setObservaciones] = useState('');
  const [items, setItems] = useState([]); // Carrito de items seleccionados
  
  // Catálogo de lotes disponibles
  const [catalogoLotes, setCatalogoLotes] = useState([]);
  const [loadingCatalogo, setLoadingCatalogo] = useState(false);
  const [catalogoBusqueda, setCatalogoBusqueda] = useState('');
  const [totalLotesDisponibles, setTotalLotesDisponibles] = useState(0);
  
  // Vista: 'catalogo' | 'carrito'
  const [vista, setVista] = useState('catalogo');
  
  // Estado de centros
  const [centros, setCentros] = useState([]);
  const [loadingCentros, setLoadingCentros] = useState(true);
  
  // Estado de procesamiento
  const [procesando, setProcesando] = useState(false);
  const [resultado, setResultado] = useState(null);
  
  // Ref para debounce de búsqueda
  const searchTimeoutRef = useRef(null);
  
  // Cargar centros al montar
  useEffect(() => {
    const cargarCentros = async () => {
      try {
        const resp = await centrosAPI.getAll({ page_size: 100, ordering: 'nombre' });
        setCentros(resp.data.results || resp.data || []);
      } catch (err) {
        console.error('Error cargando centros:', err);
        toast.error('Error al cargar centros');
      } finally {
        setLoadingCentros(false);
      }
    };
    cargarCentros();
  }, []);
  
  // Cargar catálogo de lotes disponibles
  const cargarCatalogo = useCallback(async (termino = '') => {
    setLoadingCatalogo(true);
    try {
      const params = {
        page_size: 200,
        ordering: 'producto__descripcion,fecha_caducidad',
      };
      if (termino.trim()) {
        params.search = termino.trim();
      }
      
      const resp = await salidaMasivaAPI.lotesDisponibles(params);
      const lotes = resp.data.results || resp.data || [];
      setCatalogoLotes(lotes);
      setTotalLotesDisponibles(resp.data.count || lotes.length);
    } catch (err) {
      console.error('Error cargando catálogo:', err);
      setCatalogoLotes([]);
      toast.error('Error al cargar productos disponibles');
    } finally {
      setLoadingCatalogo(false);
    }
  }, []);
  
  // Cargar catálogo inicial
  useEffect(() => {
    cargarCatalogo();
  }, [cargarCatalogo]);
  
  // Handler de búsqueda con debounce
  const handleBusquedaChange = useCallback((valor) => {
    setCatalogoBusqueda(valor);
    
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    
    searchTimeoutRef.current = setTimeout(() => {
      cargarCatalogo(valor);
    }, 300);
  }, [cargarCatalogo]);
  
  // Cleanup timeout
  useEffect(() => {
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, []);
  
  // Verificar si un lote está en el carrito
  const loteEnCarrito = useCallback((loteId) => {
    return items.some(item => item.lote_id === loteId);
  }, [items]);
  
  // Obtener cantidad en carrito de un lote
  const getCantidadEnCarrito = useCallback((loteId) => {
    const item = items.find(i => i.lote_id === loteId);
    return item ? item.cantidad : 0;
  }, [items]);
  
  // Agregar item al carrito
  const agregarItem = useCallback((lote, cantidad = 1) => {
    const existe = items.find(item => item.lote_id === lote.id);
    
    if (existe) {
      // Actualizar cantidad
      const nuevaCantidad = Math.min(existe.cantidad + cantidad, lote.cantidad_disponible);
      setItems(items.map(item => 
        item.lote_id === lote.id 
          ? { ...item, cantidad: nuevaCantidad }
          : item
      ));
    } else {
      // Agregar nuevo
      setItems([...items, {
        lote_id: lote.id,
        numero_lote: lote.numero_lote,
        producto_clave: lote.producto_clave,
        producto_nombre: lote.producto_nombre,
        unidad_medida: lote.unidad_medida,
        cantidad_disponible: lote.cantidad_disponible,
        fecha_caducidad: lote.fecha_caducidad,
        cantidad: Math.min(cantidad, lote.cantidad_disponible),
      }]);
    }
  }, [items]);
  
  // Incrementar cantidad de un item
  const incrementarCantidad = useCallback((loteId) => {
    setItems(items.map(item => {
      if (item.lote_id === loteId) {
        const nuevaCantidad = Math.min(item.cantidad + 1, item.cantidad_disponible);
        return { ...item, cantidad: nuevaCantidad };
      }
      return item;
    }));
  }, [items]);
  
  // Decrementar cantidad de un item
  const decrementarCantidad = useCallback((loteId) => {
    setItems(items.map(item => {
      if (item.lote_id === loteId) {
        const nuevaCantidad = Math.max(item.cantidad - 1, 0);
        return { ...item, cantidad: nuevaCantidad };
      }
      return item;
    }).filter(item => item.cantidad > 0)); // Eliminar si llega a 0
  }, [items]);
  
  // Actualizar cantidad de un item - solo enteros positivos
  const actualizarCantidad = useCallback((loteId, cantidad) => {
    // Limpiar cualquier caracter no numérico
    const valorLimpio = cantidad.toString().replace(/[^0-9]/g, '');
    const cantidadNum = parseInt(valorLimpio) || 0;
    
    if (cantidadNum <= 0) {
      setItems(items.filter(item => item.lote_id !== loteId));
      return;
    }
    
    setItems(items.map(item => {
      if (item.lote_id === loteId) {
        const nuevaCantidad = Math.min(cantidadNum, item.cantidad_disponible);
        if (cantidadNum > item.cantidad_disponible) {
          toast.error(`Stock máximo: ${item.cantidad_disponible}`);
        }
        return { ...item, cantidad: nuevaCantidad };
      }
      return item;
    }));
  }, [items]);
  
  // Handler para validar input - solo números enteros
  const handleCantidadKeyDown = useCallback((e) => {
    // Permitir: backspace, delete, tab, escape, enter, flechas
    const allowedKeys = ['Backspace', 'Delete', 'Tab', 'Escape', 'Enter', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'];
    if (allowedKeys.includes(e.key)) return;
    
    // Permitir Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+X
    if ((e.ctrlKey || e.metaKey) && ['a', 'c', 'v', 'x'].includes(e.key.toLowerCase())) return;
    
    // Bloquear todo excepto números
    if (!/^[0-9]$/.test(e.key)) {
      e.preventDefault();
    }
  }, []);
  
  // Handler para pegar - filtrar no numéricos
  const handleCantidadPaste = useCallback((e) => {
    e.preventDefault();
    const pasteData = e.clipboardData.getData('text');
    const numericValue = pasteData.replace(/[^0-9]/g, '');
    if (numericValue) {
      document.execCommand('insertText', false, numericValue);
    }
  }, []);
  
  // Eliminar item del carrito
  const eliminarItem = useCallback((loteId) => {
    setItems(items.filter(item => item.lote_id !== loteId));
  }, [items]);
  
  // Limpiar carrito
  const limpiarCarrito = useCallback(() => {
    setItems([]);
  }, []);
  
  // Agrupar catálogo por producto
  const catalogoAgrupado = useMemo(() => {
    const grupos = {};
    
    catalogoLotes.forEach(lote => {
      const key = lote.producto_id || lote.producto_clave;
      if (!grupos[key]) {
        grupos[key] = {
          producto_id: lote.producto_id,
          producto_clave: lote.producto_clave,
          producto_nombre: lote.producto_nombre,
          unidad_medida: lote.unidad_medida,
          lotes: []
        };
      }
      grupos[key].lotes.push(lote);
    });
    
    return Object.values(grupos);
  }, [catalogoLotes]);
  
  // Calcular totales del carrito
  const totalUnidades = useMemo(() => 
    items.reduce((sum, item) => sum + item.cantidad, 0)
  , [items]);
  
  const totalProductos = items.length;
  
  // Procesar salida masiva
  const procesarSalida = async () => {
    if (!centroDestino) {
      toast.error('Seleccione un centro destino');
      return;
    }
    
    if (items.length === 0) {
      toast.error('Agregue al menos un producto');
      return;
    }
    
    const itemsInvalidos = items.filter(item => item.cantidad <= 0);
    if (itemsInvalidos.length > 0) {
      toast.error('Todas las cantidades deben ser mayores a 0');
      return;
    }
    
    setProcesando(true);
    
    try {
      const payload = {
        centro_destino_id: parseInt(centroDestino),
        observaciones: observaciones,
        items: items.map(item => ({
          lote_id: item.lote_id,
          cantidad: item.cantidad
        }))
      };
      
      const resp = await salidaMasivaAPI.procesar(payload);
      
      if (resp.data.success) {
        setResultado(resp.data);
        toast.success(resp.data.message);
        
        if (onSuccess) {
          onSuccess(resp.data);
        }
      } else {
        toast.error(resp.data.message || 'Error al procesar salida');
      }
    } catch (err) {
      console.error('Error procesando salida:', err);
      const errorMsg = err.response?.data?.message || err.response?.data?.errores?.join('\n') || 'Error al procesar salida';
      toast.error(errorMsg);
    } finally {
      setProcesando(false);
    }
  };
  
  // Descargar hoja de entrega (con campos para firmas)
  const descargarHojaEntrega = async () => {
    if (!resultado?.grupo_salida) return;
    
    try {
      const resp = await salidaMasivaAPI.hojaEntregaPdf(resultado.grupo_salida, false);
      descargarArchivo(resp.data, `Hoja_Entrega_${resultado.grupo_salida}.pdf`);
      toast.success('Hoja de entrega descargada');
    } catch (err) {
      console.error('Error descargando hoja:', err);
      toast.error('Error al descargar hoja de entrega');
    }
  };
  
  // Descargar comprobante de entrega finalizado (con sello ENTREGADO)
  const descargarComprobanteEntregado = async () => {
    if (!resultado?.grupo_salida) return;
    
    try {
      const resp = await salidaMasivaAPI.hojaEntregaPdf(resultado.grupo_salida, true);
      descargarArchivo(resp.data, `Comprobante_Entrega_${resultado.grupo_salida}.pdf`);
      toast.success('Comprobante de entrega descargado');
    } catch (err) {
      console.error('Error descargando comprobante:', err);
      toast.error('Error al descargar comprobante');
    }
  };
  
  // Reiniciar formulario
  const reiniciar = () => {
    setCentroDestino('');
    setObservaciones('');
    setItems([]);
    setResultado(null);
    setVista('catalogo');
    cargarCatalogo();
  };
  
  // Si hay resultado exitoso, mostrar resumen
  if (resultado) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
          <div className="p-6">
            <div className="text-center mb-6">
              <FaCheckCircle className="text-6xl text-green-500 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-800">Salida Procesada Exitosamente</h2>
              <p className="text-gray-600 mt-2">{resultado.message}</p>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4 mb-6">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-semibold text-gray-700">Folio:</span>
                  <span className="ml-2 text-gray-900">{resultado.grupo_salida}</span>
                </div>
                <div>
                  <span className="font-semibold text-gray-700">Centro Destino:</span>
                  <span className="ml-2 text-gray-900">{resultado.centro_destino?.nombre}</span>
                </div>
                <div>
                  <span className="font-semibold text-gray-700">Total Productos:</span>
                  <span className="ml-2 text-gray-900">{resultado.total_items}</span>
                </div>
                <div>
                  <span className="font-semibold text-gray-700">Total Unidades:</span>
                  <span className="ml-2 text-gray-900">
                    {resultado.movimientos?.reduce((sum, m) => sum + m.cantidad, 0)}
                  </span>
                </div>
              </div>
            </div>
            
            {/* Tabla de movimientos procesados */}
            <div className="overflow-x-auto mb-6">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-3 py-2 text-left font-semibold">Clave</th>
                    <th className="px-3 py-2 text-left font-semibold">Producto</th>
                    <th className="px-3 py-2 text-left font-semibold">Lote</th>
                    <th className="px-3 py-2 text-center font-semibold">Cantidad</th>
                    <th className="px-3 py-2 text-center font-semibold">Stock Actual</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {resultado.movimientos?.map((mov, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-3 py-2 font-mono">{mov.producto_clave}</td>
                      <td className="px-3 py-2">{mov.producto_nombre}</td>
                      <td className="px-3 py-2">{mov.numero_lote}</td>
                      <td className="px-3 py-2 text-center font-semibold text-rose-600">-{mov.cantidad}</td>
                      <td className="px-3 py-2 text-center">{mov.stock_actual}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {/* Botones de acción */}
            <div className="flex flex-wrap justify-center gap-4">
              <button
                onClick={descargarHojaEntrega}
                className="flex items-center gap-2 px-6 py-3 bg-rose-700 text-white rounded-lg hover:bg-rose-800 transition-colors"
              >
                <FaFileDownload />
                Hoja de Entrega
              </button>
              <button
                onClick={descargarComprobanteEntregado}
                className="flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                <FaFileDownload />
                Comprobante Entregado
              </button>
              <button
                onClick={reiniciar}
                className="flex items-center gap-2 px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
              >
                <FaPlus />
                Nueva Salida
              </button>
              {onClose && (
                <button
                  onClick={onClose}
                  className="flex items-center gap-2 px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  Cerrar
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-6xl w-full max-h-[95vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-rose-50 to-white">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-rose-100 rounded-lg">
              <FaTruck className="text-2xl text-rose-700" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-800">Salida Masiva de Inventario</h2>
              <p className="text-sm text-gray-600">
                Agregue productos a la lista y procese la entrega al centro destino
              </p>
            </div>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <FaTimes className="text-gray-500" />
            </button>
          )}
        </div>
        
        {/* Selector de Centro y Toggle Vista */}
        <div className="p-4 border-b bg-gray-50">
          <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center justify-between">
            <div className="flex-1 max-w-md">
              <label className="block text-sm font-semibold text-gray-700 mb-1">
                <FaBuilding className="inline mr-2" />
                Centro Destino *
              </label>
              <select
                value={centroDestino}
                onChange={(e) => setCentroDestino(e.target.value)}
                disabled={loadingCentros}
                className="w-full px-4 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:border-rose-500 transition-colors"
              >
                <option value="">Seleccione un centro...</option>
                {centros.map((centro) => (
                  <option key={centro.id} value={centro.id}>
                    {centro.nombre}
                  </option>
                ))}
              </select>
            </div>
            
            {/* Toggle Vista + Carrito Badge */}
            <div className="flex items-center gap-4">
              <div className="flex rounded-lg border overflow-hidden">
                <button
                  onClick={() => setVista('catalogo')}
                  className={`px-4 py-2 text-sm font-medium transition-colors ${
                    vista === 'catalogo'
                      ? 'bg-rose-600 text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <FaBox className="inline mr-2" />
                  Catálogo
                </button>
                <button
                  onClick={() => setVista('carrito')}
                  className={`px-4 py-2 text-sm font-medium transition-colors relative ${
                    vista === 'carrito'
                      ? 'bg-rose-600 text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <FaShoppingCart className="inline mr-2" />
                  Selección
                  {totalProductos > 0 && (
                    <span className="absolute -top-2 -right-2 bg-green-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                      {totalProductos}
                    </span>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
        
        {/* Contenido Principal */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {vista === 'catalogo' ? (
            <>
              {/* Buscador */}
              <div className="p-4 border-b">
                <div className="relative max-w-xl">
                  <FaSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Buscar por clave, descripción o número de lote..."
                    value={catalogoBusqueda}
                    onChange={(e) => handleBusquedaChange(e.target.value)}
                    className="w-full border-2 rounded-lg pl-10 pr-10 py-3 text-sm focus:border-rose-500 focus:outline-none"
                  />
                  {catalogoBusqueda && (
                    <button
                      onClick={() => handleBusquedaChange('')}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      <FaTimes />
                    </button>
                  )}
                </div>
                {totalLotesDisponibles > catalogoLotes.length && (
                  <p className="text-xs text-gray-500 mt-1 ml-1">
                    Mostrando {catalogoLotes.length} de {totalLotesDisponibles} lotes disponibles
                  </p>
                )}
              </div>
              
              {/* Tabla de Catálogo */}
              <div className="flex-1 overflow-y-auto">
                {loadingCatalogo ? (
                  <div className="flex items-center justify-center py-20">
                    <FaSpinner className="animate-spin text-4xl text-gray-400 mr-3" />
                    <span className="text-gray-500">Cargando catálogo...</span>
                  </div>
                ) : catalogoAgrupado.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-20 text-gray-500">
                    <FaExclamationTriangle className="text-5xl mb-3 text-amber-400" />
                    <p className="font-semibold">No se encontraron productos</p>
                    <p className="text-sm">Intenta con otra búsqueda</p>
                  </div>
                ) : (
                  <table className="w-full text-sm">
                    <thead className="bg-gray-100 sticky top-0">
                      <tr>
                        <th className="text-left px-4 py-3 font-semibold text-gray-700">Clave</th>
                        <th className="text-left px-4 py-3 font-semibold text-gray-700">Producto</th>
                        <th className="text-left px-4 py-3 font-semibold text-gray-700">Lote</th>
                        <th className="text-center px-4 py-3 font-semibold text-gray-700">Caducidad</th>
                        <th className="text-center px-4 py-3 font-semibold text-gray-700">Disponible</th>
                        <th className="text-center px-4 py-3 font-semibold text-gray-700 w-44">Cantidad</th>
                      </tr>
                    </thead>
                    <tbody>
                      {catalogoAgrupado.map((grupo) => (
                        grupo.lotes.map((lote, loteIdx) => {
                          const enCarrito = loteEnCarrito(lote.id);
                          const cantidadCarrito = getCantidadEnCarrito(lote.id);
                          const stockDisponible = lote.cantidad_disponible || 0;
                          const fechaCad = lote.fecha_caducidad;
                          const esCaducidadProxima = fechaCad && new Date(fechaCad) <= new Date(Date.now() + 90 * 24 * 60 * 60 * 1000);
                          
                          return (
                            <tr 
                              key={lote.id} 
                              className={`border-t hover:bg-gray-50 transition-colors ${
                                enCarrito ? 'bg-green-50' : ''
                              }`}
                            >
                              {loteIdx === 0 ? (
                                <>
                                  <td 
                                    className="px-4 py-3 font-bold align-top text-rose-700"
                                    rowSpan={grupo.lotes.length}
                                  >
                                    {grupo.producto_clave}
                                  </td>
                                  <td 
                                    className="px-4 py-3 align-top"
                                    rowSpan={grupo.lotes.length}
                                  >
                                    <span className="line-clamp-2">{grupo.producto_nombre}</span>
                                    <span className="text-xs text-gray-500 block">{grupo.unidad_medida}</span>
                                  </td>
                                </>
                              ) : null}
                              <td className="px-4 py-3 font-mono text-sm">{lote.numero_lote}</td>
                              <td className={`px-4 py-3 text-center text-sm ${esCaducidadProxima ? 'text-amber-600 font-medium' : 'text-gray-600'}`}>
                                {fechaCad || 'N/A'}
                                {esCaducidadProxima && <FaExclamationTriangle className="inline ml-1 text-amber-500" />}
                              </td>
                              <td className="px-4 py-3 text-center font-semibold text-green-600">
                                {stockDisponible}
                              </td>
                              <td className="px-4 py-3">
                                <div className="flex items-center justify-center gap-2">
                                  {enCarrito ? (
                                    <>
                                      <button
                                        onClick={() => decrementarCantidad(lote.id)}
                                        className="w-8 h-8 flex items-center justify-center rounded-lg bg-gray-200 hover:bg-gray-300 text-gray-700 transition-colors font-bold"
                                        title="Reducir cantidad"
                                      >
                                        −
                                      </button>
                                      <input
                                        type="text"
                                        inputMode="numeric"
                                        pattern="[0-9]*"
                                        min="1"
                                        max={stockDisponible}
                                        value={cantidadCarrito}
                                        onChange={(e) => actualizarCantidad(lote.id, e.target.value)}
                                        onKeyDown={handleCantidadKeyDown}
                                        onPaste={handleCantidadPaste}
                                        className="w-16 h-8 px-2 border-2 border-gray-300 rounded-lg text-center font-bold text-gray-800 focus:outline-none focus:border-rose-500 focus:ring-2 focus:ring-rose-200"
                                        title="Escriba la cantidad (solo números enteros)"
                                      />
                                      <button
                                        onClick={() => incrementarCantidad(lote.id)}
                                        disabled={cantidadCarrito >= stockDisponible}
                                        className="w-8 h-8 flex items-center justify-center rounded-lg bg-green-500 hover:bg-green-600 text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed font-bold"
                                        title="Aumentar cantidad"
                                      >
                                        +
                                      </button>
                                    </>
                                  ) : (
                                    <button
                                      onClick={() => agregarItem(lote)}
                                      className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium shadow-sm"
                                    >
                                      <FaPlus /> Agregar
                                    </button>
                                  )}
                                </div>
                              </td>
                            </tr>
                          );
                        })
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </>
          ) : (
            /* Vista Carrito */
            <div className="flex-1 overflow-y-auto p-4">
              {items.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 text-gray-500">
                  <FaShoppingCart className="text-5xl mb-4 opacity-30" />
                  <p className="font-semibold">No hay productos seleccionados</p>
                  <p className="text-sm mb-4">Vuelve al catálogo y agrega productos</p>
                  <button
                    onClick={() => setVista('catalogo')}
                    className="flex items-center gap-2 px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 transition-colors"
                  >
                    <FaArrowLeft /> Ir al Catálogo
                  </button>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-800">
                      <FaClipboardList className="inline mr-2" />
                      Productos a Entregar ({totalProductos})
                    </h3>
                    <button
                      onClick={limpiarCarrito}
                      className="text-sm text-red-600 hover:text-red-800 flex items-center gap-1"
                    >
                      <FaTrash /> Limpiar todo
                    </button>
                  </div>
                  
                  <div className="overflow-x-auto border rounded-lg">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-100">
                        <tr>
                          <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Clave</th>
                          <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Producto</th>
                          <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Lote</th>
                          <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Disponible</th>
                          <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Cantidad</th>
                          <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Acción</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200 bg-white">
                        {items.map((item) => (
                          <tr key={item.lote_id} className="hover:bg-gray-50">
                            <td className="px-4 py-3 font-mono text-sm font-semibold text-rose-700">
                              {item.producto_clave}
                            </td>
                            <td className="px-4 py-3">
                              <span className="text-sm">{item.producto_nombre}</span>
                              <span className="text-xs text-gray-500 block">{item.unidad_medida}</span>
                            </td>
                            <td className="px-4 py-3 text-sm">{item.numero_lote}</td>
                            <td className="px-4 py-3 text-center text-sm text-green-600 font-semibold">
                              {item.cantidad_disponible}
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center justify-center gap-2">
                                <button
                                  onClick={() => decrementarCantidad(item.lote_id)}
                                  className="w-8 h-8 flex items-center justify-center rounded-lg bg-gray-200 hover:bg-gray-300 text-gray-700 transition-colors font-bold"
                                  title="Reducir cantidad"
                                >
                                  −
                                </button>
                                <input
                                  type="text"
                                  inputMode="numeric"
                                  pattern="[0-9]*"
                                  min="1"
                                  max={item.cantidad_disponible}
                                  value={item.cantidad}
                                  onChange={(e) => actualizarCantidad(item.lote_id, e.target.value)}
                                  onKeyDown={handleCantidadKeyDown}
                                  onPaste={handleCantidadPaste}
                                  className="w-16 h-8 px-2 border-2 border-gray-300 rounded-lg text-center font-bold text-gray-800 focus:outline-none focus:border-rose-500 focus:ring-2 focus:ring-rose-200"
                                  title="Escriba la cantidad (solo números enteros)"
                                />
                                <button
                                  onClick={() => incrementarCantidad(item.lote_id)}
                                  disabled={item.cantidad >= item.cantidad_disponible}
                                  className="w-8 h-8 flex items-center justify-center rounded-lg bg-green-500 hover:bg-green-600 text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed font-bold"
                                  title="Aumentar cantidad"
                                >
                                  +
                                </button>
                              </div>
                            </td>
                            <td className="px-4 py-3 text-center">
                              <button
                                onClick={() => eliminarItem(item.lote_id)}
                                className="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
                                title="Eliminar"
                              >
                                <FaTrash />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  
                  {/* Observaciones */}
                  <div className="mt-6">
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Observaciones (opcional)
                    </label>
                    <textarea
                      value={observaciones}
                      onChange={(e) => setObservaciones(e.target.value)}
                      placeholder="Notas adicionales para la entrega..."
                      rows={2}
                      className="w-full px-4 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:border-rose-500 transition-colors resize-none"
                    />
                  </div>
                </>
              )}
            </div>
          )}
        </div>
        
        {/* Footer con resumen y botón procesar */}
        <div className="p-4 border-t bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div>
                <span className="text-sm text-gray-500">Productos:</span>
                <span className="ml-2 text-lg font-bold text-gray-800">{totalProductos}</span>
              </div>
              <div>
                <span className="text-sm text-gray-500">Total unidades:</span>
                <span className="ml-2 text-lg font-bold text-rose-700">{totalUnidades}</span>
              </div>
              {centroDestino && (
                <div>
                  <span className="text-sm text-gray-500">Destino:</span>
                  <span className="ml-2 text-sm font-medium text-gray-800">
                    {centros.find(c => c.id.toString() === centroDestino)?.nombre}
                  </span>
                </div>
              )}
            </div>
            
            <div className="flex gap-3">
              {onClose && (
                <button
                  onClick={onClose}
                  disabled={procesando}
                  className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50"
                >
                  Cancelar
                </button>
              )}
              <button
                onClick={procesarSalida}
                disabled={procesando || items.length === 0 || !centroDestino}
                className="flex items-center gap-2 px-6 py-2 bg-rose-700 text-white rounded-lg hover:bg-rose-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {procesando ? (
                  <>
                    <FaSpinner className="animate-spin" />
                    Procesando...
                  </>
                ) : (
                  <>
                    <FaTruck />
                    Procesar Salida ({totalProductos} productos)
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SalidaMasiva;
