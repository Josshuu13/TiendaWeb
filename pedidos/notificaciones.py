"""Correos automáticos al cliente. Si un correo falla, el pedido sigue adelante."""
import logging
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def avisar_cambio(pedido):
    contexto = {
        "pedido": pedido,
        "url": settings.SITIO_URL + pedido.get_absolute_url(),
        "nombre_tienda": settings.NOMBRE_TIENDA,
    }
    try:
        send_mail(
            f"Tu pedido {pedido.folio}: {pedido.get_estado_display()}",
            render_to_string("pedidos/correo_estado.txt", contexto),
            None,
            [pedido.usuario.email],
        )
    except (SMTPException, OSError):
        logger.exception("No se pudo enviar el correo del pedido %s", pedido.folio)
