"""
Configuración del proyecto Ovillito — Tienda de crochet hecha a mano.

Los valores sensibles o dependientes del entorno se leen de variables de
entorno, con valores por defecto pensados para desarrollo local.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(nombre, defecto=False):
    valor = os.environ.get(nombre)
    if valor is None:
        return defecto
    return valor.strip().lower() in {"1", "true", "si", "sí", "yes", "on"}


# --- Seguridad -------------------------------------------------------------
# En producción define DJANGO_SECRET_KEY y DJANGO_DEBUG=0.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-solo-local-ovillito-cambia-esta-clave-en-produccion-7c1f2e9a",
)
DEBUG = _env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost"
).split(",") if h.strip()]


# Correos que reciben el rol de administrador al registrarse o iniciar sesión.
# En producción: variable ADMIN_EMAILS="uno@correo.com,otro@correo.com"
ADMIN_EMAILS = [e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()]

# Render expone el dominio público en esta variable.
_render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if _render_host:
    ALLOWED_HOSTS.append(_render_host)
    CSRF_TRUSTED_ORIGINS = [f"https://{_render_host}"]


# --- Aplicaciones ----------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Apps del proyecto
    "cuentas",
    "tienda",
    "actividades",
    "panel",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
                "tienda.context_processors.global_tienda",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# --- Base de datos ---------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Idioma y zona horaria -------------------------------------------------
LANGUAGE_CODE = "es"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True


# --- Archivos estáticos y subidos ------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Límite de tamaño para fotos subidas desde la cámara (bytes).
FOTO_TAMANO_MAXIMO = 6 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Autenticación ---------------------------------------------------------
LOGIN_URL = "cuentas:login"
LOGIN_REDIRECT_URL = "inicio"
LOGOUT_REDIRECT_URL = "tienda:home"

MESSAGE_TAGS = {
    10: "info",      # DEBUG
    20: "info",      # INFO
    25: "exito",     # SUCCESS
    30: "aviso",     # WARNING
    40: "error",     # ERROR
}


# --- Identidad de la marca y datos de la tienda física ----------------------
# La ubicación se usa en el mapa para calcular qué tan cerca está el cliente.
# Cambia latitud/longitud por la dirección real de tu tienda.
MARCA = {
    "nombre": "Ovillito",
    "slogan": "Cada puntada, un abrazo.",
    "descripcion": "Tienda de crochet y amigurumis tejidos a mano.",
}

TIENDA = {
    "nombre": "Ovillito · Taller & Tienda",
    "direccion": os.environ.get("TIENDA_DIRECCION", "Calle 93 #13-45, Bogotá (dirección de ejemplo)"),
    "latitud": float(os.environ.get("TIENDA_LATITUD", "4.6766")),
    "longitud": float(os.environ.get("TIENDA_LONGITUD", "-74.0482")),
    "telefono": "+57 300 000 0000",
    "horario": "Lunes a sábado · 9:00 a 19:00",
    "moneda": "COP",
    "envio_gratis_desde": 150000,
    "costo_envio": 12000,
}
