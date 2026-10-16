"""Refund estimates for late deliveries, for the weekly report."""

from harborline.policy import check_refund


def late_refund(order):
    """What the refund policy pays back for a late delivery."""
    return check_refund(order, "late_delivery")["refund"]
