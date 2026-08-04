from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Incident, Assignment, Notification, Staff

@receiver([post_save, post_delete], sender=Incident)
def update_staff_reliability(sender, instance, **kwargs):
    if instance.staff:
        instance.staff.update_reliability_score()

@receiver(post_save, sender=Incident)
def adjust_reliability_on_resolve(sender, instance, **kwargs):
    if not instance.pk:
        return  # new incident, handled by post_save above
    
    try:
        old = Incident.objects.get(pk=instance.pk)
    except Incident.DoesNotExist:
        return

    # If it just got resolved, give the points back
    if not old.resolved and instance.resolved:
        staff = instance.staff
        staff.reliability_score = min(100, staff.reliability_score + instance.weight_percent)
        staff.save(update_fields=['reliability_score'])

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

@receiver(post_save, sender=Assignment)
def notify_manager_on_new_assignment(sender, instance, created, **kwargs):
    # Fire only when NEW assignment is created AND staff is already assigned
    if created and instance.staff:
        _send_manager_notification(instance.staff.user, instance, "🆕", "ASSIGNED TO")