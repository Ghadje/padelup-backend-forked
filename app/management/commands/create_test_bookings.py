from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, time
from app.models import Booking, Court, Club
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates test bookings for development'

    def handle(self, *args, **kwargs):
        users = User.objects.all()
        if not users.exists():
            self.stdout.write(self.style.ERROR('No users found. Please create users first.'))
            return

        courts = Court.objects.all()
        if not courts.exists():
            self.stdout.write(self.style.ERROR('No courts found. Please add clubs and courts first.'))
            return

        statuses = ['pending', 'confirmed', 'completed', 'cancelled']
        bookings_created = 0

        # Create 15-20 random bookings
        for i in range(20):
            court = random.choice(courts)
            user = random.choice(users)
            
            # Random date within next 30 days or past 7 days
            days_offset = random.randint(-7, 30)
            booking_date = timezone.now().date() + timedelta(days=days_offset)
            
            # Random start time between 8:00 and 20:00
            start_hour = random.randint(8, 20)
            start_time = time(hour=start_hour, minute=0)
            
            duration = random.choice([60, 90, 120])
            end_time = (timezone.now().replace(hour=start_hour, minute=0) + timedelta(minutes=duration)).time()

            # Determine status based on date
            if booking_date < timezone.now().date():
                status = random.choice(['completed', 'cancelled'])
            else:
                status = random.choice(['pending', 'confirmed', 'cancelled'])

            try:
                booking = Booking.objects.create(
                    court=court,
                    user=user,
                    date=booking_date,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    status=status,
                    currency='EUR',
                    payment_status='paid' if status in ['confirmed', 'completed'] else 'pending'
                )
                booking.calculate_total()
                booking.save()
                bookings_created += 1
            except Exception as e:
                # Might fail due to unique_together constraint (court, date, start_time)
                continue

        self.stdout.write(self.style.SUCCESS(f'Successfully created {bookings_created} test bookings'))
