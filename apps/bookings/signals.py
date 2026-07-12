from apps.bookings.choices import StandardCancellationReason


def create_standard_cancellation_reasons(sender, **kwargs):
    """
    Populates the CancellationReason reference table with default values
    right after apps.bookings migrations run.
    """
    if sender.name == "apps.bookings":
        CancellationReason = sender.get_model("CancellationReason")

        for choice in StandardCancellationReason:
            CancellationReason.objects.get_or_create(
                code=choice.value,
                defaults={"description": choice.label},
            )
