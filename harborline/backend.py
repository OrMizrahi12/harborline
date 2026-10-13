"""Harborline's backend: the systems a support agent works with.

These are ordinary Python functions over the files in data/. Later in the
course they become tools that Claude can call. Refunds and escalations are
kept in memory, so every run starts from the same data.
"""

import re

from harborline import data, policy
from harborline.errors import (
    InvalidRequest,
    NotFound,
    PermissionDenied,
    PolicyViolation,
    ServiceUnavailable,
)

ORDER_ID_PATTERN = re.compile(r"^HL-\d{5}$")

_refunds = []
_escalations = []
_lookup_counts = {}


def reset():
    """Forget refunds, escalations and simulated outages (used by the tests)."""
    _refunds.clear()
    _escalations.clear()
    _lookup_counts.clear()


def _mask_email(email):
    name, domain = email.split("@")
    return f"{name[0]}***@{domain}"


def get_customer(email=None, customer_id=None, name=None):
    """Find a customer by email, customer ID or full name.

    An email or ID identifies one customer, so the result is verified.
    A name can match several people, so it returns unverified candidates.
    """
    customers = data.customers()

    if customer_id or email:
        for customer in customers:
            if customer_id and customer["customer_id"] == customer_id:
                return {"verified": True, "customer": customer}
            if email and customer["email"].lower() == email.strip().lower():
                return {"verified": True, "customer": customer}
        raise NotFound("No customer matches that email or ID.")

    if name:
        matches = [c for c in customers if c["name"].lower() == name.strip().lower()]
        if not matches:
            raise NotFound(f"No customer named {name}.")
        candidates = [
            {"customer_id": c["customer_id"], "name": c["name"], "city": c["city"],
             "email_hint": _mask_email(c["email"])}
            for c in matches
        ]
        return {"verified": False, "candidates": candidates}

    raise InvalidRequest("Give an email, a customer ID or a name.")


def _find_order(order_id):
    if not ORDER_ID_PATTERN.match(order_id or ""):
        raise InvalidRequest(f"'{order_id}' is not an order ID. Order IDs look like HL-10234.")
    for order in data.orders():
        if order["order_id"] == order_id:
            return order
    raise NotFound(f"Order {order_id} does not exist.")


def lookup_order(order_id, customer_id=None):
    """Return one order, exactly as the order systems store it.

    If customer_id is given, the order must belong to that customer.
    """
    order = _find_order(order_id)

    slow = data.faults()["slow_orders"]
    if order_id in slow:
        _lookup_counts[order_id] = _lookup_counts.get(order_id, 0) + 1
        if _lookup_counts[order_id] <= slow[order_id]:
            raise ServiceUnavailable("The warehouse system timed out. Try again in a moment.")

    if customer_id and order["customer_id"] != customer_id:
        raise PermissionDenied("That order belongs to a different customer.")
    return order


def list_orders(customer_id, limit=10):
    """Return short summaries of a customer's orders, newest first.

    A customer with no orders gets an empty list: that is a valid answer,
    not an error.
    """
    get_customer(customer_id=customer_id)  # raises NotFound for unknown IDs
    own = [o for o in data.orders() if o["customer_id"] == customer_id]
    own.sort(key=lambda o: str(policy.as_date(o["placed_at"])), reverse=True)
    return [
        {"order_id": o["order_id"], "placed_on": str(policy.as_date(o["placed_at"])),
         "items": [i["name"] for i in o["items"]], "total": o["total"]}
        for o in own[:limit]
    ]


def process_refund(order_id, amount, reason, sku=None, opened=False):
    """Refund money to the customer, if the refund policy allows it."""
    order = _find_order(order_id)
    customer = get_customer(customer_id=order["customer_id"])["customer"]
    if customer["status"] == "review_hold":
        raise PermissionDenied("This account is on review hold. Refunds need a support lead.")

    decision = policy.check_refund(order, reason, sku=sku, opened=opened)
    if not decision["allowed"]:
        raise PolicyViolation(f"Refund not allowed: {decision['rule']}.")
    if amount > decision["refund"]:
        raise PolicyViolation(f"The most this refund can be is ${decision['refund']:.2f}.")

    refund = {
        "refund_id": f"RF-{len(_refunds) + 1:04d}",
        "order_id": order_id,
        "customer_id": order["customer_id"],
        "amount": round(amount, 2),
        "reason": reason,
        "sku": sku,
        "status": "processed",
    }
    _refunds.append(refund)
    return refund


def escalate_to_human(customer_id, summary, reason, order_id=None, amount=None,
                      recommended_action=None):
    """Hand the case to a human in the support-leads queue."""
    case = {
        "escalation_id": f"ESC-{len(_escalations) + 1:04d}",
        "queue": "support-leads",
        "status": "open",
        "customer_id": customer_id,
        "order_id": order_id,
        "amount": amount,
        "reason": reason,
        "summary": summary,
        "recommended_action": recommended_action,
    }
    _escalations.append(case)
    return case


def refunds():
    return list(_refunds)


def escalations():
    return list(_escalations)
