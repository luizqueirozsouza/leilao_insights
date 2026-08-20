import os
import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR.parent, '.env'))

SECRET_KEY = env('SECRET_KEY', default='django-insecure-19@6#xzcv3p@gr_5*xauf^5#e@bj7^ew+n2zjt#yg$m4+b-*(8')

DEBUG = env.bool('DEBUG', default=True)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'backend_django.auctions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'backend_django.core.middleware.CorsMiddleware',
]

ROOT_URLCONF = 'backend_django.core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend_django.core.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('database').replace('"', ''),
        'USER': env('user').replace('"', ''),
        'PASSWORD': env('password').replace('"', ''),
        'HOST': env('host'),
        'PORT': env('port'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'leilao-insights-cache',
    }
}

CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=[
        'http://localhost:5173',
        'http://localhost:3000',
        'http://localhost:8080',
        'http://127.0.0.1:5500',
    ],
)

# --- Sessao/CSRF ---
# O login da SPA cross-origin (Cloudflare Pages -> API) exige SameSite=None.
# Para nao quebrar o Django Admin (same-origin, via proxy), usamos SameSite=None
# apenas quando CSRF_TRUSTED_ORIGINS (a origem do frontend) estiver configurada;
# caso contrario caimos para Lax, que funciona no admin e no mesmo dominio.
_has_spa_origin = bool(env.list('CSRF_TRUSTED_ORIGINS', default=[]))
_default_samesite = 'None' if _has_spa_origin else 'Lax'
_default_secure = not DEBUG

SESSION_COOKIE_SAMESITE = env('SESSION_COOKIE_SAMESITE', default=_default_samesite)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=_default_secure)
CSRF_COOKIE_SAMESITE = env('CSRF_COOKIE_SAMESITE', default=_default_samesite)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=_default_secure)
CSRF_COOKIE_HTTPONLY = False
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='Leilão Insights <no-reply@leilao-insights.com>')

APPEND_SLASH = True
