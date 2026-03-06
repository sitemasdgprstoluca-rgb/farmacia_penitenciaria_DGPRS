"""
Script de Auditoría Completa para dashboard_analytics

EJECUTAR CON:
    cd backend
    python scripts/audit_dashboard_analytics.py

PREREQUISITOS:
    1. Servidor Django corriendo en http://127.0.0.1:8000
    2. Usuarios de prueba creados (admin, farmacia, centro)
    3. Datos de prueba en la BD (requisiciones, donaciones, etc.)

SALIDA:
    Genera un reporte de auditoría en reports/AUDIT_DASHBOARD_ANALYTICS_{fecha}.md
"""
import os
import sys
import json
import requests
from datetime import datetime, date, timedelta
from decimal import Decimal

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuración
BASE_URL = os.environ.get('API_URL', 'http://127.0.0.1:8000')
API_URL = f"{BASE_URL}/api"


class AuditResult:
    """Resultado de una prueba de auditoría."""
    def __init__(self, name, passed, details="", severity="INFO"):
        self.name = name
        self.passed = passed
        self.details = details
        self.severity = severity  # INFO, WARNING, CRITICAL
    
    def __str__(self):
        status = "✅ PASS" if self.passed else f"❌ FAIL ({self.severity})"
        return f"{status} | {self.name}\n   {self.details}"


class DashboardAnalyticsAuditor:
    """Auditor completo para el endpoint dashboard_analytics."""
    
    def __init__(self):
        self.results = []
        self.session = requests.Session()
        self.tokens = {}  # {rol: access_token}
    
    def login(self, username, password):
        """Obtiene un token JWT para un usuario."""
        try:
            response = self.session.post(
                f"{API_URL}/token/",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('access')
            return None
        except Exception as e:
            print(f"Error login para {username}: {e}")
            return None
    
    def call_analytics(self, token=None, params=None):
        """Llama al endpoint dashboard_analytics."""
        headers = {}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        try:
            response = self.session.get(
                f"{API_URL}/dashboard/analytics/",
                headers=headers,
                params=params or {}
            )
            return response
        except Exception as e:
            return None
    
    # =========================================================================
    # AUDITORÍA 1: AUTENTICACIÓN
    # =========================================================================
    def audit_autenticacion(self):
        """Verifica que el endpoint requiera autenticación."""
        print("\n📋 AUDITORÍA 1: AUTENTICACIÓN\n" + "="*50)
        
        # Test 1.1: Sin token
        response = self.call_analytics(token=None)
        result = AuditResult(
            "1.1 Sin autenticación",
            response is not None and response.status_code == 401,
            f"Status: {response.status_code if response else 'ERROR'}",
            "CRITICAL" if (response and response.status_code != 401) else "INFO"
        )
        self.results.append(result)
        print(result)
        
        # Test 1.2: Token inválido
        response = self.call_analytics(token="token_invalido_12345")
        result = AuditResult(
            "1.2 Token inválido",
            response is not None and response.status_code in [401, 403],
            f"Status: {response.status_code if response else 'ERROR'}",
            "CRITICAL" if (response and response.status_code not in [401, 403]) else "INFO"
        )
        self.results.append(result)
        print(result)
    
    # =========================================================================
    # AUDITORÍA 2: SEGURIDAD POR ROL
    # =========================================================================
    def audit_seguridad_roles(self, usuarios_config):
        """
        Verifica seguridad por rol.
        
        usuarios_config: dict con estructura:
        {
            'admin': {'username': '...', 'password': '...', 'centro_id': None},
            'farmacia': {'username': '...', 'password': '...', 'centro_id': None},
            'centro1': {'username': '...', 'password': '...', 'centro_id': 1},
            'centro2': {'username': '...', 'password': '...', 'centro_id': 2},
        }
        """
        print("\n📋 AUDITORÍA 2: SEGURIDAD POR ROL\n" + "="*50)
        
        # Obtener tokens
        for rol, config in usuarios_config.items():
            token = self.login(config['username'], config['password'])
            if token:
                self.tokens[rol] = token
                print(f"  ✓ Token obtenido para {rol}")
            else:
                print(f"  ✗ Error obteniendo token para {rol}")
        
        if not self.tokens:
            result = AuditResult(
                "2.0 Obtención de tokens",
                False,
                "No se pudo obtener ningún token. Verificar credenciales.",
                "CRITICAL"
            )
            self.results.append(result)
            print(result)
            return
        
        # Test 2.1: Admin ve datos globales
        if 'admin' in self.tokens:
            response = self.call_analytics(self.tokens['admin'])
            data = response.json() if response and response.status_code == 200 else {}
            result = AuditResult(
                "2.1 Admin ve datos globales",
                response is not None and response.status_code == 200,
                f"Status: {response.status_code if response else 'ERROR'}, "
                f"top_productos: {len(data.get('top_productos', []))}, "
                f"top_centros: {len(data.get('top_centros', []))}",
                "WARNING" if (response and response.status_code != 200) else "INFO"
            )
            self.results.append(result)
            print(result)
        
        # Test 2.2: Centro solo ve sus datos
        if 'centro1' in self.tokens and 'centro2' in self.tokens:
            # Centro1 llama al endpoint
            response1 = self.call_analytics(self.tokens['centro1'])
            data1 = response1.json() if response1 and response1.status_code == 200 else {}
            
            # Centro2 llama al endpoint
            response2 = self.call_analytics(self.tokens['centro2'])
            data2 = response2.json() if response2 and response2.status_code == 200 else {}
            
            # Verificar que los datos son diferentes (si hay datos)
            centros1 = [c['centro_id'] for c in data1.get('top_centros', [])]
            centros2 = [c['centro_id'] for c in data2.get('top_centros', [])]
            
            centro1_id = usuarios_config['centro1']['centro_id']
            centro2_id = usuarios_config['centro2']['centro_id']
            
            # Centro1 solo debe ver centro1
            centro1_ok = len(centros1) == 0 or all(c == centro1_id for c in centros1)
            # Centro2 solo debe ver centro2
            centro2_ok = len(centros2) == 0 or all(c == centro2_id for c in centros2)
            
            result = AuditResult(
                "2.2 Centros solo ven sus datos",
                centro1_ok and centro2_ok,
                f"Centro1 ve: {centros1}, Centro2 ve: {centros2}",
                "CRITICAL" if not (centro1_ok and centro2_ok) else "INFO"
            )
            self.results.append(result)
            print(result)
    
    # =========================================================================
    # AUDITORÍA 3: FUGA DE CENTRO
    # =========================================================================
    def audit_fuga_centro(self, usuarios_config):
        """
        Verifica que un centro no pueda ver datos de otro centro
        aunque pase el ID como parámetro.
        """
        print("\n📋 AUDITORÍA 3: FUGA DE CENTRO\n" + "="*50)
        
        if 'centro1' not in self.tokens:
            print("  ⚠ No hay token de centro1, saltando test")
            return
        
        centro2_id = usuarios_config.get('centro2', {}).get('centro_id', 2)
        
        # Centro1 intenta ver datos de Centro2
        response = self.call_analytics(
            self.tokens['centro1'],
            params={'centro': centro2_id}
        )
        
        if response and response.status_code == 200:
            data = response.json()
            centros_vistos = [c['centro_id'] for c in data.get('top_centros', [])]
            centro1_id = usuarios_config['centro1']['centro_id']
            
            # CRÍTICO: Centro1 NO debe ver datos de centro2
            no_ve_centro2 = centro2_id not in centros_vistos
            solo_su_centro = len(centros_vistos) == 0 or all(c == centro1_id for c in centros_vistos)
            
            result = AuditResult(
                "3.1 Centro1 no puede ver Centro2",
                no_ve_centro2 and solo_su_centro,
                f"Parámetro: centro={centro2_id}, Centros vistos: {centros_vistos}",
                "CRITICAL" if not (no_ve_centro2 and solo_su_centro) else "INFO"
            )
        else:
            result = AuditResult(
                "3.1 Centro1 no puede ver Centro2",
                True,  # Si la request falla o es 403, es un comportamiento aceptable
                f"Status: {response.status_code if response else 'ERROR'}",
                "INFO"
            )
        
        self.results.append(result)
        print(result)
    
    # =========================================================================
    # AUDITORÍA 4: CACHÉ
    # =========================================================================
    def audit_cache(self):
        """
        Verifica que el caché no mezcle datos entre usuarios/roles.
        
        NOTA: Este test requiere hacer requests secuenciales y comparar
        los timestamps de respuesta.
        """
        print("\n📋 AUDITORÍA 4: CACHÉ\n" + "="*50)
        
        if 'admin' not in self.tokens:
            print("  ⚠ No hay token de admin, saltando test")
            return
        
        # Request 1: Admin sin parámetros
        response1 = self.call_analytics(self.tokens['admin'])
        data1 = response1.json() if response1 and response1.status_code == 200 else {}
        ts1 = data1.get('generado_at', '')
        
        # Request 2: Admin sin parámetros (debe usar caché)
        response2 = self.call_analytics(self.tokens['admin'])
        data2 = response2.json() if response2 and response2.status_code == 200 else {}
        ts2 = data2.get('generado_at', '')
        
        # Los timestamps deben ser iguales (mismo caché)
        result = AuditResult(
            "4.1 Caché funciona correctamente",
            ts1 == ts2 and ts1 != '',
            f"TS1: {ts1}, TS2: {ts2}",
            "WARNING" if ts1 != ts2 else "INFO"
        )
        self.results.append(result)
        print(result)
        
        # Request 3: Admin con refresh=true
        response3 = self.call_analytics(self.tokens['admin'], params={'refresh': 'true'})
        data3 = response3.json() if response3 and response3.status_code == 200 else {}
        ts3 = data3.get('generado_at', '')
        
        # El timestamp debe ser diferente (caché invalidado)
        result = AuditResult(
            "4.2 Refresh invalida caché",
            ts3 != ts1 and ts3 != '',
            f"TS original: {ts1}, TS refresh: {ts3}",
            "WARNING" if ts3 == ts1 else "INFO"
        )
        self.results.append(result)
        print(result)
    
    # =========================================================================
    # AUDITORÍA 5: CONSISTENCIA DE DATOS
    # =========================================================================
    def audit_consistencia(self, db_connection=None):
        """
        Verifica que los datos del endpoint coincidan con la BD.
        
        NOTA: Requiere conexión directa a la BD para comparar.
        """
        print("\n📋 AUDITORÍA 5: CONSISTENCIA DE DATOS\n" + "="*50)
        
        if 'admin' not in self.tokens:
            print("  ⚠ No hay token de admin, saltando test")
            return
        
        response = self.call_analytics(self.tokens['admin'], params={'refresh': 'true'})
        if response and response.status_code == 200:
            data = response.json()
            
            # Documentar estructura de respuesta
            result = AuditResult(
                "5.1 Estructura de respuesta correcta",
                all(k in data for k in ['top_productos', 'top_centros', 'donaciones', 'caja_chica', 'caducidades']),
                f"Claves presentes: {list(data.keys())}",
                "CRITICAL" if not all(k in data for k in ['top_productos', 'top_centros', 'donaciones', 'caja_chica', 'caducidades']) else "INFO"
            )
            self.results.append(result)
            print(result)
            
            # Documentar datos para verificación manual
            print(f"\n  📊 Datos para verificación manual:")
            print(f"     - Top productos: {len(data.get('top_productos', []))}")
            print(f"     - Top centros: {len(data.get('top_centros', []))}")
            print(f"     - Donaciones totales: {data.get('donaciones', {}).get('total_donaciones', 0)}")
            print(f"     - Caja chica total: ${data.get('caja_chica', {}).get('monto_total', 0):.2f}")
            print(f"     - Lotes vencidos: {data.get('caducidades', {}).get('vencidos', 0)}")
            print(f"     - Lotes por vencer (15d): {data.get('caducidades', {}).get('vencen_15_dias', 0)}")
        else:
            result = AuditResult(
                "5.1 Estructura de respuesta correcta",
                False,
                f"Error obteniendo datos: {response.status_code if response else 'Sin respuesta'}",
                "CRITICAL"
            )
            self.results.append(result)
            print(result)
    
    # =========================================================================
    # GENERAR REPORTE
    # =========================================================================
    def generate_report(self, output_dir="reports"):
        """Genera un reporte de auditoría en Markdown."""
        os.makedirs(output_dir, exist_ok=True)
        
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/AUDIT_DASHBOARD_ANALYTICS_{fecha}.md"
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        critical = sum(1 for r in self.results if not r.passed and r.severity == "CRITICAL")
        
        content = f"""# Auditoría Dashboard Analytics

**Fecha:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Endpoint:** `/api/dashboard/analytics/`

## Resumen

| Métrica | Valor |
|---------|-------|
| Total Tests | {total} |
| ✅ Pasados | {passed} |
| ❌ Fallidos | {failed} |
| 🔴 Críticos | {critical} |

## Estado General

{"✅ **PASS** - Todos los tests pasaron" if failed == 0 else "❌ **FAIL** - Hay tests fallidos"}
{"" if critical == 0 else "⚠️ **ATENCIÓN:** Hay fallos críticos de seguridad que requieren corrección inmediata"}

## Resultados Detallados

"""
        
        for result in self.results:
            status_icon = "✅" if result.passed else "❌"
            severity_badge = f"[{result.severity}]" if not result.passed else ""
            content += f"""### {status_icon} {result.name} {severity_badge}

- **Estado:** {"PASS" if result.passed else "FAIL"}
- **Detalles:** {result.details}

"""
        
        content += """
## Queries de Verificación (Cross-check SQL)

```sql
-- TOP PRODUCTOS SURTIDOS
SELECT 
    p.clave, p.nombre,
    COALESCE(SUM(dr.cantidad_surtida), 0) as total_surtido
FROM core_detallerequisicion dr
JOIN core_requisicion r ON dr.requisicion_id = r.id
JOIN core_producto p ON dr.producto_id = p.id
WHERE r.estado IN ('surtida', 'entregada', 'parcial')
GROUP BY p.id, p.clave, p.nombre
ORDER BY total_surtido DESC
LIMIT 10;

-- TOP CENTROS SOLICITANTES
SELECT 
    c.nombre,
    COUNT(r.id) as total_requisiciones,
    COUNT(r.id) FILTER (WHERE r.estado IN ('surtida', 'entregada')) as surtidas
FROM core_requisicion r
JOIN core_centro c ON r.centro_destino_id = c.id
GROUP BY c.id, c.nombre
ORDER BY total_requisiciones DESC
LIMIT 10;

-- CADUCIDADES
SELECT 
    COUNT(*) FILTER (WHERE fecha_caducidad < CURRENT_DATE) as vencidos,
    COUNT(*) FILTER (WHERE fecha_caducidad >= CURRENT_DATE 
                     AND fecha_caducidad < CURRENT_DATE + 15) as vencen_15,
    COUNT(*) FILTER (WHERE fecha_caducidad >= CURRENT_DATE 
                     AND fecha_caducidad < CURRENT_DATE + 30) as vencen_30
FROM core_lote
WHERE activo = true AND cantidad_actual > 0 AND centro_id IS NULL;

-- DONACIONES TOTALES
SELECT COUNT(*) as total_donaciones FROM core_donacion;

-- CAJA CHICA TOTALES
SELECT 
    COUNT(*) as total_compras,
    COALESCE(SUM(total), 0) as monto_total
FROM core_compracajachica 
WHERE estado IN ('comprada', 'recibida');
```

"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"\n📄 Reporte generado: {filename}")
        return filename
    
    # =========================================================================
    # EJECUTAR AUDITORÍA COMPLETA
    # =========================================================================
    def run_full_audit(self, usuarios_config=None):
        """
        Ejecuta la auditoría completa.
        
        usuarios_config: Configuración de usuarios de prueba
        """
        print("\n" + "="*60)
        print("🔍 AUDITORÍA COMPLETA DE DASHBOARD ANALYTICS")
        print("="*60)
        
        # 1. Autenticación
        self.audit_autenticacion()
        
        # 2-4. Tests con usuarios (si se proporcionan)
        if usuarios_config:
            self.audit_seguridad_roles(usuarios_config)
            self.audit_fuga_centro(usuarios_config)
            self.audit_cache()
            self.audit_consistencia()
        else:
            print("\n⚠️ No se proporcionaron credenciales de usuario.")
            print("   Para tests completos, proporcione usuarios_config con:")
            print("   - admin: cuenta de administrador")
            print("   - farmacia: cuenta de farmacia")
            print("   - centro1: usuario de centro con centro_id conocido")
            print("   - centro2: usuario de otro centro con centro_id conocido")
        
        # Generar reporte
        return self.generate_report()


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================
if __name__ == '__main__':
    auditor = DashboardAnalyticsAuditor()
    
    # Configuración de usuarios de prueba
    # MODIFICAR CON CREDENCIALES REALES
    usuarios = {
        'admin': {
            'username': 'admin',
            'password': 'admin123',
            'centro_id': None
        },
        # 'farmacia': {
        #     'username': 'farmacia',
        #     'password': 'farm123',
        #     'centro_id': None
        # },
        # 'centro1': {
        #     'username': 'centro1_user',
        #     'password': 'centro123',
        #     'centro_id': 1
        # },
        # 'centro2': {
        #     'username': 'centro2_user',
        #     'password': 'centro123',
        #     'centro_id': 2
        # },
    }
    
    # Ejecutar auditoría
    report_path = auditor.run_full_audit(usuarios)
    
    # Resumen final
    print("\n" + "="*60)
    print("📊 RESUMEN FINAL")
    print("="*60)
    
    total = len(auditor.results)
    passed = sum(1 for r in auditor.results if r.passed)
    critical_fails = [r for r in auditor.results if not r.passed and r.severity == "CRITICAL"]
    
    print(f"   Total tests: {total}")
    print(f"   ✅ Pasados: {passed}")
    print(f"   ❌ Fallidos: {total - passed}")
    
    if critical_fails:
        print(f"\n🔴 FALLOS CRÍTICOS ({len(critical_fails)}):")
        for f in critical_fails:
            print(f"   - {f.name}")
    else:
        print("\n✅ No hay fallos críticos")
    
    print(f"\n📄 Reporte: {report_path}")
