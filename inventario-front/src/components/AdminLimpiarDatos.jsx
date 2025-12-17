/**
 * Componente AdminLimpiarDatos - SOLO PARA SUPERUSUARIOS
 * 
 * Permite eliminar datos operativos del inventario (productos, lotes, 
 * movimientos, requisiciones) para empezar de cero después de capacitación.
 * 
 * NO ELIMINA: Usuarios, Centros, Configuración, Tema, Donaciones, Auditoría
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
} from 'react-icons/fa';
import { adminAPI } from '../services/api';

const AdminLimpiarDatos = () => {
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [confirmText, setConfirmText] = useState('');
  const [paso, setPaso] = useState(1); // 1: Stats, 2: Confirmación, 3: Éxito
  const [resultado, setResultado] = useState(null);

  // Abrir modal y cargar estadísticas
  const handleAbrir = async () => {
    setShowModal(true);
    setPaso(1);
    setConfirmText('');
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
  };

  // Ejecutar limpieza
  const handleLimpiar = async () => {
    if (confirmText !== 'ELIMINAR TODO') {
      toast.error('Escriba "ELIMINAR TODO" para confirmar');
      return;
    }

    setLoading(true);
    
    try {
      const resp = await adminAPI.limpiarDatos(true);
      setResultado(resp.data);
      setPaso(3);
      toast.success('Datos eliminados correctamente');
    } catch (err) {
      console.error('Error limpiando datos:', err);
      toast.error(err.response?.data?.error || 'Error al limpiar datos');
    } finally {
      setLoading(false);
    }
  };

  // Obtener valores de stats con estructura nueva o antigua
  const getStatValue = (key) => {
    if (!stats) return 0;
    // Nueva estructura: stats.resumen.productos
    if (stats.resumen) return stats.resumen[key] || 0;
    // Estructura antigua: stats.productos
    return stats[key] || 0;
  };

  // Verificar si hay datos para eliminar
  const hayDatosParaEliminar = () => {
    return getStatValue('productos') > 0 || 
           getStatValue('lotes') > 0 || 
           getStatValue('movimientos') > 0 ||
           getStatValue('requisiciones') > 0;
  };

  return (
    <>
      {/* Botón de activación */}
      <button
        onClick={handleAbrir}
        className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
      >
        <FaTrash /> Limpiar Inventario
      </button>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b bg-red-50 sticky top-0">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-red-100 rounded-lg">
                  <FaShieldAlt className="text-xl text-red-600" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-red-800">
                    {paso === 3 ? 'Limpieza Completada' : 'Reiniciar Sistema de Inventario'}
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
              {loading && paso !== 3 ? (
                <div className="flex flex-col items-center justify-center py-8">
                  <FaSpinner className="animate-spin text-4xl text-red-500 mb-4" />
                  <p className="text-gray-600">
                    {paso === 2 ? 'Eliminando datos...' : 'Cargando estadísticas...'}
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
                          {stats.mensaje || 'Esta operación eliminará todos los datos operativos del inventario.'}
                        </p>
                        <p className="text-sm text-red-700 mt-2 font-semibold">
                          {stats.advertencia_principal || stats.advertencia || '⚠️ ACCIÓN IRREVERSIBLE'}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Advertencias adicionales */}
                  {stats.advertencias && stats.advertencias.length > 0 && (
                    <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 mb-6">
                      <h4 className="font-semibold text-amber-800 mb-2">⚠️ Advertencias:</h4>
                      {stats.advertencias.map((adv, idx) => (
                        <p key={idx} className="text-sm text-amber-700">{adv}</p>
                      ))}
                    </div>
                  )}

                  {/* Estadísticas principales */}
                  <h4 className="font-semibold text-gray-700 mb-3">Se eliminarán:</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-center">
                      <FaBox className="mx-auto text-xl text-red-600 mb-1" />
                      <p className="text-xl font-bold text-red-700">{getStatValue('productos')}</p>
                      <p className="text-xs text-red-600">Productos</p>
                    </div>
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-center">
                      <FaClipboardList className="mx-auto text-xl text-red-600 mb-1" />
                      <p className="text-xl font-bold text-red-700">{getStatValue('lotes')}</p>
                      <p className="text-xs text-red-600">Lotes</p>
                    </div>
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-center">
                      <FaHistory className="mx-auto text-xl text-red-600 mb-1" />
                      <p className="text-xl font-bold text-red-700">{getStatValue('movimientos')}</p>
                      <p className="text-xs text-red-600">Movimientos</p>
                    </div>
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-center">
                      <FaFileAlt className="mx-auto text-xl text-red-600 mb-1" />
                      <p className="text-xl font-bold text-red-700">{getStatValue('requisiciones')}</p>
                      <p className="text-xs text-red-600">Requisiciones</p>
                    </div>
                  </div>

                  {/* Lo que NO se elimina */}
                  <h4 className="font-semibold text-gray-700 mb-3">NO se eliminarán (se mantienen):</h4>
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
                    <div className="grid grid-cols-2 gap-3 text-sm">
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
                        <span>Configuración</span>
                      </div>
                      <div className="flex items-center gap-2 text-green-700">
                        <FaGift className="text-green-600" />
                        <span>Donaciones</span>
                      </div>
                      <div className="flex items-center gap-2 text-green-700">
                        <FaHistory className="text-green-600" />
                        <span>Logs de auditoría</span>
                      </div>
                      <div className="flex items-center gap-2 text-green-700">
                        <FaShieldAlt className="text-green-600" />
                        <span>Permisos y roles</span>
                      </div>
                    </div>
                  </div>

                  {/* Botón continuar */}
                  <div className="flex justify-end gap-3">
                    <button
                      onClick={handleCerrar}
                      className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      Cancelar
                    </button>
                    <button
                      onClick={() => setPaso(2)}
                      disabled={!hayDatosParaEliminar()}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {hayDatosParaEliminar() ? 'Continuar' : 'No hay datos para eliminar'}
                    </button>
                  </div>
                </>
              ) : paso === 2 ? (
                <>
                  {/* Confirmación final */}
                  <div className="bg-red-100 border-2 border-red-400 rounded-lg p-4 mb-6">
                    <div className="flex items-center gap-2 mb-3">
                      <FaExclamationTriangle className="text-red-600 text-xl" />
                      <h3 className="font-bold text-red-800">Confirmación Final</h3>
                    </div>
                    <p className="text-sm text-red-700 mb-4">
                      Esta acción eliminará <strong>permanentemente</strong> todos los productos, 
                      lotes y movimientos del inventario principal. 
                      Esta operación <strong>NO SE PUEDE DESHACER</strong>.
                    </p>
                    <p className="text-sm text-red-800 font-semibold">
                      Escriba <code className="bg-red-200 px-2 py-1 rounded">ELIMINAR TODO</code> para confirmar:
                    </p>
                  </div>

                  <input
                    type="text"
                    value={confirmText}
                    onChange={(e) => setConfirmText(e.target.value.toUpperCase())}
                    placeholder="Escriba ELIMINAR TODO"
                    className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-red-500 text-center font-mono text-lg mb-6"
                    autoFocus
                  />

                  <div className="flex justify-end gap-3">
                    <button
                      onClick={() => {
                        setPaso(1);
                        setConfirmText('');
                      }}
                      className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      Atrás
                    </button>
                    <button
                      onClick={handleLimpiar}
                      disabled={confirmText !== 'ELIMINAR TODO' || loading}
                      className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loading ? (
                        <>
                          <FaSpinner className="animate-spin" /> Eliminando...
                        </>
                      ) : (
                        <>
                          <FaTrash /> Eliminar Todo
                        </>
                      )}
                    </button>
                  </div>
                </>
              ) : paso === 3 && resultado ? (
                <>
                  {/* Éxito */}
                  <div className="text-center mb-6">
                    <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <FaCheck className="text-3xl text-green-600" />
                    </div>
                    <h3 className="text-xl font-bold text-gray-800">¡Limpieza Completada!</h3>
                    <p className="text-gray-600 mt-2">{resultado.mensaje || 'El sistema está listo para comenzar de nuevo.'}</p>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-4 mb-6">
                    <h4 className="font-semibold text-gray-700 mb-3">Resumen de eliminación:</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Productos eliminados:</span>
                        <span className="font-semibold text-red-600">{resultado.eliminados?.productos || 0}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Lotes eliminados:</span>
                        <span className="font-semibold text-red-600">{resultado.eliminados?.lotes || 0}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Movimientos eliminados:</span>
                        <span className="font-semibold text-red-600">{resultado.eliminados?.movimientos || 0}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Requisiciones eliminadas:</span>
                        <span className="font-semibold text-red-600">{resultado.eliminados?.requisiciones || 0}</span>
                      </div>
                      {resultado.total_registros_eliminados && (
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
                      <strong>Siguiente paso:</strong> Importe productos y lotes usando los importadores Excel 
                      para comenzar a operar el sistema.
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
