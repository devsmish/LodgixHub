from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, validate_email
from PIL import Image

from core.constants import (
    ALLOWED_IMAGE_EXTENSIONS,
    DISPOSABLE_EMAIL_DOMAINS,
    MAX_IMAGE_HEIGHT,
    MAX_IMAGE_SIZE_MB,
    MAX_IMAGE_WIDTH,
    MIN_IMAGE_HEIGHT,
    MIN_IMAGE_WIDTH,
)

phone_validator = RegexValidator(
    regex=r"^\+[1-9]\d{6,14}$",
    message="The phone number must be in E.164 format (starting with the + sign and country code, 7 to 15 characters).",
)

nickname_validator = RegexValidator(
    regex=r"^[A-Za-z0-9_]{3,30}$",
    message="The username must be between 3 and 30 characters long and consist only of Latin letters, numbers, and '_'.",
)

name_validator = RegexValidator(
    regex=r"^[A-Za-zÀ-ÖØ-öø-ÿ\s\-']+$",
    message="The field may contain only letters (including umlauts), spaces, hyphens, and apostrophes.",
)


def validate_image(file):
    ext = file.name.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(f"Invalid file extension: .{ext}")

    if file.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"The file exceeds{MAX_IMAGE_SIZE_MB} Mb")

    try:
        image = Image.open(file)
        image.verify()
    except Exception:
        raise ValidationError("The file is corrupted or is not an image.")

    file.seek(0)
    image = Image.open(file)
    width, height = image.size

    if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
        raise ValidationError(
            f"Minimum resolution {MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT}px"
        )
    if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
        raise ValidationError(
            f"Maximum resolution {MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT}px"
        )


def validate_custom_email(value):
    if not value:
        return

    try:
        validate_email(value)
    except ValidationError:
        raise ValidationError("Enter a valid email address.")

    if " " in value:
        raise ValidationError("The email address must not contain spaces.")

    email_lower = value.lower()
    if "@" in email_lower:
        domain = email_lower.split("@")[-1]
        if domain in DISPOSABLE_EMAIL_DOMAINS:
            raise ValidationError(
                f"Registration via temporary email services ({domain}) is prohibited. "
                f"Please use a reliable email provider."
            )
