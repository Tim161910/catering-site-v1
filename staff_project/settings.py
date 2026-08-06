from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

ROOT_URLCONF = 'staff_project.urls'

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-m+1abf)q6%si-7%vl0=sgof&jt^-!@$mt_*vir3s_l%_6*_n)p')

DEBUG = True  # 1. TEMP: Turn on to see the error

ALLOWED_HOSTS = ['*', '.onrender.com', 'localhost', '127.0.0.1']

# 2. FIX: Only require SSL if we have a real DATABASE_URL
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=True
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

INSTALLED_APPS = [
    'staff',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'staff.apps.StaffConfig',
    'widget_tweaks',
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

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates', BASE_DIR / 'staff' / 'templates'], # 3. ADD staff templates dir
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

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

FERNET_KEY = '2ATJ44SLjUK2w0HLf6lcLHLWui0YSkMH3KpALLaWb0U='

# Auth redirects
LOGIN_URL = 'staff:staff_login'
LOGIN_REDIRECT_URL = 'staff:my_dashboard' 
LOGOUT_REDIRECT_URL = 'staff:staff_login'