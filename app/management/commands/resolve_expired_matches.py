from django.core.management.base import BaseCommand
from django.utils import timezone
from app.models import Match

class Command(BaseCommand):
    help = 'Check and auto-resolve matches older than 48h with creator win by default and notify players'

    def handle(self, *args, **kwargs):
        self.stdout.write("Checking matches for completion, notifications, and 48h auto-resolution...")
        
        matches = Match.objects.filter(status__in=['completed', 'open', 'full', 'in_progress'])
        processed_count = 0
        resolved_count = 0
        notified_end_count = 0

        for match in matches:
            was_resolved = match.auto_resolved_48h
            was_notified = match.end_notification_sent
            
            match.update_status()
            
            if not was_notified and match.end_notification_sent:
                notified_end_count += 1
                self.stdout.write(f"Match {match.id}: Dispatched match end notifications")
                
            if not was_resolved and match.auto_resolved_48h:
                resolved_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Match {match.id}: Auto-resolved 48h expiration. Creator ({match.organizer.username}) declared default winner."
                    )
                )
            processed_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nFinished check.\n"
                f"Matches processed: {processed_count}\n"
                f"End notifications sent: {notified_end_count}\n"
                f"48h matches auto-resolved: {resolved_count}"
            )
        )
