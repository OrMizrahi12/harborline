"""Harborline's research coordinator: a hub with three subagents.

The coordinator picks the subagents a question needs, briefs them and
writes the answer. The subagents search and read, each in a fresh
context: all they get from the coordinator is the prompt it writes.

    python -m research.coordinator "Should Harborline charge for return shipping?"
"""

import asyncio
import json
import sys
import textwrap

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions,
                              HookMatcher, ResultMessage, SystemMessage,
                              TextBlock, ToolUseBlock, query)
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
        "where every URL ends in .example. You don't search or read "
        "yourself. Your subagents: "
        "searcher finds sources, analyst reads them and returns findings "
        "as JSON, synthesizer writes the answer from findings. Use only "
        "the ones the question needs. They know only what you write in "
        "their prompt: include the question and everything they need. "
        "Use only what they report, never your own knowledge. Give the "
        "synthesizer the analyst's findings complete and unchanged, the "
        "whole JSON, never a summary, and ask for at most eight lines. "
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
    env={"CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1"},  # wait for each report
    max_turns=10,
    max_budget_usd=0.10,
)


def findings(text):
    """The list of findings handed over in a prompt, if there is one."""
    try:
        found = json.loads(text[text.index("["):text.rindex("]") + 1])
    except ValueError:
        return None
    return found if found and isinstance(found[0], dict) else None


def show(prompt):
    found = findings(prompt)
    text = prompt[:prompt.index("[")] if found else prompt
    for line in text.strip().splitlines():
        print(textwrap.fill(line, 78, initial_indent="   ",
                            subsequent_indent="   "))
    if found:  # handed over whole: say what, instead of printing it all
        print(f"   [ {len(found)} findings as JSON, keys: "
              f"{', '.join(found[0])} ]")


async def main(question):
    names, reply = {}, ""
    async for message in query(prompt=question, options=OPTIONS):
        if isinstance(message, SystemMessage) and message.subtype == "init":
            print("coordinator tools:", ", ".join(message.data["tools"]))
        if isinstance(message, AssistantMessage):
            inside = message.parent_tool_use_id  # None: the coordinator
            for block in message.content:
                if isinstance(block, ToolUseBlock) and block.name == "Agent":
                    names[block.id] = block.input["subagent_type"]
                    print(f"\n-> {names[block.id]} gets only this prompt:")
                    show(block.input["prompt"])
                elif isinstance(block, ToolUseBlock):
                    who = names.get(inside, "coordinator")
                    print(f"   [{who}] {block.name.split('__')[-1]}",
                          block.input)
                elif isinstance(block, TextBlock) and inside is None:
                    reply = block.text
        elif isinstance(message, ResultMessage):
            print("\n" + reply)
            print(f"\nsubagents: {', '.join(names.values()) or 'none'} · "
                  f"{message.num_turns} turns · ${message.total_cost_usd:.4f}")


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    asyncio.run(main(sys.argv[1]))
