from django.contrib import admin
from django.urls import path
from staff.admin import staff_admin_site  # import your custom admin

urlpatterns = [
    path('admin/', admin.site.urls),                    # default admin - empty
    path('staff_admin/', staff_admin_site.urls),        # your custom admin - has all models
]