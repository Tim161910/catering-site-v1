from django.db.models import Sum
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError

from .fields import EncryptedCharField, EncryptedTextField

# CORE / UTILS

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name
    
# EVENTS

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

# STAFF

class Staff(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, blank=True, null=True)
    phone = EncryptedCharField(max_length=255)
    whatsapp = EncryptedCharField(max_length=255)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    address = EncryptedTextField(max_length=355)
    next_of_kin = EncryptedCharField(max_length=255)
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = EncryptedCharField(max_length=255)
    
    reliability_score = models.IntegerField(default=100, help_text="Reliability score 0-100")
    reliability_notes = models.TextField(blank=True, null=True)

    # NEW: Leave balances
    annual_leave_balance = models.PositiveIntegerField(default=20)
    sick_leave_balance = models.PositiveIntegerField(default=10)
    casual_leave_balance = models.PositiveIntegerField(default=5)
    
    APPROVAL_REQUIRED_FIELDS = ['address', 'next_of_kin', 'emergency_contact_name', 'emergency_contact_phone']
    DIRECT_UPDATE_FIELDS = ['name', 'email', 'phone', 'whatsapp', 'role', 'is_active']

    def __str__(self):
        return self.name

    def update_reliability_score(self) -> None:
        penalty = self.incidents.filter(
            resolved=False,
            issue_type__counts_against_staff=True
        ).aggregate(total=Sum('issue_type__weight_percent'))['total'] or 0
        self.reliability_score = max(0, 100 - min(penalty, 100))
        self.save(update_fields=['reliability_score'])

# ADD MANAGER FLAG TO DEFAULT USER
User.add_to_class('is_manager', models.BooleanField(default=False))

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

    # THESE 3 MUST BE OUTSIDE Meta, INDENTED TO MATCH __str__
    @property
    def type(self):
        return self.get_leave_type_display()  # shows "Annual Leave" instead of "annual"

    @property 
    def from_date(self):
        return self.start_date

    @property
    def to_date(self):
        return self.end_date

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

# RELIABILITY

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
    
    incident_type = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. Late, No-Show, Uniform")
    reliability_impact = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. Low, Medium, High")
    notes = models.TextField(blank=True, null=True)
    
    resolved = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    reported_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.staff.name} - {self.issue_type.name}"

@receiver([post_save, post_delete], sender=Incident)
def update_staff_score_on_incident_change(sender, instance, **kwargs):
    instance.staff.update_reliability_score()
    
    # Import here to avoid circular import
    from .services import evaluate_rules
    evaluate_rules(instance.staff, instance) # pass incident

class Rule(models.Model):
    RULE_TYPES = (
        ('date', 'Date-based'),
        ('issue_type', 'Issue Type Count'),
        ('reliability', 'Reliability Score'),
    )
    name = models.CharField(max_length=100, help_text="e.g. 2 Late incidents in 30 days")
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    issue_type = models.ForeignKey(IssueType, on_delete=models.CASCADE, null=True, blank=True, help_text="Only for Issue Type rules")
    days = models.PositiveIntegerField(null=True, blank=True, help_text="Lookback window in days")
    min_reliability_score = models.PositiveIntegerField(null=True, blank=True, help_text="For reliability rules")
    threshold = models.IntegerField(default=1, help_text="Number of incidents to trigger")
    action = models.CharField(max_length=255, help_text="e.g. 'Flag for review'")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Rule"
        verbose_name_plural = "Rules"
        ordering = ['name']

    def __str__(self):
        return self.name

class Flag(models.Model):
    FLAG_LEVELS = (
        (1, 'Warning'),
        (2, 'Critical'),
    )
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='flags')
    rule = models.ForeignKey(Rule, on_delete=models.CASCADE, related_name='flags')
    incident = models.ForeignKey(Incident, on_delete=models.SET_NULL, null=True, blank=True, related_name='flags')
    flag_level = models.IntegerField(choices=FLAG_LEVELS, default=1)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_triggered = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('staff', 'rule')
        verbose_name = "Flag"
        verbose_name_plural = "Flags"
        ordering = ['-last_triggered']

    def __str__(self):
        return f"{self.staff.name} - {self.rule.name} - {self.get_flag_level_display()}"

# ASSIGNMENTS

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

# RECRUITMENT

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

class InterviewSlot(models.Model):
    recruitment = models.ForeignKey(Recruitment, on_delete=models.CASCADE, related_name='slots')
    applicant = models.ForeignKey('Applicant', on_delete=models.CASCADE, null=True, blank=True, related_name='interview_slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    capacity = models.PositiveIntegerField(default=1)
    interviewer = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='slots')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def booked_count(self):
        return 1 if self.applicant else 0
    
    @property
    def available(self):
        return max(0, self.capacity - self.booked_count)

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time")

    def __str__(self):
        applicant_name = self.applicant.name if self.applicant else "Unassigned"
        return f"{self.recruitment.title} - {self.date} {self.start_time}-{self.end_time} - {applicant_name}"

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

class RolePlay(models.Model):
    scenario = models.TextField()
    role = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField()
    expected_outcome = models.TextField()

    def __str__(self):
        return f"{self.role}: {self.scenario[:50]}..."

class ApplicantRolePlay(models.Model):
    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE)
    role_play = models.ForeignKey(RolePlay, on_delete=models.CASCADE)
    score = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.applicant.name} - {self.role_play.role}"
    
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

# MISC

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

from django.conf import settings # <- make sure this import is at top


# NOTIFICATIONS

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('assignment', 'Assignment'),
        ('incident', 'Incident'),
        ('leave', 'Leave'),
        ('general', 'General'),
    ]

    ACTION_CHOICES = [
        ('accept', 'Accept'),
        ('reject', 'Reject'),
        ('accept_action', 'Accept Action'),
        ('reject_action', 'Reject Action'),
    ]

    SENDER_TYPE_CHOICES = [
        ('staff', 'Staff'), 
        ('admin', 'Admin')
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_notifications')
    sender_type = models.CharField(max_length=10, choices=SENDER_TYPE_CHOICES)

    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='general')
    related_event = models.ForeignKey('Event', on_delete=models.CASCADE, null=True, blank=True)
    related_assignment = models.ForeignKey('Assignment', on_delete=models.CASCADE, null=True, blank=True)

    is_read = models.BooleanField(default=False)
    read_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='read_notifications', null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    action_required = models.CharField(max_length=255, blank=True, null=True)
    action_response = models.CharField(max_length=20, choices=ACTION_CHOICES, blank=True, null=True)
    action_responded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    is_dismissable = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['sender', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    def mark_as_read(self, user):
        if not self.is_read:
            self.is_read = True
            self.read_by = user
            self.read_at = timezone.now()
            self.save()

    def respond_to_action(self, response, user=None):
        self.action_response = response
        self.action_responded_at = timezone.now()
        if user:
            self.read_by = user
            self.is_read = True
            self.read_at = self.read_at or timezone.now()
        self.save()
    
    @property
    def read_confirmation_text(self):
        if self.is_read and self.read_by and self.read_at:
            return f"Read by {self.read_by.get_full_name() or self.read_by.username} at {self.read_at.strftime('%Y-%m-%d %H:%M')}"
        return "Not confirmed yet"
    
    @property
    def requires_action(self):  # <-- ADD THIS
        return self.action_required is not None and self.action_response is None

    @property
    def link(self):  # <-- ADD THIS
        if self.related_assignment:
            return f"/staff/event/{self.related_assignment.event.id}/" 
        if self.related_event:
            return f"/staff/event/{self.related_event.id}/"
        return "#"