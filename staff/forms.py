from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Staff, Event, Applicant, RolePlay, ApplicantRolePlay, Incident, EventTemplate, Recruitment, Role, RolePlayResponse, StaffUpdateRequest, Task, Meeting, Expense, Assignment
import re

def validate_phone(value, allow_plus=True):
    pattern = r'^\+?\d{10,15}$' if allow_plus else r'^\d{10,15}$'
    if value and not re.match(pattern, value):
        raise forms.ValidationError("Phone number must be 10-15 digits, " + ("optionally starting with +" if allow_plus else "no + or spaces"))
    return value

class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = (
            'name', 'email', 'phone', 'whatsapp', 'address',
            'next_of_kin', 'emergency_contact_name', 'emergency_contact_phone',
            'role', 'reliability_score', 'reliability_notes', 'is_active'
        )
        widgets = {
            'phone': forms.TextInput(attrs={'placeholder': '+2348012345678'}),
            'whatsapp': forms.TextInput(attrs={'placeholder': '2348012345678 (no + or spaces)'}),
            'address': forms.Textarea(attrs={'rows': 2}),
            'reliability_notes': forms.Textarea(attrs={'rows': 2}),
        }

    def clean_phone(self):
        return validate_phone(self.cleaned_data.get('phone'), allow_plus=True)

    def clean_whatsapp(self):
        return validate_phone(self.cleaned_data.get('whatsapp'), allow_plus=False)

class StaffSelfUpdateForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = (
            'name', 'email', 'phone', 'whatsapp', 'address',
            'next_of_kin', 'emergency_contact_name', 'emergency_contact_phone'
        )
        widgets = {
            'phone': forms.TextInput(attrs={'placeholder': '+2348012345678'}),
            'whatsapp': forms.TextInput(attrs={'placeholder': '2348012345678 (no + or spaces)'}),
            'address': forms.Textarea(attrs={'rows': 2}),
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
    confirmation_message = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}), help_text="Optional message to confirm the update")
    rejection_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}), help_text="Reason for rejecting the update (if applicable)")
    class Meta:
        model = StaffUpdateRequest
        fields = ['request_reason'] # or fields relevant to the update request, excluding the confirmation/rejection fields which are handled separately     

class StaffProfileForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = ('name', 'email', 'phone', 'whatsapp', 'address',
                  'next_of_kin', 'emergency_contact_name', 'emergency_contact_phone')
        widgets = {
            'phone': forms.TextInput(attrs={'placeholder': '+2348012345678'}),
            'whatsapp': forms.TextInput(attrs={'placeholder': '2348012345678 (no + or spaces)'}),
            'address': forms.Textarea(attrs={'rows': 2}),
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
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Event
        fields = ['title', 'description', 'start_time','end_time', 'location', 'template']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def get_role_counts(self):
        # Only access cleaned_data after validation
        if not hasattr(self, 'cleaned_data') or not self.is_valid():
            return {}
        
        template = self.cleaned_data.get('template')
        if template:
            return {
                str(tr.role.id): tr.count
                for tr in template.template_roles.all()
            }
        # Priority 2: Manual fields - add these if you want fallback
        return {}

class ApplicantForm(forms.ModelForm):
    class Meta:
        model = Applicant
        fields = ['name', 'email', 'phone', 'recruitment', 'resume', 'cover_letter', 'status', 'interview_time']
        widgets = {
            'phone': forms.TextInput(attrs={'placeholder': '+2348012345678'}),
            'cover_letter': forms.Textarea(attrs={'rows': 3}),
            'interview_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean_phone(self):
        return validate_phone(self.cleaned_data.get('phone'), allow_plus=True)


class RolePlayForm(forms.ModelForm):
    class Meta:
        model = RolePlay
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'expected_outcome': forms.Textarea(attrs={'rows': 4}),
            'scenario': forms.Textarea(attrs={'rows': 12, 'cols': 100}),
        }

class ApplicantRolePlayForm(forms.ModelForm):
    class Meta:
        model = ApplicantRolePlay
        fields = ('applicant', 'role_play', 'score')

class IncidentForm(forms.ModelForm):
    class Meta:
        model = Incident
        fields = ['staff', 'event', 'issue_type', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe what happened...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['event'].required = False
        self.fields['event'].empty_label = "No specific event"
        self.fields['staff'].queryset = Staff.objects.all()
        self.fields['event'].queryset = Event.objects.all()


class EventTemplateForm(forms.ModelForm):
    class Meta:
        model = EventTemplate
        fields = ['name', 'is_active']


class RecruitmentForm(forms.ModelForm):
    position = forms.ModelChoiceField(
        queryset=Role.objects.all().order_by('name'),
        empty_label="-- Select Role --",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Position/Role",
        help_text="Select from roles managed in Django Admin"
    )

    related_event = forms.ModelChoiceField(
        queryset=Event.objects.filter(start_time__date__gte=timezone.now().date()).order_by('start_time'),
        required=False,
        empty_label="No specific event - general recruitment",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    deadline = forms.DateTimeField(
        input_formats=['%d/%m/%Y %H:%M'],
        widget=forms.DateTimeInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'dd/mm/yyyy HH:MM',
                'type': 'text'
            },
            format='%d/%m/%Y %H:%M'
        ),
        help_text="Format: 29/05/2026 15:10"
    )

    class Meta:
        model = Recruitment
        fields = ['position', 'related_event', 'description', 'requirements', 'status', 'deadline']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Describe the job duties, shifts, responsibilities, team structure, ...'
            }),
            'requirements': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'e.g. Min 85% reliability_score, 2+ years experience, Available 05/06'
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['status'].initial = 'Open'
        self.fields['related_event'].label = "Related Event"

    def clean_position(self):
        """Save the role name (not ID) in the position field for easier searching"""
        role = self.cleaned_data['position']
        return role.name
    
    def clean_deadline(self):
        deadline = self.cleaned_data.get('deadline')
        if deadline and deadline < timezone.now():
            raise forms.ValidationError("Deadline cannot be in the past")
        return deadline
    
class RolePlayResponseForm(forms.ModelForm):
    class Meta:
        model = RolePlayResponse
        fields = ['action']  # Only let user fill the action
        widgets = {
            'action': forms.Textarea(attrs={
                'rows': 8, 
                'class': 'form-control',
                'placeholder': 'As the Catering Lead, what do you do?'
            })
        }
        labels = {
            'action': 'What do you do?'
        }

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields= ['title', 'description', 'assigned_to', 'due_date', 'priority', 'status']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

class MeetingForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields= ['title', 'description', 'start_time', 'end_time', 'attendees', 'location', 'meeting_link']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['staff', 'title', 'description', 'amount', 'category', 'receipt', 'status', 'approval_notes']
        widgets = {
            'approval_notes': forms.Textarea(attrs={'rows': 2}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'category': forms.Select(attrs={'class': 'form-select'}),  
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
    approval_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}), help_text="Optional notes for approval/rejection")
    class Meta:
        model = Expense
        fields = ['status']  # likely: 'pending', 'approved', 'rejected'
        # Only allow changing approval status, not the expense details
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

    def clean_status(self):
        status = self.cleaned_data['status']
        if status not in ['approved', 'rejected', 'pending']:
            raise forms.ValidationError("Invalid status")
        return status
    
class AssignmentForm(forms.ModelForm):
    force_reassign = forms.BooleanField(
        required=False, 
        label="Force reassign - end existing active assignment"
    )
    
    class Meta:
        model = Assignment
        fields = ['staff', 'event', 'duty_number', 'role', 'status']

    def clean(self):
        cleaned_data = super().clean()
        staff = cleaned_data.get('staff')
        event = cleaned_data.get('event')
        duty_number = cleaned_data.get('duty_number')
        force = cleaned_data.get('force_reassign')
    
        if staff and event and duty_number:
            existing = Assignment.objects.filter(
                staff=staff, event=event, duty_number=duty_number, 
                status='assigned'
            ).first()
        
            if existing and not force:
                raise ValidationError("Active assignment exists. Check 'Force reassign' to override.")
    
        return cleaned_data

    def save(self, commit=True):
        staff = self.cleaned_data.get('staff')
        event = self.cleaned_data.get('event') 
        duty_number = self.cleaned_data.get('duty_number')
        force = self.cleaned_data.get('force_reassign')
    
        if force and staff and event and duty_number:
            Assignment.objects.filter(
                staff=staff, event=event, duty_number=duty_number,
                status='assigned'
            ).update(status='ended', reassigned_at=timezone.now())
    
        return super().save(commit=commit)