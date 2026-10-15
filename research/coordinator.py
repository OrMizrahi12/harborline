"""Harborline's research coordinator: a hub with two subagents.

The coordinator picks the subagents a question needs, briefs them and
writes the answer. The subagents search and read, each in a fresh
context: all they get from the coordinator is the prompt it writes.

    python -m research.coordinator "Should Harborline charge for return shipping?"
"""

import asyncio
import sys
import textwrap

from claude_agent_sdk import (AgentDefinition, AssistantMessage,
                              ClaudeAgentOptions, HookMatcher,
                              ResultMessage, TextBlock, ToolUseBlock, query)
from dotenv import load_dotenv

from harborline.config import MODEL
from research.tools import server

SEARCHER = AgentDefinition(
    description="Finds sources on the web for one research question. "
                "Returns the URLs worth reading, with publisher and date.",
    prompt="You search the web with search_web. Return a short list of "
           "the most relevant sources: URL, publisher, date, and one line "
           "on what each covers. Don't read the pages.",
    tools=["mcp__research__search_web"],
    model="haiku",
)
ANALYST = AgentDefinition(
    description="Reads web pages and extracts the facts that answer a "
                "question, with the page each fact came from.",
    prompt="You read pages with fetch_url and extract the facts that "
           "answer the question. One line per fact, with its URL. Use "
           "only what the pages say.",
    tools=["mcp__research__fetch_url"],
    model="haiku",
)
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
        "store. You don't search or read yourself. You have two "
        "subagents: searcher finds sources, analyst reads them. Use only "
        "the ones the question needs. They know only what you write in "
        "their prompt: include the question and every URL or fact they "
        "need. Use only what they report, never your own knowledge. "
        "Answer in at most eight lines, citing URLs."),
    model=MODEL,
    agents={"searcher": SEARCHER, "analyst": ANALYST},
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


def show(prompt):
    for line in prompt.splitlines():
        print(textwrap.fill(line, 78, initial_indent="   ",
                            subsequent_indent="   "))


async def main(question):
    names, reply = {}, ""
    async for message in query(prompt=question, options=OPTIONS):
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
