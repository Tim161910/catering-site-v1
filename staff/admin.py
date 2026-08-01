from django.contrib import admin, messages
from django.urls import path, reverse_lazy
from django.utils import timezone
from datetime import timedelta
from django.utils.html import format_html, mark_safe
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from.forms import StaffForm
from django.contrib import admin as default_admin
from django.contrib.auth.models import Group, User

from.models import (
    Role, EventTemplate, EventTemplateRole, Event,
    Staff, IssueType, Incident, Assignment,
)

today = timezone.now()

admin.site_header = "Catering Operations"
admin.site.site_title = "Catering Admin"
admin.site.index_title = "Dashboard"

# ==========================================
# 1. CUSTOM ADMIN SITE
# ==========================================
class StaffSite(admin.AdminSite):
    site_header = "Staff Manager Portal"
    site_title = "Staff Portal"
    index_title = "Staff Operations"
    index_template = "admin/staff_index.html"

    def get_app_list(self, request):
        return [
            {'name': 'STAFF DIRECTORY', 'app_label': 'staff', 'models': [
                {'name': 'Staffs', 'admin_url': reverse_lazy('staff_staff_changelist'), 'view_only': False},
                {'name': 'Roles', 'admin_url': reverse_lazy('staff_role_changelist'), 'view_only': False},
                {'name': 'Job Assignments', 'admin_url': reverse_lazy('staff_assignment_changelist'), 'view_only': False},
            ]},
            {'name': 'SCHEDULING & RELIABILITY', 'app_label': 'staff', 'models': [
                {'name': 'Event Risk Dashboard', 'admin_url': reverse_lazy('risk-dashboard'), 'view_only': True},
                {'name': 'Events', 'admin_url': reverse_lazy('staff_event_changelist'), 'view_only': False},
                {'name': 'Event Templates', 'admin_url': reverse_lazy('staff_eventtemplate_changelist'), 'view_only': False},
            ]},
            {'name': 'COMPLIANCE', 'app_label': 'staff', 'models': [
                {'name': 'Incidents', 'admin_url': reverse_lazy('staff_incident_changelist'), 'view_only': False},
                {'name': 'HR Issues', 'admin_url': reverse_lazy('staff_issuetype_changelist'), 'view_only': False},
            ]},
        ]

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
        return redirect(reverse_lazy('risk-dashboard'))

# ==========================================
# 2. ADMIN CLASSES - ONLY FOR THE 7 MODELS WE USE
# ==========================================
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

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
    list_display = ['title', 'start_time', 'client_name', 'assignment_count']
    list_filter = ['start_time']
    search_fields = ['title', 'client_name']

    def assignment_count(self, obj):
        total = obj.assignments.count()
        filled = obj.assignments.filter(staff__isnull=False).count()
        return format_html('{}/{} filled', filled, total)
    assignment_count.short_description = 'Duties'

class StaffAdmin(admin.ModelAdmin):
    form = StaffForm
    list_display = ('name', 'role', 'phone', 'reliability_badge', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('name', 'email', 'phone')
    readonly_fields = ('reliability_score',)

    @admin.display(description='Reliability', ordering='reliability_score')
    def reliability_badge(self, obj):
        score = obj.reliability_score or 0
        color = '#28a745' if score >= 90 else '#ffc107' if score >= 75 else '#dc3545'
        emoji = '🟢' if score >= 90 else '🟡' if score >= 75 else '🔴'
        return format_html('<span style="color: {}; font-weight: 600;">{} {}%</span>', color, emoji, score)

class IssueTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'weight_percent']
    list_editable = ['weight_percent']

class IncidentAdmin(admin.ModelAdmin):
    list_display = ['staff', 'event', 'issue_type', 'resolved']
    list_filter = ['issue_type', 'resolved']
    search_fields = ['staff__name']
    autocomplete_fields = ['staff', 'event']

class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['event', 'duty_number', 'staff', 'role', 'status']
    list_filter = ['event', 'role', 'status']
    search_fields = ['staff__name', 'event__title']
    ordering = ['event', 'duty_number']
    list_editable = ['staff', 'status']

# ==========================================
# 3. REGISTRATION
# ==========================================
staff_admin_site = StaffSite(name='staff_admin')
staff_admin_site.register(Role, RoleAdmin)
staff_admin_site.register(Staff, StaffAdmin)
staff_admin_site.register(Assignment, AssignmentAdmin)
staff_admin_site.register(EventTemplate, EventTemplateAdmin)
staff_admin_site.register(Event, EventAdmin)
staff_admin_site.register(IssueType, IssueTypeAdmin)
staff_admin_site.register(Incident, IncidentAdmin)

# Keep full admin for you
default_admin.site.register(Role, RoleAdmin)
default_admin.site.register(EventTemplate, EventTemplateAdmin)
default_admin.site.register(Event, EventAdmin)
default_admin.site.register(Staff, StaffAdmin)
default_admin.site.register(IssueType, IssueTypeAdmin)
default_admin.site.register(Incident, IncidentAdmin)
default_admin.site.register(Assignment, AssignmentAdmin)

try:
    default_admin.site.unregister(Group)
    default_admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass