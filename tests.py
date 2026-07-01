
from xmlrpc import client

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse, reverse_lazy
from .models import Event, Recruitment, RolePlay, Staff, Applicant, ApplicationStatus, Interview
from datetime import date, datetime 
from django.utils import timezone


class StaffModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = Staff.objects.create(
            name='John Doe',
            email='john.doe@example.com',
            role='Chef'
        )

    def test_create_staff(self):
        self.assertEqual(self.staff.name, 'John Doe')
        self.assertEqual(self.staff.email, 'john.doe@example.com')
        self.assertEqual(self.staff.role, 'Chef')

    def test_str_representation(self):
        self.assertEqual(str(self.staff), 'John Doe (Chef)')

class EventModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.event = Event.objects.create(
            name='Catering for Wedding',
            date=date(2024, 12, 31),
            location='Banquet Hall'
        ) 

    def test_create_event(self):
        self.assertEqual(self.event.name, 'Catering for Wedding')
        self.assertEqual(self.event.date, date(2024, 12, 31))
        self.assertEqual(self.event.location, 'Banquet Hall')           
    
    def test_str_representation(self):
        self.assertEqual(str(self.event), 'Catering for Wedding (2024-12-31 at Banquet Hall)')

class BaseTest(TestCase):
    @staticmethod
    def create_recruitment(position, description, requirements, status, deadline):
        """
        Creates a new Recruitment instance with the given parameters.
        
        Args:
            position (str): The job position for the recruitment.
            description (str): A description of the recruitment.
            requirements (str): The requirements for the recruitment.
            status (str): The current status of the recruitment (e.g., 'Open', 'Closed').
            deadline (date): The application deadline for the recruitment.
            Returns:
                Recruitment: The created Recruitment instance.
        """
        return Recruitment.objects.create(
            position=position,
            description=description,
            requirements=requirements,
            status=status,
            deadline=deadline
        )

class RecruitmentModelTest(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.recruitment = cls.create_recruitment(
            position='Waiter',
            description='Looking for an experienced waiter.',
            requirements='Must have 2 years of experience.',
            status='Open',
            deadline=timezone.make_aware(datetime(2024, 12, 31))
        )
        
    def test_create_recruitment(self):
        self.assertEqual(self.recruitment.position, 'Waiter')
        self.assertEqual(self.recruitment.description, 'Looking for an experienced waiter.')
        self.assertEqual(self.recruitment.requirements, 'Must have 2 years of experience.')
        self.assertEqual(self.recruitment.status, 'Open')
        self.assertEqual(self.recruitment.deadline.date(), date(2024, 12, 31))

    def test_str_representation(self):
        self.assertEqual(str(self.recruitment), 'Waiter (Open)')

    def test_recruitment_requires_valid_deadline(self):
        with self.assertRaises(ValidationError):
            r = Recruitment(
                position='Waiter',
                description='Looking for an experienced waiter.',
                requirements='Must have 2 years of experience.',
                status='Open',
                deadline='invalid-date'
            )
            r.full_clean()  # This will trigger validation and raise ValidationError for invalid date format

class RecruitmentApplicantsViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
       cls.recruitment = Recruitment.objects.create(
           position='Waiter',
           description='Looking for an experienced waiter.',
           requirements='Must have 2 years of experience.',
           status='Open',
           deadline=timezone.make_aware(datetime(2024, 12, 31))
       )

       cls.applicant1 = Applicant.objects.create(
           name='Jane Smith',
           email='jane.smith@example.com',
           phone='123-456-7890',
           recruitment=cls.recruitment
       )

       cls.applicant2 = Applicant.objects.create(
           name='Bob Johnson',
           email='bob.johnson@example.com',
           phone='098-765-4321',
           recruitment=cls.recruitment
       )

       cls.url = reverse_lazy('staff:recruitment_applicants', kwargs={'recruitment_id': cls.recruitment.id})
        
    def setUp(self):
        staff_user = User.objects.create_superuser('staff', 'staff@example.com', 'password')
        self.client.force_login(staff_user)

    def test_view_url_accessible_by_name(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/recruitment_applicants.html')

    def test_view_lists_all_applicants(self):
        print(self.recruitment.applicant_set.all())
        response = self.client.get(self.url)
        print(response.content) # Debug
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['applicants']), 2)
        self.assertContains(response, 'Jane Smith')
        self.assertContains(response, 'Bob Johnson')

    def test_staff_required(self):
        # Non-staff user
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302) # Redirect to login or 403
        # Staff user
        staff_user = User.objects.create_superuser('another_staff', 'another_staff@example.com', 'password')
        self.client.force_login(staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

class ApplicantModelTest(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.recruitment = Recruitment.objects.create(
            position='Waiter',
            description='Looking for an experienced waiter.',
            requirements='Must have 2 years of experience.',
            status='Open',
            deadline=timezone.make_aware(datetime(2024, 12, 31))
        )

        cls.applicant = Applicant.objects.create(
            name='Jane Smith',
            email='jane.smith@example.com',
            phone='123-456-7890',
            recruitment=cls.recruitment
        )

    def test_create_applicant(self):
        self.assertEqual(self.applicant.name, 'Jane Smith')
        self.assertEqual(self.applicant.email, 'jane.smith@example.com')
        self.assertEqual(self.applicant.phone, '123-456-7890')
        self.assertEqual(self.applicant.recruitment, self.recruitment)

    def test_is_interviewed(self):
        self.assertFalse(self.applicant.interviews.exists())
        Interview.objects.create(applicant=self.applicant, date=timezone.make_aware(datetime(2024, 11, 1)), interview_type='written')
        self.assertTrue(self.applicant.interviews.exists())

    def test_str_representation(self):
        self.assertEqual(str(self.applicant), 'Jane Smith (jane.smith@example.com)')

class InterviewModelTest(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.recruitment = cls.create_recruitment(
            position='Waiter',
            description='Looking for an experienced waiter.',
            requirements='Must have 2 years of experience.',
            status='Open',
            deadline=timezone.make_aware(datetime(2024, 12, 31))
        )

        cls.applicant = Applicant.objects.create(
            name='Jane Smith',
            email='jane.smith@example.com',
            phone='123-456-7890',
            recruitment=cls.recruitment
        )

        cls.interview = Interview.objects.create(
            applicant=cls.applicant,
            date=timezone.make_aware(datetime(2024, 11, 1)),
            interview_type='written',
        )

    def test_create_interview(self):
        self.assertEqual(self.interview.applicant, self.applicant)
        self.assertEqual(self.interview.date.date(), date(2024, 11, 1))
        self.assertEqual(self.interview.interview_type, 'written')

    def test_str_representation(self):
        self.assertEqual(str(self.interview), 'Jane Smith - 2024-11-01 00:00:00+00:00 - written')

    def test_interview_requires_applicant(self):
        with self.assertRaises(IntegrityError):
            Interview.objects.create(
                date=timezone.make_aware(datetime(2024, 11, 1)),
                interview_type='written',
            )

class RolePlayListViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role_play1 = RolePlay.objects.create(scenario='Test Scenario1', role='Test Role1', description='Test Description1', expected_outcome='Test Outcome1')
        cls.role_play2 = RolePlay.objects.create(scenario='Test Scenario2', role='Test Role2', description='Test Description2', expected_outcome='Test Outcome2')

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get('/staff/role_play/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        response = self.client.get(reverse_lazy('staff:role_play_list'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(reverse_lazy('staff:role_play_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/role_play_list.html')

    def test_view_lists_all_role_plays(self):
        response = self.client.get(reverse_lazy('staff:role_play_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Scenario1')
        self.assertContains(response, 'Test Scenario2')

    


