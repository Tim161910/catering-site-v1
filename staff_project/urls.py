from django.contrib import admin
from django.urls import path, include
from staff.admin import staff_admin_site
from . import views

# --- INLINED EVENTS ADMIN SITE ---
from django.contrib.admin import AdminSite
from staff.admin_classes import RoleAdmin, StaffAdmin, AssignmentAdmin, EventTemplateAdmin, EventAdmin
from staff.models import Role, Staff, Assignment, EventTemplate, Event

class EventsAdminSite(AdminSite):
    site_header = 'Catering Events Administration'
    site_title = "Events Portal"
    index_title = "Events Management"

events_admin_site = EventsAdminSite(name='events_admin')

events_admin_site.register(Role, RoleAdmin)
events_admin_site.register(Staff, StaffAdmin)
events_admin_site.register(Assignment, AssignmentAdmin)
events_admin_site.register(EventTemplate, EventTemplateAdmin)
events_admin_site.register(Event, EventAdmin)
# --- END INLINED ---


urlpatterns = [
    # path('health/', include('health.urls')),  <- DELETE OR COMMENT THIS
    path('admin/', admin.site.urls),
    path('staff_admin/', staff_admin_site.urls),
    path('eventsportal/', events_admin_site.urls), # <- This will 100% load now
    
    path('staff/', include('staff.urls')),
    path('logout/', views.logout_view, name='logout'),
    path('', views.home, name='home'),
    # path('<path:path>', views.catch_all), # KEEP THIS COMMENTED FOR NOW
]


print(">>> FINAL URLS:", [str(p.pattern) for p in urlpatterns])