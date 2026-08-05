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
    
    # 1. Get staff name safely - handles staff with no user
    staff_obj = getattr(sender_user, 'staff', None) if sender_user else None
    if staff_obj:
        staff_name = staff_obj.name
    elif sender_user:
        staff_name = sender_user.username
    else:
        staff_name = assignment.staff.name if assignment.staff else "Unassigned Staff"
    
    print(f"Staff: {staff_name}")
    
    # 2. Get managers + superusers
    from django.db.models import Q
    from django.contrib.auth.models import User
    managers = User.objects.filter(Q(is_manager=True) | Q(is_superuser=True)).distinct()
    print(f"Managers found: {managers.count()} - {[m.username for m in managers]}")
    
    if not managers.exists():
        print("No managers found to notify")
        return

    # 3. Create notification for each manager
    for manager in managers:
        sender_for_db = sender_user if sender_user else manager  # can't save None as sender
        sender_type_for_db = 'staff' if sender_user else 'admin'

        print(f"Creating for: {manager.username}")
        Notification.objects.create(
            user=manager,
            sender=sender_for_db,
            sender_type=sender_type_for_db,
            title=f"{action_emoji} {staff_name} {action_text} Duty {assignment.duty_number}",
            message=f"{action_emoji} {staff_name} {action_text}: {assignment.event.title} - Duty {assignment.duty_number} as {assignment.role.name}",
            notification_type='assignment',
            related_event=assignment.event,
            related_assignment=assignment
        )
    print(f"***** NOTIFICATION FUNCTION DONE *****")

@receiver(post_save, sender=Assignment)
def notify_manager_on_new_assignment(sender, instance, created, **kwargs):
    # Fire only when NEW assignment is created AND staff is already assigned
    if created and instance.staff:
        _send_manager_notification(instance.staff.user, instance, "🆕", "ASSIGNED TO")