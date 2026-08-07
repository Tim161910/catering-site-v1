from django.contrib import admin
from django.utils.html import format_html
from.models import Event, Staff, Assignment, Role, EventTemplate, EventTemplateRole, IssueType, Incident
from.forms import StaffForm

class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug'); search_fields = ['name']; prepopulated_fields = {'slug': ('name',)}
class EventTemplateRoleInline(admin.TabularInline):
    model = EventTemplateRole; extra = 1; autocomplete_fields = ['role']
class EventTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']; list_filter = ['is_active']; search_fields = ['name']; inlines = [EventTemplateRoleInline]; list_editable = ['is_active']
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_time', 'client_name']; list_filter = ['start_time']; search_fields = ['title', 'client_name']
class StaffAdmin(admin.ModelAdmin):
    form = StaffForm; list_display = ('name', 'role', 'phone', 'reliability_badge', 'is_active'); list_filter = ('role', 'is_active'); search_fields = ('name', 'email', 'phone'); readonly_fields = ('reliability_score',)
    @admin.display(description='Reliability')
    def reliability_badge(self, obj):
        score = obj.reliability_score or 0; color = '#28a745' if score >= 90 else '#ffc107' if score >= 75 else '#dc3545'; emoji = '🟢' if score >= 90 else '🟡' if score >= 75 else '🔴'; return format_html('<span style="color: {}; font-weight: 600;">{} {}%</span>', color, emoji, score)
class IssueTypeAdmin(admin.ModelAdmin):
    list_display = ['name']; search_fields = ['name']
class IncidentAdmin(admin.ModelAdmin):
    list_display = ['staff', 'event', 'issue_type', 'resolved']; search_fields = ['staff__name']
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['event', 'duty_number', 'staff', 'role', 'status']; list_filter = ['status', 'event', 'role']; search_fields = ['staff__name', 'event__title']