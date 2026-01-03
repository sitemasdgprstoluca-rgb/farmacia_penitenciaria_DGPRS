# -*- coding: utf-8 -*-
"""
Módulo de Requisiciones para inventario.

RequisicionViewSet: El ViewSet más complejo del sistema con el flujo V2 de estados.

Funcionalidades principales:
- Creación y edición de borradores de requisiciones
- Flujo de autorización jerárquico V2:
  * Médico → Admin Centro → Director Centro → Farmacia
- Surtido con descuento atómico de lotes (FEFO)
- Confirmación de recepción con firma digital
- Gestión de devoluciones y rechazos
- Generación automática de hojas de recolección
- Exportación a Excel/PDF
- Historial de estados para auditoría

Estados del flujo V2:
- borrador: Requisición en creación
- pendiente_admin: Esperando aprobación del administrador del centro
- pendiente_director: Esperando aprobación del director del centro
- enviada: Enviada a farmacia central
- en_revision: En revisión por farmacia
- autorizada: Autorizada para surtido
- en_surtido: En proceso de surtido
- surtida: Surtido completado
- entregada: Entregada al centro solicitante
- rechazada/devuelta/vencida/cancelada: Estados terminales

Nota: Por ahora se re-exporta desde views_legacy.py para mantener compatibilidad.
"""

from inventario.views_legacy import RequisicionViewSet

__all__ = ['RequisicionViewSet']
