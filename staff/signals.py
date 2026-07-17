# staff/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Incident

@receiver([post_save, post_delete], sender=Incident)
def update_staff_reliability(sender, instance, **kwargs):
    if instance.staff:
        instance.staff.update_reliability_score()