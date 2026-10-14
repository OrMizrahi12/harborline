"""Lab 1 self-check: the agentic loop against a scripted fake client.

No API calls: FakeClient returns the responses each test writes, in order,
and records every request the loop sends.
"""

import copy
from types import SimpleNamespace

import pytest

from harborline import backend
from loop import agent


def text(value):
    return SimpleNamespace(type="text", text=value)


def tool_use(id_, name, **arguments):
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=arguments)


def reply(stop_reason, *content, category=None):
    details = SimpleNamespace(type="refusal", category=category) if category else None
    return SimpleNamespace(stop_reason=stop_reason, content=list(content),
                           stop_details=details, model="claude-haiku-5-5")


class FakeClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
        self.messages = self   # client.messages.create(...)

    def create(self, **request):
        self.requests.append(copy.copy(request) | {"messages": list(request["messages"])})
        if not self.responses:
            raise AssertionError("the loop sent one request too many")
        return self.responses.pop(0)


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    monkeypatch.setattr(agent, "log_usage", lambda response, label: None)
    backend.reset()


def ask(*responses):
    client = FakeClient(*responses)
    messages = [{"role": "user", "content": "Where is my order HL-10163?"}]
    return client, messages


def roles(messages):
    return [m["role"] for m in messages]


def test_end_turn_returns_the_answer():
    client, messages = ask(reply("end_turn", text("It was delivered.")))
    responses = agent.run(client, messages)
    assert len(responses) == 1 and len(client.requests) == 1
    assert roles(messages) == ["user", "assistant"]


def test_tool_use_then_end_turn():
    client, messages = ask(
        reply("tool_use", text("Checking the order."), tool_use("t1", "lookup_order", order_id="HL-10163")),
        reply("end_turn", text("It was delivered on October 3.")),
    )
    agent.run(client, messages)
    assert roles(messages) == ["user", "assistant", "user", "assistant"]
    [result] = messages[2]["content"]
    assert result["type"] == "tool_result" and result["tool_use_id"] == "t1"
    assert "HL-10163" in result["content"] and not result.get("is_error")
    # the second request carries the whole history, not just the result
    assert len(client.requests[1]["messages"]) == 3


def test_parallel_calls_answered_in_one_user_turn():
    client, messages = ask(
        reply("tool_use", tool_use("a", "lookup_order", order_id="HL-10168"),
              tool_use("b", "lookup_order", order_id="HL-10202")),
        reply("end_turn", text("Both orders found.")),
    )
    agent.run(client, messages)
    results = messages[2]["content"]
    assert [r["tool_use_id"] for r in results] == ["a", "b"]
    assert roles(messages) == ["user", "assistant", "user", "assistant"]


def test_tool_error_goes_back_with_is_error():
    client, messages = ask(
        reply("tool_use", tool_use("x", "lookup_order", order_id="12345")),
        reply("end_turn", text("Could you send the HL- order ID?")),
    )
    agent.run(client, messages)
    [result] = messages[2]["content"]
    assert result["is_error"] is True and "not an order ID" in result["content"]


def test_max_tokens_retries_with_more_room_and_drops_the_cut_reply():
    client, messages = ask(
        reply("max_tokens", text("Your pillow from HL-10168 was deliv")),
        reply("end_turn", text("Your pillow can be returned.")),
    )
    agent.run(client, messages)
    first, second = client.requests
    assert second["max_tokens"] == 2 * first["max_tokens"]
    assert second["messages"] == first["messages"]      # the same request again
    assert roles(messages) == ["user", "assistant"]     # the cut reply is not kept
    assert messages[1]["content"][0].text == "Your pillow can be returned."


def test_max_tokens_at_the_ceiling_fails_loudly():
    cut = [reply("max_tokens", text("cut")) for _ in range(5)]
    client, messages = ask(*cut)
    with pytest.raises(agent.CutOff):
        agent.run(client, messages)
    assert client.requests[-1]["max_tokens"] == agent.MAX_TOKENS_CEILING


def test_pause_turn_sends_the_paused_turn_back():
    paused = reply("pause_turn", SimpleNamespace(type="server_tool_use", id="s1", name="web_search", input={}))
    client, messages = ask(paused, reply("end_turn", text("Done.")))
    agent.run(client, messages)
    # the paused turn goes back as the last message, with no user message after it
    assert roles(client.requests[1]["messages"]) == ["user", "assistant"]
    assert client.requests[1]["messages"][-1]["content"] == paused.content


def test_refusal_stops_without_a_retry():
    client, messages = ask(reply("refusal", category="cyber"), reply("end_turn", text("never sent")))
    with pytest.raises(agent.Refused) as stop:
        agent.run(client, messages)
    assert stop.value.category == "cyber"
    assert len(client.requests) == 1                     # not resent
    assert roles(messages) == ["user"]                   # nothing to keep


def test_other_stop_reasons_are_not_answers():
    client, messages = ask(reply("stop_sequence", text("partial")))
    with pytest.raises(agent.LoopStopped, match="stop_sequence"):
        agent.run(client, messages)


def test_max_turns_is_a_failure_not_an_answer():
    calls = [reply("tool_use", tool_use(f"t{i}", "lookup_order", order_id="HL-10163"))
             for i in range(agent.MAX_TURNS)]
    client, messages = ask(*calls)
    with pytest.raises(agent.LoopStopped, match="no end_turn"):
        agent.run(client, messages)
    assert len(client.requests) == agent.MAX_TURNS
