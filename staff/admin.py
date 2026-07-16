from django.contrib import admin, messages
from django.urls import path, reverse_lazy
from django.template.response import TemplateResponse
from django.utils import timezone
from .models import RolePlayResponse, Staff, Event, IssueType, Incident, Assignment, Role, EventTemplate, EventTemplateRole, Applicant, Recruitment, InterviewSlot
from django.utils.html import format_html, mark_safe
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.utils.decorators import method_decorator
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

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

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

        # Only clone + auto-fill when creating AND template is set AND no duties exist yet
        if is_new and obj.template and not Assignment.objects.filter(event=obj).exists():
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
            
            # Auto-fill after cloning
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

class IssueTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'weight_percent', 'counts_against_staff']
    list_editable = ['weight_percent', 'counts_against_staff']
    
class IncidentAdmin(admin.ModelAdmin):
    list_display = ['staff', 'event', 'issue_type', 'incident_type', 'reliability_impact', 'resolved', 'reported_on']
    list_filter = ['issue_type', 'incident_type', 'reliability_impact', 'resolved', 'reported_on']
    search_fields = ['staff__name', 'incident_type', 'notes', 'description']
    list_editable = ['resolved'] 
    readonly_fields = ['reported_on']
    autocomplete_fields = ['staff', 'event'] # makes dropdowns faster
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('staff', 'event', 'issue_type')
        }),
        ('Incident Details', {
            'fields': ('incident_type', 'reliability_impact', 'notes', 'description')
        }),
        ('Status', {
            'fields': ('resolved', 'reported_on')
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('staff', 'event', 'issue_type') # faster loading

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
            path('replace-staff/<int:assignment_id>/', self.admin_view(self.replace_staff), name='replace-staff'),
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
                'admin_url': reverse_lazy('staff_admin:event-status'),
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
                conflicts = []
                if assign.staff:
                    score = assign.staff.reliability_score
                    status = 'Critical' if score < 50 else 'Warning' if score < 75 else 'OK'
                    if score < 75:
                        at_risk_count += 1

                    # FIX: Only check conflicts if both event times exist
                    if event.start_time and event.end_time:
                        conflicts = list(Assignment.objects.filter(
                            staff=assign.staff,
                            status='assigned',
                            event__start_time__lt=event.end_time,
                            event__end_time__gt=event.start_time
                        ).exclude(event=event).values_list('event__title', flat=True))

                else:
                    score = 0
                    status = 'Empty'

                # FIX: Build replacement queryset with conflict exclusion only if times exist
                replacements_qs = Staff.objects.filter(
                    role=assign.role,
                    is_active=True,
                    reliability_score__gte=75
                ).exclude(id__in=assigned_ids)

                if event.start_time and event.end_time: # ADD THIS CHECK
                    conflicting_staff_ids = Assignment.objects.filter(
                        status='assigned',
                        event__start_time__lt=event.end_time,
                        event__end_time__gt=event.start_time
                    ).values_list('staff_id', flat=True)
                    replacements_qs = replacements_qs.exclude(id__in=conflicting_staff_ids)
                
                replacements = replacements_qs.order_by('-reliability_score')[:5]

                duties.append({
                    'assignment_id': assign.id,
                    'duty_number': assign.duty_number,
                    'staff': assign.staff,
                    'role': assign.role.name if assign.role else 'No Role',
                    'score': score,
                    'status': status,
                    'replacements': replacements,
                    'conflicts': conflicts
                })
            empty_count = event.assignments.filter(staff__isnull=True, status='assigned').count()
            ok_count = len(duties) - at_risk_count - empty_count
            event_data.append({
                'event': event,
                'duties': duties,
                'total_duties': len(duties),
                'at_risk': at_risk_count,
                'empty_count': empty_count,
                'ok_count': ok_count
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
        return TemplateResponse(request,"staff/event_status.html", context)

    def auto_fill_event(self, event):
        empty_duties = event.assignments.filter(staff__isnull=True, status='assigned').select_related('role')
        filled_count = 0

        for duty in empty_duties:
            # Find staff available + matching role + no conflicts
            candidates = Staff.objects.filter(
                role=duty.role,
                is_active=True,
                reliability_score__gte=75
            ).exclude(
                id__in=event.assignments.filter(staff__isnull=False).values_list('staff_id', flat=True)
            )

            for candidate in candidates:
                # Check time conflicts - only check if event has valid start and end times
                conflicts = False
                if event.start_time and event.end_time:
                    conflicts = Assignment.objects.filter(
                        staff=candidate,
                        event__start_time__lt=event.end_time,
                        event__end_time__gt=event.start_time
                    ).exclude(event=event).exists()

                if not conflicts:
                    duty.staff = candidate
                    # only set times if the Assignment model has start_time and end_time fields; if not, this will raise an error. Adjust accordingly.
                    if hasattr(duty, 'start_time') and hasattr(duty, 'end_time'):
                        duty.start_time = event.start_time
                        duty.end_time = event.end_time
                        duty.save(update_fields=['staff', 'start_time', 'end_time'])
                    else:
                        duty.save(update_fields=['staff'])

                    filled_count += 1
                    break  # Move to next duty

        return filled_count
    
    def auto_fill_roster(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        filled_count = self.auto_fill_event(event)
        messages.success(request, f"Auto-filled {filled_count} duties for event '{event.title}'.")
        return redirect('staff_admin:event-status')
        

    @csrf_exempt
    def replace_staff(self, request, assignment_id):
        assignment = get_object_or_404(Assignment, id=assignment_id)
        new_staff = get_object_or_404(Staff, id=request.POST.get('new_staff_id'))
        event = assignment.event

        # Check conflicts
        conflicts = False
        if event.start_time and event.end_time:
            conflicts = Assignment.objects.filter(
                staff=new_staff,
                event__start_time__lt=event.end_time,
                event__end_time__gt=event.start_time
            ).exclude(event=event).exists()

        if conflicts:
            return JsonResponse({'success': False, 'error': 'Staff has a conflicting booking'})

        assignment.staff = new_staff
        assignment.save(update_fields=['staff'])
        return JsonResponse({'success': True})

class ApplicantAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'status', 'interview_time', 'applied_at', 'recruitment')
    list_filter = ('status', 'applied_at', 'recruitment')
    search_fields = ('name', 'email')
    date_hierarchy = 'applied_at'

class RecruitmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'event')
    list_filter = ('status',)
    search_fields = ('title',)

class InterviewSlotAdmin(admin.ModelAdmin):
    list_display = ('recruitment', 'interviewer', 'start_time', 'end_time')
    list_filter = ('recruitment', 'interviewer')
    search_fields = ('interviewer__name',)

# Activate custom admin site
staff_admin_site = StaffSite(name='staff_admin')

# Register to your CUSTOM admin site
staff_admin_site.register(Applicant, ApplicantAdmin)
staff_admin_site.register(Recruitment, RecruitmentAdmin)
staff_admin_site.register(InterviewSlot, InterviewSlotAdmin)

# Register all models to custom site
staff_admin_site.register(Staff, StaffAdmin)
staff_admin_site.register(RolePlayResponse, RolePlayResponseAdmin)
staff_admin_site.register(Event, EventAdmin)
staff_admin_site.register(IssueType, IssueTypeAdmin)
staff_admin_site.register(Incident, IncidentAdmin)
staff_admin_site.register(Assignment, AssignmentAdmin)
staff_admin_site.register(Role, RoleAdmin)
staff_admin_site.register(EventTemplate, EventTemplateAdmin)