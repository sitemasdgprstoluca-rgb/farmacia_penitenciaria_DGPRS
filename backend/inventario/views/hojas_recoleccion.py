# =============================================================================
# HojaRecoleccionViewSet Module
# =============================================================================
# Este módulo contiene el ViewSet para la gestión de Hojas de Recolección.
# Las hojas de recolección se generan automáticamente al autorizar requisiciones
# y proporcionan un documento de referencia para el personal de farmacia.
#
# Extraído del archivo monolítico views.py para mejorar la organización del código.
# =============================================================================

import logging
from django.http import HttpResponse

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import HojaRecoleccion
from core.serializers import HojaRecoleccionSerializer
from .base import CustomPagination

logger = logging.getLogger(__name__)


class HojaRecoleccionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para Hojas de Recoleccion.
    Las hojas se generan automaticamente al autorizar requisiciones.
    """
    queryset = HojaRecoleccion.objects.select_related(
        'requisicion', 'requisicion__centro', 'generado_por'
    ).prefetch_related('detalles')
    serializer_class = HojaRecoleccionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        """Filtra por centro si el usuario no es admin/farmacia."""
        queryset = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return HojaRecoleccion.objects.none()
        if user.is_superuser:
            return queryset
        rol = getattr(user, 'rol', '').lower()
        if rol in ('admin', 'farmacia', 'administrador', 'usuario_farmacia'):
            return queryset
        # Filtrar por centro del usuario
        user_centro = getattr(user, 'centro', None)
        if user_centro:
            return queryset.filter(requisicion__centro_destino=user_centro)
        return HojaRecoleccion.objects.none()

    @action(detail=True, methods=['get'])
    def verificar_integridad(self, request, pk=None):
        """Verifica que el hash de la hoja coincida con su contenido."""
        import hashlib
        import json
        hoja = self.get_object()
        contenido = json.dumps(hoja.contenido_json, sort_keys=True, ensure_ascii=False)
        hash_calculado = hashlib.sha256(contenido.encode('utf-8')).hexdigest()
        return Response({
            'folio': hoja.numero,
            'hash_almacenado': hoja.hash_contenido,
            'hash_calculado': hash_calculado,
            'integridad_ok': hash_calculado == hoja.hash_contenido
        })

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Genera y descarga el PDF de la hoja de recolección."""
        from core.utils.pdf_generator import generar_hoja_recoleccion
        
        hoja = self.get_object()
        requisicion = hoja.requisicion
        
        try:
            pdf_buffer = generar_hoja_recoleccion(requisicion)
            
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            folio_safe = (hoja.numero or f'HOJA-{hoja.id}').replace('/', '-')
            response['Content-Disposition'] = f'attachment; filename="Hoja_Recoleccion_{folio_safe}.pdf"'
            
            return response
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al generar PDF',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
