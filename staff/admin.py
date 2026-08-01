from django.contrib import admin, messages
from django.urls import path, reverse_lazy
from django.utils import timezone
from datetime import datetime, timedelta
from django.utils.html import format_html, mark_safe
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .forms import StaffForm
from django.contrib import admin as default_admin
from django.contrib.auth.models import Group, User 

from .models import (
    Role, EventTemplate, EventTemplateRole, Event,
    Staff, StaffUpdateLog, StaffUpdateRequest, StaffUpdateApproval,
    IssueType, Incident, Rule, Flag,
    Assignment, Task,
    Recruitment, InterviewSlot, Applicant, Interview, RolePlay, ApplicantRolePlay, RolePlayResponse,
    Meeting, Expense, LeaveRequest,
    Notification,
)


today = timezone.now()

admin.site.site_header = "Catering Operations"
admin.site.site_title = "Catering Admin"
admin.site.index_title = "Dashboard"


# ==========================================
# # 1. IMPORTS + CUSTOM ADMIN SITE
# ==========================================

class StaffSite(admin.AdminSite):
    site_header = "Catering Operations"
    site_title = "Catering Admin"
    index_title = "Dashboard"
    index_template = "admin/staff_index.html"

    def each_context(self, request):
        context = super().each_context(request)
        context['event_status_url'] = '/staff/event-status/'
        return context

    def get_app_list(self, request):
        return [
            {
                'name': 'STAFF DIRECTORY',
                'app_label': 'staff',
                'models': [
                    {'name': 'Staffs', 'admin_url': reverse_lazy('staff_staff_changelist'), 'view_only': False},
                    {'name': 'Roles', 'admin_url': reverse_lazy('staff_role_changelist'), 'view_only': False},
                    {'name': 'Job Assignments', 'admin_url': reverse_lazy('staff_assignment_changelist'), 'view_only': False},
                ]
            },
            {
                'name': 'SCHEDULING & RELIABILITY',
                'app_label': 'staff',
                'models': [
                    {'name': 'Event Risk Dashboard', 'admin_url': reverse_lazy('risk-dashboard'), 'view_only': True},
                    {'name': 'Events', 'admin_url': reverse_lazy('staff_event_changelist'), 'view_only': False},
                    {'name': 'Event Templates', 'admin_url': reverse_lazy('staff_eventtemplate_changelist'), 'view_only': False},
                ]
            },
            {
                'name': 'COMPLIANCE',
                'app_label': 'staff',
                'models': [
                    {'name': 'Incidents', 'admin_url': reverse_lazy('staff_incident_changelist'), 'view_only': False},
                    {'name': 'HR Issues', 'admin_url': reverse_lazy('staff_issuetype_changelist'), 'view_only': False},
                ]
            },
        ]

    def get_urls(self):
        urls = super().get_urls() 
        custom_urls = [
            path('risk-dashboard/', self.admin_view(self.risk_dashboard_view), name='risk-dashboard'),
            path('auto-fill-roster/<int:event_id>/', self.admin_view(self.auto_fill_roster), name='auto-fill-roster'),
            path('replace-staff/<int:assignment_id>/', self.admin_view(self.replace_staff), name='replace-staff'),
        ]
        return custom_urls + urls

    def risk_dashboard_view(self, request):
        today = timezone.now()
        upcoming_events = Event.objects.filter(
            start_time__gte=today,
            start_time__lte=today + timedelta(days=14)
        ).prefetch_related('assignments__staff', 'assignments__staff__role').order_by('start_time')

        risky_staff = Staff.objects.filter(
            reliability_score__lt=80,
            is_active=True
        ).select_related('role').order_by('reliability_score')

        context = dict(
            self.each_context(request),
            upcoming_events=upcoming_events,
            risky_staff=risky_staff,
            title="Event Risk Dashboard"
        )
        return render(request, "admin/risk_dashboard.html", context)

    def auto_fill_event(self, event):
        empty_duties = event.assignments.filter(staff__isnull=True, status='assigned').select_related('role')
        filled_count = 0
        for duty in empty_duties:
            candidates = Staff.objects.filter(role=duty.role, is_active=True, reliability_score__gte=75).exclude(id__in=event.assignments.filter(staff__isnull=False).values_list('staff_id', flat=True))
            for candidate in candidates:
                conflicts = False
                if event.start_time and event.end_time:
                    conflicts = Assignment.objects.filter(staff=candidate, event__start_time__lt=event.end_time, event__end_time__gt=event.start_time).exclude(event=event).exists()
                if not conflicts:
                    duty.staff = candidate
                    if hasattr(duty, 'start_time') and hasattr(duty, 'end_time'):
                        duty.start_time = event.start_time
                        duty.end_time = event.end_time
                        duty.save(update_fields=['staff', 'start_time', 'end_time'])
                    else:
                        duty.save(update_fields=['staff'])
                    filled_count += 1
                    break
        return filled_count

    def auto_fill_roster(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        filled_count = self.auto_fill_event(event)
        messages.success(request, f"Auto-filled {filled_count} duties for event '{event.title}'.")
        return redirect(reverse_lazy('risk-dashboard'))

    @csrf_exempt
    def replace_staff(self, request, assignment_id):
        assignment = get_object_or_404(Assignment, id=assignment_id)
        new_staff = get_object_or_404(Staff, id=request.POST.get('new_staff_id'))
        event = assignment.event
        conflicts = False
        if event.start_time and event.end_time:
            conflicts = Assignment.objects.filter(staff=new_staff, event__start_time__lt=event.end_time, event__end_time__gt=event.start_time).exclude(event=event).exists()
        if conflicts:
            return JsonResponse({'success': False, 'error': 'Staff has a conflicting booking'})
        assignment.staff = new_staff
        assignment.save(update_fields=['staff'])
        return JsonResponse({'success': True})

# ==========================================
# # 2. CORE/UTILS
# ==========================================
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

# ==========================================
# # 3. EVENTS
# ==========================================
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

class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_time', 'client_name', 'template', 'assignment_count', 'location']
    list_filter = ['start_time', 'template']
    search_fields = ['title', 'client_name']
    autocomplete_fields = ['template']

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)

        if is_new and obj.template and not Assignment.objects.filter(event=obj).exists():
            duty_num = 1
            created = 0
            for tr in obj.template_roles.all():
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

            empty_duties = obj.assignments.filter(staff__isnull=True, status='assigned').select_related('role')
            filled_count = 0
            for duty in empty_duties:
                assigned_staff_ids = obj.assignments.filter(staff__isnull=False).values_list('staff_id', flat=True)
                candidate = Staff.objects.filter(
                    role=duty.role,
                    is_active=True,
                    reliability_score__gte=75
                ).exclude(id__in=assigned_staff_ids).order_by('-reliability_score').first()
                if candidate:
                    duty.staff = candidate
                    duty.save(update_fields=['staff'])
                    filled_count += 1
            messages.success(request, f"Created {created} duties from template and auto-filled {filled_count}.")

    def assignment_count(self, obj):
        total = obj.assignments.count()
        filled = obj.assignments.filter(staff__isnull=False, status='assigned').count()
        return format_html('{}/{} filled', filled, total)
    assignment_count.short_description = 'Duties'

# ==========================================
# # 4. STAFF
# ==========================================
class StaffAdmin(admin.ModelAdmin):
    form = StaffForm
    list_display = ('name', 'role', 'phone', 'reliability_badge', 'is_active')
    list_filter = ('role', 'is_active', 'reliability_score')
    search_fields = ('name', 'email', 'phone')
    readonly_fields = ('reliability_score',)
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'email', 'role', 'is_active')}),
        ('Contact', {'fields': ('phone', 'whatsapp', 'address')}),
        ('Emergency Contact', {'fields': ('next_of_kin', 'emergency_contact_name', 'emergency_contact_phone')}),
        ('Performance', {'fields': ('reliability_score', 'reliability_notes')}),
    )

    @admin.display(description='Reliability', ordering='reliability_score')
    def reliability_badge(self, obj):
        score = obj.reliability_score
        if score >= 90:
            color = '#28a745'; emoji = '🟢'
        elif score >= 75:
            color = '#ffc107'; emoji = '🟡'
        else:
            color = '#dc3545'; emoji = '🔴'
        return format_html('<span style="color: {}; font-weight: 600;">{} {}%</span>', color, emoji, score)

class StaffUpdateLogAdmin(admin.ModelAdmin): pass
class StaffUpdateRequestAdmin(admin.ModelAdmin): pass
class StaffUpdateApprovalAdmin(admin.ModelAdmin): pass

# ==========================================
# # 5. RELIABILITY
# ==========================================
class IssueTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'weight_percent', 'counts_against_staff']
    list_editable = ['weight_percent', 'counts_against_staff']

class IncidentAdmin(admin.ModelAdmin):
    list_display = ['staff', 'event', 'issue_type', 'incident_type', 'reliability_impact', 'resolved', 'reported_on']
    list_filter = ['issue_type', 'incident_type', 'reliability_impact', 'resolved', 'reported_on']
    search_fields = ['staff__name', 'incident_type', 'notes', 'description']
    list_editable = ['resolved']
    readonly_fields = ['reported_on']
    autocomplete_fields = ['staff', 'event']

    fieldsets = (
        ('Basic Info', {'fields': ('staff', 'event', 'issue_type')}),
        ('Incident Details', {'fields': ('incident_type', 'reliability_impact', 'notes', 'description')}),
        ('Status', {'fields': ('resolved', 'reported_on')}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('staff', 'event', 'issue_type')

class RuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'rule_type', 'issue_type', 'threshold', 'days', 'is_active']
    list_filter = ['rule_type', 'is_active']
    search_fields = ['name']

class FlagAdmin(admin.ModelAdmin):
    list_display = ['staff', 'rule', 'flag_level', 'last_triggered']
    list_filter = ['flag_level', 'rule']
    readonly_fields = ['created_at', 'last_triggered']
    search_fields = ['staff__name', 'rule__name']

# ==========================================
# # 6. ASSIGNMENTS
# ==========================================
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['event', 'duty_number', 'staff', 'role', 'staff_score', 'status']
    list_filter = ['event', 'role', 'status']
    search_fields = ['staff__name', 'event__title', 'role__name']
    ordering = ['event', 'duty_number']
    list_editable = ['staff', 'status']

    def staff_score(self, obj):
        if obj.staff:
            return f"{obj.staff.reliability_score}%"
        return "—"
    staff_score.short_description = 'Reliability'

class TaskAdmin(admin.ModelAdmin): pass

# ==========================================
# # 7. RECRUITMENT
# ==========================================
class RecruitmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'event')
    list_filter = ('status',)
    search_fields = ('title',)

class InterviewSlotAdmin(admin.ModelAdmin):
    list_display = ('recruitment', 'interviewer', 'start_time', 'end_time')
    list_filter = ('recruitment', 'interviewer')
    search_fields = ('interviewer__name',)

class InterviewAdmin(admin.ModelAdmin): pass

class ApplicantAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'status', 'interview_time', 'applied_at', 'recruitment')
    list_filter = ('status', 'applied_at', 'recruitment')
    search_fields = ('name', 'email')
    date_hierarchy = 'applied_at'

class RolePlayAdmin(admin.ModelAdmin): pass
class ApplicantRolePlayAdmin(admin.ModelAdmin): pass

class RolePlayResponseAdmin(admin.ModelAdmin):
    list_display = ['staff', 'roleplay', 'submitted_at']
    list_filter = ['submitted_at', 'roleplay__role']
    search_fields = ['staff__name', 'action']

# ==========================================
# # 8. MISC
# ==========================================
class MeetingAdmin(admin.ModelAdmin): pass
class ExpenseAdmin(admin.ModelAdmin): pass
class LeaveRequestAdmin(admin.ModelAdmin): pass

# ==========================================
# # 9. NOTIFICATIONS
# ==========================================
class NotificationAdmin(admin.ModelAdmin): pass

# ==========================================
# # 10. REGISTER - DEMO MODE ONLY
# ==========================================
staff_admin_site = StaffSite(name='staff_admin')

# CORE 3 GROUPS ONLY - What she will see
staff_admin_site.register(Role, RoleAdmin)
staff_admin_site.register(Staff, StaffAdmin)
staff_admin_site.register(Assignment, AssignmentAdmin)

staff_admin_site.register(EventTemplate, EventTemplateAdmin)
staff_admin_site.register(Event, EventAdmin)

staff_admin_site.register(IssueType, IssueTypeAdmin)
staff_admin_site.register(Incident, IncidentAdmin)

# HIDDEN FOR DEMO - Uncomment later for Phase 2
# staff_admin_site.register(StaffUpdateLog, StaffUpdateLogAdmin)
# staff_admin_site.register(StaffUpdateRequest, StaffUpdateRequestAdmin)
# staff_admin_site.register(StaffUpdateApproval, StaffUpdateApprovalAdmin)
# staff_admin_site.register(Rule, RuleAdmin)
# staff_admin_site.register(Flag, FlagAdmin)
# staff_admin_site.register(Task, TaskAdmin)
# staff_admin_site.register(Recruitment, RecruitmentAdmin)
# staff_admin_site.register(InterviewSlot, InterviewSlotAdmin)
# staff_admin_site.register(Applicant, ApplicantAdmin)
# staff_admin_site.register(Interview, InterviewAdmin)
# staff_admin_site.register(RolePlay, RolePlayAdmin)
# staff_admin_site.register(ApplicantRolePlay, ApplicantRolePlayAdmin)
# staff_admin_site.register(RolePlayResponse, RolePlayResponseAdmin)
# staff_admin_site.register(Meeting, MeetingAdmin)
# staff_admin_site.register(Expense, ExpenseAdmin)
# staff_admin_site.register(LeaveRequest, LeaveRequestAdmin)
# staff_admin_site.register(Notification, NotificationAdmin)

# ==========================================
# # 11. REGISTER TO DEFAULT ADMIN TOO - KEEP FULL FOR YOU
# ==========================================
default_admin.site.register(Role, RoleAdmin)
default_admin.site.register(EventTemplate, EventTemplateAdmin)
default_admin.site.register(Event, EventAdmin)
default_admin.site.register(Staff, StaffAdmin)
default_admin.site.register(StaffUpdateLog, StaffUpdateLogAdmin)
default_admin.site.register(StaffUpdateRequest, StaffUpdateRequestAdmin)
default_admin.site.register(StaffUpdateApproval, StaffUpdateApprovalAdmin)
default_admin.site.register(IssueType, IssueTypeAdmin)
default_admin.site.register(Incident, IncidentAdmin)
default_admin.site.register(Rule, RuleAdmin)
default_admin.site.register(Flag, FlagAdmin)
default_admin.site.register(Assignment, AssignmentAdmin)
default_admin.site.register(Task, TaskAdmin)
default_admin.site.register(Recruitment, RecruitmentAdmin)
default_admin.site.register(InterviewSlot, InterviewSlotAdmin)
default_admin.site.register(Applicant, ApplicantAdmin)
default_admin.site.register(Interview, InterviewAdmin)
default_admin.site.register(RolePlay, RolePlayAdmin)
default_admin.site.register(ApplicantRolePlay, ApplicantRolePlayAdmin)
default_admin.site.register(RolePlayResponse, RolePlayResponseAdmin)
default_admin.site.register(Meeting, MeetingAdmin)
default_admin.site.register(Expense, ExpenseAdmin)
default_admin.site.register(LeaveRequest, LeaveRequestAdmin)
default_admin.site.register(Notification, NotificationAdmin)

# ==========================================
# # 12. HIDE GROUPS AND USERS FROM DEFAULT ADMIN
# ==========================================
try:
    default_admin.site.unregister(Group)
    default_admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass # already not registered, ignore
