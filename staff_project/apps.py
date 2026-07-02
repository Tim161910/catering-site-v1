from django.apps import AppConfig

class StaffProjectConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'staff_project'

    def ready(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'Admin1234!')
            print("Superuser created: admin / Admin1234!")