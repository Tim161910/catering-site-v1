from urllib import request

from django.contrib import admin, messages
from django.urls import path, reverse
from django.template.response import TemplateResponse
from django.utils import timezone
from .models import RolePlayResponse, Staff, Event, IssueType, Incident, Assignment, Role, EventTemplate, EventTemplateRole
from django.utils.html import format_html
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from .forms import StaffForm

today = timezone.now().date()

class EventTemplateRoleInline(admin.TabularInline):
    model = EventTemplateRole
    extra = 1
    autocomplete_fields = ['role']
    min_num = 0

class EventTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'role_summary', 'event_count', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']
    inlines = [EventTemplateRoleInline]
    list_editable = ['is_active']

    def role_summary(self, obj):
        roles = obj.template_roles.select_related('role').all()
        if not roles:
            return mark_safe('<span style="color: #999;">No roles</span>')
        return ", ".join([f"{tr.count}× {tr.role.name}" for tr in roles])
    role_summary.short_description = 'Staffing'

    def event_count(self, obj):
        return obj.event_set.count()
    event_count.short_description = 'Events Using'

class StaffAdmin(admin.ModelAdmin):
    form = StaffForm
    list_display = ('name', 'role', 'phone', 'reliability_score', 'is_active')
    list_filter = ('role', 'is_active', 'reliability_score')
    search_fields = ('name', 'email', 'phone')
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'email', 'role', 'is_active')}),
        ('Contact', {'fields': ('phone', 'whatsapp', 'address')}),
        ('Emergency Contact', {'fields': ('next_of_kin', 'emergency_contact_name', 'emergency_contact_phone')}),
        ('Performance', {'fields': ('reliability_score', 'reliability_notes')}),
    )

class RolePlayResponseAdmin(admin.ModelAdmin):
    list_display = ['staff', 'roleplay', 'submitted_at']
    list_filter = ['submitted_at', 'roleplay__role']
    search_fields = ['staff__name', 'action']

class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_time', 'client_name', 'template', 'assignment_count', 'location']
    list_filter = ['start_time', 'template']
    search_fields = ['title', 'client_name']
    autocomplete_fields = ['template']

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)

        if is_new and obj.template:
            duty_num = 1
            created = 0
            for tr in obj.template.template_roles.all():
                for _ in range(tr.count):
                    Assignment.objects.create(
                        event=obj,
                        role=tr.role,
                        duty_number=duty_num,
                        status='assigned',
                        staff=None
                    )
                    duty_num += 1
                    created += 1
            if created:
                messages.success(request, f"Created {created} empty duties from template '{obj.template.name}'")
            
    def assignment_count(self, obj):
        total = obj.assignments.count()
        filled = obj.assignments.filter(staff__isnull=False, status='assigned').count()
        return format_html('{}/{} filled', filled, total)
    assignment_count.short_description = 'Duties'

class IssueTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'weight_percent', 'counts_against_staff']
    list_editable = ['weight_percent', 'counts_against_staff']
    
class IncidentAdmin(admin.ModelAdmin):
    list_display = ['staff', 'issue_type', 'event', 'resolved', 'reported_on']
    list_filter = ['issue_type', 'resolved', 'reported_on']
    search_fields = ['staff__name']

class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['event', 'duty_number', 'staff', 'role', 'staff_score', 'status']
    list_filter = ['event', 'role', 'status']
    search_fields = ['staff__name', 'event__title', 'role__name']
    ordering = ['event', 'duty_number']  # keeps slots 1,2,3 in order
    list_editable = ['staff', 'status']  # assign without opening each record

    def staff_score(self, obj):
        if obj.staff:
            return f"{obj.staff.reliability_score}%"
        return "—"
    staff_score.short_description = 'Reliability'

class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

class StaffSite(admin.AdminSite):
    site_header = "Catering Operations"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('event-status/', self.admin_view(self.event_status_view), name='event-status'),
            path('auto-fill-roster/<int:event_id>/', self.admin_view(self.auto_fill_roster), name='auto-fill-roster'),
        ]
        return custom_urls + urls

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        app_list.insert(0, {
            'name': 'Operations',
            'app_label': 'operations',
            'models': [{
                'name': 'Event Risk Dashboard',
                'object_name': 'EventRiskDashboard',
                'admin_url': reverse('admin:event-status'),
                'view_only': True,
            }]
        })
        return app_list

    def event_status_view(self, request):
        today = timezone.now().date()
        events = Event.objects.filter(start_time__date__gte=today).prefetch_related(
            'assignments__staff',
            'assignments__role'
        ).order_by('start_time')

        event_data = []
        for event in events:
            duties = []
            assigned_ids = list(event.assignments.filter(status='assigned', staff__isnull=False).values_list('staff_id', flat=True))
            at_risk_count = 0

            for assign in event.assignments.filter(status='assigned').select_related('staff', 'role').order_by('duty_number'):
                    if assign.staff:
                        score = assign.staff.reliability_score
                        status = 'Critical' if score < 50 else 'Warning' if score < 75 else 'OK'
                        if score < 75:
                            at_risk_count += 1
                    else:
                        score = 0
                        status = 'Empty'

                    replacements = Staff.objects.filter(
                        role=assign.role,
                        is_active=True,
                        reliability_score__gte=90
                    ).exclude(id__in=assigned_ids).order_by('-reliability_score')[:5]

                    duties.append({
                        'assignment_id': assign.id,
                        'duty_number': assign.duty_number,
                        'staff': assign.staff,
                        'role': assign.role.name if assign.role else 'No Role',
                        'score': score,
                        'status': status,
                        'replacements': replacements
                    })

        event_data.append({
            'event': event,
            'duties': duties,
            'total_duties': len(duties),
            'at_risk': at_risk_count,
            'empty_count': event.assignments.filter(staff__isnull=True, status='assigned').count()
        })

        context = dict(
            self.each_context(request),
            total_events=Event.objects.count(),
            upcoming_events=Event.objects.filter(start_time__date__gte=today).count(),
            this_month=Event.objects.filter(start_time__year=today.year, start_time__month=today.month).count(),
            past_events=Event.objects.filter(start_time__date__lt=today).count(),
            recent_events=Event.objects.order_by('-start_time')[:5],
            events=event_data,
            title="",
            subtitle="Event Risk Dashboard"
        )
        return TemplateResponse(request, "admin/event_status.html", context)

    def auto_fill_roster(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        empty_duties = event.assignments.filter(staff__isnull=True, status='assigned').select_related('role')

        filled_count = 0
        with transaction.atomic():
            for duty in empty_duties:
                assigned_staff_ids = event.assignments.filter(staff__isnull=False).values_list('staff_id', flat=True)
                candidate = Staff.objects.filter(
                    role=duty.role,
                    is_active=True,
                    reliability_score__gte=75
                ).exclude(id__in=assigned_staff_ids).order_by('-reliability_score').first()

                if candidate:
                    duty.staff = candidate
                    duty.save(update_fields=['staff'])
                    filled_count += 1

        messages.success(request, f"Auto-filled {filled_count} of {empty_duties.count()} duties for {event.title}")
        return redirect('admin:event-status')
             
# Activate custom admin site
staff_admin_site = StaffSite(name='staff_admin')

# Re-register all models to custom site
staff_admin_site.register(Staff, StaffAdmin)
staff_admin_site.register(RolePlayResponse, RolePlayResponseAdmin)
staff_admin_site.register(Event, EventAdmin)
staff_admin_site.register(IssueType, IssueTypeAdmin)
staff_admin_site.register(Incident, IncidentAdmin)
staff_admin_site.register(Assignment, AssignmentAdmin)
staff_admin_site.register(Role, RoleAdmin)
staff_admin_site.register(EventTemplate, EventTemplateAdmin)