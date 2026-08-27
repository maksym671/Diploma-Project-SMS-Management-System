"""
Django settings for sms_project project.
Student Management System — Diploma Project by Maksym Shpak
"""

from pathlib import Path
import os

try:
    import dj_database_url
except ImportError:  # optional locally when Postgres driver is absent
    dj_database_url = None

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Load KEY=VALUE pairs from a local .env file if present."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(BASE_DIR / '.env')


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    value = env(key)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def hosts_for_custom_domain(domain):
    """Apex + www so a Namecheap .me works whether the user typed either."""
    domain = (domain or '').strip().lower()
    domain = domain.removeprefix('https://').removeprefix('http://').strip().strip('/')
    if not domain:
        return []
    if domain.startswith('www.'):
        apex = domain[4:]
        return [apex, domain]
    return [domain, f'www.{domain}']


def https_origins_from_hosts(hosts):
    origins = []
    for host in hosts:
        host = (host or '').strip()
        if (
            not host
            or host in {'localhost', '127.0.0.1', '*'}
            or host.startswith('.')
        ):
            continue
        origins.append(f'https://{host}')
    return origins


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

SECRET_KEY = env(
    'SECRET_KEY',
    'django-insecure-dev-only-change-me-before-production',
)

DEBUG = env_bool('DEBUG', True)

ALLOWED_HOSTS = [
    host.strip()
    for host in env('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if host.strip()
]

# Render / reverse-proxy hosts
RENDER_EXTERNAL_HOSTNAME = env('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

for host in hosts_for_custom_domain(env('CUSTOM_DOMAIN', '')):
    if host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sms_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sms_project.wsgi.application'


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

database_url = env('DATABASE_URL')
if database_url:
    if dj_database_url is None:
        raise ImportError(
            'DATABASE_URL is set but dj-database-url is not installed. '
            'Run: pip install dj-database-url psycopg2-binary'
        )
    # TLS is mandatory for the managed Postgres we deploy against, but passing
    # sslmode to any other backend (e.g. a SQLite URL used to rehearse the
    # production build locally) raises a connection error.
    is_postgres = database_url.startswith(('postgres://', 'postgresql://'))
    # Neon’s pooler (and PgBouncer in transaction mode) cannot keep a
    # Django connection open. Direct Neon hosts can, and that avoids a
    # fresh TLS handshake on every tab switch.
    uses_pooler = '-pooler' in database_url
    DATABASES['default'] = dj_database_url.parse(
        database_url,
        conn_max_age=600 if is_postgres and not uses_pooler else 0,
        ssl_require=is_postgres and not DEBUG,
    )
    if is_postgres:
        DATABASES['default']['CONN_HEALTH_CHECKS'] = True


# ---------------------------------------------------------------------------
# Auth / passwords
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'core.User'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = 'en-us'

LANGUAGES = [
    ('en', 'English'),
    ('pl', 'Polski'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

TIME_ZONE = 'Europe/Warsaw'
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
_static_backend = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
    if not DEBUG
    else 'whitenoise.storage.CompressedStaticFilesStorage'
)
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': _static_backend,
    },
}

# Hashed filenames already get an immutable cache; this covers any leftover
# unhashed file WhiteNoise still serves (favicons, error pages).
if not DEBUG:
    WHITENOISE_MAX_AGE = 31536000


# ---------------------------------------------------------------------------
# CSRF (needed behind Render's HTTPS proxy and on a custom domain)
# ---------------------------------------------------------------------------
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in env('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]


# ---------------------------------------------------------------------------
# Production security
# ---------------------------------------------------------------------------

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(env('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'
    for origin in https_origins_from_hosts(ALLOWED_HOSTS):
        if origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)

    if SECRET_KEY.startswith('django-insecure'):
        raise ValueError(
            'SECRET_KEY must be set via environment variable in production '
            '(DEBUG=False).'
        )


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

from django.contrib.messages import constants as message_constants

MESSAGE_TAGS = {
    message_constants.DEBUG: 'secondary',
    message_constants.INFO: 'info',
    message_constants.SUCCESS: 'success',
    message_constants.WARNING: 'warning',
    message_constants.ERROR: 'danger',
}
