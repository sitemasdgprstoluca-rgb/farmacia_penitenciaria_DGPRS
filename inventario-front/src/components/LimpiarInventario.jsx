/**
 * Componente LimpiarInventario - SOLO PARA SUPERUSUARIOS
 * 
 * Permite eliminar selectivamente datos operativos del inventario:
 * - Productos (incluye lotes, movimientos, requisiciones)
 * - Lotes (mantiene productos)
 * - Requisiciones (mantiene productos y lotes)
 * - Movimientos (solo historial)
 * - Donaciones (donaciones, detalles y salidas)
 * - Todo (incluye donaciones)
 * 
 * NO ELIMINA: Usuarios, Centros, Configuración, Tema, Auditoría
 * 
 * ADVERTENCIA: Esta acción es IRREVERSIBLE.
 */
import { useState } from 'react';
import { toast } from 'react-hot-toast';
import {
  FaTrash,
  FaExclamationTriangle,
  FaSpinner,
  FaBox,
  FaClipboardList,
  FaHistory,
  FaCheck,
  FaTimes,
  FaShieldAlt,
  FaFileAlt,
  FaUsers,
  FaBuilding,
  FaCog,
  FaGift,
  FaLayerGroup,
  FaExchangeAlt,
  FaBroom,
} from 'react-icons/fa';
import { adminAPI } from '../services/api';

const LimpiarInventario = ({ onLimpiezaCompletada }) => {
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [confirmText, setConfirmText] = useState('');
  const [paso, setPaso] = useState(1); // 1: Selección, 2: Stats, 3: Confirmación, 4: Éxito
  const [categoriaSeleccionada, setCategoriaSeleccionada] = useState(null);
  const [resultado, setResultado] = useState(null);

  // Configuración de categorías con iconos y colores
  const categorias = {
    productos: {
      icon: FaBox,
      color: 'red',
      titulo: 'Productos e Inventario',
      descripcion: 'Elimina productos, lotes, movimientos y requisiciones',
      advertencia: 'Elimina TODO el inventario',
    },
    lotes: {
      icon: FaLayerGroup,
      color: 'orange',
      titulo: 'Solo Lotes',
      descripcion: 'Elimina lotes y movimientos asociados, mantiene productos',
      advertencia: 'Los productos quedarán con stock 0',
    },
    requisiciones: {
      icon: FaFileAlt,
      color: 'amber',
      titulo: 'Requisiciones',
      descripcion: 'Elimina requisiciones, historial y ajustes',
      advertencia: 'Mantiene productos y lotes intactos',
    },
    movimientos: {
      icon: FaExchangeAlt,
      color: 'yellow',
      titulo: 'Movimientos',
      descripcion: 'Solo elimina el historial de movimientos',
      advertencia: 'Opción menos destructiva',
    },
    donaciones: {
      icon: FaGift,
      color: 'purple',
      titulo: 'Donaciones',
      descripcion: 'Elimina donaciones, detalles y salidas registradas',
      advertencia: 'Almacén de donaciones quedará vacío',
    },
    todos: {
      icon: FaBroom,
      color: 'red',
      titulo: 'Todo el Inventario',
      descripcion: 'Limpieza completa incluyendo donaciones',
      advertencia: '⚠️ ELIMINA TODO (incluyendo donaciones)',
    },
  };

  // Abrir modal y cargar estadísticas
  const handleAbrir = async () => {
    setShowModal(true);
    setPaso(1);
    setConfirmText('');
    setCategoriaSeleccionada(null);
    setResultado(null);
    setLoading(true);
    
    try {
      const resp = await adminAPI.getLimpiarDatosStats();
      setStats(resp.data);
    } catch (err) {
      console.error('Error obteniendo estadísticas:', err);
      if (err.response?.status === 403) {
        toast.error('Solo SUPERUSUARIOS pueden acceder a esta función');
        setShowModal(false);
      } else {
        toast.error('Error al obtener estadísticas');
      }
    } finally {
      setLoading(false);
    }
  };

  // Cerrar modal
  const handleCerrar = () => {
    setShowModal(false);
    setStats(null);
    setConfirmText('');
    setPaso(1);
    setCategoriaSeleccionada(null);
    setResultado(null);
  };

  // Seleccionar categoría y pasar a confirmación
  const handleSeleccionarCategoria = (cat) => {
    setCategoriaSeleccionada(cat);
    setPaso(2);
  };

  // Ejecutar limpieza
  const handleLimpiar = async () => {
    const palabraConfirmacion = categoriaSeleccionada === 'todos' ? 'ELIMINAR TODO' : 'CONFIRMAR';
    
    if (confirmText !== palabraConfirmacion) {
      toast.error(`Escriba "${palabraConfirmacion}" para confirmar`);
      return;
    }

    setLoading(true);
    
    try {
      const resp = await adminAPI.limpiarDatos(true, categoriaSeleccionada);
      setResultado(resp.data);
      setPaso(3);
      toast.success(resp.data.mensaje || 'Limpieza completada');
      
      // Notificar al padre si existe callback
      if (onLimpiezaCompletada) {
        onLimpiezaCompletada(resp.data);
      }
    } catch (err) {
      console.error('Error limpiando datos:', err);
      toast.error(err.response?.data?.error || 'Error al limpiar datos');
    } finally {
      setLoading(false);
    }
  };

  // Obtener datos de categoría de stats
  const getCategoriaStats = (cat) => {
    if (!stats?.categorias) return null;
    return stats.categorias[cat];
  };

  // Verificar si hay datos para eliminar en una categoría
  const hayDatosEnCategoria = (cat) => {
    const catStats = getCategoriaStats(cat);
    return catStats && catStats.total > 0;
  };

  // Renderizar tarjeta de categoría
  const renderCategoriaCard = (catKey) => {
    const cat = categorias[catKey];
    const catStats = getCategoriaStats(catKey);
    const hayDatos = hayDatosEnCategoria(catKey);
    const Icon = cat.icon;
    
    const colorClasses = {
      red: 'bg-red-50 border-red-200 hover:bg-red-100 hover:border-red-300',
      orange: 'bg-orange-50 border-orange-200 hover:bg-orange-100 hover:border-orange-300',
      amber: 'bg-amber-50 border-amber-200 hover:bg-amber-100 hover:border-amber-300',
      yellow: 'bg-yellow-50 border-yellow-200 hover:bg-yellow-100 hover:border-yellow-300',
      purple: 'bg-purple-50 border-purple-200 hover:bg-purple-100 hover:border-purple-300',
    };
    
    const textClasses = {
      red: 'text-red-700',
      orange: 'text-orange-700',
      amber: 'text-amber-700',
      yellow: 'text-yellow-700',
      purple: 'text-purple-700',
    };
    
    const iconClasses = {
      red: 'text-red-500 bg-red-100',
      orange: 'text-orange-500 bg-orange-100',
      amber: 'text-amber-500 bg-amber-100',
      yellow: 'text-yellow-500 bg-yellow-100',
      purple: 'text-purple-500 bg-purple-100',
    };

    return (
      <button
        key={catKey}
        onClick={() => hayDatos && handleSeleccionarCategoria(catKey)}
        disabled={!hayDatos}
        className={`text-left p-4 rounded-xl border-2 transition-all ${
          hayDatos 
            ? `${colorClasses[cat.color]} cursor-pointer` 
            : 'bg-gray-50 border-gray-200 cursor-not-allowed opacity-60'
        }`}
      >
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${hayDatos ? iconClasses[cat.color] : 'bg-gray-200 text-gray-400'}`}>
            <Icon className="text-lg" />
          </div>
          <div className="flex-1">
            <h4 className={`font-semibold ${hayDatos ? textClasses[cat.color] : 'text-gray-500'}`}>
              {cat.titulo}
            </h4>
            <p className="text-xs text-gray-500 mt-1">{cat.descripcion}</p>
            {catStats && (
              <p className={`text-lg font-bold mt-2 ${hayDatos ? textClasses[cat.color] : 'text-gray-400'}`}>
                {catStats.total.toLocaleString()} registros
              </p>
            )}
            {hayDatos && (
              <p className="text-xs text-red-600 mt-1 font-medium">{cat.advertencia}</p>
            )}
          </div>
        </div>
      </button>
    );
  };

  return (
    <>
      {/* Botón de activación */}
      <button
        onClick={handleAbrir}
        className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition bg-red-600 text-white hover:bg-red-700"
        title="Limpiar datos del inventario (Solo Superusuarios)"
      >
        <FaBroom /> Limpiar Inventario
      </button>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b bg-red-50 sticky top-0 z-10">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-red-100 rounded-lg">
                  <FaShieldAlt className="text-xl text-red-600" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-red-800">
                    {paso === 3 ? 'Limpieza Completada' : 'Limpiar Datos del Inventario'}
                  </h2>
                  <p className="text-sm text-red-600">Solo Superusuarios • Acción irreversible</p>
                </div>
              </div>
              <button
                onClick={handleCerrar}
                className="p-2 hover:bg-red-100 rounded-lg transition-colors"
              >
                <FaTimes className="text-red-600" />
              </button>
            </div>

            {/* Contenido */}
            <div className="p-6">
              {loading && paso !== 3 ? (
                <div className="flex flex-col items-center justify-center py-8">
                  <FaSpinner className="animate-spin text-4xl text-red-500 mb-4" />
                  <p className="text-gray-600">
                    {paso === 2 ? 'Eliminando datos...' : 'Cargando estadísticas...'}
                  </p>
                </div>
              ) : paso === 1 && stats ? (
                <>
                  {/* Advertencia general */}
                  <div className="bg-red-100 border border-red-300 rounded-lg p-4 mb-6">
                    <div className="flex items-start gap-3">
                      <FaExclamationTriangle className="text-red-600 text-xl flex-shrink-0 mt-0.5" />
                      <div>
                        <h3 className="font-bold text-red-800">Seleccione qué desea eliminar</h3>
                        <p className="text-sm text-red-700 mt-1">
                          Elija una categoría según sus necesidades. Cada opción tiene diferentes niveles de impacto.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Tarjetas de categorías */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                    {renderCategoriaCard('movimientos')}
                    {renderCategoriaCard('requisiciones')}
                    {renderCategoriaCard('lotes')}
                    {renderCategoriaCard('productos')}
                    {renderCategoriaCard('donaciones')}
                  </div>
                  
                  {/* Opción TODO */}
                  <div className="border-t pt-4">
                    <p className="text-sm text-gray-500 mb-3 text-center">¿Necesita una limpieza completa?</p>
                    {renderCategoriaCard('todos')}
                  </div>

                  {/* Lo que NO se elimina */}
                  <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-4">
                    <h4 className="font-semibold text-green-800 mb-2">✓ Nunca se eliminará:</h4>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
                      {stats.no_se_eliminara?.map((item, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-green-700">
                          <FaCheck className="text-green-500 text-xs" />
                          <span>{item}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Botón cancelar */}
                  <div className="flex justify-end mt-6">
                    <button
                      onClick={handleCerrar}
                      className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      Cancelar
                    </button>
                  </div>
                </>
              ) : paso === 2 && categoriaSeleccionada ? (
                <>
                  {/* Detalle de lo que se eliminará */}
                  {(() => {
                    const cat = categorias[categoriaSeleccionada];
                    const catStats = getCategoriaStats(categoriaSeleccionada);
                    const Icon = cat.icon;
                    const palabraConfirmacion = categoriaSeleccionada === 'todos' ? 'ELIMINAR TODO' : 'CONFIRMAR';
                    
                    return (
                      <>
                        <div className="bg-red-100 border-2 border-red-400 rounded-lg p-4 mb-6">
                          <div className="flex items-center gap-3 mb-3">
                            <Icon className="text-red-600 text-2xl" />
                            <div>
                              <h3 className="font-bold text-red-800">{cat.titulo}</h3>
                              <p className="text-sm text-red-700">{cat.descripcion}</p>
                            </div>
                          </div>
                          
                          {/* Detalle de registros */}
                          {catStats?.detalle && (
                            <div className="bg-white/50 rounded-lg p-3 mt-3">
                              <p className="text-sm font-semibold text-red-800 mb-2">Se eliminarán:</p>
                              <div className="grid grid-cols-2 gap-2 text-sm">
                                {Object.entries(catStats.detalle).map(([key, val]) => (
                                  <div key={key} className="flex justify-between">
                                    <span className="text-red-700">{key.replace(/_/g, ' ')}:</span>
                                    <span className="font-semibold text-red-800">{val.toLocaleString()}</span>
                                  </div>
                                ))}
                              </div>
                              <div className="border-t border-red-300 mt-2 pt-2 flex justify-between">
                                <span className="font-bold text-red-800">TOTAL:</span>
                                <span className="font-bold text-red-900">{catStats.total.toLocaleString()} registros</span>
                              </div>
                            </div>
                          )}
                          
                          {/* Dependencias */}
                          {catStats?.dependencias?.length > 0 && (
                            <div className="mt-3 text-sm text-red-700">
                              <p className="font-medium">⚠️ Nota:</p>
                              {catStats.dependencias.map((dep, idx) => (
                                <p key={idx} className="ml-4">• {dep}</p>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Advertencias */}
                        {stats?.advertencias?.length > 0 && (
                          <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 mb-6">
                            <h4 className="font-semibold text-amber-800 mb-2">⚠️ Advertencias:</h4>
                            {stats.advertencias.map((adv, idx) => (
                              <p key={idx} className="text-sm text-amber-700">{adv}</p>
                            ))}
                          </div>
                        )}

                        {/* Campo de confirmación */}
                        <div className="bg-gray-50 rounded-lg p-4 mb-6">
                          <p className="text-sm text-gray-700 mb-3">
                            Esta acción <strong>NO SE PUEDE DESHACER</strong>. Escriba{' '}
                            <code className="bg-red-200 px-2 py-1 rounded font-bold">{palabraConfirmacion}</code> para confirmar:
                          </p>
                          <input
                            type="text"
                            value={confirmText}
                            onChange={(e) => setConfirmText(e.target.value.toUpperCase())}
                            placeholder={`Escriba ${palabraConfirmacion}`}
                            className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-red-500 text-center font-mono text-lg"
                            autoFocus
                          />
                        </div>

                        {/* Botones */}
                        <div className="flex justify-end gap-3">
                          <button
                            onClick={() => {
                              setPaso(1);
                              setConfirmText('');
                              setCategoriaSeleccionada(null);
                            }}
                            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                          >
                            Atrás
                          </button>
                          <button
                            onClick={handleLimpiar}
                            disabled={confirmText !== palabraConfirmacion || loading}
                            className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {loading ? (
                              <>
                                <FaSpinner className="animate-spin" /> Eliminando...
                              </>
                            ) : (
                              <>
                                <FaTrash /> Eliminar
                              </>
                            )}
                          </button>
                        </div>
                      </>
                    );
                  })()}
                </>
              ) : paso === 3 && resultado ? (
                <>
                  {/* Éxito */}
                  <div className="text-center mb-6">
                    <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <FaCheck className="text-3xl text-green-600" />
                    </div>
                    <h3 className="text-xl font-bold text-gray-800">¡Limpieza Completada!</h3>
                    <p className="text-gray-600 mt-2">{resultado.mensaje}</p>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-4 mb-6">
                    <h4 className="font-semibold text-gray-700 mb-3">Resumen de eliminación:</h4>
                    <div className="space-y-2 text-sm">
                      {resultado.eliminados && Object.entries(resultado.eliminados).map(([key, val]) => (
                        <div key={key} className="flex justify-between">
                          <span className="text-gray-600">{key.replace(/_/g, ' ')}:</span>
                          <span className="font-semibold text-red-600">{val.toLocaleString()}</span>
                        </div>
                      ))}
                      {resultado.total_registros_eliminados !== undefined && (
                        <div className="flex justify-between pt-2 border-t border-gray-300">
                          <span className="text-gray-700 font-semibold">Total eliminados:</span>
                          <span className="font-bold text-red-700">{resultado.total_registros_eliminados.toLocaleString()}</span>
                        </div>
                      )}
                      <div className="flex justify-between pt-2 border-t">
                        <span className="text-gray-600">Ejecutado por:</span>
                        <span className="font-semibold">{resultado.ejecutado_por}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Fecha:</span>
                        <span className="font-semibold">{new Date(resultado.fecha).toLocaleString('es-MX')}</span>
                      </div>
                    </div>
                  </div>

                  {/* Lo que se mantuvo */}
                  {resultado.no_eliminado && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-6">
                      <p className="text-sm text-green-700 font-semibold mb-2">✓ Se mantuvieron intactos:</p>
                      <p className="text-sm text-green-600">{resultado.no_eliminado.join(', ')}</p>
                    </div>
                  )}

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-6">
                    <p className="text-sm text-blue-700">
                      <strong>Siguiente paso:</strong> {
                        resultado.categoria === 'productos' || resultado.categoria === 'todos'
                          ? 'Importe productos y lotes usando los importadores Excel.'
                          : resultado.categoria === 'lotes'
                          ? 'Importe lotes para los productos existentes.'
                          : 'El sistema está listo para continuar operando.'
                      }
                    </p>
                  </div>

                  <div className="flex justify-end">
                    <button
                      onClick={handleCerrar}
                      className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                    >
                      Entendido
                    </button>
                  </div>
                </>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default LimpiarInventario;
