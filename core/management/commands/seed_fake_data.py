import os
import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from faker import Faker

from apps.bookings.models import CancellationReason
from apps.listings.models import Amenity

from ._seeder_services import DataSeederService


class Command(BaseCommand):
    help = "Populates the database with realistic fake data for manual testing."

    def add_arguments(self, parser):
        parser.add_argument("--landlords", type=int, default=70)
        parser.add_argument("--tenants", type=int, default=100)
        parser.add_argument("--moderators", type=int, default=3)
        parser.add_argument("--listings-per-landlord", type=int, default=2)
        parser.add_argument("--seed", type=int, default=43)

    def handle(self, *args, **options):
        # Safety validation
        faker_password = os.getenv("FAKER_USER_PASSWORD")
        if not faker_password:
            raise CommandError(
                "Critical error: The FAKER_USER_PASSWORD environment variable is not set!\n"
                "Please add it to your .env file or export it before running: "
                "export FAKER_USER_PASSWORD='your_strong_password'"
            )

        # Generator initialization
        random.seed(options["seed"])
        fake = Faker("de_DE")
        Faker.seed(options["seed"])

        # Caches the data required for generation (read once).
        amenities = list(Amenity.objects.all())
        cancellation_reasons = list(CancellationReason.objects.all())

        # Initializes an isolated service.
        seeder = DataSeederService(fake_instance=fake, password=faker_password)

        with transaction.atomic():
            (
                admin,
                moderators,
                landlords,
                tenants,
                listings,
                bookings,
                photos_count,
                reviews_count,
            ) = seeder.run_seeding(
                options=options,
                amenities=amenities,
                cancellation_reasons=cancellation_reasons,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"🎉 Done! The database has been successfully populated with test data.\n"
                f"📊 Statistics of created objects:\n"
                f"  ├── 👤 Users:\n"
                f"  │    ├── Administrators: 1\n"
                f"  │    ├── Moderators:     {len(moderators)}\n"
                f"  │    ├── Landlords:      {len(landlords)}\n"
                f"  │    └── Tenants:        {len(tenants)}\n"
                f"  ├── 🏠 Listings:\n"
                f"  │    ├── Listings:       {len(listings)}\n"
                f"  │    └── Photos (Media): {photos_count}\n"
                f"  └── 📈 Activity:\n"
                f"       ├── Bookings:       {len(bookings)}\n"
                f"       └── Reviews:        {reviews_count}\n"
                f"🔒 All user passwords are securely set from FAKER_USER_PASSWORD."
            )
        )
