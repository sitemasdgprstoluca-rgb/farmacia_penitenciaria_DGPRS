/**
 * Componente SalidaMasiva - Solo para Farmacia
 * Permite agregar múltiples productos/lotes a una lista y procesarlos de una vez
 * con generación de hoja de entrega para firma.
 */
import { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import {
  FaPlus,
  FaTrash,
  FaSearch,
  FaTruck,
  FaFileDownload,
  FaSpinner,
  FaBox,
  FaClipboardList,
  FaCheckCircle,
  FaTimesCircle,
  FaBuilding,
} from 'react-icons/fa';
import { salidaMasivaAPI, centrosAPI, descargarArchivo } from '../services/api';

const SalidaMasiva = ({ onClose, onSuccess }) => {
  // Estado del formulario
  const [centroDestino, setCentroDestino] = useState('');
  const [observaciones, setObservaciones] = useState('');
  const [items, setItems] = useState([]);
  
  // Estado de búsqueda de lotes
  const [searchTerm, setSearchTerm] = useState('');
  const [lotesDisponibles, setLotesDisponibles] = useState([]);
  const [loadingLotes, setLoadingLotes] = useState(false);
  
  // Estado de centros
  const [centros, setCentros] = useState([]);
  const [loadingCentros, setLoadingCentros] = useState(true);
  
  // Estado de procesamiento
  const [procesando, setProcesando] = useState(false);
  const [resultado, setResultado] = useState(null);
  
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
  
  // Buscar lotes disponibles
  const buscarLotes = useCallback(async (term) => {
    if (!term || term.length < 2) {
      setLotesDisponibles([]);
      return;
    }
    
    setLoadingLotes(true);
    try {
      const resp = await salidaMasivaAPI.lotesDisponibles({ search: term, page_size: 20 });
      setLotesDisponibles(resp.data.results || []);
    } catch (err) {
      console.error('Error buscando lotes:', err);
      setLotesDisponibles([]);
    } finally {
      setLoadingLotes(false);
    }
  }, []);
  
  // Debounce de búsqueda
  useEffect(() => {
    const timer = setTimeout(() => {
      buscarLotes(searchTerm);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm, buscarLotes]);
  
  // Agregar lote a la lista
  const agregarItem = (lote) => {
    // Verificar si ya existe
    const existe = items.find(item => item.lote_id === lote.id);
    if (existe) {
      toast.error('Este lote ya está en la lista');
      return;
    }
    
    setItems([...items, {
      lote_id: lote.id,
      numero_lote: lote.numero_lote,
      producto_clave: lote.producto_clave,
      producto_nombre: lote.producto_nombre,
      unidad_medida: lote.unidad_medida,
      cantidad_disponible: lote.cantidad_disponible,
      fecha_caducidad: lote.fecha_caducidad,
      cantidad: 1, // Cantidad inicial
    }]);
    
    setSearchTerm('');
    setLotesDisponibles([]);
    toast.success('Producto agregado a la lista');
  };
  
  // Actualizar cantidad de un item
  const actualizarCantidad = (index, cantidad) => {
    const nuevosItems = [...items];
    const cantidadNum = parseInt(cantidad) || 0;
    
    if (cantidadNum > nuevosItems[index].cantidad_disponible) {
      toast.error(`Stock máximo disponible: ${nuevosItems[index].cantidad_disponible}`);
      nuevosItems[index].cantidad = nuevosItems[index].cantidad_disponible;
    } else if (cantidadNum < 1) {
      nuevosItems[index].cantidad = 1;
    } else {
      nuevosItems[index].cantidad = cantidadNum;
    }
    
    setItems(nuevosItems);
  };
  
  // Eliminar item de la lista
  const eliminarItem = (index) => {
    const nuevosItems = items.filter((_, i) => i !== index);
    setItems(nuevosItems);
  };
  
  // Procesar salida masiva
  const procesarSalida = async () => {
    // Validaciones
    if (!centroDestino) {
      toast.error('Seleccione un centro destino');
      return;
    }
    
    if (items.length === 0) {
      toast.error('Agregue al menos un producto a la lista');
      return;
    }
    
    // Verificar cantidades válidas
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
        
        // Callback de éxito
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
  
  // Descargar hoja de entrega
  const descargarHojaEntrega = async () => {
    if (!resultado?.grupo_salida) return;
    
    try {
      const resp = await salidaMasivaAPI.hojaEntregaPdf(resultado.grupo_salida);
      descargarArchivo(resp.data, `Hoja_Entrega_${resultado.grupo_salida}.pdf`);
      toast.success('Hoja de entrega descargada');
    } catch (err) {
      console.error('Error descargando hoja:', err);
      toast.error('Error al descargar hoja de entrega');
    }
  };
  
  // Reiniciar formulario
  const reiniciar = () => {
    setCentroDestino('');
    setObservaciones('');
    setItems([]);
    setResultado(null);
  };
  
  // Calcular total de items
  const totalUnidades = items.reduce((sum, item) => sum + item.cantidad, 0);
  
  // Si hay resultado exitoso, mostrar resumen
  if (resultado) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6 max-w-4xl mx-auto">
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
        <div className="flex justify-center gap-4">
          <button
            onClick={descargarHojaEntrega}
            className="flex items-center gap-2 px-6 py-3 bg-rose-700 text-white rounded-lg hover:bg-rose-800 transition-colors"
          >
            <FaFileDownload />
            Descargar Hoja de Entrega
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
    );
  }
  
  return (
    <div className="bg-white rounded-xl shadow-lg p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6 pb-4 border-b">
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
      
      {/* Selector de Centro Destino */}
      <div className="mb-6">
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          <FaBuilding className="inline mr-2" />
          Centro Destino *
        </label>
        <select
          value={centroDestino}
          onChange={(e) => setCentroDestino(e.target.value)}
          disabled={loadingCentros || items.length > 0}
          className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:outline-none focus:border-rose-500 transition-colors disabled:bg-gray-100"
        >
          <option value="">Seleccione un centro...</option>
          {centros.map((centro) => (
            <option key={centro.id} value={centro.id}>
              {centro.nombre}
            </option>
          ))}
        </select>
        {items.length > 0 && (
          <p className="text-xs text-amber-600 mt-1">
            No puede cambiar el centro después de agregar productos
          </p>
        )}
      </div>
      
      {/* Buscador de Lotes */}
      <div className="mb-6">
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          <FaSearch className="inline mr-2" />
          Buscar Producto/Lote
        </label>
        <div className="relative">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar por clave, nombre o número de lote..."
            disabled={!centroDestino}
            className="w-full px-4 py-3 pl-10 border-2 border-gray-200 rounded-lg focus:outline-none focus:border-rose-500 transition-colors disabled:bg-gray-100"
          />
          <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          {loadingLotes && (
            <FaSpinner className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 animate-spin" />
          )}
        </div>
        
        {/* Resultados de búsqueda */}
        {lotesDisponibles.length > 0 && (
          <div className="mt-2 border rounded-lg max-h-60 overflow-y-auto shadow-lg bg-white">
            {lotesDisponibles.map((lote) => (
              <div
                key={lote.id}
                onClick={() => agregarItem(lote)}
                className="p-3 hover:bg-rose-50 cursor-pointer border-b last:border-b-0 flex justify-between items-center"
              >
                <div>
                  <div className="font-semibold text-gray-800">
                    {lote.producto_clave} - {lote.producto_nombre}
                  </div>
                  <div className="text-sm text-gray-600">
                    Lote: {lote.numero_lote} | Cad: {lote.fecha_caducidad || 'N/A'}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-green-600">{lote.cantidad_disponible}</div>
                  <div className="text-xs text-gray-500">{lote.unidad_medida}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      
      {/* Lista de Items */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-700">
            <FaClipboardList className="inline mr-2" />
            Productos a Entregar ({items.length})
          </h3>
          {items.length > 0 && (
            <span className="text-sm font-semibold text-rose-700">
              Total: {totalUnidades} unidades
            </span>
          )}
        </div>
        
        {items.length === 0 ? (
          <div className="text-center py-8 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
            <FaBox className="text-4xl text-gray-300 mx-auto mb-2" />
            <p className="text-gray-500">
              {centroDestino 
                ? 'Busque y agregue productos a la lista'
                : 'Seleccione un centro destino primero'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto border rounded-lg">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Clave</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Producto</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Lote</th>
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-700">Disponible</th>
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-700">Cantidad</th>
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-700">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {items.map((item, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-3 py-2 font-mono text-sm">{item.producto_clave}</td>
                    <td className="px-3 py-2 text-sm">{item.producto_nombre}</td>
                    <td className="px-3 py-2 text-sm">{item.numero_lote}</td>
                    <td className="px-3 py-2 text-center text-sm text-green-600 font-semibold">
                      {item.cantidad_disponible}
                    </td>
                    <td className="px-3 py-2 text-center">
                      <input
                        type="number"
                        min="1"
                        max={item.cantidad_disponible}
                        value={item.cantidad}
                        onChange={(e) => actualizarCantidad(idx, e.target.value)}
                        className="w-20 px-2 py-1 border rounded text-center focus:outline-none focus:border-rose-500"
                      />
                    </td>
                    <td className="px-3 py-2 text-center">
                      <button
                        onClick={() => eliminarItem(idx)}
                        className="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded"
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
        )}
      </div>
      
      {/* Observaciones */}
      <div className="mb-6">
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          Observaciones
        </label>
        <textarea
          value={observaciones}
          onChange={(e) => setObservaciones(e.target.value)}
          placeholder="Notas adicionales para la entrega..."
          rows={3}
          className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:outline-none focus:border-rose-500 transition-colors resize-none"
        />
      </div>
      
      {/* Botones de Acción */}
      <div className="flex justify-end gap-4">
        {onClose && (
          <button
            onClick={onClose}
            disabled={procesando}
            className="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50"
          >
            Cancelar
          </button>
        )}
        <button
          onClick={procesarSalida}
          disabled={procesando || items.length === 0 || !centroDestino}
          className="flex items-center gap-2 px-6 py-3 bg-rose-700 text-white rounded-lg hover:bg-rose-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {procesando ? (
            <>
              <FaSpinner className="animate-spin" />
              Procesando...
            </>
          ) : (
            <>
              <FaTruck />
              Procesar Salida ({items.length} productos)
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default SalidaMasiva;
