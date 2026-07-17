from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from apps.content.errors import convert_django_validation_error
from apps.content.models import Photo
from apps.content.repositories import PhotoRepository


class PhotoService:

    def __init__(self, repository: PhotoRepository = None):
        self.repository = repository or PhotoRepository()

    def list_for_listing(self, listing_id):
        return self.repository.get_for_listing(listing_id)

    @transaction.atomic
    def create_photo(
        self, *, listing, uploaded_by, image, caption="", is_primary=False, order=0
    ):
        if is_primary:
            self._unset_previous_primary(listing)

        photo = Photo(
            listing=listing,
            uploaded_by=uploaded_by,
            image=image,
            caption=caption,
            is_primary=is_primary,
            order=order,
        )
        return self._save_or_raise(photo)

    @transaction.atomic
    def update_photo(self, *, photo, **fields):
        if fields.get("is_primary") is True:
            self._unset_previous_primary(photo.listing, exclude_id=photo.id)

        for field, value in fields.items():
            setattr(photo, field, value)
        return self._save_or_raise(photo)

    @staticmethod
    def _unset_previous_primary(listing, exclude_id=None):
        """When a new cover is set, services automatically
        clears the flag from the previous one."""
        queryset = Photo.objects.filter(listing=listing, is_primary=True)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        queryset.update(is_primary=False)

    @staticmethod
    def _save_or_raise(photo):
        try:
            photo.save()
        except DjangoValidationError as exc:
            raise convert_django_validation_error(exc) from exc
        return photo
