from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include
from staff.admin import staff_admin_site
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

def health_check(request):
    print("HEALTH VIEW HIT")
    return HttpResponse("ok")

urlpatterns = [
    path('health/', health_check),
    path('admin/', staff_admin_site.urls),
    path('staff/', include('staff.urls')), 
    path('', RedirectView.as_view(url='staff/'), name='home'),  
    path('accounts/', include('django.contrib.auth.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)