"""Lab 3's self-check, part 2: the explicit loop over harborline-mcp.
A fake Claude, the real server in memory (the same server the stdio
process runs). No API key, no cost. Copy this file into tests/."""

import copy
import json
from types import SimpleNamespace

import pytest
from mcp import Client

from harborline import backend
from loop import mcp_agent
from mcp_server.server import app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def fresh_backend(monkeypatch):
    backend.reset()  # no refunds yet; HL-10211's one timeout armed
    monkeypatch.setattr(mcp_agent, "log_usage", lambda response, label: None)


def tool_use(id_, name, **arguments):
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=arguments)


def response(stop_reason, *content):
    return SimpleNamespace(stop_reason=stop_reason, content=list(content),
                           stop_details=None)


class FakeClaude:
    """Returns the responses a test writes, in order; keeps each request."""

    def __init__(self, *responses):
        self.responses, self.requests = list(responses), []
        self.messages = self  # client.messages.create(...)

    async def create(self, **request):
        self.requests.append(copy.copy(request)
                             | {"messages": list(request["messages"])})
        return self.responses.pop(0)


async def loop(*responses):
    """Run the loop on the fake responses; return the history and the case."""
    case = {"customer_id": None}
    messages = [{"role": "user", "content": "From: a customer\n\nHelp."}]
    async with Client(app) as session:
        await mcp_agent.run(FakeClaude(*responses), session, [],
                            messages, case)
    results = [block for m in messages[2::2] for block in m["content"]]
    return results, case


def body(result):
    return json.loads(result["content"])


def test_the_guard_runs_before_the_server():
    case = {"customer_id": None}
    lookup = tool_use("t1", "lookup_order", order_id="HL-10181")
    assert "get_customer" in mcp_agent.guard(lookup, case)
    case["customer_id"] = "C-1019"
    assert mcp_agent.guard(lookup, case) is None
    for amount in (549, "600"):
        refund = tool_use("t2", "process_refund", amount=amount)
        assert "escalate_to_human" in mcp_agent.guard(refund, case)
    assert mcp_agent.guard(tool_use("t3", "process_refund", amount=500),
                           case) is None


async def test_an_order_lookup_before_verification_never_runs():
    results, case = await loop(
        response("tool_use", tool_use("t1", "lookup_order",
                                      order_id="HL-10181")),
        response("end_turn"))
    [result] = results
    assert result["is_error"] and body(result)["isRetryable"] is False
    assert case["customer_id"] is None


async def test_a_refund_above_500_is_redirected_and_never_paid():
    results, case = await loop(
        response("tool_use", tool_use("t1", "get_customer",
                                      email="julian.szabo@example.com")),
        response("tool_use", tool_use("t2", "process_refund",
                                      order_id="HL-10192", reason="damaged",
                                      amount=549.0, sku="SKU-1004")),
        response("end_turn"))
    verified, refused = results
    assert case["customer_id"] == "C-1047" and not verified.get("is_error")
    assert refused["is_error"] and "support lead" in body(refused)["message"]
    assert backend.refunds() == []


async def test_a_transient_error_gets_one_more_try():
    results, _ = await loop(
        response("tool_use", tool_use("t1", "get_customer",
                                      email="samir.ferreira@example.com")),
        response("tool_use", tool_use("t2", "lookup_order",
                                      order_id="HL-10211")),
        response("end_turn"))
    assert not results[1].get("is_error")
    assert body(results[1])["order_id"] == "HL-10211"


async def test_the_hand_off_runs_in_our_process():
    results, _ = await loop(
        response("tool_use", tool_use("t1", "get_customer",
                                      email="julian.szabo@example.com")),
        response("tool_use", tool_use(
            "t2", "escalate_to_human", customer_id="C-1047",
            order_id="HL-10192", root_cause="Refund above $500",
            amount=549.0, recommended_action="Approve the refund",
            summary="Damaged espresso machine, delivered 2026-10-12")),
        response("end_turn"))
    assert body(results[1])["escalation_id"] == "ESC-0001"
    [case] = backend.escalations()
    assert case["amount"] == 549.0 and case["order_id"] == "HL-10192"


async def test_the_loop_stops_on_an_unknown_stop_reason():
    claude = FakeClaude(response("model_context_window_exceeded"))
    async with Client(app) as session:
        with pytest.raises(mcp_agent.LoopStopped):
            await mcp_agent.run(claude, session, [], [], {"customer_id": None})
