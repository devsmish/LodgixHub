from django.db.models import Avg, Count
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.reviews.choices import ReviewStatus


def recalculate_listing_rating(listing):

    from apps.listings.models import Listing
    from apps.reviews.models import Review

    aggregate = Review.objects.filter(
        listing=listing, status=ReviewStatus.PUBLISHED
    ).aggregate(avg=Avg("rating"), count=Count("id"))

    Listing.all_objects.filter(pk=listing.pk).update(
        rating_avg=aggregate["avg"] or 0,
        reviews_count=aggregate["count"],
    )


@receiver(post_save, sender="reviews.Review")
def on_review_saved(sender, instance, **kwargs):
    recalculate_listing_rating(instance.listing)


@receiver(post_delete, sender="reviews.Review")
def on_review_deleted(sender, instance, **kwargs):
    recalculate_listing_rating(instance.listing)
