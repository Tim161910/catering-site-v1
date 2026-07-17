from django.contrib import admin
from django.urls import path, include
from staff.admin import staff_admin_site  # import your custom admin

urlpatterns = [
    path('admin/', staff_admin_site.urls),        # <-- now your custom admin lives at /admin
    path('staff/', include('staff.urls')),
]