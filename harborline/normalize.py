"""One format for order dates and statuses, whatever system wrote them.

Web orders use ISO 8601 with an offset. Orders from the old warehouse
use Unix seconds and numeric status codes. order() returns a copy with
UTC ISO 8601 dates and status names.
"""

from datetime import datetime, timezone

from legacy.warehouse.codes import status_name

DATE_FIELDS = ("placed_at", "promised_by", "delivered_at")


def to_utc(value):
    """Unix seconds or ISO 8601 -> ISO 8601 in UTC; a plain date stays."""
    if isinstance(value, (int, float)):
        moment = datetime.fromtimestamp(value, tz=timezone.utc)
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
