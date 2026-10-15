"""Lab 3: the Module 1 loop, with its tools from harborline-mcp.

Claude decides; our loop checks every stop reason and runs each tool
call through the MCP server, a separate process over stdio. Two rules
run in our code before a call reaches the server, whatever Claude
decided: verify the customer first, and refunds above $500 go to a
person. A transient error gets one more try.

    python -m loop.mcp_agent T-046
"""

import asyncio
import json
import logging
import os
import sys

import anthropic
from dotenv import load_dotenv
from mcp import Client, StdioServerParameters
from mcp.client.stdio import get_default_environment

from experiments.m2.mcp_routing import as_api_tool
from harborline import backend
from harborline.config import MAX_TOKENS, MODEL, ROOT_DIR
from harborline.errors import BackendError
from harborline.tool_errors import tool_error
from harborline.usage import log_usage
from loop.agent import (MAX_CONTINUATIONS, MAX_TOKENS_CEILING, MAX_TURNS,
                        CutOff, LoopStopped, Refused, first_message,
                        refusal_category, show)
from support.agent import SYSTEM
from support.handoff import HANDOFF
from support.hooks import REFUND_LIMIT

ESCALATE = {"name": "escalate_to_human"} | HANDOFF  # runs here, not on the server
NEEDS_CUSTOMER = ("lookup_order", "list_orders", "process_refund")


def server():
    """Start harborline-mcp as a child process, with its token only."""
    env = get_default_environment() | {
        "HARBORLINE_API_TOKEN": os.environ.get("HARBORLINE_API_TOKEN", "")}
    return StdioServerParameters(command=sys.executable, cwd=ROOT_DIR,
                                 args=["-m", "mcp_server.server"], env=env)


def guard(call, case):
    """Rules that hold on every call. None: the call may run."""
    if call.name in NEEDS_CUSTOMER and case["customer_id"] is None:
        return "No verified customer yet: call get_customer first."
    if call.name == "process_refund":
        try:
            amount = float(call.input.get("amount", 0))
        except (TypeError, ValueError):
            return "The amount must be a number."
        if amount > REFUND_LIMIT:
            return (f"Refunds above ${REFUND_LIMIT:.0f} need a support "
                    "lead. Call escalate_to_human instead; don't retry.")
    return None


def escalate(arguments):
    """The hand-off, recorded in our own process."""
    return backend.escalate_to_human(
        customer_id=arguments["customer_id"],
        order_id=arguments["order_id"], reason=arguments["root_cause"],
        amount=arguments["amount"],
        recommended_action=arguments["recommended_action"],
        summary=arguments["summary"])


async def run_call(session, call, case):
    """One tool_use block in, its tool_result block out."""
    result = {"type": "tool_result", "tool_use_id": call.id}
    problem = guard(call, case)
    if problem:  # never sent to the server
        body = {"errorCategory": "permission", "isRetryable": False,
                "message": problem}
        return result | {"content": json.dumps(body), "is_error": True}
    if call.name == "escalate_to_human":
        try:
            return result | {"content": json.dumps(escalate(call.input))}
        except (BackendError, KeyError) as error:
            text = (tool_error(error) if isinstance(error, BackendError)
                    else f"Missing field {error}.")
            return result | {"content": text, "is_error": True}
    for attempt in (1, 2):
        reply = await session.call_tool(call.name, call.input)
        text = reply.content[0].text
        if not reply.is_error or not json.loads(text).get("isRetryable"):
            break  # done, or an error that another try won't fix
    if reply.is_error:
        return result | {"content": text, "is_error": True}
    if call.name == "get_customer":
        output = json.loads(text)
        if output.get("verified"):
            case["customer_id"] = output["customer"]["customer_id"]
    return result | {"content": text}


async def run(client, session, tools, messages, case):
    """Call Claude until it ends its turn; return every response."""
    responses = []
    max_tokens = MAX_TOKENS
    continuations = 0
    for turn in range(1, MAX_TURNS + 1):
        response = await client.messages.create(
            model=MODEL, max_tokens=max_tokens, system=SYSTEM,
            tools=tools, messages=messages,
        )
        log_usage(response, "lab 3 mcp agent")
        responses.append(response)
        show(turn, response)
        reason = response.stop_reason

        if reason == "max_tokens":
            if max_tokens >= MAX_TOKENS_CEILING:
                raise CutOff(f"still cut off at max_tokens={max_tokens}")
            max_tokens = min(2 * max_tokens, MAX_TOKENS_CEILING)
            continue
        if reason == "refusal":
            raise Refused(refusal_category(response))
        if reason == "pause_turn":
            continuations += 1
            if continuations > MAX_CONTINUATIONS:
                raise LoopStopped("paused too many times")
            messages.append({"role": "assistant",
                             "content": response.content})
            continue
        if reason not in ("tool_use", "end_turn"):
            raise LoopStopped(f"stopped on {reason}")

        messages.append({"role": "assistant", "content": response.content})
        if reason == "end_turn":
            return responses
        results = [await run_call(session, block, case)
                   for block in response.content if block.type == "tool_use"]
        for result in results:
            error = " is_error" if result.get("is_error") else ""
            print(f"  [tool_result{error}]", result["content"][:70])
        messages.append({"role": "user", "content": results})
    raise LoopStopped(f"no end_turn after {MAX_TURNS} turns")


async def main(ticket_id):
    client = anthropic.AsyncAnthropic()
    async with Client(server()) as session:
        listed = (await session.list_tools()).tools
        tools = [as_api_tool(t) for t in listed] + [ESCALATE]
        print("tools:", ", ".join(t["name"] for t in tools))
        messages = [first_message(ticket_id)]
        try:
            await run(client, session, tools, messages,
                      {"customer_id": None})
        except LoopStopped as stop:
            print(f"\nNo answer: {stop}. Hand this ticket to a person.")
    for case in backend.escalations():
        print(f"\nescalated: {case['escalation_id']} {case['customer_id']} "
              f"{case['order_id']} ${case['amount']}: {case['reason']}")


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY and HARBORLINE_API_TOKEN from .env
    logging.getLogger("httpx2").setLevel(logging.WARNING)  # one line per request is noise
    asyncio.run(main(sys.argv[1]))
