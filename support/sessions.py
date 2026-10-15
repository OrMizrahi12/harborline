"""Sessions: come back to an analysis later, or branch it.

    python -m support.sessions new review "Read support/hooks.py ..."
    python -m support.sessions resume review "Which hook ...?"
    python -m support.sessions fork review tests-a "Plan ..."

A session is the whole conversation: every prompt, tool call, result
and reply, saved on disk. Resume continues it; fork copies it into a
new session and leaves the original as it was. runs/sessions.json
keeps a name for each session ID.
"""

import asyncio
import json
import sys
import textwrap
from dataclasses import replace
from pathlib import Path

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions,
                              ResultMessage, TextBlock, ToolUseBlock,
                              query)
from dotenv import load_dotenv

from harborline.config import MODEL

NAMES = Path("runs/sessions.json")
REVIEW = ClaudeAgentOptions(
    system_prompt="You review Harborline's support code. "
                  "Answer in at most five short lines.",
    model=MODEL,
    tools=["Read", "Grep", "Glob"],
    allowed_tools=["Read", "Grep", "Glob"],
    permission_mode="dontAsk",
    setting_sources=[],
    max_turns=10,
    max_budget_usd=0.10,
)


async def ask(prompt, **session):
    """One run: a new, a resumed or a forked session."""
    tools, reply, session_id = [], "", None
    options = replace(REVIEW, **session)
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    path = block.input.get("file_path", "")
                    tools.append(f"{block.name} {Path(path).name}")
                elif isinstance(block, TextBlock):
                    reply = block.text
        elif isinstance(message, ResultMessage):
            session_id = message.session_id
    return session_id, tools, reply


async def main(command, name, *words):
    names = json.loads(NAMES.read_text()) if NAMES.exists() else {}
    if command == "new":
        sid, tools, reply = await ask(words[0])
    elif command == "resume":
        sid, tools, reply = await ask(words[0], resume=names[name])
    elif command == "fork":  # from name into a new branch, words[0]
        sid, tools, reply = await ask(words[1], resume=names[name],
                                      fork_session=True)
        name = words[0]
    names[name] = sid
    NAMES.write_text(json.dumps(names, indent=1))
    print("tools:", ", ".join(tools) or "-")
    for line in reply.splitlines():
        print(textwrap.fill(line, 84, subsequent_indent="  "))
    print(f"\nsession {name}: {sid}")


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    asyncio.run(main(*sys.argv[1:]))
