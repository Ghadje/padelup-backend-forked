from django.core.management.base import BaseCommand
from django.utils import timezone
from app.models import Match


class Command(BaseCommand):
    help = 'Check upcoming matches starting within 30 minutes and dispatch reminder notifications to all match members'

    def handle(self, *args, **kwargs):
        self.stdout.write("Checking matches for 30-minute reminder notifications...")

        now = timezone.now()
        # Look for matches starting between now and now + 35 minutes
        matches = Match.objects.filter(
            status__in=['open', 'full', 'in_progress'],
            reminder_30m_sent=False,
            date_time__gte=now,
            date_time__lte=now + timezone.timedelta(minutes=35)
        )

        sent_count = 0
        for match in matches:
            was_sent = match.reminder_30m_sent
            match._check_and_trigger_30m_reminder()
            if not was_sent and match.reminder_30m_sent:
                sent_count += 1
                self.stdout.write(self.style.SUCCESS(f"Dispatched 30m reminder for match {match.id} (\"{match.title}\")"))

        self.stdout.write(self.style.SUCCESS(f"Finished reminder check. Dispatched reminders for {sent_count} match(es)."))

