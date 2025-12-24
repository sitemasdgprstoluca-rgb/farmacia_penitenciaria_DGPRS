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
from datetime import date, timedelta, datetime
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


# ============================================
# ISS-013: JERARQUÍA DE ROLES PARA VALIDACIÓN
# ============================================
# Menor número = mayor privilegio
# Esto previene escalamiento de privilegios
# FLUJO V2: Incluye roles jerárquicos del centro
ROLE_HIERARCHY = {
    # Nivel 0: Superusuario (acceso total)
    'superuser': 0,
    'superusuario': 0,
    
    # Nivel 1: Administradores del sistema
    'admin': 1,
    'admin_sistema': 1,
    
    # Nivel 2: Personal de Farmacia Central
    'farmacia': 2,
    'admin_farmacia': 2,
    
    # Nivel 3: Directivos del Centro (FLUJO V2)
    'director_centro': 3,
    'administrador_centro': 3,
    
    # Nivel 4: Personal operativo del Centro (FLUJO V2)
    'medico': 4,
    
    # Nivel 5: Usuarios de consulta
    'centro': 5,
    'usuario_centro': 5,
    'vista': 5,
    'usuario_vista': 5,
    'usuario_normal': 5,
}


def get_role_level(user, rol=None):
    """
    ISS-013: Obtiene el nivel jerárquico de un usuario o rol.
    Menor nivel = mayor privilegio.
    """
    if user and user.is_superuser:
        return 0
    
    target_rol = rol or (getattr(user, 'rol', '') or '').lower()
    return ROLE_HIERARCHY.get(target_rol, 99)


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
        """
        ISS-005 FIX (audit7): Filtra usuarios por centro Y jerarquía de roles.
        
        Un usuario solo puede ver:
        - Superusuario/Admin: Todos los usuarios
        - Farmacia: Usuarios de menor privilegio
        - Usuario de centro: Solo usuarios de su centro con menor o igual privilegio
        """
        user = self.request.user
        if user.is_superuser:
            qs = User.objects.all()
        elif self._is_farmacia_or_admin(user):
            # ISS-005 FIX: Farmacia ve todos excepto superusuarios
            qs = User.objects.filter(is_superuser=False)
        else:
            # Usuario no admin solo ve usuarios de su centro
            if hasattr(user, 'centro') and user.centro:
                qs = User.objects.filter(centro=user.centro)
                
                # ISS-005 FIX (audit7): Filtrar por jerarquía de roles
                # Solo ver usuarios de menor o igual privilegio
                user_level = get_role_level(user)
                
                # Obtener roles que este usuario puede ver (igual o menor privilegio)
                roles_visibles = [rol for rol, nivel in ROLE_HIERARCHY.items() 
                                  if nivel >= user_level]
                
                # Filtrar por roles permitidos
                qs = qs.filter(rol__in=roles_visibles)
                
                logger.debug(
                    f"ISS-005: Usuario {user.username} (nivel {user_level}) "
                    f"puede ver roles: {roles_visibles}"
                )
            else:
                # Sin centro, solo ve a sí mismo
                qs = User.objects.filter(id=user.id)
        
        # Aplicar filtros server-side
        qs = self._apply_filters(qs, self.request.query_params)
        
        return qs.select_related('centro')
    
    def get_object(self):
        """
        HALLAZGO #7 FIX: Prevenir IDOR validando que el objeto solicitado
        esté en el queryset filtrado del usuario.
        """
        obj = super().get_object()
        
        # Verificar que el usuario tiene permiso para ver este objeto específico
        # (ya está validado por get_queryset, pero double-check por seguridad)
        if not self.request.user.is_superuser and not self._is_farmacia_or_admin(self.request.user):
            # Usuario de centro: verificar que sea del mismo centro
            if hasattr(self.request.user, 'centro') and self.request.user.centro:
                if hasattr(obj, 'centro') and obj.centro != self.request.user.centro:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied('No tiene permiso para acceder a este usuario.')
        
        return obj

    def _validate_role_hierarchy(self, requesting_user, target_role, target_user=None):
        """
        ISS-013 + ISS-004 FIX: Valida que el usuario que hace la petición tenga suficientes
        privilegios para asignar el rol objetivo.
        
        Reglas:
        - Superusuarios pueden hacer cualquier cosa
        - Un usuario no puede asignar un rol de mayor o igual privilegio que el suyo
        - Un usuario no puede modificar a otro de mayor o igual privilegio
        - ISS-004 FIX: Un usuario NO puede modificar a otro del MISMO rol (excepto superusuarios)
        """
        from rest_framework.exceptions import PermissionDenied
        
        requesting_level = get_role_level(requesting_user)
        target_level = get_role_level(None, target_role)
        
        # Si el rol objetivo tiene mayor privilegio (menor nivel) que el solicitante
        if target_level <= requesting_level and not requesting_user.is_superuser:
            raise PermissionDenied(
                f'No puede asignar el rol "{target_role}". '
                f'Solo usuarios con mayor privilegio pueden asignar este rol.'
            )
        
        # Si estamos modificando un usuario existente, verificar que tengamos privilegio sobre él
        if target_user:
            target_user_level = get_role_level(target_user)
            
            # ISS-004 FIX: No permitir modificar usuarios del mismo nivel o superior
            # Excepto para superusuarios que pueden modificar a cualquiera
            if target_user_level <= requesting_level and not requesting_user.is_superuser:
                raise PermissionDenied(
                    f'No puede modificar a este usuario. '
                    f'Solo usuarios con mayor privilegio pueden modificarlo.'
                )
            
            # ISS-004 FIX: Prevenir que un usuario se modifique a sí mismo con privilegios elevados
            # (excepto superusuarios)
            if target_user.pk == requesting_user.pk and not requesting_user.is_superuser:
                # Solo permitir modificar campos básicos, no el rol
                if target_role and target_role.lower() != requesting_user.rol.lower():
                    raise PermissionDenied(
                        'No puede cambiar su propio rol. Contacte a un administrador.'
                    )

    def perform_create(self, serializer):
        """
        ISS-013: Valida jerarquía de roles antes de crear usuario.
        """
        target_role = self.request.data.get('rol', '').lower()
        is_superuser = self.request.data.get('is_superuser', False)
        
        # Si intentan crear un superusuario, validar que quien lo hace sea superusuario
        if is_superuser and not self.request.user.is_superuser:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Solo superusuarios pueden crear otros superusuarios.')
        
        # Validar jerarquía de roles
        if target_role:
            self._validate_role_hierarchy(self.request.user, target_role)
        
        # Guardar el usuario
        user = serializer.save()
        
        # Registrar en auditoría
        AuditoriaLog.objects.create(
            usuario=self.request.user,
            accion='CREATE',
            modelo='User',
            objeto_id=str(user.id),
            datos_nuevos={'username': user.username, 'rol': user.rol, 'email': user.email},
            detalles={'objeto_repr': user.username, 'creado_por': self.request.user.username},
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        logger.info(f"Usuario {user.username} creado por {self.request.user.username}")

    def perform_update(self, serializer):
        """
        ISS-013: Valida jerarquía de roles antes de actualizar usuario.
        """
        instance = serializer.instance
        target_role = self.request.data.get('rol', instance.rol).lower() if self.request.data.get('rol') else None
        is_superuser = self.request.data.get('is_superuser')
        
        # Si intentan hacer superusuario, validar que quien lo hace sea superusuario
        if is_superuser and not self.request.user.is_superuser:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Solo superusuarios pueden otorgar privilegios de superusuario.')
        
        # Validar que tenemos privilegio sobre el usuario a modificar
        self._validate_role_hierarchy(self.request.user, target_role or instance.rol, instance)
        
        # Si cambia el rol, validar también el nuevo rol
        if target_role and target_role != instance.rol:
            self._validate_role_hierarchy(self.request.user, target_role)
        
        # Guardar datos anteriores para auditoría
        old_data = {
            'username': instance.username,
            'rol': instance.rol,
            'email': instance.email,
            'is_active': instance.is_active,
        }
        
        # Guardar el usuario
        user = serializer.save()
        
        # Detectar cambios
        new_data = {
            'username': user.username,
            'rol': user.rol,
            'email': user.email,
            'is_active': user.is_active,
        }
        cambios = {k: (old_data[k], new_data[k]) for k in new_data if old_data.get(k) != new_data.get(k)}
        
        if cambios:
            AuditoriaLog.objects.create(
                usuario=self.request.user,
                accion='UPDATE',
                modelo='User',
                objeto_id=str(user.id),
                datos_anteriores=old_data,
                datos_nuevos=new_data,
                detalles={'objeto_repr': user.username, 'modificado_por': self.request.user.username, 'cambios': list(cambios.keys())},
                ip_address=self.request.META.get('REMOTE_ADDR')
            )
        logger.info(f"Usuario {user.username} actualizado por {self.request.user.username}: {cambios}")

    def destroy(self, request, *args, **kwargs):
        """
        ISS-004 FIX: Valida jerarquía de roles antes de eliminar usuario.
        
        - Un usuario no puede eliminarse a sí mismo
        - Un usuario no puede eliminar a otro de igual o mayor privilegio
        """
        from rest_framework.exceptions import PermissionDenied
        
        instance = self.get_object()
        
        # Prevenir auto-eliminación
        if instance.pk == request.user.pk:
            return Response(
                {'error': 'No puede eliminarse a sí mismo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar jerarquía (excepto superusuarios)
        if not request.user.is_superuser:
            requesting_level = get_role_level(request.user)
            target_level = get_role_level(instance)
            
            if target_level <= requesting_level:
                raise PermissionDenied(
                    'No puede eliminar a este usuario. '
                    'Solo usuarios con mayor privilegio pueden eliminarlo.'
                )
        
        # Registrar en auditoría antes de eliminar
        AuditoriaLog.objects.create(
            usuario=request.user,
            accion='DELETE',
            modelo='User',
            objeto_id=str(instance.id),
            datos_anteriores={
                'username': instance.username,
                'email': instance.email,
                'rol': instance.rol,
                'centro_id': instance.centro_id,
            },
            detalles={'objeto_repr': instance.username, 'eliminado_por': request.user.username},
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        logger.info(f"Usuario {instance.username} eliminado por {request.user.username}")
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        """GET/PATCH /api/usuarios/me/ - Perfil del usuario autenticado"""
        try:
            UserProfile.objects.get_or_create(usuario=request.user)
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
                old_data['rol'] = profile.rol
            
            serializer = UserMeSerializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            # Refrescar usuario y profile para capturar cambios
            request.user.refresh_from_db()
            
            # Detectar cambios para auditoría
            new_data = {
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
            }
            # Refrescar profile para obtener telefono actualizado
            profile = getattr(request.user, 'profile', None)
            if profile:
                profile.refresh_from_db()
                new_data['telefono'] = profile.telefono
                new_data['rol'] = profile.rol
            
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
        
        ISS-PASSWORD FIX: Incluye verificación post-guardado.
        """
        from django.db import transaction
        
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

        # ISS-022: Usar validadores de Django en lugar de reglas duplicadas
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        
        try:
            validate_password(new_password, user)
        except DjangoValidationError as e:
            return Response({'error': '; '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        if old_password == new_password:
            return Response({'error': 'La nueva contraseña debe ser diferente a la anterior'}, status=status.HTTP_400_BAD_REQUEST)

        # ISS-PASSWORD FIX: Usar transacción y verificar post-guardado
        try:
            with transaction.atomic():
                user.set_password(new_password)
                user.save()
                
                # Verificar que la contraseña se guardó correctamente
                user.refresh_from_db()
                if not user.check_password(new_password):
                    logger.error(f"me_change_password - PASSWORD VERIFICATION FAILED for {user.username}!")
                    # Reintentar
                    user.set_password(new_password)
                    user.save(update_fields=['password'])
                    user.refresh_from_db()
                    if not user.check_password(new_password):
                        raise Exception("No se pudo guardar la contraseña después de reintentar")
                    logger.info(f"me_change_password - Password fixed on retry for {user.username}")
        except Exception as e:
            logger.error(f"me_change_password - Error crítico al guardar contraseña: {e}")
            return Response({
                'error': f'Error crítico al guardar contraseña. Contacte al administrador.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # HALLAZGO #3: Invalidar todos los tokens JWT existentes del usuario
        # Esto previene que tokens robados sigan funcionando después del cambio de contraseña
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
            # Eliminar todos los tokens pendientes del usuario (los marca como inválidos)
            OutstandingToken.objects.filter(user=user).delete()
        except Exception as e:
            # Si la app token_blacklist no está habilitada, loguear advertencia
            logger.warning(f'No se pudieron invalidar tokens JWT para {user.username}: {e}')
        
        # Registrar cambio exitoso en auditoría
        AuditoriaLog.objects.create(
            usuario=user,
            accion='UPDATE',
            modelo='Usuario',
            objeto_id=str(user.id),
            detalles={'objeto_repr': str(user), 'resultado': 'Contraseña actualizada exitosamente', 'tokens_invalidados': True}
        )
        
        logger.info("Contraseña actualizada para usuario %s (verificada, tokens JWT invalidados)", user.username)
        return Response({
            'message': 'Contraseña actualizada exitosamente',
            'nota': 'Todas las sesiones activas han sido cerradas. Debe iniciar sesión nuevamente.'
        })

    @action(detail=True, methods=['post'], url_path='cambiar-password')
    def cambiar_password(self, request, pk=None):
        """POST /api/usuarios/{id}/cambiar-password/ - Admin cambia password de otro usuario
        
        ISS-PASSWORD FIX: Incluye verificación post-guardado para asegurar que la contraseña
        se guardó correctamente y es funcional.
        """
        from django.db import transaction
        
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
        
        # HALLAZGO #6: Usar validate_password de Django (consistencia con cambiar_mi_password)
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        
        try:
            validate_password(new_password, usuario)
        except DjangoValidationError as e:
            return Response({'error': '; '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        
        # ISS-PASSWORD FIX: Usar transacción y verificar post-guardado
        try:
            with transaction.atomic():
                usuario.set_password(new_password)
                usuario.save()
                
                # Verificar que la contraseña se guardó correctamente
                usuario.refresh_from_db()
                if not usuario.check_password(new_password):
                    logger.error(f"cambiar_password - PASSWORD VERIFICATION FAILED for {usuario.username}!")
                    # Reintentar
                    usuario.set_password(new_password)
                    usuario.save(update_fields=['password'])
                    usuario.refresh_from_db()
                    if not usuario.check_password(new_password):
                        raise Exception("No se pudo guardar la contraseña después de reintentar")
                    logger.info(f"cambiar_password - Password fixed on retry for {usuario.username}")
        except Exception as e:
            logger.error(f"cambiar_password - Error crítico al guardar contraseña: {e}")
            return Response({
                'error': f'Error crítico al guardar contraseña: {str(e)}. Contacte al administrador.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # HALLAZGO #3: Invalidar todos los tokens JWT existentes del usuario
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
            OutstandingToken.objects.filter(user=usuario).delete()
        except Exception as e:
            logger.warning(f'No se pudieron invalidar tokens JWT para {usuario.username}: {e}')
        
        # Registrar en auditoría
        AuditoriaLog.objects.create(
            usuario=request.user,
            accion='UPDATE',
            modelo='User',
            objeto_id=str(usuario.id),
            detalles={'objeto_repr': usuario.username, 'cambiado_por': request.user.username, 'cambio': 'password'},
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        logger.info("Contraseña de usuario %s actualizada por %s (verificada)", usuario.username, request.user.username)
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
                    
                    # Buscar centro si se proporcionó (por nombre o ID)
                    centro = None
                    if centro_clave:
                        # Intentar buscar por ID primero, luego por nombre
                        if centro_clave.isdigit():
                            centro = Centro.objects.filter(id=int(centro_clave), activo=True).first()
                        if not centro:
                            centro = Centro.objects.filter(nombre__iexact=centro_clave, activo=True).first()
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

    @action(detail=False, methods=['get'], url_path='plantilla')
    def plantilla_usuarios(self, request):
        """
        Descarga plantilla Excel actualizada para importación de usuarios.
        
        Usa el generador estandarizado con el esquema real de la base de datos.
        Columnas: Username, Email, Nombre, Apellidos, Password, Rol, Centro ID, 
        Adscripción, Teléfono, Activo
        
        SEGURIDAD: Los usuarios creados sin contraseña requieren cambio en primer login.
        """
        from core.utils.excel_templates import generar_plantilla_usuarios
        return generar_plantilla_usuarios()



# NOTA: ProductoViewSet, LoteViewSet, RequisicionViewSet y CentroViewSet
# están en inventario/views.py para evitar duplicación.
# Importar desde allí si es necesario.


class DetalleRequisicionViewSet(viewsets.ModelViewSet):
    """ViewSet para detalles de requisiciones"""
    queryset = DetalleRequisicion.objects.select_related(
        'requisicion', 'requisicion__centro', 'requisicion__solicitante',
        'producto', 'lote', 'lote__producto', 'lote__centro'
    ).all()  # HALLAZGO #8 FIX: Prevenir N+1 queries
    serializer_class = DetalleRequisicionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination  # HALLAZGO #9: Paginación forzada


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
    
    # ISS-037: Límite máximo de registros para evitar slow queries
    MAX_AUDIT_RECORDS = 10000
    
    def get_queryset(self):
        """Filtrado avanzado por parámetros de query.
        
        ISS-037: Se aplica un límite máximo para evitar escaneo de tabla completa.
        """
        queryset = AuditoriaLog.objects.select_related('usuario').order_by('-timestamp')
        
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
        
        # ISS-037: La paginación manejará el límite de registros
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
    ordering_fields = ['fecha_inicio']
    ordering = ['-fecha_inicio']


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
    # ISS-FIX: Desactivar OrderingFilter de DRF, manejamos ordering manualmente
    filter_backends = []
    ordering = ['-created_at']

    def get_queryset(self):
        try:
            queryset = Notificacion.objects.filter(usuario=self.request.user)
            
            # ISS-FIX: Manejar ordering manualmente con alias fecha_creacion -> created_at
            ordering = self.request.query_params.get('ordering', '-created_at')
            if 'fecha_creacion' in ordering:
                # Reemplazar fecha_creacion por created_at
                ordering = ordering.replace('fecha_creacion', 'created_at')
            
            # Aplicar ordering solo si es un campo válido
            valid_fields = ['created_at', '-created_at', 'leida', '-leida']
            if ordering in valid_fields:
                queryset = queryset.order_by(ordering)
            else:
                queryset = queryset.order_by('-created_at')
            
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
                    queryset = queryset.filter(created_at__date__gte=fecha_desde)
                if fecha_hasta:
                    queryset = queryset.filter(created_at__date__lte=fecha_hasta)
            except Exception:
                pass

            return queryset
        except Exception as e:
            # ISS-FIX: Si la tabla notificaciones no existe, devolver queryset vacío
            logger.warning(f"Error accediendo a notificaciones: {e}")
            return Notificacion.objects.none()
    
    def list(self, request, *args, **kwargs):
        """Override list para manejar errores de tabla inexistente."""
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.warning(f"Error listando notificaciones: {e}")
            return Response({'count': 0, 'results': []})

    @action(detail=True, methods=['post'], url_path='marcar-leida')
    def marcar_leida(self, request, pk=None):
        """POST /api/notificaciones/{id}/marcar-leida/"""
        try:
            notificacion = self.get_object()
            notificacion.leida = True
            notificacion.save()
            return Response({'leida': True})
        except Exception as e:
            logger.warning(f"Error marcando notificación como leída: {e}")
            return Response({'leida': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='marcar-todas-leidas')
    def marcar_todas_leidas(self, request):
        """
        POST /api/notificaciones/marcar-todas-leidas/
        
        Marca como leídas las notificaciones que coinciden con los filtros actuales.
        Respeta los query params: tipo, desde, hasta, leida.
        Solo afecta las notificaciones del usuario autenticado (get_queryset ya filtra).
        """
        try:
            # get_queryset() ya aplica filtros de tipo, desde, hasta, leida y usuario
            updated = self.get_queryset().filter(leida=False).update(leida=True)
            return Response({'marcadas': updated})
        except Exception as e:
            logger.warning(f"Error marcando notificaciones como leídas: {e}")
            return Response({'marcadas': 0})

    @action(detail=False, methods=['get'], url_path='no-leidas-count')
    def no_leidas_count(self, request):
        """GET /api/notificaciones/no-leidas-count/"""
        try:
            count = self.get_queryset().filter(leida=False).count()
            return Response({'no_leidas': count})
        except Exception as e:
            # ISS-FIX: Si la tabla no existe o hay error, devolver 0 sin fallar
            logger.warning(f"Error contando notificaciones no leídas: {e}")
            return Response({'no_leidas': 0})
    
    @action(detail=False, methods=['get'], url_path='diagnostico')
    def diagnostico(self, request):
        """
        ISS-DEBUG: Endpoint de diagnóstico para notificaciones.
        
        Retorna información detallada sobre las notificaciones del usuario
        para ayudar a identificar problemas.
        """
        try:
            # Obtener todas las notificaciones del usuario (sin filtros)
            todas = Notificacion.objects.filter(usuario=request.user)
            no_leidas = todas.filter(leida=False)
            
            # Obtener las últimas 10 notificaciones con todos sus campos
            ultimas = todas.order_by('-created_at')[:10]
            
            return Response({
                'usuario': {
                    'id': request.user.pk,
                    'username': request.user.username,
                    'email': request.user.email,
                },
                'estadisticas': {
                    'total': todas.count(),
                    'no_leidas': no_leidas.count(),
                    'leidas': todas.filter(leida=True).count(),
                },
                'ultimas_notificaciones': [
                    {
                        'id': n.pk,
                        'titulo': n.titulo,
                        'mensaje': n.mensaje,
                        'tipo': n.tipo,
                        'leida': n.leida,
                        'url': n.url,
                        'datos': n.datos,
                        'created_at': n.created_at.isoformat() if n.created_at else None,
                        # Verificar si mensaje está vacío
                        'mensaje_vacio': not bool(n.mensaje),
                        'titulo_vacio': not bool(n.titulo),
                    }
                    for n in ultimas
                ],
                'consulta_sql': str(todas.query),
            })
        except Exception as e:
            logger.exception(f"Error en diagnóstico de notificaciones: {e}")
            return Response({
                'error': str(e),
                'tipo_error': type(e).__name__,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
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

        queryset = Producto.objects.prefetch_related('lotes')

        datos = []
        for producto in queryset:
            stock_actual = producto.get_stock_actual()
            nivel = producto.get_nivel_stock()
            # Obtener lote principal para marca
            lote_principal = producto.lotes.filter(activo=True, cantidad_actual__gt=0).order_by('-cantidad_actual').first()
            datos.append({
                'id': producto.id,
                'clave': producto.clave,
                'descripcion': producto.descripcion,
                'presentacion': producto.presentacion or '',
                'unidad_medida': producto.unidad_medida,
                'stock_actual': stock_actual,
                'nivel_stock': nivel,
                'nivel': nivel,  # Alias para compatibilidad frontend
                'precio_unitario': float(producto.precio_unitario) if producto.precio_unitario else 0,
                'valor_inventario': float(stock_actual * (producto.precio_unitario or 0)),
                'lotes_activos': producto.lotes.filter(activo=True, cantidad_actual__gt=0).count(),
                'marca': lote_principal.marca if lote_principal and lote_principal.marca else '',
            })

        # Calcular resumen basado en niveles de stock
        resumen = {
            'total_productos': len(datos),
            'stock_total': sum(d['stock_actual'] for d in datos),
            'productos_sin_stock': sum(1 for d in datos if d['stock_actual'] == 0),
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

            headers = ['Clave', 'Descripción', 'Presentación', 'Unidad', 'Inventario', 'Nivel', 'Precio', 'Marca']
            sheet.append(headers)

            for d in datos:
                sheet.append([
                    d['clave'],
                    d['descripcion'],
                    d['presentacion'],
                    d['unidad_medida'],
                    d['stock_actual'],
                    d['nivel_stock'],
                    d['precio_unitario'],
                    d['marca']
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
            activo=True
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
                'marca': lote.marca
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
            'centro_origen', 'centro_destino', 'solicitante', 'autorizador'
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
            centro_nombre = ''
            if req.centro_destino:
                centro_nombre = req.centro_destino.nombre
            elif req.centro_origen:
                centro_nombre = req.centro_origen.nombre
            datos.append({
                'id': req.id,
                'folio': req.folio,
                'centro_nombre': centro_nombre,
                'estado': req.estado,
                'fecha_solicitud': req.fecha_solicitud.isoformat(),
                'total_items': req.detalles.count(),
                'usuario_solicita': req.solicitante.username if req.solicitante else '-'
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
        if self.action in ['retrieve', 'list']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def list(self, request):
        """
        GET /api/configuracion/
        Retorna la configuración actual del sistema.
        Público para que el frontend pueda cargar configuraciones al iniciar.
        """
        # ConfiguracionSistema es un modelo clave-valor, retornar todas las configuraciones públicas
        configs = ConfiguracionSistema.objects.filter(es_publica=True)
        serializer = ConfiguracionSistemaSerializer(configs, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """
        GET /api/configuracion/{clave}/
        Retorna una configuración específica por clave.
        """
        try:
            config = ConfiguracionSistema.objects.get(clave=pk)
            if not config.es_publica and not request.user.is_superuser:
                return Response(
                    {'error': 'Configuración no accesible'},
                    status=status.HTTP_403_FORBIDDEN
                )
            serializer = ConfiguracionSistemaSerializer(config)
            return Response(serializer.data)
        except ConfiguracionSistema.DoesNotExist:
            return Response(
                {'error': 'Configuración no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def update(self, request, pk=None):
        """
        PUT /api/configuracion/{clave}/
        Actualiza una configuración del sistema.
        Solo superusuarios pueden modificar.
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo superusuarios pueden modificar la configuración del sistema'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            config = ConfiguracionSistema.objects.get(clave=pk)
        except ConfiguracionSistema.DoesNotExist:
            return Response(
                {'error': 'Configuración no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ConfiguracionSistemaSerializer(config, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Configuración '{pk}' actualizada por {request.user.username}")
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], url_path='bulk-update')
    def bulk_update(self, request):
        """
        POST /api/configuracion/bulk-update/
        Actualiza múltiples configuraciones.
        Body: { "configuraciones": [{"clave": "...", "valor": "..."}, ...] }
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo superusuarios pueden modificar la configuración'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        configuraciones = request.data.get('configuraciones', [])
        actualizadas = 0
        errores = []
        
        for cfg in configuraciones:
            clave = cfg.get('clave')
            valor = cfg.get('valor')
            if not clave:
                continue
            try:
                config, created = ConfiguracionSistema.objects.update_or_create(
                    clave=clave,
                    defaults={'valor': str(valor) if valor is not None else ''}
                )
                actualizadas += 1
            except Exception as e:
                errores.append({'clave': clave, 'error': str(e)})
        
        logger.info(f"{actualizadas} configuraciones actualizadas por {request.user.username}")
        return Response({
            'mensaje': f'{actualizadas} configuraciones actualizadas',
            'errores': errores
        })
    
    @action(detail=False, methods=['post'], url_path='aplicar-tema')
    def aplicar_tema(self, request):
        """
        POST /api/configuracion/tema/aplicar-tema/
        Aplica un tema predefinido al sistema.
        Solo superusuarios pueden modificar.
        """
        try:
            if not request.user.is_superuser:
                return Response(
                    {'error': 'Solo superusuarios pueden aplicar temas'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            tema_nombre = request.data.get('tema')
            if not tema_nombre:
                return Response(
                    {'error': 'Se requiere el nombre del tema'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Definición de temas predefinidos con sus colores
            TEMAS_PREDEFINIDOS = {
                'default': {
                    'nombre': 'Por Defecto (Institucional)',
                    'color_primario': '#9F2241',
                    'color_primario_hover': '#6B1839',
                    'color_secundario': '#424242',
                    'color_secundario_hover': '#2E2E2E',
                    'color_exito': '#4CAF50',
                    'color_exito_hover': '#3d8b40',
                    'color_alerta': '#FF9800',
                    'color_alerta_hover': '#e68900',
                    'color_error': '#F44336',
                    'color_error_hover': '#d32f2f',
                    'color_info': '#2196F3',
                    'color_info_hover': '#1976D2',
                    'color_fondo_principal': '#F5F5F5',
                    'color_fondo_sidebar': '#9F2241',
                    'color_fondo_header': '#9F2241',
                    'color_texto_principal': '#212121',
                    'color_texto_sidebar': '#FFFFFF',
                    'color_texto_header': '#FFFFFF',
                    'color_texto_links': '#9F2241',
                    'color_borde_inputs': '#d1d5db',
                    'color_borde_focus': '#9F2241',
                    'reporte_color_encabezado': '#9F2241',
                    'reporte_color_texto': '#1f2937',
                },
                'dark': {
                    'nombre': 'Oscuro',
                    'color_primario': '#1F2937',
                    'color_primario_hover': '#111827',
                    'color_secundario': '#374151',
                    'color_secundario_hover': '#1F2937',
                    'color_exito': '#10B981',
                    'color_exito_hover': '#059669',
                    'color_alerta': '#F59E0B',
                    'color_alerta_hover': '#D97706',
                    'color_error': '#EF4444',
                    'color_error_hover': '#DC2626',
                    'color_info': '#3B82F6',
                    'color_info_hover': '#2563EB',
                    'color_fondo_principal': '#111827',
                    'color_fondo_sidebar': '#1F2937',
                    'color_fondo_header': '#1F2937',
                    'color_texto_principal': '#F9FAFB',
                    'color_texto_sidebar': '#F9FAFB',
                    'color_texto_header': '#F9FAFB',
                    'color_texto_links': '#60A5FA',
                    'color_borde_inputs': '#4B5563',
                    'color_borde_focus': '#3B82F6',
                    'reporte_color_encabezado': '#1F2937',
                    'reporte_color_texto': '#1f2937',
                },
                'green': {
                    'nombre': 'Verde Institucional',
                    'color_primario': '#166534',
                    'color_primario_hover': '#14532D',
                    'color_secundario': '#15803D',
                    'color_secundario_hover': '#166534',
                    'color_exito': '#22C55E',
                    'color_exito_hover': '#16A34A',
                    'color_alerta': '#EAB308',
                    'color_alerta_hover': '#CA8A04',
                    'color_error': '#DC2626',
                    'color_error_hover': '#B91C1C',
                    'color_info': '#0EA5E9',
                    'color_info_hover': '#0284C7',
                    'color_fondo_principal': '#F0FDF4',
                    'color_fondo_sidebar': '#166534',
                    'color_fondo_header': '#166534',
                    'color_texto_principal': '#14532D',
                    'color_texto_sidebar': '#FFFFFF',
                    'color_texto_header': '#FFFFFF',
                    'color_texto_links': '#166534',
                    'color_borde_inputs': '#86EFAC',
                    'color_borde_focus': '#22C55E',
                    'reporte_color_encabezado': '#166534',
                    'reporte_color_texto': '#14532D',
                },
                'purple': {
                    'nombre': 'Púrpura',
                    'color_primario': '#7C3AED',
                    'color_primario_hover': '#6D28D9',
                    'color_secundario': '#8B5CF6',
                    'color_secundario_hover': '#7C3AED',
                    'color_exito': '#10B981',
                    'color_exito_hover': '#059669',
                    'color_alerta': '#F59E0B',
                    'color_alerta_hover': '#D97706',
                    'color_error': '#EF4444',
                    'color_error_hover': '#DC2626',
                    'color_info': '#3B82F6',
                    'color_info_hover': '#2563EB',
                    'color_fondo_principal': '#FAF5FF',
                    'color_fondo_sidebar': '#7C3AED',
                    'color_fondo_header': '#7C3AED',
                    'color_texto_principal': '#581C87',
                    'color_texto_sidebar': '#FFFFFF',
                    'color_texto_header': '#FFFFFF',
                    'color_texto_links': '#7C3AED',
                    'color_borde_inputs': '#C4B5FD',
                    'color_borde_focus': '#8B5CF6',
                    'reporte_color_encabezado': '#7C3AED',
                    'reporte_color_texto': '#581C87',
                },
            }
            
            if tema_nombre not in TEMAS_PREDEFINIDOS:
                return Response(
                    {'error': f'Tema "{tema_nombre}" no es válido. Opciones: {list(TEMAS_PREDEFINIDOS.keys())}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            tema_colores = TEMAS_PREDEFINIDOS[tema_nombre]
            
            # Intentar actualizar TemaGlobal si existe
            try:
                from core.models import TemaGlobal
                tema_global = TemaGlobal.objects.filter(es_activo=True).first()
                if not tema_global:
                    tema_global = TemaGlobal.objects.first()
                
                if tema_global:
                    # Actualizar los colores del tema global
                    for campo, valor in tema_colores.items():
                        if hasattr(tema_global, campo):
                            setattr(tema_global, campo, valor)
                    tema_global.save()
                    logger.info(f"TemaGlobal actualizado con tema '{tema_nombre}' por {request.user.username}")
            except Exception as e:
                logger.warning(f"No se pudo actualizar TemaGlobal: {e}")
            
            # También actualizar ConfiguracionSistema para compatibilidad
            configuraciones_actualizadas = 0
            for clave, valor in tema_colores.items():
                try:
                    config, created = ConfiguracionSistema.objects.update_or_create(
                        clave=clave,
                        defaults={'valor': str(valor), 'es_publica': True}
                    )
                    configuraciones_actualizadas += 1
                except Exception as e:
                    logger.warning(f"No se pudo actualizar ConfiguracionSistema '{clave}': {e}")
            
            # Guardar el tema activo
            ConfiguracionSistema.objects.update_or_create(
                clave='tema_activo',
                defaults={'valor': tema_nombre, 'es_publica': True}
            )
            
            logger.info(f"Tema '{tema_nombre}' aplicado por {request.user.username}")
            
            # Generar respuesta con CSS variables para el frontend
            css_variables = {
                '--color-primary': tema_colores.get('color_primario', '#9F2241'),
                '--color-primary-hover': tema_colores.get('color_primario_hover', '#6B1839'),
                '--color-primary-light': f"rgba({self._hex_to_rgb(tema_colores.get('color_primario', '#9F2241'))}, 0.2)",
                '--color-secondary': tema_colores.get('color_secundario', '#424242'),
                '--color-accent': '#BC955C',
                '--color-background': tema_colores.get('color_fondo_principal', '#F5F5F5'),
                '--color-sidebar-bg': tema_colores.get('color_fondo_sidebar', '#9F2241'),
                '--color-header-bg': tema_colores.get('color_fondo_header', '#9F2241'),
                '--color-card-bg': '#FFFFFF',
                '--color-text': tema_colores.get('color_texto_principal', '#212121'),
                '--color-text-secondary': '#757575',
                '--color-sidebar-text': tema_colores.get('color_texto_sidebar', '#FFFFFF'),
                '--color-header-text': tema_colores.get('color_texto_header', '#FFFFFF'),
                '--color-success': tema_colores.get('color_exito', '#4CAF50'),
                '--color-warning': tema_colores.get('color_alerta', '#FF9800'),
                '--color-error': tema_colores.get('color_error', '#F44336'),
                '--color-info': tema_colores.get('color_info', '#2196F3'),
            }
            
            return Response({
                'mensaje': f'Tema "{tema_nombre}" aplicado correctamente',
                'configuracion': {
                    'tema_activo': tema_nombre,
                    'nombre_sistema': 'Sistema de Farmacia Penitenciaria',
                    'css_variables': css_variables,
                    **tema_colores
                }
            })
            
        except Exception as e:
            logger.error(f"Error al aplicar tema: {str(e)}")
            return Response(
                {'error': f'Error interno al aplicar tema: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _hex_to_rgb(self, hex_color):
        """Convierte color hexadecimal a formato RGB para CSS rgba()"""
        try:
            hex_color = hex_color.lstrip('#')
            return ', '.join(str(int(hex_color[i:i+2], 16)) for i in (0, 2, 4))
        except Exception:
            return '159, 34, 65'  # Default institucional
    
    @action(detail=False, methods=['post'], url_path='restablecer')
    def restablecer(self, request):
        """
        POST /api/configuracion/tema/restablecer/
        Restablece el tema a los valores institucionales por defecto.
        Solo superusuarios pueden modificar.
        """
        try:
            if not request.user.is_superuser:
                return Response(
                    {'error': 'Solo superusuarios pueden restablecer el tema'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Usar el mismo método aplicar_tema con 'default'
            request._request.method = 'POST'
            from django.http import QueryDict
            original_data = request.data
            request._full_data = {'tema': 'default'}
            
            result = self.aplicar_tema(request)
            
            # Restaurar datos originales
            request._full_data = original_data
            
            logger.info(f"Tema restablecido a institucional por {request.user.username}")
            return result
            
        except Exception as e:
            logger.error(f"Error al restablecer tema: {str(e)}")
            return Response(
                {'error': f'Error interno al restablecer tema: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # End of ConfiguracionSistemaViewSet


# ============================================================================
# VIEWSET PARA TEMA GLOBAL
# ============================================================================

from core.models import TemaGlobal
from core.serializers import TemaGlobalSerializer, TemaGlobalPublicoSerializer


class TemaGlobalViewSet(viewsets.ViewSet):
    """Gestión del tema global acorde al esquema actual (campos simples)."""

    def get_permissions(self):
        if self.action in ['tema_activo']:
            return [AllowAny()]
        # Para acciones de modificación, usar IsFarmaciaRole (admin + farmacia)
        if self.action in ['update', 'restablecer_institucional', 'subir_logo', 'eliminar_logo']:
            return [IsAuthenticated(), IsFarmaciaRole()]
        return [IsAuthenticated()]

    def _get_tema_activo(self):
        tema = TemaGlobal.objects.filter(es_activo=True).first()
        if tema:
            return tema
        return TemaGlobal.objects.first()

    @action(detail=False, methods=['get'], url_path='activo')
    def tema_activo(self, request):
        tema = self._get_tema_activo()
        if not tema:
            return Response({'error': 'No hay tema configurado'}, status=status.HTTP_404_NOT_FOUND)
        serializer = TemaGlobalPublicoSerializer(tema, context={'request': request})
        return Response(serializer.data)

    def list(self, request):
        tema = self._get_tema_activo()
        if not tema:
            return Response({'error': 'No hay tema configurado'}, status=status.HTTP_404_NOT_FOUND)
        serializer = TemaGlobalSerializer(tema, context={'request': request})
        return Response(serializer.data)

    def update(self, request, pk=None):
        # Permiso controlado por get_permissions() -> IsFarmaciaRole
        tema = self._get_tema_activo()
        if not tema:
            tema = TemaGlobal.objects.create(nombre='Tema Sistema', es_activo=True)

        serializer = TemaGlobalSerializer(tema, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            tema_guardado = serializer.save()
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
        Restablece el tema global a valores institucionales por defecto.
        Permiso: admin o farmacia (IsFarmaciaRole)
        """
        # Permiso controlado por get_permissions() -> IsFarmaciaRole
        try:
            tema = self._get_tema_activo()
            if not tema:
                tema = TemaGlobal.objects.create(nombre='Tema Institucional', es_activo=True)

            # Valores institucionales por defecto (guinda)
            valores_institucionales = {
                'nombre': 'Tema Institucional',
                'color_primario': '#9F2241',
                'color_primario_hover': '#6B1839',
                'color_secundario': '#424242',
                'color_secundario_hover': '#212121',
                'color_exito': '#4CAF50',
                'color_exito_hover': '#388E3C',
                'color_alerta': '#FF9800',
                'color_alerta_hover': '#F57C00',
                'color_error': '#F44336',
                'color_error_hover': '#D32F2F',
                'color_info': '#2196F3',
                'color_info_hover': '#1976D2',
                'color_fondo_principal': '#F5F5F5',
                'color_fondo_sidebar': '#9F2241',
                'color_fondo_header': '#9F2241',
                'color_texto_principal': '#212121',
                'color_texto_sidebar': '#FFFFFF',
                'color_texto_header': '#FFFFFF',
                'color_texto_links': '#9F2241',
                'color_borde_inputs': '#E0E0E0',
                'color_borde_focus': '#9F2241',
                'reporte_color_encabezado': '#9F2241',
                'reporte_color_texto': '#FFFFFF',
            }

            for campo, valor in valores_institucionales.items():
                setattr(tema, campo, valor)
            tema.save()

            # Registrar en auditoría
            AuditoriaLog.objects.create(
                usuario=request.user,
                accion='UPDATE',
                modelo='TemaGlobal',
                objeto_id=str(tema.id),
                datos_nuevos=valores_institucionales,
                detalles={'objeto_repr': 'Tema restablecido a institucional'}
            )

            logger.info(f"Tema restablecido a institucional por {request.user.username}")

            return Response({
                'mensaje': 'Tema restablecido a valores institucionales',
                'tema': TemaGlobalSerializer(tema, context={'request': request}).data
            })

        except Exception as e:
            logger.error(f"Error al restablecer tema: {str(e)}")
            return Response(
                {'error': f'Error interno: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='subir-logo/(?P<tipo>[^/.]+)')
    def subir_logo(self, request, tipo=None):
        """
        POST /api/tema/subir-logo/{tipo}/
        Sube un logo para el tema global.
        Tipos válidos: header, login, reportes, favicon
        Permiso: admin o farmacia (IsFarmaciaRole)
        """
        # Permiso controlado por get_permissions() -> IsFarmaciaRole

        tipos_validos = ['header', 'login', 'reportes', 'favicon']
        if tipo not in tipos_validos:
            return Response(
                {'error': f'Tipo de logo inválido. Opciones: {tipos_validos}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        archivo = request.FILES.get('archivo') or request.FILES.get('logo')
        if not archivo:
            return Response(
                {'error': 'No se proporcionó archivo. Enviar como "archivo" o "logo".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar tipo de archivo
        tipos_permitidos = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/x-icon', 'image/vnd.microsoft.icon']
        if archivo.content_type not in tipos_permitidos:
            return Response(
                {'error': f'Tipo de archivo no permitido: {archivo.content_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar tamaño (2MB máximo)
        if archivo.size > 2 * 1024 * 1024:
            return Response(
                {'error': 'El archivo no puede superar 2MB'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            import os
            from django.conf import settings
            from django.core.files.storage import default_storage

            tema = self._get_tema_activo()
            if not tema:
                tema = TemaGlobal.objects.create(nombre='Tema Sistema', es_activo=True)

            # Guardar archivo
            extension = archivo.name.split('.')[-1]
            nombre_archivo = f'tema/logos/{tipo}_{tema.id}.{extension}'
            
            # Eliminar archivo anterior si existe
            campo_url = f'logo_url' if tipo == 'header' else f'favicon_url' if tipo == 'favicon' else None
            if campo_url and hasattr(tema, campo_url):
                url_anterior = getattr(tema, campo_url)
                if url_anterior:
                    try:
                        default_storage.delete(url_anterior.replace('/media/', ''))
                    except Exception:
                        pass

            # Guardar nuevo archivo
            ruta_guardada = default_storage.save(nombre_archivo, archivo)
            url_completa = f'{settings.MEDIA_URL}{ruta_guardada}'

            # Actualizar campo correspondiente en TemaGlobal
            # Nota: Solo logo_url y favicon_url existen en el modelo actual
            if tipo == 'header':
                tema.logo_url = url_completa
            elif tipo == 'favicon':
                tema.favicon_url = url_completa
            # Para otros tipos, podríamos necesitar campos adicionales en el modelo

            tema.save()

            logger.info(f"Logo {tipo} actualizado por {request.user.username}")

            return Response({
                'mensaje': f'Logo {tipo} actualizado correctamente',
                'url': url_completa,
                'tema': TemaGlobalSerializer(tema, context={'request': request}).data
            })

        except Exception as e:
            logger.error(f"Error al subir logo {tipo}: {str(e)}")
            return Response(
                {'error': f'Error interno: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['delete'], url_path='eliminar-logo/(?P<tipo>[^/.]+)')
    def eliminar_logo(self, request, tipo=None):
        """
        DELETE /api/tema/eliminar-logo/{tipo}/
        Elimina un logo del tema global.
        Tipos válidos: header, login, reportes, favicon
        Permiso: admin o farmacia (IsFarmaciaRole)
        """
        # Permiso controlado por get_permissions() -> IsFarmaciaRole

        tipos_validos = ['header', 'login', 'reportes', 'favicon']
        if tipo not in tipos_validos:
            return Response(
                {'error': f'Tipo de logo inválido. Opciones: {tipos_validos}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from django.core.files.storage import default_storage

            tema = self._get_tema_activo()
            if not tema:
                return Response(
                    {'error': 'No hay tema configurado'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Obtener y limpiar campo correspondiente
            campo_url = 'logo_url' if tipo == 'header' else 'favicon_url' if tipo == 'favicon' else None
            
            if campo_url and hasattr(tema, campo_url):
                url_anterior = getattr(tema, campo_url)
                if url_anterior:
                    try:
                        # Intentar eliminar archivo físico
                        ruta = url_anterior.replace('/media/', '')
                        if default_storage.exists(ruta):
                            default_storage.delete(ruta)
                    except Exception as e:
                        logger.warning(f"No se pudo eliminar archivo físico: {e}")
                    
                    # Limpiar campo en BD
                    setattr(tema, campo_url, None)
                    tema.save()

            logger.info(f"Logo {tipo} eliminado por {request.user.username}")

            return Response({
                'mensaje': f'Logo {tipo} eliminado correctamente',
                'tema': TemaGlobalSerializer(tema, context={'request': request}).data
            })

        except Exception as e:
            logger.error(f"Error al eliminar logo {tipo}: {str(e)}")
            return Response(
                {'error': f'Error interno: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# PRODUCTO IMAGEN VIEWSET
# =============================================================================

class ProductoImagenViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar imagenes de productos.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        from core.models import ProductoImagen
        queryset = ProductoImagen.objects.select_related('producto').all()
        
        # Filtrar por producto si se especifica
        producto_id = self.request.query_params.get('producto')
        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)
        
        return queryset.order_by('orden', '-es_principal')
    
    def get_serializer_class(self):
        from core.serializers import ProductoImagenSerializer
        return ProductoImagenSerializer
    
    def perform_create(self, serializer):
        serializer.save()
        logger.info(f"Imagen de producto creada por {self.request.user.username}")
    
    @action(detail=True, methods=['post'], url_path='set-principal')
    def set_principal(self, request, pk=None):
        """Establecer una imagen como principal."""
        from core.models import ProductoImagen
        imagen = self.get_object()
        
        # Quitar es_principal de otras imagenes del mismo producto
        ProductoImagen.objects.filter(
            producto_id=imagen.producto_id
        ).update(es_principal=False)
        
        # Establecer esta como principal
        imagen.es_principal = True
        imagen.save()
        
        return Response({'mensaje': 'Imagen establecida como principal'})


# =============================================================================
# LOTE DOCUMENTO VIEWSET
# =============================================================================

class LoteDocumentoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar documentos de lotes (facturas, contratos).
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        from core.models import LoteDocumento
        queryset = LoteDocumento.objects.select_related('lote', 'lote__producto', 'created_by').all()
        
        # Filtrar por lote si se especifica
        lote_id = self.request.query_params.get('lote')
        if lote_id:
            queryset = queryset.filter(lote_id=lote_id)
        
        # Filtrar por tipo de documento
        tipo = self.request.query_params.get('tipo_documento')
        if tipo:
            queryset = queryset.filter(tipo_documento=tipo)
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        from core.serializers import LoteDocumentoSerializer
        return LoteDocumentoSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        logger.info(f"Documento de lote creado por {self.request.user.username}")


# =============================================================================
# DONACION VIEWSET
# =============================================================================

class DonacionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar donaciones de medicamentos.
    Solo ADMIN y FARMACIA pueden crear/editar/procesar.
    VISTA puede consultar en solo lectura.
    """
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['numero', 'donante_nombre', 'donante_rfc']
    ordering_fields = ['fecha_donacion', 'fecha_recepcion', 'created_at']
    ordering = ['-fecha_recepcion']
    
    def get_permissions(self):
        """Permisos según la acción:
        - list, retrieve: IsAuthenticated + tener perm_donaciones
        - create, update, destroy, acciones: IsFarmaciaRole (admin/farmacia)
        """
        if self.action in ['list', 'retrieve']:
            # Cualquier autenticado con permiso de donaciones puede ver
            return [IsAuthenticated()]
        # Crear, editar, eliminar, acciones solo admin/farmacia
        return [IsAuthenticated(), IsFarmaciaRole()]
    
    def get_queryset(self):
        from core.models import Donacion
        queryset = Donacion.objects.select_related(
            'centro_destino', 'recibido_por'
        ).prefetch_related('detalles', 'detalles__producto').all()
        
        # Filtros
        estado = self.request.query_params.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        centro = self.request.query_params.get('centro')
        if centro:
            queryset = queryset.filter(centro_destino_id=centro)
        
        donante_tipo = self.request.query_params.get('donante_tipo')
        if donante_tipo:
            queryset = queryset.filter(donante_tipo=donante_tipo)
        
        # Filtro por rango de fechas
        fecha_desde = self.request.query_params.get('fecha_desde')
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        if fecha_desde:
            queryset = queryset.filter(fecha_donacion__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_donacion__lte=fecha_hasta)
        
        return queryset
    
    def get_serializer_class(self):
        from core.serializers import DonacionSerializer
        return DonacionSerializer
    
    def perform_create(self, serializer):
        donacion = serializer.save(recibido_por=self.request.user)
        logger.info(f"Donacion {donacion.numero} creada por {self.request.user.username}")
    
    @action(detail=True, methods=['post'], url_path='recibir')
    def recibir(self, request, pk=None):
        """Marcar una donacion como recibida."""
        donacion = self.get_object()
        
        if donacion.estado != 'pendiente':
            return Response(
                {'error': 'Solo se pueden recibir donaciones pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        donacion.estado = 'recibida'
        donacion.recibido_por = request.user
        donacion.fecha_recepcion = timezone.now()
        donacion.save()
        
        logger.info(f"Donacion {donacion.numero} recibida por {request.user.username}")
        
        from core.serializers import DonacionSerializer
        return Response(DonacionSerializer(donacion).data)
    
    @action(detail=True, methods=['post'], url_path='procesar')
    def procesar(self, request, pk=None):
        """
        Procesar una donacion - activar stock disponible en almacen de donaciones.
        Las donaciones funcionan como ALMACEN SEPARADO, no afectan inventario principal.
        Las salidas se registran mediante SalidaDonacion.
        """
        donacion = self.get_object()
        
        if donacion.estado not in ['pendiente', 'recibida']:
            return Response(
                {'error': 'Solo se pueden procesar donaciones pendientes o recibidas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Actualizar cantidad_disponible de cada detalle
                for detalle in donacion.detalles.all():
                    # Asegurar que cantidad_disponible = cantidad recibida
                    detalle.cantidad_disponible = detalle.cantidad
                    detalle.save()
                
                # Cambiar estado a procesada
                donacion.estado = 'procesada'
                donacion.save()
                
                logger.info(f"Donacion {donacion.numero} procesada por {request.user.username}")
                
                from core.serializers import DonacionSerializer
                return Response({
                    'mensaje': 'Donacion procesada correctamente. Stock disponible en almacen de donaciones.',
                    'donacion': DonacionSerializer(donacion).data
                })
        
        except Exception as e:
            logger.error(f"Error procesando donacion {donacion.numero}: {str(e)}")
            return Response(
                {'error': f'Error procesando donacion: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='rechazar')
    def rechazar(self, request, pk=None):
        """Rechazar una donacion."""
        donacion = self.get_object()
        
        if donacion.estado == 'procesada':
            return Response(
                {'error': 'No se puede rechazar una donacion ya procesada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        motivo = request.data.get('motivo', '')
        donacion.estado = 'rechazada'
        donacion.notas = f"{donacion.notas or ''}\n\nRechazada: {motivo}".strip()
        donacion.save()
        
        logger.info(f"Donacion {donacion.numero} rechazada por {request.user.username}")
        
        from core.serializers import DonacionSerializer
        return Response(DonacionSerializer(donacion).data)
    
    @action(detail=False, methods=['get'], url_path='diagnostico')
    def diagnostico(self, request):
        """
        ISS-DEBUG: Endpoint de diagnóstico para el módulo de donaciones.
        
        Retorna información sobre:
        - Estadísticas de donaciones
        - Posibles errores de datos
        - Estado de la tabla
        """
        from core.models import Donacion, DetalleDonacion
        from django.db import connection
        
        try:
            # Verificar si la tabla existe
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM donaciones")
                total_raw = cursor.fetchone()[0]
            
            # Estadísticas via ORM
            todas = Donacion.objects.all()
            por_estado = {}
            for estado in ['pendiente', 'recibida', 'procesada', 'rechazada']:
                por_estado[estado] = todas.filter(estado=estado).count()
            
            # Últimas 5 donaciones
            ultimas = todas.order_by('-created_at')[:5]
            ultimas_data = [
                {
                    'id': d.pk,
                    'numero': d.numero,
                    'donante_nombre': d.donante_nombre,
                    'estado': d.estado,
                    'centro_destino': d.centro_destino.nombre if d.centro_destino else None,
                    'detalles_count': d.detalles.count(),
                    'created_at': d.created_at.isoformat() if d.created_at else None,
                }
                for d in ultimas
            ]
            
            # Verificar detalles
            total_detalles = DetalleDonacion.objects.count()
            detalles_sin_producto = DetalleDonacion.objects.filter(producto__isnull=True).count()
            
            return Response({
                'tabla_existe': True,
                'total_donaciones_raw': total_raw,
                'total_donaciones_orm': todas.count(),
                'por_estado': por_estado,
                'ultimas_donaciones': ultimas_data,
                'detalles': {
                    'total': total_detalles,
                    'sin_producto': detalles_sin_producto,
                },
                'usuario': {
                    'id': request.user.pk,
                    'username': request.user.username,
                    'rol': getattr(request.user, 'rol', 'N/A'),
                }
            })
        except Exception as e:
            logger.exception(f"Error en diagnóstico de donaciones: {e}")
            return Response({
                'error': str(e),
                'tipo_error': type(e).__name__,
                'tabla_existe': False,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='exportar-excel')
    def exportar_excel(self, request):
        """
        Exporta las donaciones a Excel con formato profesional.
        Respeta los filtros aplicados en la consulta.
        """
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from django.http import HttpResponse
        from django.utils import timezone
        
        try:
            donaciones = self.get_queryset()
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Donaciones'
            
            # Título
            ws.merge_cells('A1:J1')
            ws['A1'].value = 'REPORTE DE DONACIONES RECIBIDAS'
            ws['A1'].font = Font(bold=True, size=14, color='632842')
            ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
            
            ws.merge_cells('A2:J2')
            ws['A2'].value = f'Generado el {timezone.now().strftime("%d/%m/%Y %H:%M")}'
            ws['A2'].font = Font(size=10, italic=True)
            ws['A2'].alignment = Alignment(horizontal='center')
            
            ws.append([])
            
            # Encabezados
            headers = [
                'Número', 'Donante', 'Tipo Donante', 'RFC', 
                'Fecha Donación', 'Fecha Recepción', 'Centro Destino',
                'Estado', 'Productos', 'Unidades Totales'
            ]
            ws.append(headers)
            
            header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=11)
            
            for cell in ws[4]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Datos
            for donacion in donaciones:
                total_productos = donacion.detalles.count() if hasattr(donacion, 'detalles') else 0
                total_unidades = sum(d.cantidad for d in donacion.detalles.all()) if hasattr(donacion, 'detalles') else 0
                
                ws.append([
                    donacion.numero,
                    donacion.donante_nombre,
                    donacion.donante_tipo,
                    donacion.donante_rfc or '',
                    donacion.fecha_donacion.strftime('%d/%m/%Y') if donacion.fecha_donacion else '',
                    donacion.fecha_recepcion.strftime('%d/%m/%Y') if donacion.fecha_recepcion else '',
                    donacion.centro_destino.nombre if donacion.centro_destino else 'Sin asignar',
                    donacion.estado,
                    total_productos,
                    total_unidades
                ])
            
            # Ajustar anchos
            column_widths = [15, 35, 15, 15, 15, 15, 30, 12, 12, 15]
            for i, width in enumerate(column_widths, 1):
                ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width
            
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            filename = f'donaciones_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            wb.save(response)
            return response
            
        except Exception as e:
            logger.error(f"Error exportando donaciones: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='plantilla-excel')
    def plantilla_excel(self, request):
        """
        Genera plantilla Excel simplificada para importar donaciones.
        UNA SOLA HOJA con todos los campos necesarios.
        Se vincula al catálogo de productos de donación mediante clave.
        """
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from openpyxl.worksheet.datavalidation import DataValidation
        from django.http import HttpResponse
        
        try:
            wb = openpyxl.Workbook()
            
            # Estilos
            header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
            example_font = Font(italic=True, color='888888')
            thin_border = Border(
                left=Side(style='thin'), right=Side(style='thin'),
                top=Side(style='thin'), bottom=Side(style='thin')
            )
            
            # Obtener productos del catálogo de donaciones para validación
            from core.models import ProductoDonacion
            productos_donacion = ProductoDonacion.objects.filter(activo=True).order_by('nombre')
            claves_validas = [p.clave for p in productos_donacion]
            producto_ejemplo = productos_donacion.first()
            clave_ejemplo = producto_ejemplo.clave if producto_ejemplo else 'DON-001'
            
            # ========== HOJA PRINCIPAL DE DONACIONES ==========
            ws = wb.active
            ws.title = 'Donaciones'
            
            # Título
            ws.merge_cells('A1:L1')
            ws['A1'].value = 'PLANTILLA DE IMPORTACIÓN DE DONACIONES'
            ws['A1'].font = Font(bold=True, size=14, color='632842')
            ws['A1'].alignment = Alignment(horizontal='center')
            
            # Instrucciones breves
            ws.merge_cells('A2:L2')
            ws['A2'].value = '⚠️ Columnas con * son obligatorias. ELIMINE las filas de ejemplo (grises) antes de importar.'
            ws['A2'].font = Font(italic=True, size=10, color='CC0000')
            
            ws.append([])  # Fila 3 vacía
            
            # Encabezados - Fila 4
            headers = [
                'numero *',           # Número de la donación
                'donante_nombre *',   # Nombre del donante
                'fecha_donacion *',   # Fecha de la donación (YYYY-MM-DD)
                'donante_tipo',       # empresa, gobierno, ong, particular, otro
                'producto_clave *',   # Clave del producto (del catálogo)
                'cantidad *',         # Cantidad donada
                'numero_lote',        # Número de lote (opcional)
                'fecha_caducidad',    # Fecha de caducidad (opcional)
                'estado_producto',    # bueno, regular, malo
                'donante_contacto',   # Email o teléfono del donante
                'notas',              # Notas adicionales
                'documento_donacion'  # Número de documento/factura
            ]
            ws.append(headers)
            
            # Estilo de encabezados
            for cell in ws[4]:
                cell.fill = header_fill
                cell.font = Font(bold=True, color='FFFFFF')
                cell.border = thin_border
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            
            # Filas de ejemplo
            ejemplos = [
                ['DON-2024-001', 'Farmacéutica Nacional SA', '2024-06-15', 'empresa',
                 clave_ejemplo, 100, 'LOTE-001', '2025-12-31', 'bueno', 
                 'contacto@farma.com', 'Donación anual', 'FAC-12345'],
                ['DON-2024-001', 'Farmacéutica Nacional SA', '2024-06-15', 'empresa',
                 clave_ejemplo, 50, 'LOTE-002', '2026-06-30', 'bueno', 
                 '', 'Mismo donante, otro producto', ''],
                ['DON-2024-002', 'Cruz Roja Mexicana', '2024-07-20', 'ong',
                 clave_ejemplo, 200, '', '', 'regular', 
                 'donaciones@cruzroja.mx', '', 'DOC-CRM-789'],
            ]
            
            for ejemplo in ejemplos:
                ws.append(ejemplo)
            
            # Aplicar formato gris a ejemplos (filas 5, 6, 7)
            for row_num in [5, 6, 7]:
                for cell in ws[row_num]:
                    cell.font = example_font
                    cell.border = thin_border
            
            # Validación para tipo de donante
            dv_tipo = DataValidation(
                type='list',
                formula1='"empresa,gobierno,ong,particular,otro"',
                allow_blank=True
            )
            dv_tipo.error = 'Seleccione un tipo válido'
            dv_tipo.errorTitle = 'Tipo inválido'
            ws.add_data_validation(dv_tipo)
            dv_tipo.add('D5:D1000')
            
            # Validación para estado del producto
            dv_estado = DataValidation(
                type='list',
                formula1='"bueno,regular,malo"',
                allow_blank=True
            )
            dv_estado.error = 'Seleccione un estado válido'
            dv_estado.errorTitle = 'Estado inválido'
            ws.add_data_validation(dv_estado)
            dv_estado.add('I5:I1000')
            
            # Ajustar anchos de columna
            column_widths = {
                'A': 18, 'B': 35, 'C': 15, 'D': 12, 'E': 15, 'F': 10,
                'G': 15, 'H': 15, 'I': 12, 'J': 25, 'K': 30, 'L': 18
            }
            for col, width in column_widths.items():
                ws.column_dimensions[col].width = width
            
            # ========== HOJA DE CATÁLOGO (referencia) ==========
            ws_cat = wb.create_sheet(title='Catálogo Productos')
            ws_cat.merge_cells('A1:D1')
            ws_cat['A1'].value = 'CATÁLOGO DE PRODUCTOS DE DONACIÓN'
            ws_cat['A1'].font = Font(bold=True, size=12, color='632842')
            ws_cat['A1'].alignment = Alignment(horizontal='center')
            
            ws_cat['A2'].value = 'Use estas claves en la columna "producto_clave" de la hoja Donaciones'
            ws_cat['A2'].font = Font(italic=True, size=10)
            ws_cat.merge_cells('A2:D2')
            
            ws_cat.append([])
            ws_cat.append(['Clave', 'Nombre', 'Unidad', 'Presentación'])
            
            for cell in ws_cat[4]:
                cell.fill = header_fill
                cell.font = Font(bold=True, color='FFFFFF')
                cell.border = thin_border
            
            if productos_donacion.count() == 0:
                ws_cat.append(['⚠️ NO HAY PRODUCTOS EN EL CATÁLOGO'])
                ws_cat['A5'].font = Font(color='CC0000', bold=True)
            else:
                for prod in productos_donacion[:500]:
                    ws_cat.append([prod.clave, prod.nombre, prod.unidad_medida, prod.presentacion or ''])
            
            ws_cat.column_dimensions['A'].width = 15
            ws_cat.column_dimensions['B'].width = 45
            ws_cat.column_dimensions['C'].width = 15
            ws_cat.column_dimensions['D'].width = 25
            
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="plantilla_donaciones.xlsx"'
            wb.save(response)
            return response
            
        except Exception as e:
            logger.error(f"Error generando plantilla: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='importar-excel')
    def importar_excel(self, request):
        """
        Importa donaciones desde archivo Excel con formato simplificado.
        
        UNA SOLA HOJA 'Donaciones' con campos combinados:
        - numero *: Número único de la donación
        - donante_nombre *: Nombre del donante
        - fecha_donacion *: Fecha de la donación
        - donante_tipo: empresa, gobierno, ong, particular, otro
        - producto_clave *: Clave del producto (del catálogo)
        - cantidad *: Cantidad donada
        - numero_lote: Número de lote (opcional)
        - fecha_caducidad: Fecha de caducidad (opcional)
        - estado_producto: bueno, regular, malo
        - donante_contacto: Email o teléfono del donante
        - notas: Notas adicionales
        - documento_donacion: Número de documento/factura
        
        Agrupa automáticamente las filas por número de donación.
        """
        import openpyxl
        from django.db import transaction
        from core.models import Donacion, DetalleDonacion, ProductoDonacion, Centro
        
        archivo = request.FILES.get('archivo') or request.FILES.get('file')
        if not archivo:
            return Response({'error': 'No se proporcionó archivo'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            wb = openpyxl.load_workbook(archivo, data_only=True)
            
            # Buscar hoja de donaciones
            ws = None
            for sheet_name in wb.sheetnames:
                name_lower = sheet_name.lower().strip()
                if 'donacion' in name_lower or name_lower == 'hoja1' or name_lower == 'sheet1':
                    ws = wb[sheet_name]
                    break
                # Ignorar hojas de detalles - ya no usamos hoja separada
            
            if not ws:
                ws = wb.active
            
            if not ws:
                return Response({'error': 'No se encontró hoja de donaciones válida'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            # Funciones auxiliares
            def normalizar_header(val):
                if not val:
                    return ''
                return str(val).lower().strip().replace('_', ' ').replace('-', ' ').replace('*', '')
            
            def buscar_encabezados(ws, aliases_dict, min_matches=3):
                """Busca fila de encabezados en las primeras 10 filas"""
                for row_num in range(1, min(11, ws.max_row + 1)):
                    row_values = [cell.value for cell in ws[row_num]]
                    matches = 0
                    col_map = {}
                    
                    for col_idx, val in enumerate(row_values):
                        header_norm = normalizar_header(val)
                        if not header_norm:
                            continue
                        
                        for field, aliases in aliases_dict.items():
                            if field not in col_map:
                                if header_norm in aliases or any(alias in header_norm for alias in aliases):
                                    col_map[field] = col_idx
                                    matches += 1
                                    break
                    
                    if matches >= min_matches:
                        return row_num, col_map
                
                return 4, {}  # Asume fila 4 como encabezado si no encuentra
            
            def get_val(row, field, col_map, default=None):
                if field not in col_map:
                    return default
                idx = col_map[field]
                if idx < len(row):
                    val = row[idx]
                    return val if val not in [None, '', 'None'] else default
                return default
            
            def parse_fecha(val):
                if not val:
                    return None
                if hasattr(val, 'date'):
                    return val.date() if hasattr(val, 'date') else val
                if hasattr(val, 'strftime'):
                    return val
                val_str = str(val).strip()
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%d.%m.%Y']:
                    try:
                        return datetime.strptime(val_str, fmt).date()
                    except:
                        continue
                return None
            
            def es_fila_ejemplo(row):
                """Detecta si una fila es un ejemplo que debe ignorarse"""
                for cell in row:
                    if cell:
                        cell_str = str(cell).upper()
                        # Detecta filas de ejemplo por contenido típico
                        if any(marca in cell_str for marca in ['[EJEMPLO]', 'EJEMPLO', 'PRUEBA', 'TEST', 'SAMPLE']):
                            return True
                        # También detecta patrones de ejemplo comunes
                        if 'FARMACÉUTICA NACIONAL' in cell_str or 'CRUZ ROJA' in cell_str:
                            return True
                return False
            
            # Aliases para la hoja unificada (formato simplificado)
            FIELD_ALIASES = {
                'numero': ['numero', 'número', 'num', 'no', 'id', 'codigo', 'folio'],
                'donante_nombre': ['donante nombre', 'donante', 'nombre donante', 'nombre'],
                'fecha_donacion': ['fecha donacion', 'fecha', 'fecha recepcion'],
                'donante_tipo': ['donante tipo', 'tipo donante', 'tipo'],
                'producto_clave': ['producto clave', 'clave producto', 'producto', 'clave'],
                'cantidad': ['cantidad', 'cant', 'unidades'],
                'numero_lote': ['numero lote', 'lote', 'no lote'],
                'fecha_caducidad': ['fecha caducidad', 'caducidad', 'vencimiento'],
                'estado_producto': ['estado producto', 'estado', 'condicion'],
                'donante_contacto': ['donante contacto', 'contacto', 'telefono', 'email'],
                'notas': ['notas', 'observaciones', 'comentarios'],
                'documento': ['documento donacion', 'documento', 'referencia', 'factura'],
            }
            
            resultados = {
                'donaciones_creadas': 0,
                'detalles_creados': 0,
                'errores': [],
                'exitos': []
            }
            
            # Detectar encabezados
            header_row, col_map = buscar_encabezados(ws, FIELD_ALIASES)
            
            # Si no hay mapa, usar posiciones por defecto del formato simplificado
            if not col_map or len(col_map) < 3:
                col_map = {
                    'numero': 0, 'donante_nombre': 1, 'fecha_donacion': 2, 'donante_tipo': 3,
                    'producto_clave': 4, 'cantidad': 5, 'numero_lote': 6, 'fecha_caducidad': 7,
                    'estado_producto': 8, 'donante_contacto': 9, 'notas': 10, 'documento': 11
                }
            
            donaciones_map = {}  # numero -> instancia Donacion
            
            with transaction.atomic():
                # Procesar todas las filas agrupando por número de donación
                for row_num, row in enumerate(ws.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1):
                    if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                        continue
                    
                    # Ignorar filas de ejemplo
                    if es_fila_ejemplo(row):
                        continue
                    
                    try:
                        numero = get_val(row, 'numero', col_map)
                        donante_nombre = get_val(row, 'donante_nombre', col_map)
                        producto_clave = get_val(row, 'producto_clave', col_map)
                        cantidad_raw = get_val(row, 'cantidad', col_map)
                        
                        # Validar campos requeridos
                        if not numero:
                            resultados['errores'].append({
                                'fila': row_num, 'error': 'Número de donación es obligatorio'
                            })
                            continue
                        
                        if not donante_nombre:
                            resultados['errores'].append({
                                'fila': row_num, 'error': 'Nombre del donante es obligatorio'
                            })
                            continue
                        
                        if not producto_clave:
                            resultados['errores'].append({
                                'fila': row_num, 'error': 'Clave de producto es obligatoria'
                            })
                            continue
                        
                        numero = str(numero).strip()
                        producto_clave = str(producto_clave).strip()
                        
                        # Parsear cantidad
                        try:
                            cantidad = int(float(cantidad_raw)) if cantidad_raw else 0
                        except:
                            cantidad = 0
                        
                        if cantidad <= 0:
                            resultados['errores'].append({
                                'fila': row_num, 'error': 'Cantidad debe ser mayor a 0'
                            })
                            continue
                        
                        # Buscar producto en catálogo de donaciones
                        producto_donacion = ProductoDonacion.objects.filter(clave__iexact=producto_clave, activo=True).first()
                        if not producto_donacion:
                            producto_donacion = ProductoDonacion.objects.filter(nombre__icontains=producto_clave, activo=True).first()
                        
                        if not producto_donacion:
                            resultados['errores'].append({
                                'fila': row_num, 
                                'error': f'Producto "{producto_clave}" no encontrado en Catálogo de Donaciones'
                            })
                            continue
                        
                        # Crear donación si no existe para este número
                        if numero not in donaciones_map:
                            # Verificar si ya existe en BD
                            donacion_existente = Donacion.objects.filter(numero=numero).first()
                            if donacion_existente:
                                donaciones_map[numero] = donacion_existente
                            else:
                                # Buscar centro (opcional)
                                centro_destino = None
                                
                                # Parsear fecha
                                fecha_val = get_val(row, 'fecha_donacion', col_map)
                                fecha = parse_fecha(fecha_val) or timezone.now().date()
                                
                                # Normalizar tipo de donante
                                tipo_donante = str(get_val(row, 'donante_tipo', col_map, 'empresa')).lower().strip()
                                if tipo_donante not in ['empresa', 'gobierno', 'ong', 'particular', 'otro']:
                                    tipo_donante = 'empresa'
                                
                                donacion = Donacion.objects.create(
                                    numero=numero,
                                    donante_nombre=str(donante_nombre).strip()[:200],
                                    donante_tipo=tipo_donante,
                                    donante_contacto=str(get_val(row, 'donante_contacto', col_map, '')).strip()[:200] or None,
                                    fecha_donacion=fecha,
                                    centro_destino=centro_destino,
                                    notas=str(get_val(row, 'notas', col_map, '')).strip() or None,
                                    documento_donacion=str(get_val(row, 'documento', col_map, '')).strip()[:100] or None,
                                    recibido_por=request.user,
                                    estado='pendiente'
                                )
                                donaciones_map[numero] = donacion
                                resultados['donaciones_creadas'] += 1
                        
                        # Obtener donación
                        donacion = donaciones_map[numero]
                        
                        # Parsear fecha caducidad
                        fecha_cad = parse_fecha(get_val(row, 'fecha_caducidad', col_map))
                        
                        # Normalizar estado
                        estado = str(get_val(row, 'estado_producto', col_map, 'bueno')).lower().strip()
                        if estado not in ['bueno', 'regular', 'malo']:
                            estado = 'bueno'
                        
                        # Crear detalle de donación
                        DetalleDonacion.objects.create(
                            donacion=donacion,
                            producto_donacion=producto_donacion,
                            producto=None,  # Legacy - no usar catálogo principal
                            numero_lote=str(get_val(row, 'numero_lote', col_map, '')).strip()[:50] or None,
                            cantidad=cantidad,
                            cantidad_disponible=cantidad,
                            fecha_caducidad=fecha_cad,
                            estado_producto=estado,
                            notas=str(get_val(row, 'notas', col_map, '')).strip() or None
                        )
                        resultados['detalles_creados'] += 1
                        resultados['exitos'].append({
                            'fila': row_num, 'donacion': numero, 'producto': producto_clave, 'cantidad': cantidad
                        })
                        
                    except Exception as e:
                        resultados['errores'].append({
                            'fila': row_num, 'error': str(e)
                        })
            
            logger.info(f"Importación de donaciones por {request.user.username}: "
                       f"{resultados['donaciones_creadas']} donaciones, {resultados['detalles_creados']} detalles")
            
            status_code = status.HTTP_200_OK if len(resultados['errores']) == 0 else status.HTTP_207_MULTI_STATUS
            
            return Response({
                'mensaje': 'Importación completada',
                'resultados': {
                    'exitosos': resultados['detalles_creados'],
                    'fallidos': len(resultados['errores']),
                    'donaciones_creadas': resultados['donaciones_creadas'],
                    'errores': resultados['errores']
                },
                'resumen': {
                    'donaciones_creadas': resultados['donaciones_creadas'],
                    'detalles_creados': resultados['detalles_creados'],
                    'total_errores': len(resultados['errores'])
                },
                'exitos': resultados['exitos'],
                'errores': resultados['errores']
            }, status=status_code)
            
        except Exception as e:
            logger.error(f"Error importando donaciones: {e}")
            return Response({
                'error': 'Error al procesar archivo',
                'mensaje': str(e),
                'sugerencia': 'Verifique que el archivo tenga la hoja "Donaciones" con los campos requeridos'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# CATALOGO DE PRODUCTOS DONACIONES - COMPLETAMENTE INDEPENDIENTE
# =============================================================================

class ProductoDonacionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el catálogo INDEPENDIENTE de productos de donaciones.
    Este catálogo es COMPLETAMENTE SEPARADO del catálogo principal de productos.
    Las donaciones pueden tener productos con claves y nombres diferentes.
    
    Solo ADMIN y FARMACIA pueden crear/editar/eliminar.
    Cualquier usuario autenticado con permiso de donaciones puede ver.
    """
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['clave', 'nombre', 'descripcion']
    ordering_fields = ['clave', 'nombre', 'created_at']
    ordering = ['nombre']
    
    def get_permissions(self):
        """Permisos según la acción:
        - list, retrieve: IsAuthenticated
        - create, update, destroy: IsFarmaciaRole (admin/farmacia)
        """
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsFarmaciaRole()]
    
    def get_queryset(self):
        from core.models import ProductoDonacion
        queryset = ProductoDonacion.objects.all()
        
        # Filtrar por activo (por defecto solo activos)
        activo = self.request.query_params.get('activo', 'true')
        if activo.lower() == 'true':
            queryset = queryset.filter(activo=True)
        elif activo.lower() == 'false':
            queryset = queryset.filter(activo=False)
        # Si activo='all', no filtrar
        
        return queryset.order_by('nombre')
    
    def get_serializer_class(self):
        from core.serializers import ProductoDonacionSerializer
        return ProductoDonacionSerializer
    
    def perform_create(self, serializer):
        producto = serializer.save()
        logger.info(f"Producto de donación {producto.clave} creado por {self.request.user.username}")
    
    def perform_update(self, serializer):
        producto = serializer.save()
        logger.info(f"Producto de donación {producto.clave} actualizado por {self.request.user.username}")
    
    def perform_destroy(self, instance):
        clave = instance.clave
        instance.delete()
        logger.info(f"Producto de donación {clave} eliminado por {self.request.user.username}")
    
    @action(detail=False, methods=['get'], url_path='buscar')
    def buscar(self, request):
        """Búsqueda rápida de productos de donación por clave o nombre."""
        from core.models import ProductoDonacion
        from core.serializers import ProductoDonacionSerializer
        
        q = request.query_params.get('q', '').strip()
        if len(q) < 2:
            return Response([])
        
        productos = ProductoDonacion.objects.filter(
            models.Q(clave__icontains=q) | models.Q(nombre__icontains=q),
            activo=True
        )[:20]
        
        return Response(ProductoDonacionSerializer(productos, many=True).data)

    @action(detail=False, methods=['get'], url_path='exportar-excel')
    def exportar_excel(self, request):
        """
        Exporta el catálogo de productos de donación a Excel con formato profesional.
        """
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from django.http import HttpResponse
        from django.utils import timezone
        from core.models import ProductoDonacion
        
        try:
            productos = ProductoDonacion.objects.filter(activo=True).order_by('clave')
            
            # Crear libro de Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Catálogo Donaciones'
            
            # Título del reporte
            ws.merge_cells('A1:F1')
            titulo_cell = ws['A1']
            titulo_cell.value = 'CATÁLOGO DE PRODUCTOS DE DONACIÓN'
            titulo_cell.font = Font(bold=True, size=14, color='632842')
            titulo_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Fecha de generación
            ws.merge_cells('A2:F2')
            fecha_cell = ws['A2']
            fecha_cell.value = f'Generado el {timezone.now().strftime("%d/%m/%Y %H:%M")}'
            fecha_cell.font = Font(size=10, italic=True)
            fecha_cell.alignment = Alignment(horizontal='center')
            
            # Espacio
            ws.append([])
            
            # Encabezados - Alineados con modelo ProductoDonacion
            headers = ['Clave', 'Nombre', 'Descripción', 'Unidad Medida', 'Presentación', 'Activo']
            ws.append(headers)
            
            # Estilo de encabezados
            header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=11)
            header_alignment = Alignment(horizontal='center', vertical='center')
            
            for col_num, cell in enumerate(ws[4], 1):
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
            
            # Datos - campos alineados con modelo ProductoDonacion
            for producto in productos:
                ws.append([
                    producto.clave,
                    producto.nombre,
                    producto.descripcion or '',
                    producto.unidad_medida or 'PIEZA',
                    producto.presentacion or '',
                    'Sí' if producto.activo else 'No'
                ])
            
            # Ajustar anchos de columna
            ws.column_dimensions['A'].width = 15
            ws.column_dimensions['B'].width = 40
            ws.column_dimensions['C'].width = 50
            ws.column_dimensions['D'].width = 15
            ws.column_dimensions['E'].width = 20
            ws.column_dimensions['F'].width = 10
            
            # Agregar bordes
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            for row in ws.iter_rows(min_row=4, max_row=ws.max_row, min_col=1, max_col=6):
                for cell in row:
                    cell.border = thin_border
            
            # Preparar respuesta
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            filename = f'catalogo_donaciones_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            wb.save(response)
            return response
            
        except Exception as e:
            return Response(
                {'error': f'Error al exportar: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='plantilla-excel')
    def plantilla_excel(self, request):
        """
        Genera una plantilla Excel para importación de productos de donación.
        Incluye ejemplos y validaciones.
        """
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        from django.http import HttpResponse
        
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Plantilla Productos'
            
            # Título
            ws.merge_cells('A1:F1')
            titulo_cell = ws['A1']
            titulo_cell.value = 'PLANTILLA PARA IMPORTAR PRODUCTOS DE DONACIÓN'
            titulo_cell.font = Font(bold=True, size=14, color='632842')
            titulo_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Instrucciones - fila 2
            ws.merge_cells('A2:F2')
            ws['A2'].value = 'Complete los datos. Columnas con * son obligatorias. Unidades: PIEZA, CAJA, FRASCO, TABLETA, AMPOLLETA, etc.'
            ws['A2'].font = Font(size=10, italic=True)
            
            # Nota importante - fila 3
            ws.merge_cells('A3:F3')
            ws['A3'].value = '⚠️ BORRE las filas de ejemplo antes de importar (o simplemente inicie sus datos desde fila 5)'
            ws['A3'].font = Font(size=9, italic=True, color='CC0000')
            
            # Encabezados - Alineados con modelo ProductoDonacion en BD - fila 4
            headers = [
                'clave *',           # Clave única del producto
                'nombre *',          # Nombre del producto
                'descripcion',       # Descripción
                'unidad_medida',     # PIEZA, CAJA, FRASCO, etc.
                'presentacion',      # Forma farmacéutica (tabletas, jarabe, etc.)
            ]
            # Escribir encabezados en fila 4 explícitamente
            for col_idx, header in enumerate(headers, 1):
                ws.cell(row=4, column=col_idx, value=header)
            
            # Estilo de encabezados
            header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=11)
            
            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=4, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Filas de ejemplo (las elimina el usuario antes de importar)
            # Escribir en filas 5 y 6 explícitamente
            ejemplo1 = ['EJEMPLO-001', 'Paracetamol 500mg (BORRAR ESTA FILA)', 'Tabletas para fiebre y dolor', 'PIEZA', 'Tabletas']
            ejemplo2 = ['EJEMPLO-002', 'Alcohol al 70% (BORRAR ESTA FILA)', 'Solución desinfectante', 'FRASCO', 'Frasco 250ml']
            
            for col_idx, val in enumerate(ejemplo1, 1):
                ws.cell(row=5, column=col_idx, value=val)
            for col_idx, val in enumerate(ejemplo2, 1):
                ws.cell(row=6, column=col_idx, value=val)
            
            # Estilos de las filas de ejemplo (color gris para indicar que son ejemplos)
            example_font = Font(italic=True, color='888888')
            for row_num in [5, 6]:
                for col in range(1, 6):
                    ws.cell(row=row_num, column=col).font = example_font
            
            # Ajustar anchos
            ws.column_dimensions['A'].width = 15
            ws.column_dimensions['B'].width = 35
            ws.column_dimensions['C'].width = 40
            ws.column_dimensions['D'].width = 15
            ws.column_dimensions['E'].width = 20
            
            # Respuesta
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="plantilla_catalogo_donaciones.xlsx"'
            
            wb.save(response)
            return response
            
        except Exception as e:
            return Response(
                {'error': f'Error al generar plantilla: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='importar-excel')
    def importar_excel(self, request):
        """
        Importa productos de donación desde un archivo Excel.
        
        Formato esperado (alineado con modelo ProductoDonacion en BD):
        - clave: Clave única del producto (obligatorio)
        - nombre: Nombre del producto (obligatorio)
        - descripcion: Descripción (opcional)
        - unidad_medida: Unidad de medida (opcional, default: PIEZA)
        - presentacion: Forma farmacéutica (opcional)
        """
        import openpyxl
        from django.db import transaction
        from core.models import ProductoDonacion
        
        archivo = request.FILES.get('archivo')
        if not archivo:
            return Response(
                {'error': 'No se proporcionó archivo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not archivo.name.endswith(('.xlsx', '.xls')):
            return Response(
                {'error': 'El archivo debe ser Excel (.xlsx o .xls)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            wb = openpyxl.load_workbook(archivo, data_only=True)
            ws = wb.active
            
            # Buscar fila de encabezados (puede estar en fila 4 si usa plantilla)
            header_row = None
            for row_num in range(1, 10):
                cell_value = ws.cell(row=row_num, column=1).value
                if cell_value and 'clave' in str(cell_value).lower():
                    header_row = row_num
                    break
            
            if not header_row:
                header_row = 1
            
            # Mapear columnas
            headers = {}
            for col_num, cell in enumerate(ws[header_row], 1):
                if cell.value:
                    header_name = str(cell.value).lower().strip()
                    header_name = header_name.replace(' *', '').replace('*', '')
                    headers[header_name] = col_num
            
            required_cols = ['clave', 'nombre']
            for col in required_cols:
                if col not in headers:
                    return Response(
                        {'error': f'Columna requerida no encontrada: {col}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Procesar filas
            resultados = {
                'creados': 0,
                'actualizados': 0,
                'fallidos': 0,
                'errores': []
            }
            
            unidades_validas = ['PIEZA', 'CAJA', 'FRASCO', 'TABLETA', 'AMPOLLETA', 'SOBRES', 'LITRO', 'MILILITRO', 'GRAMO', 'KILOGRAMO']
            
            with transaction.atomic():
                for row_num in range(header_row + 1, ws.max_row + 1):
                    clave = ws.cell(row=row_num, column=headers['clave']).value
                    
                    # Saltar filas vacías
                    if not clave:
                        continue
                    
                    clave_str = str(clave).strip().upper()
                    
                    # Saltar filas de ejemplo, notas o instrucciones
                    skip_keywords = ['NOTA', 'EJEMPLO', 'INSTRUCCION', 'BORRAR', '---', '***']
                    if any(keyword in clave_str for keyword in skip_keywords):
                        continue
                    
                    # Saltar si la clave empieza con palabras especiales
                    if clave_str.startswith(('NOTA:', 'EJEMPLO-', 'EJ:', 'EJ-')):
                        continue
                    
                    try:
                        nombre = ws.cell(row=row_num, column=headers['nombre']).value
                        descripcion = ws.cell(row=row_num, column=headers.get('descripcion', 0)).value if headers.get('descripcion') else None
                        unidad_medida = ws.cell(row=row_num, column=headers.get('unidad_medida', 0)).value if headers.get('unidad_medida') else 'PIEZA'
                        presentacion = ws.cell(row=row_num, column=headers.get('presentacion', 0)).value if headers.get('presentacion') else None
                        
                        # Validaciones
                        if not nombre:
                            raise ValueError('Nombre es requerido')
                        
                        clave = str(clave).strip().upper()
                        nombre = str(nombre).strip()
                        
                        if unidad_medida:
                            unidad_medida = str(unidad_medida).strip().upper()
                            if unidad_medida not in unidades_validas:
                                unidad_medida = 'PIEZA'
                        else:
                            unidad_medida = 'PIEZA'
                        
                        # Crear o actualizar producto - campos alineados con modelo ProductoDonacion
                        producto, created = ProductoDonacion.objects.update_or_create(
                            clave=clave,
                            defaults={
                                'nombre': nombre,
                                'descripcion': str(descripcion).strip() if descripcion else None,
                                'unidad_medida': unidad_medida,
                                'presentacion': str(presentacion).strip() if presentacion else None,
                                'activo': True
                            }
                        )
                        
                        if created:
                            resultados['creados'] += 1
                        else:
                            resultados['actualizados'] += 1
                        
                    except Exception as e:
                        resultados['fallidos'] += 1
                        resultados['errores'].append({
                            'fila': row_num,
                            'clave': str(clave) if clave else 'N/A',
                            'error': str(e)
                        })
            
            return Response({
                'mensaje': f'Importación completada. Creados: {resultados["creados"]}, Actualizados: {resultados["actualizados"]}, Fallidos: {resultados["fallidos"]}',
                'resultados': resultados
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error al procesar archivo: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DetalleDonacionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar detalles de donaciones.
    Usa el catálogo independiente de ProductoDonacion.
    Solo ADMIN y FARMACIA pueden modificar.
    """
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'producto_donacion__nombre', 'producto_donacion__clave',  # Nuevo catálogo
        'producto__nombre', 'producto__clave',  # Legacy
        'numero_lote', 'donacion__numero'
    ]
    ordering_fields = ['created_at', 'fecha_caducidad', 'cantidad_disponible']
    ordering = ['-created_at']
    
    def get_permissions(self):
        """Permisos según la acción:
        - list, retrieve: IsAuthenticated
        - create, update, destroy: IsFarmaciaRole
        """
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsFarmaciaRole()]
    
    def get_queryset(self):
        from core.models import DetalleDonacion
        queryset = DetalleDonacion.objects.select_related(
            'donacion', 'producto', 'producto_donacion'  # Incluir ambos catálogos
        ).all()
        
        # Filtrar por donacion si se especifica
        donacion_id = self.request.query_params.get('donacion')
        if donacion_id:
            queryset = queryset.filter(donacion_id=donacion_id)
        
        # Filtrar solo con stock disponible
        solo_disponible = self.request.query_params.get('disponible')
        if solo_disponible == 'true':
            queryset = queryset.filter(cantidad_disponible__gt=0)
        
        # Filtrar por estado de producto
        estado = self.request.query_params.get('estado_producto')
        if estado:
            queryset = queryset.filter(estado_producto=estado)
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        from core.serializers import DetalleDonacionSerializer
        return DetalleDonacionSerializer


# =============================================================================
# SALIDA DONACION VIEWSET (Control de entregas del almacen donaciones)
# =============================================================================

class SalidaDonacionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar salidas/entregas del almacen de donaciones.
    Control interno sin afectar movimientos principales.
    Solo ADMIN y FARMACIA pueden registrar entregas.
    
    Endpoints adicionales:
    - GET /salidas-donaciones/exportar-excel/ - Exportar entregas a Excel
    - POST /salidas-donaciones/importar-excel/ - Importar entregas desde Excel
    - GET /salidas-donaciones/plantilla-excel/ - Descargar plantilla de importación
    """
    pagination_class = StandardResultsSetPagination
    http_method_names = ['get', 'post', 'head', 'options']  # No permite editar ni eliminar
    
    def get_permissions(self):
        """Permisos según la acción:
        - list, retrieve, exportar_excel, plantilla_excel: IsAuthenticated
        - create, importar_excel: IsFarmaciaRole
        """
        if self.action in ['list', 'retrieve', 'exportar_excel', 'plantilla_excel']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsFarmaciaRole()]
    
    def get_queryset(self):
        from core.models import SalidaDonacion
        queryset = SalidaDonacion.objects.select_related(
            'detalle_donacion', 'detalle_donacion__producto', 
            'detalle_donacion__donacion', 'entregado_por'
        ).all()
        
        # Filtrar por detalle de donacion
        detalle_id = self.request.query_params.get('detalle_donacion')
        if detalle_id:
            queryset = queryset.filter(detalle_donacion_id=detalle_id)
        
        # Filtrar por donacion
        donacion_id = self.request.query_params.get('donacion')
        if donacion_id:
            queryset = queryset.filter(detalle_donacion__donacion_id=donacion_id)
        
        # Filtrar por destinatario
        destinatario = self.request.query_params.get('destinatario')
        if destinatario:
            queryset = queryset.filter(destinatario__icontains=destinatario)
        
        # Filtrar por fecha
        fecha_desde = self.request.query_params.get('fecha_desde')
        if fecha_desde:
            queryset = queryset.filter(fecha_entrega__date__gte=fecha_desde)
        
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        if fecha_hasta:
            queryset = queryset.filter(fecha_entrega__date__lte=fecha_hasta)
        
        # Búsqueda general
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(destinatario__icontains=search) |
                Q(motivo__icontains=search) |
                Q(detalle_donacion__producto__nombre__icontains=search) |
                Q(detalle_donacion__producto__clave__icontains=search)
            )
        
        return queryset.order_by('-fecha_entrega')
    
    def get_serializer_class(self):
        from core.serializers import SalidaDonacionSerializer
        return SalidaDonacionSerializer
    
    @action(detail=False, methods=['get'], url_path='exportar-excel')
    def exportar_excel(self, request):
        """
        Exporta las entregas de donaciones a Excel con formato profesional.
        Respeta los filtros aplicados en la consulta.
        """
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from django.http import HttpResponse
        from django.utils import timezone
        
        try:
            entregas = self.get_queryset()
            
            # Crear libro de Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Entregas Donaciones'
            
            # Título del reporte
            ws.merge_cells('A1:H1')
            titulo_cell = ws['A1']
            titulo_cell.value = 'REPORTE DE ENTREGAS DE DONACIONES'
            titulo_cell.font = Font(bold=True, size=14, color='632842')
            titulo_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Fecha de generación
            ws.merge_cells('A2:H2')
            fecha_cell = ws['A2']
            fecha_cell.value = f'Generado el {timezone.now().strftime("%d/%m/%Y %H:%M")}'
            fecha_cell.font = Font(size=10, italic=True)
            fecha_cell.alignment = Alignment(horizontal='center')
            
            # Espacio
            ws.append([])
            
            # Encabezados
            headers = [
                '#', 'Fecha Entrega', 'Producto', 'Clave Producto',
                'Cantidad', 'Destinatario', 'Motivo', 'Entregado Por', 'Donación'
            ]
            ws.append(headers)
            
            # Estilo de encabezados
            header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=11)
            header_alignment = Alignment(horizontal='center', vertical='center')
            
            for col_num, cell in enumerate(ws[4], 1):
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
            
            # Datos
            for idx, entrega in enumerate(entregas, start=1):
                producto_nombre = ''
                producto_clave = ''
                donacion_numero = ''
                
                if entrega.detalle_donacion:
                    if entrega.detalle_donacion.producto:
                        producto_nombre = entrega.detalle_donacion.producto.nombre
                        producto_clave = entrega.detalle_donacion.producto.clave
                    if entrega.detalle_donacion.donacion:
                        donacion_numero = entrega.detalle_donacion.donacion.numero
                
                entregado_por_nombre = ''
                if entrega.entregado_por:
                    entregado_por_nombre = f"{entrega.entregado_por.first_name} {entrega.entregado_por.last_name}".strip()
                    if not entregado_por_nombre:
                        entregado_por_nombre = entrega.entregado_por.username
                
                fecha_str = entrega.fecha_entrega.strftime('%d/%m/%Y %H:%M') if entrega.fecha_entrega else ''
                
                ws.append([
                    idx,
                    fecha_str,
                    producto_nombre,
                    producto_clave,
                    entrega.cantidad,
                    entrega.destinatario,
                    entrega.motivo or '',
                    entregado_por_nombre,
                    donacion_numero
                ])
                
                # Estilo para filas
                row_num = idx + 4
                for cell in ws[row_num]:
                    cell.alignment = Alignment(vertical='center')
            
            # Ajustar anchos de columna
            ws.column_dimensions['A'].width = 6
            ws.column_dimensions['B'].width = 18
            ws.column_dimensions['C'].width = 40
            ws.column_dimensions['D'].width = 15
            ws.column_dimensions['E'].width = 10
            ws.column_dimensions['F'].width = 30
            ws.column_dimensions['G'].width = 30
            ws.column_dimensions['H'].width = 25
            ws.column_dimensions['I'].width = 15
            
            # Agregar bordes
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            for row in ws.iter_rows(min_row=4, max_row=ws.max_row, min_col=1, max_col=9):
                for cell in row:
                    cell.border = thin_border
            
            # Preparar respuesta
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            filename = f'entregas_donaciones_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            wb.save(response)
            return response
            
        except Exception as e:
            return Response(
                {'error': f'Error al exportar: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='plantilla-excel')
    def plantilla_excel(self, request):
        """
        Genera una plantilla Excel para importación de entregas.
        Incluye ejemplos y validaciones.
        """
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from openpyxl.utils.dataframe import dataframe_to_rows
        from openpyxl.worksheet.datavalidation import DataValidation
        from django.http import HttpResponse
        
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Plantilla Entregas'
            
            # Título
            ws.merge_cells('A1:F1')
            titulo_cell = ws['A1']
            titulo_cell.value = 'PLANTILLA PARA IMPORTAR ENTREGAS DE DONACIONES'
            titulo_cell.font = Font(bold=True, size=14, color='632842')
            titulo_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Instrucciones
            ws.merge_cells('A2:F2')
            ws['A2'].value = 'Complete los datos siguiendo el formato indicado. Las columnas marcadas con * son obligatorias.'
            ws['A2'].font = Font(size=10, italic=True)
            
            ws.append([])
            
            # Encabezados
            headers = [
                'detalle_donacion_id *',  # ID del detalle de donación
                'cantidad *',             # Cantidad a entregar
                'destinatario *',         # Nombre del destinatario
                'motivo',                 # Motivo de la entrega
                'notas'                   # Notas adicionales
            ]
            ws.append(headers)
            
            # Estilo de encabezados
            header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=11)
            
            for col_num, cell in enumerate(ws[4], 1):
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Fila de ejemplo
            ws.append([1, 10, 'Juan Pérez', 'Tratamiento médico', 'Entrega programada'])
            
            # Agregar nota sobre detalle_donacion_id
            ws.append([])
            ws.append(['NOTA: El detalle_donacion_id lo puede obtener desde el inventario de donaciones.'])
            ws['A7'].font = Font(italic=True, color='666666')
            
            # Ajustar anchos
            ws.column_dimensions['A'].width = 20
            ws.column_dimensions['B'].width = 12
            ws.column_dimensions['C'].width = 30
            ws.column_dimensions['D'].width = 30
            ws.column_dimensions['E'].width = 30
            
            # Segunda hoja con lista de detalles disponibles
            ws2 = wb.create_sheet(title='Inventario Disponible')
            ws2.merge_cells('A1:F1')
            ws2['A1'].value = 'INVENTARIO DE DONACIONES CON STOCK DISPONIBLE'
            ws2['A1'].font = Font(bold=True, size=12, color='632842')
            ws2['A1'].alignment = Alignment(horizontal='center')
            
            ws2.append([])
            headers2 = ['ID Detalle', 'Producto', 'Clave', 'Lote', 'Disponible', 'Donación']
            ws2.append(headers2)
            
            for cell in ws2[3]:
                cell.fill = header_fill
                cell.font = header_font
            
            # Obtener detalles con stock disponible
            from core.models import DetalleDonacion
            detalles = DetalleDonacion.objects.filter(
                cantidad_disponible__gt=0,
                donacion__estado='procesada'
            ).select_related('producto', 'donacion').order_by('producto__nombre')
            
            for det in detalles:
                ws2.append([
                    det.id,
                    det.producto.nombre if det.producto else '',
                    det.producto.clave if det.producto else '',
                    det.numero_lote or '',
                    det.cantidad_disponible,
                    det.donacion.numero if det.donacion else ''
                ])
            
            ws2.column_dimensions['A'].width = 12
            ws2.column_dimensions['B'].width = 40
            ws2.column_dimensions['C'].width = 15
            ws2.column_dimensions['D'].width = 15
            ws2.column_dimensions['E'].width = 12
            ws2.column_dimensions['F'].width = 15
            
            # Respuesta
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="plantilla_entregas_donaciones.xlsx"'
            
            wb.save(response)
            return response
            
        except Exception as e:
            return Response(
                {'error': f'Error al generar plantilla: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='importar-excel')
    def importar_excel(self, request):
        """
        Importa entregas de donaciones desde un archivo Excel.
        
        Formato esperado:
        - detalle_donacion_id: ID del detalle de donación (obligatorio)
        - cantidad: Cantidad a entregar (obligatorio)
        - destinatario: Nombre del destinatario (obligatorio)
        - motivo: Motivo de la entrega (opcional)
        - notas: Notas adicionales (opcional)
        """
        import openpyxl
        from django.db import transaction
        from core.models import DetalleDonacion, SalidaDonacion
        
        archivo = request.FILES.get('archivo')
        if not archivo:
            return Response(
                {'error': 'No se proporcionó archivo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not archivo.name.endswith(('.xlsx', '.xls')):
            return Response(
                {'error': 'El archivo debe ser Excel (.xlsx o .xls)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            wb = openpyxl.load_workbook(archivo, data_only=True)
            ws = wb.active
            
            # Buscar fila de encabezados (puede estar en fila 4 si usa plantilla)
            header_row = None
            for row_num in range(1, 10):
                cell_value = ws.cell(row=row_num, column=1).value
                if cell_value and 'detalle_donacion' in str(cell_value).lower():
                    header_row = row_num
                    break
            
            if not header_row:
                # Asumir que empieza en fila 1
                header_row = 1
            
            # Mapear columnas
            headers = {}
            for col_num, cell in enumerate(ws[header_row], 1):
                if cell.value:
                    header_name = str(cell.value).lower().strip()
                    header_name = header_name.replace(' *', '').replace('*', '')
                    headers[header_name] = col_num
            
            required_cols = ['detalle_donacion_id', 'cantidad', 'destinatario']
            for col in required_cols:
                if col not in headers:
                    return Response(
                        {'error': f'Columna requerida no encontrada: {col}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Procesar filas
            resultados = {
                'exitosos': 0,
                'fallidos': 0,
                'errores': []
            }
            
            with transaction.atomic():
                for row_num in range(header_row + 1, ws.max_row + 1):
                    # Verificar si la fila está vacía
                    detalle_id = ws.cell(row=row_num, column=headers['detalle_donacion_id']).value
                    if not detalle_id:
                        continue
                    
                    try:
                        cantidad = int(ws.cell(row=row_num, column=headers['cantidad']).value or 0)
                        destinatario = ws.cell(row=row_num, column=headers['destinatario']).value
                        motivo = ws.cell(row=row_num, column=headers.get('motivo', 0)).value if headers.get('motivo') else None
                        notas = ws.cell(row=row_num, column=headers.get('notas', 0)).value if headers.get('notas') else None
                        
                        # Validaciones
                        if not destinatario:
                            raise ValueError('Destinatario es requerido')
                        if cantidad <= 0:
                            raise ValueError('La cantidad debe ser mayor a 0')
                        
                        # Obtener detalle de donación
                        try:
                            detalle = DetalleDonacion.objects.select_related('donacion').get(pk=detalle_id)
                        except DetalleDonacion.DoesNotExist:
                            raise ValueError(f'Detalle de donación {detalle_id} no existe')
                        
                        # Verificar que la donación esté procesada
                        if detalle.donacion.estado != 'procesada':
                            raise ValueError(f'La donación {detalle.donacion.numero} no está procesada')
                        
                        # Verificar stock disponible
                        if cantidad > detalle.cantidad_disponible:
                            raise ValueError(
                                f'Stock insuficiente. Disponible: {detalle.cantidad_disponible}, Solicitado: {cantidad}'
                            )
                        
                        # Crear salida
                        salida = SalidaDonacion(
                            detalle_donacion=detalle,
                            cantidad=cantidad,
                            destinatario=str(destinatario).strip(),
                            motivo=str(motivo).strip() if motivo else None,
                            notas=str(notas).strip() if notas else None,
                            entregado_por=request.user
                        )
                        salida.save()
                        
                        resultados['exitosos'] += 1
                        
                    except Exception as e:
                        resultados['fallidos'] += 1
                        resultados['errores'].append({
                            'fila': row_num,
                            'error': str(e)
                        })
            
            return Response({
                'mensaje': f'Importación completada. Exitosos: {resultados["exitosos"]}, Fallidos: {resultados["fallidos"]}',
                'resultados': resultados
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error al procesar archivo: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='generar-pdf')
    def generar_pdf(self, request, pk=None):
        """
        Genera un recibo PDF para una salida de donación específica.
        Incluye campos de firma: Autoriza, Entrega, Recibe.
        
        Returns:
            PDF descargable con formato institucional
        """
        from django.http import HttpResponse
        from core.utils.pdf_reports import generar_recibo_salida_donacion
        from core.models import SalidaDonacion, Centro
        
        try:
            salida = self.get_object()
            
            # Preparar datos de la salida
            producto_nombre = ''
            lote = ''
            donacion_numero = ''
            
            if salida.detalle_donacion:
                if salida.detalle_donacion.producto:
                    producto_nombre = salida.detalle_donacion.producto.nombre
                lote = salida.detalle_donacion.numero_lote or ''
                if salida.detalle_donacion.donacion:
                    donacion_numero = salida.detalle_donacion.donacion.numero
            
            # Obtener nombre del centro si existe centro_destino
            centro_destino_nombre = salida.destinatario
            if hasattr(salida, 'centro_destino') and salida.centro_destino:
                try:
                    centro = Centro.objects.get(pk=salida.centro_destino)
                    centro_destino_nombre = centro.nombre
                except Centro.DoesNotExist:
                    pass
            
            # Usuario que registró
            usuario = ''
            if salida.entregado_por:
                usuario = f"{salida.entregado_por.first_name} {salida.entregado_por.last_name}".strip()
                if not usuario:
                    usuario = salida.entregado_por.username
            
            # Obtener estado de finalización
            es_finalizado = getattr(salida, 'finalizado', False)
            fecha_finalizado = getattr(salida, 'fecha_finalizado', None)
            
            salida_data = {
                'id': salida.id,
                'fecha': salida.fecha_entrega,
                'centro_destino_nombre': centro_destino_nombre,
                'destinatario': salida.destinatario,
                'producto_nombre': producto_nombre,
                'cantidad': salida.cantidad,
                'motivo': salida.motivo or '',
                'notas': salida.notas or '',
                'numero_lote': lote,
                'donacion_numero': donacion_numero,
                'usuario': usuario,
                'finalizado': es_finalizado,
                'fecha_finalizado': fecha_finalizado,
            }
            
            # Generar PDF (con firmas si no está finalizado, con sello si está finalizado)
            buffer = generar_recibo_salida_donacion(salida_data, finalizado=es_finalizado)
            
            response = HttpResponse(buffer, content_type='application/pdf')
            filename = f'recibo_salida_donacion_{salida.id}.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except SalidaDonacion.DoesNotExist:
            return Response(
                {'error': 'Salida de donación no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error al generar PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='generar-pdf-masivo')
    def generar_pdf_masivo(self, request):
        """
        Genera un recibo PDF para múltiples salidas de donación (salida masiva).
        Espera una lista de IDs de salidas y genera un único PDF consolidado.
        
        Body:
            {
                "salidas_ids": [1, 2, 3],
                "centro_destino": "Nombre del centro",
                "motivo": "Motivo de la salida"
            }
        
        Returns:
            PDF descargable con formato institucional
        """
        from django.http import HttpResponse
        from core.utils.pdf_reports import generar_recibo_salida_donacion
        from core.models import SalidaDonacion, Centro
        
        try:
            salidas_ids = request.data.get('salidas_ids', [])
            centro_destino = request.data.get('centro_destino', '')
            motivo = request.data.get('motivo', '')
            
            if not salidas_ids:
                return Response(
                    {'error': 'Se requiere al menos una salida'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Obtener las salidas
            salidas = SalidaDonacion.objects.filter(
                id__in=salidas_ids
            ).select_related(
                'detalle_donacion', 
                'detalle_donacion__producto',
                'detalle_donacion__donacion',
                'entregado_por'
            )
            
            if not salidas.exists():
                return Response(
                    {'error': 'No se encontraron las salidas especificadas'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Preparar datos para el PDF
            primera_salida = salidas.first()
            
            # Obtener nombre del centro si es un ID
            centro_nombre = centro_destino
            if centro_destino and str(centro_destino).isdigit():
                try:
                    centro = Centro.objects.get(pk=int(centro_destino))
                    centro_nombre = centro.nombre
                except Centro.DoesNotExist:
                    pass
            
            # Usuario que registró
            usuario = ''
            if primera_salida.entregado_por:
                usuario = f"{primera_salida.entregado_por.first_name} {primera_salida.entregado_por.last_name}".strip()
                if not usuario:
                    usuario = primera_salida.entregado_por.username
            
            salida_data = {
                'id': f"MAS-{primera_salida.id}",
                'fecha': primera_salida.fecha_entrega,
                'centro_destino_nombre': centro_nombre or primera_salida.destinatario,
                'destinatario': centro_nombre or primera_salida.destinatario,
                'motivo': motivo or primera_salida.motivo or '',
                'notas': primera_salida.notas or '',
                'usuario': usuario,
            }
            
            # Preparar detalles de productos
            detalles_data = []
            for salida in salidas:
                producto_nombre = ''
                lote = ''
                
                if salida.detalle_donacion:
                    if salida.detalle_donacion.producto:
                        producto_nombre = salida.detalle_donacion.producto.nombre
                    lote = salida.detalle_donacion.numero_lote or ''
                
                detalles_data.append({
                    'producto_nombre': producto_nombre,
                    'cantidad': salida.cantidad,
                    'numero_lote': lote,
                })
            
            # Generar PDF
            buffer = generar_recibo_salida_donacion(salida_data, detalles_data)
            
            response = HttpResponse(buffer, content_type='application/pdf')
            filename = f'recibo_salida_masiva_donacion_{primera_salida.id}.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return Response(
                {'error': f'Error al generar PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='finalizar')
    def finalizar(self, request, pk=None):
        """
        Marca una salida de donación como finalizada.
        Una vez finalizada, el PDF mostrará sello de ENTREGADO en lugar de campos de firma.
        
        Returns:
            Datos de la salida actualizada
        """
        from django.utils import timezone
        from core.models import SalidaDonacion
        
        try:
            salida = self.get_object()
            
            if salida.finalizado:
                return Response(
                    {'error': 'Esta salida ya fue finalizada'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            salida.finalizado = True
            salida.fecha_finalizado = timezone.now()
            salida.finalizado_por = request.user
            salida.save()
            
            # Retornar datos actualizados
            from core.serializers import SalidaDonacionSerializer
            serializer = SalidaDonacionSerializer(salida)
            
            return Response({
                'mensaje': 'Salida finalizada correctamente',
                'salida': serializer.data
            })
            
        except SalidaDonacion.DoesNotExist:
            return Response(
                {'error': 'Salida de donación no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error al finalizar: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='finalizar-masivo')
    def finalizar_masivo(self, request):
        """
        Marca múltiples salidas de donación como finalizadas.
        
        Body:
            {
                "salidas_ids": [1, 2, 3]
            }
        
        Returns:
            Resumen de salidas finalizadas
        """
        from django.utils import timezone
        from core.models import SalidaDonacion
        
        try:
            salidas_ids = request.data.get('salidas_ids', [])
            
            if not salidas_ids:
                return Response(
                    {'error': 'Se requiere al menos una salida'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Actualizar todas las salidas
            salidas = SalidaDonacion.objects.filter(
                id__in=salidas_ids,
                finalizado=False
            )
            
            count = salidas.update(
                finalizado=True,
                fecha_finalizado=timezone.now(),
                finalizado_por=request.user
            )
            
            return Response({
                'mensaje': f'{count} salidas finalizadas correctamente',
                'finalizadas': count
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error al finalizar: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# ISS-002 FIX: ENDPOINT DE CATÁLOGOS - Sincronizar enums frontend/backend
# =============================================================================

class CatalogosView(APIView):
    """
    Vista para obtener todos los catálogos del sistema.
    
    Expone las constantes definidas en backend para sincronizar con frontend.
    Esto evita discrepancias entre los valores válidos en front y backend.
    
    Endpoints:
    - GET /api/catalogos/ - Todos los catálogos
    - GET /api/catalogos/unidades-medida/ - Solo unidades de medida
    - GET /api/catalogos/categorias/ - Solo categorías
    - GET /api/catalogos/vias-administracion/ - Solo vías de administración
    - GET /api/catalogos/estados-requisicion/ - Solo estados de requisición
    - GET /api/catalogos/tipos-movimiento/ - Solo tipos de movimiento
    - GET /api/catalogos/roles/ - Solo roles de usuario
    """
    permission_classes = [AllowAny]  # Catálogos son públicos para formularios de login/registro
    
    def get(self, request, catalogo=None):
        from core.constants import (
            UNIDADES_MEDIDA,
            CATEGORIAS_PRODUCTO,
            ESTADOS_REQUISICION,
            TIPOS_MOVIMIENTO,
            ROLES_USUARIO,
        )
        
        # Vías de administración (no están en constants, definimos aquí)
        VIAS_ADMINISTRACION = [
            ('ORAL', 'Oral'),
            ('INTRAVENOSA', 'Intravenosa'),
            ('INTRAMUSCULAR', 'Intramuscular'),
            ('SUBCUTANEA', 'Subcutánea'),
            ('TOPICA', 'Tópica'),
            ('INHALATORIA', 'Inhalatoria'),
            ('RECTAL', 'Rectal'),
            ('OFTALMICA', 'Oftálmica'),
            ('OTICA', 'Ótica'),
            ('NASAL', 'Nasal'),
        ]
        
        # Construir respuesta según el catálogo solicitado
        catalogos = {
            'unidades_medida': [{'value': u[0], 'label': u[1]} for u in UNIDADES_MEDIDA],
            'categorias': [{'value': c[0], 'label': c[1]} for c in CATEGORIAS_PRODUCTO],
            'vias_administracion': [{'value': v[0], 'label': v[1]} for v in VIAS_ADMINISTRACION],
            'estados_requisicion': [{'value': e[0], 'label': e[1]} for e in ESTADOS_REQUISICION],
            'tipos_movimiento': [{'value': t[0], 'label': t[1]} for t in TIPOS_MOVIMIENTO],
            'roles': [{'value': r[0], 'label': r[1]} for r in ROLES_USUARIO],
        }
        
        # Si se solicita un catálogo específico
        if catalogo:
            catalogo_key = catalogo.replace('-', '_')
            if catalogo_key in catalogos:
                return Response({
                    catalogo_key: catalogos[catalogo_key]
                })
            return Response(
                {'error': f'Catálogo no encontrado: {catalogo}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Retornar todos los catálogos
        return Response(catalogos)


# =============================================================================
# ADMIN: LIMPIEZA DE DATOS PARA REINICIO COMPLETO
# =============================================================================

class AdminLimpiarDatosView(APIView):
    """
    Vista EXCLUSIVA para SUPERUSUARIOS para limpiar datos operativos del sistema.
    
    Permite dejar el sistema "en blanco" para que farmacia y centros puedan
    empezar a usar el sistema desde cero después de capacitación.
    
    SOPORTA ELIMINACIÓN SELECTIVA:
    - productos: Elimina productos, imágenes, lotes, documentos, movimientos
    - lotes: Elimina lotes, documentos, hojas recolección (no productos)
    - requisiciones: Elimina requisiciones, detalles, historial, ajustes
    - movimientos: Elimina solo movimientos
    - donaciones: Elimina donaciones, detalles y salidas de donaciones
    - todos: Elimina todo lo anterior INCLUYENDO donaciones
    
    NO ELIMINA (configuración del sistema):
    - Usuarios y sus perfiles
    - Centros
    - Configuración del sistema
    - Tema global (estilos)
    - Logs de auditoría (para mantener trazabilidad)
    - Notificaciones
    - Permisos de Django
    - Grupos de Django
    
    Endpoints:
    - GET /api/admin/limpiar-datos/ - Obtener estadísticas detalladas
    - POST /api/admin/limpiar-datos/ - Ejecutar limpieza (requiere confirmación y categoría)
    """
    permission_classes = [IsAuthenticated, IsSuperuserOnly]
    
    def get(self, request):
        """
        Retorna estadísticas detalladas de lo que se eliminaría por categoría.
        """
        from core.models import (
            Producto, Lote, Movimiento, Requisicion, DetalleRequisicion,
            HojaRecoleccion, DetalleHojaRecoleccion, LoteDocumento,
            ProductoImagen, ImportacionLog, DetalleDonacion, Donacion, SalidaDonacion,
            Notificacion
        )
        from django.db import connection
        
        # Solo superusuarios
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo SUPERUSUARIOS pueden acceder a esta función'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Conteos
        productos_count = Producto.objects.count()
        lotes_count = Lote.objects.count()
        movimientos_count = Movimiento.objects.count()
        requisiciones_count = Requisicion.objects.count()
        detalles_req_count = DetalleRequisicion.objects.count()
        hojas_recoleccion_count = HojaRecoleccion.objects.count()
        
        # Conteos de donaciones
        donaciones_count = Donacion.objects.count()
        detalles_donacion_count = DetalleDonacion.objects.count()
        salidas_donacion_count = SalidaDonacion.objects.count()
        
        # Conteo de notificaciones
        notificaciones_count = Notificacion.objects.count()
        
        # Conteos con raw SQL para tablas sin modelo
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM requisicion_ajustes_cantidad")
            ajustes_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM requisicion_historial_estados")
            historial_count = cursor.fetchone()[0]
        
        # Verificar si hay donaciones con productos
        productos_con_donaciones = DetalleDonacion.objects.values('producto_id').distinct().count()
        
        # Estadísticas organizadas por categoría
        stats = {
            'categorias': {
                'productos': {
                    'nombre': 'Productos e Inventario',
                    'descripcion': 'Elimina productos, sus imágenes, lotes asociados y documentos de lotes',
                    'total': productos_count + ProductoImagen.objects.count() + lotes_count + LoteDocumento.objects.count(),
                    'detalle': {
                        'productos': productos_count,
                        'producto_imagenes': ProductoImagen.objects.count(),
                        'lotes': lotes_count,
                        'lote_documentos': LoteDocumento.objects.count(),
                    },
                    'dependencias': ['También eliminará: movimientos, hojas recolección y sus detalles'],
                },
                'lotes': {
                    'nombre': 'Solo Lotes',
                    'descripcion': 'Elimina lotes, documentos de lotes y hojas de recolección (mantiene productos)',
                    'total': lotes_count + LoteDocumento.objects.count() + hojas_recoleccion_count + DetalleHojaRecoleccion.objects.count(),
                    'detalle': {
                        'lotes': lotes_count,
                        'lote_documentos': LoteDocumento.objects.count(),
                        'hojas_recoleccion': hojas_recoleccion_count,
                        'detalles_hojas_recoleccion': DetalleHojaRecoleccion.objects.count(),
                    },
                    'dependencias': ['También eliminará: movimientos vinculados a lotes'],
                },
                'requisiciones': {
                    'nombre': 'Requisiciones',
                    'descripcion': 'Elimina requisiciones, sus detalles, historial de estados y ajustes',
                    'total': requisiciones_count + detalles_req_count + historial_count + ajustes_count,
                    'detalle': {
                        'requisiciones': requisiciones_count,
                        'detalles_requisicion': detalles_req_count,
                        'requisicion_historial_estados': historial_count,
                        'requisicion_ajustes_cantidad': ajustes_count,
                    },
                    'dependencias': ['También eliminará: movimientos vinculados a requisiciones'],
                },
                'movimientos': {
                    'nombre': 'Movimientos',
                    'descripcion': 'Elimina solo el historial de movimientos de inventario',
                    'total': movimientos_count,
                    'detalle': {
                        'movimientos': movimientos_count,
                    },
                    'dependencias': [],
                },
                'donaciones': {
                    'nombre': 'Donaciones',
                    'descripcion': 'Elimina donaciones, sus detalles y registro de salidas',
                    'total': donaciones_count + detalles_donacion_count + salidas_donacion_count,
                    'detalle': {
                        'donaciones': donaciones_count,
                        'detalles_donacion': detalles_donacion_count,
                        'salidas_donacion': salidas_donacion_count,
                    },
                    'dependencias': [],
                },
                'notificaciones': {
                    'nombre': 'Notificaciones',
                    'descripcion': 'Elimina todas las notificaciones de usuarios',
                    'total': notificaciones_count,
                    'detalle': {
                        'notificaciones': notificaciones_count,
                    },
                    'dependencias': [],
                },
                'todos': {
                    'nombre': 'Todo el Inventario',
                    'descripcion': 'Limpieza completa: productos, lotes, requisiciones, movimientos, donaciones y notificaciones',
                    'total': productos_count + lotes_count + requisiciones_count + movimientos_count + donaciones_count + notificaciones_count,
                    'detalle': {
                        'productos': productos_count,
                        'lotes': lotes_count,
                        'requisiciones': requisiciones_count,
                        'movimientos': movimientos_count,
                        'donaciones': donaciones_count,
                        'notificaciones': notificaciones_count,
                    },
                    'dependencias': ['Incluye todos los datos asociados, dependencias, donaciones y notificaciones'],
                },
            },
            'resumen': {
                'productos': productos_count,
                'lotes': lotes_count,
                'movimientos': movimientos_count,
                'requisiciones': requisiciones_count,
                'donaciones': donaciones_count,
                'notificaciones': notificaciones_count,
            },
            'no_se_eliminara': [
                'Usuarios y perfiles',
                'Centros',
                'Configuración del sistema',
                'Tema global (estilos)',
                'Logs de auditoría',
                'Permisos y grupos',
            ],
            'advertencias': [],
        }
        
        # Advertir si hay donaciones vinculadas a productos
        if productos_con_donaciones > 0:
            stats['advertencias'].append(
                f'Hay {productos_con_donaciones} productos vinculados a donaciones. '
                'El sistema de donaciones seguirá funcionando pero los productos '
                'aparecerán como "producto eliminado" en el historial de donaciones.'
            )
        
        return Response(stats)
    
    def post(self, request):
        """
        Ejecuta la limpieza de datos operativos según la categoría seleccionada.
        Requiere: {"confirmar": true, "categoria": "productos|lotes|requisiciones|movimientos|todos"}
        """
        from core.models import (
            Producto, Lote, Movimiento, Requisicion, DetalleRequisicion,
            HojaRecoleccion, DetalleHojaRecoleccion, LoteDocumento,
            ProductoImagen, ImportacionLog, AuditoriaLog,
            Donacion, DetalleDonacion, SalidaDonacion, Notificacion
        )
        from django.db import connection
        
        # Solo superusuarios
        user = request.user
        if not user.is_superuser:
            return Response(
                {'error': 'Solo SUPERUSUARIOS pueden ejecutar esta función'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verificar confirmación
        confirmar = request.data.get('confirmar', False)
        if not confirmar:
            return Response(
                {'error': 'Debe enviar {"confirmar": true} para ejecutar la limpieza'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener categoría
        categoria = request.data.get('categoria', 'todos').lower()
        categorias_validas = ['productos', 'lotes', 'requisiciones', 'movimientos', 'donaciones', 'notificaciones', 'todos']
        
        if categoria not in categorias_validas:
            return Response(
                {'error': f'Categoría inválida. Use una de: {", ".join(categorias_validas)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                eliminados = {}
                
                # ============================================================
                # ELIMINACIÓN SELECTIVA RESPETANDO FOREIGN KEYS
                # ============================================================
                
                if categoria == 'movimientos':
                    # Solo movimientos
                    eliminados['movimientos'] = Movimiento.objects.all().delete()[0]
                
                elif categoria == 'donaciones':
                    # Eliminar donaciones en orden de dependencias FK
                    # 1. Salidas de donaciones (depende de detalle_donaciones)
                    eliminados['salidas_donacion'] = SalidaDonacion.objects.all().delete()[0]
                    # 2. Detalles de donaciones (depende de donaciones)
                    eliminados['detalles_donacion'] = DetalleDonacion.objects.all().delete()[0]
                    # 3. Donaciones
                    eliminados['donaciones'] = Donacion.objects.all().delete()[0]
                
                elif categoria == 'notificaciones':
                    # Solo notificaciones
                    eliminados['notificaciones'] = Notificacion.objects.all().delete()[0]
                
                elif categoria == 'requisiciones':
                    # 1. Ajustes de cantidad
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM requisicion_ajustes_cantidad")
                        eliminados['requisicion_ajustes_cantidad'] = cursor.rowcount
                    
                    # 2. Detalles de requisición
                    eliminados['detalles_requisicion'] = DetalleRequisicion.objects.all().delete()[0]
                    
                    # 3. Historial de estados
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM requisicion_historial_estados")
                        eliminados['requisicion_historial_estados'] = cursor.rowcount
                    
                    # 4. Movimientos vinculados a requisiciones
                    eliminados['movimientos'] = Movimiento.objects.filter(requisicion_id__isnull=False).delete()[0]
                    
                    # 5. Requisiciones
                    eliminados['requisiciones'] = Requisicion.objects.all().delete()[0]
                
                elif categoria == 'lotes':
                    # 1. Movimientos vinculados a lotes
                    eliminados['movimientos'] = Movimiento.objects.filter(lote_id__isnull=False).delete()[0]
                    
                    # 2. Detalles de hojas de recolección
                    eliminados['detalles_hojas_recoleccion'] = DetalleHojaRecoleccion.objects.all().delete()[0]
                    
                    # 3. Hojas de recolección
                    eliminados['hojas_recoleccion'] = HojaRecoleccion.objects.all().delete()[0]
                    
                    # 4. Documentos de lotes
                    eliminados['lote_documentos'] = LoteDocumento.objects.all().delete()[0]
                    
                    # 5. Actualizar detalles_requisicion para quitar referencia a lotes
                    DetalleRequisicion.objects.all().update(lote_id=None)
                    
                    # 6. Lotes
                    eliminados['lotes'] = Lote.objects.all().delete()[0]
                    
                    # 7. Actualizar stock de productos a 0
                    Producto.objects.all().update(stock_actual=0)
                
                elif categoria == 'productos':
                    # Elimina productos Y todo lo que depende de ellos
                    
                    # 1. Ajustes de cantidad
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM requisicion_ajustes_cantidad")
                        eliminados['requisicion_ajustes_cantidad'] = cursor.rowcount
                    
                    # 2. Detalles de requisición
                    eliminados['detalles_requisicion'] = DetalleRequisicion.objects.all().delete()[0]
                    
                    # 3. Historial de estados
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM requisicion_historial_estados")
                        eliminados['requisicion_historial_estados'] = cursor.rowcount
                    
                    # 4. Movimientos
                    eliminados['movimientos'] = Movimiento.objects.all().delete()[0]
                    
                    # 5. Requisiciones
                    eliminados['requisiciones'] = Requisicion.objects.all().delete()[0]
                    
                    # 6. Detalles de hojas de recolección
                    eliminados['detalles_hojas_recoleccion'] = DetalleHojaRecoleccion.objects.all().delete()[0]
                    
                    # 7. Hojas de recolección
                    eliminados['hojas_recoleccion'] = HojaRecoleccion.objects.all().delete()[0]
                    
                    # 8. Documentos de lotes
                    eliminados['lote_documentos'] = LoteDocumento.objects.all().delete()[0]
                    
                    # 9. Lotes
                    eliminados['lotes'] = Lote.objects.all().delete()[0]
                    
                    # 10. Imágenes de productos
                    eliminados['producto_imagenes'] = ProductoImagen.objects.all().delete()[0]
                    
                    # 11. Productos
                    eliminados['productos'] = Producto.objects.all().delete()[0]
                    
                    # 12. Logs de importación
                    eliminados['importacion_logs'] = ImportacionLog.objects.all().delete()[0]
                
                else:  # categoria == 'todos'
                    # LIMPIEZA COMPLETA
                    
                    # 1. Ajustes de cantidad
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM requisicion_ajustes_cantidad")
                        eliminados['requisicion_ajustes_cantidad'] = cursor.rowcount
                    
                    # 2. Detalles de requisición
                    eliminados['detalles_requisicion'] = DetalleRequisicion.objects.all().delete()[0]
                    
                    # 3. Historial de estados
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM requisicion_historial_estados")
                        eliminados['requisicion_historial_estados'] = cursor.rowcount
                    
                    # 4. Movimientos
                    eliminados['movimientos'] = Movimiento.objects.all().delete()[0]
                    
                    # 5. Requisiciones
                    eliminados['requisiciones'] = Requisicion.objects.all().delete()[0]
                    
                    # 6. Detalles de hojas de recolección
                    eliminados['detalles_hojas_recoleccion'] = DetalleHojaRecoleccion.objects.all().delete()[0]
                    
                    # 7. Hojas de recolección
                    eliminados['hojas_recoleccion'] = HojaRecoleccion.objects.all().delete()[0]
                    
                    # 8. Documentos de lotes
                    eliminados['lote_documentos'] = LoteDocumento.objects.all().delete()[0]
                    
                    # 9. Lotes
                    eliminados['lotes'] = Lote.objects.all().delete()[0]
                    
                    # 10. Imágenes de productos
                    eliminados['producto_imagenes'] = ProductoImagen.objects.all().delete()[0]
                    
                    # 11. Productos
                    eliminados['productos'] = Producto.objects.all().delete()[0]
                    
                    # 12. Logs de importación
                    eliminados['importacion_logs'] = ImportacionLog.objects.all().delete()[0]
                    
                    # 13-15. Donaciones (incluido en "todos")
                    eliminados['salidas_donacion'] = SalidaDonacion.objects.all().delete()[0]
                    eliminados['detalles_donacion'] = DetalleDonacion.objects.all().delete()[0]
                    eliminados['donaciones'] = Donacion.objects.all().delete()[0]
                    
                    # 16. Notificaciones (incluido en "todos")
                    eliminados['notificaciones'] = Notificacion.objects.all().delete()[0]
                
                # Calcular totales
                total_eliminados = sum(eliminados.values())
                
                # Nombres de categorías para el log
                nombres_categorias = {
                    'productos': 'PRODUCTOS E INVENTARIO',
                    'lotes': 'SOLO LOTES',
                    'requisiciones': 'REQUISICIONES',
                    'movimientos': 'MOVIMIENTOS',
                    'donaciones': 'DONACIONES',
                    'notificaciones': 'NOTIFICACIONES',
                    'todos': 'TODO EL INVENTARIO (INCLUYE DONACIONES Y NOTIFICACIONES)',
                }
                
                # Registrar en auditoría (NO se elimina)
                AuditoriaLog.objects.create(
                    usuario=user,
                    accion='LIMPIEZA_DATOS',
                    modelo='SISTEMA',
                    objeto_id=None,
                    datos_anteriores=None,
                    datos_nuevos=eliminados,
                    detalles={
                        'tipo': f'LIMPIEZA_SELECTIVA_{categoria.upper()}',
                        'categoria': categoria,
                        'categoria_nombre': nombres_categorias.get(categoria, categoria),
                        'ejecutado_por': user.username,
                        'email': user.email,
                        'fecha': timezone.now().isoformat(),
                        'registros_eliminados': total_eliminados,
                    },
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request.META.get('HTTP_USER_AGENT') else None,
                )
                
                logger.warning(
                    f"🗑️ LIMPIEZA DE DATOS [{categoria.upper()}] ejecutada por {user.username} ({user.email}): "
                    f"{total_eliminados} registros eliminados. Detalle: {eliminados}"
                )
                
                return Response({
                    'success': True,
                    'mensaje': f'✅ Limpieza de {nombres_categorias.get(categoria, categoria)} completada exitosamente.',
                    'categoria': categoria,
                    'eliminados': eliminados,
                    'total_registros_eliminados': total_eliminados,
                    'no_eliminado': [
                        'Usuarios y perfiles',
                        'Centros', 
                        'Configuración del sistema',
                        'Tema global',
                        'Auditoría',
                    ],
                    'ejecutado_por': user.username,
                    'fecha': timezone.now().isoformat(),
                })
                
        except Exception as e:
            logger.error(f"❌ Error en limpieza de datos [{categoria}]: {e}", exc_info=True)
            return Response(
                {'error': f'Error al limpiar datos: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

