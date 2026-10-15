"""Harborline's support agent: a ticket in, a reply and actions out.

    python -m support.agent T-003
"""

import asyncio
import sys
from pathlib import Path

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions,
                              ResultMessage, TextBlock, ToolUseBlock,
                              query)
from dotenv import load_dotenv

from harborline import data
from harborline.config import BUSINESS_DATE, MODEL
from loop.agent import first_message
from support import gates
from support.hooks import HOOKS
from support.tools import NAMES, server

PROMPT = Path(__file__).parent / "prompts" / "system.md"
SYSTEM = (PROMPT.read_text().replace("{date}", str(BUSINESS_DATE))
          .replace("{policy}", data.refund_policy()))

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
    hooks=HOOKS,
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
