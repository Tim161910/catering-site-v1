print("SETTINGS LOADING...")

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# dj_database_url may not be installed in some environments (editors, CI),
# so attempt to import it and provide a minimal fallback if unavailable.
try:
    # Some linters/IDEs may flag this import as unresolved; ignore for static checks
    import dj_database_url  # type: ignore
except Exception:
    # Fallback stub if dj_database_url is not installed (prevents import errors in editors)
    class dj_database_url:
        @staticmethod
        def config(default='sqlite:///db.sqlite3', conn_max_age=None, ssl_require=False):
            # Return a minimal Django DATABASES config for sqlite
            db_path = default.replace('sqlite:///', '') if default.startswith('sqlite:///') else 'db.sqlite3'
            return {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': os.path.join(BASE_DIR, db_path),
                'CONN_MAX_AGE': conn_max_age,
            }

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

load_dotenv()

FERNET_KEY = os.getenv('FERNET_KEY', 'AAAAAAAAAAAAAAAAAAAAAAAAAAA=')


import sys

if 'collectstatic' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }
else:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3'),
            conn_max_age=600,
            ssl_require=os.environ.get('DATABASE_URL') is not None
        )
    }

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'