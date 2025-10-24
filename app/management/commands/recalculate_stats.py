from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app.models import PlayerStats, Match


class Command(BaseCommand):
    help = 'Recalculate all player stats from scratch based on match winners/losers'

    def handle(self, *args, **options):
        self.stdout.write('Recalculating player stats...')

        # Reset all player stats to 0
        PlayerStats.objects.all().update(
            matches_played=0,
            matches_won=0,
            matches_lost=0,
            total_hours=0.0
        )
        self.stdout.write('Reset all stats to 0')

        # Get all completed matches
        completed_matches = Match.objects.filter(status='completed')
        self.stdout.write(f'Found {completed_matches.count()} completed matches')

        # Recalculate stats from winners/losers M2M relationships
        for match in completed_matches:
            # Calculate match hours
            match_hours = round(match.duration / 60, 1)

            # Process winners
            for winner in match.winners.all():
                if hasattr(winner, 'stats'):
                    winner.stats.matches_played += 1
                    winner.stats.matches_won += 1
                    winner.stats.total_hours += match_hours
                    winner.stats.save()

            # Process losers
            for loser in match.losers.all():
                if hasattr(loser, 'stats'):
                    loser.stats.matches_played += 1
                    loser.stats.matches_lost += 1
                    loser.stats.total_hours += match_hours
                    loser.stats.save()

        # Display results
        self.stdout.write('\n=== Player Stats Summary ===')
        for user in User.objects.filter(stats__isnull=False):
            stats = user.stats
            if stats.matches_played > 0:
                self.stdout.write(
                    f'{user.username}: '
                    f'{stats.matches_played} played, '
                    f'{stats.matches_won} won, '
                    f'{stats.matches_lost} lost, '
                    f'{stats.total_hours}h played '
                    f'({stats.win_rate}% win rate)'
                )

        self.stdout.write(self.style.SUCCESS('\nSuccessfully recalculated all player stats!'))
