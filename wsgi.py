import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'staff_project.settings')
application = get_wsgi_application()

# Auto create superuser on startup
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'Admin1234!')
    print("Superuser created: admin / Admin1234!")
else:
    print("Superuser already exists")