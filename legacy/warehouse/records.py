"""Read order records written by the old warehouse system."""

from datetime import datetime, timezone

from legacy.warehouse.codes import status_name


def epoch_to_iso(seconds):
    """Unix seconds -> ISO 8601 text in UTC, e.g. '2026-07-02T14:00:00+00:00'."""
    if seconds is None:
        return None
    return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()


def read_record(raw):
    """Return a copy of a legacy order with readable dates and status."""
    order = dict(raw)
    for field in ("placed_at", "delivered_at", "promised_by"):
        if isinstance(order.get(field), int):
            order[field] = epoch_to_iso(order[field])
    if isinstance(order.get("status"), int):
        order["status"] = status_name(order["status"])
    return order
