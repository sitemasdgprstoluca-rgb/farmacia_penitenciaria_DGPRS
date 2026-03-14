"""
Test: Documento de Hoja de Entrega en Donaciones.
Valida modelo, serializer y endpoints.
"""
import pytest
from django.test import RequestFactory
from rest_framework.test import force_authenticate
from core.views import DonacionViewSet
from core.models import User, Donacion, Centro
from core.serializers import DonacionSerializer
from django.utils import timezone
from io import BytesIO


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username='test_admin_doc', password='testpass123', email='admin_doc@test.com'
    )


@pytest.fixture
def centro(db):
    return Centro.objects.create(nombre='Centro Test Doc')


@pytest.fixture
def donacion(db, admin_user, centro):
    return Donacion.objects.create(
        numero='DON-TEST-DOC-001',
        donante_nombre='Donante Test',
        donante_tipo='empresa',
        fecha_donacion=timezone.now().date(),
        centro_destino=centro,
        recibido_por=admin_user,
        estado='pendiente',
    )


# =====================================================================
# 1. MODELO - Campos de documento de entrega existen
# =====================================================================

class TestModeloCamposDocumento:

    def test_campo_documento_entrega_url(self):
        assert hasattr(Donacion, 'documento_entrega_url')

    def test_campo_documento_entrega_nombre(self):
        assert hasattr(Donacion, 'documento_entrega_nombre')

    def test_campo_documento_entrega_fecha(self):
        assert hasattr(Donacion, 'documento_entrega_fecha')

    def test_campo_documento_entrega_por(self):
        assert hasattr(Donacion, 'documento_entrega_por')

    def test_campo_documento_entrega_tamano(self):
        assert hasattr(Donacion, 'documento_entrega_tamano')

    def test_fk_db_column(self):
        field = Donacion._meta.get_field('documento_entrega_por')
        assert field.column == 'documento_entrega_por_id'


# =====================================================================
# 2. SERIALIZER - Campos incluidos y read_only
# =====================================================================

class TestSerializerCampos:

    def test_fields_incluidos(self):
        campos = DonacionSerializer.Meta.fields
        esperados = [
            'documento_entrega_url', 'documento_entrega_nombre',
            'documento_entrega_fecha', 'documento_entrega_por',
            'documento_entrega_por_nombre', 'documento_entrega_tamano',
            'tiene_documento_entrega',
        ]
        for f in esperados:
            assert f in campos, f'{f} no esta en fields'

    def test_read_only_fields(self):
        ro = DonacionSerializer.Meta.read_only_fields
        esperados = [
            'documento_entrega_url', 'documento_entrega_nombre',
            'documento_entrega_fecha', 'documento_entrega_por',
            'documento_entrega_tamano',
        ]
        for f in esperados:
            assert f in ro, f'{f} no esta en read_only_fields'

    def test_method_fields_existen(self):
        assert hasattr(DonacionSerializer, 'get_documento_entrega_por_nombre')
        assert hasattr(DonacionSerializer, 'get_tiene_documento_entrega')

    @pytest.mark.django_db
    def test_serializa_donacion_sin_documento(self, donacion):
        data = DonacionSerializer(donacion).data
        assert 'tiene_documento_entrega' in data
        assert data['tiene_documento_entrega'] is False
        assert data['documento_entrega_url'] is None
        assert data['documento_entrega_por_nombre'] is None


# =====================================================================
# 3. VIEWSET - Acciones de documento registradas
# =====================================================================

class TestViewSetAcciones:

    def test_action_subir_existe(self):
        assert hasattr(DonacionViewSet, 'subir_documento_entrega')

    def test_action_descargar_existe(self):
        assert hasattr(DonacionViewSet, 'descargar_documento_entrega')

    def test_action_eliminar_existe(self):
        assert hasattr(DonacionViewSet, 'eliminar_documento_entrega')


# =====================================================================
# 4. ENDPOINTS - Validaciones de errores
# =====================================================================

@pytest.mark.django_db
class TestEndpointsValidacion:

    def test_subir_sin_archivo_400(self, admin_user, donacion):
        factory = RequestFactory()
        request = factory.post(
            f'/api/donaciones/{donacion.id}/subir-documento-entrega/',
            data={}, format='multipart'
        )
        force_authenticate(request, user=admin_user)
        view = DonacionViewSet.as_view({'post': 'subir_documento_entrega'})
        response = view(request, pk=donacion.id)
        assert response.status_code == 400

    def test_subir_archivo_no_pdf_400(self, admin_user, donacion):
        factory = RequestFactory()
        fake_txt = BytesIO(b'no es un PDF')
        fake_txt.name = 'test.txt'
        request = factory.post(
            f'/api/donaciones/{donacion.id}/subir-documento-entrega/',
            data={'archivo': fake_txt}, format='multipart'
        )
        force_authenticate(request, user=admin_user)
        view = DonacionViewSet.as_view({'post': 'subir_documento_entrega'})
        response = view(request, pk=donacion.id)
        assert response.status_code == 400

    def test_descargar_sin_documento_404(self, admin_user, donacion):
        factory = RequestFactory()
        request = factory.get(
            f'/api/donaciones/{donacion.id}/descargar-documento-entrega/'
        )
        force_authenticate(request, user=admin_user)
        view = DonacionViewSet.as_view({'get': 'descargar_documento_entrega'})
        response = view(request, pk=donacion.id)
        assert response.status_code == 404

    def test_eliminar_sin_documento_404(self, admin_user, donacion):
        factory = RequestFactory()
        request = factory.delete(
            f'/api/donaciones/{donacion.id}/eliminar-documento-entrega/'
        )
        force_authenticate(request, user=admin_user)
        view = DonacionViewSet.as_view({'delete': 'eliminar_documento_entrega'})
        response = view(request, pk=donacion.id)
        assert response.status_code == 404
