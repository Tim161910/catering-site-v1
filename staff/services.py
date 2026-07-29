# staff/services.py
from django.utils import timezone
from django.db.models import Q
from .models import Rule, Flag, Incident # 1. Capital I

def evaluate_rules(staff, incident=None): # 2. Add incident param
    """Check all active rules for a staff member"""
    active_rules = Rule.objects.filter(is_active=True)
    
    for rule in active_rules:
        # Check if rule applies
        if rule_applies(staff, rule):
            # Create/update flag
            _update_or_create_flag(staff, rule, incident) # 3. now incident exists

def rule_applies(staff, rule):
    """Check if a specific rule applies to the staff member"""
    if rule.rule_type == 'date':
        # Check incidents in date range
        incidents = staff.incidents.filter(
            reported_on__gte=timezone.now() - timezone.timedelta(days=rule.days)
        )
        return incidents.count() >= rule.threshold
    
    elif rule.rule_type == 'issue_type':
        # Check specific issue type count
        incidents = staff.incidents.filter(
            issue_type=rule.issue_type,
            resolved=False, # only count unresolved
            reported_on__gte=timezone.now() - timezone.timedelta(days=rule.days)
        )
        return incidents.count() >= rule.threshold
    
    elif rule.rule_type == 'reliability':
        # Check reliability score
        return staff.reliability_score <= rule.min_reliability_score
    
    return False

def _update_or_create_flag(staff, rule, incident=None):
    """Create or update a flag for a staff member"""
    # Count how many times this rule triggered
    count = staff.incidents.filter(
        reported_on__gte=timezone.now() - timezone.timedelta(days=rule.days)
    ).count()
    
    flag_level = 2 if count >= rule.threshold * 2 else 1 # Critical if 2x threshold

    flag, created = Flag.objects.update_or_create(
        staff=staff,
        rule=rule,
        defaults={
            'flag_level': flag_level,
            'incident': incident,
            'notes': f"Triggered: {count} times in {rule.days} days"
        }
    )
    return flag