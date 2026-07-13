import io
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from apps.content.constants import MAX_PHOTOS_PER_LISTING
from apps.content.models import Photo
from apps.listings.choices import ListingType
from apps.listings.models import Address, Listing, Room

User = get_user_model()


def make_test_image(name="test.jpg", size=(500, 500), fmt="JPEG"):
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(200, 50, 50)).save(buffer, format=fmt)
    buffer.seek(0)
    content_type = "image/jpeg" if fmt == "JPEG" else f"image/{fmt.lower()}"
    return SimpleUploadedFile(name, buffer.read(), content_type=content_type)


def make_address(**overrides):
    defaults = {
        "region": "Saarland",
        "city": "Saarlouis",
        "street": "Kaiser-Wilhelm-Straße",
        "house_number": "12",
        "postal_code": "66740",
    }
    defaults.update(overrides)
    return Address.objects.create(**defaults)


class PhotoModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com", password="securepassword123"
        )
        self.listing = Listing.objects.create(
            owner=self.user,
            title="Test Hotel",
            type=ListingType.HOTEL,
            address=make_address(),
            max_guests=2,
            current_price=Decimal("100.00"),
        )
        self.room = Room.objects.create(
            listing=self.listing, name="Room 101", max_guests=2
        )

    def test_photo_valid_listing(self):
        photo = Photo(
            listing=self.listing, image=make_test_image(), uploaded_by=self.user
        )
        photo.full_clean()

    def test_photo_xor_no_binding_raises(self):
        with self.assertRaises(ValidationError):
            Photo(image=make_test_image()).full_clean()

    def test_photo_xor_both_bindings_raises(self):
        with self.assertRaises(ValidationError):
            Photo(
                listing=self.listing, room=self.room, image=make_test_image()
            ).full_clean()

    def test_default_order_and_is_primary(self):
        photo = Photo.objects.create(
            listing=self.listing, image=make_test_image(), uploaded_by=self.user
        )
        self.assertEqual(photo.order, 0)
        self.assertFalse(photo.is_primary)

    def test_gallery_ordering(self):
        second = Photo.objects.create(
            listing=self.listing,
            image=make_test_image("b.jpg"),
            order=2,
            uploaded_by=self.user,
        )
        first = Photo.objects.create(
            listing=self.listing,
            image=make_test_image("a.jpg"),
            order=1,
            uploaded_by=self.user,
        )
        ordered_ids = list(
            Photo.objects.filter(listing=self.listing).values_list("id", flat=True)
        )
        self.assertEqual(ordered_ids, [first.id, second.id])

    def test_uploaded_by_set_null_on_user_deletion(self):
        photo = Photo.objects.create(
            listing=self.listing, image=make_test_image(), uploaded_by=self.user
        )
        User.all_objects.filter(pk=self.user.pk).delete()

        photo.refresh_from_db()
        self.assertIsNone(photo.uploaded_by)

    def test_max_photos_per_listing_enforced(self):
        for i in range(MAX_PHOTOS_PER_LISTING):
            Photo.objects.create(
                listing=self.listing,
                image=make_test_image(f"photo_{i}.jpg"),
                uploaded_by=self.user,
            )

        with self.assertRaises(ValidationError):
            Photo.objects.create(
                listing=self.listing,
                image=make_test_image("overflow.jpg"),
                uploaded_by=self.user,
            )

    def test_editing_existing_photo_not_blocked_by_limit(self):
        photos = [
            Photo.objects.create(
                listing=self.listing,
                image=make_test_image(f"p{i}.jpg"),
                uploaded_by=self.user,
            )
            for i in range(MAX_PHOTOS_PER_LISTING)
        ]
        photos[0].caption = "Updated caption"
        photos[0].save()
        self.assertEqual(photos[0].caption, "Updated caption")

    def test_hard_delete_triggers_storage_cleanup_signal(self):
        photo = Photo.objects.create(
            listing=self.listing, image=make_test_image(), uploaded_by=self.user
        )
        storage = photo.image.storage
        file_name = photo.image.name
        self.assertTrue(storage.exists(file_name))

        photo.delete()

        self.assertFalse(storage.exists(file_name))
