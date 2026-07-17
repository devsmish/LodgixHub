from apps.reviews.choices import ReviewStatus
from apps.reviews.models import Review


class ReviewRepository:

    @staticmethod
    def get_published_for_listing(listing_id):
        return Review.objects.filter(
            listing_id=listing_id, status=ReviewStatus.PUBLISHED
        )

    @staticmethod
    def get_for_author(user):
        return Review.objects.filter(author=user)

    @staticmethod
    def get_for_landlord(user):
        return Review.objects.filter(listing__owner=user)

    @staticmethod
    def get_all_queryset():
        return Review.objects.all()

    @staticmethod
    def get_by_id(review_id):
        return (
            Review.objects.filter(id=review_id)
            .select_related("listing", "listing__owner", "author", "booking")
            .first()
        )

    @staticmethod
    def exists_for_booking(booking_id):
        return Review.objects.filter(booking_id=booking_id).exists()
