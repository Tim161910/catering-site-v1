from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views import View
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Q, ProtectedError
import csv
import logging
import json
from datetime import datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.forms import modelformset_factory

logger = logging.getLogger(__name__)

from .models import Recruitment, Applicant, RolePlay, Incident, Event, Staff, Assignment, Role, RolePlayResponse, InterviewSlot
from .forms import RecruitmentForm, ApplicantForm, IncidentForm, EventForm, StaffForm, RolePlayForm, RolePlayResponseForm, InterviewSlotForm

@method_decorator(staff_member_required, name='dispatch')
class RecruitmentApplicantsView(ListView):
    model = Applicant
    template_name = 'staff/recruitment_applicants.html'
    context_object_name = 'applicants'

    def get_queryset(self):
        return Applicant.objects.filter(recruitment_id=self.kwargs['recruitment_id'])

@method_decorator(staff_member_required, name='dispatch')
class RecruitmentCreateView(CreateView):
    model = Recruitment
    form_class = RecruitmentForm
    template_name = 'staff/recruitment_form.html'
    success_url = reverse_lazy('staff:recruitment_list')

@method_decorator(staff_member_required, name='dispatch')
class EditRecruitmentView(UpdateView): # you have this in urls
    model = Recruitment
    form_class = RecruitmentForm
    template_name = 'staff/recruitment_form.html'
    pk_url_kwarg = 'recruitment_id'
    success_url = reverse_lazy('staff:recruitment_list')
    
@method_decorator(staff_member_required, name='dispatch')    
class RecruitmentListView(LoginRequiredMixin, ListView):
    model = Recruitment
    template_name = 'staff/recruitment_list.html'
    context_object_name = 'recruitments'
    ordering = ['-created_at']

@method_decorator(staff_member_required, name='dispatch')
class RecruitmentDetailView(LoginRequiredMixin, DetailView):
    model = Recruitment
    template_name = 'staff/recruitment_detail.html'
    context_object_name = 'recruitment'

@method_decorator(staff_member_required, name='dispatch')
class RecruitmentUpdateView(UpdateView):
    model = Recruitment
    form_class = RecruitmentForm
    template_name = 'staff/recruitment_form.html'
    pk_url_kwarg = 'recruitment_id'  # add this
    success_url = reverse_lazy('staff:recruitment_list')

@method_decorator(staff_member_required, name='dispatch')
class RecruitmentDeleteView(DeleteView):
    model = Recruitment
    success_url = reverse_lazy('staff:recruitment_list')
    template_name = 'staff/recruitment_confirm_delete.html'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_closed = True  # this is the only change
        self.object.save()
        messages.success(request, "Recruitment closed.")
        return HttpResponseRedirect(self.success_url)

@method_decorator(staff_member_required, name='dispatch')
class CloseRecruitmentView(View):
    def post(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        recruitment.is_closed = True
        recruitment.save()
        messages.success(request, f"Recruitment for '{recruitment.position}' closed.")
        return redirect('staff:recruitment_detail', pk=recruitment_id)
    
    def get(self, request, recruitment_id):
        # In case someone clicks it as a link
        return self.post(request, recruitment_id)


@method_decorator(staff_member_required, name='dispatch')
class ApplicantListView(ListView):
    model = Applicant
    template_name = 'staff/applicant_list.html'

    def get_queryset(self):
        recruitment_id = self.kwargs.get('recruitment_id')
        return Applicant.objects.filter(recruitment_id=recruitment_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recruitment'] = Recruitment.objects.get(id=self.kwargs['recruitment_id'])
        return context

@method_decorator(staff_member_required, name='dispatch')
class ApplicantDetailView(DetailView):
    model = Applicant
    template_name = 'staff/applicant_detail.html'

@method_decorator(staff_member_required, name='dispatch')
class ApplicantCreateView(CreateView):
    model = Applicant
    form_class = ApplicantForm
    template_name = 'staff/applicant_form.html'

    def get_recruitment(self):
        return get_object_or_404(Recruitment, pk=self.kwargs['recruitment_id'])
    
    def form_valid(self, form):
        form.instance.recruitment = self.get_recruitment()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recruitment'] = self.get_recruitment()
        return context
    
    def get_success_url(self):
        return reverse_lazy('staff:recruitment_applicants', kwargs={'pk': self.kwargs['recruitment_id']})
    

@method_decorator(staff_member_required, name='dispatch')
class ApplicantUpdateView(UpdateView):
    model = Applicant
    form_class = ApplicantForm
    template_name = 'staff/applicant_form.html'
   
    def get_success_url(self):
        messages.success(self.request, f'{self.object.name} updated successfully.')
        # Redirect back to the recruitment detail instead of global list
        return reverse_lazy('staff:recruitment_detail', kwargs={'pk' : self.object.recruitment_id})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recruitment'] = self.object.recruitment
        return context

@method_decorator(staff_member_required, name='dispatch')
class ApplicantDeleteView(DeleteView):
    model = Applicant
    template_name = 'staff/applicant_confirm_delete.html'

    def get_success_url(self):
        recruitment_id = self.object.recruitment_id
        messages.success(self.request, f'{self.object.name} deleted successfully.')
        return reverse_lazy('staff:recruitment_detail', kwargs={'pk': recruitment_id})
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.success(request, f'{self.object.name} deleted.')
        return super().delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recruitment'] = self.object.recruitment
        return context      

@method_decorator(staff_member_required, name='dispatch')
class ExportApplicantsCSVView(View):
    def get(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        applicants = recruitment.applicant_set.all()

        # Apply filters from query params
        status = request.GET.get('status')
        if status:
            applicants = applicants.filter(status=status)
        
        # Add more filters as needed
        name_search = request.GET.get('name')
        if name_search:
            applicants = applicants.filter(name__icontains=name_search)

        safe_position = "".join(c if c.isalnum() else "_" for c in recruitment.position)
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{safe_position}_{recruitment_id}_applicants.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Name', 'Email', 'Phone', 'Resume URL', 'Cover Letter URL', 'Status', 'Applied At'])  
        for applicant in applicants:
            writer.writerow([
                applicant.name,
                applicant.email,
                applicant.phone,
                request.build_absolute_uri(applicant.resume.url) if applicant.resume else '',
                request.build_absolute_uri(applicant.cover_letter.url) if applicant.cover_letter else '',
                applicant.get_status_display() if hasattr(applicant, 'get_status_display') else applicant.status,
                applicant.created_at.strftime('%Y-%m-%d %H:%M') if applicant.created_at else '',
            ])
        return response

@method_decorator(staff_member_required, name='dispatch')
class SendEmailToApplicantsView(View):
    def get(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        applicants = recruitment.applicant_set.all()
        return render(request, 'staff/emails_sent.html', {
            'recruitment': recruitment,
            'applicants': applicants,
            'total': applicants.count()
        })
    
    def post(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        applicants = recruitment.applicant_set.all()

        applicant_ids = request.POST.getlist('applicant_ids')
        if applicant_ids:
            applicants = applicants.filter(id__in=applicant_ids)


        emails_sent = 0
        errors = []
        for applicant in applicants:
            if not applicant.email:
                errors.append(f'{applicant.name} has no email address')
                continue
            try:
                send_mail(
                    subject=f'Interview Invitation - {recruitment.position}',
                    message=f'Dear {applicant.name},\n\nYou are invited for an interview for the position of {recruitment.position} you applied for. Please reply to this email to schedule your interview.\n\nBest regards,\nCatering Team',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[applicant.email],
                    fail_silently=False
                )
                logger.info(f'Email sent to {applicant.email} for recruitment {recruitment_id}')
                emails_sent += 1
            except Exception as e:
                logger.error(f'Error sending email to {applicant.name} for recruitment {recruitment.position}: {str(e)}')
                errors.append(f'Error sending email to {applicant.name}: {str(e)}')

        if errors:
            for err in errors:
                messages.error(request, err)
        if emails_sent:
            messages.success(request, f'Successfully sent {emails_sent} emails.')
        
        return redirect('staff:recruitment_detail', pk=recruitment_id)

@method_decorator(staff_member_required, name='dispatch')    
class ScheduleInterviewsView(View):
    def get(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        applicants = recruitment.applicant_set.all()
        return render(request, 'staff/schedule_interviews.html', {'recruitment': recruitment, 'applicants': applicants, 'errors':[]})
    
    def post(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        all_applicants = recruitment.applicant_set.all()
        applicant_ids = request.POST.getlist('applicant_ids')
        if not applicant_ids:
            errors = ["Please select at least one applicant to schedule an interview."]
            return render(request, 'staff/schedule_interviews.html', {'recruitment': recruitment, 'applicants': all_applicants, 'errors': errors})
        
        applicants = Applicant.objects.filter(id__in=applicant_ids, recruitment_id=recruitment_id)
        errors = []
        scheduled_applicants = []
        for applicant in applicants:
            interview_time_str = request.POST.get(f'interview_time_{applicant.id}')
            if not interview_time_str:
                errors.append(f"Please provide an interview time for {applicant.name}.")
                continue
            try:
                naive_dt = datetime.strptime(interview_time_str, '%Y-%m-%dT%H:%M')
                aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())

                if aware_dt < timezone.now():
                    errors.append(f"Interview time for {applicant.name} cannot be in the past")
                    continue

                applicant.interview_time = aware_dt
                applicant.save()
                scheduled_applicants.append(applicant.name)

            except ValueError:
                errors.append(f"Invalid interview time format for {applicant.name}. Expected format: YYYY-MM-DDTHH:MM")

        if errors:
            return render(request, 'staff/schedule_interviews.html', {'recruitment': recruitment, 'applicants': all_applicants, 'errors': errors})
        messages.success(request, f"Scheduled {len(scheduled_applicants)} interviews.")
        return render(request, 'staff/schedule_interviews.html', {'recruitment': recruitment, 'scheduled_applicants': scheduled_applicants})

@method_decorator(staff_member_required, name='dispatch')
class ManageInterviewSlotsView(View):
    def get(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        applicants = recruitment.applicant_set.all()

        InterviewSlotFormSet = modelformset_factory(
            InterviewSlot, 
            form=InterviewSlotForm, 
            extra=0  # we don't add blank extras, we use initial
        )

        # Pre-fill formset with one form per applicant
        formset = InterviewSlotFormSet(
            queryset=InterviewSlot.objects.filter(applicant__in=applicants),
            initial=[{'applicant': a} for a in applicants]
        )
        return render(request, 'recruitment/manage_slots.html', {'recruitment': recruitment, 'formset': formset})

    def post(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        applicants = recruitment.applicant_set.all()

        InterviewSlotFormSet = modelformset_factory(
            InterviewSlot, 
            form=InterviewSlotForm, 
            extra=0
        )

        formset = InterviewSlotFormSet(request.POST)  # <- fixed this
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.save() # make sure applicant is set
            messages.success(request, "Interview slots updated.")
            return redirect('recruitment:detail', pk=recruitment_id)
        
        return render(request, 'staff/recruitment_manage_slots.html', {'recruitment': recruitment, 'formset': formset})

class StaffListView(LoginRequiredMixin, ListView):
    model = Staff
    template_name = 'staff/staff_list.html'
    context_object_name = 'staff'

class StaffCreateView(LoginRequiredMixin, CreateView):
    model = Staff
    form_class = StaffForm  # change fields to match your Staff model
    template_name = 'staff/staff_form.html'
    success_url = reverse_lazy('staff:staff_list')

class StaffDetailView(LoginRequiredMixin, DetailView):
    model = Staff
    template_name = 'staff/staff_detail.html'
    context_object_name = 'staff'

class StaffUpdateView(LoginRequiredMixin, UpdateView):
    model = Staff
    form_class = StaffForm  # change fields to match your Staff model
    template_name = 'staff/staff_form.html'
    success_url = reverse_lazy('staff:staff_list')

class StaffDeleteView(LoginRequiredMixin, DeleteView):
    model = Staff
    template_name = 'staff/staff_confirm_delete.html'
    success_url = reverse_lazy('staff:staff_list')

class StaffProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Staff
    form_class = StaffForm
    template_name = 'staff/staff_profile_form.html'

    def get_object(self, queryset=None):
        staff, created = Staff.objects.get_or_create(user=self.request.user)
        defaults = {'name': self.request.user.get_full_name() or self.request.user.username, 'email': self.request.user.email}
        return staff

class SuccessView(TemplateView):
    template_name = 'staff/success.html'

@method_decorator(staff_member_required, name='dispatch')
class StartScenarioView(View):
    def post(self, request, pk):
        role_play = get_object_or_404(RolePlay, pk=pk)

        try:
            staff = request.user.staff
        except Staff.DoesNotExist:
            messages.error(request, "Your user account is not linked to a staff profile. Please contact the administrator.")
            return redirect('staff:role_play_detail', pk=pk)
        
        form = RolePlayResponseForm(request.POST)
        if form.is_valid():
            if RolePlayResponse.objects.filter(role_play=role_play, staff=staff).exists():
                messages.warning(request, "You already submitted a response.")
                return redirect('staff:role_play_detail', pk=pk)
            response = form.save(commit=False)
            response.role_play = role_play
            response.staff = staff
            response.save()
            messages.success(request, "Your response has been submitted successfully.")
            return redirect('staff:role_play_detail', pk=pk)
        else:
            messages.error(request, "Please correct the errors below.")
            return redirect('staff:role_play_detail', pk=pk)
        
    def get(self, request, pk):
        return redirect('staff:role_play_detail', pk=pk)
    
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

class RolePlayListView(ListView):
    model = RolePlay
    template_name = 'staff/role_play_list.html'
    ordering = ['-created_at']

@method_decorator(staff_member_required, name='dispatch')
class RolePlayDetailView(DetailView):
    model = RolePlay
    template_name = 'staff/role_play_detail.html'
    context_object_name = 'role_play'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['responses'] = self.object.responses.all().order_by('-submitted_at')
        context['response_form'] = RolePlayResponseForm()
        return context

@method_decorator(staff_member_required, name='dispatch')
class RolePlayDeleteView(DeleteView):
    model = RolePlay
    template_name = 'staff/role_play_confirm_delete.html'
    success_url = reverse_lazy('staff:role_play_list')
    
class EventListView(ListView):
    model = Event
    template_name = 'staff/event_list.html'
    context_object_name = 'events'

    def get_queryset(self):
        """
        Returns a queryset of events with dates greater than or equal to today, ordered by start_time.
        """
        today = timezone.now().date()
        return Event.objects.filter(start_time__date__gte=today).order_by('start_time')

@method_decorator(staff_member_required, name='dispatch')
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
            roles = {str(role.id): role for role in Role.objects.filter(id__in=role_ids)} # 1 query to fetch all roles at once

            assignments = []
            duty_num = 1
            for role_id, count in role_counts.items():
                role_obj = roles.get(str(role_id))
                if not role_obj:
                    logger.warning(f'Role with ID {role_id} not found for event {event.id}. Skipping.')
                    continue
                for _ in range(count):
                    assignments.append(
                        Assignment(
                            event=event,
                            duty_number=duty_num,
                            role=role_obj,
                            status='assigned',
                            staff=None  # Initially unassigned
                        )
                    )
                    duty_num += 1
            # Additional logic can be added here if needed

            Assignment.objects.bulk_create(assignments)
            messages.success(self.request, f'Created "{event.title}" with {len(assignments)} duty slots. Ready for auto-fill')
            return response

@method_decorator(staff_member_required, name='dispatch')
class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = 'staff/event_form.html'  # re-use the same form
    success_url = reverse_lazy('staff:event_list')

class EventDetailView(DetailView):
    model = Event
    template_name = 'staff/event_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object

        assignments_qs = event.assignments.select_related('staff', 'role').order_by('duty_number')
        for assignment in assignments_qs:
            if assignment.role:
                # Get all active staff with this role, exclude currently assigned staff
                qs = Staff.objects.filter(role=assignment.role, is_active=True)
                if assignment.staff_id:
                    qs = qs.exclude(id=assignment.staff_id)
                assignment.replacement_staff = qs
            else:
                # no role, so no replacement
                assignment.replacement_staff = Staff.objects.none()
        context['assignments'] = assignments_qs
        context['roles'] = Role.objects.all()
        return context
    
class EventDeleteView(DeleteView):
    model = Event
    template_name = 'staff/event_confirm_delete.html'
    success_url = reverse_lazy('staff:event_list')

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, "Can't delete event. It has assignments linked to it.")
            return redirect('staff:event_list')

@method_decorator(staff_member_required, name='dispatch')
class StaffDashboardView(ListView):
    model = Staff
    template_name = 'staff/staff_dashboard.html'
    context_object_name = 'staff_list'

    def get_queryset(self):
        return Staff.objects.annotate(
            events_worked=Count('assignments__event', distinct=True),
            incident_count=Count('incidents'),
            no_show=Count('incidents', filter=Q(incidents__incident_type='no_show')),
        ).order_by('-reliability_score')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        context['upcoming_events'] = Event.objects.filter(start_time__date__gte=today).order_by('start_time')
        return context
        

@method_decorator(staff_member_required, name='dispatch')
class IncidentCreateView(CreateView):
    model = Incident
    form_class = IncidentForm
    template_name = 'staff/incident_form.html'
    success_url = reverse_lazy('staff:staff_dashboard')

    def get_initial(self):
        initial = super().get_initial()
        staff_id = self.request.GET.get('staff_id')
        if staff_id:
            initial['staff'] = get_object_or_404(Staff, pk=staff_id)
        return initial
    
@require_POST
@csrf_exempt
@login_required
def create_assignment(request, pk):
    """
    AJAX endpoint to create an assignment for a specific event.
    """
    try:
        data = json.loads(request.body)
        staff_id = data.get('staff_id')
        event = get_object_or_404(Event, pk=pk)
        role_id = data.get('role_id')
        duty_number = data.get('duty_number')

        if not staff_id or not role_id or not duty_number:
            return JsonResponse({'success': False, 'error': 'Staff, Role and Duty Number are required.'}, status=400)

        if Assignment.objects.filter(event=event, staff_id=staff_id, status='assigned', duty_number=duty_number).exists():
            return JsonResponse({'success': False, 'error': 'Staff already assigned to this duty number.'}, status=400)

        role_obj = get_object_or_404(Role, id=role_id) # get Role object based on role_id
        assignment = Assignment.objects.create(
            event=event,
            staff_id=staff_id,
            duty_number=duty_number,
            role=role_obj, # pass Role object
            status='assigned'
        )

        return JsonResponse({
            'success': True,
            'assignment_id': assignment.id,
            'role_name': role_obj.name,
            'duty_number': assignment.duty_number
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
        
@require_POST
@login_required
@csrf_exempt
def reassign_assignment(request, assignment_id):
    try:
        data = json.loads(request.body)
        new_staff_id = data.get('new_staff_id')
        reason = data.get('reason', '').strip()

        old_assignment = get_object_or_404(Assignment, id=assignment_id, status='assigned')

        if old_assignment.event.assignments.filter(staff_id=new_staff_id, status='assigned').exists():
            return JsonResponse({'success': False, 'error': 'Staff already assigned to this event'}, status=400)

        # Drop old assignment and reason
        old_assignment.status = 'dropped'
        old_assignment.reassignment_reason = reason
        old_assignment.save(update_fields=['status', 'reassignment_reason'])

        # Create new assignment for same duty
        new_assignment = Assignment.objects.create(
            event=old_assignment.event,
            staff_id=new_staff_id,
            duty_number=old_assignment.duty_number,
            role=old_assignment.role, 
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
    if assignment.event.assignments.filter(staff=new_staff, status='assigned').exists():
        return JsonResponse({'success': False, 'error': 'Staff already assigned to this event'}, status=400)
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

@method_decorator(staff_member_required, name='dispatch')
class AssignmentListView(ListView):
    model = Assignment
    template_name = 'staff/assignment_list.html'
    context_object_name = 'assignments'

    def get_queryset(self):
        event_id = self.kwargs['event_id']
        return Assignment.objects.filter(event_id=event_id).select_related('staff', 'role')
    
@login_required
@staff_member_required
def event_status(request):
    """
    Admin dashboard showing event staffing risks and replacement options
    """
    print(">>>NEW EVENT_STATUS IS RUNNING")

    today = timezone.now().date()

    # Dashboard card stats - use start_time__date instead of date
    total_events = Event.objects.count()
    upcoming_events = Event.objects.filter(start_time__date__gte=today).count()
    past_events = Event.objects.filter(start_time__date__lt=today).count()
    this_month = Event.objects.filter(
        start_time__year=today.year,
        start_time__month=today.month
    ).count()


    print(f">>> Total events from DB: {total_events}")
    print(f">>> Upcoming: {upcoming_events}, Past: {past_events}, This Month: {this_month}")

    event_data = []

    # Get Upcoming events with assignments - order by start_time
    events = Event.objects.filter(start_time__date__gte=today).prefetch_related(
        'assignments__staff',
        'assignments__role'
    ).order_by('start_time')

    for event in events:
        duties = []
        at_risk = 0

        assignments = event.assignments.filter(status='assigned')
        assigned_staff_ids = assignments.values_list('staff_id', flat=True)

        for a in assignments:
            score = getattr(a.staff, 'reliability_score', 100)

            if score < 50:
                status = 'Critical'
                at_risk += 1
            elif score < 75:
                status = 'Warning'
                at_risk += 1
            else:
                status = 'OK'

            if a.role:
                replacements = Staff.objects.filter(
                    role=a.role, # FIXED: use the Role object, not .name
                    is_active= True,
                    reliability_score__gte=90
                ).exclude(
                    id__in=assigned_staff_ids
                ).order_by('-reliability_score')[:5]
            else:
                replacements = Staff.objects.none()  # No role, so no replacement

            duties.append({
                'assignment_id': a.id,
                'duty_number': a.duty_number,
                'staff': a.staff,
                'role': a.role.name if a.role else 'No Role',
                'score': score,
                'status': status,
                'replacements': replacements
            })

        if duties:
            event_data.append({
                'event': event,
                'duties': duties,
                'total_duties': len(duties),
                'at_risk': at_risk
            })

    recent_events = Event.objects.order_by('-start_time')[:5]

    context = {
        'total_events': total_events,
        'upcoming_events': upcoming_events,
        'this_month': this_month,
        'past_events': past_events,
        'recent_events': recent_events,
        'events': event_data
    }
    return render(request, 'staff/event_status.html', context)
    
@login_required
def auto_fill_roster(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    # Find empty or dropped assignments
    empty_assignments = event.assignments.filter(
        Q(staff__isnull=True) | Q(status='dropped')
    ).select_related('role')

    filled_count = 0
    skipped_roles = []

    for assign in empty_assignments:
        # Staff already assigned to this event
        assigned_staff_ids = event.assignments.filter(
            status='assigned'
        ).exclude(id=assign.id).values_list('staff_id', flat=True)

        # Best candidate: matching role, active, 75+ score, not already on event
        candidate = Staff.objects.filter(
            role=assign.role,
            is_active=True,
            reliability_score__gte=75
        ).exclude(id__in=assigned_staff_ids).order_by('-reliability_score').first()

        if candidate:
            assign.staff = candidate
            assign.status = 'assigned'
            assign.save()
            filled_count += 1
        else:
            if assign.role and assign.role.name not in skipped_roles:
                skipped_roles.append(assign.role.name)

    if filled_count:
        messages.success(request, f"Auto-filled {filled_count} duties for {event.title}.")
    if skipped_roles:
        messages.warning(request, f"No available staff for roles: {','.join(skipped_roles)}")
    if not filled_count and not skipped_roles:
        messages.info(request, f"{event.title} has no empty duties to fill.")

    return redirect('staff:event_status')


def auto_fill_event(event):
    """Auto-fill empty or dropped assignments for a single Event instance.
    Returns the number of duties filled."""
    empty_assignments = event.assignments.filter(
        Q(staff__isnull=True) | Q(status='dropped')
    ).select_related('role')

    filled_count = 0
    for assign in empty_assignments:
        assigned_staff_ids = event.assignments.filter(
            status='assigned'
        ).exclude(id=assign.id).values_list('staff_id', flat=True)

        candidate = Staff.objects.filter(
            role=assign.role,
            is_active=True,
            reliability_score__gte=75
        ).exclude(id__in=assigned_staff_ids).order_by('-reliability_score').first()

        if candidate:
            assign.staff = candidate
            assign.status = 'assigned'
            assign.save()
            filled_count += 1

    return filled_count

@staff_member_required
def auto_fill_all_events(request):
    today = timezone.now().date()
    events = Event.objects.filter(start_time__date__gte=today)
    total_filled = 0
    for event in events:
        filled = auto_fill_event(event)
        total_filled += filled
    messages.success(request, f"Auto-filled all upcoming events")
    return redirect('staff:event_status')

@staff_member_required
def create_assignments_from_template(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    template = request.GET.get('template') or request.POST.get('template')
    
    if not template:
        messages.error(request, "No template provided")
        return redirect('staff:assignment_list', event_id=event_id)

    role_counts = json.loads(template)  # expects {"1": 2, "3": 1} = role_id: count
    
    assignments = []
    duty_num = event.assignments.count() + 1
    for role_id, count in role_counts.items():
        role = get_object_or_404(Role, id=role_id)
        for _ in range(int(count)):
            assignments.append(Assignment(event=event, role=role, duty_number=duty_num, status='assigned'))
            duty_num += 1
    
    Assignment.objects.bulk_create(assignments)
    messages.success(request, f"Created {len(assignments)} assignments from template")
    return redirect('staff:assignment_list', event_id=event_id)

@staff_member_required
@require_POST
@csrf_exempt
def update_assignment_role(request, assignment_id):
    """
    AJAX endpoint to update the role for an assignment
    """
    try:
        data = json.loads(request.body)
        new_role_id = data.get('role_id')

        assignment = get_object_or_404(Assignment, id=assignment_id)
        new_role = get_object_or_404(Role, id=new_role_id)

        assignment.role = new_role
        assignment.save(update_fields=['role'])

        return JsonResponse({
            'success': True,
            'role_name': new_role.name
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

    
    

    

    
        
     
    
    



