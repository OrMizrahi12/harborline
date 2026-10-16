"""Shipping fees owed on late deliveries, per customer."""

from harborline import data, policy


def owed_by_customer(orders=None):
    """{customer_id: shipping fees owed, in cents}: integers, so totals never drift."""
    owed = {}
    for order in data.orders() if orders is None else orders:
        decision = policy.check_refund(order, "late_delivery")
        if decision["allowed"]:
            cents = round(decision["refund"] * 100)
            owed[order["customer_id"]] = owed.get(order["customer_id"], 0) + cents
    return owed
