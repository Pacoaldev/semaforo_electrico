"""
Configuración de Django para el proyecto Semáforo Eléctrico.

Modernizada para:
- Leer toda la configuración sensible desde variables de entorno (.env).
- Funcionar tanto en SQLite (desarrollo rápido) como en PostgreSQL (producción).
- Servir archivos estáticos en producción con WhiteNoise.
- Aplicar ajustes de seguridad cuando DEBUG=False.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env (si existe).
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    """Convierte variables de entorno textuales ('True', '1', 'yes') a bool."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    """Convierte una cadena separada por comas en una lista, quitando vacíos."""
    raw = os.getenv(name, default) or ""
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- Seguridad básica -------------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "Falta la variable de entorno DJANGO_SECRET_KEY. "
        "Crea un archivo .env a partir de .env.example y define la clave."
    )

# DEBUG se controla por entorno. En producción SIEMPRE debe ser False.
DEBUG = env_bool("DJANGO_DEBUG", default=False)

# Hosts permitidos (lista separada por comas en DJANGO_ALLOWED_HOSTS).
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# Orígenes de confianza para CSRF (necesario en producción con HTTPS).
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")


# --- Aplicaciones -----------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "users",
    "electricity_prices",
    "rest_framework",
    "rest_framework.authtoken",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise justo después de SecurityMiddleware para servir estáticos.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "semaforo_electrico_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "semaforo_electrico_project.wsgi.application"


# --- Base de datos ----------------------------------------------------------
# Si USE_SQLITE=True usamos SQLite (rápido, sin instalar nada).
# En caso contrario usamos DATABASE_URL (PostgreSQL en producción).
USE_SQLITE = env_bool("USE_SQLITE", default=False)

if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": dj_database_url.config(
            default="postgres://semaforo_user:semaforo_pass@localhost:5432/semaforo_db",
            conn_max_age=600,
            conn_health_checks=True,
        )
    }


# --- Autenticación ----------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Internacionalización ---------------------------------------------------
LANGUAGE_CODE = "es-es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True


# --- Archivos estáticos -----------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise: comprime y cachea los estáticos con nombres únicos (hash).
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- API REST ---------------------------------------------------------------
REST_FRAMEWORK = {
    # Autenticación por sesión (web) o token (apps móviles/PWA).
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    # Por defecto la API es pública (lectura de precios).
    # Cámbialo a IsAuthenticated si quieres exigir login también en la API.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    # Límite de peticiones para evitar abuso/scraping que consuma la cuota
    # del plan gratuito de hosting. Anónimos y usuarios autenticados aparte.
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "120/min",
    },
}


# --- Autenticación web (redirecciones) --------------------------------------
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"
LOGIN_URL = "login"


# --- Refresco de precios protegido (cron externo gratuito) ------------------
# Token que protege el endpoint /tasks/refresh-prices/.
# El cron externo (GitHub Actions, cron-job.org, etc.) lo envía por cabecera
# "X-Cron-Token" o como parámetro "?token=". Si está vacío, el endpoint queda
# deshabilitado (fail-closed).
CRON_SECRET_TOKEN = os.getenv("CRON_SECRET_TOKEN", "")


# --- Caché (usada para el "auto-refresco" de precios) -----------------------
# LocMem por defecto: suficiente para el lock diario del auto-refresco.
# En Render con varios workers cada proceso tendría su propio LocMem, pero el
# lock solo evita ráfagas dentro del mismo worker; el update_or_create de
# fetch_prices es idempotente, así que no hay riesgo de datos duplicados.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "semaforo-electrico-cache",
    }
}


# --- Auto-refresco de precios -----------------------------------------------
# Si al abrir la app no hay datos de precios para el día de hoy, se lanza
# fetch_prices automáticamente (con un lock para no repetirlo más de una vez por
# hora). Esto evita depender exclusivamente del cron externo (GitHub Actions),
# que no es fiable.
AUTO_REFRESH_PRICES = env_bool("AUTO_REFRESH_PRICES", default=True)


# --- Email ------------------------------------------------------------------
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "semaforo-electrico@localhost")


# --- Ajustes de seguridad para producción -----------------------------------
if not DEBUG:
    # Redirige HTTP -> HTTPS. Déjalo en True en un entorno con HTTPS (Render, etc.).
    # Pon DJANGO_SECURE_SSL_REDIRECT=False si sirves por HTTP (p. ej. pruebas locales).
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
