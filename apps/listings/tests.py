from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.listings.choices import ListingStatus, ListingType, RoomType
from apps.listings.models import Listing, Room

User = get_user_model()


class ListingModelTestCase(TestCase):
    """
    Testing validation and constraints for the base listing model.
    """

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", password="securepassword123"
        )
        self.valid_listing_data = {
            "owner": self.owner,
            "title": "Test Real Estate",
            "description": "Description object",
            "type": ListingType.APARTMENT,
            "status": ListingStatus.DRAFT,
            "latitude": Decimal("55.7558"),
            "longitude": Decimal("37.6173"),
            "max_guests": 2,
            "price_per_night": Decimal("3500.00"),
        }

    def test_create_valid_listing(self):
        """Verification of the successful creation of a valid advertisement and UUID inheritance."""
        listing = Listing.objects.create(**self.valid_listing_data)

        self.assertIsNotNone(listing.id)
        self.assertEqual(len(str(listing.id)), 36)
        self.assertIsNotNone(listing.created_at)
        self.assertEqual(listing.status, ListingStatus.DRAFT)

    def test_latitude_boundaries(self):
        """Validation check for the latitude range [-90, 90]."""
        self.valid_listing_data["latitude"] = Decimal("-90.0001")
        listing_invalid_low = Listing(**self.valid_listing_data)
        with self.assertRaises(ValidationError):
            listing_invalid_low.full_clean()

        self.valid_listing_data["latitude"] = Decimal("90.0001")
        listing_invalid_high = Listing(**self.valid_listing_data)
        with self.assertRaises(ValidationError):
            listing_invalid_high.full_clean()

    def test_longitude_boundaries(self):
        """Validation check for the longitude range [-180, 180]."""
        self.valid_listing_data["longitude"] = Decimal("-180.0001")
        listing_invalid_low = Listing(**self.valid_listing_data)
        with self.assertRaises(ValidationError):
            listing_invalid_low.full_clean()

        self.valid_listing_data["longitude"] = Decimal("180.0001")
        listing_invalid_high = Listing(**self.valid_listing_data)
        with self.assertRaises(ValidationError):
            listing_invalid_high.full_clean()

    def test_listing_max_guests_minimum_constraint(self):
        """Check for the listing capacity limit (max_guests >= 1)."""
        self.valid_listing_data["max_guests"] = 0
        listing = Listing(**self.valid_listing_data)

        with self.assertRaises(ValidationError):
            listing.full_clean()


class RoomModelTestCase(TestCase):
    """
    Testing business logic and constraints for Room.
    """

    def setUp(self):
        self.owner = User.objects.create_user(
            email="manager@example.com", password="securepassword123"
        )

        self.hotel_listing = Listing.objects.create(
            owner=self.owner,
            title="Grand Hotel Plaza",
            type=ListingType.HOTEL,
            latitude=Decimal("45.0000"),
            longitude=Decimal("45.0000"),
            max_guests=20,
            price_per_night=Decimal("8000.00"),
        )

        self.apartment_listing = Listing.objects.create(
            owner=self.owner,
            title="Cozy studio",
            type=ListingType.APARTMENT,
            latitude=Decimal("46.0000"),
            longitude=Decimal("46.0000"),
            max_guests=4,
            price_per_night=Decimal("4000.00"),
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
        """Verification that clean() prevents linking a room to an APARTMENT and raises a ValidationError."""
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
