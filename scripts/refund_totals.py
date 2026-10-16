from harborline import data
from scripts.late_deliveries import late_orders


def totals(orders):
    t = {}
    for r in late_orders(orders):
        c = r["customer_id"]
        t[c] = t.get(c, 0) + r["fee"]
    return t


def main():
    t = totals(data.orders())
    for c in sorted(t, key=t.get, reverse=True)[:10]:
        print(c, "%.2f" % t[c])
    print("total", round(sum(t.values())))


if __name__ == "__main__":
    main()
