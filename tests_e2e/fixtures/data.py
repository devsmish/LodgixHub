"""
Payload builders. These are simply functions that a test calls directly,
which avoids the need to create "magic" dictionaries in every single
test and ensures that if a DTO contract (in `apps/*/dto/*.py`) changes,
the necessary updates can be made in one place.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}@e2e.test"


def register_payload(*, role: str, prefix: str = "user", password: str = "TestPass123!") -> dict:
    return {
        "email": unique_email(prefix),
        "password": password,
        "role": role,
        "first_name": "E2E",
        "last_name": role.capitalize(),
        "terms_accepted": True,
    }


def listing_payload(**overrides) -> dict:
    payload = {
        "title": f"E2E Listing {uuid.uuid4().hex[:8]}",
        "description": "Created by the pytest+playwright E2E suite.",
        "type": "apartment",
        "address": {
            "country": "Germany",
            "region": "Bavaria",
            "city": "Springfield",
            "street": "Evergreen Terrace",
            "house_number": "742",
            "postal_code": "80331",
        },
        "max_guests": 4,
        "rooms_count": 2,
        "current_price": "100.00",
        "rental_type": "daily",
        "deposit_required": False,
        "deposit_percent": 0,
        "deposit_refundable": True,
    }
    payload.update(overrides)
    return payload


def booking_payload(*, listing_id: str, days_ahead: int = 7, nights: int = 3, guests_count: int = 2, **overrides) -> dict:
    check_in = date.today() + timedelta(days=days_ahead)
    check_out = check_in + timedelta(days=nights)
    payload = {
        "listing_id": listing_id,
        "check_in_date": check_in.isoformat(),
        "check_out_date": check_out.isoformat(),
        "guests_count": guests_count,
    }
    payload.update(overrides)
    return payload
