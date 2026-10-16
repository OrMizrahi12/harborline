"""Print the shipping fees owed this week, largest first.

    python -m scripts.weekly_fees
"""

from harborline.fees import owed_by_customer


def main():
    owed = owed_by_customer()
    for customer_id, amount in sorted(owed.items(), key=lambda item: -item[1]):
        print(f"{customer_id}  ${amount:,.2f}")
    print(f"total  ${sum(owed.values()):,.2f}")


if __name__ == "__main__":
    main()
