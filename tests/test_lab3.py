"""Lab 3's self-check, part 1: the support agent and its rules, offline. No API
key, no cost. Copy this file into your project's tests/ folder."""

import pytest
from claude_agent_sdk import ResultMessage

from harborline import backend, policy
from harborline.errors import PermissionDenied, PolicyViolation
from loop.tools import PROCESS_REFUND
from support import agent, evaluate, gates
from support.hooks import refund_limit
from support.tools import NAMES

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def fresh_backend():
    backend.reset()  # no refunds or escalations yet
    gates.start_case()


# 1. Refunds: one per damaged item, and never more than the order cost.

def test_a_missing_sku_says_what_is_missing():
    order = backend.lookup_order("HL-10181")
    decision = policy.check_refund(order, "damaged")
    assert not decision["allowed"]
    assert "SKU" in decision["rule"] and "None" not in decision["rule"]


def test_the_tool_says_one_refund_with_the_shipping_fee():
    text = PROCESS_REFUND["description"]
    assert "shipping fee" in text and "one refund" in text


def test_a_second_refund_cannot_pass_the_order_total():
    backend.process_refund("HL-10181", 44.95, "damaged", sku="SKU-1003")
    with pytest.raises(PolicyViolation, match="already refunded"):
        backend.process_refund("HL-10181", 44.95, "damaged",
                               sku="SKU-1003")
    assert len(backend.refunds()) == 1


# 2. The rules in code: the gates and the refund-limit hook.

def test_the_gate_blocks_orders_before_verification():
    with pytest.raises(PermissionDenied):
        gates.lookup_order("HL-10181")


def test_list_orders_is_a_tool_behind_the_gate():
    assert "mcp__harborline__list_orders" in NAMES
    with pytest.raises(PermissionDenied):
        gates.list_orders("C-1042")       # nobody verified yet
    gates.case["customer_id"] = "C-1042"
    with pytest.raises(PermissionDenied):
        gates.list_orders("C-1017")       # someone else's orders
    orders = gates.list_orders("C-1042")
    assert [o["order_id"] for o in orders] == ["HL-10183", "HL-10172"]


def refund_call(amount):
    return {"tool_name": "mcp__harborline__process_refund",
            "tool_input": {"order_id": "HL-10210", "reason": "damaged",
                           "amount": amount}}


@pytest.mark.parametrize("amount", [600, "600", 500.01])
async def test_refunds_above_500_are_denied(amount):
    out = await refund_limit(refund_call(amount), "t1", None)
    decision = out["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "escalate_to_human" in decision["permissionDecisionReason"]


@pytest.mark.parametrize("amount", [500, 44.95])
async def test_refunds_up_to_500_go_ahead(amount):
    assert await refund_limit(refund_call(amount), "t1", None) == {}


# 3. Follow-ups go into the same session.

def result(session_id, cost=0.001):
    return ResultMessage(subtype="success", duration_ms=1,
                         duration_api_ms=1, is_error=False, num_turns=1,
                         session_id=session_id, total_cost_usd=cost)


async def test_follow_ups_resume_the_same_session(monkeypatch):
    sent = []

    async def fake_handle(ticket_id, prompt=None, resume=None):
        sent.append((prompt, resume))
        return {"calls": ["get_customer"], "reply": "",
                "result": result("s-1")}

    monkeypatch.setattr(evaluate, "handle", fake_handle)
    ticket = {"ticket_id": "T-015", "follow_ups": ["my email is x@y.z"]}
    calls, cost = await evaluate.conversation(ticket)
    assert sent == [(None, None), ("my email is x@y.z", "s-1")]
    assert calls == ["get_customer", "get_customer"]
    assert cost == pytest.approx(0.002)


async def test_resume_keeps_the_verified_customer(monkeypatch):
    seen = []

    async def fake_query(prompt, options):
        seen.append(options.resume)
        yield result("s-1")

    monkeypatch.setattr(agent, "query", fake_query)
    gates.case["customer_id"] = "C-1042"
    await agent.handle("T-015", prompt="my email is x@y.z", resume="s-1")
    assert gates.case["customer_id"] == "C-1042"
    await agent.handle("T-015", prompt="a new ticket")
    assert gates.case["customer_id"] is None
    assert seen == ["s-1", None]


# 4. The grade and the target.

LABEL = {"outcome": "resolve", "expected_refunds": [
    {"order_id": "HL-10181", "amount": 44.95}]}


@pytest.mark.parametrize("refunds, escalations, verdict, wrong", [
    ([{"order_id": "HL-10181", "amount": 44.95}], [], "resolved", 0),
    ([{"order_id": "HL-10181", "amount": 38.0}], [], "wrong refund", 1),
    ([], [], "refund missing", 0),
    ([], [{"escalation_id": "ESC-0001"}], "escalated, could resolve", 0),
])
def test_grade(refunds, escalations, verdict, wrong):
    assert evaluate.grade(LABEL, refunds, escalations) == (verdict, wrong)


def row(verdict, outcome="resolve", wrong=0):
    return {"split": "dev", "outcome": outcome, "verdict": verdict,
            "wrong": wrong, "cost": 0.001}


def test_the_target_needs_all_three():
    good = [row("resolved")] * 9 + [row("escalated", "escalate")]
    assert evaluate.meets(evaluate.totals(good))             # 9/10, 1/1, 0
    missed = good[:-1] + [row("missed escalation", "escalate")]
    assert not evaluate.meets(evaluate.totals(missed))       # recall 0/1
    paid = good + [row("wrong refund", wrong=1)]
    assert not evaluate.meets(evaluate.totals(paid))         # 9/11, 1 wrong
