from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.listings.choices import ListingStatus, ListingType, RoomType
from apps.listings.models import Address, Amenity, Listing, ListingAmenity, Room

User = get_user_model()


def make_address(**overrides):
    """A common helper — the Address is mandatory for any Listing."""
    defaults = {
        "region": "Saarland",
        "city": "Saarlouis",
        "street": "Kaiser-Wilhelm-Straße",
        "house_number": "12",
        "postal_code": "66740",
    }
    defaults.update(overrides)
    return Address.objects.create(**defaults)


class AddressModelTestCase(TestCase):

    def test_latitude_boundaries(self):
        address = Address(
            **{
                "region": "Saarland",
                "city": "Saarlouis",
                "street": "Teststraße",
                "house_number": "1",
                "postal_code": "66740",
                "latitude": Decimal("-90.0001"),
                "longitude": Decimal("0"),
            }
        )
        with self.assertRaises(ValidationError):
            address.full_clean()

        address.latitude = Decimal("90.0001")
        with self.assertRaises(ValidationError):
            address.full_clean()

    def test_longitude_boundaries(self):
        address = Address(
            **{
                "region": "Saarland",
                "city": "Saarlouis",
                "street": "Teststraße",
                "house_number": "1",
                "postal_code": "66740",
                "latitude": Decimal("0"),
                "longitude": Decimal("-180.0001"),
            }
        )
        with self.assertRaises(ValidationError):
            address.full_clean()

        address.longitude = Decimal("180.0001")
        with self.assertRaises(ValidationError):
            address.full_clean()

    def test_latitude_longitude_optional(self):
        address = Address(
            **{
                "region": "Saarland",
                "city": "Saarlouis",
                "street": "Teststraße",
                "house_number": "1",
                "postal_code": "66740",
                "latitude": Decimal("49.3137"),
                "longitude": Decimal("6.7515"),
            }
        )
        address.full_clean()


class ListingModelTestCase(TestCase):
    """Testing validation and constraints for the base listing model."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", password="securepassword123"
        )
        self.address = make_address()
        self.valid_listing_data = {
            "owner": self.owner,
            "title": "Test Real Estate",
            "description": "Description object",
            "type": ListingType.APARTMENT,
            "status": ListingStatus.DRAFT,
            "address": self.address,
            "max_guests": 2,
            "current_price": Decimal("3500.00"),
        }

    def test_create_valid_listing(self):
        """Verification of the successful creation of
        a valid advertisement and UUID inheritance."""
        listing = Listing.objects.create(**self.valid_listing_data)

        self.assertIsNotNone(listing.id)
        self.assertEqual(len(str(listing.id)), 36)
        self.assertIsNotNone(listing.created_at)
        self.assertEqual(listing.status, ListingStatus.DRAFT)
        self.assertTrue(listing.is_active)
        self.assertIsNone(listing.deleted_at)

    def test_listing_max_guests_minimum_constraint(self):
        """Check for the listing capacity limit (max_guests >= 1)."""
        self.valid_listing_data["max_guests"] = 0
        listing = Listing(**self.valid_listing_data)

        with self.assertRaises(ValidationError):
            listing.full_clean()

    def test_deposit_percent_range_constraint(self):
        """deposit_percent must be in the range of 0–100."""
        self.valid_listing_data["deposit_percent"] = 150
        listing = Listing(**self.valid_listing_data)

        with self.assertRaises(ValidationError):
            listing.full_clean()

    def test_rooms_count_only_for_apartment_type(self):
        """rooms_count is forbidden for type != apartment (clean())."""
        self.valid_listing_data["type"] = ListingType.HOTEL
        self.valid_listing_data["rooms_count"] = 5
        listing = Listing(**self.valid_listing_data)

        with self.assertRaises(ValidationError) as context:
            listing.full_clean()
        self.assertIn("rooms_count", context.exception.message_dict)

    def test_rooms_count_allowed_for_apartment(self):
        self.valid_listing_data["rooms_count"] = 3
        listing = Listing.objects.create(**self.valid_listing_data)
        self.assertEqual(listing.rooms_count, 3)

    def test_soft_delete_via_base_model(self):
        listing = Listing.objects.create(**self.valid_listing_data)

        listing.delete()

        self.assertIsNotNone(listing.deleted_at)
        self.assertNotIn(listing, Listing.objects.all())
        self.assertIn(listing, Listing.all_objects.all())

        listing.restore()
        self.assertIn(listing, Listing.objects.all())

    def test_increment_views_count_bypasses_full_clean(self):
        listing = Listing.objects.create(**self.valid_listing_data)
        self.assertEqual(listing.views_count, 0)

        listing.increment_views_count()
        listing.refresh_from_db()

        self.assertEqual(listing.views_count, 1)


class RoomModelTestCase(TestCase):
    """Testing business logic and constraints for Room."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="manager@example.com", password="securepassword123"
        )

        self.hotel_listing = Listing.objects.create(
            owner=self.owner,
            title="Grand Hotel Plaza",
            type=ListingType.HOTEL,
            address=make_address(
                city="Berlin", street="Alexanderplatz", house_number="1"
            ),
            max_guests=16,
            current_price=Decimal("8000.00"),
        )

        self.apartment_listing = Listing.objects.create(
            owner=self.owner,
            title="Cozy studio",
            type=ListingType.APARTMENT,
            address=make_address(city="Munich", street="Marienplatz", house_number="2"),
            max_guests=4,
            current_price=Decimal("4000.00"),
        )

    def test_attach_room_to_hotel_success(self):
        """Verification of the successful addition of a room to a HOTEL/HOSTEL type listing."""
        room = Room.objects.create(
            listing=self.hotel_listing,
            room_type=RoomType.SINGLE,
            name="Room 101",
            max_guests=2,
        )

        self.assertIsNotNone(room.id)
        self.assertEqual(room.listing, self.hotel_listing)
        # Verification that soft deletion from BaseModel works (the room is active by default)
        self.assertIsNone(room.deleted_at)

    def test_attach_room_to_apartment_raises_validation_error(self):
        """Verification that clean() prevents linking a room
        to an APARTMENT and raises a ValidationError."""
        room = Room(
            listing=self.apartment_listing,
            room_type=RoomType.SINGLE,
            name="Invalid Room",
            max_guests=1,
        )

        # Since the full_clean() method is forcibly called within save(),
        # an error occurs right during the execution of the .save() method.
        with self.assertRaises(ValidationError) as context:
            room.save()

        # Check that the error points to the invalid 'listing' field.
        self.assertIn("listing", context.exception.message_dict)
        self.assertEqual(
            context.exception.message_dict["listing"][0],
            "Cannot attach individual rooms to an APARTMENT listing type.",
        )

    def test_room_max_guests_minimum_constraint(self):
        """Check of the capacity limit for a specific room (max_guests >= 1)."""
        room = Room(
            listing=self.hotel_listing,
            room_type=RoomType.SINGLE,
            name="Empty room",
            max_guests=0,
        )

        with self.assertRaises(ValidationError):
            room.save()


class ListingAmenityModelTestCase(TestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="host@example.com", password="securepassword123"
        )
        self.listing = Listing.objects.create(
            owner=self.owner,
            title="Test Listing",
            type=ListingType.APARTMENT,
            address=make_address(),
            max_guests=2,
            current_price=Decimal("1000.00"),
        )
        self.amenity = Amenity.objects.get(slug="wifi")

    def test_duplicate_listing_amenity_raises_integrity_error(self):
        ListingAmenity.objects.create(listing=self.listing, amenity=self.amenity)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ListingAmenity.objects.create(
                    listing=self.listing, amenity=self.amenity
                )

    def test_amenity_group_autoset_on_save(self):
        """Amenity.save(): StandardAmenity.get_group_for_slug."""
        wifi = Amenity.objects.get(slug="wifi")
        self.assertEqual(wifi.group, "basic")
