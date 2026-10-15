"""Hello, Agent SDK: Claude Code's agent loop as a library.

    python -m support.hello_agent T-008
"""

import asyncio
import sys

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions,
                              ResultMessage, SystemMessage, TextBlock,
                              ToolUseBlock, query)
from dotenv import load_dotenv

from harborline.config import BUSINESS_DATE, MODEL
from loop.agent import first_message
from support.tools import server

OPTIONS = ClaudeAgentOptions(
    system_prompt=(
        "You are Harborline's customer support agent. "
        f"Today is {BUSINESS_DATE}. Verify the sender with "
        "get_customer first; only then look up their order. "
        "You can't issue refunds yet. Answer in four sentences "
        "or fewer, in plain text."),
    model=MODEL,
    mcp_servers={"harborline": server},
    tools=[],  # no built-in tools: no Bash, no file access
    allowed_tools=["mcp__harborline__get_customer",
                   "mcp__harborline__lookup_order"],
    permission_mode="dontAsk",  # not allowed means denied, not asked
    setting_sources=[],  # no Claude Code settings from this machine
    max_turns=6,  # safety nets
    max_budget_usd=0.05,
)


async def main(ticket_id):
    prompt = first_message(ticket_id)["content"]
    async for message in query(prompt=prompt, options=OPTIONS):
        if isinstance(message, SystemMessage) and message.subtype == "init":
            print("tools:", message.data["tools"])
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print("[tool]", block.name, block.input)
                elif isinstance(block, TextBlock):
                    print("[text]", block.text)
        elif isinstance(message, ResultMessage):
            print(f"\n{message.subtype}: {message.num_turns} turns, "
                  f"${message.total_cost_usd:.4f}")


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    asyncio.run(main(sys.argv[1]))
