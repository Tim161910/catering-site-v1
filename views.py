# 1. IMPORT + HELPERS + MIXINS

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views import View
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Q, ProtectedError, Sum
import csv
import logging
import json
from django.views import View
from datetime import datetime
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.forms import modelformset_factory
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.utils.dateparse import parse_datetime 

logger = logging.getLogger(__name__)


def is_admin(user):
    """Return True for users allowed to access the admin dashboard."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


from .models import Recruitment, Applicant, RolePlay, Incident, Event, Staff, Assignment, Role, RolePlayResponse, InterviewSlot, Task, Notification, LeaveRequest, EventTemplate
from .forms import RecruitmentForm, ApplicantForm, IncidentForm, EventForm, StaffForm, RolePlayForm, RolePlayResponseForm, InterviewSlotForm


class StaffRequiredMixin(UserPassesTestMixin):
    """Only allow users who have a Staff profile"""
    def test_func(self):
        return hasattr(self.request.user, 'staff') and self.request.user.staff.is_active
    
    def handle_no_permission(self):
        messages.error(self.request, "You must be logged in as active staff to access this page.")
        return redirect('staff:staff_login')


# 2. CORE / UTILS

class RoleListView(StaffRequiredMixin, ListView):
    model = Role
    template_name = 'staff/role_list.html'

# 3. EVENTS

class EventListView(LoginRequiredMixin, ListView):
    login_url = 'staff:staff_login'
    model = Event
    template_name = 'staff/event_list.html'
    context_object_name = 'events'

    def get_queryset(self):
        """Different queryset for staff vs admin"""
        today = timezone.now().date()
        
        if hasattr(self.request.user, 'staff'):
            # STAFF: show only events where they have assignments
            staff = self.request.user.staff
            event_ids = Assignment.objects.filter(staff=staff).values_list('event_id', flat=True)
            return Event.objects.filter(id__in=event_ids, start_time__date__gte=today).order_by('start_time')
        else:
            # ADMIN: show all upcoming events
            return Event.objects.filter(start_time__date__gte=today).order_by('start_time')

    def get_context_data(self, **kwargs):
        """Add notifications + extra data"""
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # 1. Add notifications for both admin and staff
        context['notifications'] = Notification.objects.filter(user=user).order_by('-created_at')[:10]
        context['unread_notification_count'] = Notification.objects.filter(user=user, is_read=False).count()

        # 2. Add staff assignments if user is staff
        if hasattr(user, 'staff'):
            context['assignments'] = Assignment.objects.filter(staff=user.staff)
        else:
            # 3. Add counts for admin
            for event in context['events']:
                event.accepted_count = Assignment.objects.filter(event=event, status='accepted').count()
                event.declined_count = Assignment.objects.filter(event=event, status='declined').count()

        return context

class EventDetailView(LoginRequiredMixin, DetailView):
    login_url = 'staff:staff_login'
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

class EventCreateView(StaffRequiredMixin, CreateView):
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

class EventUpdateView(StaffRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = 'staff/event_form.html'  # re-use the same form
    success_url = reverse_lazy('staff:event_list')

class EventDeleteView(StaffRequiredMixin, DeleteView):
    model = Event
    template_name = 'staff/event_confirm_delete.html'
    success_url = reverse_lazy('staff:event_list')

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, "Can't delete event. It has assignments linked to it.")
            return redirect('staff:event_list')

class EventStatusView(StaffRequiredMixin, View):
    def get(self, request):
        print(">>>NEW EVENT_STATUS IS RUNNING - FULL VERSION")
        today = timezone.now().date()

        stats = {
            'total_events': Event.objects.count(),
            'upcoming': Event.objects.filter(start_time__date__gte=today).count(),
            'past': Event.objects.filter(start_time__date__lt=today).count(),
            'this_month': Event.objects.filter(start_time__year=today.year, start_time__month=today.month).count(),
        }

        event_data = []
        events = Event.objects.filter(start_time__date__gte=today).prefetch_related(
            'assignments__staff', 'assignments__role', 'template__required_roles'
        ).order_by('start_time')

        for event in events:
            duties = []
            at_risk = 0
            empty = 0
            accepted = 0
            declined = 0
            ok = 0
            
            assignments = event.assignments.filter(status__in=['assigned', 'accepted', 'declined'])
            assigned_staff_ids = list(assignments.exclude(staff=None).values_list('staff_id', flat=True))

            busy_staff_ids = list(Assignment.objects.filter(
                status__in=['assigned', 'accepted'],
                staff__isnull=False,
                event__start_time__lt=event.end_time,
                event__end_time__gt=event.start_time
            ).values_list('staff_id', flat=True))

            # KEY 1: Get required count from template, not assignments
            required_total = 0
            if event.template:
                required_total = event.template.required_roles.aggregate(total=Sum('quantity'))['total'] or 0
            
            accepted_count = assignments.filter(status='accepted').count()
            assigned_count = assignments.filter(status='assigned').count()
            empty_count = required_total - assignments.count()
            if empty_count < 0: empty_count = 0

            # Loop existing assignments
            for a in assignments:
                score = getattr(a.staff, 'reliability_score', 0) if a.staff else 0
                
                if a.status == 'declined':
                    status = 'critical'
                    declined += 1
                elif a.status == 'accepted' and score >= 75:
                    status = 'ok'
                    accepted += 1
                    ok += 1
                elif a.status == 'accepted' and score < 75:
                    status = 'warning'
                    accepted += 1
                    at_risk += 1
                elif score < 50:
                    status = 'critical'
                    at_risk += 1
                elif score < 75:
                    status = 'warning'
                    at_risk += 1
                else: 
                    status = 'ok'
                    ok += 1

                if a.role:
                    replacements = Staff.objects.filter(
                        role=a.role, 
                        is_active=True, 
                        reliability_score__gte=75
                    ).exclude(id__in=assigned_staff_ids).exclude(id__in=busy_staff_ids).order_by('-reliability_score')[:5]
                else:
                    replacements = Staff.objects.none()

                duties.append({
                    'assignment_id': a.id,
                    'index': a.duty_number,
                    'staff': a.staff.name if a.staff else None,
                    'role': a.role.name if a.role else 'No Role',
                    'score': score,
                    'status': status,
                    'assignment_status': a.status,
                    'candidates': replacements
                })

            # KEY 2: Add empty slots so dashboard shows what's missing
            for i in range(empty_count):
                duties.append({
                    'assignment_id': None,
                    'index': assignments.count() + i + 1,
                    'staff': None,
                    'role': 'Empty Slot',
                    'score': 0,
                    'status': 'empty',
                    'assignment_status': 'empty',
                    'candidates': Staff.objects.none()
                })
                empty += 1

            # KEY 3: Overall event badge based on template
            if accepted_count >= required_total and required_total > 0:
                event_badge = "✅ Fully Staffed"
                event_class = "success"
            elif assigned_count > 0:
                event_badge = "🟡 Pending Response"
                event_class = "warning"
            elif required_total > 0:
                event_badge = f"❌ Needs Staff: {required_total} left"
                event_class = "danger"
            else:
                event_badge = "⚠️ No Template"
                event_class = "secondary"

            event_data.append({
                'id': event.id,
                'title': event.title,
                'date': event.start_time,
                'location': event.location,
                'duties': duties,
                'total_duties': required_total,
                'at_risk': at_risk,
                'empty': empty,
                'accepted': accepted,
                'declined': declined,
                'ok': ok,
                'event_badge': event_badge,
                'event_class': event_class,
            })

        context = {'stats': stats, 'events': event_data}
        return render(request, 'staff/event_status.html', context)

class CreateEventFromTemplateView(LoginRequiredMixin, StaffRequiredMixin, View):
    template_name = 'staff/create_event_from_template.html'

    def get(self, request):
        templates = EventTemplate.objects.filter(is_active=True).order_by('name')
        return render(request, self.template_name, {'templates': templates})

    def post(self, request):
        template_id = request.POST.get('template_id')
        title = request.POST.get('title', '').strip()
        
        if not title:
            messages.error(request, "Event Name is required.")
            return redirect('staff:create_event_from_template') # change to your url name

        start_str = request.POST.get('start_time')
        end_str = request.POST.get('end_time')
        location = request.POST.get('location', '')

        # Convert "2025-08-10T14:00" from datetime-local to datetime
        start_time = parse_datetime(start_str) if start_str else None
        end_time = parse_datetime(end_str) if end_str else None
        
        # Make timezone aware for Django
        if start_time and timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time)
        if end_time and timezone.is_naive(end_time):
            end_time = timezone.make_aware(end_time)

        template = get_object_or_404(EventTemplate, id=template_id)

        # Use your existing method!
        event = template.create_event_with_assignments(
            start_time=start_time,
            title=title,
            location=location,
            end_time=end_time,
            created_by=request.user
        )

        messages.success(request, f"Event '{event.title}' created with {event.assignments.count()} duties!")
        return redirect('staff:event_detail', pk=event.id)

# AUTO-FILL HELPERS
def _find_best_candidate(role, event, exclude_ids):
    """Helper: Find best available staff for a role + event time"""
    if not role:
        return None  # safety
    # Staff already booked at this time in ANY event
    busy_staff_ids = Assignment.objects.filter(
        status__in=['assigned', 'accepted'],
        staff__isnull=False,
        event__start_time__lt=event.end_time,
        event__end_time__gt=event.start_time
    ).values_list('staff_id', flat=True)

    candidate = Staff.objects.filter(
        role=role,
        is_active=True,
        reliability_score__gte=75
    ).exclude(id__in=exclude_ids).exclude(id__in=busy_staff_ids).order_by('-reliability_score', '-events_completed').first()
    
    return candidate

def auto_fill_event(event, sender_user=None):
    """Core logic used by both single and bulk auto-fill."""
    if sender_user is None:
        sender_user = User.objects.filter(is_superuser=True).first()

    if event.assignments.count() == 0 and event.template:
        for role_req in event.template.required_roles.all():
            for i in range(role_req.quantity):
                Assignment.objects.create(
                    event=event,
                    role=role_req.role,
                    duty_number=i+1,
                    status='dropped' # 'dropped' = empty slot so we can fill it
                )

    empty_assignments = event.assignments.filter(
        Q(staff__isnull=True) | Q(status='dropped')
    ).select_related('role')

    filled_count = 0
    skipped_roles = []

    for assign in empty_assignments:
        if not assign.role:
            continue
            
        assigned_staff_ids = event.assignments.exclude(id=assign.id).values_list('staff_id', flat=True)
        candidate = _find_best_candidate(assign.role, event, assigned_staff_ids)

        if candidate:
            assign.staff = candidate
            assign.status = 'assigned' # now it's assigned, not dropped
            assign.save()
            
            if candidate.user:
                Notification.objects.create(
                    user=candidate.user,
                    sender=sender_user,
                    sender_type='system',
                    message=f'You have been auto-assigned to: {event.title} as {assign.role.name} on {event.start_time.strftime("%b %d, %H:%M")}',
                    notification_type='assignment',
                    related_event=event,
                    related_assignment=assign
                )
            filled_count += 1
        else:
            if assign.role.name not in skipped_roles:
                skipped_roles.append(assign.role.name)

    return filled_count, skipped_roles

# AUTO-FILL VIEWS
class AutoFillRosterView(StaffRequiredMixin, View):
    def get(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        filled_count, skipped_roles = auto_fill_event(event, request.user)
        request.session['last_auto_fill'] = timezone.now()

        if filled_count:
            messages.success(request, f"Auto-filled {filled_count} duties for {event.title}.")
        if skipped_roles:
            messages.warning(request, f"No available staff for roles: {', '.join(skipped_roles)}")
        if not filled_count and not skipped_roles:
            messages.info(request, f"{event.title} has no empty duties to fill.")

        return redirect('staff:event_status')

class AutoFillAllEventsView(StaffRequiredMixin, View):
    def get(self, request):
        today = timezone.now().date()
        events = Event.objects.filter(start_time__date__gte=today)
        total_filled = 0
        events_with_gaps = 0
        
        for event in events:
            # SKIP CHECK GOES HERE
            if event.template:
                required = event.template.required_roles.aggregate(total=Sum('quantity'))['total'] or 0
                accepted = event.assignments.filter(status='accepted').count()
                if accepted >= required and required > 0:
                    continue # already fully staffed, skip
            
            filled, skipped = auto_fill_event(event, request.user)
            total_filled += filled
            if skipped:
                events_with_gaps += 1
        
        request.session['last_auto_fill'] = timezone.now()
        messages.success(request, f"Auto-filled {total_filled} duties across {events.count()} upcoming events")
        if events_with_gaps:
            messages.warning(request, f"{events_with_gaps} events still have unfilled roles.")
            
        return redirect('staff:event_status')

# 4. RELIABILITY

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

class IncidentListView(StaffRequiredMixin, ListView): pass

def update_reliability_score(staff):
    """Recalculate reliability: completed vs no-shows + incidents"""
    total_completed = staff.assignments.filter(status='completed').count()
    total_accepted = staff.assignments.filter(status__in=['accepted', 'completed']).count()
    no_shows = staff.assignments.filter(status='no_show').count()
    incidents = staff.incidents.count()
    declines = staff.assignments.filter(status='declined').count()

    # Base score starts at 100
    score = 100

    # Big penalties
    score -= no_shows * 15      # no-show is worst
    score -= incidents * 10     # incident logged
    score -= declines * 5       # declining hurts but less

    # Small bonus for actually completing what they accepted
    if total_accepted > 0:
        completion_rate = (total_completed / total_accepted) * 100
        score = (score + completion_rate) / 2  # average with base penalties

    # If they have no history, give them benefit of doubt
    if total_accepted == 0 and no_shows == 0 and incidents == 0:
        score = 100

    staff.reliability_score = max(0, min(100, round(score)))
    staff.save(update_fields=['reliability_score'])
    return staff.reliability_score

# 5. STAFF

@method_decorator(staff_member_required, name='dispatch')
class StaffListView(LoginRequiredMixin, ListView):
    model = Staff
    template_name = 'staff/staff_list.html'
    context_object_name = 'staff_list' # <- CHANGE THIS from 'staff_members'

    def get_queryset(self):
        q = self.request.GET.get('q', '')
        qs = Staff.objects.all().select_related('role')
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | 
                Q(email__icontains=q)
            )
        return qs

class StaffDetailView(LoginRequiredMixin, DetailView):
    login_url = 'staff:staff_login'
    model = Staff
    template_name = 'staff/staff_detail.html'
    context_object_name = 'staff'

@method_decorator(staff_member_required, name='dispatch')
class StaffCreateView(LoginRequiredMixin, CreateView):
    model = Staff
    form_class = StaffForm  # change fields to match your Staff model
    template_name = 'staff/staff_form.html'
    success_url = reverse_lazy('staff:staff_list')

@method_decorator(staff_member_required, name='dispatch')
class StaffUpdateView(LoginRequiredMixin, UpdateView):
    model = Staff
    form_class = StaffForm  # change fields to match your Staff model
    template_name = 'staff/staff_form.html'
    success_url = reverse_lazy('staff:staff_list')

@method_decorator(staff_member_required, name='dispatch')
class StaffDeleteView(LoginRequiredMixin, DeleteView):
    model = Staff
    template_name = 'staff/staff_confirm_delete.html'
    success_url = reverse_lazy('staff:staff_list')

class StaffProfileView(LoginRequiredMixin, DetailView):
    login_url = 'staff:staff_login'
    model = Staff
    template_name = 'staff/staff_profile.html'
    context_object_name = 'staff'

    def get_object(self):
        return self.request.user.staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff = self.object  # this is the staff from get_object()

        # Build the leave_balance dict for the template
        context['leave_balance'] = {
            'Annual Leave': getattr(staff, 'annual_leave_balance', 0),
            'Sick Leave': getattr(staff, 'sick_leave_balance', 0),
            'Casual Leave': getattr(staff, 'casual_leave_balance', 0),
        }
        
        # Make sure leave_requests is available for the table
        context['staff'].leave_requests = staff.leaverequest_set.all().order_by('-from_date')[:5] 
        # ^^^ assumes your LeaveRequest model has ForeignKey to Staff. 
        # If your related_name is different, use that instead of leaverequest_set

        return context

class StaffProfileUpdateView(LoginRequiredMixin, UpdateView):
    login_url = 'staff:staff_login'
    model = Staff
    form_class = StaffForm
    template_name = 'staff/staff_profile_form.html'
    success_url = reverse_lazy('staff:my_dashboard') 

    def get_object(self, queryset=None):
        # NEW: Don't look for pk. Just get the staff linked to logged in user
        try:
            return self.request.user.staff
        except AttributeError:
            raise PermissionDenied("You do not have a staff profile linked to your account.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update My Profile'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully.')
        return super().form_valid(form)

class ApplyLeaveView(LoginRequiredMixin, View):
    login_url = 'staff:staff_login'
    template_name = 'staff/apply_leave.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        staff = request.user.staff
        leave_type = request.POST.get('leave_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        reason = request.POST.get('reason', '')

        # Basic validation
        if not leave_type or not start_date or not end_date:
            messages.error(request, "All fields are required")
            return render(request, self.template_name)

        # Create the leave request
        LeaveRequest.objects.create(
            staff=staff,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            status='pending'
        )

        messages.success(request, "Leave request submitted successfully. Waiting for approval.")
        return redirect('staff:staff_profile')

@method_decorator([login_required(login_url='staff:staff_login'), staff_member_required], name='dispatch')
class ExportStaffCSVView(View):
    """
    Export staff list to CSV
    """
    def get(self, request):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="staff_export.csv"'

        writer = csv.writer(response)
        writer.writerow(['Name', 'Role', 'Reliability Score', 'Phone', 'Email', 'Active'])

        staff = Staff.objects.all().select_related('role')
        for s in staff:
            writer.writerow([
                s.name, 
                s.role.name if hasattr(s, 'role') and s.role else '', 
                getattr(s, 'reliability_score', 100),
                getattr(s, 'phone', ''),
                getattr(s, 'email', ''),
                'Yes' if s.is_active else 'No'
            ])

        return response

class StaffLoginView(LoginView):
    template_name = 'staff/login.html'
    redirect_authenticated_user = False # CHANGE THIS to False

    def dispatch(self, request, *args, **kwargs):
        # If someone is already logged in but not staff, log them out
        if request.user.is_authenticated:
            if not hasattr(request.user, 'staff'):
                from django.contrib.auth import logout
                logout(request)
                messages.warning(request, "You were logged in as admin. Please login as staff.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_active:
            messages.error(self.request, "This account has been deactivated.")
            return self.form_invalid(form)
        if not hasattr(user, 'staff'):
            messages.error(self.request, "Access denied. You are not registered as staff.")
            return self.form_invalid(form)
        if not user.staff.is_active:
            messages.error(self.request, "Your staff profile has been deactivated. Contact admin.")
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('staff:my_dashboard')

class StaffLogoutView(View):
    def get(self, request):
        logout(request)
        messages.success(request, "You have been logged out.")
        return redirect('staff:staff_login')


# 1. ADMIN/MANAGER VIEW - See all staff

from django.db.models import Count, Q

@method_decorator(staff_member_required, name='dispatch') 
class StaffDashboardView(ListView):
    model = Staff
    template_name = 'staff/staff_dashboard.html'  # Admin table view
    context_object_name = 'staff_list'
    paginate_by = 20

    def get_queryset(self):
        qs = Staff.objects.filter(is_active=True).select_related('role').annotate(
            events_completed=Count('assignments', filter=Q(assignments__status='completed')), # renamed
            incidents_count=Count('incidents'), # renamed
            no_shows=Count('incidents', filter=Q(incidents__incident_type='no_show')) # renamed
        )
        
        # 1. FILTER - changed from 'status' to 'filter'
        f = self.request.GET.get('filter', 'all')
        if f == 'a_team':
            qs = qs.filter(reliability_score__gte=90)
        elif f == 'standard':
            qs = qs.filter(reliability_score__gte=60, reliability_score__lt=90)
        elif f == 'warning':
            qs = qs.filter(reliability_score__lt=60)
            
        # 2. SEARCH
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(role__name__icontains=q))
            
        # 3. SORT - changed to match new select names
        sort = self.request.GET.get('sort', '-reliability_score')
        if sort in ['reliability_score', '-reliability_score', 'name', '-events_completed', '-incidents_count']:
            qs = qs.order_by(sort)
            
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['upcoming_events'] = Event.objects.filter(start_time__gte=timezone.now()).order_by('start_time')[:5]
        
        # STATS CARDS
        context['total_staff'] = Staff.objects.filter(is_active=True).count()
        context['a_team_count'] = Staff.objects.filter(is_active=True, reliability_score__gte=90).count()
        context['standard_count'] = Staff.objects.filter(is_active=True, reliability_score__gte=60, reliability_score__lt=90).count()
        context['warning_count'] = Staff.objects.filter(is_active=True, reliability_score__lt=60).count()
        
        # For keeping form values
        context['query'] = self.request.GET.get('q', '')
        context['current_filter'] = self.request.GET.get('filter', 'all')
        context['current_sort'] = self.request.GET.get('sort', '-reliability_score')
        return context

# 2. STAFF PERSONAL VIEW - See only their assignments

class StaffPersonalDashboardView(StaffRequiredMixin, LoginRequiredMixin, View):
    login_url = 'staff:staff_login'
    template_name = 'staff/my_dashboard.html'

    def get(self, request):
        staff, created = Staff.objects.get_or_create(
            user=request.user,
            defaults={
                'name': request.user.get_full_name() or request.user.username,
                'email': request.user.email
            }
        )
        
        assignments = staff.assignments.filter(
            event__start_time__gte=timezone.now(), 
            status__in=['assigned', 'accepted'] # Show both
        ).select_related('event', 'role').order_by('event__start_time')
        
        notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:10]
        
        flag_rules = getattr(staff, 'flag_rules', None)
        if flag_rules: flag_rules = flag_rules.all()
        
        interview_slots = getattr(staff, 'interview_slots', None) 
        if interview_slots: interview_slots = interview_slots.all()
        
        context = {
            'staff': staff,
            'assignments': assignments,
            'assigned_count': assignments.count(),
            'notifications': notifications,
            'unread_count': notifications.count(),
            'reliability_score': staff.reliability_score or 0,
            'chart_labels': json.dumps(['Week 1', 'Week 2', 'Week 3', 'Week 4']),
            'chart_data': json.dumps([85, 90, 88, staff.reliability_score or 0]),
            'flag_rules': flag_rules,
            'interview_slots': interview_slots,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        action = request.POST.get('action')
        staff = request.user.staff
        
        if action == 'accept':
            assignment_id = request.POST.get('assignment_id')
            assignment = get_object_or_404(Assignment, pk=assignment_id, staff=staff)
            assignment.status = 'accepted'
            assignment.save()
            update_reliability_score(staff)
            messages.success(request, f"You accepted {assignment.event.title}")
            
        elif action == 'decline':
            assignment_id = request.POST.get('assignment_id')
            assignment = get_object_or_404(Assignment, pk=assignment_id, staff=staff)
            assignment.status = 'declined'
            assignment.save()
            update_reliability_score(staff)
            messages.warning(request, f"You declined {assignment.event.title}")
            
        elif action == 'mark_read':
            notification_id = request.POST.get('notification_id')
            notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            
        elif action == 'mark_all_read':
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            messages.success(request, "All notifications marked as read")
        
        return redirect('staff:my_dashboard')

class RiskDashboardView(StaffRequiredMixin, View):
    def get(self, request):
        """
        Dashboard focused on staffing risks: critical, warning, and empty duties
        """
        today = timezone.now().date()

        # Stats cards
        stats = {
            'total_events': Event.objects.count(),
            'upcoming': Event.objects.filter(start_time__date__gte=today).count(),
            'critical_duties': 0,
            'warning_duties': 0,
            'empty_duties': 0,
        }

        risky_events = []
        events = Event.objects.filter(start_time__date__gte=today).prefetch_related(
            'assignments__staff',
            'assignments__role'
        ).order_by('start_time')

        for event in events:
            event_critical = 0
            event_warning = 0
            event_empty = 0
            duties = []
            
            assignments = event.assignments.filter(status='assigned')
            assigned_staff_ids = assignments.values_list('staff_id', flat=True)

            for a in assignments:
                if a.staff is None:
                    status = 'empty'
                    score = 0
                    event_empty += 1
                    stats['empty_duties'] += 1
                else:
                    score = getattr(a.staff, 'reliability_score', 100)
                    if score < 50:
                        status = 'critical'
                        event_critical += 1
                        stats['critical_duties'] += 1
                    elif score < 75:
                        status = 'warning'
                        event_warning += 1
                        stats['warning_duties'] += 1
                    else:
                        status = 'ok'

                if a.role:
                    replacements = Staff.objects.filter(
                        role=a.role,
                        is_active=True,
                        reliability_score__gte=90
                    ).exclude(id__in=assigned_staff_ids).order_by('-reliability_score')[:3]
                else:
                    replacements = Staff.objects.none()

                # Only add risky duties to the list
                if status in ['critical', 'warning', 'empty']:
                    duties.append({
                        'assignment_id': a.id,
                        'index': a.duty_number,
                        'staff': a.staff.name if a.staff else 'UNASSIGNED',
                        'role': a.role.name if a.role else 'No Role',
                        'score': score,
                        'status': status,
                        'candidates': replacements
                    })

            # Only show events that actually have risks
            if duties:
                risky_events.append({
                    'id': event.id,
                    'title': event.title,
                    'date': event.start_time,
                    'location': event.location,
                    'duties': duties,
                    'critical_count': event_critical,
                    'warning_count': event_warning,
                    'empty_count': event_empty,
                })

        context = {
            'stats': stats,
            'risky_events': risky_events,
        }
        return render(request, 'staff/risk_dashboard.html', context)

class HRLeaveListView(LoginRequiredMixin, View):
    login_url = 'staff:staff_login'
    template_name = 'staff/hr_leave_list.html'

    def get(self, request):
        # Only HR/Admin should see this. We'll add permission later
        leave_requests = LeaveRequest.objects.filter(status='pending').select_related('staff')
        return render(request, self.template_name, {'leave_requests': leave_requests})
    
class HRLeaveDetailView(LoginRequiredMixin, View):
    login_url = 'staff:staff_login'
    template_name = 'staff/hr_leave_detail.html'

    def get(self, request, pk):
        leave = get_object_or_404(LeaveRequest, pk=pk)
        return render(request, self.template_name, {'leave': leave})

    def post(self, request, pk):
        leave = get_object_or_404(LeaveRequest, pk=pk)
        action = request.POST.get('action') # 'approve' or 'reject'
        notes = request.POST.get('approval_notes', '')

        if leave.status != 'pending':
            messages.error(request, "This request has already been processed")
            return redirect('staff:hr_leave_list')

        if action == 'approve':
            # 1. Calculate number of days
            delta = leave.end_date - leave.start_date
            days_requested = delta.days + 1 # +1 because both start and end day count

            staff = leave.staff
            can_approve = False

            # 2. Check balance and deduct
            if leave.leave_type == 'annual':
                if staff.annual_leave_balance >= days_requested:
                    staff.annual_leave_balance -= days_requested
                    can_approve = True
                else:
                    messages.error(request, f"Not enough Annual Leave. Has {staff.annual_leave_balance} days")
            
            elif leave.leave_type == 'sick':
                if staff.sick_leave_balance >= days_requested:
                    staff.sick_leave_balance -= days_requested
                    can_approve = True
                else:
                    messages.error(request, f"Not enough Sick Leave. Has {staff.sick_leave_balance} days")

            elif leave.leave_type == 'casual':
                if staff.casual_leave_balance >= days_requested:
                    staff.casual_leave_balance -= days_requested
                    can_approve = True
                else:
                    messages.error(request, f"Not enough Casual Leave. Has {staff.casual_leave_balance} days")
            
            if can_approve:
                staff.save() # Save the new balance
                leave.status = 'approved'
                messages.success(request, f"Leave approved. {days_requested} days deducted.")
            else:
                return redirect('staff:hr_leave_detail', pk=pk) # Go back if not enough balance

        elif action == 'reject':
            leave.status = 'rejected'
            messages.success(request, "Leave request rejected")

        # 3. Save approval details
        leave.approved_by = request.user
        leave.approval_notes = notes
        leave.approved_at = timezone.now()
        leave.save()

        return redirect('staff:hr_leave_list')


# 6. ASSIGNMENTS

@method_decorator(staff_member_required, name='dispatch')
class AssignmentListView(ListView):
    model = Assignment
    template_name = 'staff/assignment_list.html'
    context_object_name = 'assignments'

    def get_queryset(self):
        event_id = self.kwargs['event_id']
        return Assignment.objects.filter(event_id=event_id).select_related('staff', 'role')

@require_POST
@csrf_exempt
@login_required(login_url='staff:staff_login')
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
        staff_obj = get_object_or_404(Staff, id=staff_id)
        assignment = Assignment.objects.create(
            event=event,
            staff=staff_obj,
            duty_number=duty_number,
            role=role_obj, # pass Role object
            status='assigned'
        )

        Notification.objects.create(
            user=staff_obj.user,
            sender=request.user,
            sender_type='staff',
            message=f'You have been assigned to: {event.title} as {role_obj.name}',
            notification_type='assignment',
            related_event=event
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
@csrf_exempt
@login_required(login_url='staff:staff_login')
def reassign_assignment(request, assignment_id):
    try:
        data = json.loads(request.body)
        new_staff_id = data.get('new_staff_id')
        reason = data.get('reason', '').strip()

        assignment = get_object_or_404(Assignment, id=assignment_id)
        new_staff_obj = get_object_or_404(Staff, id=new_staff_id) 
        old_staff_name = assignment.staff.name if assignment.staff else 'Empty'

        # 1. Check if new staff already on this event
        if assignment.event.assignments.filter(staff_id=new_staff_id, status__in=['assigned', 'accepted']).exists():
            return JsonResponse({'success': False, 'error': 'Staff already assigned to this event'}, status=400)

        # 2. Check if new staff busy at this time
        is_busy = Assignment.objects.filter(
            staff=new_staff_obj,
            status__in=['assigned', 'accepted'],
            event__start_time__lt=assignment.event.end_time,
            event__end_time__gt=assignment.event.start_time
        ).exists()
        if is_busy:
            return JsonResponse({'success': False, 'error': f'{new_staff_obj.name} is busy at this time'}, status=400)

        # 3. UPDATE in place
        assignment.staff = new_staff_obj
        assignment.status = 'assigned' # reset status
        assignment.reassigned_at = timezone.now()
        assignment.reassigned_by = request.user
        assignment.reassignment_reason = reason
        assignment.save()

        # 4. Notify new staff
        Notification.objects.create(
            user=new_staff_obj.user,
            sender=request.user,
            sender_type='staff',
            message=f'You have been assigned to: {assignment.event.title} as {assignment.role.name} - Duty {assignment.duty_number}',
            notification_type='assignment',
            related_event=assignment.event,
            related_assignment=assignment
        )
        
        return JsonResponse({
            'success': True,
            'new_staff': assignment.staff.name,
            'new_score': assignment.staff.reliability_score
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_POST
@login_required(login_url='staff:staff_login')
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

    # NEW BLOCK
    Notification.objects.create(
        user=new_staff.user,
        sender=request.user,
        sender_type='staff',
        message=f'You have replaced {old_staff_name} on: {assignment.event.title} - Duty {assignment.duty_number}',
        notification_type='assignment',
        related_event=assignment.event,
        related_assignment=assignment
    )

    return JsonResponse({
        'success': True,
        'new_staff': new_staff.name,
        'new_score': new_staff.reliability_score
    })

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

def _send_manager_notification(sender_user, assignment, action_emoji, action_text):
    """Helper so we don't repeat code"""
    print(f"***** NOTIFICATION FUNCTION CALLED *****") 
    staff_name = getattr(sender_user, 'staff', None)
    staff_name = staff_name.name if staff_name else sender_user.username
    print(f"Staff: {staff_name}")
    
    managers = User.objects.filter(Q(is_manager=True) | Q(is_superuser=True)).distinct()
    print(f"Managers found: {managers.count()} - {[m.username for m in managers]}")
    
    for manager in managers:
        if getattr(manager, 'is_manager', False) or manager.is_superuser:
            print(f"Creating for: {manager.username}")
            Notification.objects.create(
                user=manager,
                sender=sender_user,
                sender_type='staff',
                message=f"{action_emoji} {staff_name} {action_text}: {assignment.event.title} - Duty {assignment.duty_number}",
                notification_type='assignment_response',
                related_event=assignment.event,
                related_assignment=assignment
            )
    print(f"***** NOTIFICATION FUNCTION DONE *****")

@login_required(login_url='staff:staff_login')
def decline_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk, staff__user=request.user)
    
    if assignment.status == 'declined':
        messages.warning(request, "You already declined this duty")
        return redirect('staff:my_dashboard')
        
    assignment.status = 'declined'
    assignment.assigned_to = None # free the slot
    assignment.save()
    
    _send_manager_notification(request.user, assignment, "❌", "DECLINED")
        
    messages.warning(request, "Duty declined. Manager has been notified.")
    return redirect('staff:my_dashboard')

@login_required(login_url='staff:staff_login')
def accept_assignment(request, pk):
    print(f"*** ACCEPT VIEW HIT FOR PK={pk} ***")  # ADD THIS LINE
    assignment = get_object_or_404(Assignment, pk=pk, staff__user=request.user)
    if assignment.status == 'accepted':
        messages.warning(request, "You already accepted this duty")
        return redirect('staff:my_dashboard')
        
    assignment.status = 'accepted'
    assignment.save()
    
    _send_manager_notification(request.user, assignment, "✅", "ACCEPTED")
        
    messages.success(request, "Duty accepted! Manager has been notified.")
    return redirect('staff:my_dashboard')

# 7. RECRUITMENT VIEWS
    
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
class RecruitmentCreateView(LoginRequiredMixin, CreateView):
    model = Recruitment
    form_class = RecruitmentForm
    template_name = 'staff/recruitment_form.html'
    success_url = reverse_lazy('staff:recruitment_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Recruitment created.")
        return super().form_valid(form)

@method_decorator(staff_member_required, name='dispatch')
class RecruitmentUpdateView(UpdateView):
    model = Recruitment
    form_class = RecruitmentForm
    template_name = 'staff/recruitment_form.html'
    success_url = reverse_lazy('staff:recruitment_list')

    def form_valid(self, form):
        messages.success(self.request, "Recruitment updated.")
        return super().form_valid(form)

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
class RecruitmentApplicantsView(ListView):
    model = Applicant
    template_name = 'staff/recruitment_applicants.html'
    context_object_name = 'applicants'

    def get_queryset(self):
        return Applicant.objects.filter(recruitment_id=self.kwargs['recruitment_id'])

class ExportApplicantsCSVView(View):
    def get(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        applicants = recruitment.applicants.all() # FIXED

        # Apply filters from query params
        status = request.GET.get('status')
        if status:
            applicants = applicants.filter(status=status)
        
        name_search = request.GET.get('name')
        if name_search:
            applicants = applicants.filter(name__icontains=name_search)

        safe_position = "".join(c if c.isalnum() else "_" for c in recruitment.position) # FIXED
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
                applicant.applied_at.strftime('%Y-%m-%d %H:%M') if applicant.applied_at else '', # was created_at
            ])
        return response

class SendEmailToApplicantsView(View):
    def get(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        applicants = recruitment.applicants.all() # FIXED
        return render(request, 'staff/send_emails.html', {
            'recruitment': recruitment,
            'applicants': applicants,
            'total': applicants.count()
        })
    
    def post(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        applicants = recruitment.applicants.all() # FIXED

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
                    subject=f'Interview Invitation - {recruitment.position}', # FIXED
                    message=f'Dear {applicant.name},\n\nYou are invited for an interview for the position of {recruitment.position} you applied for. Please reply to this email to schedule your interview.\n\nBest regards,\nCatering Team', # FIXED
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[applicant.email],
                    fail_silently=False
                )
                logger.info(f'Email sent to {applicant.email} for recruitment {recruitment_id}')
                emails_sent += 1
            except Exception as e:
                logger.error(f'Error sending email to {applicant.name} for recruitment {recruitment.position}: {str(e)}') # FIXED
                errors.append(f'Error sending email to {applicant.name}: {str(e)}')

        if errors:
            for err in errors:
                messages.error(request, err)
        if emails_sent:
            messages.success(request, f'Successfully sent {emails_sent} emails.')
        
        return redirect('staff:recruitment_detail', pk=recruitment_id)

class ScheduleInterviewsView(View):
    def get(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        applicants = recruitment.applicants.all() # FIXED
        return render(request, 'staff/schedule_interviews.html', {'recruitment': recruitment, 'applicants': applicants, 'errors':[]})
    
    def post(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        all_applicants = recruitment.applicants.all() # FIXED
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
        return render(request, 'staff/interviews_schedule.html', {'recruitment': recruitment, 'scheduled_applicants': scheduled_applicants})

@method_decorator(staff_member_required, name='dispatch')
class ManageInterviewSlotsView(View):
    def get(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        applicants = recruitment.applicants.all()
        existing_slots = recruitment.slots.select_related('applicant') # get existing ones too

        InterviewSlotFormSet = modelformset_factory(
            InterviewSlot,
            form=InterviewSlotForm,
            extra=max(0, len(applicants) - existing_slots.count()), # only show empty forms for unassigned applicants
            can_delete=True # <- ADD THIS for delete
        )

        # Load existing slots + empty ones
        formset = InterviewSlotFormSet(queryset=existing_slots)

        return render(request, 'staff/manage_slots.html', {
           'recruitment': recruitment,
           'formset': formset,
           'applicants_forms': zip(applicants, formset.forms)
        })

    def post(self, request, recruitment_id):
        recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
        applicants = list(recruitment.applicants.all()) # cast to list so we can index
        existing_slots = recruitment.slots.all()

        InterviewSlotFormSet = modelformset_factory(
            InterviewSlot,
            form=InterviewSlotForm,
            extra=max(0, len(applicants) - existing_slots.count()),
            can_delete=True
        )

        formset = InterviewSlotFormSet(request.POST, queryset=existing_slots)

        if formset.is_valid():
            instances = formset.save(commit=False)
            
            # Track which applicants are already assigned
            assigned_applicant_ids = {s.applicant_id for s in existing_slots if s.applicant_id}
            applicant_idx = 0

            for instance in instances:
                if instance._state.adding: # new slot
                    # find next unassigned applicant
                    while applicant_idx < len(applicants) and applicants[applicant_idx].id in assigned_applicant_ids:
                        applicant_idx += 1
                    if applicant_idx < len(applicants):
                        instance.applicant = applicants[applicant_idx]
                        applicant_idx += 1
                
                instance.recruitment = recruitment
                instance.save()
            
            # Handle deletions
            for obj in formset.deleted_objects:
                obj.delete()
                
            messages.success(request, "Interview slots updated.")
            return redirect('staff:recruitment_detail', pk=recruitment_id)

        # If invalid, re-render with errors
        return render(request, 'staff/manage_slots.html', {
           'recruitment': recruitment,
           'formset': formset,
           'applicants_forms': zip(applicants, formset.forms)
        })

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
        return reverse_lazy('staff:recruitment_applicants', kwargs={'recruitment_id': self.kwargs['recruitment_id']})
    
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

# 8. ROLEPLAY / TRAINING VIEWS

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
class RolePlayCreateView(CreateView):
    model = RolePlay
    form_class = RolePlayForm
    template_name = 'staff/role_play_form.html'
    success_url = reverse_lazy('staff:role_play_list')

@method_decorator(staff_member_required, name='dispatch')
class RolePlayUpdateView(UpdateView):
    model = RolePlay
    form_class = RolePlayForm
    template_name = 'staff/role_play_form.html'
    success_url = reverse_lazy('staff:role_play_list')

@method_decorator(staff_member_required, name='dispatch')
class RolePlayDeleteView(DeleteView):
    model = RolePlay
    template_name = 'staff/role_play_confirm_delete.html'
    success_url = reverse_lazy('staff:role_play_list')

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

# 9. MISC: TASKS, MEETINGS, EXPENSES

@method_decorator(staff_member_required, name='dispatch')
class TaskListView(ListView):
    model = Task
    template_name = 'staff/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 20

    def get_queryset(self):
        return Task.objects.all()

class SuccessView(TemplateView):
    template_name = 'staff/success.html'
    
def reset_admin(request):
    from django.contrib.auth.models import User
    from django.http import HttpResponse
    
    # If admin exists, update it. If not, create it
    user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'is_staff': True,
            'is_superuser': True
        }
    )
    user.set_password('admin123')
    user.is_staff = True
    user.is_superuser = True
    user.save()
    
    if created:
        return HttpResponse("✅ Admin CREATED. Username: admin, Password: admin123. DELETE THIS VIEW AFTER TESTING")
    else:
        return HttpResponse("✅ Admin UPDATED. Username: admin, Password: admin123. DELETE THIS VIEW AFTER TESTING")


# NOTIFICATIONS

class NotificationListView(LoginRequiredMixin, ListView):
    login_url = 'staff:staff_login'
    model = Notification
    template_name = 'staff/notifications_list.html'
    context_object_name = 'notifications'

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user).order_by('-created_at')
        status = self.request.GET.get('status')
        if status == 'unread':
            qs = qs.filter(is_read=False)
        elif status == 'read':
            qs = qs.filter(is_read=True)
        elif status == 'accepted':
            qs = qs.filter(action_response__in=['accept', 'accept_action'])
        elif status == 'rejected':
            qs = qs.filter(action_response__in=['reject', 'reject_action'])
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status'] = self.request.GET.get('status', 'all')
        return context

class MarkNotificationReadView(LoginRequiredMixin, View):
    login_url = 'staff:staff_login' 
    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.mark_as_read(request.user)
        return JsonResponse({'success': True})

class RespondNotificationView(LoginRequiredMixin, View):
    login_url = 'staff:staff_login' 
    def post(self, request, pk, action):
        notification = get_object_or_404(Notification, pk=pk, user=request.user, requires_action=True)
        if action in ['accept', 'reject']:
            notification.respond_to_action(action, user=request.user) # use the model method
        return redirect('staff:notifications_list')

# ... all your CBVs above

@staff_member_required
def mark_all_notifications_read(request): 
    updated = Notification.objects.filter(user=request.user, is_read=False).update(
        is_read=True, 
        read_at=timezone.now()
    )
    messages.success(request, f"{updated} notifications marked as read")
    return redirect('staff:notifications_list')

# ===== APPLICANT ACTIONS =====


@login_required(login_url='staff:staff_login')
def accept_interview(request, slot_id):
    slot = get_object_or_404(InterviewSlot, id=slot_id)
    
    # Find applicant by email
    try:
        applicant = Applicant.objects.get(email=request.user.email, recruitment=slot.recruitment)
    except Applicant.DoesNotExist:
        messages.error(request, "No application found for you for this recruitment")
        return redirect('staff:my_dashboard')

    # security: only claim empty slots
    if slot.applicant and slot.applicant != applicant:
        messages.error(request, "This slot is already taken")
        return redirect('staff:my_dashboard')
        
    slot.applicant = applicant
    slot.save()
    messages.success(request, f"You accepted the interview for {slot.date} at {slot.start_time}")
    return redirect('staff:my_dashboard')


@login_required(login_url='staff:staff_login')
def decline_interview(request, slot_id):
    slot = get_object_or_404(InterviewSlot, id=slot_id)
    try:
        applicant = Applicant.objects.get(email=request.user.email, recruitment=slot.recruitment)
    except Applicant.DoesNotExist:
        messages.error(request, "No application found for you")
        return redirect('staff:my_dashboard')
    
    if slot.applicant == applicant:
        slot.applicant = None
        slot.save()
        messages.info(request, f"You declined the interview for {slot.date} at {slot.start_time}")
    return redirect('staff:my_dashboard')