"""
Tests exhaustivos de transiciones de estado de requisiciones.

Valida que las transiciones en el código Django coincidan EXACTAMENTE
con las transiciones permitidas por el trigger de Supabase:
    validar_transicion_estado_requisicion()

ISS-TRIGGER-FIX: Este test asegura que no haya errores de transición
al ejecutar operaciones contra la BD de producción.
"""

import pytest
from django.test import TestCase
from core.constants import TRANSICIONES_REQUISICION, ROLES_POR_TRANSICION


# Transiciones EXACTAS del trigger de Supabase (crear_bd_desarrollo.sql)
# Estas son las ÚNICAS transiciones que la BD acepta
TRANSICIONES_SUPABASE = {
    'borrador': ['pendiente_admin', 'cancelada'],
    'pendiente_admin': ['pendiente_director', 'rechazada', 'devuelta', 'cancelada'],
    'pendiente_director': ['enviada', 'rechazada', 'devuelta', 'cancelada'],
    'enviada': ['en_revision', 'rechazada', 'cancelada'],
    'en_revision': ['autorizada', 'rechazada', 'devuelta'],  # NO parcial
    'autorizada': ['en_surtido', 'cancelada'],
    'en_surtido': ['surtida', 'parcial', 'cancelada'],
    'surtida': ['entregada', 'vencida'],
    'parcial': ['surtida', 'entregada', 'vencida'],
    # Estados finales (sin transiciones)
    'entregada': [],
    'rechazada': [],
    'vencida': [],
    'cancelada': [],
    'devuelta': [],  # No está en trigger pero es válido en Django
}


class TestTransicionesCoinciden(TestCase):
    """
    Verifica que las transiciones definidas en constants.py
    sean un SUBCONJUNTO de las permitidas por Supabase.
    
    Django puede tener MENOS transiciones pero NUNCA más.
    """
    
    def test_todas_las_transiciones_django_son_validas_en_supabase(self):
        """
        Cada transición definida en Django DEBE estar permitida por Supabase.
        """
        errores = []
        
        for estado_origen, destinos_django in TRANSICIONES_REQUISICION.items():
            destinos_supabase = TRANSICIONES_SUPABASE.get(estado_origen, [])
            
            for destino in destinos_django:
                if destino not in destinos_supabase and destinos_supabase:
                    errores.append(
                        f"  ❌ {estado_origen} -> {destino} "
                        f"(Django permite, Supabase NO)"
                    )
        
        if errores:
            msg = "Transiciones en Django que Supabase rechazará:\n"
            msg += "\n".join(errores)
            msg += "\n\nActualiza TRANSICIONES_REQUISICION en constants.py"
            self.fail(msg)
    
    def test_en_revision_no_permite_parcial(self):
        """
        ISS-TRIGGER-FIX: Verifica que en_revision -> parcial NO esté permitida.
        
        El trigger de Supabase solo permite:
            en_revision -> autorizada, rechazada, devuelta
        
        El estado 'parcial' es SOLO para surtido parcial (en_surtido -> parcial).
        """
        destinos_en_revision = TRANSICIONES_REQUISICION.get('en_revision', [])
        
        self.assertNotIn(
            'parcial', destinos_en_revision,
            "❌ en_revision -> parcial NO debe estar permitida. "
            "El estado 'parcial' es solo para SURTIDO parcial, no autorización."
        )
    
    def test_en_revision_permite_autorizada(self):
        """Verifica que en_revision -> autorizada SÍ esté permitida."""
        destinos = TRANSICIONES_REQUISICION.get('en_revision', [])
        self.assertIn('autorizada', destinos)
    
    def test_autorizada_permite_en_surtido(self):
        """
        Verifica que autorizada -> en_surtido esté permitida.
        
        El trigger NO permite autorizada -> surtida directamente.
        Debe pasar por en_surtido.
        """
        destinos = TRANSICIONES_REQUISICION.get('autorizada', [])
        self.assertIn('en_surtido', destinos)
        # Verificar que NO permita ir directo a surtida
        self.assertNotIn(
            'surtida', destinos,
            "❌ autorizada -> surtida NO debe estar permitida. "
            "Debe pasar por en_surtido primero."
        )
        # Verificar que NO permita ir directo a entregada
        self.assertNotIn(
            'entregada', destinos,
            "❌ autorizada -> entregada NO debe estar permitida. "
            "Debe pasar por en_surtido -> surtida primero."
        )
    
    def test_en_surtido_permite_parcial(self):
        """
        Verifica que en_surtido -> parcial SÍ esté permitida.
        
        'parcial' es el estado de surtido parcial, alcanzable desde en_surtido.
        """
        destinos = TRANSICIONES_REQUISICION.get('en_surtido', [])
        self.assertIn('parcial', destinos)
        self.assertIn('surtida', destinos)
    
    def test_enviada_no_permite_autorizada_directa(self):
        """
        ISS-FLUJO-FIX: enviada NO debe ir directo a autorizada.
        
        El flujo correcto es: enviada -> en_revision -> autorizada
        """
        destinos = TRANSICIONES_REQUISICION.get('enviada', [])
        self.assertNotIn(
            'autorizada', destinos,
            "❌ enviada -> autorizada NO debe estar permitida. "
            "Debe pasar por en_revision primero."
        )
        self.assertIn('en_revision', destinos)


class TestRolesPorTransicion(TestCase):
    """Verifica que los roles definidos sean coherentes."""
    
    def test_farmacia_autoriza_desde_en_revision(self):
        """Solo farmacia puede autorizar desde en_revision."""
        roles = ROLES_POR_TRANSICION.get(('en_revision', 'autorizada'), [])
        self.assertTrue(len(roles) > 0)
        self.assertIn('farmacia', roles)
    
    def test_no_hay_rol_para_en_revision_parcial(self):
        """
        No debe existir definición de roles para en_revision -> parcial
        porque esa transición no está permitida.
        """
        roles = ROLES_POR_TRANSICION.get(('en_revision', 'parcial'), [])
        self.assertEqual(
            roles, [],
            f"❌ No deberían existir roles para en_revision -> parcial: {roles}"
        )


class TestFlujoCompletoFarmacia(TestCase):
    """
    Verifica el flujo completo de farmacia según el trigger de Supabase.
    """
    
    def test_flujo_farmacia_correcto(self):
        """
        El flujo correcto de farmacia es:
        
        1. enviada (llega de centro)
        2. -> en_revision (farmacia recibe)
        3. -> autorizada (farmacia autoriza con fecha)
        4. -> en_surtido (farmacia inicia surtido)
        5. -> surtida (farmacia completa surtido)
        6. -> entregada (farmacia entrega)
        
        En caso de surtido parcial:
        4. -> en_surtido
        5. -> parcial (si no se pudo surtir todo)
        6. -> entregada (cuando se complete)
        """
        # Paso 1: enviada -> en_revision
        self.assertIn('en_revision', TRANSICIONES_REQUISICION.get('enviada', []))
        
        # Paso 2: en_revision -> autorizada
        self.assertIn('autorizada', TRANSICIONES_REQUISICION.get('en_revision', []))
        
        # Paso 3: autorizada -> en_surtido
        self.assertIn('en_surtido', TRANSICIONES_REQUISICION.get('autorizada', []))
        
        # Paso 4: en_surtido -> surtida o parcial
        destinos_surtido = TRANSICIONES_REQUISICION.get('en_surtido', [])
        self.assertIn('surtida', destinos_surtido)
        self.assertIn('parcial', destinos_surtido)
        
        # Paso 5: surtida -> entregada
        self.assertIn('entregada', TRANSICIONES_REQUISICION.get('surtida', []))
        
        # Alternativa: parcial -> entregada
        self.assertIn('entregada', TRANSICIONES_REQUISICION.get('parcial', []))
    
    def test_transiciones_prohibidas(self):
        """
        Verifica transiciones que NO deben existir según el trigger.
        """
        prohibidas = [
            ('enviada', 'autorizada'),      # Debe pasar por en_revision
            ('enviada', 'parcial'),         # No existe
            ('en_revision', 'parcial'),     # parcial es solo para surtido
            ('autorizada', 'surtida'),      # Debe pasar por en_surtido
            ('autorizada', 'entregada'),    # Debe pasar por en_surtido -> surtida
            ('surtida', 'cancelada'),       # Ya hay movimientos de inventario
        ]
        
        errores = []
        for origen, destino in prohibidas:
            destinos = TRANSICIONES_REQUISICION.get(origen, [])
            if destino in destinos:
                errores.append(f"  ❌ {origen} -> {destino} NO debería existir")
        
        if errores:
            self.fail("Transiciones prohibidas encontradas:\n" + "\n".join(errores))


class TestEstadosFinales(TestCase):
    """Verifica que los estados finales no tengan transiciones."""
    
    def test_estados_finales_sin_transiciones(self):
        """
        Los estados finales no deben tener transiciones de salida.
        """
        estados_finales = ['entregada', 'rechazada', 'vencida', 'cancelada']
        
        for estado in estados_finales:
            destinos = TRANSICIONES_REQUISICION.get(estado, [])
            self.assertEqual(
                destinos, [],
                f"❌ Estado final '{estado}' no debe tener transiciones: {destinos}"
            )


# Ejecutar tests con pytest
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
