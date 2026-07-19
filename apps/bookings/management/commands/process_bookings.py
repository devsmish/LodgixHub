from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.bookings.choices import BookingStatus
from apps.bookings.models import Booking
from apps.bookings.services import calculate_auto_cancel_deadline


class Command(BaseCommand):
    """
    A periodic task — triggered by the system cron inside the
    Docker container every N minutes (interval: 1–5 minutes):

      1) pending -> auto_cancelled if the deadline has passed (based on the
         business-hours formula in apps.bookings.services.calculate_auto_cancel_deadline).
         Processed one record at a time via save() — full_clean() and the
         post_save signal (apps.notifications) must execute: BOOKING_AUTO_CANCELLED
         is included in the list of email triggers.

      2) confirmed -> completed upon reaching the check_out_date — handled by the
         same cron job, not a separate daily task. Uses a bulk queryset.update() —
         intentionally bypassing save()/signals: booking 'completion' is not
         included in the list of email triggers (as dates/prices do not change)..
    """

    help = (
        "Automatic cancellation of overdue pending bookings and transition of confirmed bookings "
        "to 'completed' status upon the check-out date."
    )

    def handle(self, *args, **options):
        auto_cancelled_count = self._auto_cancel_overdue_pending_bookings()
        completed_count = self._complete_finished_bookings()
        self.stdout.write(
            self.style.SUCCESS(
                f"auto_cancelled={auto_cancelled_count}, completed={completed_count}"
            )
        )

    def _auto_cancel_overdue_pending_bookings(self) -> int:
        now = timezone.now()
        count = 0

        for booking in Booking.objects.filter(status=BookingStatus.PENDING):
            deadline = calculate_auto_cancel_deadline(booking.created_at)
            if now < deadline:
                continue

            try:
                with transaction.atomic():
                    booking.status = BookingStatus.AUTO_CANCELLED
                    booking.cancelled_at = now
                    booking.save(
                        update_fields=["status", "cancelled_at", "updated_at"]
                    )
                count += 1
            # noqa: BLE001 — A single problematic record shouldn't cause the entire batch to fail.
            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(
                        f"Failed to auto-cancel booking {booking.id}: {exc}"
                    )
                )

        return count

    @staticmethod
    def _complete_finished_bookings() -> int:
        today = timezone.localdate()
        return Booking.objects.filter(
            status=BookingStatus.CONFIRMED, check_out_date__lte=today
        ).update(status=BookingStatus.COMPLETED)
