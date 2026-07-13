from apps.listings.choices import StandardAmenity


def create_standard_amenities(sender, **kwargs):
    """
    Automatically populates the `Amenity` table with default values
    immediately after the `listings` application migrations are executed.
    """
    # The sender in the post_migrate signal is the AppConfig of the app that was just migrated
    if sender.name == "apps.listings":
        Amenity = sender.get_model("Amenity")

        for choice in StandardAmenity:
            Amenity.objects.get_or_create(
                slug=choice.value,
                defaults={
                    "name": choice.label,
                    "group": "basic",
                },
            )
