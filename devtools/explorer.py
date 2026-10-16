"""Harborline's codebase explorer: an Agent SDK agent for developers.

The built-in tools, plus codemap's MCP tools for where names come from.

    python -m devtools.explorer "Where does legacy.warehouse.load_record come from?"
"""

import asyncio
import sys

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions,
                              ResultMessage, TextBlock, ToolUseBlock,
                              query)
from dotenv import load_dotenv

from harborline.config import MODEL, ROOT_DIR

CODEMAP = {"type": "stdio", "command": sys.executable,
           "args": ["-m", "devtools.codemap_server"]}

OPTIONS = ClaudeAgentOptions(
    system_prompt=("You help Harborline's developers understand and extend "
                   "this repository. Name files and line numbers. Write "
                   "files only when asked. Run tests with exactly "
                   ".venv/bin/python -m pytest -q <file>, and fix what fails."),
    model=MODEL,
    cwd=ROOT_DIR,
    mcp_servers={"codemap": CODEMAP},
    tools=["Read", "Grep", "Glob", "Write", "Edit", "Bash"],
    allowed_tools=["Read", "Grep", "Glob", "Write", "Edit",
                   "Bash(.venv/bin/python -m pytest *)",
                   "mcp__codemap__list_public_names",
                   "mcp__codemap__trace_export"],
    permission_mode="dontAsk",
    setting_sources=[],
    max_turns=20,
    max_budget_usd=0.10,
)


async def main(prompt):
    async for message in query(prompt=prompt, options=OPTIONS):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print("tool:", block.name.split("__")[-1], block.input)
                elif isinstance(block, TextBlock):
                    print(block.text)
        elif isinstance(message, ResultMessage):
            print(f"{message.subtype}: {message.num_turns} turns, "
                  f"${message.total_cost_usd:.4f}")


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    asyncio.run(main(sys.argv[1]))
