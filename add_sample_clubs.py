"""
Script to add sample clubs to the database for testing geolocation
"""
import os
import django
import json
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from app.models import Club, Court

# Sample clubs with real-world coordinates
clubs_data = [
    {
        "name": "Padel Madrid Central",
        "address": "Calle Mayor, 45",
        "city": "Madrid",
        "postal_code": "28013",
        "latitude": Decimal("40.416775"),
        "longitude": Decimal("-3.703790"),
        "phone": "+34 915 123 456",
        "email": "info@padelmadrid.com",
        "website": "https://padelmadrid.com",
        "opening_hours": {
            "monday": "07:00-23:00",
            "tuesday": "07:00-23:00",
            "wednesday": "07:00-23:00",
            "thursday": "07:00-23:00",
            "friday": "07:00-00:00",
            "saturday": "08:00-00:00",
            "sunday": "08:00-22:00"
        },
        "amenities": ["Parking", "Lockers", "Showers", "Shop", "Bar", "WiFi", "Pro Shop"],
        "price_min": Decimal("25.00"),
        "price_max": Decimal("70.00"),
        "currency": "EUR",
        "is_partner": True,
    },
    {
        "name": "Valencia Padel Club",
        "address": "Avenida del Puerto, 200",
        "city": "Valencia",
        "postal_code": "46023",
        "latitude": Decimal("39.469907"),
        "longitude": Decimal("-0.376288"),
        "phone": "+34 963 456 789",
        "email": "contact@valenciapadel.es",
        "website": "https://valenciapadel.es",
        "opening_hours": {
            "monday": "08:00-22:00",
            "tuesday": "08:00-22:00",
            "wednesday": "08:00-22:00",
            "thursday": "08:00-22:00",
            "friday": "08:00-23:00",
            "saturday": "09:00-23:00",
            "sunday": "09:00-21:00"
        },
        "amenities": ["Parking", "Showers", "Restaurant", "WiFi"],
        "price_min": Decimal("18.00"),
        "price_max": Decimal("50.00"),
        "currency": "EUR",
        "is_partner": False,
    },
    {
        "name": "Sevilla Padel Arena",
        "address": "Calle Torneo, 75",
        "city": "Sevilla",
        "postal_code": "41002",
        "latitude": Decimal("37.389092"),
        "longitude": Decimal("-5.984459"),
        "phone": "+34 954 789 012",
        "email": "hola@sevillapadel.com",
        "website": "https://sevillapadel.com",
        "opening_hours": {
            "monday": "08:00-22:00",
            "tuesday": "08:00-22:00",
            "wednesday": "08:00-22:00",
            "thursday": "08:00-22:00",
            "friday": "08:00-23:00",
            "saturday": "09:00-23:00",
            "sunday": "10:00-20:00"
        },
        "amenities": ["Parking", "Lockers", "Showers", "Cafeteria"],
        "price_min": Decimal("20.00"),
        "price_max": Decimal("55.00"),
        "currency": "EUR",
        "is_partner": True,
    },
    {
        "name": "Bilbao Padel Sports",
        "address": "Gran Vía, 35",
        "city": "Bilbao",
        "postal_code": "48009",
        "latitude": Decimal("43.263012"),
        "longitude": Decimal("-2.934985"),
        "phone": "+34 944 234 567",
        "email": "info@bilbaopadel.com",
        "website": "https://bilbaopadel.com",
        "opening_hours": {
            "monday": "07:00-22:00",
            "tuesday": "07:00-22:00",
            "wednesday": "07:00-22:00",
            "thursday": "07:00-22:00",
            "friday": "07:00-23:00",
            "saturday": "08:00-23:00",
            "sunday": "09:00-21:00"
        },
        "amenities": ["Indoor Courts", "Parking", "Showers", "Shop", "Restaurant"],
        "price_min": Decimal("22.00"),
        "price_max": Decimal("60.00"),
        "currency": "EUR",
        "is_partner": False,
    },
    {
        "name": "Barcelona Beach Padel",
        "address": "Passeig Marítim, 10",
        "city": "Barcelona",
        "postal_code": "08003",
        "latitude": Decimal("41.377200"),
        "longitude": Decimal("2.189300"),
        "phone": "+34 932 456 789",
        "email": "beach@barcelonapadel.com",
        "website": "https://beachpadel.com",
        "opening_hours": {
            "monday": "08:00-22:00",
            "tuesday": "08:00-22:00",
            "wednesday": "08:00-22:00",
            "thursday": "08:00-22:00",
            "friday": "08:00-23:00",
            "saturday": "08:00-23:00",
            "sunday": "09:00-22:00"
        },
        "amenities": ["Beach View", "Parking", "Showers", "Beach Bar", "WiFi"],
        "price_min": Decimal("28.00"),
        "price_max": Decimal("65.00"),
        "currency": "EUR",
        "is_partner": True,
    },
    {
        "name": "Málaga Padel Resort",
        "address": "Camino de San Rafael, 50",
        "city": "Málaga",
        "postal_code": "29006",
        "latitude": Decimal("36.721261"),
        "longitude": Decimal("-4.421265"),
        "phone": "+34 952 345 678",
        "email": "resort@malagapadel.es",
        "website": "https://malagapadel.es",
        "opening_hours": {
            "monday": "07:00-23:00",
            "tuesday": "07:00-23:00",
            "wednesday": "07:00-23:00",
            "thursday": "07:00-23:00",
            "friday": "07:00-00:00",
            "saturday": "08:00-00:00",
            "sunday": "08:00-23:00"
        },
        "amenities": ["Resort", "Pool", "Spa", "Restaurant", "Hotel", "Pro Shop", "WiFi"],
        "price_min": Decimal("30.00"),
        "price_max": Decimal("80.00"),
        "currency": "EUR",
        "is_partner": True,
    },
    {
        "name": "Zaragoza Padel Center",
        "address": "Avenida Cesareo Alierta, 120",
        "city": "Zaragoza",
        "postal_code": "50013",
        "latitude": Decimal("41.649693"),
        "longitude": Decimal("-0.877566"),
        "phone": "+34 976 567 890",
        "email": "center@zaragozapadel.com",
        "website": "https://zaragozapadel.com",
        "opening_hours": {
            "monday": "08:00-22:00",
            "tuesday": "08:00-22:00",
            "wednesday": "08:00-22:00",
            "thursday": "08:00-22:00",
            "friday": "08:00-23:00",
            "saturday": "09:00-23:00",
            "sunday": "09:00-21:00"
        },
        "amenities": ["Parking", "Lockers", "Showers", "Cafeteria", "WiFi"],
        "price_min": Decimal("18.00"),
        "price_max": Decimal("45.00"),
        "currency": "EUR",
        "is_partner": False,
    },
    {
        "name": "Palma Padel Paradise",
        "address": "Carrer de Sant Miquel, 80",
        "city": "Palma de Mallorca",
        "postal_code": "07002",
        "latitude": Decimal("39.571669"),
        "longitude": Decimal("2.650211"),
        "phone": "+34 971 234 567",
        "email": "paradise@palmapadel.com",
        "website": "https://palmapadel.com",
        "opening_hours": {
            "monday": "07:00-23:00",
            "tuesday": "07:00-23:00",
            "wednesday": "07:00-23:00",
            "thursday": "07:00-23:00",
            "friday": "07:00-00:00",
            "saturday": "08:00-00:00",
            "sunday": "08:00-22:00"
        },
        "amenities": ["Sea View", "Parking", "Pool", "Restaurant", "Bar", "Shop", "WiFi"],
        "price_min": Decimal("35.00"),
        "price_max": Decimal("90.00"),
        "currency": "EUR",
        "is_partner": True,
    }
]

# Court types for variety
court_types = ["glass", "panoramic", "outdoor", "indoor"]
court_features = [
    ["LED Lighting", "Air Conditioning", "Premium Surface"],
    ["Panoramic View", "Natural Light", "Pro Surface"],
    ["Open Air", "Natural Grass Surroundings"],
    ["Climate Control", "Sound System", "Video Recording"]
]

def add_clubs():
    created_count = 0
    for club_data in clubs_data:
        club, created = Club.objects.get_or_create(
            name=club_data["name"],
            defaults=club_data
        )

        if created:
            created_count += 1
            print(f"Created club: {club.name}")

            # Add 2-4 courts for each club
            import random
            num_courts = random.randint(2, 4)

            for i in range(1, num_courts + 1):
                court_type = court_types[(i-1) % len(court_types)]
                features = court_features[(i-1) % len(court_features)]

                court = Court.objects.create(
                    club=club,
                    name=f"Court {i}",
                    court_type=court_type,
                    is_indoor=court_type != "outdoor",
                    is_available=True,
                    price_per_hour=Decimal(str(random.uniform(25, 60))),
                    features=features,
                    prices={
                        "morning": random.randint(20, 35),
                        "afternoon": random.randint(30, 45),
                        "evening": random.randint(35, 55),
                        "weekend": random.randint(40, 65)
                    }
                )
                print(f"  - Added {court.name} ({court_type})")
        else:
            print(f"Club already exists: {club.name}")

    total_clubs = Club.objects.count()
    print(f"\nTotal clubs in database: {total_clubs}")
    print(f"New clubs added: {created_count}")

if __name__ == "__main__":
    add_clubs()