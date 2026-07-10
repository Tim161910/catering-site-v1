from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Recruitment, Applicant, RolePlay, Incident, Event, Staff, Assignment
from .forms import RecruitmentForm, ApplicantForm, IncidentForm, EventForm

class RecruitmentUpdateView(UpdateView):
    model = Recruitment
    form_class = RecruitmentForm
    template_name = 'staff/recruitment_form.html'
    success_url = reverse_lazy('staff:recruitment_list')

class RecruitmentDeleteView(DeleteView):
    model = Recruitment
    success_url = reverse_lazy('staff:recruitment_list')
    template_name = 'staff/recruitment_confirm_delete.html'

class ApplicantListView(ListView):
    model = Applicant
    template_name = 'staff/applicant_list.html'

class ApplicantDetailView(DetailView):
    model = Applicant
    template_name = 'staff/applicant_detail.html'

class ApplicantCreateView(CreateView):
    model = Applicant
    form_class = ApplicantForm
    template_name = 'staff/applicant_form.html'
    success_url = reverse_lazy('staff:applicant_list')

class ApplicantUpdateView(UpdateView):
    model = Applicant
    form_class = ApplicantForm
    template_name = 'staff/applicant_form.html'
    success_url = reverse_lazy('staff:applicant_list')

class ApplicantDeleteView(DeleteView):
    model = Applicant
    success_url = reverse_lazy('staff:applicant_list')
    template_name = 'staff/applicant_confirm_delete.html'

class StaffListView(LoginRequiredMixin, ListView):
    model = Staff
    template_name = 'staff/staff_list.html'
    context_object_name = 'staff_members'

class StaffCreateView(LoginRequiredMixin, CreateView):
    model = Staff
    fields = ['name', 'phone', 'email', 'reliability_score', 'is_active', 'user'] # change fields to match your Staff model
    template_name = 'staff/staff_form.html'
    success_url = reverse_lazy('staff:staff_list')

class StaffDetailView(LoginRequiredMixin, DetailView):
    model = Staff
    template_name = 'staff/staff_detail.html'
    context_object_name = 'staff'

class StaffUpdateView(LoginRequiredMixin, UpdateView):
    model = Staff
    fields = ['name', 'phone', 'email', 'reliability_score', 'is_active', 'user'] # same as create
    template_name = 'staff/staff_form.html'
    success_url = reverse_lazy('staff:staff_list')

class StaffDeleteView(LoginRequiredMixin, DeleteView):
    model = Staff
    template_name = 'staff/staff_confirm_delete.html'
    success_url = reverse_lazy('staff:staff_list')

class RolePlayListView(ListView):
    model = RolePlay
    template_name = 'staff/roleplay_list.html'

class RolePlayDetailView(DetailView):
    model = RolePlay
    template_name = 'staff/roleplay_detail.html'

class IncidentListView(ListView):
    model = Incident
    template_name = 'staff/incident_list.html'


class IncidentCreateView(CreateView):
    model = Incident
    form_class = IncidentForm
    template_name = 'staff/incident_form.html'
    success_url = reverse_lazy('staff:incident_list')

class IncidentUpdateView(UpdateView):
    model = Incident
    form_class = IncidentForm
    template_name = 'staff/incident_form.html'
    success_url = reverse_lazy('staff:incident_list')

class IncidentDetailView(DetailView):
    model = Incident
    template_name = 'staff/incident_detail.html'

class EventCreateView(CreateView):
    model = Event
    form_class = EventForm
    template_name = 'staff/event_form.html'
    success_url = reverse_lazy('staff:event_list')

class DashboardView(TemplateView):
    template_name = 'staff/dashboard.html'

class StaffDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'staff/staff_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        try:
            staff = Staff.objects.get(user=user)
        except Staff.DoesNotExist:
            staff = None

        context['staff'] = staff
        if staff:
            context['upcoming_assignments'] = Assignment.objects.filter(
                staff=staff, 
                event__start_time__gte=timezone.now()
            ).order_by('event__start_time')[:5]
            context['reliability_score'] = staff.reliability_score
        return context

class EventStaffDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'staff/event_staff_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event_id = kwargs.get('event_id')
        event = get_object_or_404(Event, id=event_id)
        context['event'] = event
        context['assignments'] = event.assignments.all().select_related('staff', 'role')
        return context

@staff_member_required
@require_POST
@csrf_exempt
def replace_staff(request, assignment_id):
    """
    AJAX endpoint to replace staff on a duty via dashboard dropdown
    """
    try:
        assignment = get_object_or_404(Assignment, id=assignment_id, status='assigned')
        new_staff_id = request.POST.get('new_staff_id')
        
        if not new_staff_id:
            return JsonResponse({'success': False, 'error': 'No staff selected'}, status=400)
        
        new_staff = get_object_or_404(Staff, id=new_staff_id, is_active=True)
        old_staff_name = assignment.staff.name if assignment.staff else 'Empty'
        
        assignment.staff = new_staff
        assignment.reassignment_reason = f"Replaced {old_staff_name} via dashboard"
        assignment.reassigned_at = timezone.now()
        assignment.reassigned_by = request.user
        assignment.save()
        
        return JsonResponse({
            'success': True, 
            'new_staff': new_staff.name,
            'new_score': new_staff.reliability_score
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)