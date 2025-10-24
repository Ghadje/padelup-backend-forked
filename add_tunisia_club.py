"""
Add a club near user's test location in Tunisia
"""
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from app.models import Club, Court

# Club near user's location (Tunisia - Sfax area)
tunisia_club = {
    "name": "Sfax Padel Club",
    "address": "Avenue Habib Bourguiba, Sfax",
    "city": "Sfax",
    "postal_code": "3000",
    "latitude": Decimal("34.740000"),  # Near user's coordinates
    "longitude": Decimal("10.760000"),  # Near user's coordinates
    "phone": "+216 74 123 456",
    "email": "info@sfaxpadel.tn",
    "website": "https://sfaxpadel.tn",
    "opening_hours": {
        "monday": "08:00-22:00",
        "tuesday": "08:00-22:00",
        "wednesday": "08:00-22:00",
        "thursday": "08:00-22:00",
        "friday": "08:00-23:00",
        "saturday": "09:00-23:00",
        "sunday": "09:00-21:00"
    },
    "amenities": ["Parking", "Lockers", "Showers", "Cafeteria", "WiFi", "Air Conditioning"],
    "price_min": Decimal("15.00"),
    "price_max": Decimal("40.00"),
    "currency": "TND",
    "is_partner": True,
}

# Another club closer to exact user coordinates
tunisia_club2 = {
    "name": "Padel Tunisia Central",
    "address": "Route de Tunis, KM 5",
    "city": "Sfax",
    "postal_code": "3001",
    "latitude": Decimal("33.627895"),  # Exact user coordinates
    "longitude": Decimal("10.280188"),  # Exact user coordinates
    "phone": "+216 74 789 012",
    "email": "contact@padeltunisia.tn",
    "website": "https://padeltunisia.tn",
    "opening_hours": {
        "monday": "07:00-23:00",
        "tuesday": "07:00-23:00",
        "wednesday": "07:00-23:00",
        "thursday": "07:00-23:00",
        "friday": "07:00-00:00",
        "saturday": "08:00-00:00",
        "sunday": "08:00-22:00"
    },
    "amenities": ["Indoor Courts", "Parking", "Restaurant", "Pro Shop", "WiFi"],
    "price_min": Decimal("20.00"),
    "price_max": Decimal("50.00"),
    "currency": "TND",
    "is_partner": False,
}

def add_tunisia_clubs():
    clubs_data = [tunisia_club, tunisia_club2]

    for club_data in clubs_data:
        club, created = Club.objects.get_or_create(
            name=club_data["name"],
            defaults=club_data
        )

        if created:
            print(f"Created club: {club.name}")

            # Add courts
            for i in range(1, 4):
                court_type = "glass" if i == 1 else ("panoramic" if i == 2 else "outdoor")
                court = Court.objects.create(
                    club=club,
                    name=f"Court {i}",
                    court_type=court_type,
                    is_indoor=court_type != "outdoor",
                    is_available=True,
                    price_per_hour=Decimal("30.00"),
                    features=["LED Lighting", "Climate Control"] if court_type != "outdoor" else ["Natural Light"],
                    prices={
                        "morning": 25,
                        "afternoon": 30,
                        "evening": 35,
                        "weekend": 40
                    }
                )
                print(f"  - Added {court.name} ({court_type})")
        else:
            print(f"Club already exists: {club.name}")

    total_clubs = Club.objects.count()
    print(f"\nTotal clubs in database: {total_clubs}")

if __name__ == "__main__":
    add_tunisia_clubs()