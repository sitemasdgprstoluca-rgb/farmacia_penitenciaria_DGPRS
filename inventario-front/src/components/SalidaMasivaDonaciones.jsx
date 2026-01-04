/**
 * Componente SalidaMasivaDonaciones - ALMACÉN INDEPENDIENTE
 * 
 * IMPORTANTE: Este componente maneja ÚNICAMENTE el inventario de donaciones.
 * NO afecta el inventario principal de farmacia, lotes, ni movimientos.
 * Las salidas se registran SOLO en la tabla salidas_donaciones.
 * 
 * Permite seleccionar múltiples productos del almacén de donaciones
 * y registrar entregas masivas a destinatarios.
 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { toast } from 'react-hot-toast';
import {
  FaPlus,
  FaMinus,
  FaTrash,
  FaSearch,
  FaHandHoldingMedical,
  FaSpinner,
  FaBox,
  FaClipboardList,
  FaCheckCircle,
  FaTimes,
  FaShoppingCart,
  FaArrowLeft,
  FaExclamationTriangle,
  FaGift,
  FaUser,
  FaBuilding,
  FaFilePdf,
} from 'react-icons/fa';
import { detallesDonacionAPI, salidasDonacionesAPI, centrosAPI } from '../services/api';

const SalidaMasivaDonaciones = ({ onClose, onSuccess }) => {
  // Estado del formulario
  const [tipoDestinatario, setTipoDestinatario] = useState('centro'); // 'centro' | 'persona'
  const [centroDestino, setCentroDestino] = useState('');
  const [destinatario, setDestinatario] = useState('');
  const [motivo, setMotivo] = useState('');
  const [notas, setNotas] = useState('');
  const [items, setItems] = useState([]); // Carrito de items seleccionados
  
  // Centros disponibles
  const [centros, setCentros] = useState([]);
  const [loadingCentros, setLoadingCentros] = useState(false);
  
  // Catálogo de productos donados disponibles
  const [catalogoProductos, setCatalogoProductos] = useState([]);
  const [loadingCatalogo, setLoadingCatalogo] = useState(false);
  const [catalogoBusqueda, setCatalogoBusqueda] = useState('');
  const [totalDisponibles, setTotalDisponibles] = useState(0);
  
  // Vista: 'catalogo' | 'carrito'
  const [vista, setVista] = useState('catalogo');
  
  // Estado de procesamiento
  const [procesando, setProcesando] = useState(false);
  const [resultado, setResultado] = useState(null);
  
  // Ref para debounce de búsqueda
  const searchTimeoutRef = useRef(null);
  
  // Cargar centros
  const cargarCentros = useCallback(async () => {
    setLoadingCentros(true);
    try {
      const resp = await centrosAPI.getAll({ page_size: 100, activo: true, ordering: 'nombre' });
      setCentros(resp.data.results || resp.data || []);
    } catch (err) {
      console.error('Error cargando centros:', err);
      setCentros([]);
    } finally {
      setLoadingCentros(false);
    }
  }, []);
  
  // Cargar catálogo de productos donados con stock
  const cargarCatalogo = useCallback(async (termino = '') => {
    setLoadingCatalogo(true);
    try {
      const params = {
        page_size: 200,
        disponible: 'true', // Solo con stock disponible
        ordering: 'producto__nombre',
      };
      if (termino.trim()) {
        params.search = termino.trim();
      }
      
      const resp = await detallesDonacionAPI.getAll(params);
      const productos = resp.data.results || resp.data || [];
      setCatalogoProductos(productos);
      setTotalDisponibles(resp.data.count || productos.length);
    } catch (err) {
      console.error('Error cargando catálogo donaciones:', err);
      setCatalogoProductos([]);
      toast.error('Error al cargar productos donados');
    } finally {
      setLoadingCatalogo(false);
    }
  }, []);
  
  // Cargar catálogo y centros inicial
  useEffect(() => {
    cargarCatalogo();
    cargarCentros();
  }, [cargarCatalogo, cargarCentros]);
  
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
  
  // Verificar si un detalle está en el carrito
  const detalleEnCarrito = useCallback((detalleId) => {
    return items.some(item => item.detalle_id === detalleId);
  }, [items]);
  
  // Obtener cantidad en carrito de un detalle
  const getCantidadEnCarrito = useCallback((detalleId) => {
    const item = items.find(i => i.detalle_id === detalleId);
    return item ? item.cantidad : 0;
  }, [items]);
  
  // Agregar item al carrito
  const agregarItem = useCallback((detalle, cantidad = 1) => {
    const existe = items.find(item => item.detalle_id === detalle.id);
    
    if (existe) {
      const nuevaCantidad = Math.min(existe.cantidad + cantidad, detalle.cantidad_disponible);
      setItems(items.map(item => 
        item.detalle_id === detalle.id 
          ? { ...item, cantidad: nuevaCantidad }
          : item
      ));
    } else {
      setItems([...items, {
        detalle_id: detalle.id,
        producto_codigo: detalle.producto_codigo || detalle.producto?.clave,
        producto_nombre: detalle.producto_nombre || detalle.producto?.nombre,
        numero_lote: detalle.numero_lote,
        donacion_numero: detalle.donacion_numero || `DON-${detalle.donacion}`,
        cantidad_disponible: detalle.cantidad_disponible,
        fecha_caducidad: detalle.fecha_caducidad,
        cantidad: Math.min(cantidad, detalle.cantidad_disponible),
      }]);
    }
  }, [items]);
  
  // Incrementar cantidad
  const incrementarCantidad = useCallback((detalleId) => {
    setItems(items.map(item => {
      if (item.detalle_id === detalleId) {
        const nuevaCantidad = Math.min(item.cantidad + 1, item.cantidad_disponible);
        return { ...item, cantidad: nuevaCantidad };
      }
      return item;
    }));
  }, [items]);
  
  // Decrementar cantidad
  const decrementarCantidad = useCallback((detalleId) => {
    setItems(items.map(item => {
      if (item.detalle_id === detalleId) {
        const nuevaCantidad = Math.max(item.cantidad - 1, 0);
        return { ...item, cantidad: nuevaCantidad };
      }
      return item;
    }).filter(item => item.cantidad > 0));
  }, [items]);
  
  // Actualizar cantidad - solo enteros positivos
  const actualizarCantidad = useCallback((detalleId, cantidad) => {
    // Limpiar cualquier caracter no numérico
    const valorLimpio = cantidad.toString().replace(/[^0-9]/g, '');
    const cantidadNum = parseInt(valorLimpio) || 0;
    
    if (cantidadNum <= 0) {
      setItems(items.filter(item => item.detalle_id !== detalleId));
      return;
    }
    
    setItems(items.map(item => {
      if (item.detalle_id === detalleId) {
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
  
  // Eliminar item
  const eliminarItem = useCallback((detalleId) => {
    setItems(items.filter(item => item.detalle_id !== detalleId));
  }, [items]);
  
  // Limpiar carrito
  const limpiarCarrito = useCallback(() => {
    setItems([]);
  }, []);
  
  // Calcular totales
  const totalUnidades = useMemo(() => 
    items.reduce((sum, item) => sum + item.cantidad, 0)
  , [items]);
  
  const totalProductos = items.length;
  
  // Procesar salida masiva de donaciones
  const procesarSalida = async () => {
    // Validar destinatario según tipo
    const destinatarioFinal = tipoDestinatario === 'centro' 
      ? centros.find(c => c.id == centroDestino)?.nombre || ''
      : destinatario.trim();
    
    if (!destinatarioFinal) {
      toast.error(tipoDestinatario === 'centro' ? 'Seleccione un centro destino' : 'Ingrese el destinatario');
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
      // Procesar cada salida individualmente
      // (la tabla salidas_donaciones es por detalle)
      const resultados = {
        exitosos: 0,
        fallidos: 0,
        errores: [],
        salidas: []
      };
      
      for (const item of items) {
        try {
          const salidaData = {
            detalle_donacion: item.detalle_id,
            cantidad: item.cantidad,
            destinatario: destinatarioFinal,
            motivo: motivo.trim() || null,
            notas: notas.trim() || null,
          };
          
          // Agregar centro_destino solo si es tipo centro
          if (tipoDestinatario === 'centro' && centroDestino) {
            salidaData.centro_destino = parseInt(centroDestino);
          }
          
          const resp = await salidasDonacionesAPI.create(salidaData);
          resultados.exitosos++;
          resultados.salidas.push({
            ...item,
            salida_id: resp.data.id
          });
        } catch (err) {
          resultados.fallidos++;
          resultados.errores.push({
            producto: item.producto_nombre,
            error: err.response?.data?.error || err.response?.data?.cantidad?.[0] || 'Error desconocido'
          });
        }
      }
      
      if (resultados.exitosos > 0) {
        setResultado({
          success: true,
          message: `${resultados.exitosos} entregas registradas - Pendiente de confirmar`,
          destinatario: destinatarioFinal,
          centro_destino_id: tipoDestinatario === 'centro' ? centroDestino : null,
          total_productos: resultados.exitosos,
          total_unidades: resultados.salidas.reduce((sum, s) => sum + s.cantidad, 0),
          salidas: resultados.salidas,
          errores: resultados.errores
        });
        
        toast.success(`${resultados.exitosos} entregas registradas - Pendiente de confirmar`);
        
        if (onSuccess) {
          onSuccess(resultados);
        }
      }
      
      if (resultados.fallidos > 0) {
        toast.error(`${resultados.fallidos} entregas fallaron`);
      }
      
    } catch (err) {
      console.error('Error procesando salidas:', err);
      toast.error('Error al procesar entregas');
    } finally {
      setProcesando(false);
    }
  };
  
  // Reiniciar
  const reiniciar = () => {
    setTipoDestinatario('centro');
    setCentroDestino('');
    setDestinatario('');
    setMotivo('');
    setNotas('');
    setItems([]);
    setResultado(null);
    setVista('catalogo');
    cargarCatalogo();
  };
  
  // Si hay resultado exitoso
  if (resultado) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
          <div className="p-6">
            <div className="text-center mb-6">
              <FaCheckCircle className="text-6xl text-amber-500 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-800">Entregas Registradas</h2>
              <p className="text-gray-600 mt-2">{resultado.message}</p>
              <p className="text-amber-600 text-sm mt-1 font-medium">
                ⚠️ Las entregas deben ser confirmadas para descontar del inventario
              </p>
            </div>
            
            <div className="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-lg p-4 mb-6">
              <div className="flex items-center gap-2 mb-2">
                <FaGift className="text-purple-600" />
                <span className="font-semibold text-purple-800">Almacén de Donaciones</span>
              </div>
              <p className="text-sm text-purple-700">
                Estas entregas se registraron únicamente en el inventario de donaciones.
                No afectan el inventario principal de farmacia.
              </p>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4 mb-6">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-semibold text-gray-700">Destinatario:</span>
                  <span className="ml-2 text-gray-900">{resultado.destinatario}</span>
                </div>
                <div>
                  <span className="font-semibold text-gray-700">Total Productos:</span>
                  <span className="ml-2 text-gray-900">{resultado.total_productos}</span>
                </div>
                <div>
                  <span className="font-semibold text-gray-700">Total Unidades:</span>
                  <span className="ml-2 text-gray-900">{resultado.total_unidades}</span>
                </div>
              </div>
            </div>
            
            {/* Tabla de entregas */}
            <div className="w-full overflow-x-auto rounded-lg border border-gray-200 shadow-md mb-6">
              <table className="w-full min-w-[600px] divide-y divide-gray-200 text-sm">
                <thead className="bg-theme-gradient sticky top-0 z-10">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Producto</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Donación</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Lote</th>
                    <th className="px-3 py-2 text-center text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Cantidad</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {resultado.salidas?.map((salida, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-3 py-2">
                        <span className="font-mono text-purple-700">{salida.producto_codigo}</span>
                        <span className="block text-xs text-gray-500">{salida.producto_nombre}</span>
                      </td>
                      <td className="px-3 py-2 text-sm">{salida.donacion_numero}</td>
                      <td className="px-3 py-2 text-sm">{salida.numero_lote || '-'}</td>
                      <td className="px-3 py-2 text-center font-semibold text-green-600">
                        {salida.cantidad}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {resultado.errores?.length > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                <h4 className="font-semibold text-red-800 mb-2">Errores:</h4>
                {resultado.errores.map((err, idx) => (
                  <p key={idx} className="text-sm text-red-700">
                    • {err.producto}: {err.error}
                  </p>
                ))}
              </div>
            )}
            
            {/* Botones */}
            <div className="flex justify-center gap-4">
              <button
                onClick={reiniciar}
                className="flex items-center gap-2 px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                <FaPlus />
                Nueva Entrega
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
        <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-purple-50 to-pink-50">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-purple-100 rounded-lg">
              <FaHandHoldingMedical className="text-2xl text-purple-700" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-800">Entrega Masiva de Donaciones</h2>
              <p className="text-sm text-gray-600">
                Almacén independiente - No afecta inventario de farmacia
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
        
        {/* Aviso importante */}
        <div className="mx-4 mt-4 p-3 bg-gradient-to-r from-purple-100 to-pink-100 border border-purple-300 rounded-lg">
          <div className="flex items-center gap-2 text-purple-800">
            <FaGift />
            <span className="font-semibold">Almacén de Donaciones Independiente</span>
          </div>
          <p className="text-sm text-purple-700 mt-1">
            Las entregas aquí registradas NO afectan el inventario principal, lotes, ni movimientos de farmacia.
          </p>
        </div>
        
        {/* Destinatario y Toggle Vista */}
        <div className="p-4 border-b bg-gray-50">
          <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center justify-between">
            <div className="flex-1 max-w-lg">
              {/* Selector de tipo de destinatario */}
              <div className="flex items-center gap-4 mb-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="tipoDestinatario"
                    value="centro"
                    checked={tipoDestinatario === 'centro'}
                    onChange={() => setTipoDestinatario('centro')}
                    className="text-purple-600 focus:ring-purple-500"
                  />
                  <FaBuilding className="text-gray-600" />
                  <span className="text-sm font-medium">Centro</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="tipoDestinatario"
                    value="persona"
                    checked={tipoDestinatario === 'persona'}
                    onChange={() => setTipoDestinatario('persona')}
                    className="text-purple-600 focus:ring-purple-500"
                  />
                  <FaUser className="text-gray-600" />
                  <span className="text-sm font-medium">Otra Persona</span>
                </label>
              </div>
              
              {tipoDestinatario === 'centro' ? (
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    <FaBuilding className="inline mr-2" />
                    Centro Destino *
                  </label>
                  <select
                    value={centroDestino}
                    onChange={(e) => setCentroDestino(e.target.value)}
                    disabled={loadingCentros}
                    className="w-full px-4 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:border-purple-500 transition-colors"
                  >
                    <option value="">Seleccione un centro...</option>
                    {centros.map((centro) => (
                      <option key={centro.id} value={centro.id}>
                        {centro.nombre}
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    <FaUser className="inline mr-2" />
                    Destinatario *
                  </label>
                  <input
                    type="text"
                    value={destinatario}
                    onChange={(e) => setDestinatario(e.target.value)}
                    placeholder="Nombre del interno, paciente o área..."
                    className="w-full px-4 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:border-purple-500 transition-colors"
                  />
                </div>
              )}
            </div>
            
            {/* Toggle Vista */}
            <div className="flex items-center gap-4">
              <div className="flex rounded-lg border overflow-visible">
                <button
                  onClick={() => setVista('catalogo')}
                  className={`px-4 py-2 text-sm font-medium transition-colors ${
                    vista === 'catalogo'
                      ? 'bg-purple-600 text-white'
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
                      ? 'bg-purple-600 text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <FaShoppingCart className="inline mr-2" />
                  Selección
                  {totalProductos > 0 && (
                    <span className="absolute -top-3 -right-3 bg-green-500 text-white text-xs rounded-full min-w-[22px] h-[22px] flex items-center justify-center font-bold shadow-sm border-2 border-white">
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
                    placeholder="Buscar producto en donaciones..."
                    value={catalogoBusqueda}
                    onChange={(e) => handleBusquedaChange(e.target.value)}
                    className="w-full border-2 rounded-lg pl-10 pr-10 py-3 text-sm focus:border-purple-500 focus:outline-none"
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
                {totalDisponibles > catalogoProductos.length && (
                  <p className="text-xs text-gray-500 mt-1 ml-1">
                    Mostrando {catalogoProductos.length} de {totalDisponibles} productos
                  </p>
                )}
              </div>
              
              {/* Tabla de Catálogo */}
              <div className="flex-1 overflow-y-auto">
                {loadingCatalogo ? (
                  <div className="flex items-center justify-center py-20">
                    <FaSpinner className="animate-spin text-4xl text-gray-400 mr-3" />
                    <span className="text-gray-500">Cargando productos donados...</span>
                  </div>
                ) : catalogoProductos.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-20 text-gray-500">
                    <FaExclamationTriangle className="text-5xl mb-3 text-amber-400" />
                    <p className="font-semibold">No hay productos disponibles</p>
                    <p className="text-sm">Procesa donaciones para agregar stock al almacén</p>
                  </div>
                ) : (
                  <table className="w-full text-sm">
                    <thead className="bg-gray-100 sticky top-0">
                      <tr>
                        <th className="text-left px-4 py-3 font-semibold text-gray-700">Producto</th>
                        <th className="text-left px-4 py-3 font-semibold text-gray-700">Donación</th>
                        <th className="text-left px-4 py-3 font-semibold text-gray-700">Lote</th>
                        <th className="text-center px-4 py-3 font-semibold text-gray-700">Caducidad</th>
                        <th className="text-center px-4 py-3 font-semibold text-gray-700">Disponible</th>
                        <th className="text-center px-4 py-3 font-semibold text-gray-700 w-44">Cantidad</th>
                      </tr>
                    </thead>
                    <tbody>
                      {catalogoProductos.map((detalle) => {
                        const enCarrito = detalleEnCarrito(detalle.id);
                        const cantidadCarrito = getCantidadEnCarrito(detalle.id);
                        const stockDisponible = detalle.cantidad_disponible || 0;
                        const fechaCad = detalle.fecha_caducidad;
                        const esCaducidadProxima = fechaCad && new Date(fechaCad) <= new Date(Date.now() + 90 * 24 * 60 * 60 * 1000);
                        
                        return (
                          <tr 
                            key={detalle.id} 
                            className={`border-t hover:bg-gray-50 transition-colors ${
                              enCarrito ? 'bg-purple-50' : ''
                            }`}
                          >
                            <td className="px-4 py-3">
                              <span className="font-bold text-purple-700">
                                {detalle.producto_codigo || detalle.producto?.clave}
                              </span>
                              <span className="block text-xs text-gray-500 line-clamp-1">
                                {detalle.producto_nombre || detalle.producto?.nombre}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">
                              {detalle.donacion_numero || `DON-${detalle.donacion}`}
                            </td>
                            <td className="px-4 py-3 font-mono text-sm">{detalle.numero_lote || '-'}</td>
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
                                      onClick={() => decrementarCantidad(detalle.id)}
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
                                      onChange={(e) => actualizarCantidad(detalle.id, e.target.value)}
                                      onKeyDown={handleCantidadKeyDown}
                                      onPaste={handleCantidadPaste}
                                      className="w-16 h-8 px-2 border-2 border-gray-300 rounded-lg text-center font-bold text-gray-800 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-200"
                                      title="Escriba la cantidad (solo números enteros)"
                                    />
                                    <button
                                      onClick={() => incrementarCantidad(detalle.id)}
                                      disabled={cantidadCarrito >= stockDisponible}
                                      className="w-8 h-8 flex items-center justify-center rounded-lg bg-green-500 hover:bg-green-600 text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed font-bold"
                                      title="Aumentar cantidad"
                                    >
                                      +
                                    </button>
                                  </>
                                ) : (
                                  <button
                                    onClick={() => agregarItem(detalle)}
                                    disabled={stockDisponible <= 0}
                                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium shadow-sm disabled:opacity-50"
                                  >
                                    <FaPlus /> Agregar
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
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
                    className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
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
                  
                  <div className="w-full overflow-x-auto rounded-lg border border-gray-200 shadow-md mb-6">
                    <table className="w-full min-w-[800px] divide-y divide-gray-200">
                      <thead className="bg-theme-gradient sticky top-0 z-10">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Producto</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Donación</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Lote</th>
                          <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Disponible</th>
                          <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Cantidad</th>
                          <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-white whitespace-nowrap">Acción</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200 bg-white">
                        {items.map((item) => (
                          <tr key={item.detalle_id} className="hover:bg-gray-50">
                            <td className="px-4 py-3">
                              <span className="font-mono text-sm font-semibold text-purple-700">
                                {item.producto_codigo}
                              </span>
                              <span className="block text-xs text-gray-500">{item.producto_nombre}</span>
                            </td>
                            <td className="px-4 py-3 text-sm">{item.donacion_numero}</td>
                            <td className="px-4 py-3 text-sm">{item.numero_lote || '-'}</td>
                            <td className="px-4 py-3 text-center text-sm text-green-600 font-semibold">
                              {item.cantidad_disponible}
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center justify-center gap-2">
                                <button
                                  onClick={() => decrementarCantidad(item.detalle_id)}
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
                                  onChange={(e) => actualizarCantidad(item.detalle_id, e.target.value)}
                                  onKeyDown={handleCantidadKeyDown}
                                  onPaste={handleCantidadPaste}
                                  className="w-16 h-8 px-2 border-2 border-gray-300 rounded-lg text-center font-bold text-gray-800 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-200"
                                  title="Escriba la cantidad (solo números enteros)"
                                />
                                <button
                                  onClick={() => incrementarCantidad(item.detalle_id)}
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
                                onClick={() => eliminarItem(item.detalle_id)}
                                className="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
                              >
                                <FaTrash />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  
                  {/* Motivo y Notas */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">
                        Motivo (opcional)
                      </label>
                      <input
                        type="text"
                        value={motivo}
                        onChange={(e) => setMotivo(e.target.value)}
                        placeholder="Motivo de la entrega..."
                        className="w-full px-4 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:border-purple-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">
                        Notas (opcional)
                      </label>
                      <input
                        type="text"
                        value={notas}
                        onChange={(e) => setNotas(e.target.value)}
                        placeholder="Notas adicionales..."
                        className="w-full px-4 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:border-purple-500"
                      />
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="p-4 border-t bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div>
                <span className="text-sm text-gray-500">Productos:</span>
                <span className="ml-2 text-lg font-bold text-gray-800">{totalProductos}</span>
              </div>
              <div>
                <span className="text-sm text-gray-500">Total unidades:</span>
                <span className="ml-2 text-lg font-bold text-purple-700">{totalUnidades}</span>
              </div>
              {destinatario && (
                <div>
                  <span className="text-sm text-gray-500">Destinatario:</span>
                  <span className="ml-2 text-sm font-medium text-gray-800">{destinatario}</span>
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
                disabled={procesando || items.length === 0 || (tipoDestinatario === 'centro' ? !centroDestino : !destinatario.trim())}
                className="flex items-center gap-2 px-6 py-2 bg-purple-700 text-white rounded-lg hover:bg-purple-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {procesando ? (
                  <>
                    <FaSpinner className="animate-spin" />
                    Procesando...
                  </>
                ) : (
                  <>
                    <FaHandHoldingMedical />
                    Registrar Entregas ({totalProductos})
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

export default SalidaMasivaDonaciones;
