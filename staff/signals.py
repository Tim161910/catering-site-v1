# staff/signals.py
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import Incident

@receiver([post_save, post_delete], sender=Incident)
def update_staff_reliability(sender, instance, **kwargs):
    if instance.staff:
        instance.staff.update_reliability_score()

@receiver(pre_save, sender=Incident)
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