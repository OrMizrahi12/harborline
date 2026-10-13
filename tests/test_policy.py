"""The refund policy, as code."""

from datetime import date

from harborline import policy


def order(delivered="2026-10-01T10:00:00Z", status="delivered", category="home", final_sale=False,
          price=50.0, fee=6.95, promised="2026-09-28"):
    return {
        "status": status,
        "delivered_at": delivered,
        "promised_by": promised,
        "shipping_fee": fee,
        "total": price + fee,
        "items": [{"sku": "SKU-1", "category": category, "final_sale": final_sale,
                   "unit_price": price, "quantity": 1}],
    }


def test_timestamps_in_both_formats_become_dates():
    assert policy.as_date("2026-09-03T14:22:05Z") == date(2026, 9, 3)
    assert policy.as_date("2026-09-03T21:30:00-04:00") == date(2026, 9, 3)
    assert policy.as_date(1751464800) == date(2025, 7, 2)
    assert policy.as_date(None) is None


def test_change_of_mind_within_30_days_refunds_the_item_only():
    decision = policy.check_refund(order(), "changed_mind", sku="SKU-1")
    assert decision == {"allowed": True, "refund": 50.0, "rule": decision["rule"]}


def test_change_of_mind_after_30_days_is_refused():
    decision = policy.check_refund(order(delivered="2026-09-01T10:00:00Z"), "changed_mind", sku="SKU-1")
    assert decision["allowed"] is False


def test_opened_electronics_have_15_days():
    o = order(delivered="2026-09-25T10:00:00Z", category="electronics")
    assert policy.check_refund(o, "changed_mind", sku="SKU-1", opened=False)["allowed"] is True
    assert policy.check_refund(o, "changed_mind", sku="SKU-1", opened=True)["allowed"] is False


def test_final_sale_only_for_damage():
    o = order(final_sale=True)
    assert policy.check_refund(o, "changed_mind", sku="SKU-1")["allowed"] is False
    damaged = policy.check_refund(o, "damaged", sku="SKU-1")
    assert damaged["allowed"] is True
    assert damaged["refund"] == 56.95  # item plus shipping


def test_cancel_only_before_shipment():
    assert policy.check_refund(order(status="processing", delivered=None), "cancel_before_shipment")["refund"] == 56.95
    assert policy.check_refund(order(status="shipped", delivered=None), "cancel_before_shipment")["allowed"] is False


def test_late_delivery_refunds_shipping():
    late = order(delivered="2026-10-05T10:00:00Z", promised="2026-09-28")
    on_time = order(delivered="2026-09-30T10:00:00Z", promised="2026-09-28")
    assert policy.check_refund(late, "late_delivery")["refund"] == 6.95
    assert policy.check_refund(on_time, "late_delivery")["allowed"] is False


def test_shipping_charged_on_a_free_shipping_order():
    assert policy.check_refund(order(price=80.0), "shipping_charged_in_error")["refund"] == 6.95
    assert policy.check_refund(order(price=40.0), "shipping_charged_in_error")["allowed"] is False


def test_refunds_above_500_need_approval():
    assert policy.needs_approval(500.00) is False
    assert policy.needs_approval(500.01) is True
