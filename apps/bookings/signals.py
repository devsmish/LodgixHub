import django.dispatch

from apps.bookings.choices import StandardCancellationReason

# An extension point for future integration with refunds money.
dispute_resolved = django.dispatch.Signal()


def create_standard_cancellation_reasons(sender, **kwargs):
    """
    Populates the CancellationReason reference table with default values
    right after apps.bookings migrations run.
    """
    if sender.name == "apps.bookings":
        CancellationReason = sender.get_model("CancellationReason")

        for choice in StandardCancellationReason:
            CancellationReason.objects.get_or_create(
                code=choice.name,
                defaults={"description": choice.label},
            )
