from django.db import models
from django.utils.translation import gettext_lazy as _


class ListingType(models.TextChoices):
    APARTMENT = "apartment", _("Apartment")
    HOTEL = "hotel", _("Hotel")
    HOSTEL = "hostel", _("Hostel")


class ListingStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PUBLISHED = "published", _("Published")
    HIDDEN = "hidden", _("Hidden")
    REJECTED = "rejected", _("Rejected")


class RentalType(models.TextChoices):
    DAILY = "daily", _("Daily")
    LONG_TERM = "long_term", _("Long Term")
    ANY = "any", _("Any Type")


class MealType(models.TextChoices):
    NONE = "none", _("No Meals")
    BREAKFAST = "breakfast", _("Breakfast Included")
    HALF_BOARD = "half_board", _("Half Board")
    FULL_BOARD = "full_board", _("Full Board")
    ALL_INCLUSIVE = "all_inclusive", _("All Inclusive")


class RoomType(models.TextChoices):
    SINGLE = "single", _("Single Room")  # 1 guest, 1 bed
    DOUBLE = "double", _("Double Room")  # 2 guests, 1 big bed
    TWIN = "twin", _("Twin Room")  # 2 guests, 2 beds
    TRIPLE = "triple", _("Triple Room")  # 3 guests
    QUAD = "quad", _("Quadruple Room")  # 4 guests
    SUITE = "suite", _("Suite")  # lux / Multi-room
    STUDIO = "studio", _("Studio Room")  # Room with a private kitchenette
    DORM_BED = "dorm_bed", _("Bed in Dormitory Room")  # Hostel bed (bed space)
    FAMILY = "family", _("Family Room")  # High-capacity family room


class MaxGuestsChoices(models.IntegerChoices):
    ONE = 1, _("1 Guest")
    TWO = 2, _("2 Guests")
    THREE = 3, _("3 Guests")
    FOUR = 4, _("4 Guests")
    FIVE = 5, _("5 Guests")
    SIX = 6, _("6 Guests")
    SEVEN = 7, _("7 Guests")
    EIGHT = 8, _("8 Guests")
    TEN = 10, _("10 Guests")
    TWELVE = 12, _("12 Guests")
    SIXTEEN = 16, _("16+ Guests")


class AmenityGroup(models.TextChoices):
    BASIC = "basic", _("Basic Utilities")
    KITCHEN = "kitchen", _("Kitchen & Dining")
    MEDIA = "media", _("Media & Technology")
    SERVICES = "services", _("Facilities & Services")
    OUTDOORS = "outdoors", _("Outdoors & Views")


class StandardAmenity(models.TextChoices):
    # Basic Utilities
    WIFI = "wifi", _("Free Wi-Fi")
    AC = "air_conditioning", _("Air Conditioning")
    HEATING = "heating", _("Heating")
    IRON = "iron", _("Iron")
    WORKSPACE = "dedicated_workspace", _("Dedicated Workspace")

    # Kitchen & Dining
    KITCHEN = "kitchen", _("Fully Equipped Kitchen")
    REFRIGERATOR = "refrigerator", _("Refrigerator")
    MICROWAVE = "microwave", _("Microwave")
    COFFEE = "coffee_maker", _("Coffee Maker")

    # Media & Technology
    TV = "tv", _("TV / Cable")
    SOUND = "sound_system", _("Sound System")

    # Services / Facilities
    PARKING = "free_parking", _("Free Parking on Premises")
    POOL = "swimming_pool", _("Swimming Pool")
    GYM = "gym", _("Gym / Fitness Center")
    WASHER = "washing_machine", _("Washing Machine")
    ELEVATOR = "elevator", _("Elevator")

    # Outdoors
    BALCONY = "balcony", _("Balcony / Terrace")
    BBQ = "bbq_grill", _("BBQ Grill")
    BEACH = "beach_front", _("Beachfront Access")

    @classmethod
    def get_group_for_slug(cls, slug_value):
        """Returns the group for a specific amenity key."""
        mapping = {
            # Basic Utilities
            cls.WIFI.value: AmenityGroup.BASIC.value,
            cls.AC.value: AmenityGroup.BASIC.value,
            cls.HEATING.value: AmenityGroup.BASIC.value,
            cls.IRON.value: AmenityGroup.BASIC.value,
            cls.WORKSPACE.value: AmenityGroup.BASIC.value,
            # Kitchen & Dining
            cls.KITCHEN.value: AmenityGroup.KITCHEN.value,
            cls.REFRIGERATOR.value: AmenityGroup.KITCHEN.value,
            cls.MICROWAVE.value: AmenityGroup.KITCHEN.value,
            cls.COFFEE.value: AmenityGroup.KITCHEN.value,
            # Media & Technology
            cls.TV.value: AmenityGroup.MEDIA.value,
            cls.SOUND.value: AmenityGroup.MEDIA.value,
            # Services / Facilities
            cls.PARKING.value: AmenityGroup.SERVICES.value,
            cls.POOL.value: AmenityGroup.SERVICES.value,
            cls.GYM.value: AmenityGroup.SERVICES.value,
            cls.WASHER.value: AmenityGroup.SERVICES.value,
            cls.ELEVATOR.value: AmenityGroup.SERVICES.value,
            # Outdoors
            cls.BALCONY.value: AmenityGroup.OUTDOORS.value,
            cls.BBQ.value: AmenityGroup.OUTDOORS.value,
            cls.BEACH.value: AmenityGroup.OUTDOORS.value,
        }

        return mapping.get(slug_value, AmenityGroup.BASIC.value)
