"""Harborline's support agent: a ticket in, a reply and actions out.

    python -m support.agent T-003
"""

import asyncio
import sys

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions,
                              ResultMessage, TextBlock, ToolUseBlock,
                              query)
from dotenv import load_dotenv

from harborline.config import BUSINESS_DATE, MODEL
from loop.agent import first_message
from support import gates
from support.tools import NAMES, server

SYSTEM = (
    "You are Harborline's customer support agent. "
    f"Today is {BUSINESS_DATE}. Verify the sender with get_customer "
    "first, then look up the order. Refund what the refund policy "
    "allows: process_refund checks it. Hand the case to a person with "
    "escalate_to_human when the customer asks for one, when a refund "
    "is above $500, or when the policy doesn't cover the request. "
    "Reply in four sentences or fewer, in plain text.")

OPTIONS = ClaudeAgentOptions(
    system_prompt=SYSTEM,
    model=MODEL,
    mcp_servers={"harborline": server},
    tools=[],
    allowed_tools=NAMES,
    permission_mode="dontAsk",
    setting_sources=[],
    max_turns=10,
    max_budget_usd=0.10,
)


async def handle(ticket_id, prompt=None):
    """One ticket: the tools Claude called, its reply, the result."""
    gates.start_case()
    prompt = prompt or first_message(ticket_id)["content"]
    calls, reply, result = [], "", None
    async for message in query(prompt=prompt, options=OPTIONS):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    calls.append(block.name.split("__")[-1])
                elif isinstance(block, TextBlock):
                    reply = block.text
        elif isinstance(message, ResultMessage):
            result = message
    return {"calls": calls, "reply": reply, "result": result}


async def main(ticket_id):
    case = await handle(ticket_id)
    result = case["result"]
    print("tools:", ", ".join(case["calls"]))
    print("reply:", case["reply"])
    print(f"{result.subtype}: {result.num_turns} turns, "
          f"${result.total_cost_usd:.4f}, session {result.session_id}")


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    asyncio.run(main(sys.argv[1]))
