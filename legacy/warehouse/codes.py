"""Order status codes used by the old warehouse system."""

STATUS_NAMES = {
    0: "received",
    1: "picking",
    2: "packed",
    3: "shipped",
    4: "delivered",
    7: "returned",
    9: "cancelled",
}


def status_name(code):
    """Turn a numeric status code into its name."""
    return STATUS_NAMES.get(code, "unknown")
