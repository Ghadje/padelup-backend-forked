from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from app.models import Match, MatchParticipant, Club, Court
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates test matches for development'

    def handle(self, *args, **kwargs):
        # Get or create test users
        test_user, _ = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'testuser@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        test_user.set_password('password123')
        test_user.save()

        other_users = []
        for i in range(1, 6):
            user, _ = User.objects.get_or_create(
                username=f'player{i}',
                defaults={
                    'email': f'player{i}@example.com',
                    'first_name': f'Player',
                    'last_name': f'{i}'
                }
            )
            user.set_password('password123')
            user.save()
            other_users.append(user)

        # Get available clubs and courts
        clubs = Club.objects.all()
        if not clubs:
            self.stdout.write(self.style.ERROR('No clubs found. Please add clubs first.'))
            return

        # Match types
        match_types = ['casual', 'competitive', 'tournament', 'training']

        # Create various matches
        matches_created = 0

        for club in clubs[:3]:  # Use first 3 clubs
            courts = Court.objects.filter(club=club)
            if not courts:
                continue

            for i in range(3):  # Create 3 matches per club
                court = random.choice(courts)

                # Vary the match timing
                days_ahead = random.randint(1, 14)
                hours = random.choice([9, 11, 14, 16, 18, 20])

                match = Match.objects.create(
                    title=f"{random.choice(['Morning', 'Afternoon', 'Evening'])} {random.choice(['Friendly', 'Competitive', 'Training', 'Tournament'])} Match",
                    description=f"Join us for an exciting padel match at {club.name}!",
                    organizer=random.choice([test_user] + other_users[:2]),
                    club=club,
                    court=court,
                    date_time=timezone.now() + timedelta(days=days_ahead, hours=hours),
                    duration=random.choice([60, 90, 120]),
                    match_type=random.choice(match_types),
                    status='open',
                    is_open=True,
                    is_public=True,
                    max_players=4,
                    min_skill_level=random.randint(1, 3),
                    max_skill_level=random.randint(7, 10),
                    price_per_player=random.choice([15.0, 20.0, 25.0, 30.0]),
                    currency='EUR'
                )

                # Add some participants
                num_participants = random.randint(0, 2)
                available_users = [u for u in other_users if u != match.organizer]

                for j in range(min(num_participants, len(available_users))):
                    MatchParticipant.objects.create(
                        match=match,
                        user=available_users[j],
                        status='confirmed'
                    )

                # Update match status if full
                if match.participants.filter(status='confirmed').count() >= 3:
                    match.status = 'full'
                    match.is_open = False
                    match.save()

                matches_created += 1

        # Create some past matches (completed)
        for i in range(3):
            club = random.choice(clubs)
            courts = Court.objects.filter(club=club)
            if not courts:
                continue

            court = random.choice(courts)

            match = Match.objects.create(
                title=f"Completed Match #{i+1}",
                description="This match has been completed.",
                organizer=test_user,
                club=club,
                court=court,
                date_time=timezone.now() - timedelta(days=random.randint(1, 7)),
                duration=90,
                match_type='casual',
                status='completed',
                is_open=False,
                is_public=True,
                max_players=4,
                min_skill_level=1,
                max_skill_level=10,
                price_per_player=20.0,
                currency='EUR'
            )

            # Add participants
            for user in other_users[:3]:
                MatchParticipant.objects.create(
                    match=match,
                    user=user,
                    status='confirmed'
                )

            matches_created += 1

        # Create some private matches
        for i in range(2):
            club = random.choice(clubs)
            courts = Court.objects.filter(club=club)
            if not courts:
                continue

            court = random.choice(courts)

            match = Match.objects.create(
                title=f"Private Match - Invite Only",
                description="This is a private match for invited players only.",
                organizer=test_user,
                club=club,
                court=court,
                date_time=timezone.now() + timedelta(days=random.randint(1, 7)),
                duration=90,
                match_type='competitive',
                status='open',
                is_open=True,
                is_public=False,  # Private match
                max_players=4,
                min_skill_level=5,
                max_skill_level=10,
                price_per_player=25.0,
                currency='EUR'
            )

            matches_created += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully created {matches_created} test matches'))

        # Print login info
        self.stdout.write(self.style.SUCCESS('\nTest user credentials:'))
        self.stdout.write(self.style.SUCCESS('Username: testuser'))
        self.stdout.write(self.style.SUCCESS('Password: password123'))