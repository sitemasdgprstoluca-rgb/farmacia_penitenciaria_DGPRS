"""
Signals para el sistema de Farmacia Penitenciaria.
Incluye auditoría automática, snapshots, notificaciones de estado
e invalidación de caché del dashboard.
"""
import logging
import os
import sys
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from .models import Movimiento, Lote, Requisicion, Producto, AuditoriaLogs, Notificacion, Donacion
from .middleware import get_current_request, get_current_user

logger = logging.getLogger(__name__)

# Flag para detectar si estamos en modo de tests
# Con pytest no existe el argumento literal "test", por lo que
# validamos variables de entorno y cualquier argumento que contenga "pytest".
_TESTING = (
    os.environ.get('PYTEST_CURRENT_TEST') is not None
    or any(arg == 'test' for arg in sys.argv)
    or any('pytest' in arg for arg in sys.argv)
)


def registrar_auditoria(modelo, objeto, accion, cambios=None):
    """Función auxiliar para registrar auditoría.
    
    En modo de tests, se omite la auditoría para evitar problemas
    de FK constraints cuando TransactionTestCase hace rollback.
    """
    if _TESTING:
        # En tests, solo loguear sin crear registros de auditoría
        # para evitar FK constraint issues con usuarios eliminados
        logger.debug(f"[TEST MODE] Auditoría omitida: {accion} - {modelo} #{getattr(objeto, 'pk', '?')}")
        return
    
    request = get_current_request()
    usuario = get_current_user()

    if not usuario or not usuario.is_authenticated:
        usuario = None

    ip_address = None
    user_agent = ''

    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')

        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

    try:
        AuditoriaLogs.objects.create(
            usuario=usuario,
            accion=accion,
            modelo=modelo,
            objeto_id=str(objeto.pk),
            datos_nuevos=cambios or {},
            detalles={'objeto_repr': str(objeto)[:255]},
            ip_address=ip_address,
            user_agent=user_agent
        )
        logger.info(f"Auditoría registrada: {usuario} - {accion} - {modelo} #{objeto.pk}")
    except Exception as exc:  # pragma: no cover
        logger.error(f"Error al registrar auditoría: {exc}")


def _verificar_stock_bajo_producto(producto):
    """
    Verifica si un producto tiene stock bajo y notifica a farmacia.
    Solo crea notificación si no existe una reciente (últimas 4 horas).
    """
    if _TESTING:
        return  # No crear notificaciones en tests
    
    from django.db.models import Sum
    from django.utils import timezone
    from datetime import timedelta, date
    from .models import Lote, User
    
    if not producto.stock_minimo or producto.stock_minimo <= 0:
        return  # No tiene stock mínimo configurado
    
    # Calcular stock total de lotes activos no vencidos
    hoy = date.today()
    stock_total = Lote.objects.filter(
        producto=producto,
        activo=True,
        fecha_caducidad__gte=hoy
    ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
    
    # Si el stock está por debajo del mínimo
    if stock_total < producto.stock_minimo:
        # Verificar si ya existe notificación reciente para evitar spam
        existe_reciente = Notificacion.objects.filter(
            tipo='warning',
            titulo__icontains='Stock Bajo',
            datos__tipo_alerta='stock_bajo_producto',
            datos__producto_id=producto.id,
            created_at__gte=timezone.now() - timedelta(hours=4)
        ).exists()
        
        if existe_reciente:
            logger.debug(f"Notificación de stock bajo para {producto.clave} ya existe (últimas 4h)")
            return
        
        # Obtener usuarios de farmacia
        # Roles de farmacia según ROLES_USUARIO en constants.py
        usuarios_farmacia = User.objects.filter(
            rol__in=['farmacia', 'admin', 'admin_sistema', 'admin_farmacia', 'superusuario'],
            is_active=True
        )
        
        for usuario in usuarios_farmacia:
            try:
                Notificacion.objects.create(
                    usuario=usuario,
                    tipo='warning',
                    titulo=f'⚠️ Stock Bajo: {producto.clave}',
                    mensaje=f'El producto {producto.clave} - {producto.nombre} tiene stock bajo.\n\n'
                            f'Stock actual: {stock_total}\n'
                            f'Stock mínimo: {producto.stock_minimo}',
                    datos={
                        'tipo_alerta': 'stock_bajo_producto',
                        'producto_id': producto.id,
                        'producto_clave': producto.clave,
                        'stock_actual': stock_total,
                        'stock_minimo': producto.stock_minimo
                    },
                    url=f'/productos/{producto.id}'
                )
                logger.info(f"Notificación de stock bajo creada para {producto.clave} -> {usuario.username}")
            except Exception as e:
                logger.error(f"Error creando notificación de stock bajo: {e}")


@receiver(post_save, sender=Movimiento)
def auditar_movimiento(sender, instance, created, **kwargs):
    """Audita creación de movimientos de inventario y verifica alertas de stock."""
    if created:
        lote = instance.lote
        producto = instance.producto
        
        # Log informativo
        if lote:
            logger.info(
                f"Signal disparado - Movimiento {instance.tipo} en Lote {lote.numero_lote}: "
                f"Cantidad: {instance.cantidad}, Stock actual: {lote.cantidad_actual}"
            )
        else:
            logger.info(
                f"Signal disparado - Movimiento {instance.tipo} de Producto {producto.nombre}: "
                f"Cantidad: {instance.cantidad}"
            )
        
        # Determinar centro (puede ser origen o destino)
        centro = instance.centro_destino or instance.centro_origen
        
        # Auditoría formal
        registrar_auditoria(
            modelo='Movimiento',
            objeto=instance,
            accion=f'movimiento_{instance.tipo}',
            cambios={
                'tipo': instance.tipo,
                'lote': lote.numero_lote if lote else None,
                'producto': producto.descripcion,
                'producto_clave': producto.clave,
                'cantidad': instance.cantidad,
                'stock_resultante': lote.cantidad_actual if lote else None,
                'centro': centro.nombre if centro else None,
                'usuario': instance.usuario.username if instance.usuario else 'Sistema',
                'motivo': instance.motivo or '',
                'referencia': instance.referencia or ''
            }
        )
        
        # Verificar alertas de stock bajo después de movimientos de salida
        if instance.tipo.lower() == 'salida' and producto:
            _verificar_stock_bajo_producto(producto)


@receiver(pre_save, sender=Lote)
def validar_caducidad_lote(sender, instance, **kwargs):
    """Marca automáticamente lotes vencidos como inactivos antes de guardar."""
    from datetime import date

    if instance.fecha_caducidad < date.today() and instance.activo:
        instance.activo = False
        logger.warning(
            f"Lote {instance.numero_lote} marcado automáticamente como INACTIVO (vencido) "
            f"(caducidad: {instance.fecha_caducidad})"
        )


@receiver(pre_save, sender=Requisicion)
def snapshot_requisicion(sender, instance, **kwargs):
    """Guarda estado previo de la requisición para evaluar cambios."""
    if instance.pk:
        try:
            previo = sender.objects.get(pk=instance.pk)
            instance._estado_anterior = previo.estado
        except sender.DoesNotExist:
            instance._estado_anterior = None
    else:
        instance._estado_anterior = None


@receiver(post_save, sender=Requisicion)
def auditar_cambios_requisicion(sender, instance, created, **kwargs):
    """Audita creación y cambios en requisiciones y genera notificaciones."""
    if created:
        registrar_auditoria(
            modelo='Requisicion',
            objeto=instance,
            accion='crear',
            cambios={
                'numero': instance.numero,
                'centro_destino': instance.centro_destino.nombre if instance.centro_destino else None,
                'centro_origen': instance.centro_origen.nombre if instance.centro_origen else None,
                'estado': instance.estado,
                'total_productos': instance.detalles.count()
            }
        )
        return

    estado_anterior = getattr(instance, '_estado_anterior', None)
    if not estado_anterior or estado_anterior == instance.estado:
        return

    cambios = {
        'estado_anterior': estado_anterior,
        'estado_nuevo': instance.estado,
    }

    if instance.estado in ['autorizada', 'rechazada'] and instance.autorizador:
        cambios['autorizador'] = instance.autorizador.username

    if instance.estado == 'rechazada' and instance.notas:
        cambios['motivo_rechazo'] = instance.notas

    registrar_auditoria(
        modelo='Requisicion',
        objeto=instance,
        accion=f'cambiar_estado_{instance.estado}',
        cambios=cambios
    )

    # =========================================================================
    # SISTEMA DE NOTIFICACIONES BIDIRECCIONAL - FLUJO V2
    # =========================================================================
    
    # FLUJO V2: Notificaciones según estado
    
    # Caso 1: Médico envía a Admin del Centro
    if instance.estado == 'pendiente_admin':
        _notificar_admin_centro(instance)
        return
    
    # Caso 2: Admin envía a Director del Centro
    if instance.estado == 'pendiente_director':
        _notificar_director_centro(instance)
        return
    
    # Caso 3: Director envía a Farmacia (en_revision)
    if instance.estado == 'en_revision':
        _notificar_farmacia_nueva_requisicion(instance)
        return
    
    # Caso 4: Centro ENVÍA requisición directamente a Farmacia (legacy)
    if instance.estado == 'enviada':
        _notificar_farmacia_nueva_requisicion(instance)
        return
    
    # Caso 5: Farmacia PROCESA requisición → Notificar al solicitante (Centro)
    mensajes_para_solicitante = {
        'autorizada': ('success', 'Requisición AUTORIZADA', 
                       f'Su requisición {instance.numero} ha sido autorizada por Farmacia.'),
        'parcial': ('info', 'Requisición PARCIALMENTE AUTORIZADA', 
                    f'Su requisición {instance.numero} ha sido parcialmente autorizada.'),
        'rechazada': ('warning', 'Requisición RECHAZADA', 
                      f'Su requisición {instance.numero} ha sido rechazada. Motivo: {instance.notas or "No especificado"}'),
        'surtida': ('success', 'Requisición SURTIDA', 
                    f'Su requisición {instance.numero} ha sido surtida y está lista para recoger.'),
        # ISS-DB-002: Usar 'entregada' en lugar de 'recibida'
        'entregada': ('success', 'Requisición ENTREGADA', 
                     f'La requisición {instance.numero} ha sido entregada al centro.'),
        'cancelada': ('warning', 'Requisición CANCELADA', 
                      f'Su requisición {instance.numero} ha sido cancelada.'),
        # FLUJO V2: Notificar devoluciones
        'devuelta': ('warning', 'Requisición DEVUELTA', 
                     f'Su requisición {instance.numero} ha sido devuelta para correcciones.'),
    }

    if instance.estado in mensajes_para_solicitante:
        tipo, titulo, mensaje = mensajes_para_solicitante[instance.estado]
        _notificar_solicitante(instance, tipo, titulo, mensaje)


def _notificar_admin_centro(requisicion):
    """
    FLUJO V2: Notifica al Administrador del Centro cuando un médico envía una requisición.
    Incluye protección contra notificaciones duplicadas.
    """
    from .models import User, Notificacion
    
    centro = requisicion.centro_destino or requisicion.centro_origen
    if not centro:
        logger.warning(f"No se puede notificar admin: requisición {requisicion.numero} sin centro")
        return
    
    # Buscar usuarios con rol de administrador en el mismo centro
    # Roles válidos: administrador_centro (FLUJO V2) o admin (legacy)
    admins_centro = User.objects.filter(
        centro=centro,
        rol__in=['administrador_centro', 'admin_centro', 'admin'],
        is_active=True
    )
    
    if not admins_centro.exists():
        logger.warning(f"No hay administradores en el centro {centro.nombre} para notificar")
        return
    
    solicitante_nombre = requisicion.solicitante.get_full_name() or requisicion.solicitante.username if requisicion.solicitante else 'Usuario'
    
    notificaciones_creadas = 0
    for admin in admins_centro:
        # ISS-FIX: Verificar si ya existe una notificación similar
        notificacion_existente = Notificacion.objects.filter(
            usuario=admin,
            titulo='Nueva Requisición para Autorizar',
            datos__requisicion_id=requisicion.pk
        ).exists()
        
        if notificacion_existente:
            logger.debug(f"Notificación ya existe para admin {admin.username} - requisición {requisicion.numero}")
            continue
        
        try:
            Notificacion.objects.create(
                usuario=admin,
                tipo='info',
                titulo='Nueva Requisición para Autorizar',
                mensaje=f'{solicitante_nombre} ha enviado la requisición {requisicion.numero} para su autorización.',
                datos={
                    'requisicion_id': requisicion.pk,
                    'numero': requisicion.numero,
                    'solicitante': requisicion.solicitante.username if requisicion.solicitante else None,
                    'estado': 'pendiente_admin'
                },
                url=f'/requisiciones/{requisicion.pk}'
            )
            notificaciones_creadas += 1
            logger.debug(f"Notificación enviada a admin {admin.username}: Requisición {requisicion.numero}")
        except Exception as exc:
            logger.error(f"Error creando notificación para admin {admin.username}: {exc}")
    
    logger.info(f"Notificaciones creadas: {notificaciones_creadas} de {admins_centro.count()} admin(s) del centro {centro.nombre}")


def _notificar_director_centro(requisicion):
    """
    FLUJO V2: Notifica al Director del Centro cuando el admin autoriza una requisición.
    Incluye protección contra notificaciones duplicadas.
    """
    from .models import User, Notificacion
    
    centro = requisicion.centro_destino or requisicion.centro_origen
    if not centro:
        logger.warning(f"No se puede notificar director: requisición {requisicion.numero} sin centro")
        return
    
    # Buscar usuarios con rol de director en el mismo centro
    # Roles válidos: director_centro (FLUJO V2) o director (legacy)
    directores_centro = User.objects.filter(
        centro=centro,
        rol__in=['director_centro', 'director'],
        is_active=True
    )
    
    if not directores_centro.exists():
        logger.warning(f"No hay directores en el centro {centro.nombre} para notificar")
        return
    
    notificaciones_creadas = 0
    for director in directores_centro:
        # ISS-FIX: Verificar si ya existe una notificación similar
        notificacion_existente = Notificacion.objects.filter(
            usuario=director,
            titulo='Requisición Pendiente de Autorización',
            datos__requisicion_id=requisicion.pk
        ).exists()
        
        if notificacion_existente:
            logger.debug(f"Notificación ya existe para director {director.username} - requisición {requisicion.numero}")
            continue
        
        try:
            Notificacion.objects.create(
                usuario=director,
                tipo='info',
                titulo='Requisición Pendiente de Autorización',
                mensaje=f'La requisición {requisicion.numero} requiere su autorización como Director.',
                datos={
                    'requisicion_id': requisicion.pk,
                    'numero': requisicion.numero,
                    'solicitante': requisicion.solicitante.username if requisicion.solicitante else None,
                    'estado': 'pendiente_director'
                },
                url=f'/requisiciones/{requisicion.pk}'
            )
            notificaciones_creadas += 1
            logger.debug(f"Notificación enviada a director {director.username}: Requisición {requisicion.numero}")
        except Exception as exc:
            logger.error(f"Error creando notificación para director {director.username}: {exc}")
    
    logger.info(f"Notificaciones creadas: {notificaciones_creadas} de {directores_centro.count()} director(es) del centro {centro.nombre}")


def _notificar_farmacia_nueva_requisicion(requisicion):
    """
    Notifica a todos los usuarios de Farmacia cuando un Centro envía una requisición.
    Incluye protección contra notificaciones duplicadas.
    """
    from .models import User, Notificacion
    
    # Obtener usuarios de farmacia y admin que deben recibir notificaciones
    # Roles de farmacia según ROLES_USUARIO en constants.py
    usuarios_farmacia = User.objects.filter(
        rol__in=['farmacia', 'admin', 'admin_sistema', 'admin_farmacia', 'superusuario'],
        is_active=True
    )
    
    centro_nombre = requisicion.centro_origen.nombre if requisicion.centro_origen else 'Centro desconocido'
    
    notificaciones_creadas = 0
    for usuario in usuarios_farmacia:
        # ISS-FIX: Verificar si ya existe una notificación similar para este usuario y requisición
        # (evitar duplicados cuando el estado cambia múltiples veces)
        notificacion_existente = Notificacion.objects.filter(
            usuario=usuario,
            titulo='Nueva Requisición Recibida',
            datos__requisicion_id=requisicion.pk
        ).exists()
        
        if notificacion_existente:
            logger.debug(f"Notificación ya existe para {usuario.username} - requisición {requisicion.numero}")
            continue
        
        try:
            Notificacion.objects.create(
                usuario=usuario,
                tipo='info',
                titulo='Nueva Requisición Recibida',
                mensaje=f'El {centro_nombre} ha enviado la requisición {requisicion.numero}. Requiere su atención.',
                datos={
                    'requisicion_id': requisicion.pk,
                    'numero': requisicion.numero,
                    'centro_origen_id': requisicion.centro_origen_id,
                    'centro_origen': centro_nombre,
                    'solicitante': requisicion.solicitante.username if requisicion.solicitante else None,
                    'prioridad': requisicion.prioridad
                },
                url=f'/requisiciones/{requisicion.pk}'
            )
            notificaciones_creadas += 1
            logger.debug(f"Notificación enviada a {usuario.username}: Nueva requisición {requisicion.numero}")
        except Exception as exc:
            logger.error(f"Error creando notificación para {usuario.username}: {exc}")
    
    logger.info(f"Notificaciones creadas: {notificaciones_creadas} de {usuarios_farmacia.count()} usuarios de Farmacia para requisición {requisicion.numero}")


def _notificar_solicitante(requisicion, tipo, titulo, mensaje):
    """
    Notifica al solicitante (usuario del Centro) sobre el estado de su requisición.
    """
    if not requisicion.solicitante:
        logger.warning(f"No se puede notificar: requisición {requisicion.numero} sin solicitante")
        return
    
    try:
        Notificacion.objects.create(
            usuario=requisicion.solicitante,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            datos={
                'requisicion_id': requisicion.pk,
                'numero': requisicion.numero,
                'estado': requisicion.estado,
                'autorizador': requisicion.autorizador.username if requisicion.autorizador else None
            },
            url=f'/requisiciones/{requisicion.pk}'
        )
        logger.info(f"Notificación enviada a {requisicion.solicitante.username}: {titulo}")
    except Exception as exc:
        logger.error(f"Error creando notificación para solicitante: {exc}")


@receiver(pre_save, sender=Producto)
def snapshot_producto(sender, instance, **kwargs):
    """Conserva el estado previo del producto para detectar cambios reales."""
    if not instance.pk:
        instance._previous_state = None
        return

    try:
        instance._previous_state = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._previous_state = None


@receiver(post_save, sender=Producto)
def auditar_cambios_producto(sender, instance, created, **kwargs):
    """Audita creación y cambios relevantes en productos."""
    if created:
        registrar_auditoria(
            modelo='Producto',
            objeto=instance,
            accion='crear',
            cambios={
                'clave': instance.clave,
                'descripcion': instance.descripcion,
                'unidad_medida': instance.unidad_medida,
                'stock_minimo': instance.stock_minimo,
                'activo': instance.activo,
                'es_controlado': instance.es_controlado,
            }
        )
        return

    anterior = getattr(instance, '_previous_state', None)
    if not anterior:
        return

    cambios = {}
    if anterior.descripcion != instance.descripcion:
        cambios['descripcion'] = (anterior.descripcion, instance.descripcion)
    if anterior.unidad_medida != instance.unidad_medida:
        cambios['unidad_medida'] = (anterior.unidad_medida, instance.unidad_medida)
    # ISS-FIX: precio_unitario NO existe en Producto (está en Lote)
    # if anterior.precio_unitario != instance.precio_unitario:
    #     cambios['precio_unitario'] = (str(anterior.precio_unitario), str(instance.precio_unitario))
    if anterior.stock_minimo != instance.stock_minimo:
        cambios['stock_minimo'] = (anterior.stock_minimo, instance.stock_minimo)
    if anterior.activo != instance.activo:
        cambios['activo'] = (anterior.activo, instance.activo)
    if anterior.es_controlado != instance.es_controlado:
        cambios['es_controlado'] = (anterior.es_controlado, instance.es_controlado)

    if cambios:
        registrar_auditoria(
            modelo='Producto',
            objeto=instance,
            accion='actualizar',
            cambios=cambios
        )


@receiver(pre_save, sender=Lote)
def snapshot_lote(sender, instance, **kwargs):
    """
    ISS-AUDIT: Conserva estado previo del lote para detectar cambios reales.
    Permite registrar datos_anteriores vs datos_nuevos en auditoría.
    """
    if not instance.pk:
        instance._previous_state = None
        return
    try:
        instance._previous_state = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._previous_state = None


@receiver(post_save, sender=Lote)
def auditar_lote(sender, instance, created, **kwargs):
    """
    ISS-AUDIT: Audita creación y actualización de lotes con diff completo.
    
    En creación: registra todos los campos iniciales.
    En actualización: registra solo los campos que cambiaron (antes/después).
    """
    if created:
        registrar_auditoria(
            modelo='Lote',
            objeto=instance,
            accion='crear',
            cambios={
                'numero_lote': instance.numero_lote,
                'producto': instance.producto.nombre if instance.producto else None,
                'producto_id': instance.producto_id,
                'cantidad_inicial': instance.cantidad_inicial,
                'cantidad_actual': instance.cantidad_actual,
                'cantidad_contrato': instance.cantidad_contrato,
                'precio_unitario': str(instance.precio_unitario) if instance.precio_unitario else '0',
                'numero_contrato': instance.numero_contrato,
                'activo': instance.activo,
                'fecha_caducidad': instance.fecha_caducidad.isoformat() if instance.fecha_caducidad else None,
                'centro': instance.centro.nombre if instance.centro else 'Farmacia Central',
            }
        )
        return
    
    # Actualización: registrar diff real
    anterior = getattr(instance, '_previous_state', None)
    if not anterior:
        return
    
    # Campos a comparar para auditoría
    campos_auditar = [
        'cantidad_contrato', 'precio_unitario', 'marca', 'ubicacion',
        'activo', 'numero_contrato', 'fecha_fabricacion',
    ]
    
    cambios_anteriores = {}
    cambios_nuevos = {}
    
    for campo in campos_auditar:
        val_anterior = getattr(anterior, campo, None)
        val_nuevo = getattr(instance, campo, None)
        if val_anterior != val_nuevo:
            cambios_anteriores[campo] = str(val_anterior) if val_anterior is not None else None
            cambios_nuevos[campo] = str(val_nuevo) if val_nuevo is not None else None
    
    # También detectar cambios en cantidad_actual (por movimientos)
    if anterior.cantidad_actual != instance.cantidad_actual:
        cambios_anteriores['cantidad_actual'] = anterior.cantidad_actual
        cambios_nuevos['cantidad_actual'] = instance.cantidad_actual
    
    if cambios_anteriores:
        registrar_auditoria(
            modelo='Lote',
            objeto=instance,
            accion='actualizar',
            cambios={
                'numero_lote': instance.numero_lote,
                'datos_anteriores': cambios_anteriores,
                'datos_nuevos': cambios_nuevos,
            }
        )


@receiver(post_delete, sender=Producto)
def auditar_eliminacion_producto(sender, instance, **kwargs):
    """Auditoría específica para eliminaciones de productos."""
    registrar_auditoria(
        modelo='Producto',
        objeto=instance,
        accion='eliminar',
        cambios={
            'clave': instance.clave,
            'descripcion': instance.descripcion,
            'razon': 'Producto eliminado'
        }
    )


# ============================================================================
# SEÑALES PARA CREAR USERPROFILE Y AUDITAR USUARIOS
# ============================================================================
from .models import User, UserProfile, Centro

@receiver(post_save, sender=User)
def auditar_y_crear_perfil_usuario(sender, instance, created, **kwargs):
    """
    Crea automáticamente un UserProfile cuando se crea un nuevo usuario.
    También audita creación y cambios relevantes en usuarios.
    """
    if created:
        # Crear perfil
        try:
            UserProfile.objects.get_or_create(usuario=instance)
            logger.debug(f"UserProfile creado para usuario: {instance.username}")
        except Exception as e:
            logger.error(f"Error al crear UserProfile para {instance.username}: {e}")
        
        # Auditar creación de usuario
        registrar_auditoria(
            modelo='Usuario',
            objeto=instance,
            accion='crear',
            cambios={
                'username': instance.username,
                'rol': instance.rol,
                'centro': instance.centro.nombre if instance.centro else None,
                'is_active': instance.is_active,
                'is_superuser': instance.is_superuser
            }
        )


@receiver(pre_save, sender=User)
def snapshot_usuario(sender, instance, **kwargs):
    """Conserva estado previo del usuario para detectar cambios."""
    if not instance.pk:
        instance._previous_state = None
        return
    try:
        instance._previous_state = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._previous_state = None


@receiver(post_save, sender=User)
def auditar_cambios_usuario(sender, instance, created, **kwargs):
    """Audita cambios relevantes en usuarios (no creación, esa va en auditar_y_crear_perfil_usuario)."""
    if created:
        return  # La creación se maneja en auditar_y_crear_perfil_usuario
    
    anterior = getattr(instance, '_previous_state', None)
    if not anterior:
        return
    
    cambios = {}
    if anterior.rol != instance.rol:
        cambios['rol'] = (anterior.rol, instance.rol)
    if anterior.is_active != instance.is_active:
        cambios['is_active'] = (anterior.is_active, instance.is_active)
    if getattr(anterior, 'centro_id', None) != getattr(instance, 'centro_id', None):
        centro_ant = anterior.centro.nombre if anterior.centro else None
        centro_new = instance.centro.nombre if instance.centro else None
        cambios['centro'] = (centro_ant, centro_new)
    if anterior.is_superuser != instance.is_superuser:
        cambios['is_superuser'] = (anterior.is_superuser, instance.is_superuser)
    
    if cambios:
        registrar_auditoria(
            modelo='Usuario',
            objeto=instance,
            accion='actualizar',
            cambios=cambios
        )


# ============================================================================
# SEÑALES PARA AUDITAR CENTROS
# ============================================================================
@receiver(pre_save, sender=Centro)
def snapshot_centro(sender, instance, **kwargs):
    """Conserva estado previo del centro para detectar cambios."""
    if not instance.pk:
        instance._previous_state = None
        return
    try:
        instance._previous_state = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._previous_state = None


@receiver(post_save, sender=Centro)
def auditar_centro(sender, instance, created, **kwargs):
    """Audita creación y actualización de centros."""
    if created:
        registrar_auditoria(
            modelo='Centro',
            objeto=instance,
            accion='crear',
            cambios={
                'id': instance.id,
                'nombre': instance.nombre,
                'activo': instance.activo
            }
        )
    else:
        anterior = getattr(instance, '_previous_state', None)
        if not anterior:
            return
        
        cambios = {}
        if anterior.nombre != instance.nombre:
            cambios['nombre'] = (anterior.nombre, instance.nombre)
        if anterior.activo != instance.activo:
            cambios['activo'] = (anterior.activo, instance.activo)
        if anterior.direccion != instance.direccion:
            cambios['direccion'] = (anterior.direccion[:50] if anterior.direccion else None, 
                                     instance.direccion[:50] if instance.direccion else None)
        
        if cambios:
            registrar_auditoria(
                modelo='Centro',
                objeto=instance,
                accion='actualizar',
                cambios=cambios
            )


@receiver(post_delete, sender=Centro)
def auditar_eliminacion_centro(sender, instance, **kwargs):
    """Audita eliminación de centros."""
    registrar_auditoria(
        modelo='Centro',
        objeto=instance,
        accion='eliminar',
        cambios={'id': instance.id, 'nombre': instance.nombre}
    )


# =============================================================================
# INVALIDACIÓN DE CACHÉ DEL DASHBOARD
# =============================================================================
# Se invalida automáticamente al crear/actualizar/eliminar modelos clave.
# Esto asegura que el Dashboard siempre muestre datos frescos sin importar
# desde qué endpoint se modifiquen los datos (views, services, admin, shell).
# =============================================================================

def _invalidar_cache_dashboard_signal(centro_id=None):
    """
    Invalida el caché del dashboard de forma segura desde signals.
    Maneja errores silenciosamente ya que el caché no es crítico.
    """
    try:
        from django.core.cache import cache
        # Siempre invalidar el global
        cache.delete('dashboard_resumen_global')
        cache.delete('dashboard_graficas_global')
        # Si hay un centro específico, invalidar también ese
        if centro_id:
            cache.delete(f'dashboard_resumen_{centro_id}')
            cache.delete(f'dashboard_graficas_{centro_id}')
    except Exception as e:
        logger.debug(f'Error al invalidar caché del dashboard desde signal: {e}')


def _extraer_centro_id(instance, model_name):
    """Extrae el centro_id relevante de una instancia de modelo."""
    try:
        if model_name == 'Movimiento':
            # Un movimiento puede afectar al centro del lote, al origen y al destino
            centros = set()
            if hasattr(instance, 'lote') and instance.lote and hasattr(instance.lote, 'centro') and instance.lote.centro:
                centros.add(instance.lote.centro_id)
            if hasattr(instance, 'centro_origen') and instance.centro_origen:
                centros.add(instance.centro_origen_id)
            if hasattr(instance, 'centro_destino') and instance.centro_destino:
                centros.add(instance.centro_destino_id)
            return centros  # Puede ser un set de varios centros
        elif model_name == 'Lote':
            if hasattr(instance, 'centro') and instance.centro:
                return {instance.centro_id}
        elif model_name == 'Requisicion':
            centros = set()
            if hasattr(instance, 'centro_destino') and instance.centro_destino:
                centros.add(instance.centro_destino_id)
            if hasattr(instance, 'centro_origen') and instance.centro_origen:
                centros.add(instance.centro_origen_id)
            return centros
    except Exception:
        pass
    return set()


@receiver(post_save, sender=Movimiento)
def invalidar_cache_movimiento(sender, instance, **kwargs):
    """Invalida caché del dashboard cuando se crea/modifica un movimiento."""
    centros = _extraer_centro_id(instance, 'Movimiento')
    if centros:
        for cid in centros:
            _invalidar_cache_dashboard_signal(cid)
    else:
        _invalidar_cache_dashboard_signal()


@receiver(post_delete, sender=Movimiento)
def invalidar_cache_movimiento_delete(sender, instance, **kwargs):
    """Invalida caché del dashboard cuando se elimina un movimiento."""
    centros = _extraer_centro_id(instance, 'Movimiento')
    if centros:
        for cid in centros:
            _invalidar_cache_dashboard_signal(cid)
    else:
        _invalidar_cache_dashboard_signal()


@receiver(post_save, sender=Lote)
def invalidar_cache_lote_save(sender, instance, **kwargs):
    """Invalida caché del dashboard cuando se crea/modifica un lote."""
    centros = _extraer_centro_id(instance, 'Lote')
    if centros:
        for cid in centros:
            _invalidar_cache_dashboard_signal(cid)
    else:
        _invalidar_cache_dashboard_signal()


@receiver(post_delete, sender=Lote)
def invalidar_cache_lote_delete(sender, instance, **kwargs):
    """Invalida caché del dashboard cuando se elimina un lote."""
    centros = _extraer_centro_id(instance, 'Lote')
    if centros:
        for cid in centros:
            _invalidar_cache_dashboard_signal(cid)
    else:
        _invalidar_cache_dashboard_signal()


@receiver(post_save, sender=Producto)
def invalidar_cache_producto_save(sender, instance, **kwargs):
    """Invalida caché del dashboard cuando se crea/modifica un producto."""
    _invalidar_cache_dashboard_signal()


@receiver(post_delete, sender=Producto)
def invalidar_cache_producto_delete(sender, instance, **kwargs):
    """Invalida caché del dashboard cuando se elimina un producto."""
    _invalidar_cache_dashboard_signal()


@receiver(post_save, sender=Requisicion)
def invalidar_cache_requisicion_save(sender, instance, **kwargs):
    """Invalida caché del dashboard cuando se crea/modifica una requisición."""
    centros = _extraer_centro_id(instance, 'Requisicion')
    if centros:
        for cid in centros:
            _invalidar_cache_dashboard_signal(cid)
    else:
        _invalidar_cache_dashboard_signal()


@receiver(post_delete, sender=Requisicion)
def invalidar_cache_requisicion_delete(sender, instance, **kwargs):
    """Invalida caché del dashboard cuando se elimina una requisición."""
    centros = _extraer_centro_id(instance, 'Requisicion')
    if centros:
        for cid in centros:
            _invalidar_cache_dashboard_signal(cid)
    else:
        _invalidar_cache_dashboard_signal()


@receiver(post_save, sender=Donacion)
def invalidar_cache_donacion_save(sender, instance, **kwargs):
    """Invalida caché del dashboard cuando se crea/modifica una donación."""
    _invalidar_cache_dashboard_signal()


@receiver(post_delete, sender=Donacion)
def invalidar_cache_donacion_delete(sender, instance, **kwargs):
    """Invalida caché del dashboard cuando se elimina una donación."""
    _invalidar_cache_dashboard_signal()
