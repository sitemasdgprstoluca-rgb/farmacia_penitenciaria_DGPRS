from django.test import TestCase
from unittest import skipIf
from django.db import connection
from core.models import User, Centro, UserProfile


def is_sqlite():
    """Detecta si estamos usando SQLite."""
    return connection.vendor == 'sqlite'


class TestUserCentroAssignment(TestCase):
    """Tests de asignación de centro a usuario.
    
    NOTA: Estos tests pueden fallar en SQLite porque los modelos 
    Centro y UserProfile usan managed=False, y la estructura de 
    tablas en SQLite de tests puede diferir de Supabase.
    """
    
    @skipIf(is_sqlite(), "Skipped: modelos con managed=False no funcionan bien en SQLite")
    def test_user_centro_is_unique_source_of_truth(self):
        """User.centro is the only source of centro assignment."""
        centro = Centro.objects.create(nombre='Centro Test')
        user = User.objects.create_user(
            username='testuser',
            password='dummy-pass',
            centro=centro
        )
        self.assertEqual(user.centro, centro)
    
    @skipIf(is_sqlite(), "Skipped: modelos con managed=False no funcionan bien en SQLite")
    def test_requisicion_filtering_by_centro(self):
        """Users keep independent centro values."""
        centro1 = Centro.objects.create(nombre='Centro 1')
        centro2 = Centro.objects.create(nombre='Centro 2')
        user1 = User.objects.create_user(username='user1', password='pass-1', centro=centro1)
        user2 = User.objects.create_user(username='user2', password='pass-2', centro=centro2)
        self.assertNotEqual(user1.centro, user2.centro)

    def test_profile_has_centro_field(self):
        """UserProfile exposes centro field (per Supabase schema).
        
        La tabla user_profiles en Supabase SÍ tiene centro_id.
        Esto es independiente de User.centro.
        """
        profile_fields = [f.name for f in UserProfile._meta.get_fields()]
        # UserProfile.centro existe en BD Supabase
        self.assertIn('centro', profile_fields)
