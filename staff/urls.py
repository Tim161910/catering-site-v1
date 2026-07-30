from django.urls import path
from . import views
from  .views import MarkNotificationReadView, RespondNotificationView, NotificationListView

app_name = 'staff'

urlpatterns = [
    # DASHBOARD / STAFF

    path('risk-dashboard/', views.RiskDashboardView.as_view(), name='risk_dashboard'),  # FIXED: underscore
    path('', views.StaffDashboardView.as_view(), name='staff_dashboard'),
    path('dashboard/', views.StaffDashboardView.as_view(), name='staff_dashboard_alt'),
    path('my-dashboard/', views.StaffPersonalDashboardView.as_view(), name='my_dashboard'),
    path('staff-list/', views.StaffListView.as_view(), name='staff_list'),
    path('create/', views.StaffCreateView.as_view(), name='staff_create'),
    path('<int:pk>/', views.StaffDetailView.as_view(), name='staff_detail'),
    path('<int:pk>/update/', views.StaffUpdateView.as_view(), name='staff_update'),
    path('<int:pk>/delete/', views.StaffDeleteView.as_view(), name='staff_delete'),
    path('profile/edit/', views.StaffProfileUpdateView.as_view(), name='staff_profile_edit'),
    path('dashboard/export-csv/', views.ExportStaffCSVView.as_view(), name='export_staff_csv'),
    path('tasks/', views.TaskListView.as_view(), name='task_list'),
    path('reset-admin/', views.reset_admin, name='reset_admin'),

    # EVENTS

    path('event/', views.EventListView.as_view(), name='event_list'),
    path('events/', views.EventListView.as_view(), name='events_list'),  # add this line
    path('event/new/', views.EventCreateView.as_view(), name='event_create'),
    path('event/<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
    path('event/<int:pk>/update/', views.EventUpdateView.as_view(), name='event_update'),
    path('event/<int:pk>/delete/', views.EventDeleteView.as_view(), name='event_delete'),
    
    # EVENT STATUS + AUTO FILL

    path('event-status/', views.EventStatusView.as_view(), name='event_status'),
    path('event/<int:event_id>/auto-fill/', views.AutoFillRosterView.as_view(), name='auto_fill_roster'),
    path('auto-fill-all/', views.AutoFillAllEventsView.as_view(), name='auto_fill_all_events'),
    
    path('event/<int:event_id>/assignments/', views.AssignmentListView.as_view(), name='assignment_list'),
    path('event/<int:event_id>/create-from-template/', views.create_assignments_from_template, name='create_from_template'),
    path('incident/add/', views.IncidentCreateView.as_view(), name='incident_add'),

    # ASSIGNMENT API

    path('api/events/<int:pk>/assignments/', views.create_assignment, name='create_assignment'), 
    path('api/assignments/<int:assignment_id>/reassign/', views.reassign_assignment, name='reassign_assignment'), 
    path('api/assignments/<int:assignment_id>/replace_staff/', views.replace_staff, name='replace_staff'), 
    
    # ACTION URLS - THE 4 STUBS

    path('assignment/<int:pk>/accept/', views.accept_assignment, name='accept_assignment'),
    path('assignment/<int:pk>/decline/', views.decline_assignment, name='decline_assignment'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
    
    # RECRUITMENT

    path('recruitment/', views.RecruitmentListView.as_view(), name='recruitment_list'),
    path('recruitment/new/', views.RecruitmentCreateView.as_view(), name='recruitment_create'),
    path('recruitment/<int:recruitment_id>/', views.RecruitmentDetailView.as_view(), name='recruitment_detail'),
    path('recruitment/<int:recruitment_id>/update/', views.RecruitmentUpdateView.as_view(), name='recruitment_update'),
    path('recruitment/<int:recruitment_id>/delete/', views.RecruitmentDeleteView.as_view(), name='recruitment_delete'),
    path('recruitment/<int:recruitment_id>/applicant/add/', views.ApplicantCreateView.as_view(), name='applicant_add'),
    path('recruitment/<int:recruitment_id>/applicants/', views.RecruitmentApplicantsView.as_view(), name='recruitment_applicants'),
    path('recruitment/<int:recruitment_id>/export_csv/', views.ExportApplicantsCSVView.as_view(), name='export_applicants_csv'),
    path('recruitment/<int:recruitment_id>/send_email/', views.SendEmailToApplicantsView.as_view(), name='send_email_to_applicants'),
    path('recruitment/<int:recruitment_id>/schedule_interviews/', views.ScheduleInterviewsView.as_view(), name='schedule_interviews'),
    path('recruitment/<int:recruitment_id>/manage_interview_slots/', views.ManageInterviewSlotsView.as_view(), name='manage_interview_slots'),
    path('interview/<int:slot_id>/accept/', views.accept_interview, name='accept_interview'),
    path('interview/<int:slot_id>/decline/', views.decline_interview, name='decline_interview'),

    # ROLE PLAY

    path('role_play/', views.RolePlayListView.as_view(), name='role_play_list'),
    path('role_play/new/', views.RolePlayCreateView.as_view(), name='role_play_create'),
    path('role_play/<int:pk>/', views.RolePlayDetailView.as_view(), name='role_play_detail'),
    path('role_play/<int:pk>/update/', views.RolePlayUpdateView.as_view(), name='role_play_update'),
    path('role_play/<int:pk>/delete/', views.RolePlayDeleteView.as_view(), name='role_play_delete'),
    path('role_play/<int:pk>/start/', views.StartScenarioView.as_view(), name='start_scenario'),

    # OTHER

    path('success/', views.SuccessView.as_view(), name='success'),

    # NOTIFICATIONS
    
    path('notifications/', NotificationListView.as_view(), name='notifications_list'),
    path('notifications/<int:pk>/mark-read/', MarkNotificationReadView.as_view(), name='mark_notification_read'),
    path('notifications/<int:pk>/respond/<str:action>/', RespondNotificationView.as_view(), name='respond_notification'),
]

