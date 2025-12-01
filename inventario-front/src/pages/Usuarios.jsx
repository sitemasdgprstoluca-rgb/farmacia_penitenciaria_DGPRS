import { useState, useEffect, useRef } from 'react';
import { usuariosAPI, centrosAPI } from '../services/api';
import { toast } from 'react-hot-toast';
import { FaPlus, FaEdit, FaTrash, FaKey, FaUsers, FaTimes, FaDownload, FaFileUpload, FaSearch, FaFilter, FaShieldAlt } from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import { COLORS, PRIMARY_GRADIENT } from '../constants/theme';
import { usePermissions } from '../hooks/usePermissions';

const ROLES = [
  { value: 'admin', label: 'Administrador' },
  { value: 'admin_sistema', label: 'Admin Sistema' },
  { value: 'farmacia', label: 'Farmacia' },
  { value: 'centro', label: 'Centro' },
  { value: 'vista', label: 'Consulta' }
];

function Usuarios() {
  const [usuarios, setUsuarios] = useState([]);
  const [filteredUsuarios, setFilteredUsuarios] = useState([]);
  const [centros, setCentros] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [showPermisosAvanzados, setShowPermisosAvanzados] = useState(false);
  const [editingUsuario, setEditingUsuario] = useState(null);
  const fileInputRef = useRef(null);
  const { permisos, getRolPrincipal } = usePermissions();
  
  // Sistema de permisos completo
  const rolPrincipal = getRolPrincipal(); // ADMIN | FARMACIA | CENTRO | VISTA | SIN_ROL
  const esAdmin = rolPrincipal === 'ADMIN';
  const esFarmacia = rolPrincipal === 'FARMACIA';
  const esVista = rolPrincipal === 'VISTA';
  const esSuperusuario = permisos?.isSuperuser;
  
  // Admin, Farmacia y superusuario pueden gestionar usuarios
  const tienePermisoGestion = esAdmin || esFarmacia || esSuperusuario;
  // Vista solo puede ver (sin acciones de modificacin)
  const soloLectura = esVista;
  
  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRol, setFilterRol] = useState('');
  const [filterEstado, setFilterEstado] = useState('');
  
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    adscripcion: '',
    password: '',
    password_confirm: '',
    rol: 'centro',
    centro: '',
    is_active: true,
    // Permisos personalizados (null = usar permisos del rol)
    perm_dashboard: null,
    perm_productos: null,
    perm_lotes: null,
    perm_requisiciones: null,
    perm_centros: null,
    perm_usuarios: null,
    perm_reportes: null,
    perm_trazabilidad: null,
    perm_auditoria: null,
    perm_notificaciones: null,
    perm_movimientos: null,
  });
  
  const [passwordData, setPasswordData] = useState({
    new_password: '',
    confirm_password: ''
  });

  useEffect(() => {
    cargarUsuarios();
    cargarCentros();
  }, []);
  
  // Aplicar filtros cuando cambian
  useEffect(() => {
    let filtered = [...usuarios];
    
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(u => 
        u.username?.toLowerCase().includes(term) ||
        u.email?.toLowerCase().includes(term) ||
        u.first_name?.toLowerCase().includes(term) ||
        u.last_name?.toLowerCase().includes(term)
      );
    }
    
    if (filterRol) {
      filtered = filtered.filter(u => u.rol === filterRol);
    }
    
    if (filterEstado === 'activo') {
      filtered = filtered.filter(u => u.is_active !== false);
    } else if (filterEstado === 'inactivo') {
      filtered = filtered.filter(u => u.is_active === false);
    }
    
    setFilteredUsuarios(filtered);
  }, [usuarios, searchTerm, filterRol, filterEstado]);
  
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
      const data = response.data.results || response.data;
      setUsuarios(data);
      setFilteredUsuarios(data);
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
        adscripcion: usuario.adscripcion || '',
        password: '',
        password_confirm: '',
        rol: usuario.rol || 'centro',
        centro: usuario.centro?.id || '',
        is_active: usuario.is_active !== false,
        // Cargar permisos personalizados existentes
        perm_dashboard: usuario.perm_dashboard,
        perm_productos: usuario.perm_productos,
        perm_lotes: usuario.perm_lotes,
        perm_requisiciones: usuario.perm_requisiciones,
        perm_centros: usuario.perm_centros,
        perm_usuarios: usuario.perm_usuarios,
        perm_reportes: usuario.perm_reportes,
        perm_trazabilidad: usuario.perm_trazabilidad,
        perm_auditoria: usuario.perm_auditoria,
        perm_notificaciones: usuario.perm_notificaciones,
        perm_movimientos: usuario.perm_movimientos,
      });
      // Mostrar permisos avanzados si hay alguno personalizado
      const tienePermisosPersonalizados = [
        usuario.perm_dashboard, usuario.perm_productos, usuario.perm_lotes,
        usuario.perm_requisiciones, usuario.perm_centros, usuario.perm_usuarios,
        usuario.perm_reportes, usuario.perm_trazabilidad, usuario.perm_auditoria,
        usuario.perm_notificaciones, usuario.perm_movimientos
      ].some(p => p !== null && p !== undefined);
      setShowPermisosAvanzados(tienePermisosPersonalizados);
    } else {
      setEditingUsuario(null);
      setFormData({
        username: '',
        email: '',
        first_name: '',
        last_name: '',
        adscripcion: '',
        password: '',
        password_confirm: '',
        rol: 'centro',
        centro: '',
        is_active: true,
        perm_dashboard: null,
        perm_productos: null,
        perm_lotes: null,
        perm_requisiciones: null,
        perm_centros: null,
        perm_usuarios: null,
        perm_reportes: null,
        perm_trazabilidad: null,
        perm_auditoria: null,
        perm_notificaciones: null,
        perm_movimientos: null,
      });
      setShowPermisosAvanzados(false);
    }
    setShowModal(true);
  };
  
  const handleCloseModal = () => {
    setShowModal(false);
    setEditingUsuario(null);
    setShowPermisosAvanzados(false);
    setFormData({
      username: '',
      email: '',
      first_name: '',
      last_name: '',
      adscripcion: '',
      password: '',
      password_confirm: '',
      rol: 'centro',
      centro: '',
      is_active: true,
      perm_dashboard: null,
      perm_productos: null,
      perm_lotes: null,
      perm_requisiciones: null,
      perm_centros: null,
      perm_usuarios: null,
      perm_reportes: null,
      perm_trazabilidad: null,
      perm_auditoria: null,
      perm_notificaciones: null,
      perm_movimientos: null,
    });
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!editingUsuario && formData.password !== formData.password_confirm) {
      toast.error('Las contraseas no coinciden');
      return;
    }
    
    if (!editingUsuario && formData.password.length < 8) {
      toast.error('La contrasea debe tener al menos 8 caracteres');
      return;
    }
    
    try {
      const payload = {
        username: formData.username,
        email: formData.email,
        first_name: formData.first_name,
        last_name: formData.last_name,
        adscripcion: formData.adscripcion,
        rol: formData.rol,
        is_active: formData.is_active
      };
      
      if (formData.centro) {
        payload.centro = formData.centro;
      }
      
      if (!editingUsuario && formData.password) {
        payload.password = formData.password;
      }
      
      // Solo admin puede configurar permisos personalizados
      if (esAdmin || esSuperusuario) {
        payload.perm_dashboard = formData.perm_dashboard;
        payload.perm_productos = formData.perm_productos;
        payload.perm_lotes = formData.perm_lotes;
        payload.perm_requisiciones = formData.perm_requisiciones;
        payload.perm_centros = formData.perm_centros;
        payload.perm_usuarios = formData.perm_usuarios;
        payload.perm_reportes = formData.perm_reportes;
        payload.perm_trazabilidad = formData.perm_trazabilidad;
        payload.perm_auditoria = formData.perm_auditoria;
        payload.perm_notificaciones = formData.perm_notificaciones;
        payload.perm_movimientos = formData.perm_movimientos;
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
    if (!window.confirm(`Eliminar usuario ${usuario.username}?`)) return;
    
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
      toast.error('Las contraseas no coinciden');
      return;
    }
    
    if (passwordData.new_password.length < 8) {
      toast.error('La contrasea debe tener al menos 8 caracteres');
      return;
    }
    
    try {
      await usuariosAPI.changePassword(editingUsuario.id, {
        new_password: passwordData.new_password
      });
      toast.success('Contrasea actualizada');
      setShowPasswordModal(false);
      setPasswordData({ new_password: '', confirm_password: '' });
    } catch (error) {
      toast.error('Error al cambiar contrasea');
    }
  };

  // Exportar usuarios a Excel
  const handleExportar = async () => {
    try {
      setLoading(true);
      const response = await usuariosAPI.exportar();
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `usuarios_${new Date().toISOString().slice(0, 10)}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Usuarios exportados correctamente');
    } catch (error) {
      toast.error('Error al exportar usuarios');
    } finally {
      setLoading(false);
    }
  };

  // Importar usuarios desde Excel
  const handleImportar = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      setLoading(true);
      const response = await usuariosAPI.importar(formData);
      const { creados, errores } = response.data;
      toast.success(`Importacin completada. Usuarios creados: ${creados}`);
      if (errores?.length) {
        console.warn('Errores de importacin:', errores);
        toast.error(`${errores.length} fila(s) con errores`);
      }
      cargarUsuarios();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al importar');
    } finally {
      e.target.value = null;
      setLoading(false);
    }
  };

  // Limpiar filtros
  const limpiarFiltros = () => {
    setSearchTerm('');
    setFilterRol('');
    setFilterEstado('');
  };

  const puede = {
    ver: tienePermisoGestion || soloLectura,
    crear: tienePermisoGestion,
    editar: tienePermisoGestion,
    eliminar: tienePermisoGestion,
    cambiarPassword: tienePermisoGestion,
    exportar: tienePermisoGestion,
    importar: tienePermisoGestion
  };

  const headerActions = (
    <div className="flex flex-wrap gap-2">
      {puede.exportar && (
        <button
          type="button"
          onClick={handleExportar}
          className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
          style={{ background: PRIMARY_GRADIENT, border: '1px solid rgba(255,255,255,0.3)' }}
        >
          <FaDownload /> Exportar
        </button>
      )}
      {puede.importar && (
        <>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
            style={{ background: PRIMARY_GRADIENT, border: '1px solid rgba(255,255,255,0.3)' }}
          >
            <FaFileUpload /> Importar
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls"
            className="hidden"
            onChange={handleImportar}
          />
        </>
      )}
      {puede.crear && (
        <button
          type="button"
          onClick={() => handleOpenModal()}
          className="flex items-center gap-2 rounded-full bg-white/90 px-4 py-2 text-sm font-bold hover:bg-white transition"
          style={{ color: COLORS.vino }}
        >
          <FaPlus /> Nuevo Usuario
        </button>
      )}
    </div>
  );

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <PageHeader
        icon={FaUsers}
        title="Gestin de Usuarios"
        subtitle={`Total: ${filteredUsuarios.length} de ${usuarios.length} usuarios`}
        actions={headerActions}
      />

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="relative">
            <FaSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar usuario, email, nombre..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
              style={{ focusRing: COLORS.vino }}
            />
          </div>
          <div>
            <select
              value={filterRol}
              onChange={(e) => setFilterRol(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            >
              <option value="">Todos los roles</option>
              {ROLES.map(rol => (
                <option key={rol.value} value={rol.value}>{rol.label}</option>
              ))}
            </select>
          </div>
          <div>
            <select
              value={filterEstado}
              onChange={(e) => setFilterEstado(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            >
              <option value="">Todos los estados</option>
              <option value="activo">Activos</option>
              <option value="inactivo">Inactivos</option>
            </select>
          </div>
          <div>
            <button
              type="button"
              onClick={limpiarFiltros}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 font-semibold transition"
            >
              <FaFilter className="inline mr-2" /> Limpiar
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto" style={{ borderColor: COLORS.vino }}></div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead style={{ background: PRIMARY_GRADIENT }}>
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-white uppercase">#</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-white uppercase">Usuario</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-white uppercase">Nombre</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-white uppercase">Email</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-white uppercase">Rol</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-white uppercase">Centro</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-white uppercase">Estado</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-white uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredUsuarios.length === 0 ? (
                <tr>
                  <td colSpan="8" className="px-6 py-12 text-center text-gray-500">
                    {usuarios.length === 0 ? 'No hay usuarios registrados' : 'No se encontraron usuarios con los filtros aplicados'}
                  </td>
                </tr>
              ) : filteredUsuarios.map((usuario, idx) => (
                <tr key={usuario.id} className={`hover:bg-gray-50 ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}>
                  <td className="px-6 py-4 text-sm text-gray-500">{idx + 1}</td>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{usuario.username}</td>
                  <td className="px-6 py-4 text-sm text-gray-700">{usuario.first_name} {usuario.last_name}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{usuario.email}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                      usuario.rol === 'admin' || usuario.rol === 'admin_sistema' ? 'bg-purple-100 text-purple-800' :
                      usuario.rol === 'farmacia' ? 'bg-blue-100 text-blue-800' :
                      usuario.rol === 'centro' ? 'bg-green-100 text-green-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {ROLES.find(r => r.value === usuario.rol)?.label || usuario.rol || 'Sin rol'}
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
                        title="Cambiar contrasea"
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
          <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white px-6 py-4 border-b flex justify-between items-center rounded-t-2xl">
              <h3 className="text-xl font-bold" style={{ color: COLORS.vino }}>
                {editingUsuario ? 'Editar Usuario' : 'Nuevo Usuario'}
              </h3>
              <button onClick={handleCloseModal} className="text-gray-400 hover:text-gray-600">
                <FaTimes size={24} />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
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
                
                <div className="md:col-span-2">
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Adscripción
                  </label>
                  <input
                    type="text"
                    value={formData.adscripcion}
                    onChange={(e) => setFormData({...formData, adscripcion: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Ej: Departamento de Sistemas, Área Médica, etc."
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
                        Contrasea <span className="text-red-500">*</span>
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
                        Confirmar Contrasea <span className="text-red-500">*</span>
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
              
              {/* Seccin de Permisos Avanzados - Solo visible para Admin */}
              {(esAdmin || esSuperusuario) && (
                <div className="border-t pt-4 mt-4">
                  <button
                    type="button"
                    onClick={() => setShowPermisosAvanzados(!showPermisosAvanzados)}
                    className="flex items-center gap-2 text-sm font-semibold mb-3"
                    style={{ color: COLORS.vino }}
                  >
                    <FaShieldAlt />
                    {showPermisosAvanzados ? '' : ''} Configurar Permisos Personalizados
                  </button>
                  
                  {showPermisosAvanzados && (
                    <div className="bg-gray-50 rounded-lg p-5 space-y-4">
                      <p className="text-xs text-gray-600">
                        Configure permisos especficos para este usuario. Dejar en "Por defecto" usa los permisos del rol asignado.
                      </p>
                      
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {[
                          { key: 'perm_dashboard', label: 'Dashboard', icon: '' },
                          { key: 'perm_productos', label: 'Productos', icon: '' },
                          { key: 'perm_lotes', label: 'Lotes', icon: '' },
                          { key: 'perm_requisiciones', label: 'Requisiciones', icon: '' },
                          { key: 'perm_movimientos', label: 'Movimientos', icon: '' },
                          { key: 'perm_centros', label: 'Centros', icon: '' },
                          { key: 'perm_usuarios', label: 'Usuarios', icon: '' },
                          { key: 'perm_reportes', label: 'Reportes', icon: '' },
                          { key: 'perm_trazabilidad', label: 'Trazabilidad', icon: '' },
                          { key: 'perm_auditoria', label: 'Auditora', icon: '' },
                          { key: 'perm_notificaciones', label: 'Notificaciones', icon: '' },
                        ].map(({ key, label, icon }) => (
                          <div key={key} className="flex items-center gap-3 bg-white p-3 rounded-lg border border-gray-200 shadow-sm">
                            <span>{icon}</span>
                            <span className="text-xs font-medium flex-1">{label}</span>
                            <select
                              value={formData[key] === null ? 'default' : formData[key] ? 'true' : 'false'}
                              onChange={(e) => {
                                const val = e.target.value;
                                setFormData({
                                  ...formData,
                                  [key]: val === 'default' ? null : val === 'true'
                                });
                              }}
                              className="text-xs border rounded px-2 py-1 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                              <option value="default">Por defecto</option>
                              <option value="true"> Permitir</option>
                              <option value="false"> Denegar</option>
                            </select>
                          </div>
                        ))}
                      </div>
                      
                      <div className="flex gap-2 mt-3">
                        <button
                          type="button"
                          onClick={() => setFormData({
                            ...formData,
                            perm_dashboard: null, perm_productos: null, perm_lotes: null,
                            perm_requisiciones: null, perm_centros: null, perm_usuarios: null,
                            perm_reportes: null, perm_trazabilidad: null, perm_auditoria: null,
                            perm_notificaciones: null, perm_movimientos: null,
                          })}
                          className="text-xs px-3 py-1 bg-gray-200 hover:bg-gray-300 rounded transition font-semibold"
                        >
                          Restablecer todos
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
              
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
      
      {/* Modal Cambiar Contrasea */}
      {showPasswordModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full">
            <div className="px-6 py-4 border-b flex justify-between items-center">
              <h3 className="text-xl font-bold" style={{ color: COLORS.vino }}>
                Cambiar Contrasea
              </h3>
              <button onClick={() => setShowPasswordModal(false)} className="text-gray-400 hover:text-gray-600">
                <FaTimes size={24} />
              </button>
            </div>
            
            <form onSubmit={handleChangePassword} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">
                  Nueva Contrasea <span className="text-red-500">*</span>
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
                  Confirmar Contrasea <span className="text-red-500">*</span>
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
                  Cambiar Contrasea
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









