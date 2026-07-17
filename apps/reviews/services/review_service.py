from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models as django_models
from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from apps.reviews.errors import (
    ReviewAlreadyExistsError,
    convert_django_validation_error,
)
from apps.reviews.models import Review
from apps.reviews.repositories import ReviewRepository


class ReviewService:

    def __init__(self, repository: ReviewRepository = None):
        self.repository = repository or ReviewRepository()

    # --- lists ---

    def list_published_for_listing(self, listing_id):
        return self.repository.get_published_for_listing(listing_id)

    def list_mine(self, user):
        return self.repository.get_for_author(user)

    def list_for_landlord(self, user):
        return self.repository.get_for_landlord(user)

    def list_for_moderation(self):
        return self.repository.get_all_queryset()

    # --- creation (booking.tenant == author, there are no reviews for this booking yet.) ---

    @transaction.atomic
    def create_review(self, *, author, booking, rating, comment):
        if booking.tenant_id != author.id:
            raise PermissionDenied(
                "Only the renter associated with this booking can leave a review."
            )
        if self.repository.exists_for_booking(booking.id):
            raise ReviewAlreadyExistsError()

        review = Review(
            booking=booking,
            listing=self._derive_listing(booking),
            author=author,
            rating=rating,
            comment=comment,
        )
        return self._save_or_raise(review)

    @staticmethod
    def _derive_listing(booking):
        return booking.listing or (booking.room.listing if booking.room else None)

    # --- Author editing — the 7-day window is checked in Review.clean(). ---

    @transaction.atomic
    def update_review(self, *, review, rating=None, comment=None):
        if rating is not None:
            review.rating = rating
        if comment is not None:
            review.comment = comment
        return self._save_or_raise(review)

    @staticmethod
    def _save_or_raise(review):
        try:
            review.save()
        except DjangoValidationError as exc:
            raise convert_django_validation_error(exc) from exc
        return review

    # owner response / moderation — I deliberately do *not* check via
    # Review.clean() (_save_bypassing_author_window below)

    @transaction.atomic
    def respond(self, *, review, actor, response_text):
        if review.listing.owner_id != actor.id:
            raise PermissionDenied("Only the listing owner can reply to a review.")
        review.landlord_response = response_text
        self._save_bypassing_author_window(
            review, update_fields=["landlord_response", "updated_at"]
        )
        return review

    @transaction.atomic
    def update_status(self, *, review, new_status):
        review.status = new_status
        self._save_bypassing_author_window(
            review, update_fields=["status", "updated_at"]
        )
        return review

    @staticmethod
    def _save_bypassing_author_window(review, update_fields):
        """The status and landlord_response fields are updated by a moderator or the owner, not the author;
        the 7-day editing window applies only to the author's changes
        (rating/comment) and should not block moderation long
        after checkout. We call 'django.db.models.Model.save()' directly,
        bypassing 'Review.save()'— but we avoid 'queryset.update()' so that the 'post_save' signal
        triggering the recalculation of 'Listing.rating_avg' and 'reviews_count' still fires.
        """
        django_models.Model.save(review, update_fields=update_fields)
