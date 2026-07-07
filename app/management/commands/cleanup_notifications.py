from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from app.models import Notification

class Command(BaseCommand):
    help = 'Clean up notifications older than 90 days'

    def handle(self, *args, **kwargs):
        three_months_ago = timezone.now() - timedelta(days=90)
        deleted_count, _ = Notification.objects.filter(created_at__lt=three_months_ago).delete()
        self.stdout.write(self.style.SUCCESS(f"Successfully deleted {deleted_count} notifications older than 90 days."))
