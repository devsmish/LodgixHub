from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.content.models import Photo
from apps.listings.models import Listing, Room

User = get_user_model()


class PhotoModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="test@example.com")
        self.listing = Listing.objects.create(
            owner=self.user,
            title="Test Hotel",
            type="hotel",
            latitude=0.0,
            longitude=0.0,
            max_guests=2,
            price_per_night=100.0,
        )
        self.room = Room.objects.create(
            listing=self.listing, name="Room 101", max_guests=2
        )

    def test_photo_valid_listing(self):
        photo = Photo(listing=self.listing, image="test.jpg")
        photo.full_clean()

    def test_photo_xor_fail(self):
        # Error: no binding
        with self.assertRaises(ValidationError):
            Photo(image="test.jpg").full_clean()

        # Error: both bindings
        with self.assertRaises(ValidationError):
            Photo(listing=self.listing, room=self.room, image="test.jpg").full_clean()
