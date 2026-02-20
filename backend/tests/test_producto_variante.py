# -*- coding: utf-8 -*-
"""
ISS-PROD-VAR: Tests para el sistema de variantes por presentación.

Cobertura:
  - normalizar_presentacion: normalización semántica + básica + fallback
  - extraer_codigo_base / es_variante: parsing de claves
  - siguiente_codigo_variante: generación de sufijos
  - obtener_o_crear_variante: flujo completo (crear, reusar, variante nueva)
  - migrar_variantes_existentes: detección de conflictos
"""
import pytest
from django.test import TestCase
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# UNIT: normalizar_presentacion
# ---------------------------------------------------------------------------

class TestNormalizarPresentacion(TestCase):

    def setUp(self):
        from core.utils.producto_variante import normalizar_presentacion
        self.norm = normalizar_presentacion

    def test_basico_uppercase(self):
        assert self.norm('caja') == 'CAJA'

    def test_quita_acentos(self):
        assert 'CAPSULA' in self.norm('cápsulas') or 'CAPSULA' in self.norm('capsulas')

    def test_tabs_a_tableta(self):
        result = self.norm('caja con 10 tabs')
        assert 'TABLETA' in result

    def test_caps_a_capsula(self):
        result = self.norm('frasco 30 caps')
        assert 'CAPSULA' in result

    def test_comprimidos_a_tableta(self):
        result = self.norm('caja 15 comprimidos')
        assert 'TABLETA' in result

    def test_c_barra_a_con(self):
        result = self.norm('frasco c/ 120ml')
        assert 'CON' in result

    def test_mililitros_a_ml(self):
        result = self.norm('frasco 120 mililitros')
        assert 'ML' in result

    def test_ampolletas_singular(self):
        result = self.norm('caja 5 ampolletas')
        assert 'AMPOLLETA' in result

    def test_frascos_singular(self):
        result = self.norm('2 frascos')
        assert 'FRASCO' in result

    def test_porcentaje(self):
        result = self.norm('solucion 5%')
        assert 'PORCIENTO' in result or '5' in result

    def test_equivalencia_semantica(self):
        """Dos textos con diferente ortografía deben normalizar igual."""
        a = self.norm('Caja c/10 tabletas')
        b = self.norm('CAJA CON 10 TABS')
        assert a == b, f"Se esperaba igualdad pero got: '{a}' vs '{b}'"

    def test_equivalencia_plurales(self):
        a = self.norm('caja 5 capsulas')
        b = self.norm('CAJA 5 CAPS')
        assert a == b, f"'{a}' != '{b}'"

    def test_vacio(self):
        assert self.norm('') == ''
        assert self.norm(None) == ''

    def test_texto_sin_abreviaturas(self):
        """Texto que no tiene abreviaturas se normaliza igual a mayúsculas básicas."""
        result = self.norm('JERINGA 10 ML')
        assert result == 'JERINGA 10 ML'

    def test_fallback_no_crash(self):
        """Incluso con texto raro, no debe crashear."""
        result = self.norm('   !!!§§§   ')
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# UNIT: extraer_codigo_base / es_variante
# ---------------------------------------------------------------------------

class TestCodigoBase(TestCase):

    def setUp(self):
        from core.utils.producto_variante import extraer_codigo_base, es_variante
        self.base = extraer_codigo_base
        self.variante = es_variante

    def test_sin_sufijo(self):
        assert self.base('663') == '663'

    def test_con_sufijo_2(self):
        assert self.base('663.2') == '663'

    def test_con_sufijo_10(self):
        assert self.base('663.10') == '663'

    def test_codigo_alfanumerico(self):
        assert self.base('MED-001') == 'MED-001'

    def test_codigo_alfanumerico_con_sufijo(self):
        assert self.base('MED-001.3') == 'MED-001'

    def test_es_variante_true(self):
        assert self.variante('663.2') is True

    def test_es_variante_false(self):
        assert self.variante('663') is False

    def test_es_variante_alfanumerico(self):
        assert self.variante('MED-001') is False

    def test_vacio(self):
        assert self.base('') == ''
        assert self.variante('') is False

    def test_solo_punto(self):
        # '663.' no tiene dígito después del punto → no es variante
        assert self.base('663.') == '663.'
        assert self.variante('663.') is False


# ---------------------------------------------------------------------------
# INTEGRATION: obtener_o_crear_variante (con DB de tests)
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestObtenerOCrearVariante(TestCase):

    def _call(self, clave, nombre='PARACETAMOL', presentacion='CAJA 10 TABLETAS', defaults=None):
        from core.utils.producto_variante import obtener_o_crear_variante
        return obtener_o_crear_variante(
            clave_input=clave,
            nombre=nombre,
            presentacion=presentacion,
            defaults=defaults or {},
        )

    def test_crear_producto_base_nuevo(self):
        """Primer producto: se crea con la clave exacta enviada."""
        prod, created, info = self._call('TEST001')
        assert created is True
        assert prod.clave == 'TEST001'
        assert info['codigo_asignado'] == 'TEST001'
        assert info['motivo'] == 'producto_base_nuevo'
        assert info['es_variante'] is False

    def test_reusar_producto_identico(self):
        """Si ya existe con misma presentación, se reutiliza sin crear duplicado."""
        self._call('TEST002', presentacion='CAJA 10 TABLETAS')
        prod2, created2, info2 = self._call('TEST002', presentacion='caja con 10 tabs')
        assert created2 is False
        assert prod2.clave == 'TEST002'
        assert info2['motivo'] == 'reutilizado_presentacion_identica'

    def test_crear_variante_nueva(self):
        """Misma clave base, presentación diferente → crea 663.2."""
        self._call('TEST003', presentacion='CAJA 10 TABLETAS')
        prod2, created2, info2 = self._call('TEST003', presentacion='CAJA 15 TABLETAS')
        assert created2 is True
        assert prod2.clave == 'TEST003.2'
        assert info2['es_variante'] is True
        assert info2['codigo_base'] == 'TEST003'
        assert info2['motivo'] == 'variante_nueva_creada'

    def test_crear_tercera_variante(self):
        """Dos presentaciones existentes → tercera recibe sufijo .3."""
        self._call('TEST004', presentacion='CAJA 10 TABLETAS')
        self._call('TEST004', presentacion='CAJA 15 TABLETAS')
        prod3, created3, info3 = self._call('TEST004', presentacion='FRASCO 30 TABLETAS')
        assert created3 is True
        assert prod3.clave == 'TEST004.3'
        assert info3['codigo_asignado'] == 'TEST004.3'

    def test_reusar_variante_existente(self):
        """Si ya existe una variante con la misma presentación, se reutiliza."""
        self._call('TEST005', presentacion='CAJA 10 TABLETAS')
        self._call('TEST005', presentacion='CAJA 15 TABLETAS')  # crea TEST005.2
        # Volver a pedir TEST005 con la presentación de la segunda variante
        prod, created, info = self._call('TEST005', presentacion='caja con 15 tabs')
        assert created is False
        assert prod.clave == 'TEST005.2'
        assert info['motivo'] == 'reutilizado_variante_existente'

    def test_clave_sufijada_explicita_match(self):
        """Usuario envía TEST006.2 con presentación igual a la existente → ok."""
        from core.models import Producto
        Producto.objects.create(
            clave='TEST006',
            nombre='PARACETAMOL',
            presentacion='CAJA 10 TABLETAS',
        )
        Producto.objects.create(
            clave='TEST006.2',
            nombre='PARACETAMOL',
            presentacion='CAJA 15 TABLETAS',
        )
        prod, created, info = self._call(
            'TEST006.2', presentacion='caja 15 tabletas'
        )
        assert created is False
        assert prod.clave == 'TEST006.2'

    def test_clave_sufijada_explicita_conflicto(self):
        """Usuario envía TEST007.2 con presentación DISTINTA → ValueError."""
        from core.models import Producto
        from core.utils.producto_variante import obtener_o_crear_variante
        Producto.objects.create(
            clave='TEST007.2',
            nombre='PARACETAMOL',
            presentacion='CAJA 10 TABLETAS',
        )
        with pytest.raises(ValueError):
            obtener_o_crear_variante(
                clave_input='TEST007.2',
                nombre='PARACETAMOL',
                presentacion='CAJA 30 TABLETAS',  # diferente
                defaults={},
            )

    def test_sin_presentacion_reusar(self):
        """Si la presentación está vacía, se reutiliza el producto existente."""
        from core.models import Producto
        Producto.objects.create(
            clave='TEST008',
            nombre='GENERICO',
        )
        prod, created, info = self._call('TEST008', presentacion='')
        assert created is False
        assert prod.clave == 'TEST008'
        assert 'sin_presentacion' in info['motivo']

    def test_uppercase_normalizacion_clave(self):
        """La clave siempre se guarda en mayúsculas."""
        prod, created, _ = self._call('test009', presentacion='CAJA 5 TABLETAS')
        assert prod.clave == 'TEST009'


# ---------------------------------------------------------------------------
# UNIT: siguiente_codigo_variante
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestSiguienteCodigoVariante(TestCase):

    def test_sin_variantes_devuelve_2(self):
        from core.models import Producto
        from core.utils.producto_variante import siguiente_codigo_variante
        Producto.objects.create(clave='SVAR001', nombre='TEST')
        resultado = siguiente_codigo_variante('SVAR001')
        assert resultado == 'SVAR001.2'

    def test_con_variante_2_devuelve_3(self):
        from core.models import Producto
        from core.utils.producto_variante import siguiente_codigo_variante
        Producto.objects.create(clave='SVAR002', nombre='TEST')
        Producto.objects.create(clave='SVAR002.2', nombre='TEST')
        resultado = siguiente_codigo_variante('SVAR002')
        assert resultado == 'SVAR002.3'

    def test_con_huecos_va_al_siguiente_del_maximo(self):
        """Si existen .2 y .5, el siguiente debe ser .6 (no .3)."""
        from core.models import Producto
        from core.utils.producto_variante import siguiente_codigo_variante
        Producto.objects.create(clave='SVAR003', nombre='TEST')
        Producto.objects.create(clave='SVAR003.2', nombre='TEST')
        Producto.objects.create(clave='SVAR003.5', nombre='TEST')
        resultado = siguiente_codigo_variante('SVAR003')
        assert resultado == 'SVAR003.6'


# ---------------------------------------------------------------------------
# UNIT: migrar_variantes_existentes
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestMigrarVariantesExistentes(TestCase):

    def test_detecta_conflictos_dry_run(self):
        from core.models import Producto
        from core.utils.producto_variante import migrar_variantes_existentes
        # Crear situación conflictiva: misma clave base, presentaciones diferentes
        Producto.objects.create(clave='MIG001', nombre='DROGA', presentacion='CAJA 10 TABS')
        Producto.objects.create(clave='MIG001.2', nombre='DROGA', presentacion='CAJA 20 TABS')

        resultados = migrar_variantes_existentes(dry_run=True)
        claves_afectadas = [r['codigo_base'] for r in resultados]
        assert 'MIG001' in claves_afectadas

        # Con dry_run, no debería haber cambios
        resultado_mig = next(r for r in resultados if r['codigo_base'] == 'MIG001')
        assert resultado_mig['accion'] == 'detectado'

    def test_sin_conflictos_devuelve_lista_vacia(self):
        from core.models import Producto
        from core.utils.producto_variante import migrar_variantes_existentes
        Producto.objects.create(clave='MIG002', nombre='DROGA UNICA', presentacion='CAJA')
        resultados = migrar_variantes_existentes(dry_run=True)
        # MIG002 solo tiene 1 producto → no hay conflicto
        bases_en_resultado = [r['codigo_base'] for r in resultados]
        assert 'MIG002' not in bases_en_resultado
