from django.db.models import Sum
try: 
    from django.conf import settings  # type: ignore[import]
except ImportError:  # fallback for static analysis or missing Django in environment
    settings = None
try:
    from django.db import models  # type: ignore[import]
except ImportError:
    models = None
try:
    from django.db.models.signals import post_save, post_delete  # type: ignore[import]
except ImportError:
    post_save = None
    post_delete = None
try:
    from django.dispatch import receiver  # type: ignore[import]
except ImportError:
    receiver = None
try:
    from django.contrib.auth.models import User  # type: ignore[import]
except ImportError:
    User = None
try:
    from django.urls import reverse_lazy  # type: ignore[import]
except ImportError:
    reverse_lazy = None
try:
    from django.utils import timezone  # type: ignore[import]
except ImportError:
    timezone = None
from .fields import EncryptedCharField, EncryptedTextField
from django import forms
from django.core.exceptions import ValidationError


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name
    

class Recruitment(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('draft', 'Draft'), # added this - useful before publishing
    ]

    event = models.ForeignKey('Event', on_delete=models.SET_NULL, null=True, blank=True, related_name='recruitments')
    position = models.CharField(max_length=100)
    title = models.CharField(max_length=255) # you can keep both, or make title = position
    description = models.TextField()
    requirements = models.TextField()
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        default='open'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"

    @property
    def is_active(self):
        from django.utils import timezone
        if self.status != 'open':
            return False
        if self.deadline and self.deadline < timezone.now():
            return False
        return True
    
class Staff(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, blank=True, null=True)
    phone = EncryptedCharField(max_length=255)
    whatsapp = EncryptedCharField(max_length=255)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Add these 4 new fields:
    address = EncryptedTextField(max_length=355)
    next_of_kin = EncryptedCharField(max_length=255)
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = EncryptedCharField(max_length=255)
    reliability_score = models.IntegerField(default=100, help_text="Reliability score 0-100")
    reliability_notes = models.TextField(blank=True, null=True)
    APPROVAL_REQUIRED_FIELDS = ['address', 'next_of_kin', 'emergency_contact_name', 'emergency_contact_phone']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        if self.pk and user:
            try:
                old = Staff.objects.get(pk=self.pk)
                for field in self.APPROVAL_REQUIRED_FIELDS:
                    old_value = getattr(old, field)
                    new_value = getattr(self, field)
                    if old_value != new_value:
                        StaffUpdateRequest.objects.create(
                            staff=self,
                            requested_by=user,
                            request_reason=f"Change {field}",
                            field_name=field,
                            old_value=old_value,
                            new_value=new_value
                        )
            except Exception as e:
                print(f"Error creating update request: {e}")
        super().save(*args, **kwargs)
              

    def update_reliability_score(self) -> None: #noqa: F401
        penalty = self.incidents.filter(
            resolved=False,
            issue_type__counts_against_staff=True
        ).aggregate(total=Sum('issue_type__weight_percent'))['total'] or 0
    
        self.reliability_score = max(0, 100 - min(penalty, 100))
        self.save(update_fields=['reliability_score'])

class InterviewSlot(models.Model):
    recruitment = models.ForeignKey(Recruitment, on_delete=models.CASCADE, related_name='slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    capacity = models.PositiveIntegerField(default=1)
    interviewer = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='slots')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def booked_count(self):
        return self.applicants.count()
    
    @property
    def available(self):
        return max(0, self.capacity - self.booked_count)

    def __str__(self):
        return f"{self.recruitment.title} - {self.date} {self.start_time}-{self.end_time}"

class Applicant(models.Model):
    STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('interviewed', 'Interviewed'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
    ]

    recruitment = models.ForeignKey(Recruitment, on_delete=models.CASCADE, related_name='applicants')
    slot = models.ForeignKey(InterviewSlot, on_delete=models.SET_NULL, null=True, blank=True, related_name='applicants')
    
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    cover_letter = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    
    interview_time = models.DateTimeField(null=True, blank=True) # <-- new field

    def __str__(self):
        return f"{self.name} ({self.email})"
    
    @property
    def is_interviewed(self):
        return self.interviews.exists()
    
class Interview(models.Model):
    INTERVIEW_TYPES = [
        ('written', 'Written'), 
        ('role_play', 'Role Play')
    ]
    
    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE, related_name='interviews')
    slot = models.ForeignKey(InterviewSlot, on_delete=models.SET_NULL, null=True, blank=True) # link result back to slot
    date = models.DateTimeField()
    interview_type = models.CharField(max_length=20, choices=INTERVIEW_TYPES)
    score = models.IntegerField(blank=True, null=True)
    notes = models.TextField(blank=True)
    interviewers = models.ManyToManyField(Staff, related_name='interviews_conducted')
    
    def __str__(self):
        return f"{self.applicant.name} - {self.date:%Y-%m-%d} - {self.interview_type}"

class ApplicationStatus(models.Model):
    STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('interviewed', 'Interviewed'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.status

class StaffUpdateLog(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='update_logs')
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    field_name = models.CharField(max_length=50)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Staff Update Log"
        verbose_name_plural = "Staff Update Logs"

    def __str__(self):
        return f"{self.staff.name} - {self.field_name} changed at {self.timestamp:%Y-%m-%d %H:%M}"
    
class StaffUpdateRequest(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='update_requests')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    request_reason = models.TextField(blank=True, null=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    field_name = models.CharField(max_length=50)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)

    class Meta:
        ordering = ['-requested_at']
        verbose_name = "Staff Update Request"
        verbose_name_plural = "Staff Update Requests"

    def __str__(self):
        return f"{self.staff.name} - {self.field_name} update requested at {self.requested_at:%Y-%m-%d %H:%M}"

class StaffUpdateApproval(models.Model):
    update_request = models.OneToOneField(StaffUpdateRequest, on_delete=models.CASCADE, related_name='approval')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Staff Update Approval"
        verbose_name_plural = "Staff Update Approvals"

    def __str__(self):
        return f"{self.update_request.staff.name} - {self.update_request.field_name} update approved at {self.approved_at:%Y-%m-%d %H:%M}"

class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True)
    client_name = models.CharField(max_length=255, blank=True)
    template = models.ForeignKey('EventTemplate', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        if self.start_time:
            return f"{self.title} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"
        return f"{self.title} - No Date Set"
    
class IssueType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    weight_percent = models.PositiveIntegerField(default=10)
    counts_against_staff = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Issue Types"
    
    def __str__(self):
        return f"{self.name} - {self.weight_percent}%"
    
class Incident(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='incidents')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True)
    issue_type = models.ForeignKey(IssueType, on_delete=models.PROTECT)
    resolved = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    reported_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.staff.name} - {self.issue_type.name}"

@receiver([post_save, post_delete], sender=Incident)
def update_staff_score_on_incident_change(sender, instance, **kwargs):
    instance.staff.update_reliability_score()
    
class EventTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    default_location = models.CharField(max_length=255, blank=True)
    default_duration_hours = models.PositiveIntegerField(default=1, help_text="Default duration in hours")
    required_staff_count = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True, help_text="Internal notes for staff")

    def create_event_with_assignments(self, start_time, **kwargs):
        event = Event.objects.create(start_time=start_time, template=self, **kwargs)
        for tr in self.template_roles.all():
            for i in range(tr.count):
                Assignment.objects.create(event=event, role=tr.role, duty_number=i+1)
        return event

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class EventTemplateRole(models.Model):
    template = models.ForeignKey(EventTemplate, related_name='template_roles', on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    count = models.PositiveIntegerField(default=1, blank=True)

    class Meta:
        unique_together = ('template', 'role')
        ordering = ['role__name']

    def __str__(self):
        return f"{self.template.name}: {self.count} x {self.role.name}"

    def clean(self):
        if self.count < 1:
            raise ValidationError({'count': 'Count must be at least 1.'})

class Task(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey('Staff', on_delete=models.SET_NULL, null=True, blank=True)
    due_date = models.DateTimeField(blank=True, null=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.assigned_to.name if self.assigned_to else 'Unassigned'} - {self.get_status_display()}"
    
    class Meta:
        ordering = ['-created_at', 'due_date']
        verbose_name_plural = "Tasks"

class Assignment(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='assignments', null=True, blank=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='assignments')
    duty_number = models.PositiveIntegerField(help_text="Duty slot: 1, 2, 3...")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, help_text="Role for this event")
    
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('dropped', 'Dropped'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    
    date_assigned = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    reassignment_reason = models.CharField(max_length=255, blank=True, null=True)
    reassigned_at = models.DateTimeField(blank=True, null=True)
    reassigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['event', 'duty_number', 'status'],
                name='unique_assignment_per_duty_status'
            )
        ]
        ordering = ['event', 'date_assigned', 'duty_number']
        verbose_name_plural = "Assignments"

    def __str__(self):
        staff_name = self.staff.name if self.staff else "Unassigned"
        event_title = self.event.title if self.event else "No Event"
        return f"Duty {self.duty_number}: {staff_name} @ {event_title} [{self.status}]"
    
class Meeting(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True)
    attendees = models.ManyToManyField('Staff', related_name='meetings')
    meeting_link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        ordering = ['start_time']
        verbose_name_plural = "Meetings"

class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('transport', 'Transport'),
        ('accommodation', 'Accommodation'),
        ('supplies', 'Supplies'),
        ('meals', 'Meals'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='expenses')
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    receipt = models.FileField(upload_to='expense_receipts/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    approval_notes = models.TextField(blank=True, null=True, help_text="Optional notes for approval/rejection")
    
    def __str__(self):
        return f"{self.title} - {self.get_category_display()} - {self.get_status_display()}: {self.amount}"
    
    class Meta:
        ordering = ['-submitted_at']
        verbose_name_plural = "Expenses"

class RolePlay(models.Model):
    scenario = models.TextField()
    role = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField()
    expected_outcome = models.TextField()

    def __str__(self):
        return f"{self.role}: {self.scenario[:50]}..."

class RolePlayResponse(models.Model):
    """Staff responses to roleplay scenarios"""
    roleplay = models.ForeignKey(RolePlay, on_delete=models.CASCADE, related_name='responses')
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='roleplay_responses')
    action = models.TextField(help_text="What the staff member said/did")
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-submitted_at']
        verbose_name = "Role Play Response"
        verbose_name_plural = "Role Play Responses"

    def __str__(self):
        return f"{self.staff.name} - {self.roleplay.role} @ {self.submitted_at:%Y-%m-%d %H:%M}"

class ApplicantRolePlay(models.Model):
    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE)
    role_play = models.ForeignKey(RolePlay, on_delete=models.CASCADE)
    score = models.IntegerField(null=True, blank=True)

class LeaveRequest(models.Model):
    LEAVE_TYPE_CHOICES = [
        ('annual', 'Annual Leave'),
        ('sick', 'Sick Leave'),
        ('maternity', 'Maternity Leave'),
        ('paternity', 'Paternity Leave'),
        ('unpaid', 'Unpaid Leave'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=15, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    approval_notes = models.TextField(blank=True, null=True, help_text="Notes from approver")
    approved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.staff.name} - {self.leave_type} {self.start_date} to {self.end_date} [{self.status}]"
    
    class Meta:
        ordering = ['-submitted_at']
    