"""One format for order dates and statuses, whatever system wrote them.

Web orders use ISO 8601 with an offset. Orders from the old warehouse
use Unix seconds and numeric status codes. order() returns a copy with
UTC ISO 8601 dates and status names.
"""

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from legacy.warehouse.codes import status_name

DATE_FIELDS = ("placed_at", "promised_by", "delivered_at")

# Marketplace partner: US month/day, Eastern time, and the time is optional.
PARTNER_SHAPE = re.compile(r"\d{2}/\d{2}/\d{4}( \d{1,2}:\d{2} [AP]M ET)?")
PARTNER_ZONE = ZoneInfo("America/New_York")


def partner_to_utc(value):
    """'10/08/2026 2:30 PM ET' -> UTC ISO 8601; '10/08/2026' stays a plain date."""
    if not PARTNER_SHAPE.fullmatch(value):
        raise ValueError(f"Not a partner date: {value!r}")
    try:
        if value.endswith(" ET"):
            local = datetime.strptime(value[:-3], "%m/%d/%Y %I:%M %p")
            moment = local.replace(tzinfo=PARTNER_ZONE).astimezone(timezone.utc)
            return moment.strftime("%Y-%m-%dT%H:%M:%SZ")
        return datetime.strptime(value, "%m/%d/%Y").date().isoformat()
    except ValueError:
        raise ValueError(f"Not a partner date: {value!r}") from None


def to_utc(value):
    """Unix seconds, ISO 8601 or partner dates -> ISO 8601 in UTC; a plain date stays."""
    if isinstance(value, (int, float)):
        moment = datetime.fromtimestamp(value, tz=timezone.utc)
    elif isinstance(value, str) and "/" in value:
        return partner_to_utc(value)
    elif isinstance(value, str) and "T" in value:
        moment = datetime.fromisoformat(value).astimezone(timezone.utc)
    else:
        return value  # None, or a date like "2026-10-08"
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def order(record):
    """A copy of one order with UTC dates and a status name."""
    clean = dict(record)
    for field in DATE_FIELDS:
        if field in clean:
            clean[field] = to_utc(clean[field])
    if isinstance(record.get("status"), int):
        clean["status"] = status_name(record["status"])
    return clean
