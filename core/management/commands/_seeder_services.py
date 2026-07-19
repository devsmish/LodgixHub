import io
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image

from apps.analytics.models import SearchHistory, ViewHistory
from apps.bookings.choices import BookingStatus
from apps.bookings.models import Booking
from apps.content.models import Photo
from apps.listings.choices import (
    ListingStatus,
    ListingType,
    MealType,
    RentalType,
    RoomType,
)
from apps.listings.models import Address, Listing, Room
from apps.pricing.models import PriceHistory
from apps.reviews.models import Review
from apps.security.constants import (
    GROUP_ADMIN,
    GROUP_LANDLORD,
    GROUP_MODERATOR,
    GROUP_TENANT,
)
from apps.users.models import User
from core.management.commands._data_constants import (
    CITIES,
    FAKE_EMAIL_DOMAIN,
    FIRST_NAMES,
    LAST_NAMES,
    LISTING_ADJECTIVES,
    LISTING_FEATURES,
    LISTING_TITLES_BASE,
    REVIEW_COMMENTS_MIXED,
    REVIEW_COMMENTS_POSITIVE,
    STREETS,
)


class DataSeederService:
    def __init__(self, fake_instance, password: str):
        self.fake = fake_instance
        self.password = password
        self._groups = {}

    def run_seeding(self, options, amenities, cancellation_reasons):
        self._groups = {
            name: Group.objects.get_or_create(name=name)[0]
            for name in (GROUP_TENANT, GROUP_LANDLORD, GROUP_MODERATOR, GROUP_ADMIN)
        }

        admin = self._create_admin()
        moderators = self._create_moderators(options["moderators"])
        landlords = self._create_landlords(options["landlords"])
        tenants = self._create_tenants(options["tenants"])

        listings = self._create_listings(
            landlords, options["listings_per_landlord"], amenities
        )
        self._create_photos(listings)

        all_bookable_targets = self._collect_bookable_targets(listings)
        bookings = self._create_bookings(
            all_bookable_targets, tenants, cancellation_reasons
        )
        self._create_reviews(bookings)

        self._create_search_history(tenants, listings)
        self._create_view_history(listings, tenants)

        photos_count = Photo.objects.filter(listing__in=listings).count()
        reviews_count = Review.objects.filter(booking__in=bookings).count()

        return (
            admin,
            moderators,
            landlords,
            tenants,
            listings,
            bookings,
            photos_count,
            reviews_count,
        )

    def _create_admin(self):
        admin, created = User.objects.get_or_create(
            email=f"admin@{FAKE_EMAIL_DOMAIN}",
            defaults={"first_name": "Platform", "last_name": "Admin"},
        )
        if created:
            admin.set_password(self.password)
            admin.is_staff = True
            admin.is_superuser = True
            admin.save()
        admin.groups.add(self._groups[GROUP_ADMIN])
        return admin

    def _create_moderators(self, count):
        moderators = []
        for i in range(count):
            user = self._create_user(f"moderator{i}")
            user.groups.add(self._groups[GROUP_MODERATOR])
            moderators.append(user)
        return moderators

    def _create_landlords(self, count):
        landlords = []
        for i in range(count):
            user = self._create_user(f"landlord{i}")
            user.groups.add(self._groups[GROUP_LANDLORD])
            if random.random() < 0.4:
                user.groups.add(self._groups[GROUP_TENANT])
            landlords.append(user)
        return landlords

    def _create_tenants(self, count):
        tenants = []
        for i in range(count):
            user = self._create_user(f"tenant{i}")
            user.groups.add(self._groups[GROUP_TENANT])
            tenants.append(user)
        return tenants

    def _create_user(self, unique_key):
        first_name, gender = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        email = f"{unique_key}.{first_name.lower()}@{FAKE_EMAIL_DOMAIN}"

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "nickname": "".join(
                    ch for ch in f"{first_name}{last_name}{unique_key}" if ch.isalnum()
                )[:30]
                or "user",
                "gender": gender,
                "phone": "+49" + "".join(str(random.randint(0, 9)) for _ in range(9)),
                "birth_date": self.fake.date_of_birth(minimum_age=19, maximum_age=70),
                "notify_by_email": True,
                "terms_accepted_at": timezone.now(),
            },
        )
        if created:
            user.set_password(self.password)
            user.save()
        return user

    def _create_listings(self, landlords, per_landlord, amenities):
        listings = []
        for landlord in landlords:
            for _ in range(random.randint(1, per_landlord)):
                listing_type = random.choices(
                    [ListingType.APARTMENT, ListingType.HOTEL, ListingType.HOSTEL],
                    weights=[0.6, 0.25, 0.15],
                )[0]

                city, region, district = random.choice(CITIES)
                address = Address.objects.create(
                    country="Germany",
                    region=region,
                    city=city,
                    district=district,
                    street=random.choice(STREETS),
                    house_number=f"{random.randint(1, 99)}{random.choice(['', 'a', 'b'])}",
                    postal_code=str(random.randint(10000, 99999)),
                    floor=(
                        random.randint(0, 8)
                        if listing_type == ListingType.APARTMENT
                        else None
                    ),
                )

                base_price = Decimal(
                    random.choice([45, 60, 75, 90, 110, 140, 180, 220])
                )
                deposit_required = random.random() < 0.4

                listing = Listing.objects.create(
                    owner=landlord,
                    type=listing_type,
                    title=f"{random.choice(LISTING_ADJECTIVES)} {random.choice(LISTING_TITLES_BASE[listing_type])} {random.choice(LISTING_FEATURES)}",
                    description=self.fake.paragraph(nb_sentences=4)[:5000],
                    address=address,
                    max_guests=random.choice([1, 2, 2, 4, 4, 6]),
                    rooms_count=(
                        random.randint(1, 4)
                        if listing_type == ListingType.APARTMENT
                        else None
                    ),
                    current_price=base_price,
                    rental_type=random.choice([RentalType.DAILY, RentalType.ANY]),
                    meal_type=(
                        random.choice(list(MealType))
                        if listing_type != ListingType.APARTMENT
                        else MealType.NONE
                    ),
                    deposit_required=deposit_required,
                    deposit_percent=(
                        random.choice([10, 15, 20]) if deposit_required else 0
                    ),
                    deposit_refundable=deposit_required and random.random() < 0.7,
                    status=random.choices(
                        [ListingStatus.PUBLISHED, ListingStatus.DRAFT],
                        weights=[0.85, 0.15],
                    )[0],
                    is_active=True,
                )

                PriceHistory.objects.create(
                    listing=listing,
                    price=base_price,
                    valid_from=timezone.localdate(),
                    changed_by=landlord,
                )
                listing.amenities.set(
                    random.sample(
                        amenities, k=min(len(amenities), random.randint(3, 8))
                    )
                )
                listings.append(listing)

                if listing_type != ListingType.APARTMENT:
                    self._create_rooms(listing)
        return listings

    def _create_rooms(self, listing):
        mapping = {
            RoomType.SINGLE: 1,
            RoomType.DOUBLE: 2,
            RoomType.TWIN: 2,
            RoomType.TRIPLE: 3,
            RoomType.QUAD: 4,
            RoomType.SUITE: 4,
        }
        for room_type in random.sample(list(RoomType), k=random.randint(2, 4)):
            Room.objects.create(
                listing=listing,
                room_type=room_type,
                name=f"{room_type.label} #{random.randint(1, 20)}",
                max_guests=mapping.get(room_type, 2),
                rooms_available_count=random.randint(1, 5),
            )

    def _create_photos(self, listings):
        for listing in listings:
            for i in range(random.randint(3, 5)):
                buffer = io.BytesIO()
                Image.new(
                    "RGB", (800, 600), tuple(random.randint(60, 220) for _ in range(3))
                ).save(buffer, format="JPEG")
                Photo.objects.create(
                    listing=listing,
                    uploaded_by=listing.owner,
                    order=i,
                    is_primary=(i == 0),
                    image=ContentFile(buffer.getvalue(), name=f"{listing.id}-{i}.jpg"),
                    caption=random.choice(["", "Wohnzimmer", "Blick vom Balkon"]),
                )

    def _collect_bookable_targets(self, listings):
        targets = []
        for l in listings:
            if l.type == ListingType.APARTMENT:
                targets.append((l, None))
            else:
                for r in l.rooms.all():
                    targets.append((l, r))
        return targets

    def _create_bookings(self, targets, tenants, cancellation_reasons):
        bookings = []
        today = timezone.localdate()

        for listing, room in targets:
            tenant = random.choice(tenants)

            # Past Completed
            days_ago = random.randint(1, 6)
            past_in, past_out = today - timedelta(days=days_ago + 2), today - timedelta(
                days=days_ago
            )
            completed = Booking(
                tenant=tenant,
                listing=listing if room is None else None,
                room=room,
                status=BookingStatus.COMPLETED,
                check_in_date=past_in,
                check_out_date=past_out,
                guests_count=1,
                total_price=(
                    listing.current_price * (past_out - past_in).days
                ).quantize(Decimal("0.01")),
            )
            Booking.objects.bulk_create([completed])
            bookings.append(completed)

            # Future Confirmed
            f_in, f_out = today + timedelta(days=10), today + timedelta(days=13)
            try:
                b = Booking.objects.create(
                    tenant=random.choice(tenants),
                    listing=listing if room is None else None,
                    room=room,
                    status=BookingStatus.CONFIRMED,
                    check_in_date=f_in,
                    check_out_date=f_out,
                    guests_count=1,
                    total_price=(listing.current_price * (f_out - f_in).days).quantize(
                        Decimal("0.01")
                    ),
                    confirmed_at=timezone.now(),
                )
                bookings.append(b)
            except Exception:
                continue
        return bookings

    def _create_reviews(self, bookings):
        completed = [b for b in bookings if b.status == BookingStatus.COMPLETED]
        for booking in completed:
            if random.random() < 0.15:
                continue
            rating = random.choices([5, 4, 3], weights=[0.6, 0.3, 0.1])[0]
            review = Review.objects.create(
                booking=booking,
                author=booking.tenant,
                rating=rating,
                status="published",
                comment=random.choice(
                    REVIEW_COMMENTS_POSITIVE if rating >= 4 else REVIEW_COMMENTS_MIXED
                ),
            )
            if random.random() < 0.3:
                review.landlord_response = "Vielen Dank!"
                from django.db.models import Model

                Model.save(review, update_fields=["landlord_response", "updated_at"])

    def _create_search_history(self, tenants, listings):
        keywords = list({l.address.city.lower() for l in listings}) + [
            "wohnung",
            "hotel",
        ]
        for _ in range(40):
            SearchHistory.objects.create(
                user=random.choice(tenants) if random.random() < 0.7 else None,
                keyword=random.choice(keywords),
                results_count=random.randint(1, 10),
            )

    def _create_view_history(self, listings, tenants):
        for l in listings:
            for _ in range(random.randint(2, 5)):
                user = random.choice(tenants) if random.random() < 0.6 else None
                ViewHistory.objects.create(
                    listing=l,
                    user=user,
                    session_key=None if user else self.fake.uuid4()[:32],
                )
