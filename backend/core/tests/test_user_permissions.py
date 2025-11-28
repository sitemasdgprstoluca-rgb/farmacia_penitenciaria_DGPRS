"""
Tests para permisos de usuarios y campos perm_*.
Verifica:
- Edición de usuarios con permisos personalizados
- Rutas protegidas por rol
- Flujos clave por rol
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username='admin_test',
        password='Admin1234!',
        email='admin@test.com',
        rol='admin_sistema',
        is_superuser=True,
        is_staff=True
    )


@pytest.fixture
def farmacia_user(db):
    return User.objects.create_user(
        username='farmacia_test',
        password='Farm1234!',
        email='farmacia@test.com',
        rol='farmacia'
    )


@pytest.fixture
def centro_user(db):
    from core.models import Centro, User
    centro = Centro.objects.create(nombre='Centro Test', clave='CT01')
    user = User.objects.create_user(
        username='centro_test',
        password='Centro1234!',
        email='centro@test.com',
        rol='centro',
        centro=centro
    )
    return user


@pytest.fixture
def vista_user(db):
    return User.objects.create_user(
        username='vista_test',
        password='Vista1234!',
        email='vista@test.com',
        rol='vista'
    )


class TestUserPermissionFields:
    """Tests para campos perm_* en usuarios."""
    
    @pytest.mark.django_db
    def test_admin_can_set_perm_fields(self, api_client, admin_user, vista_user):
        """Admin puede establecer permisos personalizados en un usuario."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.patch(
            f'/api/usuarios/{vista_user.id}/',
            {
                'perm_dashboard': False,
                'perm_productos': True,
                'perm_auditoria': True,  # Sobrescribe el False del rol VISTA
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        vista_user.refresh_from_db()
        assert vista_user.perm_dashboard is False
        assert vista_user.perm_productos is True
        assert vista_user.perm_auditoria is True
    
    @pytest.mark.django_db
    def test_permisos_personalizados_override_rol(self, api_client, admin_user, vista_user):
        """Permisos personalizados sobrescriben los del rol."""
        api_client.force_authenticate(user=admin_user)
        
        # VISTA normalmente no tiene verAuditoria
        # Pero si lo asignamos explícitamente, debe tenerlo
        api_client.patch(
            f'/api/usuarios/{vista_user.id}/',
            {'perm_auditoria': True},
            format='json'
        )
        
        # Verificar que el permiso efectivo incluye auditoría
        response = api_client.get(f'/api/usuarios/{vista_user.id}/')
        assert response.status_code == 200
        permisos = response.data.get('permisos', {})
        assert permisos.get('verAuditoria') is True
    
    @pytest.mark.django_db
    def test_perm_null_uses_rol_default(self, api_client, admin_user, vista_user):
        """Si perm_* es null, usa el valor del rol."""
        api_client.force_authenticate(user=admin_user)
        
        # VISTA tiene verDashboard=True por rol
        # Verificamos que sin personalizar, usa el del rol
        response = api_client.get(f'/api/usuarios/{vista_user.id}/')
        assert response.status_code == 200
        permisos = response.data.get('permisos', {})
        assert permisos.get('verDashboard') is True
        
        # VISTA tiene verAuditoria=False por rol
        assert permisos.get('verAuditoria') is False
    
    @pytest.mark.django_db
    def test_farmacia_can_edit_user_perms(self, api_client, farmacia_user, vista_user):
        """Usuario farmacia puede editar permisos de otros usuarios."""
        api_client.force_authenticate(user=farmacia_user)
        
        response = api_client.patch(
            f'/api/usuarios/{vista_user.id}/',
            {'perm_productos': False},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.django_db
    def test_centro_cannot_edit_users(self, api_client, centro_user, vista_user):
        """Usuario centro NO puede editar otros usuarios."""
        api_client.force_authenticate(user=centro_user)
        
        response = api_client.patch(
            f'/api/usuarios/{vista_user.id}/',
            {'perm_productos': False},
            format='json'
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.django_db
    def test_vista_cannot_edit_users(self, api_client, vista_user, farmacia_user):
        """Usuario vista NO puede editar otros usuarios."""
        api_client.force_authenticate(user=vista_user)
        
        response = api_client.patch(
            f'/api/usuarios/{farmacia_user.id}/',
            {'perm_productos': False},
            format='json'
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestProtectedRoutes:
    """Tests para rutas protegidas por rol."""
    
    @pytest.mark.django_db
    def test_admin_can_access_auditoria(self, api_client, admin_user):
        """Admin puede acceder a auditoría."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/auditoria/')
        assert response.status_code in [200, 404]  # 404 si no hay registros aún
    
    @pytest.mark.django_db
    def test_farmacia_cannot_access_auditoria(self, api_client, farmacia_user):
        """Farmacia NO puede acceder a auditoría (solo admin/superuser)."""
        api_client.force_authenticate(user=farmacia_user)
        response = api_client.get('/api/auditoria/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.django_db
    def test_vista_cannot_access_trazabilidad(self, api_client, vista_user):
        """Vista NO puede acceder a trazabilidad (IsFarmaciaRole)."""
        from core.models import Producto
        producto = Producto.objects.create(
            clave='TRAZ001',
            descripcion='Producto Trazabilidad',
            unidad_medida='PIEZA',
            precio_unitario=50
        )
        api_client.force_authenticate(user=vista_user)
        response = api_client.get(f'/api/trazabilidad/producto/{producto.clave}/')
        # Debería ser 403 si está protegido correctamente
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.django_db
    def test_centro_cannot_access_usuarios_list(self, api_client, centro_user):
        """Centro solo puede ver su propio usuario, no el listado completo."""
        api_client.force_authenticate(user=centro_user)
        response = api_client.get('/api/usuarios/')
        # Debería retornar solo el propio usuario
        assert response.status_code == 200
        # El queryset debería filtrar por id
        data = response.data
        if isinstance(data, dict) and 'results' in data:
            users = data['results']
        else:
            users = data
        assert len(users) == 1
        assert users[0]['id'] == centro_user.id
    
    @pytest.mark.django_db
    def test_admin_can_access_all_usuarios(self, api_client, admin_user, farmacia_user, vista_user):
        """Admin puede ver todos los usuarios."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/usuarios/')
        assert response.status_code == 200
        data = response.data
        if isinstance(data, dict) and 'results' in data:
            users = data['results']
        else:
            users = data
        # Debe haber al menos 3 usuarios (admin, farmacia, vista)
        assert len(users) >= 3
    
    @pytest.mark.django_db
    def test_reportes_requires_farmacia_role(self, api_client, centro_user):
        """Reportes requiere rol farmacia."""
        api_client.force_authenticate(user=centro_user)
        response = api_client.get('/api/reportes/inventario/')
        # Centro tiene verReportes=True, pero el endpoint exige IsFarmaciaRole
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestNotificacionesReadOnly:
    """Tests para verificar que notificaciones es read-only."""
    
    @pytest.mark.django_db
    def test_cannot_create_notificacion(self, api_client, admin_user):
        """No se puede crear notificación via API."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post('/api/notificaciones/', {
            'mensaje': 'Test',
            'tipo': 'info'
        }, format='json')
        # ReadOnlyModelViewSet no permite POST
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    
    @pytest.mark.django_db
    def test_cannot_delete_notificacion(self, api_client, admin_user):
        """No se puede eliminar notificación via API."""
        from core.models import Notificacion
        notif = Notificacion.objects.create(
            usuario=admin_user,
            mensaje='Test',
            tipo='info'
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(f'/api/notificaciones/{notif.id}/')
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    
    @pytest.mark.django_db
    def test_can_mark_as_read(self, api_client, admin_user):
        """Sí se puede marcar como leída."""
        from core.models import Notificacion
        notif = Notificacion.objects.create(
            usuario=admin_user,
            mensaje='Test',
            tipo='info',
            leida=False
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(f'/api/notificaciones/{notif.id}/marcar-leida/')
        assert response.status_code == 200
        notif.refresh_from_db()
        assert notif.leida is True


class TestRoleBasedFlows:
    """Tests de flujos clave por rol."""
    
    @pytest.mark.django_db
    def test_centro_can_create_requisicion(self, api_client, centro_user):
        """Centro puede crear requisición."""
        from core.models import Producto
        producto = Producto.objects.create(
            clave='PROD001',
            descripcion='Producto Test',
            unidad_medida='PIEZA',
            precio_unitario=100
        )
        
        api_client.force_authenticate(user=centro_user)
        response = api_client.post('/api/requisiciones/', {
            'detalles': [{'producto': producto.id, 'cantidad_solicitada': 5}]
        }, format='json')
        
        # Centro puede crear requisiciones para su centro
        assert response.status_code in [200, 201]
    
    @pytest.mark.django_db
    def test_centro_cannot_authorize_requisicion(self, api_client, centro_user):
        """Centro NO puede autorizar requisiciones."""
        from core.models import Requisicion
        req = Requisicion.objects.create(
            usuario_solicita=centro_user,
            centro=centro_user.centro,
            estado='enviada'
        )
        
        api_client.force_authenticate(user=centro_user)
        response = api_client.post(f'/api/requisiciones/{req.id}/autorizar/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.django_db
    def test_farmacia_can_authorize_requisicion(self, api_client, farmacia_user, centro_user):
        """Farmacia puede autorizar requisiciones."""
        from core.models import Requisicion, Producto, DetalleRequisicion, Lote
        from datetime import date, timedelta
        
        producto = Producto.objects.create(
            clave='PROD002',
            descripcion='Producto Test 2',
            unidad_medida='PIEZA',
            precio_unitario=100
        )
        # Crear lote con stock
        Lote.objects.create(
            producto=producto,
            numero_lote='L001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100
        )
        
        req = Requisicion.objects.create(
            usuario_solicita=centro_user,
            centro=centro_user.centro,
            estado='enviada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=producto,
            cantidad_solicitada=5
        )
        
        api_client.force_authenticate(user=farmacia_user)
        response = api_client.post(f'/api/requisiciones/{req.id}/autorizar/')
        
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_vista_can_view_but_not_modify_productos(self, api_client, vista_user):
        """Vista puede ver productos pero no modificarlos."""
        from core.models import Producto
        producto = Producto.objects.create(
            clave='PROD003',
            descripcion='Producto Test 3',
            unidad_medida='PIEZA',
            precio_unitario=50
        )
        
        api_client.force_authenticate(user=vista_user)
        
        # Puede ver
        response = api_client.get(f'/api/productos/{producto.id}/')
        assert response.status_code == 200
        
        # No puede modificar
        response = api_client.patch(f'/api/productos/{producto.id}/', {
            'descripcion': 'Modificado'
        }, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.django_db
    def test_movimientos_is_readonly(self, api_client, admin_user):
        """Movimientos es readonly (no update/destroy)."""
        from core.models import Movimiento, Producto, Lote
        from datetime import date, timedelta
        
        producto = Producto.objects.create(
            clave='PROD004',
            descripcion='Producto Mov',
            unidad_medida='PIEZA',
            precio_unitario=100
        )
        lote = Lote.objects.create(
            producto=producto,
            numero_lote='LMOV01',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=90  # Menor que inicial para evitar ValidationError
        )
        
        mov = Movimiento.objects.create(
            lote=lote,
            tipo='entrada',
            cantidad=10,
            usuario=admin_user
        )
        
        api_client.force_authenticate(user=admin_user)
        
        # No puede actualizar (403 o 405 son aceptables - readonly o sin permiso)
        response = api_client.patch(f'/api/movimientos/{mov.id}/', {
            'cantidad': 20
        }, format='json')
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED]
        
        # No puede eliminar
        response = api_client.delete(f'/api/movimientos/{mov.id}/')
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED]


class TestPermissionPayload:
    """Tests para verificar el payload de permisos en respuestas."""
    
    @pytest.mark.django_db
    def test_user_me_includes_permisos(self, api_client, farmacia_user):
        """GET /api/usuarios/me/ incluye permisos calculados."""
        api_client.force_authenticate(user=farmacia_user)
        response = api_client.get('/api/usuarios/me/')
        
        assert response.status_code == 200
        assert 'permisos' in response.data
        permisos = response.data['permisos']
        
        # FARMACIA tiene permisos operativos
        assert permisos.get('verDashboard') is True
        assert permisos.get('verProductos') is True
        # Pero NO tiene acceso a auditoría (solo admin/superuser)
        assert permisos.get('verAuditoria') is False
    
    @pytest.mark.django_db
    def test_vista_user_permisos_restringidos(self, api_client, vista_user):
        """VISTA tiene permisos restringidos en trazabilidad/auditoria."""
        api_client.force_authenticate(user=vista_user)
        response = api_client.get('/api/usuarios/me/')
        
        assert response.status_code == 200
        permisos = response.data['permisos']
        
        # VISTA NO tiene acceso a trazabilidad ni auditoría
        assert permisos.get('verTrazabilidad') is False
        assert permisos.get('verAuditoria') is False
        # Pero sí a dashboard
        assert permisos.get('verDashboard') is True
    
    @pytest.mark.django_db
    def test_custom_perm_reflected_in_payload(self, api_client, admin_user, vista_user):
        """Permisos personalizados se reflejan en el payload."""
        api_client.force_authenticate(user=admin_user)
        
        # Dar acceso a auditoría a vista_user
        response = api_client.patch(f'/api/usuarios/{vista_user.id}/', {
            'perm_auditoria': True
        }, format='json')
        assert response.status_code == 200
        
        # Verificar que el perm se guardó
        vista_user.refresh_from_db()
        assert vista_user.perm_auditoria is True
        
        # Verificar desde me endpoint
        api_client.force_authenticate(user=vista_user)
        response = api_client.get('/api/usuarios/me/')
        
        permisos = response.data['permisos']
        assert permisos.get('verAuditoria') is True  # Personalizado
        assert permisos.get('verTrazabilidad') is False  # Sigue siendo del rol
