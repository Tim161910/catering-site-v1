import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)

print("SETTINGS LOADING...")

BASE_DIR = Path(__file__).resolve().parent.parent  # Keep only Path

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

ROOT_URLCONF = 'catering_site.urls'
WSGI_APPLICATION = 'catering_site.wsgi.application'

# Database
if 'collectstatic' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',  # <-- Changed to Path
        }
    }
else:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL', f'sqlite:///{BASE_DIR / "db.sqlite3"}'), # <-- Changed
            conn_max_age=600,
            ssl_require=os.environ.get('DATABASE_URL') is not None
        )
    }

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # <-- Changed to Path
STATICFILES_DIRS = []  
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',        # <-- Changed to Path
            BASE_DIR / 'staff' / 'templates', # <-- Changed to Path
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'staff.context_processors.notifications',  # <-- Already added. Good
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
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'