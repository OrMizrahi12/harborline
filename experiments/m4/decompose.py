"""Two ways to split work: a fixed chain, and a plan that adapts.

    python -m experiments.m4.decompose chain
    python -m experiments.m4.decompose explore

chain: a review of legacy/warehouse in fixed steps, one pass per file and
then one pass across the files. explore: an open-ended task; the agent maps
the package first and decides each next step from what it found.
"""

import asyncio
import sys

import anthropic
from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions,
                              ResultMessage, TextBlock, ToolUseBlock, query)
from dotenv import load_dotenv

from harborline.config import MODEL, ROOT_DIR
from harborline.costs import estimate_cost

PACKAGE = ROOT_DIR / "legacy" / "warehouse"
ROOM = 4096  # one reply: thinking plus the answer
FILE_PASS = (
    "You review one Python file on its own. List at most three problems "
    "in it, one line each, starting with the line number. If there are "
    "none, say so.")
CROSS_PASS = (
    "You review how the files of one package work together. You get the "
    "files and the notes from a review of each file alone. List at most "
    "four problems that only show across files, such as one function "
    "under two names or two files that disagree. One line each, naming "
    "the files. Don't repeat the per-file notes.")
TASK = (
    "Open-ended task: plan unit tests for legacy/warehouse, most important "
    "first. Nobody has mapped this package for you. Start by mapping it: "
    "its files, their public names, and what imports them across the "
    "project. Then decide what matters most and look closer there. When "
    "something you find changes the plan, say so and change it. Before "
    "each step, say in one line what you'll do next and why. Don't change "
    "any files. End with the plan: at most eight lines, most important "
    "first.")


def ask(client, system, text, costs):
    reply = client.messages.create(
        model=MODEL, max_tokens=ROOM, system=system,
        messages=[{"role": "user", "content": text}])
    costs.append(estimate_cost(reply.model, reply.usage.input_tokens,
                               reply.usage.output_tokens))
    return "".join(b.text for b in reply.content if b.type == "text").strip()


def chain():
    """Fixed steps, known before the run: each file, then across files."""
    client = anthropic.Anthropic()
    files = sorted(PACKAGE.glob("*.py"))
    costs, notes = [], []
    for path in files:  # step 1: one pass per file
        name = path.relative_to(ROOT_DIR)
        note = ask(client, FILE_PASS, f"{name}\n\n{path.read_text()}", costs)
        notes.append(f"{name}\n{note}")
        print(f"--- {name}\n{note}\n")
    code = "\n\n".join(f"{p.relative_to(ROOT_DIR)}\n{p.read_text()}"
                       for p in files)
    cross = ask(client, CROSS_PASS,  # step 2: one pass across the files
                code + "\n\nNotes per file:\n\n" + "\n\n".join(notes), costs)
    print(f"--- across the files\n{cross}\n")
    print(f"{len(costs)} calls, fixed before the run · ${sum(costs):.4f}")


async def explore():
    """Open-ended: the agent maps first, then picks each next step."""
    options = ClaudeAgentOptions(
        model=MODEL,
        tools=["Read", "Grep", "Glob"],  # it can look, not change
        allowed_tools=["Read", "Grep", "Glob"],
        permission_mode="dontAsk",
        setting_sources=[],
        cwd=ROOT_DIR,
        max_turns=25,
        max_budget_usd=0.10,
    )
    steps = 0
    async for message in query(prompt=TASK, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    steps += 1
                    args = " ".join(str(v) for v in block.input.values())
                    args = args.replace(f"{ROOT_DIR}/", "").replace(
                        str(ROOT_DIR), ".")  # paths from the project
                    print(f"  {steps:2}. {block.name} {args}")
                elif isinstance(block, TextBlock):
                    print(block.text.strip())
        elif isinstance(message, ResultMessage):
            print(f"\n{steps} tool calls, chosen during the run · "
                  f"{message.num_turns} turns · ${message.total_cost_usd:.4f}")


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    if sys.argv[1] == "chain":
        chain()
    else:
        asyncio.run(explore())
