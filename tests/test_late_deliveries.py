"""The late-delivery report finds the orders the refund policy covers."""

from datetime import datetime, timezone

from harborline import data
from scripts import late_deliveries


def _order(order_id="HL-99999", promised_by="2026-09-01", delivered_at="2026-09-10T12:00:00Z",
           status="delivered", shipping_fee=5.00):
    return {
        "order_id": order_id,
        "customer_id": "C-0001",
        "status": status,
        "promised_by": promised_by,
        "delivered_at": delivered_at,
        "shipping_fee": shipping_fee,
        "items": [{"sku": "SKU-0001", "unit_price": 20.0, "quantity": 1,
                   "category": "home", "final_sale": False}],
        "total": 25.0,
    }


def test_real_data_lists_the_two_known_late_orders():
    rows = late_deliveries.late_orders(data.orders())

    assert [row["order_id"] for row in rows] == ["HL-10147", "HL-10148"]
    assert [row["fee"] for row in rows] == [6.95, 6.95]
    assert [row["days_late"] for row in rows] == [8, 8]
    assert round(sum(row["fee"] for row in rows), 2) == 13.90


def test_exactly_five_days_late_is_not_included():
    on_time_edge = _order(promised_by="2026-09-01", delivered_at="2026-09-06T12:00:00Z")
    assert late_deliveries.late_orders([on_time_edge]) == []


def test_six_days_late_is_included():
    late = _order(promised_by="2026-09-01", delivered_at="2026-09-07T12:00:00Z")
    rows = late_deliveries.late_orders([late])
    assert [row["days_late"] for row in rows] == [6]
    assert rows[0]["fee"] == 5.00


def test_legacy_unix_timestamps_and_offset_iso_are_compared_correctly():
    # Legacy warehouse order: Unix seconds for both dates.
    promised = int(datetime(2026, 8, 1, tzinfo=timezone.utc).timestamp())
    delivered = int(datetime(2026, 8, 10, tzinfo=timezone.utc).timestamp())
    legacy = _order(order_id="HL-00001", promised_by=promised, delivered_at=delivered)

    # Web order: offset ISO delivery time against a bare-date promise.
    web = _order(order_id="HL-00002", promised_by="2026-08-01",
                 delivered_at="2026-08-09T18:30:00-04:00")

    rows = late_deliveries.late_orders([legacy, web])
    assert [(row["order_id"], row["days_late"]) for row in rows] == [("HL-00001", 9), ("HL-00002", 8)]


def test_undelivered_and_cancelled_orders_are_skipped():
    undelivered = _order(order_id="HL-00003", delivered_at=None)
    cancelled = _order(order_id="HL-00004", status="cancelled")
    assert late_deliveries.late_orders([undelivered, cancelled]) == []


def test_main_prints_each_order_and_the_total(capsys):
    assert late_deliveries.main() == 0
    out = capsys.readouterr().out

    assert "HL-10147" in out
    assert "HL-10148" in out
    assert "$13.90" in out
