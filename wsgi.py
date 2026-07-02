"""
WSGI config for staff_project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'staff_project.settings')

application = get_wsgi_application()

"""
WSGI config for staff_project project.
"""
# Auto-create superuser on first deploy - remove after first login!
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'Admin1234!')
    print("Superuser created: admin / Admin1234!")
