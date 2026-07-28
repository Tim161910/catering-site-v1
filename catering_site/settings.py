import os
import sys
import logging

logging.basicConfig(level=logging.DEBUG)

print("SETTINGS LOADING...")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Security
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-this')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*', 'catering-app-rnam.onrender.com', 'localhost', '127.0.0.1']

# Apps
INSTALLED_APPS = [
    'staff',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'widget_tweaks'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'catering_site.urls'  # <-- THIS WAS MISSING
WSGI_APPLICATION = 'catering_site.wsgi.application'

# Database
if 'collectstatic' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }
else:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3'),
            conn_max_age=600,
            ssl_require=os.environ.get('DATABASE_URL') is not None
        )
    }

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = []  # <-- EMPTY. Don't add app folders here
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
            os.path.join(BASE_DIR, 'staff', 'templates'),
        ],
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

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

FERNET_KEY = 'gDVz3ECufpfkYF7t6za6GgNMnBC9BQx4uUn47DU2L6g='

# Timezone Settings - Lagos
TIME_ZONE = 'Africa/Lagos'
USE_TZ = True
USE_I18N = True

# Auth redirects
LOGIN_URL = 'admin:login'
LOGIN_REDIRECT_URL = '/admin/'
LOGOUT_REDIRECT_URL = '/admin/'

# Email Settings
DEFAULT_FROM_EMAIL = 'Bamboo Staff <noreply@bamboo.com>'

# For LOCAL TESTING - prints emails to console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# For PRODUCTION - use SMTP. Example with Gmail:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')  # your gmail
# EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')  # app password