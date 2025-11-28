"""
Core tests package.

Exports base test classes for use in other test modules:
- BaseTestCase: For model/unit tests without API
- BaseAPITestCase: For API tests with common setup
- NoThrottleMixin: Mixin to disable throttling in any test class

Usage:
    from core.tests import BaseAPITestCase
    
    class MyAPITest(BaseAPITestCase):
        def test_endpoint(self):
            self.authenticate_as_admin()
            response = self.client.get('/api/v1/productos/')
            self.assertResponseOk(response)
"""

from core.tests.base import BaseTestCase, BaseAPITestCase, NoThrottleMixin

__all__ = ['BaseTestCase', 'BaseAPITestCase', 'NoThrottleMixin']
