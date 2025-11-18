import { useState, useEffect } from 'react';
import { usuariosAPI } from '../services/api';
import { toast } from 'react-hot-toast';
import { FaPlus, FaEdit, FaTrash, FaKey, FaUsers } from 'react-icons/fa';
import { DEV_CONFIG } from '../config/dev';
import PageHeader from '../components/PageHeader';
import { COLORS } from '../constants/theme';

const MOCK_USUARIOS = Array.from({ length: 12 }).map((_, index) => ({
  id: index + 1,
  username: `usuario${index + 1}`,
  first_name: ['María', 'Juan', 'Sandra', 'Diego'][index % 4],
  last_name: ['García', 'Torres', 'Hernández', 'Martínez'][index % 4],
  email: `usuario${index + 1}@edomex.gob.mx`,
  rol: index === 0 ? 'SUPERUSER' : index % 3 === 0 ? 'FARMACIA_ADMIN' : 'CENTRO_USER',
}));

function Usuarios() {
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    cargarUsuarios();
  }, []);

  const cargarUsuarios = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      if ((!token && DEV_CONFIG.ENABLED) || token === 'dev-token') {
        setUsuarios(MOCK_USUARIOS);
        return;
      }

      const response = await usuariosAPI.getAll();
      setUsuarios(response.data.results || response.data);
    } catch (error) {
      if (DEV_CONFIG.ENABLED || localStorage.getItem('token') === 'dev-token') {
        setUsuarios(MOCK_USUARIOS);
      } else {
        toast.error('Error al cargar usuarios');
      }
    } finally {
      setLoading(false);
    }
  };

  const headerActions = (
    <button
      type="button"
      className="flex items-center gap-2 rounded-full bg-white/90 px-4 py-2 text-sm font-bold hover:bg-white"
      style={{ color: COLORS.vino }}
    >
      <FaPlus /> Nuevo Usuario
    </button>
  );

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        icon={FaUsers}
        title="Gestión de Usuarios"
        subtitle={`Total: ${usuarios.length} usuarios registrados`}
        actions={headerActions}
      />

      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Usuario</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nombre</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rol</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {usuarios.map(usuario => (
                <tr key={usuario.id}>
                  <td className="px-6 py-4">{usuario.username}</td>
                  <td className="px-6 py-4">{usuario.first_name} {usuario.last_name}</td>
                  <td className="px-6 py-4">{usuario.email}</td>
                  <td className="px-6 py-4">{usuario.rol}</td>
                  <td className="px-6 py-4 space-x-2">
                    <button className="text-blue-600 hover:text-blue-800"><FaEdit /></button>
                    <button className="text-green-600 hover:text-green-800"><FaKey /></button>
                    <button className="text-red-600 hover:text-red-800"><FaTrash /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default Usuarios;








