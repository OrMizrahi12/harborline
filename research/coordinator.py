"""Harborline's research coordinator: a hub with three subagents.

The coordinator gets a goal and what a good answer looks like, splits
the work so no two subagents cover the same ground, starts independent
subagents together, and checks the answer against the goal. Each line
it prints starts with the seconds since the run began.

    python -m research.coordinator "Should Harborline charge for return shipping?"
"""

import asyncio
import sys
import time

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions,
                              HookMatcher, ResultMessage, TextBlock,
                              ToolUseBlock, UserMessage, query)
from dotenv import load_dotenv

from harborline.config import MODEL
from research.agents import AGENTS
from research.tools import server

RESEARCH_TOOLS = ["mcp__research__search_web", "mcp__research__fetch_url"]


async def spokes_only(input_data, tool_use_id, context):
    """The hub routes; only a subagent searches or reads."""
    if input_data.get("agent_id"):
        return {}  # called inside a subagent
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            "The coordinator doesn't search or read. Delegate with the "
            "Agent tool: searcher finds sources, analyst reads them."),
    }}


OPTIONS = ClaudeAgentOptions(
    system_prompt=(
        "You coordinate research for Harborline, an online home-goods "
        "store. The research tools work on a saved copy of the web, "
        "where every URL ends in .example; Harborline's own documents "
        "start with harborline://internal/. You don't search or read "
        "yourself: searcher finds sources, analyst reads them and "
        "returns findings as JSON, synthesizer writes the answer from "
        "findings. Subagents know only what you write in their prompt.\n"
        "Goal: an answer Harborline's managers can act on. A good answer "
        "covers the cost of returns, how customers react to a fee, what "
        "competitors do, and Harborline's own data; keeps every claim "
        "with its source; and shows where sources disagree.\n"
        "Split the work so no two subagents cover the same ground, for "
        "example by part of the goal or by source type (web pages, "
        "Harborline's documents). Subagents that don't depend on each "
        "other start together, in one response.\n"
        "Before you answer, check the synthesizer's answer against the "
        "goal. If a part is missing, send a subagent for that gap only, "
        "then have the synthesizer write again with all the findings. "
        "Give it findings whole, as JSON, and ask for at most ten lines. "
        "Your answer is the synthesizer's."),
    model=MODEL,
    agents=AGENTS,
    mcp_servers={"research": server},
    tools=["Agent"],
    allowed_tools=["Agent"] + RESEARCH_TOOLS,
    hooks={"PreToolUse": [HookMatcher(matcher="mcp__research__.*",
                                      hooks=[spokes_only])]},
    permission_mode="dontAsk",
    setting_sources=[],
    env={"CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",  # wait for each report
         "CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS": "1"},  # only our three
    max_turns=10,
    max_budget_usd=0.10,
)


def covered(spans):
    """Seconds when at least one subagent was running."""
    total, end = 0.0, 0.0
    for a, b in sorted(spans):
        total += max(0.0, b - max(a, end))
        end = max(end, b)
    return total


async def main(question):
    names, started, counts, spans, reply = {}, {}, {}, [], ""
    start = time.monotonic()
    async for message in query(prompt=question, options=OPTIONS):
        now = time.monotonic() - start
        if isinstance(message, AssistantMessage):
            inside = message.parent_tool_use_id  # None: the coordinator
            for block in message.content:
                if isinstance(block, ToolUseBlock) and block.name == "Agent":
                    kind = block.input["subagent_type"]
                    counts[kind] = counts.get(kind, 0) + 1
                    names[block.id] = f"{kind} {counts[kind]}"
                    started[block.id] = now
                    print(f"{now:5.1f}s -> {names[block.id]}: "
                          f"{block.input['prompt'][:60]}...")
                elif isinstance(block, ToolUseBlock):
                    tool = block.name.split("__")[-1]
                    who = names.get(inside, "coordinator, denied")  # the hook
                    print(f"{now:5.1f}s    [{who}] {tool}",
                          *block.input.values())
                elif isinstance(block, TextBlock) and inside is None:
                    reply = block.text  # the last one is the answer
        elif isinstance(message, UserMessage) and isinstance(message.content,
                                                             list):
            for block in message.content:  # a subagent's report is back
                done = getattr(block, "tool_use_id", None)
                if done in started:
                    spans.append((started[done], now))
                    print(f"{now:5.1f}s <- {names[done]} done "
                          f"({now - started[done]:.1f}s)")
        elif isinstance(message, ResultMessage):
            print("\n" + reply)
            print(f"\nsubagents: {', '.join(names.values()) or 'none'}")
            work, clock = sum(b - a for a, b in spans), covered(spans)
            print(f"subagents worked {work:.0f}s in {clock:.0f}s of clock "
                  f"time: running together saved {work - clock:.0f}s")
            print(f"{now:.0f}s in all · {message.num_turns} turns · "
                  f"${message.total_cost_usd:.4f}")


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    asyncio.run(main(sys.argv[1]))
