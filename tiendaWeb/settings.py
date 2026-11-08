"""
Configuración del proyecto tiendaWeb (tienda Pretexto).

Sigue la práctica de "12-factor app": todo lo que cambia entre computadoras vive en
variables de entorno (ver .env.example), nunca en el código.

- En desarrollo usa SQLite y no hace falta configurar nada.
- En producción basta con definir DATABASE_URL (PostgreSQL), DJANGO_SECRET_KEY y
  DJANGO_DEBUG=0; se activan solas las protecciones de HTTPS y cookies.
"""
import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Identidad de la tienda. Es el único lugar donde se escribe el nombre: las plantillas,
# los correos y el admin lo toman de aquí. La página 500 es la excepción, porque Django
# la muestra sin datos para que funcione incluso si todo lo demás falló.
NOMBRE_TIENDA = "Pretexto"
LEMA_TIENDA = "Siempre hay un pretexto."


def _bandera(nombre, por_defecto="0"):
    """Lee una variable de entorno de sí o no ("1" significa sí)."""
    return os.environ.get(nombre, por_defecto) == "1"


CLAVE_DE_DESARROLLO = "solo-para-desarrollo-cambiar-en-produccion"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", CLAVE_DE_DESARROLLO)
DEBUG = _bandera("DJANGO_DEBUG", "1")
if not DEBUG and SECRET_KEY == CLAVE_DE_DESARROLLO:
    raise ImproperlyConfigured("Define DJANGO_SECRET_KEY antes de publicar la tienda.")

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o
]

# Dirección pública del sitio; se usa en los correos, donde no hay petición del navegador.
SITIO_URL = os.environ.get("SITIO_URL", "http://127.0.0.1:8000")

# Render informa su dominio en esta variable.
HOST_RENDER = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if HOST_RENDER:
    ALLOWED_HOSTS.append(HOST_RENDER)
    CSRF_TRUSTED_ORIGINS.append(f"https://{HOST_RENDER}")
    SITIO_URL = f"https://{HOST_RENDER}"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    # Apps del proyecto
    "catalogo",   # productos, simulador y cotización
    "carrito",    # selección del cliente antes de pagar
    "pedidos",    # compra, pago, seguimiento y solicitudes
    "cuentas",    # registro e inicio de sesión
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "tiendaWeb.middleware.EncabezadosSeguridadMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tiendaWeb.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "catalogo.context_processors.categorias_menu",
                "carrito.context_processors.carrito",
                "pedidos.context_processors.tienda",
            ],
        },
    },
]

WSGI_APPLICATION = "tiendaWeb.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Cuentas
LOGIN_URL = "cuentas:entrar"
LOGIN_REDIRECT_URL = "pedidos:lista"
LOGOUT_REDIRECT_URL = "catalogo:inicio"

# Idioma y zona horaria de México
LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True

# Archivos estáticos (CSS, JS del simulador) y subidos (fotos y capas)
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# WhiteNoise sirve y comprime los estáticos en producción. No se usan nombres con
# huella porque el simulador arma varias rutas en el navegador; para eso está
# VERSION_ESTATICOS.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG
        else "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Versión de los archivos CSS/JS. Se agrega a sus URL (?v=...) para que el
# navegador descargue la versión nueva en lugar de usar la que tiene guardada.
# Cámbienla cada vez que modifiquen un CSS o JS.
VERSION_ESTATICOS = "2026.11.12"

# Reglas de negocio configurables
DIAS_ENVIO = int(os.environ.get("DIAS_ENVIO", "3"))

# Pagos: Stripe en modo de pruebas. Sin llaves, y solo en desarrollo, se usa un pago
# simulado que pasa por la misma confirmación que un pago real.
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
PAGO_SIMULADO = DEBUG and not STRIPE_SECRET_KEY

# Correo: en desarrollo se imprime en la terminal.
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", f"{NOMBRE_TIENDA} <no-responder@pretexto.example>")

# Seguridad en producción (se revisa con: python manage.py check --deploy)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^salud/$"]  # la revisión interna del servidor usa HTTP
    SECURE_HSTS_SECONDS = 31536000  # un año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Registro de eventos en la salida estándar, como esperan las plataformas en la nube.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "{levelname} {name}: {message}", "style": "{"}},
    "handlers": {"consola": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["consola"], "level": "INFO"},
    "loggers": {"django": {"handlers": ["consola"], "level": "INFO", "propagate": False}},
}
