"""
Tests para validar las correcciones de auditoría ISS-001, ISS-002, ISS-003.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from datetime import date, timedelta
from decimal import Decimal
import logging

from core.models import Producto, Lote, Centro
from core.password_reset import send_password_reset_email

User = get_user_model()


@pytest.fixture
def centro(db):
    """Fixture para crear un centro de prueba."""
    return Centro.objects.create(
        nombre="Centro Test",
        clave="CT001",  # Usar 'clave' en lugar de 'codigo'
        direccion="Dirección Test"
    )


@pytest.fixture
def producto(db):
    """Fixture para crear un producto de prueba."""
    return Producto.objects.create(
        clave="PROD001",
        descripcion="Producto de prueba para tests",
        unidad_medida="PIEZA",  # Usar unidad válida según constants.py
        precio_unitario=Decimal("10.00"),
        stock_minimo=10
    )


@pytest.fixture
def lote_farmacia(db, producto):
    """Fixture para crear un lote en farmacia central (sin centro)."""
    return Lote.objects.create(
        producto=producto,
        numero_lote="LOT-FARM-001",
        fecha_caducidad=date.today() + timedelta(days=365),
        cantidad_inicial=100,
        cantidad_actual=100,
        centro=None,  # Farmacia central
        lote_origen=None
    )


@pytest.fixture
def user(db):
    """Fixture para crear un usuario de prueba."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        first_name="Test"
    )


# =============================================================================
# ISS-001: Tests de logging correcto en Producto.save()
# =============================================================================
class TestProductoLogging:
    """Tests para verificar que el log de Producto registra correctamente creación vs actualización."""
    
    @pytest.mark.django_db
    def test_log_creacion_producto(self, caplog):
        """ISS-001: Verificar que al crear un producto se loguea 'creado'."""
        with caplog.at_level(logging.INFO):
            producto = Producto.objects.create(
                clave="NEWPROD",
                descripcion="Nuevo producto para test de logging",
                unidad_medida="PIEZA",  # Usar unidad válida
                precio_unitario=Decimal("15.00"),
                stock_minimo=5
            )
        
        # Verificar que el log indica 'creado'
        assert any("NEWPROD" in record.message and "creado" in record.message 
                   for record in caplog.records), \
            "El log debe indicar 'creado' para productos nuevos"
    
    @pytest.mark.django_db
    def test_log_actualizacion_producto(self, producto, caplog):
        """ISS-001: Verificar que al actualizar un producto se loguea 'actualizado'."""
        with caplog.at_level(logging.INFO):
            producto.descripcion = "Descripción modificada para test"
            producto.save()
        
        # Verificar que el log indica 'actualizado'
        assert any(producto.clave in record.message and "actualizado" in record.message 
                   for record in caplog.records), \
            "El log debe indicar 'actualizado' para productos existentes"


# =============================================================================
# ISS-002: Tests de trazabilidad obligatoria lote_origen
# =============================================================================
class TestLoteOrigenObligatorio:
    """Tests para verificar que los lotes en centros deben tener lote_origen."""
    
    @pytest.mark.django_db
    def test_lote_farmacia_sin_origen_ok(self, producto):
        """Lotes en farmacia central (centro=None) NO deben tener lote_origen."""
        lote = Lote(
            producto=producto,
            numero_lote="LOT-FC-001",
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            centro=None,
            lote_origen=None
        )
        # No debe lanzar excepción
        lote.full_clean()
        lote.save()
        assert lote.pk is not None
    
    @pytest.mark.django_db
    def test_lote_farmacia_con_origen_error(self, producto, lote_farmacia):
        """ISS-002: Lotes en farmacia central NO deben tener lote_origen."""
        lote = Lote(
            producto=producto,
            numero_lote="LOT-FC-002",
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=50,
            cantidad_actual=50,
            centro=None,
            lote_origen=lote_farmacia  # ERROR: farmacia no debe tener origen
        )
        with pytest.raises(ValidationError) as exc_info:
            lote.full_clean()
        
        assert 'lote_origen' in exc_info.value.message_dict
        assert "farmacia central no deben tener lote origen" in str(exc_info.value)
    
    @pytest.mark.django_db
    def test_lote_centro_sin_origen_error(self, producto, centro):
        """ISS-002: Lotes en centros DEBEN tener lote_origen - error si falta."""
        lote = Lote(
            producto=producto,
            numero_lote="LOT-CTR-001",
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=30,
            cantidad_actual=30,
            centro=centro,
            lote_origen=None  # ERROR: centro DEBE tener origen
        )
        with pytest.raises(ValidationError) as exc_info:
            lote.full_clean()
        
        assert 'lote_origen' in exc_info.value.message_dict
        assert "trazabilidad" in str(exc_info.value).lower()
    
    @pytest.mark.django_db
    def test_lote_centro_con_origen_ok(self, producto, centro, lote_farmacia):
        """ISS-002: Lotes en centros con lote_origen válido deben guardarse."""
        lote = Lote(
            producto=producto,
            numero_lote=lote_farmacia.numero_lote,  # Mismo número de lote que el origen
            fecha_caducidad=lote_farmacia.fecha_caducidad,  # Misma fecha
            cantidad_inicial=20,
            cantidad_actual=20,
            centro=centro,
            lote_origen=lote_farmacia
        )
        # No debe lanzar excepción
        lote.full_clean()
        lote.save()
        assert lote.pk is not None
        assert lote.lote_origen == lote_farmacia
    
    @pytest.mark.django_db
    def test_lote_centro_origen_producto_diferente_error(self, centro, lote_farmacia):
        """ISS-002: lote_origen debe ser del mismo producto."""
        otro_producto = Producto.objects.create(
            clave="OTRO001",
            descripcion="Otro producto diferente",
            unidad_medida="PIEZA",  # Usar unidad válida
            precio_unitario=Decimal("20.00"),
            stock_minimo=5
        )
        
        lote = Lote(
            producto=otro_producto,  # Producto diferente al lote_origen
            numero_lote="LOT-CTR-003",
            fecha_caducidad=lote_farmacia.fecha_caducidad,
            cantidad_inicial=10,
            cantidad_actual=10,
            centro=centro,
            lote_origen=lote_farmacia
        )
        with pytest.raises(ValidationError) as exc_info:
            lote.full_clean()
        
        assert 'lote_origen' in exc_info.value.message_dict
        assert "mismo producto" in str(exc_info.value).lower()
    
    @pytest.mark.django_db
    def test_lote_centro_fecha_caducidad_diferente_error(self, producto, centro, lote_farmacia):
        """ISS-002: La fecha de caducidad debe coincidir con lote_origen."""
        lote = Lote(
            producto=producto,
            numero_lote="LOT-CTR-004",
            fecha_caducidad=date.today() + timedelta(days=100),  # Fecha diferente
            cantidad_inicial=10,
            cantidad_actual=10,
            centro=centro,
            lote_origen=lote_farmacia
        )
        with pytest.raises(ValidationError) as exc_info:
            lote.full_clean()
        
        assert 'fecha_caducidad' in exc_info.value.message_dict
        assert "coincidir" in str(exc_info.value).lower()


# =============================================================================
# ISS-003: Tests de password reset seguro
# =============================================================================
class TestPasswordResetSeguro:
    """Tests para verificar que los tokens no se exponen en logs."""
    
    @pytest.mark.django_db
    def test_send_email_no_expone_token_en_logs(self, user, caplog):
        """ISS-003: La función de envío NO debe loguear tokens."""
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        
        with patch('core.password_reset.send_mail') as mock_send:
            mock_send.return_value = 1
            with caplog.at_level(logging.DEBUG):
                result = send_password_reset_email(user, uid, token)
        
        # Verificar que el token NO aparece en los logs
        log_text = " ".join(record.message for record in caplog.records)
        assert token not in log_text, "El token NO debe aparecer en los logs"
        assert uid not in log_text or user.email not in log_text, \
            "No deben aparecer datos sensibles en logs"
    
    @pytest.mark.django_db
    def test_send_email_error_no_expone_detalles(self, user, caplog):
        """ISS-003: En caso de error, no exponer detalles sensibles."""
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        
        with patch('core.password_reset.send_mail') as mock_send:
            mock_send.side_effect = Exception("SMTP connection failed with password XYZ")
            with caplog.at_level(logging.ERROR):
                result = send_password_reset_email(user, uid, token)
        
        # Verificar que el error no expone detalles sensibles
        log_text = " ".join(record.message for record in caplog.records)
        assert "password" not in log_text.lower(), "No debe exponer passwords en logs"
        assert "XYZ" not in log_text, "No debe exponer detalles de error sensibles"
        assert result is False
    
    @pytest.mark.django_db
    def test_email_contiene_url_reset(self, user, settings):
        """ISS-003: El email debe contener la URL de reset correcta."""
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        
        with patch('core.password_reset.send_mail') as mock_send:
            mock_send.return_value = 1
            settings.FRONTEND_URL = 'https://farmacia.example.com'
            result = send_password_reset_email(user, uid, token)
        
        # Verificar que se llamó send_mail con los parámetros correctos
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        message = call_args.kwargs.get('message') or call_args[0][1]
        
        assert uid in message, "El mensaje debe contener el uid"
        assert token in message, "El mensaje debe contener el token"
        assert "reset-password" in message, "El mensaje debe contener la URL de reset"
