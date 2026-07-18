from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views import View
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Q, ProtectedError, F, Avg
from django.db.models.functions import TruncMonth
import csv
import logging
import json
from datetime import datetime, timedelta
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.utils.decorators import method_decorator
from  .forms import StaffFilterForm, StaffForm
from django.http import Http404
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.db.models.functions import Coalesce
from django.db.models import IntegerField, Value

logger = logging.getLogger(__name__)

from django import forms
from .models import Recruitment, Applicant, RolePlay, Incident, Event, Staff, Assignment, Role, RolePlayResponse, InterviewSlot, ApplicantRolePlay, Notification, StaffUpdateRequest, Task
from .forms import RecruitmentForm, ApplicantForm, IncidentForm, EventForm, StaffForm, StaffProfileForm, RolePlayForm, RolePlayResponseForm, StaffFilterForm

def bamboo_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Redirect based on role
            if user.is_superuser or user.is_staff:
                return redirect('staff:staff_dashboard')
            else:
                return redirect('staff:staff_profile_edit')
        else:
            messages.error(request, "Invalid username or password")
    else:
        form = AuthenticationForm()
    return render(request, 'staff/bamboo_login.html', {'form': form})

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
        self.object.status = 'closed' 
        self.object.save()
        messages.success(request, "Recruitment closed.")
        return HttpResponseRedirect(self.success_url)

@method_decorator(staff_member_required, name='dispatch')
class CloseRecruitmentView(View):
    def post(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        recruitment.status = 'closed'
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
        applicants = recruitment.applicants.all()

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
        applicants = recruitment.applicants.all()
        return render(request, 'staff/send_email_form.html', { # changed this
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

        return render(request, 'staff/emails_sent.html', { # render results instead of redirect
            'recruitment': recruitment,
            'emails_sent': emails_sent,
            'errors': errors
        })       

@method_decorator(staff_member_required, name='dispatch')    
class ScheduleInterviewsView(View):
    def get(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        applicants = recruitment.applicants.all()
        return render(request, 'staff/schedule_interviews.html', {
            'recruitment': recruitment, 
            'applicants': applicants, 
            'errors':[],
            'scheduled_applicants': []
        })
    
    def post(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        all_applicants = recruitment.applicant_set.all()
        applicant_ids = request.POST.getlist('applicant_ids')
        
        errors = []
        scheduled_applicants = []
        
        if not applicant_ids:
            errors = ["Please select at least one applicant to schedule an interview."]
        else:
            applicants = Applicant.objects.filter(id__in=applicant_ids, recruitment_id=recruitment_id)
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

        # Always render with full context
        return render(request, 'staff/schedule_interviews.html', {
            'recruitment': recruitment, 
            'applicants': all_applicants, 
            'errors': errors,
            'scheduled_applicants': scheduled_applicants
        })

@method_decorator(staff_member_required, name='dispatch')
class ManageInterviewSlotsView(View):
    template_name = 'staff/manage_slots.html'

    def get(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        
        # Get all slots for this recruitment with booking counts
        slots = InterviewSlot.objects.filter(recruitment=recruitment).annotate(
            booked_count=Count('applicants'),
            available=F('capacity') - Count('applicants')
        ).order_by('date', 'start_time')

        context = {
            'recruitment': recruitment,
            'slots': slots,
            'today': timezone.now().date()
        }
        return render(request, self.template_name, context)

    def post(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)

        date = request.POST.get('date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        capacity = request.POST.get('capacity')

        # Basic validation
        if date and start_time and end_time and capacity:
            InterviewSlot.objects.create(
                recruitment=recruitment,
                date=date,
                start_time=start_time,
                end_time=end_time,
                capacity=capacity
            )
            messages.success(request, "Interview slot added.")
        else:
            messages.error(request, "Please fill all fields.")

        return redirect('staff:manage_interview_slots', recruitment_id=recruitment_id)

class StaffCreateView(CreateView):
    model = Staff
    form_class = StaffForm
    template_name = 'staff/staff_form.html'
    success_url = '/staff/'

class StaffListView(LoginRequiredMixin, ListView):
    model = Staff
    template_name = 'staff/staff_list.html'
    context_object_name = 'staff_list'
    paginate_by = 20

    def get_queryset(self):
        # Don't loop here. Assume score is updated via signal on Incident save
        qs = Staff.objects.select_related('role').all()

        search = self.request.GET.get('q') # match your template input name
        role_id = self.request.GET.get('role')
        reliability = self.request.GET.get('reliability')

        if search:
            # Can't do icontains on EncryptedCharField. So only search non-encrypted fields
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(role__name__icontains=search)
            )
        
        if role_id:
            qs = qs.filter(role_id=role_id)

        # Reliability filter
        if reliability == 'a_team':
            qs = qs.filter(reliability_score__gte=90)
        elif reliability == 'good':
            qs = qs.filter(reliability_score__gte=80, reliability_score__lt=90)
        elif reliability == 'watch':
            qs = qs.filter(reliability_score__gte=70, reliability_score__lt=80)
        elif reliability == 'warning':
            qs = qs.filter(reliability_score__lt=70)

        return qs.order_by('-reliability_score', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = StaffFilterForm(self.request.GET)
        context['roles'] = Role.objects.all() # for role dropdown
        context['staff_count'] = self.get_queryset().count()
        return context
    
    def get(self, request, *args, **kwargs):
        if request.GET.get('export') == 'csv':
            return self.export_to_csv()
        return super().get(request, *args, **kwargs)

    def export_to_csv(self):
        queryset = self.get_queryset()
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="staff_list.csv"'

        writer = csv.writer(response)
        writer.writerow(['Name', 'Role', 'Email', 'Phone', 'WhatsApp', 'Reliability', 'Status'])
        for staff in queryset:
            writer.writerow([
                staff.name,
                staff.role.name if staff.role else '-',
                staff.email or '-',
                str(staff.phone) if staff.phone else '-', # cast EncryptedField to str
                str(staff.whatsapp) if staff.whatsapp else '-',
                staff.reliability_score,
                'Active' if staff.is_active else 'Inactive'
            ])
        return response

class StaffDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Staff
    template_name = 'staff/staff_confirm_delete.html'
    success_url = reverse_lazy('staff:staff_list')
    context_object_name = 'staff'  # so {{ staff.name }} works in template

    def test_func(self):
        return self.request.user.is_staff # Only allow staff users to delete

    def handle_no_permission(self):
        messages.error(self.request, "You cannot delete yourself.")
        return redirect('staff:staff_list')

    def form_valid(self, form):
        staff = self.get_object()
        
        # Safety: don't delete last admin
        if staff.role == 'admin' and Staff.objects.filter(role='admin').count() <= 1:
            messages.error(self.request, "Cannot delete the last admin.")
            return redirect('staff:staff_list')
            
        messages.success(self.request, f"Staff '{staff.name}' deleted successfully.")
        return super().form_valid(form)

class StaffUpdateView(LoginRequiredMixin, UpdateView):
    model = Staff
    form_class = StaffForm  # change fields to match your Staff model
    template_name = 'staff/staff_form.html'
    success_url = reverse_lazy('staff:staff_list')

class StaffDetailView(DetailView):
    model = Staff
    template_name = 'staff/staff_detail.html'
    context_object_name = 'staff'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff = self.get_object()

        history = staff.incidents.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            score=Avg('reliability_impact')  # impact should be +5 for good, -10 for no_show etc
        ).order_by('month')

        # Convert to lists for the chart
        context['chart_labels'] = [h['month'].strftime("%b %Y") for h in history if h['month']]
        context['chart_data'] = [round(h['score'] or 0, 1) for h in history]
        
        return context

class StaffProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Staff
    form_class = StaffProfileForm
    template_name = 'staff/staff_profile_form.html'

    def get_object(self, queryset=None):
        return self.request.user.staff

    def get_success_url(self):
        return reverse('staff:staff_detail', kwargs={'pk': self.object.pk})

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

    def get_success_url(self):
        # redirect with flag so list page can show toast
        return f"{reverse('staff:role_play_list')}?deleted=1"

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            # if this roleplay has responses linked, prevent delete
            return redirect(f"{reverse('staff:role_play_list')}?error=protected")

class ApplicantRolePlayForm(forms.ModelForm):
    class Meta:
        model = ApplicantRolePlay
        fields = ('applicant', 'role_play', 'score')
        widgets = {
            'applicant': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white'
            }),
            'role_play': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white'
            }),
            'score': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500',
                'min': 0,
                'max': 100,
                'placeholder': 'Score out of 100'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['applicant'].empty_label = "Select Applicant"
        self.fields['role_play'].empty_label = "Select Scenario"
        self.fields['applicant'].queryset = Applicant.objects.all().order_by('name')  # now defined
        self.fields['role_play'].queryset = RolePlay.objects.all().order_by('title')  # now defined
    
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
class EventCreateView(LoginRequiredMixin, CreateView):
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
            roles = {str(role.id): role for role in Role.objects.filter(id__in=role_ids)}

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
                            status='unassigned', # 👈 FIX 1: should be 'unassigned' not 'assigned' since staff=None
                            staff=None  # Initially unassigned
                        )
                    )
                    duty_num += 1

            Assignment.objects.bulk_create(assignments)
            
            messages.success(self.request, f'Created "{event.title}" with {len(assignments)} duty slots. Ready for auto-fill')
            return response

@method_decorator(staff_member_required, name='dispatch')
class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = 'staff/event_form.html'  # re-use the same form
    success_url = reverse_lazy('staff:event_list')

    def get_form_kwargs(self):
     
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.get_object()
        return kwargs

    def form_valid(self, form):
        with transaction.atomic():
            event = self.object
    
            old_assignments = list(event.assignments.all())
            old_count = len(old_assignments)

            response = super().form_valid(form)
            
            new_role_counts = form.get_role_counts()

            event.assignments.filter(staff__isnull=True).delete()

            assigned_counts = {}
            for a in event.assignments.filter(staff__isnull=False):
                assigned_counts[a.role_id] = assigned_counts.get(a.role_id, 0) + 1

            roles = {str(role.id): role for role in Role.objects.filter(id__in=new_role_counts.keys())}
            
            assignments_to_create = []
            duty_num = event.assignments.count() + 1 # continue numbering

            for role_id, target_count in new_role_counts.items():
                role_obj = roles.get(str(role_id))
                if not role_obj: continue

                already_assigned = assigned_counts.get(int(role_id), 0)
                needed = target_count - already_assigned # only create the difference

                for _ in range(max(0, needed)):
                    assignments_to_create.append(
                        Assignment(
                            event=event,
                            duty_number=duty_num,
                            role=role_obj,
                            status='unassigned',
                            staff=None
                        )
                    )
                    duty_num += 1
            
            Assignment.objects.bulk_create(assignments_to_create)

            new_total = event.assignments.count()
            messages.success(self.request, f'Updated "{event.title}". Duties: {old_count} → {new_total}')
            return response

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

    def get_success_url(self):
        # redirect with flag so list page can show toast
        return f"{reverse('staff:event_list')}?deleted=1"

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            # redirect with error flag instead of messages
            return redirect(f"{reverse('staff:event_list')}?error=protected")

class EventStatusView(LoginRequiredMixin, TemplateView):
    template_name = 'staff/event_status.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0)

        # STATS
        context['stats'] = {
            'total_events': Event.objects.count(),
            'upcoming': Event.objects.filter(start_time__gte=now).count(),
            'this_month': Event.objects.filter(start_time__gte=month_start).count(),
            'past': Event.objects.filter(start_time__lt=now).count(),
        }

        # EVENTS + DUTIES
        events = Event.objects.filter(start_time__gte=now - timedelta(days=1)).order_by('start_time')[:10]
        event_list = []

        for event in events:
            assignments = Assignment.objects.filter(event=event).select_related('staff', 'role')
            duties = []
            at_risk = empty = ok = 0

            for a in assignments:
                staff = a.staff
                score = staff.reliability_score if staff else 0

                # determine status
                if not staff:
                    status = 'critical'
                    empty += 1
                elif score < 70:
                    status = 'critical'
                    at_risk += 1
                elif score < 85:
                    status = 'warning'
                    at_risk += 1
                else:
                    status = 'ok'
                    ok += 1

                # check conflicts - same staff assigned to another event at same time
                conflicts = []
                if staff:
                    overlapping = Assignment.objects.filter(
                        staff=staff, 
                        event__start_time__lt=event.end_time,
                        event__end_time__gt=event.start_time
                    ).exclude(event=event)
                    conflicts = [o.event.title for o in overlapping]

                # candidates for replacement: active staff not already assigned, sorted by reliability
                candidates = Staff.objects.filter(is_active=True).exclude(id=staff.id if staff else None).order_by('-reliability_score')[:10]

                duties.append({
                    'index': a.duty_number,
                    'assignment_id': a.id,
                    'staff': staff.name if staff else None,
                    'role': a.role.name if a.role else 'General',
                    'score': score,
                    'status': status,
                    'conflicts': conflicts,
                    'candidates': candidates,
                })

            event_list.append({
                'id': event.id,
                'title': event.title,
                'date': event.start_time,
                'location': event.location,
                'duties': duties,
                'at_risk': at_risk,
                'empty': empty,
                'ok': ok,
                'total_duties': len(duties),
            })

        context['events'] = event_list
        return context

class TaskListView(ListView):
    model = Task
    template_name = 'staff/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 20  # optional

    def get_queryset(self):
        # Show all tasks. You can filter by user later if you want
        return Task.objects.all()

@method_decorator(staff_member_required, name='dispatch')
class StaffDashboardView(ListView):
    model = Staff
    template_name = 'admin/risk_dashboard.html'  # <-- fixed
    context_object_name = 'staff_list'

    def get_queryset(self):
        qs = Staff.objects.annotate(
            events_worked=Count('assignments__event', distinct=True),
            incident_count=Count('incidents'),
            no_show=Count('incidents', filter=Q(incidents__incident_type='no_show')),
            reliability_score_safe=Coalesce('reliability_score', Value(0), output_field=IntegerField())
        )

        status = self.request.GET.get('status')
        q = self.request.GET.get('q')
        sort = self.request.GET.get('sort')

        if status == 'A-Team':
            qs = qs.filter(reliability_score_safe__gte=90)
        elif status == 'Standard':
            qs = qs.filter(reliability_score_safe__gte=60, reliability_score_safe__lt=90)
        elif status == 'Warning':
            qs = qs.filter(reliability_score_safe__lt=60)

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(role__name__icontains=q) |
                Q(email__icontains=q) |
                Q(phone__icontains=q)
            )

        if sort == 'score':
            qs = qs.order_by('-reliability_score_safe')
        elif sort == 'events':
            qs = qs.order_by('-events_worked')
        elif sort == 'incidents':
            qs = qs.order_by('-incident_count')
        else:
            qs = qs.order_by('-reliability_score_safe')

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        context['upcoming_events'] = Event.objects.filter(start_time__date__gte=today).order_by('start_time')
        context['risky_staff'] = Staff.objects.filter(reliability_score__lt=80).order_by('reliability_score')
        return context
    
@method_decorator(staff_member_required, name='dispatch')
class IncidentCreateView(CreateView):
    model = Incident
    form_class = IncidentForm
    template_name = 'staff/incident_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # match the ?staff=1 from staff_detail.html button
        kwargs['staff_id'] = self.request.GET.get('staff')  
        return kwargs

    def get_success_url(self):
        # redirect back to the staff profile instead of dashboard
        return reverse('staff:staff_detail', kwargs={'pk': self.object.staff.pk})
    
@require_POST
@csrf_exempt
@login_required
@staff_member_required
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

        # Prevent double booking same staff on same duty
        if Assignment.objects.filter(event=event, staff_id=staff_id, status='assigned', duty_number=duty_number).exists():
            return JsonResponse({'success': False, 'error': 'Staff already assigned to this duty number.'}, status=400)

        # Prevent same duty_number + role having 2 people
        if Assignment.objects.filter(event=event, role_id=role_id, duty_number=duty_number, status='assigned').exists():
            return JsonResponse({'success': False, 'error': 'This duty slot is already filled.'}, status=400)

        role_obj = get_object_or_404(Role, id=role_id)
        assignment = Assignment.objects.create(
            event=event,
            staff_id=staff_id,
            duty_number=duty_number,
            role=role_obj,
            status='assigned'
        )

        return JsonResponse({
            'success': True,
            'assignment_id': assignment.id,
            'role_name': role_obj.name,
            'duty_number': assignment.duty_number
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)  

@require_POST
@login_required
@staff_member_required
@csrf_exempt
def reassign_assignment(request, assignment_id):
    try:
        data = json.loads(request.body)
        new_staff_id = data.get('new_staff_id')
        reason = data.get('reason', '').strip()

        if not new_staff_id:
            return JsonResponse({'success': False, 'error': 'No staff selected'}, status=400)

        old_assignment = get_object_or_404(Assignment, id=assignment_id)

        if old_assignment.status == 'dropped':
            return JsonResponse({'success': False, 'error': 'This assignment was already dropped'}, status=400)

        # Check if new staff is already assigned to THIS event on ANY duty
        if old_assignment.event.assignments.filter(staff_id=new_staff_id, status='assigned').exists():
            return JsonResponse({'success': False, 'error': 'Staff already assigned to this event'}, status=400)

        with transaction.atomic():
            # Drop old assignment
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
            'new_staff': new_assignment.staff.get_full_name() or new_assignment.staff.username,
            'duty': new_assignment.duty_number
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@staff_member_required
@require_POST
def replace_staff(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    new_staff_id = request.POST.get('new_staff_id')

    if not new_staff_id:
        return JsonResponse({'success': False, 'error': 'No staff selected'}, status=400)
    
    new_staff = get_object_or_404(Staff, id=new_staff_id)
    
    # Check if staff already assigned to this event
    if assignment.event.assignments.filter(staff=new_staff, status='assigned').exists():
        return JsonResponse({'success': False, 'error': 'Staff already assigned to this event'}, status=400)
    
    old_staff_name = assignment.staff.name if assignment.staff else 'Empty'

    assignment.staff = new_staff
    assignment.status = 'assigned'
    assignment.reassigned_at = timezone.now()
    assignment.reassigned_by = request.user
    assignment.reassignment_reason = request.POST.get('reason', 'Replaced via dashboard')
    assignment.save(update_fields=['staff', 'status', 'reassigned_at', 'reassigned_by', 'reassignment_reason'])

    return JsonResponse({
        'success': True,
        'old_staff': old_staff_name,
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
def assign_staff(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id) # CHANGED
    event = assignment.event
    
    if request.method == 'POST':
        staff_id = request.POST.get('staff')
        if not staff_id:
            messages.error(request, 'Please select a staff member')
        else:
            assignment.staff_id = staff_id
            assignment.status = 'assigned'  # 'pending' doesn't exist in your Assignment model
            assignment.save()
            
            messages.success(request, f'Staff assigned to {assignment.role.name}')
            
            # Create in-app notification for the assigned staff
            assignment_link = reverse('staff:assignment_list', args=[event.id]) # you don't have assignment_detail url
            Notification.objects.create(
                user=assignment.staff.user,  # CHANGED: Notification.user is a User, not Staff
                message=f"You've been assigned as {assignment.role.name} for '{event.title}'",
                related_event=event,
                related_assignment=assignment
            )
            
            return redirect('staff:assignment_list', event_id=event.id) # FIX: your url uses event_id
    
    # staff already assigned to this event
    assigned_staff_ids = event.assignments.values_list('staff_id', flat=True)
    
    # show only active staff not already assigned to this event
    available_staff = Staff.objects.filter(is_active=True).exclude(id__in=assigned_staff_ids)
    
    context = {
        'assignment': assignment,
        'event': event,
        'available_staff': available_staff,
    }
    return render(request, 'staff/assign_staff.html', context)

@login_required
def update_staff(request, pk):
    staff = get_object_or_404(Staff, pk=pk)

    if request.method == 'POST':
        form = StaffForm(request.POST, instance=staff)
        if form.is_valid():
            # Get old data before we save anything
            old = Staff.objects.get(pk=staff.pk)
            approval_needed = False

            # 1. Check APPROVAL_REQUIRED_FIELDS
            for field in staff.APPROVAL_REQUIRED_FIELDS:
                old_value = getattr(old, field)
                new_value = form.cleaned_data.get(field)

                if old_value!= new_value:
                    StaffUpdateRequest.objects.create(
                        staff=staff,
                        requested_by=request.user,
                        request_reason=f"Change {field} from '{old_value}' to '{new_value}'",
                        field_name=field,
                        old_value=old_value,
                        new_value=new_value
                    )
                    approval_needed = True

            # 2. Update DIRECT_UPDATE_FIELDS immediately
            for field in staff.DIRECT_UPDATE_FIELDS:
                setattr(staff, field, form.cleaned_data[field])

            staff.save(update_fields=staff.DIRECT_UPDATE_FIELDS)

            if approval_needed:
                # redirect to "pending approval" page
                return redirect('staff_detail', pk=staff.pk)
            else:
                return redirect('staff_detail', pk=staff.pk)
    else:
        form = StaffForm(instance=staff)

    return render(request, 'staff/staff_form.html', {'form': form, 'staff': staff})

def staff_context(request):
    if request.user.is_authenticated:
        return {
            'notifications': request.user.notifications.all()[:10],
            'unread_count': request.user.notifications.filter(is_read=False).count()
        }
    return {}

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

@staff_member_required
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
    messages.success(request, f"Auto-filled {total_filled} assignments across {events.count()} upcoming events")
    return redirect('staff:event_status')

@staff_member_required
def create_assignments_from_template(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    template = request.GET.get('template') or request.POST.get('template')
    
    if not template:
        messages.error(request, "No template provided")
        return redirect('staff:assignment_list', event_id=event_id)

    try:
        role_counts = json.loads(template)  # expects {"1": 2, "3": 1} = role_id: count
    except json.JSONDecodeError:
        messages.error(request, "Invalid template format")
        return redirect('staff:assignment_list', event_id=event_id)
    
    assignments = []
    duty_num = event.assignments.count() + 1
    for role_id, count in role_counts.items():
        role = get_object_or_404(Role, id=role_id)
        for _ in range(int(count)):
            assignments.append(Assignment(event=event, role=role, duty_number=duty_num, status='assigned'))
            duty_num += 1
    
    if assignments:
        Assignment.objects.bulk_create(assignments)
        messages.success(request, f"Created {len(assignments)} assignments from template")
    else:
        messages.warning(request, "Template had no roles")

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

        if not new_role_id:
            return JsonResponse({'success': False, 'error': 'No role_id provided'}, status=400)

        assignment = get_object_or_404(Assignment, id=assignment_id)
        new_role = get_object_or_404(Role, id=new_role_id, is_active=True) # only allow active roles

        if assignment.role_id == new_role_id:
            return JsonResponse({'success': True, 'role_name': new_role.name, 'message': 'No change'})

        assignment.role = new_role
        assignment.save(update_fields=['role']) # only update role field

        return JsonResponse({
            'success': True,
            'role_name': new_role.name
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

def apply_to_recruitment(request, recruitment_id):
    recruitment = get_object_or_404(Recruitment, pk=recruitment_id, status='open')

    if request.method == 'POST':
        form = ApplicantForm(request.POST, request.FILES)
        if form.is_valid():
            applicant = form.save(commit=False)
            applicant.recruitment = recruitment
            applicant.save()
            messages.success(request, f"Application submitted for {recruitment.position}!")
            return redirect('staff:recruitment_detail', recruitment_id=recruitment_id)
    else:
        form = ApplicantForm()

    return render(request, 'staff/application_form.html', {
        'form': form, 
        'recruitment': recruitment
    })

class SlotApplicantsView(View):
    def get(self, request, slot_id):
        slot = get_object_or_404(InterviewSlot, pk=slot_id)
        applicants = slot.applicants.all()  # use slot.applications.all() if you set related_name
        return render(request, 'staff/slot_applicants.html', {'slot': slot, 'applicants': applicants})

class DeleteSlotView(View):
    def get(self, request, slot_id):
        slot = get_object_or_404(InterviewSlot, pk=slot_id)
        recruitment_id = slot.recruitment.id
        slot.delete()
        messages.success(request, "Interview slot deleted.")
        return redirect('staff:manage_interview_slots', recruitment_id=recruitment_id)

@method_decorator(staff_member_required, name='dispatch')
class ExportStaffCSVView(View):
    def get(self, request):
        # Reuse the same filtering logic from StaffDashboardView
        qs = Staff.objects.annotate(
            events_worked=Count('assignments__event', distinct=True),
            incident_count=Count('incidents'),
            no_show=Count('incidents', filter=Q(incidents__incident_type='no_show')),
        )

        # Apply same filters as dashboard
        status = request.GET.get('status')
        q = request.GET.get('q')
        sort = request.GET.get('sort')

        if status == 'A-Team':
            qs = qs.filter(reliability_score__gte=90)
        elif status == 'Standard':
            qs = qs.filter(reliability_score__gte=60, reliability_score__lt=90)
        elif status == 'Warning':
            qs = qs.filter(reliability_score__lt=60)

        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(role__icontains=q))

        if sort == 'score':
            qs = qs.order_by('-reliability_score')
        elif sort == 'events':
            qs = qs.order_by('-events_worked')
        elif sort == 'incidents':
            qs = qs.order_by('-incident_count')

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="staff_report.csv"'

        writer = csv.writer(response)
        writer.writerow(['Name', 'Role', 'Events', 'Incidents', 'No Shows', 'Reliability Score', 'Status'])

        for staff in qs:
            status = (
                'A-Team' if staff.reliability_score >= 90 
                else 'Standard' if staff.reliability_score >= 60 
                else 'Warning'
            )
            writer.writerow([
                staff.name,
                staff.role,
                staff.events_worked,
                staff.incident_count,
                staff.no_show,
                f'{staff.reliability_score}%',
                status
            ])
        return response

@login_required
def staff_dashboard(request):
    try:
        staff = request.user.staff
    except Staff.DoesNotExist:
        messages.error(request, "No staff profile linked to your account.")
        return redirect('staff:staff_profile_edit')

    now = timezone.now()
    
    # 1. Upcoming assignments
    upcoming_assignments = Assignment.objects.filter(
        staff=staff,
        status='assigned',
        event__start_time__gte=now
    ).select_related('event', 'role').order_by('event__start_time')[:5]

    # 2. Unread notifications
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:5]
    unread_count = notifications.count()

    # 3. Reliability history for chart
    history = staff.incidents.annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        score=Avg('reliability_impact')
    ).order_by('month')[:6]

    chart_labels = [h['month'].strftime("%b %Y") for h in history if h['month']]
    chart_data = [round(h['score'] or 0, 1) for h in history]

    context = {
        'staff': staff,
        'assignments': upcoming_assignments,
        'notifications': notifications,
        'unread_count': unread_count,
        'reliability_score': staff.reliability_score,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
    }
    return render(request, 'staff/dashboard.html', context)

@require_POST
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'success': True})

def mark_all_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect(request.META.get('HTTP_REFERER', 'staff:event_list'))
        