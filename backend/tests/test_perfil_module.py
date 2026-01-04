"""
Tests completos para el módulo de Perfil
Cubre: Backend API, integración con BD, y validaciones

NOTA: Muchos modelos usan managed=False (tablas en Supabase),
      por lo que tests de API pueden fallar con 500 en entorno de test.
      Los tests de lógica y validaciones funcionan correctamente.

Ejecutar con: pytest tests/test_perfil_module.py -v
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


# ============================================================================
# HELPER FUNCTIONS - Imports lazy para evitar problemas de app registry
# ============================================================================

def get_tema_global_model():
    """Obtiene TemaGlobal model de forma lazy"""
    from core.models import TemaGlobal
    return TemaGlobal


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def api_client():
    """Cliente API para tests"""
    return APIClient()


# ============================================================================
# TESTS DE BASE DE DATOS - TEMA GLOBAL (sin managed=False issues)
# ============================================================================

class TestTemaGlobalModelo:
    """Tests para modelo TemaGlobal - Solo instancias en memoria"""
    
    def test_tema_colores_por_defecto_institucionales(self):
        """Verificar colores institucionales por defecto"""
        TemaGlobal = get_tema_global_model()
        tema = TemaGlobal(nombre='Test Tema')
        
        # Colores institucionales del gobierno
        assert tema.color_primario == '#9F2241'  # Rojo vino
        assert tema.color_primario_hover == '#6B1839'  # Vino oscuro
    
    def test_tema_colores_secundarios_defecto(self):
        """Verificar colores secundarios por defecto"""
        TemaGlobal = get_tema_global_model()
        tema = TemaGlobal(nombre='Test Tema')
        
        assert tema.color_exito == '#4a7c4b'
        assert tema.color_alerta == '#d4a017'
        assert tema.color_error == '#c53030'
        assert tema.color_info == '#3182ce'
    
    def test_tema_propiedades_compatibilidad(self):
        """Verificar propiedades de compatibilidad del tema"""
        TemaGlobal = get_tema_global_model()
        tema = TemaGlobal(nombre='Test Compat', es_activo=True)
        
        # Propiedades calculadas
        assert tema.activo is True
        assert tema.color_fondo == '#f7f8fa'
        assert tema.color_texto == '#1f2937'
    
    def test_tema_campos_reporte(self):
        """Verificar campos para reportes"""
        TemaGlobal = get_tema_global_model()
        tema = TemaGlobal(
            nombre='Test Reportes',
            titulo_sistema='Mi Sistema',
            subtitulo_sistema='Mi Subtítulo'
        )
        assert tema.reporte_titulo_institucion == 'Mi Sistema'
        assert tema.reporte_subtitulo == 'Mi Subtítulo'
    
    def test_tema_colores_hover_diferentes(self):
        """Los colores hover deben ser diferentes a los base"""
        TemaGlobal = get_tema_global_model()
        tema = TemaGlobal(nombre='Test Hover')
        
        assert tema.color_primario != tema.color_primario_hover
        assert tema.color_exito != tema.color_exito_hover
        assert tema.color_alerta != tema.color_alerta_hover
        assert tema.color_error != tema.color_error_hover
    
    def test_tema_fuentes_defecto(self):
        """Verificar fuentes por defecto"""
        TemaGlobal = get_tema_global_model()
        tema = TemaGlobal(nombre='Test Fuentes')
        
        assert tema.fuente_principal == 'Inter'
        assert tema.fuente_titulos == 'Inter'
    
    def test_tema_representacion_string(self):
        """__str__ retorna el nombre del tema"""
        TemaGlobal = get_tema_global_model()
        tema = TemaGlobal(nombre='Tema Institucional')
        assert str(tema) == 'Tema Institucional'


# ============================================================================
# TESTS DE VALIDACIONES
# ============================================================================

class TestValidacionesEmail:
    """Tests para validación de email"""
    
    def test_email_valido_simple(self):
        """Email simple válido"""
        from django.core.validators import validate_email
        validate_email('usuario@ejemplo.com')
    
    def test_email_valido_con_puntos(self):
        """Email con puntos en nombre"""
        from django.core.validators import validate_email
        validate_email('usuario.nombre@ejemplo.com')
    
    def test_email_valido_subdominio(self):
        """Email con subdominio"""
        from django.core.validators import validate_email
        validate_email('usuario@mail.ejemplo.com')
    
    def test_email_invalido_sin_arroba(self):
        """Email sin @ es inválido"""
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        
        with pytest.raises(ValidationError):
            validate_email('usuario.ejemplo.com')
    
    def test_email_invalido_sin_dominio(self):
        """Email sin dominio es inválido"""
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        
        with pytest.raises(ValidationError):
            validate_email('usuario@')
    
    def test_email_invalido_espacios(self):
        """Email con espacios es inválido"""
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        
        with pytest.raises(ValidationError):
            validate_email('usuario @ejemplo.com')


class TestValidacionesPassword:
    """Tests para validación de contraseñas"""
    
    def test_password_muy_corta(self):
        """Contraseña < 8 caracteres es inválida"""
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        
        with pytest.raises(ValidationError):
            validate_password('abc123')
    
    def test_password_solo_numeros(self):
        """Contraseña solo con números es inválida"""
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        
        with pytest.raises(ValidationError):
            validate_password('12345678')
    
    def test_password_comun(self):
        """Contraseñas comunes son inválidas"""
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        
        with pytest.raises(ValidationError):
            validate_password('password123')
    
    def test_password_valida_compleja(self):
        """Contraseña compleja pasa validación"""
        from django.contrib.auth.password_validation import validate_password
        # No debe lanzar excepción
        validate_password('MiPassword@Segura2024!')


class TestCalculoFortalezaPassword:
    """Tests para cálculo de fortaleza de contraseña (lógica frontend)"""
    
    @staticmethod
    def calcular_fortaleza(password):
        """Replica la lógica del frontend para calcular fortaleza"""
        score = 0
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if any(c.isupper() for c in password):
            score += 1
        if any(c.isdigit() for c in password):
            score += 1
        if any(c in '!@#$%^&*()_+-=' for c in password):
            score += 1
        return score
    
    def test_fortaleza_password_vacia(self):
        """Password vacía tiene fortaleza 0"""
        assert self.calcular_fortaleza('') == 0
    
    def test_fortaleza_password_muy_corta(self):
        """Password < 8 chars tiene fortaleza 0 (solo si no tiene otros elementos)"""
        assert self.calcular_fortaleza('abc') == 0
        # Una password corta con caracteres variados tiene puntos por variedad
        # pero no por longitud
        fortaleza_corta = self.calcular_fortaleza('Ab1!')
        assert fortaleza_corta < 5  # No puede tener fortaleza máxima sin longitud
    
    def test_fortaleza_password_minima(self):
        """Password 8 chars minúsculas = fortaleza 1"""
        assert self.calcular_fortaleza('abcdefgh') == 1
    
    def test_fortaleza_password_con_mayuscula(self):
        """Password con mayúscula = +1"""
        assert self.calcular_fortaleza('Abcdefgh') == 2
    
    def test_fortaleza_password_con_numero(self):
        """Password con número = +1"""
        assert self.calcular_fortaleza('abcdefg1') == 2
    
    def test_fortaleza_password_con_especial(self):
        """Password con carácter especial = +1"""
        assert self.calcular_fortaleza('abcdefg!') == 2
    
    def test_fortaleza_password_larga(self):
        """Password >= 12 chars = +1 adicional"""
        assert self.calcular_fortaleza('abcdefghijkl') == 2
    
    def test_fortaleza_password_maxima(self):
        """Password con todo = fortaleza 5"""
        assert self.calcular_fortaleza('LongPassword1!') == 5
    
    def test_fortaleza_password_institucional_segura(self):
        """Password típica institucional segura"""
        assert self.calcular_fortaleza('Farmacia2024!') == 5


class TestValidacionTelefono:
    """Tests para validación de formato de teléfono"""
    
    @staticmethod
    def es_telefono_valido(telefono):
        """Valida formato de teléfono mexicano (10 dígitos)"""
        import re
        if not telefono:
            return True  # Campo opcional
        patron = r'^\d{10}$'
        return bool(re.match(patron, telefono.replace(' ', '').replace('-', '')))
    
    def test_telefono_10_digitos_valido(self):
        """Teléfono de 10 dígitos es válido"""
        assert self.es_telefono_valido('5551234567') is True
    
    def test_telefono_con_guiones_valido(self):
        """Teléfono con guiones es válido"""
        assert self.es_telefono_valido('555-123-4567') is True
    
    def test_telefono_con_espacios_valido(self):
        """Teléfono con espacios es válido"""
        assert self.es_telefono_valido('555 123 4567') is True
    
    def test_telefono_corto_invalido(self):
        """Teléfono < 10 dígitos es inválido"""
        assert self.es_telefono_valido('55512345') is False
    
    def test_telefono_largo_invalido(self):
        """Teléfono > 10 dígitos es inválido"""
        assert self.es_telefono_valido('55512345678901') is False
    
    def test_telefono_vacio_valido(self):
        """Teléfono vacío es válido (campo opcional)"""
        assert self.es_telefono_valido('') is True
        assert self.es_telefono_valido(None) is True


# ============================================================================
# TESTS DE FORMATO DE DATOS
# ============================================================================

class TestFormatoNombres:
    """Tests para formateo de nombres"""
    
    @staticmethod
    def formatear_iniciales(first_name, last_name):
        """Genera iniciales a partir del nombre"""
        iniciales = ''
        if first_name:
            iniciales += first_name[0].upper()
        if last_name:
            iniciales += last_name[0].upper()
        return iniciales or '??'
    
    def test_iniciales_nombre_completo(self):
        """Iniciales de nombre y apellido"""
        assert self.formatear_iniciales('Juan', 'Pérez') == 'JP'
    
    def test_iniciales_solo_nombre(self):
        """Iniciales con solo nombre"""
        assert self.formatear_iniciales('Juan', '') == 'J'
    
    def test_iniciales_solo_apellido(self):
        """Iniciales con solo apellido"""
        assert self.formatear_iniciales('', 'Pérez') == 'P'
    
    def test_iniciales_vacias(self):
        """Iniciales por defecto cuando no hay nombre"""
        assert self.formatear_iniciales('', '') == '??'
        assert self.formatear_iniciales(None, None) == '??'
    
    @staticmethod
    def formatear_nombre_completo(first_name, last_name):
        """Concatena nombre y apellido"""
        partes = []
        if first_name:
            partes.append(first_name)
        if last_name:
            partes.append(last_name)
        return ' '.join(partes) or 'Sin nombre'
    
    def test_nombre_completo(self):
        """Nombre completo formateado"""
        assert self.formatear_nombre_completo('Juan', 'Pérez') == 'Juan Pérez'
    
    def test_nombre_sin_apellido(self):
        """Nombre sin apellido"""
        assert self.formatear_nombre_completo('Juan', '') == 'Juan'
    
    def test_nombre_vacio(self):
        """Placeholder cuando no hay nombre"""
        assert self.formatear_nombre_completo('', '') == 'Sin nombre'


class TestAgrupacionPermisos:
    """Tests para agrupación de permisos (lógica frontend)"""
    
    @staticmethod
    def agrupar_permisos(permisos_lista):
        """Agrupa permisos por módulo (replica lógica del frontend)"""
        grupos = {}
        for permiso in permisos_lista:
            partes = permiso.split('_', 1)
            if len(partes) == 2:
                accion, modulo = partes
                if modulo not in grupos:
                    grupos[modulo] = []
                grupos[modulo].append(accion)
        return grupos
    
    def test_agrupar_permisos_por_modulo(self):
        """Permisos se agrupan por módulo"""
        permisos = ['view_producto', 'add_producto', 'change_producto', 'view_lote']
        grupos = self.agrupar_permisos(permisos)
        
        assert 'producto' in grupos
        assert 'lote' in grupos
        assert 'view' in grupos['producto']
        assert 'add' in grupos['producto']
    
    def test_agrupar_permisos_vacio(self):
        """Lista vacía retorna diccionario vacío"""
        assert self.agrupar_permisos([]) == {}


# ============================================================================
# TESTS DE MODELO AUDITORIA
# ============================================================================

class TestModeloAuditoria:
    """Tests para verificar estructura del modelo AuditoriaLog"""
    
    def test_modelo_existe(self):
        """El modelo AuditoriaLog existe"""
        from core.models import AuditoriaLog
        assert AuditoriaLog is not None
    
    def test_campos_basicos_existen(self):
        """Campos básicos están definidos en el modelo"""
        from core.models import AuditoriaLog
        field_names = [f.name for f in AuditoriaLog._meta.get_fields()]
        
        # Campos que deben existir
        assert 'accion' in field_names
        assert 'modelo' in field_names
    
    def test_modelo_tiene_meta_correcta(self):
        """El modelo tiene configuración Meta correcta"""
        from core.models import AuditoriaLog
        # El nombre de la tabla puede ser singular o plural
        assert 'auditoria' in AuditoriaLog._meta.db_table.lower()


# ============================================================================
# TESTS DE API - Con manejo de errores de BD (managed=False)
# ============================================================================

@pytest.mark.django_db
class TestPerfilAPIConManagedFalse:
    """
    Tests de API que pueden fallar debido a tablas managed=False.
    Estos tests verifican el comportamiento esperado pero aceptan
    errores 500 que ocurren en entorno de test debido a tablas
    faltantes (UserProfile, etc.)
    """
    
    def test_endpoint_me_sin_autenticacion(self, api_client):
        """GET /api/usuarios/me/ sin auth retorna 401"""
        response = api_client.get('/api/usuarios/me/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_endpoint_cambio_password_sin_autenticacion(self, api_client):
        """POST /api/usuarios/me/change-password/ sin auth retorna 401"""
        response = api_client.post('/api/usuarios/me/change-password/', {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# TESTS DE SEGURIDAD - Lógica
# ============================================================================

class TestSeguridadLogica:
    """Tests de lógica de seguridad sin BD"""
    
    def test_campos_sensibles_no_serializables(self):
        """Verificar que los campos sensibles no están en serializers"""
        from core.serializers import UserMeSerializer
        
        # Campos que NO deben estar
        campos_prohibidos = ['password', 'password_hash']
        campos_serializer = UserMeSerializer().fields.keys()
        
        for campo in campos_prohibidos:
            assert campo not in campos_serializer, f"Campo sensible '{campo}' expuesto"
    
    def test_campos_no_editables_readonly(self):
        """Verificar campos de solo lectura en serializer"""
        from core.serializers import UserMeSerializer
        
        serializer = UserMeSerializer()
        # is_superuser e is_staff deben ser readonly si existen
        if 'is_superuser' in serializer.fields:
            assert serializer.fields['is_superuser'].read_only
        if 'is_staff' in serializer.fields:
            assert serializer.fields['is_staff'].read_only


