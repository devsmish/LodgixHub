from django.db import migrations

# Hard-coded on purpose: a migration must not depend on the current state of
# apps.bookings.choices (the enum may change later, the migration must not).
STANDARD_CODES = {
    "personal_emergency": "PERSONAL_EMERGENCY",
    "changed_plans": "CHANGED_PLANS",
    "property_unavailable": "PROPERTY_UNAVAILABLE",
    "cleanliness_issues": "CLEANLINESS_ISSUES",
}


def _rename(apps, mapping):
    CancellationReason = apps.get_model("bookings", "CancellationReason")
    Booking = apps.get_model("bookings", "Booking")
    # _default_manager in a migration is a plain manager: it also sees
    # soft-deleted rows, which is what we want here.
    reasons = CancellationReason._default_manager

    for old_code, new_code in mapping.items():
        old = reasons.filter(code=old_code).first()
        if old is None:
            continue
        new = reasons.filter(code=new_code).first()
        if new is None:
            old.code = new_code
            old.save(update_fields=["code"])
        else:
            # Both variants exist (the seed signal already created the new
            # one): move the bookings to it and drop the duplicate.
            Booking._default_manager.filter(cancellation_reason=old).update(
                cancellation_reason=new
            )
            old.delete()


def to_uppercase(apps, schema_editor):
    _rename(apps, STANDARD_CODES)


def to_lowercase(apps, schema_editor):
    _rename(apps, {v: k for k, v in STANDARD_CODES.items()})


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0002_alter_cancellationreason_code"),
    ]

    operations = [
        migrations.RunPython(to_uppercase, to_lowercase),
    ]
