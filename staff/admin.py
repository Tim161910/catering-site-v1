from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse_lazy
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta

from .models import Event, Staff, Assignment, Role, EventTemplate, EventTemplateRole, IssueType, Incident
from .forms import StaffForm

from django.urls import reverse_lazy

class StaffSite(admin.AdminSite):
    site_header = 'Catering Management Administration'
    site_title = "Staff Portal"
    index_title = "Staff Operations"
    index_template = "admin/staff_index.html" 
    site_url = "/"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('risk-dashboard/', self.admin_view(self.risk_dashboard), name='risk-dashboard'),
            path('auto-fill-roster/<int:event_id>/', self.admin_view(self.auto_fill_roster), name='auto-fill-roster'),
        ]
        return custom_urls + urls
    
    def risk_dashboard(self, request):
        today = timezone.now()
        upcoming_events = Event.objects.filter(
            start_time__gte=today, start_time__lte=today + timedelta(days=14)
        ).prefetch_related('assignments__staff', 'assignments__staff__role').order_by('start_time')

        risky_staff = Staff.objects.filter(reliability_score__lt=80, is_active=True).select_related('role').order_by('reliability_score')

        context = dict(self.each_context(request), upcoming_events=upcoming_events, risky_staff=risky_staff, title="Event Risk Dashboard")
        return render(request, "admin/risk_dashboard.html", context)

    def auto_fill_event(self, event):
        empty_duties = event.assignments.filter(staff__isnull=True, status='assigned').select_related('role')
        filled_count = 0
        for duty in empty_duties:
            assigned_staff_ids = event.assignments.filter(staff__isnull=False).values_list('staff_id', flat=True)
            candidates = Staff.objects.filter(role=duty.role, is_active=True, reliability_score__gte=75).exclude(id__in=assigned_staff_ids)
            for candidate in candidates:
                conflicts = Assignment.objects.filter(staff=candidate, event__start_time__lt=event.end_time, event__end_time__gt=event.start_time).exclude(event=event).exists() if event.start_time and event.end_time else False
                if not conflicts:
                    duty.staff = candidate
                    duty.save(update_fields=['staff'])
                    filled_count += 1
                    break
        return filled_count

    def auto_fill_roster(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        filled_count = self.auto_fill_event(event)
        messages.success(request, f"Auto-filled {filled_count} duties for event '{event.title}'.")
        return redirect(reverse_lazy('staff_admin:risk-dashboard'))
    
# ADMIN CLASSES
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

class EventTemplateRoleInline(admin.TabularInline):
    model = EventTemplateRole
    extra = 1
    autocomplete_fields = ['role']

class EventTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    inlines = [EventTemplateRoleInline]
    list_editable = ['is_active']

class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_time', 'client_name']
    list_filter = ['start_time']
    search_fields = ['title', 'client_name']

class StaffAdmin(admin.ModelAdmin):
    form = StaffForm
    list_display = ('name', 'role', 'phone', 'reliability_badge', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('name', 'email', 'phone')
    readonly_fields = ('reliability_score',)

    @admin.display(description='Reliability')
    def reliability_badge(self, obj):
        score = obj.reliability_score or 0
        color = '#28a745' if score >= 90 else '#ffc107' if score >= 75 else '#dc3545'
        emoji = '🟢' if score >= 90 else '🟡' if score >= 75 else '🔴'
        return format_html('<span style="color: {}; font-weight: 600;">{} {}%</span>', color, emoji, score)

class IssueTypeAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

class IncidentAdmin(admin.ModelAdmin):
    list_display = ['staff', 'event', 'issue_type', 'resolved']
    search_fields = ['staff__name']

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['event', 'duty_number', 'staff', 'role', 'status']  # REMOVED start_time
    list_filter = ['status', 'event', 'role']
    search_fields = ['staff__name', 'event__title']
    
    def event_date(self, obj):
        return obj.event.start_time
    event_date.short_description = 'Event Date'  # Optional: if you want to see the date

# REGISTER ONLY TO STAFF_ADMIN_SITE
staff_admin_site = StaffSite(name='staff_admin')
staff_admin_site.register(Role, RoleAdmin)
staff_admin_site.register(Staff, StaffAdmin)
staff_admin_site.register(Assignment, AssignmentAdmin)
staff_admin_site.register(EventTemplate, EventTemplateAdmin)
staff_admin_site.register(Event, EventAdmin)
staff_admin_site.register(IssueType, IssueTypeAdmin)
staff_admin_site.register(Incident, IncidentAdmin)