"""Harborline's refund policy, written as code.

data/refund_policy.md is the version customers and agents read.
This file is the same policy as rules a program can check.
"""

from datetime import date, datetime, timezone

from harborline.config import BUSINESS_DATE, REFUND_APPROVAL_LIMIT

RETURN_WINDOW_DAYS = 30
OPENED_ELECTRONICS_WINDOW_DAYS = 15
LATE_DELIVERY_DAYS = 5
FREE_SHIPPING_FROM = 75.00

REASONS = (
    "changed_mind",
    "damaged",
    "defective",
    "wrong_item",
    "cancel_before_shipment",
    "late_delivery",
    "shipping_charged_in_error",
)


def as_date(value):
    """Turn a stored timestamp into a date.

    Orders from the new web store use ISO 8601 text ("2026-09-03T14:22:05Z").
    Orders from the old warehouse system use Unix seconds (1751464800).
    """
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, int):
        return datetime.fromtimestamp(value, tz=timezone.utc).date()
    return datetime.fromisoformat(value).date()


def needs_approval(amount):
    """Refunds above the limit need a support lead."""
    return amount > REFUND_APPROVAL_LIMIT


def _find_item(order, sku):
    for item in order["items"]:
        if item["sku"] == sku:
            return item
    return None


def _decision(allowed, refund, rule):
    return {"allowed": allowed, "refund": round(refund, 2), "rule": rule}


def check_refund(order, reason, sku=None, opened=False, today=BUSINESS_DATE):
    """Decide whether a refund is allowed, and for how much.

    order  : the order record (as stored)
    reason : one of REASONS
    sku    : the item being returned (not needed to cancel or for shipping refunds)
    opened : True if an electronics item has been opened
    """
    if reason not in REASONS:
        return _decision(False, 0, f"unknown reason '{reason}'")

    status = order["status"]
    if status in ("cancelled", "returned", 9, 7):
        return _decision(False, 0, "this order was already cancelled or refunded")

    if reason == "cancel_before_shipment":
        if status in ("processing", 0, 1, 2):
            return _decision(True, order["total"], "orders that have not shipped can be cancelled in full")
        return _decision(False, 0, "the order has already shipped, so it can't be cancelled; return it instead")

    if reason == "shipping_charged_in_error":
        subtotal = sum(i["unit_price"] * i["quantity"] for i in order["items"])
        if subtotal >= FREE_SHIPPING_FROM and order["shipping_fee"] > 0:
            return _decision(True, order["shipping_fee"], "orders of $75 or more ship free")
        return _decision(False, 0, "the shipping fee on this order was correct")

    delivered = as_date(order.get("delivered_at"))
    if delivered is None:
        return _decision(False, 0, "the order has not been delivered yet")
    days = (today - delivered).days

    if reason == "late_delivery":
        promised = as_date(order.get("promised_by"))
        if promised and (delivered - promised).days > LATE_DELIVERY_DAYS:
            return _decision(True, order["shipping_fee"], "deliveries more than 5 days late get the shipping fee back")
        return _decision(False, 0, "the order was not delivered more than 5 days late")

    item = _find_item(order, sku)
    if item is None:
        return _decision(False, 0, f"item {sku} is not on this order")
    item_total = item["unit_price"] * item["quantity"]

    if reason in ("damaged", "defective", "wrong_item"):
        if days > RETURN_WINDOW_DAYS:
            return _decision(False, 0, "problems must be reported within 30 days of delivery")
        return _decision(True, item_total + order["shipping_fee"], "our error: item and shipping are refunded")

    # reason == "changed_mind"
    if item["final_sale"]:
        return _decision(False, 0, "final-sale items can't be returned unless damaged or defective")
    window = RETURN_WINDOW_DAYS
    if item["category"] == "electronics" and opened:
        window = OPENED_ELECTRONICS_WINDOW_DAYS
    if days > window:
        return _decision(False, 0, f"the {window}-day return window has closed")
    return _decision(True, item_total, f"returned within {window} days: the item price is refunded")
