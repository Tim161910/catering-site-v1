from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from django.views.generic import TemplateView
from staff.admin import staff_admin_site # <-- THIS IS YOUR DEMO ADMIN
from django.conf import settings
from django.conf.urls.static import static

def health_check(request):
    print("HEALTH VIEW HIT")
    return HttpResponse("ok")

urlpatterns = [
    path('health/', health_check),
    path('admin/', admin.site.urls), # your full admin - keep this for you
    path('staff_admin/', staff_admin_site.urls), # <-- ADD THIS for demo admin
    path('staff/', include('staff.urls', namespace='staff')),
    path('logout/', LogoutView.as_view(next_page='admin:login'), name='logout'),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)