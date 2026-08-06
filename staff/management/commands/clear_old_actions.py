from django.core.management.base import BaseCommand
from django.contrib.admin.models import LogEntry
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Delete admin log entries older than X days. Default is 30 days.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', 
            type=int, 
            default=30,
            help='Delete actions older than this many days'
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff = timezone.now() - timedelta(days=days)
        
        old_actions = LogEntry.objects.filter(action_time__lt=cutoff)
        count = old_actions.count()
        
        old_actions.delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Deleted {count} admin actions older than {days} days')
        )