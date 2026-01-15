/**
 * Componente AdminLimpiarDatos - SOLO PARA SUPERUSUARIOS
 * Versión: 2.1 - 15/Enero/2026
 * 
 * Permite eliminar datos operativos del sistema de forma SELECTIVA por categoría.
 * 
 * CATEGORÍAS DISPONIBLES (10 total):
 * 1. Productos e Inventario - productos, imágenes, lotes, documentos
 * 2. Solo Lotes - lotes sin eliminar productos
 * 3. Requisiciones - requisiciones, detalles, historial, ajustes
 * 4. Movimientos - historial de movimientos
 * 5. Donaciones - donaciones, detalles, salidas, catálogo donación
 * 6. Notificaciones - alertas de usuarios
 * 7. Dispensaciones (Formato C) - dispensaciones a pacientes
 * 8. Pacientes/Internos - catálogo de pacientes
 * 9. Caja Chica - compras, inventario y movimientos de caja chica
 * 10. Todo el Sistema - elimina todo lo anterior
 * 
 * NO ELIMINA (siempre se mantienen):
 * - Usuarios y perfiles
 * - Centros
 * - Configuración del sistema
 * - Tema global (estilos)
 * - Logs de auditoría
 * - Permisos y grupos
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
  FaBell,
  FaPills,
  FaUserInjured,
  FaMoneyBillWave,
} from 'react-icons/fa';
import { adminAPI } from '../services/api';

// Iconos por categoría
const CATEGORY_ICONS = {
  productos: FaBox,
  lotes: FaClipboardList,
  requisiciones: FaFileAlt,
  movimientos: FaHistory,
  donaciones: FaGift,
  notificaciones: FaBell,
  dispensaciones: FaPills,
  pacientes: FaUserInjured,
  caja_chica: FaMoneyBillWave,
  todos: FaTrash,
};

// Colores por categoría
const CATEGORY_COLORS = {
  productos: 'bg-blue-50 border-blue-200 text-blue-700',
  lotes: 'bg-purple-50 border-purple-200 text-purple-700',
  requisiciones: 'bg-indigo-50 border-indigo-200 text-indigo-700',
  movimientos: 'bg-cyan-50 border-cyan-200 text-cyan-700',
  donaciones: 'bg-pink-50 border-pink-200 text-pink-700',
  notificaciones: 'bg-amber-50 border-amber-200 text-amber-700',
  dispensaciones: 'bg-teal-50 border-teal-200 text-teal-700',
  pacientes: 'bg-emerald-50 border-emerald-200 text-emerald-700',
  caja_chica: 'bg-lime-50 border-lime-200 text-lime-700',
  todos: 'bg-red-50 border-red-300 text-red-700',
};

const AdminLimpiarDatos = () => {
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [confirmText, setConfirmText] = useState('');
  const [paso, setPaso] = useState(1); // 1: Selección, 2: Detalle, 3: Confirmación, 4: Éxito
  const [resultado, setResultado] = useState(null);
  const [categoriaSeleccionada, setCategoriaSeleccionada] = useState(null);

  // Abrir modal y cargar estadísticas
  const handleAbrir = async () => {
    setShowModal(true);
    setPaso(1);
    setConfirmText('');
    setCategoriaSeleccionada(null);
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
    setResultado(null);
    setCategoriaSeleccionada(null);
  };

  // Seleccionar categoría
  const handleSelectCategoria = (categoria) => {
    setCategoriaSeleccionada(categoria);
    setPaso(2);
  };

  // Ejecutar limpieza
  const handleLimpiar = async () => {
    const textoConfirmacion = categoriaSeleccionada === 'todos' ? 'ELIMINAR TODO' : 'ELIMINAR';
    if (confirmText !== textoConfirmacion) {
      toast.error(`Escriba "${textoConfirmacion}" para confirmar`);
      return;
    }

    setLoading(true);
    
    try {
      const resp = await adminAPI.limpiarDatos(true, categoriaSeleccionada);
      setResultado(resp.data);
      setPaso(4);
      toast.success('Datos eliminados correctamente');
    } catch (err) {
      console.error('Error limpiando datos:', err);
      toast.error(err.response?.data?.error || 'Error al limpiar datos');
    } finally {
      setLoading(false);
    }
  };

  // Obtener datos de categoría
  const getCategoriaData = (key) => {
    if (!stats?.categorias) return null;
    return stats.categorias[key];
  };

  // Renderizar tarjeta de categoría
  const renderCategoriaCard = (key) => {
    const cat = getCategoriaData(key);
    if (!cat) return null;
    
    const Icon = CATEGORY_ICONS[key] || FaBox;
    const colorClass = CATEGORY_COLORS[key] || 'bg-gray-50 border-gray-200 text-gray-700';
    const tieneData = cat.total > 0;
    
    return (
      <button
        key={key}
        onClick={() => tieneData && handleSelectCategoria(key)}
        disabled={!tieneData}
        className={`p-4 rounded-lg border-2 transition-all ${
          tieneData 
            ? `${colorClass} hover:scale-105 hover:shadow-md cursor-pointer` 
            : 'bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed opacity-60'
        }`}
      >
        <Icon className={`mx-auto text-2xl mb-2 ${tieneData ? '' : 'text-gray-300'}`} />
        <p className={`text-lg font-bold ${tieneData ? '' : 'text-gray-400'}`}>{cat.total}</p>
        <p className="text-xs font-medium">{cat.nombre}</p>
        {key === 'todos' && <p className="text-xs mt-1 opacity-75">⚠️ Todo</p>}
      </button>
    );
  };

  return (
    <>
      {/* Botón de activación */}
      <button
        onClick={handleAbrir}
        className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
      >
        <FaTrash /> Limpiar Datos del Sistema
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
                    {paso === 4 ? 'Limpieza Completada' : 'Limpiar Datos del Sistema'}
                  </h2>
                  <p className="text-sm text-red-600">Solo Superusuarios</p>
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
              {loading && paso !== 4 ? (
                <div className="flex flex-col items-center justify-center py-8">
                  <FaSpinner className="animate-spin text-4xl text-red-500 mb-4" />
                  <p className="text-gray-600">
                    {paso === 3 ? 'Eliminando datos...' : 'Cargando estadísticas...'}
                  </p>
                </div>
              ) : paso === 1 && stats ? (
                <>
                  {/* Advertencia */}
                  <div className="bg-red-100 border border-red-300 rounded-lg p-4 mb-6">
                    <div className="flex items-start gap-3">
                      <FaExclamationTriangle className="text-red-600 text-xl flex-shrink-0 mt-0.5" />
                      <div>
                        <h3 className="font-bold text-red-800">¡ADVERTENCIA IMPORTANTE!</h3>
                        <p className="text-sm text-red-700 mt-1">
                          Seleccione la categoría de datos que desea eliminar. Esta acción es <strong>IRREVERSIBLE</strong>.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Advertencias adicionales del sistema */}
                  {stats.advertencias && stats.advertencias.length > 0 && (
                    <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 mb-6">
                      <h4 className="font-semibold text-amber-800 mb-2">⚠️ Advertencias:</h4>
                      {stats.advertencias.map((adv, idx) => (
                        <p key={idx} className="text-sm text-amber-700">{adv}</p>
                      ))}
                    </div>
                  )}

                  {/* Selección de categoría */}
                  <h4 className="font-semibold text-gray-700 mb-3">Seleccione qué datos eliminar:</h4>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
                    {['productos', 'lotes', 'requisiciones', 'movimientos', 'donaciones'].map(key => 
                      renderCategoriaCard(key)
                    )}
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
                    {['notificaciones', 'dispensaciones', 'pacientes', 'caja_chica', 'todos'].map(key => 
                      renderCategoriaCard(key)
                    )}
                  </div>

                  {/* Lo que NO se elimina */}
                  <h4 className="font-semibold text-gray-700 mb-3">NUNCA se eliminarán (siempre se mantienen):</h4>
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                      <div className="flex items-center gap-2 text-green-700">
                        <FaUsers className="text-green-600" />
                        <span>Usuarios y perfiles</span>
                      </div>
                      <div className="flex items-center gap-2 text-green-700">
                        <FaBuilding className="text-green-600" />
                        <span>Centros</span>
                      </div>
                      <div className="flex items-center gap-2 text-green-700">
                        <FaCog className="text-green-600" />
                        <span>Configuración del sistema</span>
                      </div>
                      <div className="flex items-center gap-2 text-green-700">
                        <FaHistory className="text-green-600" />
                        <span>Logs de auditoría</span>
                      </div>
                      <div className="flex items-center gap-2 text-green-700">
                        <FaShieldAlt className="text-green-600" />
                        <span>Permisos y roles</span>
                      </div>
                      <div className="flex items-center gap-2 text-green-700">
                        <FaCog className="text-green-600" />
                        <span>Tema global</span>
                      </div>
                    </div>
                  </div>

                  {/* Botón cerrar */}
                  <div className="flex justify-end">
                    <button
                      onClick={handleCerrar}
                      className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      Cerrar
                    </button>
                  </div>
                </>
              ) : paso === 2 && categoriaSeleccionada && stats ? (
                <>
                  {/* Detalle de la categoría seleccionada */}
                  {(() => {
                    const cat = getCategoriaData(categoriaSeleccionada);
                    const Icon = CATEGORY_ICONS[categoriaSeleccionada];
                    return (
                      <>
                        <div className="bg-red-100 border-2 border-red-300 rounded-lg p-4 mb-6">
                          <div className="flex items-center gap-3 mb-3">
                            <Icon className="text-2xl text-red-600" />
                            <div>
                              <h3 className="font-bold text-red-800">{cat.nombre}</h3>
                              <p className="text-sm text-red-600">{cat.descripcion}</p>
                            </div>
                          </div>
                        </div>

                        {/* Detalle de lo que se eliminará */}
                        <h4 className="font-semibold text-gray-700 mb-3">Detalle de registros a eliminar:</h4>
                        <div className="bg-gray-50 rounded-lg p-4 mb-6">
                          <div className="space-y-2 text-sm">
                            {Object.entries(cat.detalle || {}).map(([key, value]) => (
                              <div key={key} className="flex justify-between">
                                <span className="text-gray-600 capitalize">{key.replace(/_/g, ' ')}:</span>
                                <span className="font-semibold text-red-600">{value}</span>
                              </div>
                            ))}
                            <div className="flex justify-between pt-2 border-t border-gray-300">
                              <span className="text-gray-700 font-semibold">Total:</span>
                              <span className="font-bold text-red-700">{cat.total}</span>
                            </div>
                          </div>
                        </div>

                        {/* Dependencias/Advertencias */}
                        {cat.dependencias && cat.dependencias.length > 0 && (
                          <div className="bg-amber-50 border border-amber-300 rounded-lg p-3 mb-6">
                            <p className="text-sm text-amber-800 font-semibold mb-1">⚠️ Dependencias:</p>
                            {cat.dependencias.map((dep, idx) => (
                              <p key={idx} className="text-sm text-amber-700">{dep}</p>
                            ))}
                          </div>
                        )}

                        {/* Botones */}
                        <div className="flex justify-end gap-3">
                          <button
                            onClick={() => {
                              setCategoriaSeleccionada(null);
                              setPaso(1);
                            }}
                            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                          >
                            Atrás
                          </button>
                          <button
                            onClick={() => setPaso(3)}
                            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                          >
                            Continuar a Confirmación
                          </button>
                        </div>
                      </>
                    );
                  })()}
                </>
              ) : paso === 3 ? (
                <>
                  {/* Confirmación final */}
                  {(() => {
                    const cat = getCategoriaData(categoriaSeleccionada);
                    const textoConfirmacion = categoriaSeleccionada === 'todos' ? 'ELIMINAR TODO' : 'ELIMINAR';
                    return (
                      <>
                        <div className="bg-red-100 border-2 border-red-400 rounded-lg p-4 mb-6">
                          <div className="flex items-center gap-2 mb-3">
                            <FaExclamationTriangle className="text-red-600 text-xl" />
                            <h3 className="font-bold text-red-800">Confirmación Final - {cat.nombre}</h3>
                          </div>
                          <p className="text-sm text-red-700 mb-4">
                            Esta acción eliminará <strong>permanentemente</strong> {cat.total} registros 
                            de la categoría <strong>{cat.nombre}</strong>.
                            Esta operación <strong>NO SE PUEDE DESHACER</strong>.
                          </p>
                          <p className="text-sm text-red-800 font-semibold">
                            Escriba <code className="bg-red-200 px-2 py-1 rounded">{textoConfirmacion}</code> para confirmar:
                          </p>
                        </div>

                        <input
                          type="text"
                          value={confirmText}
                          onChange={(e) => setConfirmText(e.target.value.toUpperCase())}
                          placeholder={`Escriba ${textoConfirmacion}`}
                          className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-red-500 text-center font-mono text-lg mb-6"
                          autoFocus
                        />

                        <div className="flex justify-end gap-3">
                          <button
                            onClick={() => {
                              setPaso(2);
                              setConfirmText('');
                            }}
                            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                          >
                            Atrás
                          </button>
                          <button
                            onClick={handleLimpiar}
                            disabled={confirmText !== textoConfirmacion || loading}
                            className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {loading ? (
                              <>
                                <FaSpinner className="animate-spin" /> Eliminando...
                              </>
                            ) : (
                              <>
                                <FaTrash /> {textoConfirmacion}
                              </>
                            )}
                          </button>
                        </div>
                      </>
                    );
                  })()}
                </>
              ) : paso === 4 && resultado ? (
                <>
                  {/* Éxito */}
                  <div className="text-center mb-6">
                    <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <FaCheck className="text-3xl text-green-600" />
                    </div>
                    <h3 className="text-xl font-bold text-gray-800">¡Limpieza Completada!</h3>
                    <p className="text-gray-600 mt-2">{resultado.mensaje || 'Los datos han sido eliminados correctamente.'}</p>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-4 mb-6">
                    <h4 className="font-semibold text-gray-700 mb-3">Resumen de eliminación ({resultado.categoria}):</h4>
                    <div className="space-y-2 text-sm max-h-60 overflow-y-auto">
                      {Object.entries(resultado.eliminados || {}).map(([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <span className="text-gray-600 capitalize">{key.replace(/_/g, ' ')}:</span>
                          <span className="font-semibold text-red-600">{value}</span>
                        </div>
                      ))}
                      {resultado.total_registros_eliminados !== undefined && (
                        <div className="flex justify-between pt-2 border-t border-gray-300">
                          <span className="text-gray-700 font-semibold">Total registros eliminados:</span>
                          <span className="font-bold text-red-700">{resultado.total_registros_eliminados}</span>
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
                      <strong>Siguiente paso:</strong> Si eliminó productos o lotes, puede importarlos nuevamente 
                      usando los importadores Excel del sistema.
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

export default AdminLimpiarDatos;
