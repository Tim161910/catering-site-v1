from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect  # ADD THIS
from staff.admin import staff_admin_site
from django.conf import settings
from django.conf.urls.static import static

def health_check(request):
    print("HEALTH VIEW HIT")
    return HttpResponse("ok")

urlpatterns = [
    path('health/', health_check),
    path('admin/', admin.site.urls),
    path('staff_admin/', staff_admin_site.urls),
    path('staff/', include('staff.urls', namespace='staff')),
    path('logout/', LogoutView.as_view(next_page='staff:staff_login'), name='logout'), # FIXED
    path('', lambda request: redirect('staff:staff_login'), name='home'), # FIXED
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)