from django.test import TestCase
from core.models import User, Centro, UserProfile


class TestUserCentroAssignment(TestCase):
    def test_user_centro_is_unique_source_of_truth(self):
        """User.centro is the only source of centro assignment."""
        centro = Centro.objects.create(clave='CP-001', nombre='Centro Test')

        user = User.objects.create_user(
            username='testuser',
            password='dummy-pass',
            centro=centro
        )

        self.assertEqual(user.centro, centro)

        profile, _ = UserProfile.objects.get_or_create(user=user)
        self.assertFalse(hasattr(profile, 'centro'))

    def test_requisicion_filtering_by_centro(self):
        """Users keep independent centro values."""
        centro1 = Centro.objects.create(clave='CP-001', nombre='Centro 1')
        centro2 = Centro.objects.create(clave='CP-002', nombre='Centro 2')

        user1 = User.objects.create_user(username='user1', password='pass-1', centro=centro1)
        user2 = User.objects.create_user(username='user2', password='pass-2', centro=centro2)

        self.assertNotEqual(user1.centro, user2.centro)

    def test_no_profile_centro_field(self):
        """UserProfile no longer exposes a centro field."""
        profile_fields = [f.name for f in UserProfile._meta.get_fields()]
        self.assertNotIn('centro', profile_fields)
