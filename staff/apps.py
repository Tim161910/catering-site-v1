from django.apps import AppConfig
import os

class StaffConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'staff'

    def ready(self):
        import staff.signals  # keep this for reliability auto-update
        
        if os.environ.get('RENDER'):
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            username = 'Bamboo'
            password = 'newpassword123'
            email = 'admin@test.com'

            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': email, 'is_staff': True, 'is_superuser': True}
            )
            
            if created:
                # Only set password if we just created the user
                user.set_password(password)
                user.save()
                print(f"Superuser {username} created with password")
            else:
                # User already exists. Do nothing so we don't overwrite their password
                print(f"Superuser {username} already exists. Skipping password reset.")