"""
ViewSets para la API REST del sistema de farmacia penitenciaria
"""

from rest_framework import viewsets, status, filters, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from datetime import date, timedelta
from io import BytesIO
import openpyxl
import logging
import requests

from core.models import (
    User, Centro, Producto, Lote, Requisicion, DetalleRequisicion,
    Movimiento, AuditoriaLog, ImportacionLog, Notificacion, UserProfile,
    ConfiguracionSistema
)
from core.utils.pdf_reports import generar_reporte_auditoria, generar_reporte_trazabilidad
from core.serializers import (
    UserSerializer, CentroSerializer, UserMeSerializer,
    ProductoSerializer, LoteSerializer, RequisicionSerializer,
    DetalleRequisicionSerializer, MovimientoSerializer,
    AuditoriaLogSerializer, ImportacionLogSerializer, NotificacionSerializer,
    ConfiguracionSistemaSerializer
)
from core.permissions import (
    IsFarmaciaRole, IsCentroUser, CanAuthorizeRequisicion, CanViewNotifications, 
    CanViewProfile, IsVistaRole, IsSuperuserOnly
)
from django.conf import settings

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000


# ============================================
# THROTTLING - CLASES DE RATE LIMITING
# ============================================

class LoginThrottle(AnonRateThrottle):
    """Rate limit específico para login: 5 intentos por minuto por IP."""
    scope = 'login'


class PasswordChangeThrottle(UserRateThrottle):
    """Rate limit para cambio de contraseña: 3 intentos por minuto."""
    scope = 'password_change'


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet para gestion de usuarios"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name', 'adscripcion']
    ordering_fields = ['username', 'date_joined']
    ordering = ['-date_joined']
    
    def _apply_filters(self, queryset, params):
        """Aplica filtros comunes a queryset de usuarios"""
        # Filtro por rol
        rol = params.get('rol')
        if rol:
            queryset = queryset.filter(rol=rol)
        
        # Filtro por estado activo/inactivo
        is_active = params.get('is_active')
        if is_active is not None:
            if is_active in ['true', 'True', '1', True]:
                queryset = queryset.filter(is_active=True)
            elif is_active in ['false', 'False', '0', False]:
                queryset = queryset.filter(is_active=False)
        
        # Filtro por centro
        centro = params.get('centro')
        if centro:
            queryset = queryset.filter(centro_id=centro)
        
        return queryset

    def get_serializer_class(self):
        if self.action in ['me', 'me_change_password']:
            return UserMeSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        """
        Permisos por acción:
        - me, me_change_password: Cualquier autenticado
        - list, retrieve: Autenticado (queryset filtra según rol)
        - create, update, destroy, cambiar_password: Solo FARMACIA/Admin
        """
        if self.action in ['me', 'me_change_password']:
            return [IsAuthenticated(), CanViewProfile()]
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'cambiar_password', 
                           'exportar_excel', 'importar_excel']:
            return [IsAuthenticated(), IsFarmaciaRole()]
        return [IsAuthenticated()]

    def _is_farmacia_or_admin(self, user):
        """Verifica si el usuario es farmacia o admin"""
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        rol = (getattr(user, 'rol', '') or '').lower()
        if rol in ['admin_sistema', 'superusuario', 'farmacia', 'admin_farmacia']:
            return True
        group_names = set(g.name.upper() for g in user.groups.all())
        return bool({'FARMACIA_ADMIN', 'FARMACIA', 'ADMIN'} & group_names)

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or self._is_farmacia_or_admin(user):
            qs = User.objects.all()
        else:
            # Usuario no admin solo ve usuarios de su centro (o solo a sí mismo si no tiene centro)
            if hasattr(user, 'centro') and user.centro:
                qs = User.objects.filter(centro=user.centro)
            else:
                qs = User.objects.filter(id=user.id)
        
        # Aplicar filtros server-side
        qs = self._apply_filters(qs, self.request.query_params)
        
        return qs.select_related('centro')

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        """GET/PATCH /api/usuarios/me/ - Perfil del usuario autenticado"""
        try:
            UserProfile.objects.get_or_create(user=request.user)
        except Exception as e:
            # Si la tabla user_profiles no existe, continuar sin profile
            logger.warning(f"No se pudo crear UserProfile para {request.user}: {e}")
        
        if request.method == 'PATCH':
            # Guardar datos anteriores para auditoría
            old_data = {
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
            }
            profile = getattr(request.user, 'profile', None)
            if profile:
                old_data['telefono'] = profile.telefono
                old_data['cargo'] = profile.cargo
            
            serializer = UserMeSerializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            # Detectar cambios para auditoría
            new_data = {
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
            }
            profile = getattr(request.user, 'profile', None)
            if profile:
                new_data['telefono'] = profile.telefono
                new_data['cargo'] = profile.cargo
            
            cambios = {k: (old_data.get(k), new_data.get(k)) 
                      for k in new_data if old_data.get(k) != new_data.get(k)}
            
            if cambios:
                AuditoriaLog.objects.create(
                    usuario=request.user,
                    accion='UPDATE',
                    modelo='Usuario',
                    objeto_id=str(request.user.id),
                    datos_nuevos=cambios,
                    detalles={'objeto_repr': str(request.user)}
                )
            
            updated_user = User.objects.select_related('profile').get(pk=request.user.pk)
            updated = UserMeSerializer(updated_user)
            return Response(updated.data)
        else:
            serializer = UserMeSerializer(request.user)
            return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='me/change-password', throttle_classes=[PasswordChangeThrottle])
    def me_change_password(self, request):
        """
        POST /api/usuarios/me/change-password/
        
        Cambio de contraseña del usuario autenticado.
        Requiere: old_password, new_password, confirm_password
        
        Validaciones:
        - Contraseña actual correcta
        - Nueva contraseña ≥8 caracteres
        - Al menos una mayúscula
        - Al menos un número
        - Diferente a la anterior
        """
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not all([old_password, new_password, confirm_password]):
            return Response({'error': 'Debe proporcionar old_password, new_password y confirm_password'}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({'error': 'Las contraseñas nuevas no coinciden'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(old_password):
            logger.warning("Intento de cambio de contraseña fallido para %s: contraseña actual incorrecta", user.username)
            # Registrar intento fallido en auditoría
            AuditoriaLog.objects.create(
                usuario=user,
                accion='UPDATE',
                modelo='Usuario',
                objeto_id=str(user.id),
                detalles={'objeto_repr': str(user), 'razon': 'Contraseña actual incorrecta', 'resultado': 'fallido'}
            )
            return Response({'error': 'Contraseña actual incorrecta'}, status=status.HTTP_400_BAD_REQUEST)

        # Validaciones de complejidad (unificadas con cambiar_password)
        if len(new_password) < 8:
            return Response({'error': 'La nueva contraseña debe tener al menos 8 caracteres'}, status=status.HTTP_400_BAD_REQUEST)

        if not any(c.isupper() for c in new_password):
            return Response({'error': 'La nueva contraseña debe tener al menos una mayúscula'}, status=status.HTTP_400_BAD_REQUEST)

        if not any(c.isdigit() for c in new_password):
            return Response({'error': 'La nueva contraseña debe tener al menos un número'}, status=status.HTTP_400_BAD_REQUEST)

        if old_password == new_password:
            return Response({'error': 'La nueva contraseña debe ser diferente a la anterior'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        
        # Registrar cambio exitoso en auditoría
        AuditoriaLog.objects.create(
            usuario=user,
            accion='UPDATE',
            modelo='Usuario',
            objeto_id=str(user.id),
            detalles={'objeto_repr': str(user), 'resultado': 'Contraseña actualizada exitosamente'}
        )
        
        logger.info("Contraseña actualizada para usuario %s", user.username)
        return Response({'message': 'Contraseña actualizada exitosamente'})

    @action(detail=True, methods=['post'], url_path='cambiar-password')
    def cambiar_password(self, request, pk=None):
        """POST /api/usuarios/{id}/cambiar-password/ - Admin cambia password de otro usuario"""
        # Solo superusuarios o farmacia pueden cambiar passwords de otros
        if not request.user.is_superuser and request.user.rol not in ['admin_sistema', 'farmacia', 'admin_farmacia']:
            return Response({'error': 'No tiene permisos para cambiar contraseñas de otros usuarios'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            usuario = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        # No permitir cambiar password de superusuarios (solo otro superuser puede)
        if usuario.is_superuser and not request.user.is_superuser:
            return Response({'error': 'No puede cambiar la contraseña de un superusuario'}, status=status.HTTP_403_FORBIDDEN)
        
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response({'error': 'Debe proporcionar new_password'}, status=status.HTTP_400_BAD_REQUEST)
        
        if len(new_password) < 8:
            return Response({'error': 'La contraseña debe tener al menos 8 caracteres'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar complejidad mínima
        if not any(c.isupper() for c in new_password):
            return Response({'error': 'La contraseña debe tener al menos una mayúscula'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not any(c.isdigit() for c in new_password):
            return Response({'error': 'La contraseña debe tener al menos un número'}, status=status.HTTP_400_BAD_REQUEST)
        
        usuario.set_password(new_password)
        usuario.save()
        
        # Registrar en auditoría
        AuditoriaLog.objects.create(
            usuario=request.user,
            accion='UPDATE',
            modelo='User',
            objeto_id=str(usuario.id),
            detalles={'objeto_repr': usuario.username, 'cambiado_por': request.user.username},
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        logger.info("Contraseña de usuario %s actualizada por %s", usuario.username, request.user.username)
        return Response({'message': f'Contraseña de {usuario.username} actualizada exitosamente'})

    @action(detail=False, methods=['get'], url_path='exportar-excel')
    def exportar_excel(self, request):
        """GET /api/usuarios/exportar_excel/ - Exporta usuarios a Excel
        
        Acepta los mismos filtros que el listado:
        - search: búsqueda en username, email, first_name, last_name, adscripcion
        - rol: filtrar por rol específico
        - is_active: true/false para filtrar por estado
        - centro: ID del centro para filtrar
        """
        import openpyxl
        from openpyxl.styles import Font, PatternFill
        from django.http import HttpResponse
        from django.db.models import Q
        
        # Admin y Farmacia pueden exportar usuarios
        if not request.user.is_superuser and request.user.rol not in ['admin_sistema', 'farmacia', 'admin_farmacia']:
            return Response({'error': 'No tiene permisos para exportar usuarios'}, status=status.HTTP_403_FORBIDDEN)
        
        # Obtener queryset base según permisos del usuario
        user = request.user
        if user.is_superuser or self._is_farmacia_or_admin(user):
            usuarios = User.objects.all()
        else:
            # Usuario no admin solo puede exportar usuarios de su centro
            if hasattr(user, 'centro') and user.centro:
                usuarios = User.objects.filter(centro=user.centro)
            else:
                usuarios = User.objects.filter(id=user.id)
        
        # Aplicar filtros server-side (mismos que el listado)
        usuarios = self._apply_filters(usuarios, request.query_params)
        
        # Aplicar búsqueda de texto (igual que search_fields)
        search = request.query_params.get('search', '').strip()
        if search:
            usuarios = usuarios.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(adscripcion__icontains=search)
            )
        
        usuarios = usuarios.select_related('centro').order_by('username')
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Usuarios'
        
        headers = ['#', 'Usuario', 'Email', 'Nombre', 'Apellidos', 'Rol', 'Centro', 'Activo', 'Fecha Registro']
        ws.append(headers)
        
        header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
        for idx, u in enumerate(usuarios, start=1):
            ws.append([
                idx,
                u.username,
                u.email,
                u.first_name,
                u.last_name,
                u.rol or 'Sin rol',
                u.centro.nombre if u.centro else '-',
                'Si' if u.is_active else 'No',
                u.date_joined.strftime('%Y-%m-%d %H:%M') if u.date_joined else '-'
            ])
        
        for col in ws.columns:
            max_length = max(len(str(cell.value or '')) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 50)
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=usuarios_{timezone.now().strftime("%Y%m%d")}.xlsx'
        wb.save(response)
        return response

    @action(detail=False, methods=['post'], url_path='importar-excel')
    def importar_excel(self, request):
        """POST /api/usuarios/importar-excel/ - Importa usuarios desde Excel
        
        Columnas esperadas:
        - username (requerido, único, se normaliza a minúsculas)
        - email (opcional, se genera si falta)
        - first_name (opcional)
        - last_name (opcional)
        - rol (opcional: admin, farmacia, centro, vista; default: centro)
        - password (opcional, mín 8 chars; default: temporal que requiere cambio)
        - centro_clave (opcional: clave del centro a asignar)
        
        SEGURIDAD:
        - Tamaño máximo de archivo: 5MB
        - Máximo de filas: 1000
        - Solo archivos .xlsx
        - Usernames normalizados a minúsculas
        - Contraseñas temporales NO se exponen en respuesta
        """
        import openpyxl
        import re
        from .models import Centro
        
        # === VALIDACIÓN DE PERMISOS ===
        if not request.user.is_superuser and request.user.rol not in ['admin_sistema', 'farmacia', 'admin_farmacia']:
            return Response({'error': 'No tiene permisos para importar usuarios'}, status=status.HTTP_403_FORBIDDEN)
        
        archivo = request.FILES.get('file')
        if not archivo:
            return Response({'error': 'No se recibió archivo'}, status=status.HTTP_400_BAD_REQUEST)
        
        # === VALIDACIÓN DE ARCHIVO (ISS-001) ===
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
        MAX_ROWS = 1000
        ALLOWED_EXTENSIONS = ['.xlsx']
        
        # Validar tamaño
        if archivo.size > MAX_FILE_SIZE:
            return Response(
                {'error': f'Archivo demasiado grande. Máximo permitido: {MAX_FILE_SIZE // (1024*1024)}MB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar extensión
        file_ext = '.' + archivo.name.split('.')[-1].lower() if '.' in archivo.name else ''
        if file_ext not in ALLOWED_EXTENSIONS:
            return Response(
                {'error': f'Tipo de archivo no permitido. Solo se aceptan: {ALLOWED_EXTENSIONS}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar contenido (magic bytes para xlsx/zip)
        archivo.seek(0)
        header = archivo.read(4)
        archivo.seek(0)
        if header[:4] != b'PK\x03\x04':  # ZIP/XLSX magic bytes
            return Response(
                {'error': 'El archivo no parece ser un Excel válido (.xlsx)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # === CONSTANTES DE VALIDACIÓN ===
        ROLES_VALIDOS = ['admin_sistema', 'admin_farmacia', 'farmacia', 'centro', 'vista', 'usuario_normal', 'usuario_vista']
        USERNAME_PATTERN = re.compile(r'^[a-z0-9_.-]{3,50}$')
        EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        try:
            wb = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
            ws = wb.active
            
            # Contar filas antes de procesar
            row_count = sum(1 for _ in ws.iter_rows(min_row=2, max_row=MAX_ROWS + 2, values_only=True))
            if row_count > MAX_ROWS:
                return Response(
                    {'error': f'Demasiadas filas. Máximo permitido: {MAX_ROWS}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Reabrir para procesar (read_only no permite re-iterar)
            archivo.seek(0)
            wb = openpyxl.load_workbook(archivo)
            ws = wb.active
            
            creados = 0
            actualizados = 0
            errores = []
            usuarios_con_reset = 0  # Solo conteo, NO exponemos contraseñas (ISS-002)
            cambios_auditoria = []  # Para logging de cambios masivos
            
            with transaction.atomic():
                for row_idx, row in enumerate(ws.iter_rows(min_row=2, max_row=MAX_ROWS + 1, values_only=True), start=2):
                    valores = list(row) + [None] * 10
                    
                    # === EXTRACCIÓN Y NORMALIZACIÓN (ISS-003) ===
                    username_raw = str(valores[0] or '').strip()
                    username = username_raw.lower()  # Normalizar a minúsculas
                    email = str(valores[1] or '').strip().lower()
                    first_name = str(valores[2] or '').strip()[:100]  # Limitar longitud
                    last_name = str(valores[3] or '').strip()[:100]
                    rol = str(valores[4] or 'centro').strip().lower()
                    password = str(valores[5] or '').strip()
                    centro_clave = str(valores[6] or '').strip().upper()
                    
                    # Saltar filas vacías
                    if not username:
                        continue
                    
                    # === VALIDACIONES ESTRICTAS ===
                    
                    # Validar formato de username
                    if not USERNAME_PATTERN.match(username):
                        errores.append({
                            'fila': row_idx, 
                            'campo': 'username',
                            'error': f'Username "{username}" inválido. Solo letras minúsculas, números, guiones y puntos (3-50 chars)'
                        })
                        continue
                    
                    # Validar rol estrictamente (NO usar default silencioso)
                    if rol not in ROLES_VALIDOS:
                        errores.append({
                            'fila': row_idx,
                            'campo': 'rol', 
                            'error': f'Rol "{rol}" no válido. Roles permitidos: {ROLES_VALIDOS}'
                        })
                        continue
                    
                    # Validar email si se proporciona
                    if email and not EMAIL_PATTERN.match(email):
                        errores.append({
                            'fila': row_idx,
                            'campo': 'email',
                            'error': f'Email "{email}" no tiene formato válido'
                        })
                        continue
                    
                    # Buscar centro si se proporcionó
                    centro = None
                    if centro_clave:
                        centro = Centro.objects.filter(clave__iexact=centro_clave, activo=True).first()
                        if not centro:
                            errores.append({
                                'fila': row_idx,
                                'campo': 'centro_clave',
                                'error': f'Centro "{centro_clave}" no encontrado o inactivo'
                            })
                            continue
                    
                    # Generar password seguro si no se proporciona o es débil
                    requiere_reset = False
                    if not password or len(password) < 8:
                        import secrets
                        import string
                        chars = string.ascii_letters + string.digits + '!@#$%&*'
                        password = ''.join(secrets.choice(chars) for _ in range(12))
                        requiere_reset = True
                    
                    # === CREAR O ACTUALIZAR USUARIO ===
                    try:
                        # Buscar case-insensitive para evitar duplicados (ISS-003)
                        existing_user = User.objects.filter(username__iexact=username).first()
                        
                        if existing_user is None:
                            # Crear nuevo usuario
                            user = User.objects.create(
                                username=username,
                                email=email or f'{username}@sistema.local',
                                first_name=first_name,
                                last_name=last_name,
                                rol=rol,
                                centro=centro,
                                is_active=True,
                                activo=True,
                            )
                            user.set_password(password)
                            user.save()
                            creados += 1
                            if requiere_reset:
                                usuarios_con_reset += 1
                            
                            cambios_auditoria.append({
                                'accion': 'crear',
                                'username': username,
                                'rol': rol,
                                'centro': centro_clave or None
                            })
                        else:
                            # Actualizar usuario existente - registrar cambios
                            cambios = []
                            if email and existing_user.email != email:
                                cambios.append(f'email: {existing_user.email} -> {email}')
                                existing_user.email = email
                            if first_name and existing_user.first_name != first_name:
                                existing_user.first_name = first_name
                            if last_name and existing_user.last_name != last_name:
                                existing_user.last_name = last_name
                            if existing_user.rol != rol:
                                cambios.append(f'rol: {existing_user.rol} -> {rol}')
                                existing_user.rol = rol
                            if centro and existing_user.centro != centro:
                                cambios.append(f'centro: {existing_user.centro} -> {centro}')
                                existing_user.centro = centro
                            
                            existing_user.save()
                            actualizados += 1
                            
                            if cambios:
                                cambios_auditoria.append({
                                    'accion': 'actualizar',
                                    'username': username,
                                    'cambios': cambios
                                })
                                
                    except Exception as e:
                        logger.error(f"Error procesando fila {row_idx}: {e}")
                        errores.append({
                            'fila': row_idx,
                            'campo': 'general',
                            'error': f'Error al procesar: {str(e)[:100]}'
                        })
                
                # Registrar auditoría de importación masiva
                if cambios_auditoria:
                    logger.info(
                        f"Importación masiva por {request.user.username}: "
                        f"{creados} creados, {actualizados} actualizados, {len(errores)} errores"
                    )
            
            # === RESPUESTA SIN CONTRASEÑAS (ISS-002) ===
            return Response({
                'mensaje': 'Importación completada exitosamente',
                'resumen': {
                    'creados': creados,
                    'actualizados': actualizados,
                    'errores': len(errores),
                    'usuarios_requieren_cambio_password': usuarios_con_reset
                },
                # NO incluimos contraseñas - deben gestionarse por canal seguro
                'errores': errores[:20],  # Limitar errores mostrados
                'nota': (
                    f'{usuarios_con_reset} usuarios fueron creados con contraseña temporal. '
                    'Las credenciales deben entregarse por un canal seguro (NO por esta API). '
                    'Los usuarios deberán cambiar su contraseña en el primer inicio de sesión.'
                ) if usuarios_con_reset > 0 else None,
                'advertencia': (
                    'Se encontraron errores en algunas filas. Revise el detalle y corrija el archivo.'
                ) if errores else None
            })
            
        except openpyxl.utils.exceptions.InvalidFileException:
            return Response(
                {'error': 'El archivo no es un Excel válido o está corrupto'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error al importar usuarios: {e}")
            return Response(
                {'error': 'Error inesperado al procesar archivo. Contacte al administrador.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# NOTA: ProductoViewSet, LoteViewSet, RequisicionViewSet y CentroViewSet
# están en inventario/views.py para evitar duplicación.
# Importar desde allí si es necesario.


class DetalleRequisicionViewSet(viewsets.ModelViewSet):
    """ViewSet para detalles de requisiciones"""
    queryset = DetalleRequisicion.objects.all()
    serializer_class = DetalleRequisicionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination


class AuditoriaLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para registros de auditoria (solo lectura)"""
    queryset = AuditoriaLog.objects.all()
    serializer_class = AuditoriaLogSerializer
    # Solo Superuser/Admin puede leer el log de auditoría.
    permission_classes = [IsSuperuserOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['modelo', 'usuario__username', 'accion']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        """Filtrado avanzado por parámetros de query"""
        queryset = AuditoriaLog.objects.select_related('usuario').all()
        
        # Filtro por acción
        accion = self.request.query_params.get('accion')
        if accion:
            queryset = queryset.filter(accion=accion)
        
        # Filtro por modelo
        modelo = self.request.query_params.get('modelo')
        if modelo:
            queryset = queryset.filter(modelo__icontains=modelo)
        
        # Filtro por usuario
        usuario = self.request.query_params.get('usuario')
        if usuario:
            queryset = queryset.filter(
                Q(usuario__username__icontains=usuario) |
                Q(usuario__first_name__icontains=usuario) |
                Q(usuario__last_name__icontains=usuario)
            )
        
        # Filtro por fecha inicio
        fecha_inicio = self.request.query_params.get('fecha_inicio')
        if fecha_inicio:
            queryset = queryset.filter(timestamp__date__gte=fecha_inicio)
        
        # Filtro por fecha fin
        fecha_fin = self.request.query_params.get('fecha_fin')
        if fecha_fin:
            queryset = queryset.filter(timestamp__date__lte=fecha_fin)
        
        return queryset

    @action(detail=False, methods=['get'])
    def exportar(self, request):
        """
        Exporta logs de auditoría a Excel.
        GET /api/auditoria/exportar/
        """
        try:
            logs = self.get_queryset()[:5000]  # Limitar a 5000 registros
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Auditoria'
            
            # Título
            ws.merge_cells('A1:G1')
            titulo = ws['A1']
            titulo.value = 'REPORTE DE AUDITORÍA'
            titulo.font = openpyxl.styles.Font(bold=True, size=14, color='632842')
            titulo.alignment = openpyxl.styles.Alignment(horizontal='center', vertical='center')
            
            ws.merge_cells('A2:G2')
            fecha = ws['A2']
            fecha.value = f'Generado el {timezone.now().strftime("%d/%m/%Y %H:%M")}'
            fecha.font = openpyxl.styles.Font(size=10, italic=True)
            fecha.alignment = openpyxl.styles.Alignment(horizontal='center')
            
            ws.append([])
            
            # Encabezados
            headers = ['#', 'Fecha', 'Usuario', 'Acción', 'Modelo', 'Objeto', 'IP']
            ws.append(headers)
            
            header_fill = openpyxl.styles.PatternFill(start_color='632842', end_color='632842', fill_type='solid')
            header_font = openpyxl.styles.Font(bold=True, color='FFFFFF', size=11)
            for cell in ws[4]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = openpyxl.styles.Alignment(horizontal='center', vertical='center')
            
            # Datos
            for idx, log in enumerate(logs, 1):
                objeto_repr = ''
                if log.detalles and isinstance(log.detalles, dict):
                    objeto_repr = log.detalles.get('objeto_repr', '')
                if not objeto_repr:
                    objeto_repr = f"{log.modelo} #{log.objeto_id}" if log.objeto_id else log.modelo
                
                ws.append([
                    idx,
                    log.timestamp.strftime('%d/%m/%Y %H:%M:%S') if log.timestamp else '',
                    log.usuario.username if log.usuario else 'Sistema',
                    log.accion,
                    log.modelo,
                    str(objeto_repr)[:100],
                    log.ip_address or ''
                ])
            
            # Ajustar anchos
            ws.column_dimensions['A'].width = 8
            ws.column_dimensions['B'].width = 20
            ws.column_dimensions['C'].width = 15
            ws.column_dimensions['D'].width = 12
            ws.column_dimensions['E'].width = 20
            ws.column_dimensions['F'].width = 50
            ws.column_dimensions['G'].width = 15
            
            from django.http import HttpResponse
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename=Auditoria_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            wb.save(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error al exportar auditoría: {e}")
            return Response({
                'error': 'Error al exportar auditoría',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='exportar-pdf')
    def exportar_pdf(self, request):
        """
        Exporta logs de auditoría a PDF con fondo institucional.
        GET /api/auditoria/exportar-pdf/
        
        Ideal para reportes oficiales de auditoría y cumplimiento normativo.
        """
        try:
            logs = self.get_queryset()[:2000]  # Limitar para PDFs
            
            # Preparar datos para el generador
            auditoria_data = []
            for log in logs:
                objeto_repr = ''
                if log.detalles and isinstance(log.detalles, dict):
                    objeto_repr = log.detalles.get('objeto_repr', '')
                if not objeto_repr:
                    objeto_repr = f"{log.modelo} #{log.objeto_id}" if log.objeto_id else log.modelo
                
                auditoria_data.append({
                    'fecha': log.timestamp,
                    'usuario': log.usuario.username if log.usuario else 'Sistema',
                    'accion': log.accion,
                    'modelo': log.modelo,
                    'objeto_repr': objeto_repr,
                    'ip_address': log.ip_address or ''
                })
            
            # Filtros aplicados
            filtros = {
                'fecha_inicio': request.query_params.get('fecha_inicio'),
                'fecha_fin': request.query_params.get('fecha_fin'),
                'usuario': request.query_params.get('usuario'),
                'accion': request.query_params.get('accion'),
                'modelo': request.query_params.get('modelo'),
            }
            filtros = {k: v for k, v in filtros.items() if v}
            
            # Generar PDF
            pdf_buffer = generar_reporte_auditoria(auditoria_data, filtros)
            
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename=Auditoria_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            return response
            
        except Exception as e:
            logger.error(f"Error al exportar auditoría PDF: {e}")
            return Response({
                'error': 'Error al exportar auditoría',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def opciones_filtro(self, request):
        """
        Devuelve opciones para filtros de auditoría.
        GET /api/auditoria/opciones_filtro/
        
        Retorna:
        - acciones: Lista de acciones únicas registradas
        - modelos: Lista de modelos auditados
        """
        from .constants import ACCIONES_AUDITORIA, MODELOS_AUDITADOS
        
        # Acciones que realmente existen en la base de datos
        acciones_db = list(
            AuditoriaLog.objects.values_list('accion', flat=True)
            .distinct()
            .order_by('accion')
        )
        
        # Modelos que realmente existen en la base de datos
        modelos_db = list(
            AuditoriaLog.objects.values_list('modelo', flat=True)
            .distinct()
            .order_by('modelo')
        )
        
        return Response({
            'acciones': acciones_db,
            'modelos': modelos_db,
            'catalogo_acciones': dict(ACCIONES_AUDITORIA),
            'catalogo_modelos': MODELOS_AUDITADOS
        })


class ImportacionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para registros de importacion (solo lectura)"""
    queryset = ImportacionLog.objects.all()
    serializer_class = ImportacionLogSerializer
    permission_classes = [IsAuthenticated, IsFarmaciaRole]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['modelo', 'usuario__username', 'estado']
    ordering_fields = ['fecha_creacion']
    ordering = ['-fecha_creacion']


class NotificacionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    """
    ViewSet para notificaciones del usuario.
    
    Las notificaciones son generadas automáticamente por el sistema:
    - Cambios de estado en requisiciones
    - Alertas de stock crítico
    - Alertas de lotes por caducar
    
    Endpoints:
    - GET /api/notificaciones/ - Lista notificaciones del usuario
    - GET /api/notificaciones/{id}/ - Detalle de notificación
    - DELETE /api/notificaciones/{id}/ - Eliminar notificación propia
    - POST /api/notificaciones/{id}/marcar-leida/ - Marcar como leída
    - POST /api/notificaciones/marcar-todas-leidas/ - Marcar todas como leídas
    - GET /api/notificaciones/no-leidas-count/ - Contador de no leídas
    """
    http_method_names = ['get', 'post', 'delete', 'head', 'options']
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated, CanViewNotifications]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['fecha_creacion']
    ordering = ['-fecha_creacion']

    def get_queryset(self):
        queryset = Notificacion.objects.filter(usuario=self.request.user)
        tipo = self.request.query_params.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo=tipo)

        leida = self.request.query_params.get('leida')
        if leida in ['true', 'false']:
            queryset = queryset.filter(leida=leida == 'true')

        fecha_desde = self.request.query_params.get('desde')
        fecha_hasta = self.request.query_params.get('hasta')
        try:
            if fecha_desde:
                queryset = queryset.filter(fecha_creacion__date__gte=fecha_desde)
            if fecha_hasta:
                queryset = queryset.filter(fecha_creacion__date__lte=fecha_hasta)
        except Exception:
            pass

        return queryset

    @action(detail=True, methods=['post'], url_path='marcar-leida')
    def marcar_leida(self, request, pk=None):
        """POST /api/notificaciones/{id}/marcar-leida/"""
        notificacion = self.get_object()
        notificacion.leida = True
        notificacion.save()
        return Response({'leida': True})

    @action(detail=False, methods=['post'], url_path='marcar-todas-leidas')
    def marcar_todas_leidas(self, request):
        """
        POST /api/notificaciones/marcar-todas-leidas/
        
        Marca como leídas las notificaciones que coinciden con los filtros actuales.
        Respeta los query params: tipo, desde, hasta, leida.
        Solo afecta las notificaciones del usuario autenticado (get_queryset ya filtra).
        """
        # get_queryset() ya aplica filtros de tipo, desde, hasta, leida y usuario
        updated = self.get_queryset().filter(leida=False).update(leida=True)
        return Response({'marcadas': updated})

    @action(detail=False, methods=['get'], url_path='no-leidas-count')
    def no_leidas_count(self, request):
        """GET /api/notificaciones/no-leidas-count/"""
        count = self.get_queryset().filter(leida=False).count()
        return Response({'no_leidas': count})
    
    def destroy(self, request, *args, **kwargs):
        """
        Eliminar notificación propia.
        
        Cualquier usuario autenticado puede eliminar sus propias notificaciones.
        El queryset ya filtra por usuario, así que solo pueden borrar las suyas.
        """
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {'error': f'No se pudo eliminar la notificación: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class ReportesViewSet(viewsets.ViewSet):
    """ViewSet para reportes del sistema"""
    permission_classes = [IsAuthenticated, IsFarmaciaRole]

    @method_decorator(cache_page(60 * 5))  # Cache 5 minutos
    @action(detail=False, methods=['get'])
    def inventario(self, request):
        """GET /api/reportes/inventario/?formato=excel|pdf|json"""
        from django.http import FileResponse
        from core.utils.pdf_reports import generar_reporte_inventario
        
        formato = request.query_params.get('formato', 'json')

        queryset = Producto.objects.select_related('created_by').prefetch_related('lotes')

        datos = []
        for producto in queryset:
            stock_actual = producto.get_stock_actual()
            nivel = producto.get_nivel_stock()
            datos.append({
                'id': producto.id,
                'clave': producto.clave,
                'descripcion': producto.descripcion,
                'unidad_medida': producto.unidad_medida,
                'stock_actual': stock_actual,
                'stock_minimo': producto.stock_minimo,
                'nivel_stock': nivel,
                'nivel': nivel,  # Alias para compatibilidad frontend
                'precio_unitario': float(producto.precio_unitario),
                'valor_inventario': float(stock_actual * producto.precio_unitario),
                'lotes_activos': producto.lotes.filter(estado='disponible').count()
            })

        # Calcular productos bajo mínimo (stock_actual < stock_minimo)
        productos_bajo_minimo = sum(
            1 for d in datos 
            if d['stock_actual'] < d['stock_minimo'] and d['stock_minimo'] > 0
        )
        
        resumen = {
            'total_productos': len(datos),
            'stock_total': sum(d['stock_actual'] for d in datos),
            'productos_sin_stock': sum(1 for d in datos if d['stock_actual'] == 0),
            'productos_bajo_minimo': productos_bajo_minimo,
            'productos_stock_critico': sum(1 for d in datos if d['nivel_stock'] == 'critico'),
            'valor_total_inventario': sum(d['valor_inventario'] for d in datos)
        }

        if formato == 'pdf':
            pdf_buffer = generar_reporte_inventario(datos)
            return FileResponse(
                pdf_buffer,
                content_type='application/pdf',
                as_attachment=True,
                filename=f'reporte_inventario_{timezone.now().strftime("%Y%m%d")}.pdf'
            )

        if formato == 'excel':
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.title = 'Inventario'

            headers = ['Clave', 'Descripcion', 'Stock Actual', 'Stock Minimo', 'Nivel', 'Precio Unitario', 'Valor Total']
            sheet.append(headers)

            for d in datos:
                sheet.append([
                    d['clave'],
                    d['descripcion'],
                    d['stock_actual'],
                    d['stock_minimo'],
                    d['nivel_stock'],
                    d['precio_unitario'],
                    d['valor_inventario']
                ])

            for row in sheet.iter_rows(min_row=1, max_row=len(datos) + 1):
                for cell in row:
                    cell.alignment = openpyxl.styles.Alignment(horizontal='center')

            buffer = BytesIO()
            workbook.save(buffer)
            buffer.seek(0)

            return FileResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                filename='reporte_inventario.xlsx'
            )

        return Response({
            'reporte': 'inventario',
            'fecha_generacion': timezone.now().isoformat(),
            'datos': datos,
            'resumen': resumen
        })

    @method_decorator(cache_page(60 * 5))  # Cache 5 minutos
    @action(detail=False, methods=['get'])
    def caducidades(self, request):
        """GET /api/reportes/caducidades/?dias=30&formato=json|pdf"""
        from django.http import FileResponse
        from core.utils.pdf_reports import generar_reporte_caducidades
        
        dias = int(request.query_params.get('dias', 30))
        formato = request.query_params.get('formato', 'json')
        fecha_limite = date.today() + timedelta(days=dias)

        lotes = Lote.objects.filter(
            fecha_caducidad__lte=fecha_limite,
            estado__in=['disponible', 'critico', 'proximo'],
            deleted_at__isnull=True
        ).select_related('producto').order_by('fecha_caducidad')

        datos = []
        for lote in lotes:
            dias_restantes = lote.dias_para_caducar()
            datos.append({
                'id': lote.id,
                'producto_clave': lote.producto.clave,
                'producto_descripcion': lote.producto.descripcion,
                'numero_lote': lote.numero_lote,
                'fecha_caducidad': lote.fecha_caducidad.isoformat(),
                'dias_restantes': dias_restantes,
                'alerta': lote.alerta_caducidad(),
                'cantidad_actual': lote.cantidad_actual,
                'proveedor': lote.proveedor
            })

        resumen = {
            'total_lotes_proximos': len(datos),
            'lotes_vencidos': sum(1 for d in datos if d['alerta'] == 'vencido'),
            'lotes_criticos': sum(1 for d in datos if d['alerta'] == 'critico'),
            'lotes_proximos': sum(1 for d in datos if d['alerta'] == 'proximo')
        }

        if formato == 'pdf':
            pdf_buffer = generar_reporte_caducidades(datos, dias=dias)
            return FileResponse(
                pdf_buffer,
                content_type='application/pdf',
                as_attachment=True,
                filename=f'reporte_caducidades_{timezone.now().strftime("%Y%m%d")}.pdf'
            )

        return Response({
            'reporte': 'caducidades',
            'fecha_generacion': timezone.now().isoformat(),
            'datos': datos,
            'resumen': resumen
        })

    @method_decorator(cache_page(60 * 10))  # Cache 10 minutos
    @action(detail=False, methods=['get'])
    def requisiciones(self, request):
        """GET /api/reportes/requisiciones/?formato=json|pdf"""
        from django.http import FileResponse
        from core.utils.pdf_reports import generar_reporte_requisiciones
        
        formato = request.query_params.get('formato', 'json')
        estado = request.query_params.get('estado')
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')

        queryset = Requisicion.objects.select_related(
            'centro', 'usuario_solicita', 'usuario_autoriza'
        ).prefetch_related('detalles')

        filtros = {}
        if estado:
            queryset = queryset.filter(estado=estado)
            filtros['estado'] = estado

        if fecha_inicio:
            queryset = queryset.filter(fecha_solicitud__gte=fecha_inicio)
            filtros['fecha_inicio'] = fecha_inicio

        if fecha_fin:
            queryset = queryset.filter(fecha_solicitud__lte=fecha_fin)
            filtros['fecha_fin'] = fecha_fin

        datos = []
        for req in queryset:
            datos.append({
                'id': req.id,
                'folio': req.folio,
                'centro_nombre': req.centro.nombre,
                'estado': req.estado,
                'fecha_solicitud': req.fecha_solicitud.isoformat(),
                'total_items': req.detalles.count(),
                'usuario_solicita': req.usuario_solicita.username
            })

        if formato == 'pdf':
            pdf_buffer = generar_reporte_requisiciones(datos, filtros=filtros)
            return FileResponse(
                pdf_buffer,
                content_type='application/pdf',
                as_attachment=True,
                filename=f'reporte_requisiciones_{timezone.now().strftime("%Y%m%d")}.pdf'
            )

        return Response({
            'reporte': 'requisiciones',
            'fecha_generacion': timezone.now().isoformat(),
            'datos': datos
        })


# ============================================
# AUTENTICACION JWT
# ============================================

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    View personalizado para login que retorna tokens + datos del usuario.
    Usa CustomTokenObtainPairSerializer de serializers_jwt.py
    ✅ Incluye rate limiting para prevenir fuerza bruta.
    """
    from core.serializers_jwt import CustomTokenObtainPairSerializer
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]

    def _verify_captcha(self, token, remote_ip=None):
        """
        Valida el token de reCAPTCHA contra el servicio de Google.
        Retorna True si es válido o si la validación está deshabilitada.
        """
        if not settings.RECAPTCHA_ENABLED:
            return True
        secret = settings.RECAPTCHA_SECRET_KEY
        if not secret:
            logger.warning("RECAPTCHA_ENABLED sin RECAPTCHA_SECRET_KEY configurado")
            return False
        try:
            resp = requests.post(
                'https://www.google.com/recaptcha/api/siteverify',
                data={'secret': secret, 'response': token, 'remoteip': remote_ip},
                timeout=5
            )
            data = resp.json()
            return bool(data.get('success'))
        except Exception as exc:
            logger.error(f"Error verificando reCAPTCHA: {exc}")
            return False

    def post(self, request, *args, **kwargs):
        if settings.RECAPTCHA_ENABLED:
            captcha_token = request.data.get('captcha_token') or request.data.get('captcha')
            if not captcha_token:
                return Response({'error': 'Captcha requerido'}, status=status.HTTP_400_BAD_REQUEST)
            if not self._verify_captcha(captcha_token, request.META.get('REMOTE_ADDR')):
                return Response({'error': 'Captcha inválido'}, status=status.HTTP_400_BAD_REQUEST)
        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    """Endpoint para logout (blacklist del refresh token)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                # Si no se envía refresh, solo confirmamos logout
                # (el access token expirará naturalmente)
                return Response({"message": "Logout exitoso (access token invalidado)"}, status=status.HTTP_200_OK)
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logout exitoso (refresh blacklisted)"}, status=status.HTTP_200_OK)
        except Exception as e:
            # Si el refresh ya expiró o es inválido, igual consideramos logout exitoso
            return Response({"message": "Logout completado (refresh inválido/expirado)", "detail": str(e)}, status=status.HTTP_200_OK)


class DevAutoLoginView(APIView):
    """
    SOLO DESARROLLO: Autologin sin credenciales.
    Automaticamente deshabilitado en produccion (DEBUG=False).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from django.conf import settings
        if not settings.DEBUG:
            return Response(
                {'error': 'Este endpoint solo esta disponible en modo desarrollo'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        username = request.data.get('username', 'admin')
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {'error': f'Usuario {username} no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        })

# NOTA: UserProfileView eliminada - usar /api/usuarios/me/ del UserViewSet
# class UserProfileView eliminada (código muerto, duplicaba funcionalidad)


class ConfiguracionSistemaViewSet(viewsets.ViewSet):
    """
    ViewSet para la configuración global del sistema (colores del tema).
    
    GET  /api/configuracion/tema/  - Obtiene la configuración actual (público)
    PUT  /api/configuracion/tema/  - Actualiza la configuración (solo superusuario)
    POST /api/configuracion/tema/aplicar-tema/  - Aplica un tema predefinido (solo superusuario)
    POST /api/configuracion/tema/restablecer/    - Restablece al tema por defecto (solo superusuario)
    """
    
    def get_permissions(self):
        """
        GET es público (para cargar el tema al inicio).
        PUT, POST requieren superusuario.
        """
        if self.action == 'retrieve':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def retrieve(self, request, pk=None):
        """
        GET /api/configuracion/tema/
        Retorna la configuración actual del sistema.
        Público para que el frontend pueda cargar los colores al iniciar.
        """
        config = ConfiguracionSistema.get_config()
        serializer = ConfiguracionSistemaSerializer(config)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """
        PUT /api/configuracion/tema/
        Actualiza la configuración del sistema.
        Solo superusuarios pueden modificar.
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo superusuarios pueden modificar la configuración del sistema'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        config = ConfiguracionSistema.get_config()
        serializer = ConfiguracionSistemaSerializer(config, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            logger.info(f"Configuración del sistema actualizada por {request.user.username}")
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], url_path='aplicar-tema')
    def aplicar_tema(self, request):
        """
        POST /api/configuracion/tema/aplicar-tema/
        Aplica un tema predefinido (default, dark, green, purple).
        Body: { "tema": "dark" }
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo superusuarios pueden cambiar el tema'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        tema = request.data.get('tema')
        if not tema:
            return Response(
                {'error': 'Debe especificar el tema a aplicar'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        temas_validos = [t[0] for t in ConfiguracionSistema.TEMAS_PREDEFINIDOS if t[0] != 'custom']
        if tema not in temas_validos:
            return Response(
                {'error': f'Tema inválido. Opciones: {", ".join(temas_validos)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if ConfiguracionSistema.aplicar_tema_predefinido(tema):
            config = ConfiguracionSistema.get_config()
            config.updated_by = request.user
            config.save()
            serializer = ConfiguracionSistemaSerializer(config)
            logger.info(f"Tema '{tema}' aplicado por {request.user.username}")
            return Response({
                'mensaje': f'Tema "{tema}" aplicado correctamente',
                'configuracion': serializer.data
            })
        
        return Response(
            {'error': 'No se pudo aplicar el tema'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    @action(detail=False, methods=['post'], url_path='restablecer')
    def restablecer(self, request):
        """
        POST /api/configuracion/tema/restablecer/
        Restablece la configuración al tema por defecto.
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo superusuarios pueden restablecer la configuración'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        ConfiguracionSistema.aplicar_tema_predefinido('default')
        config = ConfiguracionSistema.get_config()
        config.updated_by = request.user
        config.save()
        
        serializer = ConfiguracionSistemaSerializer(config)
        logger.info(f"Configuración restablecida a valores por defecto por {request.user.username}")
        
        return Response({
            'mensaje': 'Configuración restablecida a valores por defecto',
            'configuracion': serializer.data
        })
    
    @action(detail=False, methods=['post'], url_path='subir-logo-header')
    def subir_logo_header(self, request):
        """
        POST /api/configuracion/tema/subir-logo-header/
        Sube el logo para el header de la interfaz.
        Acepta multipart/form-data con campo 'logo'.
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo superusuarios pueden subir logos'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        logo = request.FILES.get('logo')
        if not logo:
            return Response(
                {'error': 'Debe enviar un archivo en el campo "logo"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar tipo de archivo
        allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp']
        if logo.content_type not in allowed_types:
            return Response(
                {'error': 'Formato no válido. Use PNG, JPG o WebP'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar tamaño (max 500KB)
        if logo.size > 500 * 1024:
            return Response(
                {'error': 'El archivo no puede superar 500KB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        config = ConfiguracionSistema.get_config()
        # Eliminar logo anterior si existe
        if config.logo_header:
            config.logo_header.delete(save=False)
        
        config.logo_header = logo
        config.updated_by = request.user
        config.save()
        
        serializer = ConfiguracionSistemaSerializer(config, context={'request': request})
        logger.info(f"Logo header actualizado por {request.user.username}")
        
        return Response({
            'mensaje': 'Logo del header actualizado correctamente',
            'configuracion': serializer.data
        })
    
    @action(detail=False, methods=['post'], url_path='subir-logo-pdf')
    def subir_logo_pdf(self, request):
        """
        POST /api/configuracion/tema/subir-logo-pdf/
        Sube el logo/fondo institucional para reportes PDF.
        Acepta multipart/form-data con campo 'logo'.
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo superusuarios pueden subir logos'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        logo = request.FILES.get('logo')
        if not logo:
            return Response(
                {'error': 'Debe enviar un archivo en el campo "logo"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar tipo de archivo
        allowed_types = ['image/png', 'image/jpeg', 'image/jpg']
        if logo.content_type not in allowed_types:
            return Response(
                {'error': 'Formato no válido. Use PNG o JPG'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar tamaño (max 2MB para PDFs)
        if logo.size > 2 * 1024 * 1024:
            return Response(
                {'error': 'El archivo no puede superar 2MB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        config = ConfiguracionSistema.get_config()
        # Eliminar logo anterior si existe
        if config.logo_pdf:
            config.logo_pdf.delete(save=False)
        
        config.logo_pdf = logo
        config.updated_by = request.user
        config.save()
        
        serializer = ConfiguracionSistemaSerializer(config, context={'request': request})
        logger.info(f"Logo PDF actualizado por {request.user.username}")
        
        return Response({
            'mensaje': 'Logo para PDFs actualizado correctamente',
            'configuracion': serializer.data
        })
    
    @action(detail=False, methods=['delete'], url_path='eliminar-logo-header')
    def eliminar_logo_header(self, request):
        """
        DELETE /api/configuracion/tema/eliminar-logo-header/
        Elimina el logo del header.
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo superusuarios pueden eliminar logos'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        config = ConfiguracionSistema.get_config()
        if config.logo_header:
            config.logo_header.delete(save=False)
            config.logo_header = None
            config.updated_by = request.user
            config.save()
            logger.info(f"Logo header eliminado por {request.user.username}")
        
        serializer = ConfiguracionSistemaSerializer(config)
        return Response({
            'mensaje': 'Logo del header eliminado',
            'configuracion': serializer.data
        })
    
    @action(detail=False, methods=['delete'], url_path='eliminar-logo-pdf')
    def eliminar_logo_pdf(self, request):
        """
        DELETE /api/configuracion/tema/eliminar-logo-pdf/
        Elimina el logo para PDFs.
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo superusuarios pueden eliminar logos'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        config = ConfiguracionSistema.get_config()
        if config.logo_pdf:
            config.logo_pdf.delete(save=False)
            config.logo_pdf = None
            config.updated_by = request.user
            config.save()
            logger.info(f"Logo PDF eliminado por {request.user.username}")
        
        serializer = ConfiguracionSistemaSerializer(config)
        return Response({
            'mensaje': 'Logo para PDFs eliminado',
            'configuracion': serializer.data
        })


# ============================================================================
# VIEWSET PARA TEMA GLOBAL
# ============================================================================

from core.models import TemaGlobal
from core.serializers import TemaGlobalSerializer, TemaGlobalPublicoSerializer


class TemaGlobalViewSet(viewsets.ViewSet):
    """
    ViewSet para gestionar el tema global del sistema.
    
    Endpoints:
    - GET /api/tema/activo/ - Obtener tema activo (público)
    - GET /api/tema/ - Obtener tema para administración
    - PUT /api/tema/ - Actualizar tema (solo admin)
    - POST /api/tema/restablecer/ - Restablecer tema institucional (solo admin)
    - DELETE /api/tema/eliminar-logo/<tipo>/ - Eliminar logo específico (solo admin)
    """
    
    def get_permissions(self):
        """Permisos según la acción"""
        if self.action in ['tema_activo']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['get'], url_path='activo')
    def tema_activo(self, request):
        """
        GET /api/tema/activo/
        Endpoint público para obtener el tema activo.
        Puede ser consultado sin autenticación (para login, etc).
        """
        tema = TemaGlobal.get_tema_activo()
        serializer = TemaGlobalPublicoSerializer(tema, context={'request': request})
        return Response(serializer.data)
    
    def list(self, request):
        """
        GET /api/tema/
        Obtener el tema activo con información completa (admin).
        """
        tema = TemaGlobal.get_tema_activo()
        serializer = TemaGlobalSerializer(tema, context={'request': request})
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """
        PUT /api/tema/
        Actualizar el tema global. Solo administradores.
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo superusuarios pueden modificar el tema global'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        tema = TemaGlobal.get_tema_activo()
        
        # No permitir modificar tema institucional base
        if tema.es_tema_institucional:
            # Si intentan modificar el institucional, crear uno nuevo basado en él
            tema.pk = None
            tema.nombre = 'Tema Personalizado'
            tema.es_tema_institucional = False
        
        serializer = TemaGlobalSerializer(tema, data=request.data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            # Guardar con auditoría
            tema_guardado = serializer.save()
            if tema.pk is None:
                # Es un tema nuevo
                tema_guardado.creado_por = request.user
            tema_guardado.modificado_por = request.user
            tema_guardado.save()
            
            # Registrar en auditoría
            AuditoriaLog.objects.create(
                usuario=request.user,
                accion='UPDATE',
                modelo='TemaGlobal',
                objeto_id=str(tema_guardado.id),
                datos_nuevos=serializer.data,
                detalles={'objeto_repr': f'Tema global: {tema_guardado.nombre}'}
            )
            
            logger.info(f"Tema global actualizado por {request.user.username}")
            
            return Response({
                'mensaje': 'Tema actualizado correctamente',
                'tema': TemaGlobalSerializer(tema_guardado, context={'request': request}).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], url_path='restablecer')
    def restablecer_institucional(self, request):
        """
        POST /api/tema/restablecer/
        Restablecer al tema institucional por defecto.
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo superusuarios pueden restablecer el tema'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Desactivar todos los temas actuales
        TemaGlobal.objects.update(activo=False)
        
        # Buscar o crear el tema institucional
        tema_institucional = TemaGlobal.objects.filter(es_tema_institucional=True).first()
        
        if tema_institucional:
            tema_institucional.activo = True
            tema_institucional.save()
        else:
            # Crear tema institucional por defecto
            tema_institucional = TemaGlobal.crear_tema_institucional()
        
        # Registrar en auditoría
        AuditoriaLog.objects.create(
            usuario=request.user,
            accion='UPDATE',
            modelo='TemaGlobal',
            objeto_id=str(tema_institucional.id),
            detalles={'objeto_repr': 'Tema restablecido a institucional'}
        )
        
        logger.info(f"Tema restablecido a institucional por {request.user.username}")
        
        serializer = TemaGlobalSerializer(tema_institucional, context={'request': request})
        return Response({
            'mensaje': 'Tema restablecido al institucional',
            'tema': serializer.data
        })
    
    @action(detail=False, methods=['delete'], url_path='eliminar-logo/(?P<tipo>\\w+)')
    def eliminar_logo(self, request, tipo=None):
        """
        DELETE /api/tema/eliminar-logo/<tipo>/
        Elimina un logo específico del tema.
        
        Tipos válidos: header, login, reportes, favicon, fondo_login, fondo_reportes
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo superusuarios pueden eliminar logos'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        campos_logo = {
            'header': 'logo_header',
            'login': 'logo_login',
            'reportes': 'logo_reportes',
            'favicon': 'favicon',
            'fondo_login': 'imagen_fondo_login',
            'fondo_reportes': 'imagen_fondo_reportes',
        }
        
        if tipo not in campos_logo:
            return Response(
                {'error': f'Tipo de logo no válido. Opciones: {list(campos_logo.keys())}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tema = TemaGlobal.get_tema_activo()
        campo = campos_logo[tipo]
        archivo = getattr(tema, campo)
        
        if archivo:
            archivo.delete(save=False)
            setattr(tema, campo, None)
            tema.modificado_por = request.user
            tema.save()
            
            logger.info(f"Logo {tipo} eliminado del tema por {request.user.username}")
            
            return Response({
                'mensaje': f'Logo {tipo} eliminado correctamente',
                'tema': TemaGlobalSerializer(tema, context={'request': request}).data
            })
        
        return Response({
            'mensaje': f'El logo {tipo} no estaba configurado',
            'tema': TemaGlobalSerializer(tema, context={'request': request}).data
        })
    
    @action(detail=False, methods=['post'], url_path='subir-logo/(?P<tipo>\\w+)')
    def subir_logo(self, request, tipo=None):
        """
        POST /api/tema/subir-logo/<tipo>/
        Sube un logo específico al tema.
        
        Tipos válidos: header, login, reportes, favicon, fondo_login, fondo_reportes
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo superusuarios pueden subir logos'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        campos_logo = {
            'header': 'logo_header',
            'login': 'logo_login',
            'reportes': 'logo_reportes',
            'favicon': 'favicon',
            'fondo_login': 'imagen_fondo_login',
            'fondo_reportes': 'imagen_fondo_reportes',
        }
        
        if tipo not in campos_logo:
            return Response(
                {'error': f'Tipo de logo no válido. Opciones: {list(campos_logo.keys())}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if 'archivo' not in request.FILES:
            return Response(
                {'error': 'No se proporcionó ningún archivo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        archivo = request.FILES['archivo']
        
        # Validar tipo de archivo
        tipos_permitidos = ['image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/svg+xml']
        if tipo == 'favicon':
            tipos_permitidos.append('image/x-icon')
        
        if archivo.content_type not in tipos_permitidos:
            return Response(
                {'error': f'Tipo de archivo no permitido. Tipos válidos: {tipos_permitidos}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar tamaño (max 5MB para imágenes, 500KB para favicon)
        max_size = 500 * 1024 if tipo == 'favicon' else 5 * 1024 * 1024
        if archivo.size > max_size:
            max_mb = max_size / (1024 * 1024)
            return Response(
                {'error': f'El archivo excede el tamaño máximo permitido ({max_mb}MB)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tema = TemaGlobal.get_tema_activo()
        campo = campos_logo[tipo]
        
        # Eliminar archivo anterior si existe
        archivo_anterior = getattr(tema, campo)
        if archivo_anterior:
            archivo_anterior.delete(save=False)
        
        # Guardar nuevo archivo
        setattr(tema, campo, archivo)
        tema.modificado_por = request.user
        tema.save()
        
        logger.info(f"Logo {tipo} actualizado en el tema por {request.user.username}")
        
        return Response({
            'mensaje': f'Logo {tipo} actualizado correctamente',
            'tema': TemaGlobalSerializer(tema, context={'request': request}).data
        })






