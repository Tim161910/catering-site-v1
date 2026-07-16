from django import forms
from datetime import date
from django.utils import timezone
from django.core.exceptions import ValidationError
from.models import Staff, Event, Applicant, RolePlay, ApplicantRolePlay, Incident, EventTemplate, Recruitment, Role, RolePlayResponse, StaffUpdateRequest, Task, Meeting, Expense, Assignment, InterviewSlot
import re

def validate_phone(value, allow_plus=True):
    pattern = r'^\+?\d{10,15}$' if allow_plus else r'^\d{10,15}$'
    if value and not re.match(pattern, value):
        raise forms.ValidationError("Phone number must be 10-15 digits, " + ("optionally starting with +" if allow_plus else "no + or spaces"))
    return value

# local validate_phone is defined below; avoid importing .utils to prevent unresolved import
from.models import Staff


class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = Staff.DIRECT_UPDATE_FIELDS + Staff.APPROVAL_REQUIRED_FIELDS + ['reliability_notes']
        
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+2348012345678'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '2348012345678 (no + or spaces)'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'next_of_kin': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+2348012345678'}),
            'reliability_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].empty_label = "Select Role"
        for field_name in Staff.APPROVAL_REQUIRED_FIELDS:
            self.fields[field_name].help_text = "This change will require manager approval"

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        return validate_phone(phone, allow_plus=True)

    def clean_whatsapp(self):
        whatsapp = self.cleaned_data.get('whatsapp')
        return validate_phone(whatsapp, allow_plus=False)
    
    def clean_emergency_contact_phone(self):
        phone = self.cleaned_data.get('emergency_contact_phone')
        return validate_phone(phone, allow_plus=True) 

class StaffSelfUpdateForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = (
            'name', 'email', 'phone', 'whatsapp', 'address',
            'next_of_kin', 'emergency_contact_name', 'emergency_contact_phone'
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+2348012345678'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '2348012345678 (no + or spaces)'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'next_of_kin': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+2348012345678'}),
        }

    def clean_phone(self):
        return validate_phone(self.cleaned_data.get('phone'), allow_plus=True)

    def clean_whatsapp(self):
        return validate_phone(self.cleaned_data.get('whatsapp'), allow_plus=False)

    def clean_address(self):
        address = self.cleaned_data.get('address')
        if address and len(address) < 10:
            raise forms.ValidationError("Address must be at least 10 characters long")
        return address

class StaffUpdateRequestForm(forms.ModelForm):
    confirmation_message = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), help_text="Optional message to confirm the update")
    rejection_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), help_text="Reason for rejecting the update (if applicable)")
    class Meta:
        model = StaffUpdateRequest
        fields = ['request_reason']
        widgets = {
            'request_reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
        }

class StaffProfileForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = ('name', 'email', 'phone', 'whatsapp', 'address',
                  'next_of_kin', 'emergency_contact_name', 'emergency_contact_phone')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+2348012345678'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '2348012345678 (no + or spaces)'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'next_of_kin': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+2348012345678'}),
        }

    def clean_phone(self):
        return validate_phone(self.cleaned_data.get('phone'), allow_plus=True)

    def clean_whatsapp(self):
        return validate_phone(self.cleaned_data.get('whatsapp'), allow_plus=False)

    def clean_address(self):
        address = self.cleaned_data.get('address')
        if address and len(address) < 10:
            raise forms.ValidationError("Address must be at least 10 characters long")
        return address


class EventForm(forms.ModelForm):
    template = forms.ModelChoiceField(
        queryset=EventTemplate.objects.filter(is_active=True),
        required=False,
        empty_label="-- Custom: set roles manually --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Event
        fields = ['title', 'description', 'start_time', 'end_time', 'location', 'template']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'What is this event about?'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'HQ Conference Room / Venue'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # BIT 1: Fix datetime-local format for edit
        for field in ['start_time', 'end_time']:
            if self.initial.get(field):
                self.initial[field] = self.initial[field].strftime('%Y-%m-%dT%H:%M')
            elif self.instance and self.instance.pk and getattr(self.instance, field):
                self.initial[field] = getattr(self.instance, field).strftime('%Y-%m-%dT%H:%M')

        # BIT 2: Dynamically add a field for each Role: role_{id}
        self.role_fields = {}
        for role in Role.objects.filter(is_active=True).order_by('name'):
            field_name = f'role_{role.id}'
            initial_count = 0

            # If editing, pre-fill with current count of assignments for this role
            if self.instance and self.instance.pk:
                initial_count = self.instance.assignments.filter(role=role).count()

            self.fields[field_name] = forms.IntegerField(
                label=f"{role.name} Slots",
                min_value=0,
                initial=initial_count,
                required=False,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'placeholder': '0',
                    'min': '0'
                }),
                help_text=f"How many {role.name}s needed"
            )
            self.role_fields[role.id] = field_name

    def clean(self):
        cleaned_data = super().clean()
        # BIT 3: If template is selected, override role counts with template defaults
        template = cleaned_data.get('template')
        if template:
            for tr in template.templaterole_set.all():
                field_name = f'role_{tr.role.id}'
                if field_name in self.fields:
                    self.cleaned_data[field_name] = tr.default_count
        return cleaned_data

    def get_role_counts(self):
        # BIT 4: Returns {'role_id': count} for only roles > 0
        role_counts = {}
        for role_id, field_name in self.role_fields.items():
            count = self.cleaned_data.get(field_name) or 0
            if count > 0:
                role_counts[role_id] = count
        return role_counts

class ApplicantForm(forms.ModelForm):
    class Meta:
        model = Applicant
        fields = ['name', 'email', 'phone', 'resume', 'cover_letter'] # removed recruitment, status, interview_time
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+2348012345678'}),
            'resume': forms.FileInput(attrs={'class': 'form-control'}),
            'cover_letter': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Tell us why you are a good fit...'}),
        }

    def clean_phone(self):
        return validate_phone(self.cleaned_data.get('phone'), allow_plus=True)

class RolePlayForm(forms.ModelForm):
    class Meta:
        model = RolePlay
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Brief summary of the scenario'}),
            'expected_outcome': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'What should the staff member do/say?'}),
            'scenario': forms.Textarea(attrs={'rows': 12, 'class': 'form-control font-monospace', 'placeholder': 'Full roleplay script / situation details...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['description', 'expected_outcome', 'scenario']:
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs.update({'class': 'form-select'})
                elif isinstance(field.widget, forms.TextInput):
                    field.widget.attrs.update({'class': 'form-control'})

class ApplicantRolePlayForm(forms.ModelForm):
    class Meta:
        model = ApplicantRolePlay
        fields = ('applicant', 'role_play', 'score')
        widgets = {
            'applicant': forms.Select(attrs={'class': 'form-select'}),
            'role_play': forms.Select(attrs={'class': 'form-select'}),
            'score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['applicant'].empty_label = "Select Applicant"
        self.fields['role_play'].empty_label = "Select Scenario"
        self.fields['applicant'].queryset = Applicant.objects.all().order_by('name')
        self.fields['role_play'].queryset = RolePlay.objects.all().order_by('title')


class IncidentForm(forms.ModelForm):
    # Map incident_type to default scores. Adjust these to match your choices
    RELIABILITY_MAPPING = {
        'no_show': -20,
        'late': -10,
        'complaint': -15,
        'great_feedback': 5,
        'went_above': 10,
    }

    class Meta:
        model = Incident
        fields = ['staff', 'event', 'issue_type', 'incident_type', 'reliability_impact', 'notes', 'resolved', 'description']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-select'}),
            'event': forms.Select(attrs={'class': 'form-select'}),
            'issue_type': forms.Select(attrs={'class': 'form-select'}),
            'incident_type': forms.Select(attrs={'class': 'form-select'}),
            'reliability_impact': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': '-20, -10, +5',
                'min': '-50', 
                'max': '50'
            }),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe what happened...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full description...'}),
            'resolved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        staff_id = kwargs.pop('staff_id', None)
        super().__init__(*args, **kwargs)
        
        self.fields['event'].required = False
        self.fields['resolved'].required = False
        self.fields['reliability_impact'].required = False # allow auto-fill
        
        self.fields['event'].empty_label = "No specific event"
        self.fields['staff'].empty_label = "Select Staff Member"
        self.fields['issue_type'].empty_label = "Select Issue Type"
        self.fields['incident_type'].empty_label = "Select Incident Type"
        
        self.fields['staff'].queryset = Staff.objects.all().order_by('name')
        self.fields['event'].queryset = Event.objects.filter(start_time__date__gte=date.today()).order_by('-start_time')
        
        if staff_id:
            self.fields['staff'].initial = staff_id
            self.fields['staff'].widget.attrs['readonly'] = True
            self.fields['staff'].widget.attrs['disabled'] = True # readonly doesn't post, so we need hidden input
            # Add hidden input to actually submit the value
            self.fields['staff'].help_text = "Staff is locked for this incident"

    def clean_reliability_impact(self):
        impact = self.cleaned_data.get('reliability_impact')
        incident_type = self.cleaned_data.get('incident_type')
        
        # If user left it blank, auto-fill from mapping
        if impact in [None, '']:
            return self.RELIABILITY_MAPPING.get(incident_type, 0)
            
        # Validate range
        if impact < -50 or impact > 50:
            raise forms.ValidationError("Reliability impact must be between -50 and 50")
            
        return impact

    def clean(self):
        cleaned_data = super().clean()
        # If staff was disabled, we need to set it back from initial
        if 'staff' in self.initial and not cleaned_data.get('staff'):
            cleaned_data['staff'] = self.initial['staff']
        return cleaned_data

class EventTemplateForm(forms.ModelForm):
    class Meta:
        model = EventTemplate
        fields = ['name', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class RecruitmentForm(forms.ModelForm):
    position = forms.ModelChoiceField(
        queryset=Role.objects.all().order_by('name'),
        empty_label="-- Select Role --",
        widget=forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'}),
        label="Position/Role"
    )
    related_event = forms.ModelChoiceField(
        queryset=Event.objects.filter(start_time__date__gte=timezone.now().date()).order_by('start_time'),
        required=False,
        empty_label="No specific event - general recruitment",
        widget=forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'})
    )
    deadline = forms.DateTimeField(
        input_formats=['%d/%m/%Y %H:%M'],
        widget=forms.DateTimeInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500', 'placeholder': 'dd/mm/yyyy HH:MM', 'type': 'text'}, format='%d/%m/%Y %H:%M'),
        help_text="Format: 29/05/2026 15:10"
    )

    class Meta:
        model = Recruitment
        fields = ['position', 'related_event', 'description', 'requirements', 'status', 'deadline']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'w-full px-3 py-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'requirements': forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'status': forms.Select(attrs={'class': 'w-full px-3 py-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'}),
        }

    def clean_position(self):
        return self.cleaned_data['position'].name

    def clean_deadline(self):
        deadline = self.cleaned_data.get('deadline')
        if deadline and deadline < timezone.now():
            raise forms.ValidationError("Deadline cannot be in the past")
        return deadline

class RolePlayResponseForm(forms.ModelForm):
    class Meta:
        model = RolePlayResponse
        fields = ['action']
        widgets = {
            'action': forms.Textarea(attrs={'rows': 8, 'class': 'form-control font-monospace', 'placeholder': 'As the Catering Lead, what do you do?'})
        }

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'assigned_to', 'due_date', 'priority', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_to'].queryset = Staff.objects.filter(is_active=True).order_by('name')

class MeetingForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = ['title', 'description', 'start_time', 'end_time', 'attendees', 'location', 'meeting_link']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'attendees': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'meeting_link': forms.URLInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['attendees'].queryset = Staff.objects.filter(is_active=True)

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['staff', 'title', 'description', 'amount', 'category', 'receipt', 'status', 'approval_notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'receipt': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'approval_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['staff'].initial = user
            self.fields['staff'].widget = forms.HiddenInput()
            if hasattr(user, 'staff'):
                self.fields['staff'].queryset = Staff.objects.filter(id=user.staff.id)

    def clean_receipt(self):
        receipt = self.cleaned_data.get('receipt')
        if receipt and not receipt.name.lower().endswith(('.pdf','.jpg', '.png')):
            raise forms.ValidationError("Only PDF, JPG, PNG allowed")
        return receipt

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than 0")
        return amount

class ExpenseApprovalForm(forms.ModelForm):
    approval_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}))
    class Meta:
        model = Expense
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.approved_by = self.user
        if commit:
            instance.save()
        return instance

class AssignmentForm(forms.ModelForm):
    force_reassign = forms.BooleanField(required=False, label="Force reassign - end existing active assignment", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta:
        model = Assignment
        fields = ['staff', 'event', 'duty_number', 'role', 'status']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-select'}),
            'event': forms.Select(attrs={'class': 'form-select'}),
            'duty_number': forms.NumberInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        staff = cleaned_data.get('staff')
        event = cleaned_data.get('event')
        duty_number = cleaned_data.get('duty_number')
        force = cleaned_data.get('force_reassign')
        if staff and event and duty_number:
            existing = Assignment.objects.filter(staff=staff, event=event, duty_number=duty_number, status='assigned').first()
            if existing and not force:
                raise ValidationError("Active assignment exists. Check 'Force reassign' to override.")
        return cleaned_data

    def save(self, commit=True):
        staff = self.cleaned_data.get('staff')
        event = self.cleaned_data.get('event')
        duty_number = self.cleaned_data.get('duty_number')
        force = self.cleaned_data.get('force_reassign')
        if force and staff and event and duty_number:
            Assignment.objects.filter(staff=staff, event=event, duty_number=duty_number, status='assigned').update(status='ended', reassigned_at=timezone.now())
        return super().save(commit=commit)

class InterviewSlotForm(forms.ModelForm):
    class Meta:
        model = InterviewSlot
        fields = ['recruitment', 'date', 'start_time', 'end_time', 'capacity', 'interviewer']
        widgets = {
            'recruitment': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'interviewer': forms.Select(attrs={'class': 'form-select'}),
        }

class StaffFilterForm(forms.Form):
    search = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={
            'placeholder': 'Search name, phone, email...', 
            'class': 'form-control'
        })
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(), 
        required=False, 
        empty_label="All Roles", 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    reliability = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Reliability'),
            ('a_team', 'A-Team 90+'),
            ('good', 'Good 80-89'),
            ('watch', 'Watch 70-79'),
            ('warning', 'Warning <70'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

