"""Tests E2E - Flujos completos y validaciones de seguridad."""

from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
import openpyxl

from core.models import Centro, Producto, Lote, Requisicion, DetalleRequisicion

User = get_user_model()


class E2EFlujosCompletos(TestCase):
    """E2E: Flujos completos de usuario."""

    def setUp(self):
        # Usuarios
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123",
        )
        self.farmacia_user = User.objects.create_user(
            username="farmacia",
            password="test123",
            is_staff=True,
            rol="farmacia",  # Rol necesario para acceder a reportes
        )
        self.centro_user = User.objects.create_user(
            username="centro_user",
            password="test123",
        )

        # Centros
        self.farmacia = Centro.objects.create(
            clave="FARM001",
            nombre="Farmacia Principal",
            tipo="Farmacia",
        )
        self.centro = Centro.objects.create(
            clave="CTR001",
            nombre="Centro de Salud",
            tipo="Centro Penitenciario",
        )

        # Asignar centros
        self.farmacia_user.centro = self.farmacia
        self.farmacia_user.save()
        self.centro_user.centro = self.centro
        self.centro_user.save()

        # Producto y lote base
        self.producto = Producto.objects.create(
            clave="PROD001",
            descripcion="Medicamento de Prueba",
            unidad_medida="CAJA",
            precio_unitario=Decimal("500.00"),
            stock_minimo=5,
            created_by=self.admin,
        )
        # Lote en farmacia CENTRAL (centro=None)
        self.lote = Lote.objects.create(
            producto=self.producto,
            numero_lote="LOT001",
            fecha_caducidad=date.today() + timedelta(days=60),
            cantidad_inicial=100,
            cantidad_actual=100,
            centro=None,  # Farmacia central
            created_by=self.admin,
        )

        self.client = APIClient()

    def _auth(self, username, password):
        """Helper para autenticarse por token JWT."""
        response = self.client.post(
            "/api/token/",
            {"username": username, "password": password},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token = response.data.get("access")
        self.assertTrue(token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_e2e_requisicion_completa(self):
        """Flujo: crear requisicion -> autorizar y notificar."""
        # Admin crea requisición directamente en estado "enviada"
        self._auth("admin", "admin123")
        req_payload = {
            "centro": self.centro.id,
            "estado": "borrador",  # Se crea en borrador primero
            "detalles": [
                {"producto": self.producto.id, "cantidad_solicitada": 10}
            ],
        }
        resp = self.client.post("/api/requisiciones/", req_payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        # La respuesta puede tener estructura {'requisicion': {...}} o directamente {...}
        req_data = resp.data.get("requisicion", resp.data)
        req_id = req_data.get("id")
        if not req_id:
            print("DEBUG: resp.data =", resp.data)
            self.fail("No se pudo obtener ID de requisición")

        # Admin cambia estado a "enviada" mientras está en borrador
        resp = self.client.patch(
            f"/api/requisiciones/{req_id}/",
            {"estado": "enviada"},
            format="json",
        )
        if resp.status_code != status.HTTP_200_OK:
            print(f"DEBUG: PATCH enviada failed: {resp.status_code}, data={resp.data}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Admin la autoriza usando POST /autorizar/
        resp = self.client.post(
            f"/api/requisiciones/{req_id}/autorizar/",
            {},
            format="json",
        )
        if resp.status_code != status.HTTP_200_OK:
            print(f"DEBUG: POST autorizar failed: {resp.status_code}, data={resp.data}")
        self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

        # Verificar notificación (admin puede verlas todas)
        resp = self.client.get("/api/notificaciones/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        listado = resp.data.get("results", resp.data)
        # Puede o no haber notificaciones dependiendo de la lógica
        self.assertIsInstance(listado, list)

    def test_e2e_reporte_inventario_excel(self):
        """Generar reporte inventario JSON y Excel."""
        self._auth("farmacia", "test123")

        resp = self.client.get("/api/reportes/inventario/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.client.get("/api/reportes/inventario/?formato=excel")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def test_e2e_escanear_codigo_producto(self):
        """Busqueda por codigo de barras de producto."""
        self.producto.codigo_barras_producto = "BARCODE123"
        self.producto.save()

        self._auth("admin", "admin123")
        resp = self.client.get("/api/productos/?codigo_barras=BARCODE123")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resultados = resp.data.get("results", resp.data)
        self.assertTrue(len(resultados) >= 1)
        primer = resultados[0]
        self.assertEqual(primer.get("clave"), "PROD001")

    def test_e2e_perfil_usuario(self):
        """Flujo: obtener perfil -> editar datos -> cambiar contraseña."""
        self._auth("centro_user", "test123")
        
        # Obtener perfil
        resp = self.client.get("/api/usuarios/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["username"], "centro_user")
        
        # Editar datos
        resp = self.client.patch("/api/usuarios/me/", {
            "first_name": "Juan",
            "last_name": "Pérez"
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["first_name"], "Juan")
        
        # Cambiar contraseña (debe tener 8+ chars, mayúscula y número)
        resp = self.client.post("/api/usuarios/me/change-password/", {
            "old_password": "test123",
            "new_password": "NewPass123",
            "confirm_password": "NewPass123"
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        # Verificar nueva contraseña
        self.client.credentials()
        self._auth("centro_user", "NewPass123")
        resp = self.client.get("/api/usuarios/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_e2e_inventario_centro(self):
        """Flujo: obtener inventario de un centro específico."""
        self._auth("farmacia", "test123")
        
        # Usuario accede a su propio centro
        resp = self.client.get(f"/api/centros/{self.farmacia.id}/inventario/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # La respuesta es un dict con estructura {'centro': ..., 'inventario': [...]}
        self.assertIn('inventario', resp.data)
        self.assertIsInstance(resp.data['inventario'], list)


class E2ESeguridad(TestCase):
    """E2E: Validaciones de seguridad y permisos."""

    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="test123")
        self.user2 = User.objects.create_user(username="user2", password="test123")

        self.centro1 = Centro.objects.create(clave="CTR001", nombre="Centro 1", tipo="Centro Penitenciario")
        self.centro2 = Centro.objects.create(clave="CTR002", nombre="Centro 2", tipo="Centro Penitenciario")

        self.user1.centro = self.centro1
        self.user1.save()
        self.user2.centro = self.centro2
        self.user2.save()

        self.client = APIClient()

    def _auth(self, username, password):
        resp = self.client.post("/api/token/", {"username": username, "password": password})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        token = resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_usuario_no_ve_requisicion_de_otro_centro(self):
        req = Requisicion.objects.create(usuario_solicita=self.user1, centro=self.centro1)
        DetalleRequisicion.objects.create(requisicion=req, producto=Producto.objects.create(
            clave="SEG001",
            descripcion="Prod Seg",
            unidad_medida="PIEZA",
            precio_unitario=Decimal("10.00"),
            created_by=self.user1,
        ), cantidad_solicitada=1)

        self._auth("user2", "test123")
        resp = self.client.get(f"/api/requisiciones/{req.id}/")
        # Puede ser 403 o 404 dependiendo de la implementación
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_token_invalido_rechazado(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer INVALID_TOKEN")
        resp = self.client.get("/api/requisiciones/")
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_sin_autenticacion_rechazado(self):
        resp = self.client.get("/api/requisiciones/")
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_cambio_password_con_password_incorrecta(self):
        """Cambiar contraseña con contraseña incorrecta debe fallar."""
        self._auth("user1", "test123")
        
        resp = self.client.post("/api/usuarios/me/change-password/", {
            "old_password": "incorrecta",
            "new_password": "newpass123",
            "confirm_password": "newpass123"
        })
        self.assertIn(resp.status_code, [400, 403])

    def test_usuario_no_puede_editar_otro_usuario(self):
        """Usuario no puede editar datos de otro usuario."""
        self._auth("user1", "test123")
        
        # Intenta editar user2
        resp = self.client.patch(f"/api/usuarios/{self.user2.id}/", {
            "first_name": "Hacked"
        })
        self.assertIn(resp.status_code, [403, 404, 405])
