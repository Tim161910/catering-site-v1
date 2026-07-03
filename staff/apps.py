from django.apps import AppConfig
import os

class StaffConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'staff'

    def ready(self):
        if os.environ.get('RENDER'):
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if not User.objects.filter(username='bamboo3').exists():
                User.objects.create_superuser('bamboo3', 'admin@test.com', 'TempPass123')
                print("Superuser bamboo3 created on startup")