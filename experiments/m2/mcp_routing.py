"""Lab 2: does Claude still pick the right tool when the tools come
from harborline-mcp instead of loop/tools.py? 3 tries each.

    python -m experiments.m2.mcp_routing
"""

import asyncio
import logging
import textwrap

import anthropic
from dotenv import load_dotenv
from mcp import Client

from experiments.m2.routing_eval import HELD_OUT, TRIES, correct
from harborline import data
from harborline.config import MAX_TOKENS, MODEL
from harborline.usage import log_usage
from mcp_server.server import app

LOOKUPS = ["get_customer", "lookup_order", "list_orders"]
TARGET = 0.9  # held-out: at least 90% of the tries right


def as_api_tool(tool):
    """One MCP tool, in the shape the Messages API takes."""
    return {"name": tool.name, "description": tool.description,
            "input_schema": tool.input_schema}


def cases_for(names):
    """The labeled and held-out cases whose tool the server publishes."""
    labeled = [(c["id"], "C-1046", c["request"], c["expected_tool"], {})
               for c in data.tool_routing_cases()]
    return ([c for c in labeled if c[3] in names],
            [c for c in HELD_OUT if c[3] in names])


async def run_lookup(session, call):
    """Run a lookup through the MCP server; return the tool_result."""
    result = await session.call_tool(call.name, call.input)
    return {"type": "tool_result", "tool_use_id": call.id,
            "content": result.content[0].text, "is_error": result.is_error}


async def decide(client, session, tools, customer, request, want):
    """Claude's first call that matters. Lookups on the way run through
    the server (two rounds at most); nothing else ever runs."""
    text = f"Signed-in customer: {customer}\n\n{request}"
    messages, records = [{"role": "user", "content": text}], []
    for _ in range(3):
        response = await client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS, tools=tools,
            messages=messages,
        )
        records.append(log_usage(response, "lab 2 mcp routing"))
        calls = [b for b in response.content if b.type == "tool_use"]
        for call in calls:
            if call.name == want or call.name not in LOOKUPS:
                return call.name, call.input, records
        if not calls:
            return f"({response.stop_reason})", {}, records
        results = [await run_lookup(session, call) for call in calls]
        messages += [{"role": "assistant", "content": response.content},
                     {"role": "user", "content": results}]
    return "(lookups only)", {}, records


async def main():
    client = anthropic.AsyncAnthropic()
    async with Client(app) as session:
        listed = (await session.list_tools()).tools
        tools = [as_api_tool(t) for t in listed]
        print("tools from harborline-mcp:", ", ".join(t.name for t in listed))
        labeled, held_out = cases_for({t.name for t in listed})
        totals, cost = {}, 0.0
        for title, cases in [("labeled", labeled), ("held-out", held_out)]:
            print(f"-- {title}")
            right_here = 0
            for case_id, customer, request, want, needs in cases:
                tries = await asyncio.gather(*[decide(
                    client, session, tools, customer, request, want)
                    for _ in range(TRIES)])
                misses = []
                for got, given, records in tries:
                    cost += sum(r["cost_usd"] for r in records)
                    if not correct(got, given, want, needs, customer):
                        misses.append(got[:20])
                right = TRIES - len(misses)
                right_here += right
                print(f"{case_id}  {want:15} {right}/{TRIES}"
                      + (f"  got {', '.join(misses)}" if misses else ""))
                if misses:
                    print("     " + textwrap.shorten(request, 54))
            totals[title] = (right_here, TRIES * len(cases))
    print()
    for title, (right, out_of) in totals.items():
        print(f"{title:9} {right}/{out_of}")
    right, out_of = totals["held-out"]
    verdict = "PASS" if right >= TARGET * out_of else "below target"
    print(f"held-out target {TARGET:.0%}: {verdict}   ${cost:.4f}")


if __name__ == "__main__":
    load_dotenv()
    logging.getLogger("httpx").setLevel(logging.WARNING)  # one line per request is noise
    asyncio.run(main())
