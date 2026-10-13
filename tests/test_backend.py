"""The backend behaves like Harborline's real systems would."""

import pytest

from harborline import backend, data
from harborline.errors import (
    InvalidRequest,
    NotFound,
    PermissionDenied,
    PolicyViolation,
    ServiceUnavailable,
)


@pytest.fixture(autouse=True)
def fresh_backend():
    backend.reset()


def a_customer_with_orders():
    order = data.orders()[-1]
    customer = backend.get_customer(customer_id=order["customer_id"])["customer"]
    return customer, order


def test_find_customer_by_email_is_verified():
    customer, _ = a_customer_with_orders()
    result = backend.get_customer(email=customer["email"].upper())
    assert result["verified"] is True
    assert result["customer"]["customer_id"] == customer["customer_id"]


def test_a_shared_name_returns_unverified_candidates():
    result = backend.get_customer(name="Jordan Lee")
    assert result["verified"] is False
    assert len(result["candidates"]) == 2
    assert "@" in result["candidates"][0]["email_hint"]


def test_unknown_customer_and_empty_request():
    with pytest.raises(NotFound):
        backend.get_customer(email="nobody@example.com")
    with pytest.raises(InvalidRequest):
        backend.get_customer()


def test_lookup_checks_the_order_id_format():
    with pytest.raises(InvalidRequest):
        backend.lookup_order("12345")
    with pytest.raises(NotFound):
        backend.lookup_order("HL-99999")


def test_lookup_refuses_another_customers_order():
    _, order = a_customer_with_orders()
    with pytest.raises(PermissionDenied):
        backend.lookup_order(order["order_id"], customer_id="C-1058")


def test_a_slow_order_times_out_once_then_works():
    slow_id = next(iter(data.faults()["slow_orders"]))
    with pytest.raises(ServiceUnavailable) as failure:
        backend.lookup_order(slow_id)
    assert failure.value.retryable is True
    assert backend.lookup_order(slow_id)["order_id"] == slow_id


def test_no_orders_is_an_empty_list_not_an_error():
    assert backend.list_orders("C-1058") == []
    with pytest.raises(NotFound):
        backend.list_orders("C-9999")


def test_list_orders_is_newest_first():
    _, order = a_customer_with_orders()
    summaries = backend.list_orders(order["customer_id"])
    dates = [s["placed_on"] for s in summaries]
    assert dates == sorted(dates, reverse=True)


def test_refunds_follow_the_policy():
    for ticket in data.tickets():
        for refund in ticket["label"]["expected_refunds"]:
            result = backend.process_refund(refund["order_id"], refund["amount"], refund["reason"],
                                            sku=refund["sku"])
            assert result["status"] == "processed"
    assert len(backend.refunds()) == sum(len(t["label"]["expected_refunds"]) for t in data.tickets())


def test_refund_above_the_allowed_amount_is_refused():
    ticket = next(t for t in data.tickets() if t["label"]["story"] == "refund_ok")
    refund = ticket["label"]["expected_refunds"][0]
    with pytest.raises(PolicyViolation):
        backend.process_refund(refund["order_id"], refund["amount"] + 1, refund["reason"], sku=refund["sku"])


def test_final_sale_and_review_hold_are_refused():
    final_sale = next(t for t in data.tickets() if t["label"]["story"] == "final_sale")
    order = backend.lookup_order(final_sale["label"]["order_ids"][0])
    clearance = next(i for i in order["items"] if i["final_sale"])
    with pytest.raises(PolicyViolation):
        backend.process_refund(order["order_id"], 1.00, "changed_mind", sku=clearance["sku"])

    hold = next(t for t in data.tickets() if t["label"]["story"] == "review_hold")
    order = backend.lookup_order(hold["label"]["order_ids"][0])
    with pytest.raises(PermissionDenied):
        backend.process_refund(order["order_id"], 1.00, "changed_mind", sku=order["items"][0]["sku"])


def test_escalation_creates_an_open_case():
    case = backend.escalate_to_human("C-1012", "Refund above $500", "above_approval_limit",
                                     order_id="HL-10177", amount=649.0)
    assert case["status"] == "open"
    assert case["queue"] == "support-leads"
    assert backend.escalations() == [case]
