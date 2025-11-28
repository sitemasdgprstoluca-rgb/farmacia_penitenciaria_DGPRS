# -*- coding: utf-8 -*-
"""
Tests para el sistema de configuración de tema.
"""
from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from core.models import ConfiguracionSistema

User = get_user_model()


class ConfiguracionSistemaModelTest(TestCase):
    """Tests para el modelo ConfiguracionSistema."""
    
    def setUp(self):
        # Limpiar configuración existente
        ConfiguracionSistema.objects.all().delete()
    
    def test_singleton_pattern(self):
        """Verificar que solo puede existir una instancia."""
        config1 = ConfiguracionSistema.get_config()
        config2 = ConfiguracionSistema.get_config()
        self.assertEqual(config1.pk, config2.pk)
    
    def test_valores_por_defecto(self):
        """Verificar valores por defecto del tema."""
        config = ConfiguracionSistema.get_config()
        self.assertEqual(config.nombre_sistema, 'Sistema de Farmacia Penitenciaria')
        self.assertEqual(config.tema_activo, 'default')
        self.assertEqual(config.color_primario, '#1976D2')
    
    def test_to_css_variables(self):
        """Verificar generación de variables CSS."""
        config = ConfiguracionSistema.get_config()
        css_vars = config.to_css_variables()
        
        self.assertIn('--color-primary', css_vars)
        self.assertIn('--color-secondary', css_vars)
        self.assertIn('--color-background', css_vars)
        # Verificar que el valor está en los valores del diccionario
        self.assertEqual(css_vars['--color-primary'], '#1976D2')
    
    def test_aplicar_tema_predefinido(self):
        """Verificar aplicación de tema predefinido."""
        success = ConfiguracionSistema.aplicar_tema_predefinido('dark')
        self.assertTrue(success)
        
        config = ConfiguracionSistema.get_config()
        self.assertEqual(config.tema_activo, 'dark')
        self.assertEqual(config.color_primario, '#BB86FC')
        self.assertEqual(config.color_fondo, '#121212')
    
    def test_aplicar_tema_invalido(self):
        """Verificar que tema inválido retorna False."""
        success = ConfiguracionSistema.aplicar_tema_predefinido('tema_inexistente')
        self.assertFalse(success)
    
    def test_temas_predefinidos_disponibles(self):
        """Verificar que los temas predefinidos están disponibles."""
        temas = ConfiguracionSistema.TEMAS_PREDEFINIDOS
        
        # Es una lista de tuplas (clave, nombre)
        temas_keys = [t[0] for t in temas]
        self.assertIn('default', temas_keys)
        self.assertIn('dark', temas_keys)
        self.assertIn('green', temas_keys)
        self.assertIn('purple', temas_keys)


class ConfiguracionSistemaAPITest(APITestCase):
    """Tests para la API de configuración de tema."""
    
    def setUp(self):
        self.client = APIClient()
        
        # Crear superusuario
        self.superuser = User.objects.create_superuser(
            username='superadmin',
            email='superadmin@test.com',
            password='superpass123',
            first_name='Super',
            last_name='Admin'
        )
        
        # Crear usuario normal
        self.normal_user = User.objects.create_user(
            username='normaluser',
            email='normal@test.com',
            password='normalpass123',
            first_name='Normal',
            last_name='User'
        )
        
        # Limpiar configuración
        ConfiguracionSistema.objects.all().delete()
    
    def test_obtener_tema_sin_auth(self):
        """Cualquiera puede obtener el tema actual."""
        response = self.client.get('/api/configuracion/tema/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tema_activo', response.data)
        self.assertIn('css_variables', response.data)
    
    def test_obtener_tema_con_auth(self):
        """Usuario autenticado puede obtener tema."""
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get('/api/configuracion/tema/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_modificar_tema_como_superuser(self):
        """Superusuario puede modificar el tema."""
        self.client.force_authenticate(user=self.superuser)
        
        data = {
            'color_primario': '#FF5722',
            'color_secundario': '#4CAF50'
        }
        
        response = self.client.put('/api/configuracion/tema/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que se guardó
        config = ConfiguracionSistema.get_config()
        self.assertEqual(config.color_primario, '#FF5722')
        self.assertEqual(config.color_secundario, '#4CAF50')
    
    def test_modificar_tema_sin_permisos(self):
        """Usuario normal no puede modificar el tema."""
        self.client.force_authenticate(user=self.normal_user)
        
        data = {'color_primario': '#FF5722'}
        
        response = self.client.put('/api/configuracion/tema/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_aplicar_tema_predefinido(self):
        """Superusuario puede aplicar tema predefinido."""
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.post(
            '/api/configuracion/tema/aplicar-tema/',
            {'tema': 'dark'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        config = ConfiguracionSistema.get_config()
        self.assertEqual(config.tema_activo, 'dark')
    
    def test_aplicar_tema_predefinido_sin_permisos(self):
        """Usuario normal no puede aplicar tema."""
        self.client.force_authenticate(user=self.normal_user)
        
        response = self.client.post(
            '/api/configuracion/tema/aplicar-tema/',
            {'tema': 'dark'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_restablecer_tema(self):
        """Superusuario puede restablecer tema por defecto."""
        self.client.force_authenticate(user=self.superuser)
        
        # Primero cambiar a otro tema
        ConfiguracionSistema.aplicar_tema_predefinido('dark')
        
        # Restablecer
        response = self.client.post('/api/configuracion/tema/restablecer/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        config = ConfiguracionSistema.get_config()
        self.assertEqual(config.tema_activo, 'default')
    
    def test_css_variables_en_respuesta(self):
        """Verificar que CSS variables se incluyen en respuesta."""
        response = self.client.get('/api/configuracion/tema/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('css_variables', response.data)
        self.assertIn('--color-primary', response.data['css_variables'])


class ConfiguracionSistemaIntegracionTest(APITestCase):
    """Tests de integración para configuración de tema."""
    
    def setUp(self):
        self.client = APIClient()
        self.superuser = User.objects.create_superuser(
            username='superadmin',
            email='superadmin@test.com',
            password='superpass123'
        )
        ConfiguracionSistema.objects.all().delete()
    
    def test_flujo_completo_personalizacion(self):
        """Test del flujo completo de personalización."""
        self.client.force_authenticate(user=self.superuser)
        
        # 1. Obtener configuración inicial
        response = self.client.get('/api/configuracion/tema/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['tema_activo'], 'default')
        
        # 2. Aplicar tema oscuro
        response = self.client.post(
            '/api/configuracion/tema/aplicar-tema/',
            {'tema': 'dark'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 3. Verificar cambio
        response = self.client.get('/api/configuracion/tema/')
        self.assertEqual(response.data['tema_activo'], 'dark')
        
        # 4. Personalizar colores específicos
        response = self.client.put(
            '/api/configuracion/tema/',
            {'color_acento': '#FF4081', 'tema_activo': 'custom'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 5. Verificar personalización
        response = self.client.get('/api/configuracion/tema/')
        self.assertEqual(response.data['tema_activo'], 'custom')
        
        # 6. Restablecer
        response = self.client.post('/api/configuracion/tema/restablecer/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 7. Verificar restablecimiento
        response = self.client.get('/api/configuracion/tema/')
        self.assertEqual(response.data['tema_activo'], 'default')
