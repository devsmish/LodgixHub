from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.listings.models import Listing
from apps.pricing.models import PriceHistory


class Command(BaseCommand):
    """
    Daily task — triggered by the system cron once a day
    (at 00:05 server time).

    'Role of the daily cron: the cron does NOT create new PriceHistory records.
    The cron's sole task is to update the denormalized cache field
    Listing.current_price: it finds the PriceHistory record with the latest
    valid_from date (<= today) and copies its price to current_price. If
    the landlord hasn't changed the price, current_price remains unchanged.'

    Bulk queryset.update() — intentionally bypassing save()/full_clean():
    current_price is a pure cache field; no Listing.clean() business rules
    depend on it, and the cache update is not among the email triggers.
    """

    help = (
        "Updates Listing.current_price based on the latest active PriceHistory record."
    )

    def handle(self, *args, **options):
        today = timezone.localdate()
        updated_count = 0

        for listing in Listing.objects.all().only("id", "current_price"):
            latest_price = PriceHistory.objects.effective_on(
                today, listing=listing
            ).first()
            if latest_price is None:
                continue
            if latest_price.price != listing.current_price:
                Listing.objects.filter(pk=listing.pk).update(
                    current_price=latest_price.price
                )
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"updated_listings={updated_count}"))
