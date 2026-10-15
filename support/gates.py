"""A prerequisite gate for the order tools.

list_orders, lookup_order and process_refund refuse until get_customer
has verified the sender, and then they only reach that customer's own
orders. The system prompt asks for this too, but a prompt can be
skipped: this check runs in our code, on every call.
"""

from harborline import backend, data
from harborline.errors import PermissionDenied

ENFORCE = True  # False: the prompt rule alone, for the comparison
case = {"customer_id": None, "served": 0, "blocked": 0}


def start_case():
    """A new ticket: nobody is verified yet."""
    case.update(customer_id=None, served=0, blocked=0)


def get_customer(**arguments):
    """The backend call, and remember a verified customer ID."""
    result = backend.get_customer(**arguments)
    if result["verified"]:
        case["customer_id"] = result["customer"]["customer_id"]
    return result


def check(order_id):
    """An order call without a verified owner: block it, or count it."""
    owner = next((o["customer_id"] for o in data.orders()
                  if o["order_id"] == order_id), None)
    if case["customer_id"] is None:
        problem = "No verified customer yet: call get_customer first."
    elif owner and owner != case["customer_id"]:
        problem = "That order belongs to a different customer."
    else:
        return
    if ENFORCE:
        case["blocked"] += 1
        raise PermissionDenied(problem)
    case["served"] += 1


def list_orders(customer_id):
    """Only the verified customer's own orders."""
    if case["customer_id"] is None:
        problem = "No verified customer yet: call get_customer first."
    elif customer_id != case["customer_id"]:
        problem = "You can only list the verified customer's orders."
    else:
        return backend.list_orders(customer_id)
    if ENFORCE:
        case["blocked"] += 1
        raise PermissionDenied(problem)
    case["served"] += 1
    return backend.list_orders(customer_id)


def lookup_order(order_id):
    check(order_id)
    return backend.lookup_order(order_id)


def process_refund(order_id, **refund):
    check(order_id)
    return backend.process_refund(order_id, **refund)
