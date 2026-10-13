"""The labeled tickets agree with the policy and the data."""

from collections import Counter

from harborline import data, policy


def test_outcomes_and_splits():
    tickets = data.tickets()
    outcomes = Counter(t["label"]["outcome"] for t in tickets)
    assert outcomes == {"resolve": 42, "escalate": 8}
    assert Counter(t["split"] for t in tickets) == {"dev": 20, "test": 30}
    dev = Counter(t["label"]["outcome"] for t in tickets if t["split"] == "dev")
    assert dev == {"resolve": 17, "escalate": 3}


def test_expected_refunds_match_the_policy():
    orders = {o["order_id"]: o for o in data.orders()}
    for ticket in data.tickets():
        for refund in ticket["label"]["expected_refunds"]:
            decision = policy.check_refund(orders[refund["order_id"]], refund["reason"], sku=refund["sku"])
            assert decision["allowed"] and decision["refund"] == refund["amount"], ticket["ticket_id"]


def test_tickets_name_real_orders_of_the_right_customer():
    orders = {o["order_id"]: o for o in data.orders()}
    for ticket in data.tickets():
        for order_id in ticket["label"]["order_ids"]:
            assert orders[order_id]["customer_id"] == ticket["label"]["customer_id"]


def test_escalations_have_a_reason_and_no_refund():
    for ticket in data.tickets():
        label = ticket["label"]
        if label["outcome"] == "escalate":
            assert label["escalation_reason"]
            assert label["expected_refunds"] == []


def test_tool_routing_cases_name_known_tools():
    tools = {"get_customer", "lookup_order", "list_orders", "process_refund", "escalate_to_human"}
    cases = data.tool_routing_cases()
    assert len(cases) == 16
    assert {c["expected_tool"] for c in cases} == tools
