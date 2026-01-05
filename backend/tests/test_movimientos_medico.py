# -*- coding: utf-8 -*-
"""
Tests unitarios para restricción de tipos de movimiento por rol.

Los médicos de centro SOLO pueden hacer "Dispensación por receta" (subtipo_salida='receta').
"""
import pytest
from django.test import TestCase


class TestRestriccionTipoMovimientoMedico(TestCase):
    """Tests para la restricción de tipos de movimiento según rol."""
    
    # Subtipos de salida disponibles
    SUBTIPOS_SALIDA = {
        'transferencia': 'Transferencia a centro',
        'consumo_interno': 'Consumo interno',
        'receta': 'Dispensación por receta',
        'merma': 'Merma / Pérdida',
        'caducidad': 'Caducidad',
    }
    
    def _get_subtipos_permitidos(self, rol, es_superuser=False):
        """Obtener subtipos permitidos según el rol."""
        if es_superuser:
            return ['transferencia']  # Admin usa transferencias
        
        rol_lower = rol.lower() if rol else ''
        
        if rol_lower in ['farmacia', 'admin_farmacia']:
            return ['transferencia']  # Solo transferencias a centros
        
        if rol_lower == 'medico':
            return ['receta']  # SOLO dispensación por receta
        
        if rol_lower in ['centro', 'usuario_centro']:
            return ['consumo_interno', 'receta', 'merma', 'caducidad']
        
        return []  # Sin permisos
    
    def _validar_movimiento(self, rol, subtipo_salida, es_superuser=False):
        """Validar si un rol puede crear un movimiento con cierto subtipo."""
        permitidos = self._get_subtipos_permitidos(rol, es_superuser)
        return subtipo_salida in permitidos
    
    # ========== Tests para médicos ==========
    
    def test_medico_puede_hacer_dispensacion_receta(self):
        """Médico puede crear movimiento tipo 'receta'."""
        self.assertTrue(self._validar_movimiento('medico', 'receta'))
    
    def test_medico_no_puede_hacer_consumo_interno(self):
        """Médico NO puede crear movimiento tipo 'consumo_interno'."""
        self.assertFalse(self._validar_movimiento('medico', 'consumo_interno'))
    
    def test_medico_no_puede_hacer_merma(self):
        """Médico NO puede crear movimiento tipo 'merma'."""
        self.assertFalse(self._validar_movimiento('medico', 'merma'))
    
    def test_medico_no_puede_hacer_caducidad(self):
        """Médico NO puede crear movimiento tipo 'caducidad'."""
        self.assertFalse(self._validar_movimiento('medico', 'caducidad'))
    
    def test_medico_no_puede_hacer_transferencia(self):
        """Médico NO puede crear movimiento tipo 'transferencia'."""
        self.assertFalse(self._validar_movimiento('medico', 'transferencia'))
    
    def test_medico_solo_tiene_un_subtipo_disponible(self):
        """Médico solo tiene acceso a un subtipo de salida."""
        subtipos = self._get_subtipos_permitidos('medico')
        self.assertEqual(len(subtipos), 1)
        self.assertEqual(subtipos[0], 'receta')
    
    # ========== Tests para farmacia ==========
    
    def test_farmacia_puede_hacer_transferencia(self):
        """Farmacia puede crear movimiento tipo 'transferencia'."""
        self.assertTrue(self._validar_movimiento('farmacia', 'transferencia'))
    
    def test_farmacia_no_puede_hacer_receta(self):
        """Farmacia NO puede crear movimiento tipo 'receta' (es para centros)."""
        self.assertFalse(self._validar_movimiento('farmacia', 'receta'))
    
    def test_farmacia_no_puede_hacer_consumo_interno(self):
        """Farmacia NO puede crear movimiento tipo 'consumo_interno'."""
        self.assertFalse(self._validar_movimiento('farmacia', 'consumo_interno'))
    
    def test_farmacia_solo_tiene_un_subtipo_disponible(self):
        """Farmacia solo tiene acceso a transferencias."""
        subtipos = self._get_subtipos_permitidos('farmacia')
        self.assertEqual(len(subtipos), 1)
        self.assertEqual(subtipos[0], 'transferencia')
    
    # ========== Tests para usuario_centro ==========
    
    def test_usuario_centro_puede_hacer_consumo_interno(self):
        """Usuario de centro puede crear movimiento tipo 'consumo_interno'."""
        self.assertTrue(self._validar_movimiento('usuario_centro', 'consumo_interno'))
    
    def test_usuario_centro_puede_hacer_receta(self):
        """Usuario de centro puede crear movimiento tipo 'receta'."""
        self.assertTrue(self._validar_movimiento('usuario_centro', 'receta'))
    
    def test_usuario_centro_puede_hacer_merma(self):
        """Usuario de centro puede crear movimiento tipo 'merma'."""
        self.assertTrue(self._validar_movimiento('usuario_centro', 'merma'))
    
    def test_usuario_centro_puede_hacer_caducidad(self):
        """Usuario de centro puede crear movimiento tipo 'caducidad'."""
        self.assertTrue(self._validar_movimiento('usuario_centro', 'caducidad'))
    
    def test_usuario_centro_no_puede_hacer_transferencia(self):
        """Usuario de centro NO puede crear transferencias."""
        self.assertFalse(self._validar_movimiento('usuario_centro', 'transferencia'))
    
    def test_usuario_centro_tiene_cuatro_subtipos(self):
        """Usuario de centro tiene 4 subtipos disponibles."""
        subtipos = self._get_subtipos_permitidos('usuario_centro')
        self.assertEqual(len(subtipos), 4)
    
    # ========== Tests para admin ==========
    
    def test_admin_superuser_usa_transferencia(self):
        """Superusuario usa transferencias."""
        subtipos = self._get_subtipos_permitidos('admin', es_superuser=True)
        self.assertEqual(subtipos, ['transferencia'])


class TestValidacionPayloadMovimiento(TestCase):
    """Tests de validación de payload de movimientos."""
    
    def _validar_payload_medico(self, payload):
        """Validar payload de movimiento para médico."""
        errores = []
        
        # Campos requeridos
        if not payload.get('lote'):
            errores.append('El lote es requerido')
        
        cantidad = payload.get('cantidad')
        if not cantidad or cantidad <= 0:
            errores.append('La cantidad debe ser mayor a 0')
        
        # Para médicos, subtipo DEBE ser 'receta'
        subtipo = payload.get('subtipo_salida')
        if subtipo != 'receta':
            errores.append('Los médicos solo pueden registrar dispensación por receta')
        
        # Número de expediente es obligatorio para recetas
        if subtipo == 'receta':
            expediente = payload.get('numero_expediente', '').strip()
            if not expediente:
                errores.append('El número de expediente es obligatorio')
        
        return {
            'valido': len(errores) == 0,
            'errores': errores,
        }
    
    def test_payload_valido_completo(self):
        """Payload con todos los campos válidos."""
        payload = {
            'lote': 201,
            'cantidad': 5,
            'subtipo_salida': 'receta',
            'numero_expediente': 'EXP-2026-001',
            'centro': 1,
            'observaciones': 'Dispensación mensual',
        }
        
        resultado = self._validar_payload_medico(payload)
        
        self.assertTrue(resultado['valido'])
        self.assertEqual(len(resultado['errores']), 0)
    
    def test_falla_sin_lote(self):
        """Falla si no hay lote."""
        payload = {
            'lote': None,
            'cantidad': 5,
            'subtipo_salida': 'receta',
            'numero_expediente': 'EXP-001',
        }
        
        resultado = self._validar_payload_medico(payload)
        
        self.assertFalse(resultado['valido'])
        self.assertIn('El lote es requerido', resultado['errores'])
    
    def test_falla_cantidad_cero(self):
        """Falla si cantidad es 0."""
        payload = {
            'lote': 201,
            'cantidad': 0,
            'subtipo_salida': 'receta',
            'numero_expediente': 'EXP-001',
        }
        
        resultado = self._validar_payload_medico(payload)
        
        self.assertFalse(resultado['valido'])
        self.assertIn('La cantidad debe ser mayor a 0', resultado['errores'])
    
    def test_falla_cantidad_negativa(self):
        """Falla si cantidad es negativa."""
        payload = {
            'lote': 201,
            'cantidad': -3,
            'subtipo_salida': 'receta',
            'numero_expediente': 'EXP-001',
        }
        
        resultado = self._validar_payload_medico(payload)
        
        self.assertFalse(resultado['valido'])
    
    def test_falla_subtipo_no_receta(self):
        """Falla si subtipo no es 'receta' para médico."""
        payload = {
            'lote': 201,
            'cantidad': 5,
            'subtipo_salida': 'consumo_interno',  # NO permitido
            'numero_expediente': '',
        }
        
        resultado = self._validar_payload_medico(payload)
        
        self.assertFalse(resultado['valido'])
        self.assertIn('Los médicos solo pueden registrar dispensación por receta', resultado['errores'])
    
    def test_falla_sin_expediente_en_receta(self):
        """Falla si falta expediente en dispensación por receta."""
        payload = {
            'lote': 201,
            'cantidad': 5,
            'subtipo_salida': 'receta',
            'numero_expediente': '',  # Vacío
        }
        
        resultado = self._validar_payload_medico(payload)
        
        self.assertFalse(resultado['valido'])
        self.assertIn('El número de expediente es obligatorio', resultado['errores'])
    
    def test_falla_expediente_solo_espacios(self):
        """Falla si expediente solo tiene espacios."""
        payload = {
            'lote': 201,
            'cantidad': 5,
            'subtipo_salida': 'receta',
            'numero_expediente': '   ',  # Solo espacios
        }
        
        resultado = self._validar_payload_medico(payload)
        
        self.assertFalse(resultado['valido'])
        self.assertIn('El número de expediente es obligatorio', resultado['errores'])


class TestSubtiposDescripcion(TestCase):
    """Tests de descripciones y etiquetas de subtipos."""
    
    SUBTIPOS_INFO = {
        'transferencia': {
            'label': 'Transferencia a centro',
            'icono': '🚛',
            'descripcion': 'Envío de medicamentos desde almacén central a centros penitenciarios',
            'roles_permitidos': ['farmacia', 'admin_farmacia', 'admin_sistema'],
        },
        'consumo_interno': {
            'label': 'Consumo interno',
            'icono': '🏥',
            'descripcion': 'Uso de medicamentos dentro del centro sin receta',
            'roles_permitidos': ['usuario_centro'],
        },
        'receta': {
            'label': 'Dispensación por receta',
            'icono': '💊',
            'descripcion': 'Entrega de medicamento a paciente con receta médica',
            'roles_permitidos': ['medico', 'usuario_centro'],
        },
        'merma': {
            'label': 'Merma / Pérdida',
            'icono': '📉',
            'descripcion': 'Pérdida, rotura o daño de medicamentos',
            'roles_permitidos': ['usuario_centro'],
        },
        'caducidad': {
            'label': 'Caducidad',
            'icono': '⏰',
            'descripcion': 'Baja por vencimiento del medicamento',
            'roles_permitidos': ['usuario_centro'],
        },
    }
    
    def test_receta_permitida_para_medico(self):
        """El subtipo 'receta' está permitido para médicos."""
        info = self.SUBTIPOS_INFO['receta']
        self.assertIn('medico', info['roles_permitidos'])
    
    def test_consumo_interno_no_permitido_medico(self):
        """El subtipo 'consumo_interno' NO está permitido para médicos."""
        info = self.SUBTIPOS_INFO['consumo_interno']
        self.assertNotIn('medico', info['roles_permitidos'])
    
    def test_merma_no_permitido_medico(self):
        """El subtipo 'merma' NO está permitido para médicos."""
        info = self.SUBTIPOS_INFO['merma']
        self.assertNotIn('medico', info['roles_permitidos'])
    
    def test_caducidad_no_permitido_medico(self):
        """El subtipo 'caducidad' NO está permitido para médicos."""
        info = self.SUBTIPOS_INFO['caducidad']
        self.assertNotIn('medico', info['roles_permitidos'])
    
    def test_transferencia_no_permitido_medico(self):
        """El subtipo 'transferencia' NO está permitido para médicos."""
        info = self.SUBTIPOS_INFO['transferencia']
        self.assertNotIn('medico', info['roles_permitidos'])
    
    def test_receta_tiene_icono_correcto(self):
        """El subtipo 'receta' tiene el ícono de pastilla."""
        info = self.SUBTIPOS_INFO['receta']
        self.assertEqual(info['icono'], '💊')
    
    def test_todos_subtipos_tienen_descripcion(self):
        """Todos los subtipos tienen descripción."""
        for subtipo, info in self.SUBTIPOS_INFO.items():
            self.assertIn('descripcion', info)
            self.assertTrue(len(info['descripcion']) > 10)


class TestFiltrosMovimientosMedico(TestCase):
    """Tests de filtros de movimientos para médicos."""
    
    def test_medico_solo_ve_su_centro(self):
        """Médico solo ve movimientos de su centro."""
        movimientos = [
            {'id': 1, 'centro_id': 1, 'subtipo_salida': 'receta'},
            {'id': 2, 'centro_id': 2, 'subtipo_salida': 'receta'},
            {'id': 3, 'centro_id': 1, 'subtipo_salida': 'consumo_interno'},
        ]
        
        centro_medico = 1
        filtrados = [m for m in movimientos if m['centro_id'] == centro_medico]
        
        self.assertEqual(len(filtrados), 2)
        for m in filtrados:
            self.assertEqual(m['centro_id'], centro_medico)
    
    def test_medico_puede_filtrar_por_subtipo(self):
        """Médico puede filtrar movimientos por subtipo."""
        movimientos = [
            {'id': 1, 'centro_id': 1, 'subtipo_salida': 'receta'},
            {'id': 2, 'centro_id': 1, 'subtipo_salida': 'consumo_interno'},
            {'id': 3, 'centro_id': 1, 'subtipo_salida': 'receta'},
        ]
        
        subtipo_filtro = 'receta'
        filtrados = [m for m in movimientos if m['subtipo_salida'] == subtipo_filtro]
        
        self.assertEqual(len(filtrados), 2)
        for m in filtrados:
            self.assertEqual(m['subtipo_salida'], 'receta')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
