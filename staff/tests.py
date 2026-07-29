from django.contrib.auth.models import User
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from datetime import date, datetime 
from .models import (
    Event, Recruitment, RolePlay, Staff, Applicant, Interview, 
    Role, EventTemplate, Assignment, Task, Incident, IssueType, 
    Rule, Flag, Meeting, Expense, LeaveRequest, Notification,
    ApplicantRolePlay
)

# 1. IMPORTS + HELPERS
class BaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role_chef = Role.objects.create(name='Chef', slug='chef')
        cls.role_waiter = Role.objects.create(name='Waiter', slug='waiter')

    @staticmethod
    def create_recruitment(position, description, requirements, status, deadline):
        return Recruitment.objects.create(
            position=position,
            description=description,
            requirements=requirements,
            status=status,
            deadline=deadline
        )

# 2. CORE / UTILS
class RoleModelTest(TestCase): 
    def test_create_role(self):
        role = Role.objects.create(name='Manager', slug='manager')
        self.assertEqual(str(role), 'Manager')

# 3. EVENTS
class EventModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.event = Event.objects.create(
            title='Catering for Wedding',
            start_time=timezone.make_aware(datetime(2024, 12, 31, 18, 0)),
            end_time=timezone.make_aware(datetime(2024, 12, 31, 22, 0)),
            location='Banquet Hall'
        ) 

    def test_create_event(self):
        self.assertEqual(self.event.title, 'Catering for Wedding')
        self.assertEqual(self.event.location, 'Banquet Hall')           
    
    def test_str_representation(self):
        self.assertIn('Catering for Wedding', str(self.event))

class EventTemplateModelTest(TestCase): pass
class EventViewTest(TestCase): pass

# 4. STAFF
class StaffModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role = Role.objects.create(name='Chef', slug='chef')
        cls.staff = Staff.objects.create(
            name='John Doe',
            email='john.doe@example.com',
            role=cls.role
        )

    def test_create_staff(self):
        self.assertEqual(self.staff.name, 'John Doe')
        self.assertEqual(self.staff.role.name, 'Chef')

    def test_str_representation(self):
        self.assertEqual(str(self.staff), 'John Doe (Chef)')

class StaffViewTest(TestCase): pass
class StaffFormTest(TestCase): pass

# 5. RELIABILITY
class IncidentModelTest(TestCase): pass
class IssueTypeModelTest(TestCase): pass
class RuleModelTest(TestCase): pass
class FlagModelTest(TestCase): pass

# 6. ASSIGNMENTS
class AssignmentModelTest(TestCase): pass
class TaskModelTest(TestCase): pass

# 7. RECRUITMENT
class RecruitmentModelTest(BaseTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.recruitment = cls.create_recruitment(
            position=cls.role_waiter,
            description='Looking for an experienced waiter.',
            requirements='Must have 2 years of experience.',
            status='open',
            deadline=timezone.make_aware(datetime(2024, 12, 31))
        )
        
    def test_create_recruitment(self):
        self.assertEqual(self.recruitment.position.name, 'Waiter')
        self.assertEqual(self.recruitment.status, 'open')

    def test_str_representation(self):
        self.assertEqual(str(self.recruitment), 'Waiter (open)')

class ApplicantModelTest(BaseTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.recruitment = Recruitment.objects.create(
            position=cls.role_waiter,
            description='Looking for an experienced waiter.',
            requirements='Must have 2 years of experience.',
            status='open',
            deadline=timezone.make_aware(datetime(2024, 12, 31))
        )
        cls.applicant = Applicant.objects.create(
            name='Jane Smith',
            email='jane.smith@example.com',
            phone='1234567890',
            recruitment=cls.recruitment
        )

class InterviewModelTest(BaseTest): ... # same pattern, use cls.role_waiter

class RecruitmentApplicantsViewTest(TestCase): ... # same, use Role.objects.create

class RolePlayModelTest(TestCase): pass
class RolePlayListViewTest(TestCase): pass
class ApplicantRolePlayModelTest(TestCase): pass

# 8. MISC
class MeetingModelTest(TestCase): pass
class ExpenseModelTest(TestCase): pass
class LeaveRequestModelTest(TestCase): pass

# 9. NOTIFICATIONS
class NotificationModelTest(TestCase): pass