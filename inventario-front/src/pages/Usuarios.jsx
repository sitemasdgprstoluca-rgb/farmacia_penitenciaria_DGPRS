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

// Constantes de validación de contraseña
const PASSWORD_MIN_LENGTH = 8;
const PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;
const PASSWORD_REQUIREMENTS = 'Mínimo 8 caracteres, 1 mayúscula, 1 minúscula y 1 número';

// Jerarquía de roles (menor número = mayor jerarquía)
const ROL_JERARQUIA = {
  'admin_sistema': 1,
  'admin': 2,
  'farmacia': 3,
  'centro': 4,
  'vista': 5
};

// Extensiones y tamaño máximo para importación
const IMPORT_ALLOWED_EXTENSIONS = ['.xlsx', '.xls'];
const IMPORT_MAX_FILE_SIZE_MB = 10;

function Usuarios() {
  const [usuarios, setUsuarios] = useState([]);
  const [filteredUsuarios, setFilteredUsuarios] = useState([]);
  const [centros, setCentros] = useState([]);
  const [loading, setLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(null); // ID del usuario en acción
  const [showModal, setShowModal] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [showPermisosAvanzados, setShowPermisosAvanzados] = useState(false);
  const [editingUsuario, setEditingUsuario] = useState(null);
  const fileInputRef = useRef(null);
  const { user, permisos, getRolPrincipal } = usePermissions();
  
  // ID del usuario actual (desde el contexto, ya cargado)
  const currentUserId = user?.id;
  
  // Sistema de permisos completo
  const rolPrincipal = getRolPrincipal(); // ADMIN | FARMACIA | CENTRO | VISTA | SIN_ROL
  const esAdmin = rolPrincipal === 'ADMIN';
  const esFarmacia = rolPrincipal === 'FARMACIA';
  const esVista = rolPrincipal === 'VISTA';
  const esSuperusuario = permisos?.isSuperuser;
  const esAdminOFarmacia = esAdmin || esFarmacia || esSuperusuario;
  
  // Admin, Farmacia y superusuario pueden gestionar usuarios
  const tienePermisoGestion = esAdmin || esFarmacia || esSuperusuario;
  // Vista solo puede ver (sin acciones de modificacin)
  const soloLectura = esVista;
  
  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRol, setFilterRol] = useState('');
  const [filterEstado, setFilterEstado] = useState('');
  const [filterCentro, setFilterCentro] = useState('');
  
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

  // Construir los parámetros de filtro para enviar al backend
  const buildFilterParams = () => {
    const params = {};
    
    // Si no es admin/farmacia, siempre filtrar por centro del usuario
    if (!esAdminOFarmacia && user?.centro?.id) {
      params.centro = user.centro.id;
    } else if (filterCentro) {
      // Admin/farmacia pueden filtrar por cualquier centro
      params.centro = filterCentro;
    }
    
    if (searchTerm.trim()) {
      params.search = searchTerm.trim();
    }
    
    if (filterRol) {
      params.rol = filterRol;
    }
    
    if (filterEstado === 'activo') {
      params.is_active = 'true';
    } else if (filterEstado === 'inactivo') {
      params.is_active = 'false';
    }
    
    return params;
  };

  // Ref para debounce
  const debounceRef = useRef(null);
  
  // Cargar usuarios con filtros server-side
  const cargarUsuarios = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      const params = buildFilterParams();
      const response = await usuariosAPI.getAll(params);
      const data = response.data.results || response.data;
      setUsuarios(data);
      setFilteredUsuarios(data);
    } catch (error) {
      toast.error('Error al cargar usuarios');
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  useEffect(() => {
    cargarCentros();
  }, []);

  // Cargar usuarios cuando los filtros cambian (con debounce para búsqueda)
  useEffect(() => {
    // Si es la primera carga o cambió algo que no sea searchTerm, cargar inmediatamente
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    
    // Debounce solo para searchTerm (300ms), el resto es inmediato
    const delay = searchTerm ? 300 : 0;
    
    debounceRef.current = setTimeout(() => {
      cargarUsuarios();
    }, delay);
    
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [searchTerm, filterRol, filterEstado, filterCentro, esAdminOFarmacia, user?.centro?.id]);
  
  const cargarCentros = async () => {
    try {
      const response = await centrosAPI.getAll({ activo: true });
      setCentros(response.data.results || response.data);
    } catch (error) {
      console.error('Error al cargar centros');
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
  
  // Validar si el rol actual puede asignar el rol objetivo
  const puedeAsignarRol = (rolObjetivo) => {
    const miJerarquia = ROL_JERARQUIA[rolPrincipal?.toLowerCase()] || 99;
    const objetivoJerarquia = ROL_JERARQUIA[rolObjetivo] || 99;
    // Solo puede asignar roles de igual o menor jerarquía
    return miJerarquia <= objetivoJerarquia || esSuperusuario;
  };

  // Validar si el usuario actual puede modificar/eliminar a otro usuario
  // Retorna true si el usuario objetivo tiene igual o menor jerarquía
  const puedeModificarUsuario = (usuario) => {
    if (esSuperusuario) return true;
    if (!tienePermisoGestion) return false;
    const miJerarquia = ROL_JERARQUIA[rolPrincipal?.toLowerCase()] || 99;
    const usuarioJerarquia = ROL_JERARQUIA[usuario.rol] || 99;
    return miJerarquia <= usuarioJerarquia;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validar contraseña para nuevos usuarios
    if (!editingUsuario) {
      if (formData.password !== formData.password_confirm) {
        toast.error('Las contraseñas no coinciden');
        return;
      }
      
      if (formData.password.length < PASSWORD_MIN_LENGTH) {
        toast.error(`La contraseña debe tener al menos ${PASSWORD_MIN_LENGTH} caracteres`);
        return;
      }

      if (!PASSWORD_REGEX.test(formData.password)) {
        toast.error(PASSWORD_REQUIREMENTS);
        return;
      }
    }

    // Validar escalamiento de privilegios
    if (editingUsuario) {
      const rolAnterior = editingUsuario.rol;
      const rolNuevo = formData.rol;
      const jerarquiaAnterior = ROL_JERARQUIA[rolAnterior] || 99;
      const jerarquiaNueva = ROL_JERARQUIA[rolNuevo] || 99;
      
      // Si está elevando privilegios, confirmar
      if (jerarquiaNueva < jerarquiaAnterior) {
        if (!puedeAsignarRol(rolNuevo)) {
          toast.error('No tiene permisos para asignar ese rol');
          return;
        }
        const confirmElevacion = window.confirm(
          `⚠️ ADVERTENCIA DE SEGURIDAD\n\n` +
          `Está elevando los privilegios de "${editingUsuario.username}":\n` +
          `• Rol anterior: ${ROLES.find(r => r.value === rolAnterior)?.label || rolAnterior}\n` +
          `• Rol nuevo: ${ROLES.find(r => r.value === rolNuevo)?.label || rolNuevo}\n\n` +
          `¿Confirma este cambio de privilegios?`
        );
        if (!confirmElevacion) return;
      }
    } else {
      // Validar que puede crear usuario con ese rol
      if (!puedeAsignarRol(formData.rol)) {
        toast.error('No tiene permisos para crear usuarios con ese rol');
        return;
      }
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
      
      // Admin y Farmacia pueden configurar permisos personalizados
      if (esAdmin || esFarmacia || esSuperusuario) {
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
    // Prevenir auto-eliminación (validación robusta)
    if (!currentUserId) {
      toast.error('Espere a que se cargue la sesión antes de eliminar usuarios');
      return;
    }
    if (usuario.id === currentUserId) {
      toast.error('No puede eliminarse a sí mismo. Contacte a otro administrador.');
      return;
    }

    // Prevenir eliminar usuarios de mayor jerarquía
    const miJerarquia = ROL_JERARQUIA[rolPrincipal?.toLowerCase()] || 99;
    const usuarioJerarquia = ROL_JERARQUIA[usuario.rol] || 99;
    if (usuarioJerarquia < miJerarquia && !esSuperusuario) {
      toast.error('No puede eliminar usuarios con rol superior al suyo');
      return;
    }

    const mensaje = `⚠️ ELIMINAR USUARIO\n\n` +
      `Usuario: ${usuario.username}\n` +
      `Nombre: ${usuario.first_name} ${usuario.last_name}\n` +
      `Rol: ${ROLES.find(r => r.value === usuario.rol)?.label || usuario.rol}\n\n` +
      `Esta acción no se puede deshacer. ¿Confirma la eliminación?`;
    
    if (!window.confirm(mensaje)) return;
    
    setActionLoading(usuario.id);
    try {
      await usuariosAPI.delete(usuario.id);
      toast.success('Usuario eliminado correctamente');
      cargarUsuarios();
    } catch (error) {
      const errorMsg = error.response?.data?.error ||
                       error.response?.data?.detail ||
                       'Error al eliminar usuario';
      toast.error(errorMsg);
    } finally {
      setActionLoading(null);
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
    
    if (passwordData.new_password.length < PASSWORD_MIN_LENGTH) {
      toast.error(`La contraseña debe tener al menos ${PASSWORD_MIN_LENGTH} caracteres`);
      return;
    }

    if (!PASSWORD_REGEX.test(passwordData.new_password)) {
      toast.error(PASSWORD_REQUIREMENTS);
      return;
    }
    
    setActionLoading(editingUsuario.id);
    try {
      await usuariosAPI.cambiarPassword(editingUsuario.id, {
        new_password: passwordData.new_password
      });
      toast.success('Contraseña actualizada correctamente');
      setShowPasswordModal(false);
      setPasswordData({ new_password: '', confirm_password: '' });
    } catch (error) {
      const errorMsg = error.response?.data?.error ||
                       error.response?.data?.detail ||
                       'Error al cambiar contraseña';
      toast.error(errorMsg);
    } finally {
      setActionLoading(null);
    }
  };

  // Exportar usuarios a Excel (con los mismos filtros que la vista)
  const handleExportar = async () => {
    if (exportLoading) return; // Prevenir doble clic
    
    try {
      setExportLoading(true);
      // Usar los mismos filtros que el listado para coherencia
      const params = buildFilterParams();
      const response = await usuariosAPI.exportar(params);
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `usuarios_${new Date().toISOString().slice(0, 10)}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Usuarios exportados correctamente');
    } catch (error) {
      toast.error('Error al exportar usuarios');
    } finally {
      setExportLoading(false);
    }
  };

  // Importar usuarios desde Excel
  const handleImportar = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validar extensión localmente
    const extension = '.' + file.name.split('.').pop().toLowerCase();
    if (!IMPORT_ALLOWED_EXTENSIONS.includes(extension)) {
      toast.error(`Extensión no permitida: ${extension}. Use: ${IMPORT_ALLOWED_EXTENSIONS.join(', ')}`);
      e.target.value = null;
      return;
    }

    // Validar tamaño localmente
    const sizeMB = file.size / (1024 * 1024);
    if (sizeMB > IMPORT_MAX_FILE_SIZE_MB) {
      toast.error(`Archivo demasiado grande: ${sizeMB.toFixed(1)}MB. Máximo: ${IMPORT_MAX_FILE_SIZE_MB}MB`);
      e.target.value = null;
      return;
    }

    const formDataFile = new FormData();
    formDataFile.append('file', file);

    try {
      setImportLoading(true);
      const response = await usuariosAPI.importar(formDataFile);
      const { creados, actualizados, errores } = response.data;
      toast.success(`Importación completada: ${creados || 0} creados, ${actualizados || 0} actualizados`);
      
      if (errores?.length) {
        console.warn('Errores de importación:', errores);
        // Mostrar hasta 5 errores en toasts
        errores.slice(0, 5).forEach((err, idx) => {
          const fila = err.fila || idx + 1;
          const msg = err.error || err.mensaje || JSON.stringify(err);
          toast.error(`Fila ${fila}: ${msg}`, { duration: 5000 });
        });
        if (errores.length > 5) {
          toast.error(`... y ${errores.length - 5} errores más. Revise la consola.`, { duration: 5000 });
        }
      }
      cargarUsuarios();
    } catch (error) {
      const errorMsg = error.response?.data?.error ||
                       error.response?.data?.detail ||
                       'Error al importar usuarios';
      toast.error(errorMsg);
    } finally {
      e.target.value = null;
      setImportLoading(false);
    }
  };

  // Limpiar filtros
  const limpiarFiltros = () => {
    setSearchTerm('');
    setFilterRol('');
    setFilterEstado('');
    setFilterCentro('');
  };

  // Cruzar tienePermisoGestion con permisos del backend para respetar permisos personalizados
  // Un usuario puede tener rol farmacia pero permisos limitados por el admin
  const tieneGestionBackend = permisos?.gestionUsuarios !== false;
  const puedeGestionar = tienePermisoGestion && tieneGestionBackend;

  const puede = {
    ver: puedeGestionar || soloLectura,
    crear: puedeGestionar,
    editar: puedeGestionar,
    eliminar: puedeGestionar,
    cambiarPassword: puedeGestionar,
    exportar: puedeGestionar,
    importar: puedeGestionar
  };

  const headerActions = (
    <div className="flex flex-wrap gap-2">
      {puede.exportar && (
        <button
          type="button"
          onClick={handleExportar}
          disabled={exportLoading || importLoading}
          className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
          style={{ background: PRIMARY_GRADIENT, border: '1px solid rgba(255,255,255,0.3)' }}
        >
          <FaDownload /> {exportLoading ? 'Exportando...' : 'Exportar'}
        </button>
      )}
      {puede.importar && (
        <>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={exportLoading || importLoading}
            className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: PRIMARY_GRADIENT, border: '1px solid rgba(255,255,255,0.3)' }}
          >
            <FaFileUpload /> {importLoading ? 'Importando...' : 'Importar'}
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
          disabled={exportLoading || importLoading}
          className="flex items-center gap-2 rounded-full bg-white/90 px-4 py-2 text-sm font-bold hover:bg-white transition disabled:opacity-50 disabled:cursor-not-allowed"
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
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
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
              value={esAdminOFarmacia ? filterCentro : (user?.centro?.id?.toString() || '')}
              onChange={(e) => esAdminOFarmacia && setFilterCentro(e.target.value)}
              disabled={!esAdminOFarmacia}
              className={`w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent ${
                !esAdminOFarmacia ? 'bg-gray-100 cursor-not-allowed' : ''
              }`}
              title={!esAdminOFarmacia ? 'Solo puedes ver usuarios de tu centro' : ''}
            >
              {esAdminOFarmacia ? (
                <>
                  <option value="">Todos los centros</option>
                  {centros.map(centro => (
                    <option key={centro.id} value={centro.id}>{centro.nombre}</option>
                  ))}
                </>
              ) : (
                <option value={user?.centro?.id || ''}>
                  {centros.find(c => c.id === user?.centro?.id)?.nombre || 'Tu centro'}
                </option>
              )}
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
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-t-transparent mx-auto" style={{ borderColor: '#9F224133', borderTopColor: '#9F2241' }}></div>
          <p className="mt-3 text-gray-600">Cargando usuarios...</p>
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
                    {/* Solo mostrar botones si el usuario actual puede modificar a este usuario */}
                    {puedeModificarUsuario(usuario) ? (
                      <>
                        {puede.editar && (
                          <button 
                            onClick={() => handleOpenModal(usuario)}
                            disabled={actionLoading === usuario.id}
                            className="text-blue-600 hover:text-blue-800 transition disabled:opacity-50"
                            title="Editar"
                          >
                            <FaEdit />
                          </button>
                        )}
                        {puede.cambiarPassword && (
                          <button 
                            onClick={() => handleOpenPasswordModal(usuario)}
                            disabled={actionLoading === usuario.id}
                            className="text-green-600 hover:text-green-800 transition disabled:opacity-50"
                            title="Cambiar contraseña"
                          >
                            <FaKey />
                          </button>
                        )}
                        {puede.eliminar && usuario.id !== currentUserId && (
                          <button 
                            onClick={() => handleDelete(usuario)}
                            disabled={actionLoading === usuario.id || !currentUserId}
                            className="text-red-600 hover:text-red-800 transition disabled:opacity-50"
                            title={!currentUserId ? "Cargando sesión..." : "Eliminar"}
                          >
                            {actionLoading === usuario.id ? (
                              <span className="animate-spin inline-block">⏳</span>
                            ) : (
                              <FaTrash />
                            )}
                          </button>
                        )}
                        {usuario.id === currentUserId && (
                          <span className="text-gray-400 text-xs italic" title="No puede eliminarse a sí mismo">
                            (Tú)
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="text-gray-400 text-xs italic" title="Usuario con mayor privilegio">
                        🔒 Protegido
                      </span>
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
                    {ROLES.map(rol => {
                      const disabled = !puedeAsignarRol(rol.value);
                      return (
                        <option 
                          key={rol.value} 
                          value={rol.value}
                          disabled={disabled}
                        >
                          {rol.label}{disabled ? ' (sin permiso)' : ''}
                        </option>
                      );
                    })}
                  </select>
                  {editingUsuario && formData.rol !== editingUsuario.rol && (
                    <p className="text-xs text-amber-600 mt-1">
                      ⚠️ Cambiar el rol afectará los permisos del usuario
                    </p>
                  )}
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
                        className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                          formData.password && !PASSWORD_REGEX.test(formData.password) 
                            ? 'border-amber-400' 
                            : 'border-gray-300'
                        }`}
                        required
                        minLength={8}
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        {PASSWORD_REQUIREMENTS}
                      </p>
                      {formData.password && (
                        <div className="text-xs mt-1 space-y-0.5">
                          <p className={formData.password.length >= 8 ? 'text-green-600' : 'text-red-500'}>
                            {formData.password.length >= 8 ? '✓' : '✗'} Mínimo 8 caracteres
                          </p>
                          <p className={/[A-Z]/.test(formData.password) ? 'text-green-600' : 'text-red-500'}>
                            {/[A-Z]/.test(formData.password) ? '✓' : '✗'} Al menos 1 mayúscula
                          </p>
                          <p className={/[a-z]/.test(formData.password) ? 'text-green-600' : 'text-red-500'}>
                            {/[a-z]/.test(formData.password) ? '✓' : '✗'} Al menos 1 minúscula
                          </p>
                          <p className={/\d/.test(formData.password) ? 'text-green-600' : 'text-red-500'}>
                            {/\d/.test(formData.password) ? '✓' : '✗'} Al menos 1 número
                          </p>
                        </div>
                      )}
                    </div>
                    
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1">
                        Confirmar Contraseña <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="password"
                        value={formData.password_confirm}
                        onChange={(e) => setFormData({...formData, password_confirm: e.target.value})}
                        className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                          formData.password_confirm && formData.password !== formData.password_confirm 
                            ? 'border-red-400' 
                            : 'border-gray-300'
                        }`}
                        required
                        minLength={8}
                      />
                      {formData.password_confirm && formData.password !== formData.password_confirm && (
                        <p className="text-xs text-red-500 mt-1">Las contraseñas no coinciden</p>
                      )}
                      {formData.password_confirm && formData.password === formData.password_confirm && (
                        <p className="text-xs text-green-600 mt-1">✓ Las contraseñas coinciden</p>
                      )}
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
              
              {/* Seccin de Permisos Avanzados - Visible para Admin y Farmacia */}
              {(esAdmin || esFarmacia || esSuperusuario) && (
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
                        Configure permisos especficos para este usuario. Dejar en &quot;Por defecto&quot; usa los permisos del rol asignado.
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
            
            <div className="px-6 py-2 bg-gray-50 border-b">
              <p className="text-sm text-gray-600">
                Usuario: <span className="font-semibold">{editingUsuario?.username}</span>
              </p>
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
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    passwordData.new_password && !PASSWORD_REGEX.test(passwordData.new_password) 
                      ? 'border-amber-400' 
                      : 'border-gray-300'
                  }`}
                  required
                  minLength={8}
                />
                <p className="text-xs text-gray-500 mt-1">{PASSWORD_REQUIREMENTS}</p>
                {passwordData.new_password && (
                  <div className="text-xs mt-1 space-y-0.5">
                    <p className={passwordData.new_password.length >= 8 ? 'text-green-600' : 'text-red-500'}>
                      {passwordData.new_password.length >= 8 ? '✓' : '✗'} Mínimo 8 caracteres
                    </p>
                    <p className={/[A-Z]/.test(passwordData.new_password) ? 'text-green-600' : 'text-red-500'}>
                      {/[A-Z]/.test(passwordData.new_password) ? '✓' : '✗'} Al menos 1 mayúscula
                    </p>
                    <p className={/[a-z]/.test(passwordData.new_password) ? 'text-green-600' : 'text-red-500'}>
                      {/[a-z]/.test(passwordData.new_password) ? '✓' : '✗'} Al menos 1 minúscula
                    </p>
                    <p className={/\d/.test(passwordData.new_password) ? 'text-green-600' : 'text-red-500'}>
                      {/\d/.test(passwordData.new_password) ? '✓' : '✗'} Al menos 1 número
                    </p>
                  </div>
                )}
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">
                  Confirmar Contraseña <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  value={passwordData.confirm_password}
                  onChange={(e) => setPasswordData({...passwordData, confirm_password: e.target.value})}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    passwordData.confirm_password && passwordData.new_password !== passwordData.confirm_password 
                      ? 'border-red-400' 
                      : 'border-gray-300'
                  }`}
                  required
                  minLength={8}
                />
                {passwordData.confirm_password && passwordData.new_password !== passwordData.confirm_password && (
                  <p className="text-xs text-red-500 mt-1">Las contraseñas no coinciden</p>
                )}
                {passwordData.confirm_password && passwordData.new_password === passwordData.confirm_password && (
                  <p className="text-xs text-green-600 mt-1">✓ Las contraseñas coinciden</p>
                )}
              </div>
              
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowPasswordModal(false)}
                  disabled={actionLoading}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-semibold transition disabled:opacity-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={actionLoading || !PASSWORD_REGEX.test(passwordData.new_password) || passwordData.new_password !== passwordData.confirm_password}
                  className="flex-1 px-4 py-2 text-white rounded-lg font-semibold transition hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ background: PRIMARY_GRADIENT }}
                >
                  {actionLoading ? 'Cambiando...' : 'Cambiar Contraseña'}
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







