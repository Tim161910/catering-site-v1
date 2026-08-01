from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from django.views.generic import TemplateView 
from staff.admin import staff_admin_site # <-- ADD THIS

urlpatterns = [
    path('admin/', admin.site.urls), # your full admin - keep this for you
    path('staff_admin/', staff_admin_site.urls), # <-- ADD THIS for demo admin
    path('staff/', include('staff.urls', namespace='staff')),
    path('logout/', LogoutView.as_view(next_page='admin:login'), name='logout'),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
]