from django.core.management.base import BaseCommand
from django.utils import timezone
from app.models import Match

class Command(BaseCommand):
    help = 'Fix match statuses for all existing matches'

    def handle(self, *args, **kwargs):
        matches = Match.objects.all()
        self.stdout.write(f"Found {matches.count()} matches to update")
        
        for match in matches:
            old_status = match.status
            old_is_open = match.is_open
            
            # Set a default status if it's None or empty
            if not match.status:
                match.status = 'open'
                match.is_open = True
                match.save()
                self.stdout.write(f"Match {match.id}: Set default status to 'open'")
            
            # Now update based on actual conditions
            match.update_status()
            
            if match.status != old_status or match.is_open != old_is_open:
                self.stdout.write(
                    f"Match {match.id}: Updated from status={old_status}, is_open={old_is_open} "
                    f"to status={match.status}, is_open={match.is_open}"
                )
        
        # Show summary
        open_matches = Match.objects.filter(status='open').count()
        full_matches = Match.objects.filter(status='full').count()
        in_progress = Match.objects.filter(status='in_progress').count()
        completed = Match.objects.filter(status='completed').count()
        cancelled = Match.objects.filter(status='cancelled').count()
        
        self.stdout.write(self.style.SUCCESS(
            f"\nSummary:\n"
            f"Open: {open_matches}\n"
            f"Full: {full_matches}\n"
            f"In Progress: {in_progress}\n"
            f"Completed: {completed}\n"
            f"Cancelled: {cancelled}\n"
            f"Total: {matches.count()}"
        ))