import { useState, useEffect } from 'react';
import { usuariosAPI, centrosAPI } from '../services/api';
import { toast } from 'react-hot-toast';
import { FaPlus, FaEdit, FaTrash, FaKey, FaUsers, FaTimes } from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import { COLORS, PRIMARY_GRADIENT } from '../constants/theme';
import { usePermissions } from '../hooks/usePermissions';

const ROLES = [
  { value: 'admin', label: 'Administrador' },
  { value: 'farmacia', label: 'Farmacia' },
  { value: 'centro', label: 'Centro' },
  { value: 'vista', label: 'Consulta' }
];

function Usuarios() {
  const [usuarios, setUsuarios] = useState([]);
  const [centros, setCentros] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [editingUsuario, setEditingUsuario] = useState(null);
  const { permisos } = usePermissions();
  
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    password: '',
    password_confirm: '',
    rol: 'centro',
    centro: '',
    is_active: true
  });
  
  const [passwordData, setPasswordData] = useState({
    new_password: '',
    confirm_password: ''
  });

  useEffect(() => {
    cargarUsuarios();
    cargarCentros();
  }, []);
  
  const cargarCentros = async () => {
    try {
      const response = await centrosAPI.getAll({ activo: true });
      setCentros(response.data.results || response.data);
    } catch (error) {
      console.error('Error al cargar centros');
    }
  };

  const cargarUsuarios = async () => {
    setLoading(true);
    try {
      const response = await usuariosAPI.getAll();
      setUsuarios(response.data.results || response.data);
    } catch (error) {
      toast.error('Error al cargar usuarios');
    } finally {
      setLoading(false);
    }
  };
  
  const handleOpenModal = (usuario = null) => {
    if (usuario) {
      setEditingUsuario(usuario);
      setFormData({
        username: usuario.username,
        email: usuario.email || '',
        first_name: usuario.first_name || '',
        last_name: usuario.last_name || '',
        password: '',
        password_confirm: '',
        rol: usuario.rol || 'centro',
        centro: usuario.centro?.id || '',
        is_active: usuario.is_active !== false
      });
    } else {
      setEditingUsuario(null);
      setFormData({
        username: '',
        email: '',
        first_name: '',
        last_name: '',
        password: '',
        password_confirm: '',
        rol: 'centro',
        centro: '',
        is_active: true
      });
    }
    setShowModal(true);
  };
  
  const handleCloseModal = () => {
    setShowModal(false);
    setEditingUsuario(null);
    setFormData({
      username: '',
      email: '',
      first_name: '',
      last_name: '',
      password: '',
      password_confirm: '',
      rol: 'centro',
      centro: '',
      is_active: true
    });
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!editingUsuario && formData.password !== formData.password_confirm) {
      toast.error('Las contraseñas no coinciden');
      return;
    }
    
    if (!editingUsuario && formData.password.length < 8) {
      toast.error('La contraseña debe tener al menos 8 caracteres');
      return;
    }
    
    try {
      const payload = {
        username: formData.username,
        email: formData.email,
        first_name: formData.first_name,
        last_name: formData.last_name,
        rol: formData.rol,
        is_active: formData.is_active
      };
      
      if (formData.centro) {
        payload.centro = formData.centro;
      }
      
      if (!editingUsuario && formData.password) {
        payload.password = formData.password;
      }
      
      if (editingUsuario) {
        await usuariosAPI.update(editingUsuario.id, payload);
        toast.success('Usuario actualizado correctamente');
      } else {
        await usuariosAPI.create(payload);
        toast.success('Usuario creado correctamente');
      }
      
      handleCloseModal();
      cargarUsuarios();
    } catch (error) {
      const errorMsg = error.response?.data?.error 
        || error.response?.data?.detail 
        || Object.values(error.response?.data || {}).flat().join(', ')
        || 'Error al guardar usuario';
      toast.error(errorMsg);
    }
  };
  
  const handleDelete = async (usuario) => {
    if (!window.confirm(`¿Eliminar usuario ${usuario.username}?`)) return;
    
    try {
      await usuariosAPI.delete(usuario.id);
      toast.success('Usuario eliminado');
      cargarUsuarios();
    } catch (error) {
      toast.error('Error al eliminar usuario');
    }
  };
  
  const handleOpenPasswordModal = (usuario) => {
    setEditingUsuario(usuario);
    setPasswordData({ new_password: '', confirm_password: '' });
    setShowPasswordModal(true);
  };
  
  const handleChangePassword = async (e) => {
    e.preventDefault();
    
    if (passwordData.new_password !== passwordData.confirm_password) {
      toast.error('Las contraseñas no coinciden');
      return;
    }
    
    if (passwordData.new_password.length < 8) {
      toast.error('La contraseña debe tener al menos 8 caracteres');
      return;
    }
    
    try {
      await usuariosAPI.changePassword(editingUsuario.id, {
        new_password: passwordData.new_password
      });
      toast.success('Contraseña actualizada');
      setShowPasswordModal(false);
      setPasswordData({ new_password: '', confirm_password: '' });
    } catch (error) {
      toast.error('Error al cambiar contraseña');
    }
  };

  const puede = {
    crear: permisos.includes('crearUsuarios') || permisos.includes('gestionarUsuarios'),
    editar: permisos.includes('editarUsuarios') || permisos.includes('gestionarUsuarios'),
    eliminar: permisos.includes('eliminarUsuarios') || permisos.includes('gestionarUsuarios'),
    cambiarPassword: permisos.includes('cambiarPasswordUsuarios') || permisos.includes('gestionarUsuarios')
  };

  const headerActions = puede.crear && (
    <button
      type="button"
      onClick={() => handleOpenModal()}
      className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-bold text-white transition hover:opacity-90"
      style={{ background: PRIMARY_GRADIENT }}
    >
      <FaPlus /> Nuevo Usuario
    </button>
  );

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <PageHeader
        icon={FaUsers}
        title="Gestión de Usuarios"
        subtitle={`Total: ${usuarios.length} usuarios registrados`}
        actions={headerActions}
      />

      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto" style={{ borderColor: COLORS.vino }}></div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Usuario</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nombre</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rol</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Centro</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {usuarios.map(usuario => (
                <tr key={usuario.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{usuario.username}</td>
                  <td className="px-6 py-4 text-sm text-gray-700">{usuario.first_name} {usuario.last_name}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{usuario.email}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                      usuario.rol === 'admin' ? 'bg-purple-100 text-purple-800' :
                      usuario.rol === 'farmacia' ? 'bg-blue-100 text-blue-800' :
                      usuario.rol === 'centro' ? 'bg-green-100 text-green-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {usuario.rol === 'admin' ? 'Admin' : usuario.rol === 'farmacia' ? 'Farmacia' : usuario.rol === 'centro' ? 'Centro' : 'Vista'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{usuario.centro?.nombre || '-'}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                      usuario.is_active !== false ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {usuario.is_active !== false ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right space-x-2">
                    {puede.editar && (
                      <button 
                        onClick={() => handleOpenModal(usuario)}
                        className="text-blue-600 hover:text-blue-800 transition"
                        title="Editar"
                      >
                        <FaEdit />
                      </button>
                    )}
                    {puede.cambiarPassword && (
                      <button 
                        onClick={() => handleOpenPasswordModal(usuario)}
                        className="text-green-600 hover:text-green-800 transition"
                        title="Cambiar contraseña"
                      >
                        <FaKey />
                      </button>
                    )}
                    {puede.eliminar && (
                      <button 
                        onClick={() => handleDelete(usuario)}
                        className="text-red-600 hover:text-red-800 transition"
                        title="Eliminar"
                      >
                        <FaTrash />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}
      
      {/* Modal Crear/Editar Usuario */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white px-6 py-4 border-b flex justify-between items-center">
              <h3 className="text-xl font-bold" style={{ color: COLORS.vino }}>
                {editingUsuario ? 'Editar Usuario' : 'Nuevo Usuario'}
              </h3>
              <button onClick={handleCloseModal} className="text-gray-400 hover:text-gray-600">
                <FaTimes size={24} />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Usuario <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.username}
                    onChange={(e) => setFormData({...formData, username: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Email <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Nombre <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.first_name}
                    onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Apellidos <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.last_name}
                    onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Rol <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formData.rol}
                    onChange={(e) => setFormData({...formData, rol: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  >
                    {ROLES.map(rol => (
                      <option key={rol.value} value={rol.value}>{rol.label}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Centro
                  </label>
                  <select
                    value={formData.centro}
                    onChange={(e) => setFormData({...formData, centro: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">Sin asignar</option>
                    {centros.map(centro => (
                      <option key={centro.id} value={centro.id}>{centro.nombre}</option>
                    ))}
                  </select>
                </div>
                
                {!editingUsuario && (
                  <>
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1">
                        Contraseña <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="password"
                        value={formData.password}
                        onChange={(e) => setFormData({...formData, password: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        required
                        minLength={8}
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1">
                        Confirmar Contraseña <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="password"
                        value={formData.password_confirm}
                        onChange={(e) => setFormData({...formData, password_confirm: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        required
                        minLength={8}
                      />
                    </div>
                  </>
                )}
                
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="is_active"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                    className="w-4 h-4 rounded border-gray-300 focus:ring-2 focus:ring-blue-500"
                  />
                  <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
                    Usuario activo
                  </label>
                </div>
              </div>
              
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-semibold transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 text-white rounded-lg font-semibold transition hover:opacity-90"
                  style={{ background: PRIMARY_GRADIENT }}
                >
                  {editingUsuario ? 'Actualizar' : 'Crear'} Usuario
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      
      {/* Modal Cambiar Contraseña */}
      {showPasswordModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full">
            <div className="px-6 py-4 border-b flex justify-between items-center">
              <h3 className="text-xl font-bold" style={{ color: COLORS.vino }}>
                Cambiar Contraseña
              </h3>
              <button onClick={() => setShowPasswordModal(false)} className="text-gray-400 hover:text-gray-600">
                <FaTimes size={24} />
              </button>
            </div>
            
            <form onSubmit={handleChangePassword} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">
                  Nueva Contraseña <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  value={passwordData.new_password}
                  onChange={(e) => setPasswordData({...passwordData, new_password: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                  minLength={8}
                />
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">
                  Confirmar Contraseña <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  value={passwordData.confirm_password}
                  onChange={(e) => setPasswordData({...passwordData, confirm_password: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                  minLength={8}
                />
              </div>
              
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowPasswordModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-semibold transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 text-white rounded-lg font-semibold transition hover:opacity-90"
                  style={{ background: PRIMARY_GRADIENT }}
                >
                  Cambiar Contraseña
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Usuarios;








