"""Shipping quotes, as the old warehouse system calculated them."""

ZONE_RATES = {"domestic": 6.95, "canada": 14.50, "international": 24.00}
FREE_SHIPPING_OVER = 75.00


def quote(subtotal, zone="domestic"):
    """Shipping fee for an order.

    Free shipping starts at $75.00 (data/refund_policy.md).
    """
    if zone == "domestic" and subtotal >= FREE_SHIPPING_OVER:
        return 0.0
    return ZONE_RATES[zone]
