"""List the orders that were delivered more than 5 days late, and the shipping fee owed for each.

Section 4 of data/refund_policy.md refunds the shipping fee on these orders.
The amounts are what the policy owes by its rules. The script reads the
data/orders.json seed file, which doesn't record refunds already issued
through the Harborline tools, so an order listed here may already be paid.

Run it from the repository folder:
    python -m scripts.late_deliveries
"""

from harborline import data, policy


def late_orders(orders):
    """Return one row per order that the late-delivery rule refunds."""
    rows = []
    for order in orders:
        if order.get("delivered_at") is None:
            continue
        decision = policy.check_refund(order, "late_delivery")
        if not decision["allowed"]:
            continue
        promised = policy.as_date(order["promised_by"])
        delivered = policy.as_date(order["delivered_at"])
        rows.append({
            "order_id": order["order_id"],
            "customer_id": order["customer_id"],
            "promised": str(promised),
            "delivered": str(delivered),
            "days_late": (delivered - promised).days,
            "fee": decision["refund"],
        })
    return sorted(rows, key=lambda row: row["order_id"])


def main():
    rows = late_orders(data.orders())
    if not rows:
        print("No late deliveries.")
        return 0

    print(f"{'order':<10} {'customer':<10} {'promised':<11} {'delivered':<11} {'late':>5} {'fee':>8}")
    for row in rows:
        print(f"{row['order_id']:<10} {row['customer_id']:<10} {row['promised']:<11} "
              f"{row['delivered']:<11} {row['days_late']:>5} {row['fee']:>8.2f}")

    total = sum(row["fee"] for row in rows)
    print(f"\n{len(rows)} orders. Total shipping fees owed: ${total:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
