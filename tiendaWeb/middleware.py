"""
Encabezados de seguridad que el navegador aplica a cada respuesta.

La política de contenido (CSP) indica de dónde se puede cargar cada recurso. Si
alguien lograra inyectar un <script>, el navegador se negaría a ejecutarlo.
"""

POLITICA_CONTENIDO = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",  # los colores de los moños son estilos en línea
    "img-src 'self' data:",              # data: para la vista previa del moño
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
    "form-action 'self' https://checkout.stripe.com",
])
POLITICA_PERMISOS = "camera=(), microphone=(), geolocation=(), payment=(self)"


class EncabezadosSeguridadMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        respuesta.headers.setdefault("Content-Security-Policy", POLITICA_CONTENIDO)
        respuesta.headers.setdefault("Permissions-Policy", POLITICA_PERMISOS)
        return respuesta
