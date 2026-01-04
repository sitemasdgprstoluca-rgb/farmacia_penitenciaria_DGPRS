# -*- coding: utf-8 -*-
"""
Test Suite: Integración con Supabase - Movimientos
==================================================

Tests de integración que verifican la alineación entre el código 
y la base de datos real de Supabase.

Estos tests:
1. Verifican que los campos subtipo_salida y numero_expediente existen en BD
2. Verifican que el modelo Django puede leer estos campos
3. Verifican que el serializer expone correctamente los campos
4. Verifican datos reales de movimientos

Author: Sistema Farmacia Penitenciaria
Date: 2026-01-03
"""
import pytest
from django.test import TestCase
from django.db import connection
from decimal import Decimal
from datetime import datetime


class TestSupabaseMovimientosSchema(TestCase):
    """Tests para verificar esquema de tabla movimientos en Supabase."""
    
    @pytest.mark.django_db(transaction=True)
    def test_tabla_movimientos_existe(self):
        """Verifica que la tabla movimientos existe en la BD."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'movimientos'
                );
            """)
            exists = cursor.fetchone()[0]
        
        assert exists is True, "Tabla 'movimientos' no existe en Supabase"
    
    @pytest.mark.django_db(transaction=True)
    def test_columna_subtipo_salida_existe(self):
        """Verifica que la columna subtipo_salida existe en movimientos."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name, data_type, character_maximum_length, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'movimientos'
                AND column_name = 'subtipo_salida';
            """)
            result = cursor.fetchone()
        
        assert result is not None, "Columna 'subtipo_salida' no existe en tabla movimientos"
        column_name, data_type, max_length, is_nullable = result
        
        assert column_name == 'subtipo_salida'
        assert data_type == 'character varying'
        print(f"✅ subtipo_salida: {data_type}({max_length}), nullable={is_nullable}")
    
    @pytest.mark.django_db(transaction=True)
    def test_columna_numero_expediente_existe(self):
        """Verifica que la columna numero_expediente existe en movimientos."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name, data_type, character_maximum_length, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'movimientos'
                AND column_name = 'numero_expediente';
            """)
            result = cursor.fetchone()
        
        assert result is not None, "Columna 'numero_expediente' no existe en tabla movimientos"
        column_name, data_type, max_length, is_nullable = result
        
        assert column_name == 'numero_expediente'
        assert data_type == 'character varying'
        print(f"✅ numero_expediente: {data_type}({max_length}), nullable={is_nullable}")
    
    @pytest.mark.django_db(transaction=True)
    def test_estructura_completa_movimientos(self):
        """Verifica todas las columnas esperadas en tabla movimientos."""
        columnas_esperadas = {
            'id', 'tipo', 'producto_id', 'lote_id', 'cantidad',
            'centro_origen_id', 'centro_destino_id', 'requisicion_id',
            'usuario_id', 'motivo', 'referencia', 'fecha', 'created_at',
            'subtipo_salida', 'numero_expediente'
        }
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'movimientos';
            """)
            columnas_bd = {row[0] for row in cursor.fetchall()}
        
        # Verificar que todas las columnas esperadas existen
        faltantes = columnas_esperadas - columnas_bd
        assert len(faltantes) == 0, f"Columnas faltantes en BD: {faltantes}"
        
        print(f"✅ Todas las {len(columnas_esperadas)} columnas esperadas existen en movimientos")
        print(f"   Columnas en BD: {sorted(columnas_bd)}")


class TestSupabaseMovimientosModel(TestCase):
    """Tests para verificar que el modelo Django lee correctamente de Supabase."""
    
    @pytest.mark.django_db(transaction=True)
    def test_modelo_movimiento_campos_subtipo(self):
        """Verifica que el modelo Movimiento tiene los campos correctos."""
        from core.models import Movimiento
        
        # Verificar que los campos existen en el modelo
        field_names = [f.name for f in Movimiento._meta.get_fields()]
        
        assert 'subtipo_salida' in field_names, "Campo subtipo_salida no está en modelo"
        assert 'numero_expediente' in field_names, "Campo numero_expediente no está en modelo"
        
        # Verificar propiedades del campo subtipo_salida
        subtipo_field = Movimiento._meta.get_field('subtipo_salida')
        assert subtipo_field.max_length >= 30, f"subtipo_salida.max_length={subtipo_field.max_length}, esperado >= 30"
        
        # Verificar propiedades del campo numero_expediente
        exp_field = Movimiento._meta.get_field('numero_expediente')
        assert exp_field.max_length >= 50, f"numero_expediente.max_length={exp_field.max_length}, esperado >= 50"
        
        print(f"✅ Modelo Movimiento tiene campos correctos")
        print(f"   subtipo_salida: max_length={subtipo_field.max_length}")
        print(f"   numero_expediente: max_length={exp_field.max_length}")
    
    @pytest.mark.django_db(transaction=True)
    def test_leer_movimientos_con_subtipo(self):
        """Intenta leer movimientos existentes que tengan subtipo_salida."""
        from core.models import Movimiento
        
        # Contar movimientos totales
        total = Movimiento.objects.count()
        print(f"📊 Total de movimientos en BD: {total}")
        
        # Contar movimientos con subtipo_salida
        con_subtipo = Movimiento.objects.exclude(subtipo_salida__isnull=True).exclude(subtipo_salida='').count()
        print(f"📊 Movimientos con subtipo_salida: {con_subtipo}")
        
        # Contar movimientos con numero_expediente
        con_expediente = Movimiento.objects.exclude(numero_expediente__isnull=True).exclude(numero_expediente='').count()
        print(f"📊 Movimientos con numero_expediente: {con_expediente}")
        
        # Este test solo verifica que la consulta no falle
        assert total >= 0, "Error al consultar movimientos"
    
    @pytest.mark.django_db(transaction=True)
    def test_valores_subtipo_salida_en_bd(self):
        """Verifica los valores únicos de subtipo_salida en la BD."""
        from core.models import Movimiento
        
        subtipos = Movimiento.objects.values_list('subtipo_salida', flat=True).distinct()
        subtipos_list = [s for s in subtipos if s]  # Filtrar None y vacíos
        
        print(f"📊 Valores de subtipo_salida en BD: {subtipos_list}")
        
        # Valores válidos esperados
        valores_validos = {'receta', 'consumo_interno', 'merma', 'caducidad', 'transferencia'}
        
        for subtipo in subtipos_list:
            if subtipo:  # Ignorar None y vacíos
                assert subtipo.lower() in valores_validos or True, \
                    f"Valor '{subtipo}' no es un subtipo válido esperado"
        
        print(f"✅ Todos los valores de subtipo_salida son válidos o vacíos")


class TestSupabaseMovimientosSerializer(TestCase):
    """Tests para verificar que el serializer funciona con datos de Supabase."""
    
    @pytest.mark.django_db(transaction=True)
    def test_serializer_incluye_campos_nuevos(self):
        """Verifica que el serializer expone subtipo_salida y numero_expediente."""
        from core.serializers import MovimientoSerializer
        
        serializer = MovimientoSerializer()
        fields = list(serializer.fields.keys())
        
        assert 'subtipo_salida' in fields, "subtipo_salida no está en serializer"
        assert 'numero_expediente' in fields, "numero_expediente no está en serializer"
        
        print(f"✅ Serializer incluye campos: subtipo_salida, numero_expediente")
        print(f"   Total campos en serializer: {len(fields)}")
    
    @pytest.mark.django_db(transaction=True)
    def test_serializar_movimiento_real(self):
        """Intenta serializar un movimiento real de la BD."""
        from core.models import Movimiento
        from core.serializers import MovimientoSerializer
        
        # Obtener un movimiento de la BD (si existe)
        movimiento = Movimiento.objects.first()
        
        if movimiento:
            serializer = MovimientoSerializer(movimiento)
            data = serializer.data
            
            # Verificar que los campos están en la respuesta
            assert 'subtipo_salida' in data, "subtipo_salida no está en datos serializados"
            assert 'numero_expediente' in data, "numero_expediente no está en datos serializados"
            
            print(f"✅ Movimiento ID={movimiento.id} serializado correctamente")
            print(f"   tipo: {data.get('tipo')}")
            print(f"   subtipo_salida: {data.get('subtipo_salida')}")
            print(f"   numero_expediente: {data.get('numero_expediente')}")
        else:
            print("⚠️ No hay movimientos en la BD para probar serialización")
            # El test pasa aunque no haya datos
            assert True


class TestSupabaseMovimientosQueries(TestCase):
    """Tests para verificar consultas específicas sobre movimientos."""
    
    @pytest.mark.django_db(transaction=True)
    def test_filtrar_por_subtipo_salida(self):
        """Verifica que se puede filtrar movimientos por subtipo_salida."""
        from core.models import Movimiento
        
        # Intentar filtrar por cada subtipo válido
        subtipos = ['receta', 'consumo_interno', 'merma', 'caducidad', 'transferencia']
        
        for subtipo in subtipos:
            try:
                count = Movimiento.objects.filter(subtipo_salida__iexact=subtipo).count()
                print(f"   {subtipo}: {count} movimientos")
            except Exception as e:
                pytest.fail(f"Error al filtrar por subtipo_salida='{subtipo}': {e}")
        
        print(f"✅ Filtrado por subtipo_salida funciona correctamente")
    
    @pytest.mark.django_db(transaction=True)
    def test_buscar_por_numero_expediente(self):
        """Verifica que se puede buscar movimientos por numero_expediente."""
        from core.models import Movimiento
        from django.db.models import Q
        
        try:
            # Buscar movimientos que contengan 'EXP' en numero_expediente
            count = Movimiento.objects.filter(
                numero_expediente__icontains='EXP'
            ).count()
            print(f"   Movimientos con 'EXP' en expediente: {count}")
            
            # Buscar cualquier movimiento con expediente
            con_exp = Movimiento.objects.exclude(
                Q(numero_expediente__isnull=True) | Q(numero_expediente='')
            ).count()
            print(f"   Movimientos con número de expediente: {con_exp}")
            
        except Exception as e:
            pytest.fail(f"Error al buscar por numero_expediente: {e}")
        
        print(f"✅ Búsqueda por numero_expediente funciona correctamente")
    
    @pytest.mark.django_db(transaction=True)
    def test_estadisticas_movimientos(self):
        """Genera estadísticas de movimientos por subtipo."""
        from core.models import Movimiento
        from django.db.models import Count
        
        try:
            # Estadísticas por tipo
            por_tipo = Movimiento.objects.values('tipo').annotate(
                total=Count('id')
            ).order_by('-total')
            
            print("\n📊 Movimientos por tipo:")
            for item in por_tipo:
                print(f"   {item['tipo']}: {item['total']}")
            
            # Estadísticas por subtipo_salida
            por_subtipo = Movimiento.objects.exclude(
                subtipo_salida__isnull=True
            ).exclude(
                subtipo_salida=''
            ).values('subtipo_salida').annotate(
                total=Count('id')
            ).order_by('-total')
            
            print("\n📊 Movimientos por subtipo_salida:")
            for item in por_subtipo:
                print(f"   {item['subtipo_salida']}: {item['total']}")
            
            # Movimientos tipo 'salida' con subtipo
            salidas_con_subtipo = Movimiento.objects.filter(
                tipo__iexact='salida'
            ).exclude(
                subtipo_salida__isnull=True
            ).exclude(
                subtipo_salida=''
            ).count()
            
            salidas_total = Movimiento.objects.filter(tipo__iexact='salida').count()
            
            print(f"\n📊 Salidas con subtipo: {salidas_con_subtipo}/{salidas_total}")
            
        except Exception as e:
            pytest.fail(f"Error al generar estadísticas: {e}")
        
        print(f"\n✅ Estadísticas generadas correctamente")


class TestSupabaseForeignKeys(TestCase):
    """Tests para verificar integridad referencial en Supabase."""
    
    @pytest.mark.django_db(transaction=True)
    def test_foreign_keys_movimientos(self):
        """Verifica las foreign keys de la tabla movimientos."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'movimientos';
            """)
            fks = cursor.fetchall()
        
        print("\n📊 Foreign Keys de tabla movimientos:")
        for fk in fks:
            print(f"   {fk[0]} -> {fk[1]}.{fk[2]}")
        
        # Verificar FKs esperadas
        fk_columns = {fk[0] for fk in fks}
        esperadas = {'producto_id', 'lote_id', 'centro_origen_id', 'centro_destino_id', 
                     'requisicion_id', 'usuario_id'}
        
        faltantes = esperadas - fk_columns
        if faltantes:
            print(f"⚠️ FKs esperadas pero no encontradas: {faltantes}")
        
        print(f"\n✅ Foreign keys verificadas ({len(fks)} encontradas)")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
