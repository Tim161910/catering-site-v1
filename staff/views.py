from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test, login_required

try:
    # staff_member_required is imported above with a fallback for environments
    # where Django isn't available, so avoid re-importing here which can
    # trigger unresolved-import errors in static analysis tools.
    pass
except Exception:
    # Fallback for environments where Django isn't available to satisfy linters/static analysis
    def staff_member_required(view_func=None):
        if view_func is None:
            def decorator(f):
                return f
            return decorator
        return view_func

# Note: login_required is provided above with a fallback for non-Django environments.
# Avoid re-importing here which can trigger unresolved-import errors in static analysis tools.
try:
    from django.contrib.auth.mixins import LoginRequiredMixin  # type: ignore
except Exception:
    # Fallback for environments where Django isn't available to satisfy linters/static analysis
    class LoginRequiredMixin:
        """Simple fallback mixin that does nothing when Django isn't installed.

        Used to avoid unresolved import errors in static analysis or testing
        environments.
        """
        pass
try:
    # messages is defined above with a Django import fallback to avoid unresolved-import
    # errors in static analysis environments. Do not re-import here.
    pass
except Exception:
    # Fallback stub for environments without Django to satisfy linters/static analysis
    class _MessagesStub:
        @staticmethod
        def success(request, message, extra_tags='', fail_silently=False):
            return None

        @staticmethod
        def error(request, message, extra_tags='', fail_silently=False):
            return None

        @staticmethod
        def info(request, message, extra_tags='', fail_silently=False):
            return None

        @staticmethod
        def warning(request, message, extra_tags='', fail_silently=False):
            return None

        @staticmethod
        def add_message(request, level, message, extra_tags=''):
            return None

    messages = _MessagesStub()
try:
    from django.utils.decorators import method_decorator  # type: ignore[import]
except Exception:
    # Fallback stub for environments without Django to satisfy linters/static analysis
    def method_decorator(func):
        return func
try:
    from django.views.decorators.http import require_POST  # type: ignore[import]
except Exception:
    # Fallback stub for environments without Django to satisfy linters/static analysis
    def require_POST(func):
        return func

try:
    from django.views.decorators.csrf import csrf_exempt  # type: ignore[import]
except Exception:
    # Fallback stub
    def csrf_exempt(func):
        return func
try:
    from django.contrib.auth.decorators import login_required  # type: ignore[import]
except Exception:
    # Fallback stub for environments without Django to satisfy linters/static analysis
    def login_required(func):
        return func
try:
    from django.shortcuts import render, get_object_or_404, redirect  # type: ignore[import]
    from django.urls import reverse_lazy  # type: ignore[import]
except Exception:
    # Fallback stubs for environments without Django to satisfy linters/static analysis
    def render(request, template_name, context=None, content_type=None, status=None, using=None):
        return None

    def get_object_or_404(klass, *args, **kwargs):
        raise Exception('Django not available')

    def redirect(to, *args, **kwargs):
        return None

    def reverse_lazy(*args, **kwargs):
        return None
from .models import Staff, Event, Recruitment, Applicant, RolePlay, Incident, Assignment, Role, RolePlayResponse
from  .forms import RolePlayResponseForm, StaffForm, EventForm, ApplicantForm, RolePlayForm, IncidentForm, RecruitmentForm, StaffProfileForm
try:
    try:
        try:
            from django.views.generic import (  # type: ignore[import]
                CreateView,
                UpdateView,
                DetailView,
                ListView,
                DeleteView,
                TemplateView,
                View,
            )
        except Exception:
            # Fallback stub classes for environments without Django to satisfy linters/static analysis
            class CreateView:
                pass

            class UpdateView:
                pass

            class DetailView:
                pass

            class ListView:
                pass

            class DeleteView:
                pass

            class TemplateView:
                pass

            class View:
                pass
    except Exception:
        class CreateView:
            pass

        class UpdateView:
            pass

        class DetailView:
            pass

        class ListView:
            pass

        class DeleteView:
            pass

        class TemplateView:
            pass

        class View:
            pass
except Exception:
    class CreateView:
        pass

    class UpdateView:
        pass

    class DetailView:
        pass

    class ListView:
        pass

    class DeleteView:
        pass

    class TemplateView:
        pass

    class View:
        pass
try:
    from django.utils import timezone  # type: ignore[import]
except Exception:
    class _TimezoneStub:
        @staticmethod
        def now():
            from datetime import datetime
            return datetime.now()
    timezone = _TimezoneStub()
import csv
try:
    from django.http import HttpResponse, JsonResponse  # type: ignore[import]
except Exception:
    # Lightweight stubs for environments without Django available (e.g., static analysis)
    class HttpResponse:
        def __init__(self, content=b"", *args, **kwargs):
            self.content = content

    class JsonResponse(HttpResponse):
        def __init__(self, data, *args, **kwargs):
            import json as _json
            body = _json.dumps(data).encode("utf-8")
            super().__init__(body, *args, **kwargs)
try:
    from django.core.mail import send_mail  # type: ignore[import]
except Exception:
    def send_mail(subject, message, from_email, recipient_list, fail_silently=False, auth_user=None, auth_password=None, connection=None, html_message=None):
        return 0
try:
    from django.conf import settings  # type: ignore[import]
except Exception:
    class _SettingsStub:
        pass
    settings = _SettingsStub()
try:
    from django.db import transaction  # type: ignore[import]
except Exception:
    # Lightweight stub for environments without Django (static analysis/testing)
    class _TransactionStub:
        class atomic:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc, tb):
                return False

    transaction = _TransactionStub()

try:
    from django.db.models import Count, Q  # type: ignore[import]
except Exception:
    # Minimal stubs so static analysis doesn't fail when Django isn't installed
    def Count(*args, **kwargs):
        raise Exception('Django not available')

    class Q:
        def __init__(self, *args, **kwargs):
            pass
import logging, json
from datetime import datetime

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


class EventListView(ListView):
    """
    View to list upcoming events.
    """
    model = Event
    template_name = 'staff/event_list.html'
    context_object_name = 'events'

    def get_queryset(self):
        """
        Returns a queryset of events with dates greater than or equal to today.
        """
        return Event.objects.filter(start_time__date__gte=timezone.now().date()).order_by('start_time')
    
class EventDetailView(DetailView):
    model = Event
    template_name = 'staff/event_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
    
        assignments_qs = event.assignments.all().select_related('staff', 'role').order_by('duty_number')

        for assignment in assignments_qs:
            if assignment.role:
                qs = Staff.objects.filter(role=assignment.role, is_active=True)
                if assignment.staff_id:
                    qs = qs.exclude(id=assignment.staff_id)
                assignment.replacement_staff = qs
            else:
                assignment.replacement_staff = Staff.objects.none()

            # (Removed duplicate/incorrect block that referenced undefined
            # variables `role_name` and `staff_id`.)
        context['assignments'] = assignments_qs
        context['roles'] = Role.objects.all()
        return context
      
class RecruitmentCreateView(CreateView):
    """
    View to create a new recruitment.
    """
    model = Recruitment
    form_class = RecruitmentForm
    template_name = 'staff/recruitment_form.html'
    success_url = reverse_lazy('staff:recruitment_list')

class RecruitmentListView(ListView):
    """
    View to list recruitments.
    """
    model = Recruitment
    template_name = 'staff/recruitment_list.html'


class RecruitmentDetailView(DetailView):
    """
    View to display recruitment details.
    """
    model = Recruitment
    pk_url_kwarg = 'recruitment_id'
    template_name = 'staff/recruitment_detail.html'

@method_decorator(staff_member_required, name='dispatch')
class RecruitmentApplicantsView(DetailView):
    model = Recruitment
    pk_url_kwarg = 'recruitment_id'
    template_name = 'staff/recruitment_applicants.html'
    context_object_name = 'recruitment'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # reference kwargs to avoid linter warnings about unused parameter
        _ = kwargs
        context['applicants'] = self.object.applicant_set.all()
        return context
    
class CloseRecruitmentView(UpdateView):
    model = Recruitment
    pk_url_kwarg = 'recruitment_id'
    fields = ['status']
    template_name = 'staff/close_recruitment.html'
    success_url = reverse_lazy('staff:recruitment_list')

    def get_object(self, queryset=None):
        recruitment_id = self.kwargs['recruitment_id']
        return get_object_or_404(Recruitment, id=recruitment_id)

    def form_valid(self, form):
        form.instance.status = 'Closed'
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # reference kwargs to avoid linter warnings about unused parameter
        _ = kwargs
        applicants = self.object.applicant_set.all()
        print(applicants)
        context['applicants'] = applicants
        return context
    
class RecruitmentDeleteView(DeleteView):
    model = Recruitment
    pk_url_kwarg = 'recruitment_id'
    template_name = 'staff/recruitment_confirm_delete.html'
    success_url = reverse_lazy('staff:recruitment_list')

class RecruitmentUpdateView(UpdateView):
    model = Recruitment
    form_class = RecruitmentForm
    pk_url_kwarg = 'recruitment_id'
    template_name = 'staff/recruitment_form.html'
    success_url = reverse_lazy('staff:recruitment_list')

class EditRecruitmentView(UpdateView):
    model = Recruitment
    form_class = RecruitmentForm
    template_name = 'staff/recruitment_form.html'
    success_url = reverse_lazy('recruitment_list')

@login_required
def staff_home(request):
    return render(request, 'staff/staff_home.html')

@method_decorator(staff_member_required, name='dispatch')
class StaffListView(ListView):
    """
    View to list staff members.
    """
    model = Staff
    template_name = 'staff/staff_list.html'

class StaffCreateView(CreateView):
    """
    View to create a new staff member.
    """
    model = Staff
    form_class = StaffForm
    template_name = 'staff/staff_form.html'
    success_url = reverse_lazy('staff_list')

class StaffUpdateView(UpdateView):
    """
    View to update a staff member.
    """
    model = Staff
    form_class = StaffForm
    template_name = 'staff/staff_form.html'
    success_url = reverse_lazy('staff_list')

class StaffDeleteView(DeleteView):
    """
    View to delete a staff member.
    """
    model = Staff
    template_name = 'staff/staff_confirm_delete.html'
    success_url = reverse_lazy('staff_list')

class StaffProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Staff
    form_class = StaffProfileForm
    template_name = 'staff/staff_profile_form.html'
    success_url = reverse_lazy('staff:staff_profile')

    def get_object(self, queryset=None):
        staff, created = Staff.objects.get_or_create(user=self.request.user, defaults={'name': self.request.user.get_full_name() or self.request.user.username})
        return staff 

class EventCreateView(CreateView):
    model = Event
    form_class = EventForm
    template_name = 'staff/event_form.html'
    success_url = reverse_lazy('staff:event_list')

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            event = self.object

            role_counts = form.get_role_counts()
            if not role_counts:
                messages.warning(self.request, f'Created "{event.title}" with 0 duty slots. Add roles manually.')
                return response

            role_ids = list(role_counts.keys())
            roles = {str(r.id): r for r in Role.objects.filter(id__in=role_ids)}  # 1 query instead of N

            assignments = []
            duty_num = 1
            for role_id, count in role_counts.items():
                role_obj = roles.get(str(role_id))
                if not role_obj:
                    continue  # skip if role was deleted
                for _ in range(count):
                    assignments.append(
                        Assignment(
                            event=event,
                            duty_number=duty_num,
                            role=role_obj,
                            status='assigned',
                            staff=None
                        )
                    )
                    duty_num += 1

            Assignment.objects.bulk_create(assignments)
            messages.success(
                self.request,
                f'Created "{event.title}" with {len(assignments)} duty slots. Ready for auto-fill.'
            )
        return response

class EventUpdateView(UpdateView):
    """
    View to update an event.
    """
    model = Event
    form_class = EventForm
    template_name = 'staff/event_form.html'
    success_url = reverse_lazy('staff:event_list')

class ApplicantCreateView(CreateView):
    model = Applicant
    form_class = ApplicantForm
    template_name = 'staff/applicant_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.recruitment = get_object_or_404(Recruitment, pk=kwargs['recruitment_id'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.recruitment = self.recruitment
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recruitment'] = self.recruitment
        return context
    
    def get_success_url(self):
        return reverse_lazy('success')
    
class SuccessView(TemplateView):
    template_name = 'staff/success.html'

class ExportApplicantsCSVView(View):
    def get(self, request, recruitment_id):
        applicants = Applicant.objects.filter(recruitment_id=recruitment_id)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="applicants_{recruitment_id}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Name', 'Email', 'Phone', 'Resume', 'Status']) # header
        for applicant in applicants:
            writer.writerow([applicant.name, applicant.email, applicant.phone, applicant.resume.url if applicant.resume else '', applicant.status])
        return response
    
class SendEmailToApplicantsView(View):
    def get(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        applicants = recruitment.applicant_set.all()
        emails_sent = 0
        errors = []
        for applicant in applicants:
            try:
                send_mail(
                    'Interview Invitation',
                    f'Dear {applicant.name},\n\nYou have been selected for an interview for the position of {recruitment.position}. Please reply to this email to schedule your interview.\n\nBest regards,\nCatering Company',
                    settings.DEFAULT_FROM_EMAIL,
                    [applicant.email],
                    fail_silently=False,
                )
                logger.info(f"Email sent to {applicant.email} for recruitment {recruitment.position}")
                emails_sent += 1
            except Exception as e:
                logger.error(f"Error sending email to {applicant.email} for recruitment {recruitment.position}: {str(e)}")
                errors.append(f"Error sending email to {applicant.email}")
        return render(request,'staff/emails_sent.html', {'recruitment': recruitment, 'emails_sent': emails_sent,  'errors': errors})
    
class ScheduleInterviewsView(View):
    def get(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        return render(request, 'staff/schedule_interviews.html', {'recruitment': recruitment, 'errors': []})
    
    def post(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        applicant_ids = request.POST.getlist('applicant_ids')
        if not applicant_ids:
            errors = ["Please select at least one applicant to schedule an interview."]
            return render(request, 'staff/schedule_interviews.html', {'recruitment': recruitment, 'errors': errors})
        
        applicants = Applicant.objects.filter(id__in=applicant_ids, recruitment_id=recruitment_id) 
        errors = []
        scheduled_applicants = []
        for applicant in applicants:
            interview_time = request.POST.get(f'interview_time_{applicant.id}')
            if not interview_time:
                errors.append(f"Please provide an interview time for {applicant.name}.")
                continue
            try:   
                applicant.interview_time = timezone.make_aware(
                    datetime.strptime(interview_time, '%Y-%m-%dT%H:%M'), timezone.get_current_timezone())
                applicant.save()
                scheduled_applicants.append(applicant.name)
            except ValueError:
                errors.append(f"Invalid interview time format for {applicant.name}. Expected format: YYYY-MM-DDTHH:MM")
        if errors:
            return render(request, 'staff/schedule_interviews.html', {'recruitment': recruitment, 'errors': errors})
        return render(request, 'staff/interviews_scheduled.html', {'recruitment': recruitment,  'scheduled_applicants': scheduled_applicants})
    
class ManageInterviewSlotsView(View):
    def get(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        applicants = recruitment.applicant_set.all()
        # Here you would implement the logic to manage interview slots for the applicants
        # This is just a placeholder for demonstration purposes
        for applicant in applicants:
            print(f"Managing interview slots for {applicant.name} for recruitment {recruitment.position}")
        return HttpResponse("Interview slots managed for applicants.")
    
    def post(self, request, recruitment_id):
        # Here you would implement the logic to handle interview slot management form submission
        # This is just a placeholder for demonstration purposes
        return HttpResponse("Interview slots updated for applicants.")

class RolePlayListView(ListView):
    model = RolePlay
    template_name = 'staff/role_play_list.html'

class RolePlayCreateView(CreateView):
    model = RolePlay
    form_class = RolePlayForm
    template_name = 'staff/role_play_form.html'
    success_url = reverse_lazy('staff:role_play_list')

class RolePlayUpdateView(UpdateView):
    model = RolePlay
    form_class = RolePlayForm
    template_name = 'staff/role_play_form.html'
    success_url = reverse_lazy('staff:role_play_list')

class RolePlayDeleteView(DeleteView):
    model = RolePlay
    template_name = 'staff/role_play_confirm_delete.html'
    success_url = reverse_lazy('staff:role_play_list')

class RolePlayDetailView(DetailView):
    model = RolePlay
    template_name = 'staff/role_play_detail.html'
    context_object_name = 'roleplay'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['responses'] = self.object.responses.all().order_by('-submitted_at')
        context['form'] = RolePlayResponseForm()
        return context
    
class StartScenarioView(View):
    def post(self, request, pk):
        roleplay = get_object_or_404(RolePlay, pk=pk)
        
        try:
            staff = request.user.staff
        except Staff.DoesNotExist:
            messages.error(request, "Your user account isn't linked to a Staff profile. Ask admin to create one.")
            return redirect('staff:role_play_detail', pk=pk)
        
        form = RolePlayResponseForm(request.POST)
        if form.is_valid():
            response = form.save(commit=False)
            response.staff = staff
            response.roleplay = roleplay
            response.save()
            messages.success(request, "Response submitted!")
        else:
            messages.error(request, "Please enter what you do.")
            
        return redirect('staff:role_play_detail', pk=pk)

    def get(self, request, pk):
        return redirect('staff:role_play_detail', pk=pk)   

@method_decorator(staff_member_required, name='dispatch')    
class StaffDashboardView(ListView):
    model = Staff
    template_name = 'staff/staff_dashboard.html'
    context_object_name = 'staff_list'

    def get_queryset(self):
        return Staff.objects.annotate(
            events_worked=Count('assignments', distinct=True),
            incident_count=Count('incidents', filter=Q(incidents__is_resolved=False)),
            no_shows=Count('incidents', filter=Q(incidents__issue_type='No Show'))
        ).order_by('-reliability_score')
    
@method_decorator(staff_member_required, name='dispatch')
class IncidentCreateView(CreateView):
    model = Incident
    form_class = IncidentForm
    template_name = 'staff/incident_form.html'
    success_url = reverse_lazy('staff:staff_dashboard')

    def get_initial(self):
        initial = super().get_initial()
        staff_id = self.request.GET.get('staff')
        if staff_id:
            initial['staff'] = staff_id
        return initial
    
@require_POST
@csrf_exempt
def create_assignment(request, pk):
    try:
        data = json.loads(request.body)
        staff_id = data.get('staff_id')
        role_id = data.get('role_id')
        
        event = get_object_or_404(Event, pk=pk)
        
        if Assignment.objects.filter(event=event, staff_id=staff_id, status='assigned').exists():
            return JsonResponse({'success': False, 'error': 'Staff already assigned'}, status=400)

        role_obj = get_object_or_404(Role, id=role_id)  # get Role object
        assignment = Assignment.objects.create(
            event=event,
            staff_id=staff_id,
            duty_number=event.assignments.filter(status='assigned').count() + 1,
            role=role_obj,  # ✅ pass Role object
            status='assigned'
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_POST
@csrf_exempt
def update_assignment_role(request, assignment_id):
    try:
        data = json.loads(request.body)
        role_id = data.get('role')
        assignment = get_object_or_404(Assignment, id=assignment_id, status='assigned')

        if role_id:
            role_obj = get_object_or_404(Role, id=role_id)
            assignment.role = role_obj  # assign object, not _id
            assignment.save(update_fields=['role'])
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_POST
@login_required
def reassign_assignment(request, assignment_id):
    try:
        data = json.loads(request.body)
        new_staff_id = data.get('new_staff_id')
        reason = data.get('reason', '').strip()
        
        old_assignment = get_object_or_404(Assignment, id=assignment_id, status='assigned')

        # Drop old assignment and store reason
        old_assignment.status = 'dropped'
        old_assignment.reassignment_reason = reason
        old_assignment.save(update_fields=['status', 'reassignment_reason'])

        # Create new assignment for same duty
        new_assignment = Assignment.objects.create(
            event=old_assignment.event,
            staff_id=new_staff_id,
            duty_number=old_assignment.duty_number,
            role=old_assignment.role,  # <-- Fixed: was role_id=old_assignment.role
            status='assigned'
        )

        return JsonResponse({
            'success': True,
            'new_staff': new_assignment.staff.name,
            'duty': new_assignment.duty_number
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)  
    
@login_required
@require_POST
def replace_staff(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    new_staff_id = request.POST.get('new_staff_id')
    
    if not new_staff_id:
        return JsonResponse({'success': False, 'error': 'No staff selected'}, status=400)
    
    new_staff = get_object_or_404(Staff, id=new_staff_id)
    old_staff_name = assignment.staff.name if assignment.staff else 'Empty'
    
    assignment.staff = new_staff
    assignment.status = 'assigned'
    assignment.reassigned_at = timezone.now()
    assignment.reassigned_by = request.user
    assignment.reassignment_reason = request.POST.get('reason', 'Replaced via dashboard')
    assignment.save()
    
    return JsonResponse({
        'success': True, 
        'new_staff': new_staff.name,
        'new_score': new_staff.reliability_score
    })



def is_staff_or_bamboo(user):
    return user.is_staff or user.username == 'bamboo3'

@login_required
@staff_member_required
def event_status(request):
    """
    Admin dashboard showing event staffing risks and replacement options
    """
    print(">>> NEW EVENT_STATUS IS RUNNING")
    
    today = timezone.now().date()
    
    # ===== AUTO-FILL ALL UPCOMING EVENTS ON LOAD =====
    upcoming_for_fill = Event.objects.filter(start_time__date__gte=today)
    for event in upcoming_for_fill:
        empty_assignments = event.assignments.filter(Q(staff__isnull=True) | Q(status='dropped')).select_related('role')
        assigned_staff_ids = list(event.assignments.filter(status='assigned').values_list('staff_id', flat=True))
        
        for assign in empty_assignments:
            if not assign.role: 
                continue
            candidate = Staff.objects.filter(
                role=assign.role,
                is_active=True,
                reliability_score__gte=75
            ).exclude(id__in=assigned_staff_ids).order_by('-reliability_score').first()

            if candidate:
                assign.staff = candidate
                assign.status = 'assigned'
                assign.save()
                assigned_staff_ids.append(candidate.id) # update list so we don't double-book
    # ===== END AUTO-FILL =====
    
    # Dashboard card stats
    stats = {
        'total_events': Event.objects.count(),
        'upcoming': Event.objects.filter(start_time__date__gte=today).count(),
        'past': Event.objects.filter(start_time__date__lt=today).count(),
        'this_month': Event.objects.filter(start_time__year=today.year, start_time__month=today.month).count(),
    }
    
    print(f">>> Total events from DB: {stats['total_events']}")
    
    events_data = []
    
    events = Event.objects.filter(start_time__date__gte=today).prefetch_related(
        'assignments__staff', 
        'assignments__role'
    ).order_by('start_time')
    
    for event in events:
        duties_data = []
        at_risk = 0
        empty = 0
        
        assignments = event.assignments.all().select_related('staff', 'role')
        assigned_staff_ids = list(assignments.filter(status='assigned').values_list('staff_id', flat=True))
        
        for idx, a in enumerate(assignments.order_by('duty_number'), start=1):
            staff_obj = a.staff
            score = staff_obj.reliability_score if staff_obj else 0
            
            # Determine status and counts
            if not staff_obj:
                status = 'critical'
                empty += 1
                at_risk += 1
            elif score < 70:
                status = 'critical'
                at_risk += 1
            elif score < 85:
                status = 'warning'
                at_risk += 1
            else:
                status = 'ok'
            
            # Get replacement candidates
            candidates = []
            candidates_qs = Staff.objects.filter(is_active=True).exclude(
                id__in=assigned_staff_ids
            ).order_by('-reliability_score')[:5]
            
            for c in candidates_qs:
                candidates.append({'id': c.id, 'name': c.name, 'score': c.reliability_score})

            duties_data.append({
                'index': idx,
                'assignment_id': a.id,
                'staff': staff_obj.name if staff_obj else None,
                'role': a.role.name if a.role else 'No Role',
                'score': score,
                'status': status,
                'conflicts': [],  # placeholder for later
                'candidates': candidates
            })
        
        events_data.append({
            'id': event.id,
            'title': event.title,
            'date': event.start_time,
            'location': event.location,
            'duties': duties_data,
            'total_duties': len(duties_data),
            'at_risk': at_risk,
            'empty': empty,
            'ok': len(duties_data) - at_risk
        })
    
    context = {
        'stats': stats,
        'events': events_data
    }
    return render(request, 'staff/event_status.html', context) # <- Note: path changed