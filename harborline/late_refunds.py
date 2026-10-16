"""Refund estimates for late deliveries, for the weekly report."""

from datetime import datetime


def days_late(order):
    promised = datetime.fromisoformat(order["promised_by"])
    delivered = datetime.fromisoformat(order["delivered_at"])
    return (delivered - promised).days


def late_refund(order):
    """10% of the order total for each day late, up to the full total."""
    days = days_late(order)
    if days <= 0:
        return 0
    return round(min(order["total"], order["total"] * 0.10 * days), 2)
