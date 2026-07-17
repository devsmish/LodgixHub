from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.bookings.choices import BookingStatus
from apps.bookings.models import Booking
from apps.notifications.choices import NotificationType
from apps.notifications.services import NotificationService
from apps.pricing.models import PriceHistory
from apps.reviews.models import Review

User = get_user_model()


# --- registration ---


@receiver(post_save, sender=User)
def notify_registration(sender, instance, created, **kwargs):
    if not created:
        return
    NotificationService.send(
        user=instance,
        notification_type=NotificationType.REGISTRATION,
        subject="Добро пожаловать!",
        message=(
            f"Здравствуйте, {instance.first_name or instance.email}! "
            "Регистрация на платформе прошла успешно."
        ),
    )


# --- Bookings: confirmation / rejection / cancellation / auto-cancellation ---


@receiver(post_save, sender=Booking)
def notify_booking_status_change(sender, instance, created, update_fields, **kwargs):
    if created or not update_fields:
        return

    handlers = {
        BookingStatus.CONFIRMED: _notify_booking_confirmed,
        BookingStatus.REJECTED: _notify_booking_rejected,
        BookingStatus.CANCELLED_BY_TENANT: _notify_booking_cancelled_by_tenant,
        BookingStatus.CANCELLED_BY_LANDLORD: _notify_booking_cancelled_by_landlord,
        BookingStatus.AUTO_CANCELLED: _notify_booking_auto_cancelled,
    }
    handler = handlers.get(instance.status)
    if handler:
        handler(instance)


def _notify_booking_confirmed(booking):
    NotificationService.send(
        user=booking.tenant,
        notification_type=NotificationType.BOOKING_CONFIRMED,
        subject="Your reservation is confirmed.",
        message=f"Booking #{booking.id} for {booking.check_in_date} has been confirmed by the owner.",
    )


def _notify_booking_rejected(booking):
    NotificationService.send(
        user=booking.tenant,
        notification_type=NotificationType.BOOKING_REJECTED,
        subject="Your booking has been declined.",
        message=f"Booking #{booking.id} for {booking.check_in_date} has been declined by the owner.",
    )


def _notify_booking_cancelled_by_tenant(booking):
    landlord = booking.get_landlord()
    if landlord is None:
        return
    NotificationService.send(
        user=landlord,
        notification_type=NotificationType.BOOKING_CANCELLED,
        subject="The renter cancelled the booking.",
        message=f"Booking #{booking.id} for {booking.check_in_date} has been cancelled by the renter.",
    )


def _notify_booking_cancelled_by_landlord(booking):
    """When the owner cancels and is required to provide a reason, this email
    must be an automated apology message."""
    reason = (
        booking.cancellation_reason.description if booking.cancellation_reason else ""
    )
    NotificationService.send(
        user=booking.tenant,
        notification_type=NotificationType.BOOKING_CANCELLED,
        subject="Your booking has been cancelled by the owner — we apologize.",
        message=(
            f"Unfortunately, the owner was forced to cancel your booking #{booking.id} "
            f"for {booking.check_in_date}. Reason: {reason}. "
            "We sincerely apologize for the inconvenience."
        ),
    )


def _notify_booking_auto_cancelled(booking):
    NotificationService.send(
        user=booking.tenant,
        notification_type=NotificationType.BOOKING_AUTO_CANCELLED,
        subject="The reservation has been automatically cancelled.",
        message=(
            f"Booking #{booking.id} for {booking.check_in_date} was automatically "
            "cancelled because it was not confirmed by the owner on time."
        ),
    )


# --- price change (only if the user already has a booking) ---


@receiver(post_save, sender=PriceHistory)
def notify_price_changed(sender, instance, created, **kwargs):
    if not created:
        # PriceHistory is append-only (LogModel) — save() always creates a new record;
        # the check is retained for clarity/in case of future changes.
        return

    filter_kwargs = (
        {"listing_id": instance.listing_id}
        if instance.listing_id
        else {"room_id": instance.room_id}
    )
    affected_bookings = Booking.objects.filter(
        status__in=(BookingStatus.PENDING, BookingStatus.CONFIRMED),
        check_in_date__gte=instance.valid_from,
        **filter_kwargs,
    ).select_related("tenant")

    target = instance.listing or instance.room.listing
    for booking in affected_bookings:
        NotificationService.send(
            user=booking.tenant,
            notification_type=NotificationType.PRICE_CHANGED,
            subject=f"The price in the listing has changed «{target.title}»",
            message=(
                f"As of {instance.valid_from}, the price for the listing '{target.title}' "
                f"is {instance.price}. The price of your existing booking "
                f"#{booking.id} remains unchanged—it was locked in at the time of booking."
            ),
        )


# --- reviews: new review / owner response ---


@receiver(post_save, sender=Review)
def notify_new_review(sender, instance, created, **kwargs):
    if not created:
        return
    NotificationService.send(
        user=instance.listing.owner,
        notification_type=NotificationType.NEW_REVIEW,
        subject="New review for your listing",
        message=(
            f"A new review ({instance.rating}/5) has been left for the listing"
            f"«{instance.listing.title}»."
        ),
    )


@receiver(post_save, sender=Review)
def notify_review_response(sender, instance, created, update_fields, **kwargs):
    if created or not update_fields or "landlord_response" not in update_fields:
        return
    NotificationService.send(
        user=instance.author,
        notification_type=NotificationType.REVIEW_RESPONSE,
        subject="The owner replied to your review",
        message=f"The owner of the listing «{instance.listing.title}» has replied to your review.",
    )
