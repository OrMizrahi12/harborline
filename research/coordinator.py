"""Harborline's research coordinator: a hub with three subagents.

The coordinator gets a goal and what a good answer looks like, splits
the work so no two subagents cover the same ground, starts independent
subagents together, and checks the answer against the goal. Each line
it prints starts with the seconds since the run began; a "!" marks a tool
call that failed.

    python -m research.coordinator "Should Harborline charge for return shipping?"
    python -m research.coordinator --resume <run_id>

Each subagent's report is saved as it arrives (research/state.py), so a run
that crashes resumes from its manifest instead of redoing that work.
"""

import asyncio
import json
import os
import sys
import time

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions,
                              HookMatcher, ResultMessage, TextBlock,
                              ToolUseBlock, UserMessage, query)
from dotenv import load_dotenv

from harborline.config import MODEL
from research import state
from research.agents import AGENTS
from research.provenance import check, parse, render
from research.tools import FOUND, server

RESEARCH_TOOLS = ["mcp__research__search_web", "mcp__research__load_document",
                  "mcp__research__verify_fact"]


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
        "findings and checks their figures. If it says a source is "
        "missing, send a searcher for that only. Subagents know only what "
        "you write in their prompt.\n"
        "Goal: an answer Harborline's managers can act on. A good answer "
        "covers the cost of returns, how customers react to a fee, what "
        "competitors do, and Harborline's own data; keeps every claim "
        "with its source; and shows where sources disagree.\n"
        "Split the work so no two subagents cover the same ground, for "
        "example by part of the goal or by source type (web pages, "
        "Harborline's documents). Subagents that don't depend on each "
        "other start together, in one response. If a subagent reports a "
        "search it couldn't complete, carry on with the rest and tell the "
        "synthesizer which part isn't covered, so the answer says so.\n"
        "Before you answer, check the synthesizer's answer against the "
        "goal. If a part is missing, send a subagent for that gap only, "
        "then have the synthesizer write again with all the findings. "
        "Give it the findings with relevance 0.5 or more, whole, as JSON. "
        "Reply with the synthesizer's "
        "JSON report only, unchanged, with nothing before or after it."),
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


def text_of(content):
    """A result's text, whether it came as one string or in parts."""
    return content if isinstance(content, str) else " ".join(
        part.get("text", "") for part in content or [])


def failure(content):
    """A failed tool's failure_type, or the start of its message."""
    text = text_of(content)
    try:
        return json.loads(text)["failure_type"]
    except (ValueError, KeyError, TypeError):
        return text[:60]


async def main(run_id):
    names, started, counts, spans, reply = {}, {}, {}, [], ""
    calls, prompts = {}, {}  # each tool call: who made it; each brief
    prompt, earlier = state.manifest(run_id)["question"], state.done(run_id)
    failures = state.manifest(run_id).get("failures", [])  # kept on resume
    for report in earlier:  # number new subagents after the saved ones
        kind, number = report["name"].rsplit(" ", 1)
        counts[kind] = max(counts.get(kind, 0), int(number))
    if earlier:
        print(f"resuming {run_id}: {len(earlier)} reports already saved")
        FOUND.update(state.manifest(run_id)["found"])  # what searches found
        prompt += ("\n\nThis run is resuming after a crash. These subagents "
                   "already reported. Use their reports, and don't repeat "
                   "their work:\n" + json.dumps(earlier))
    else:
        print(f"run {run_id}")
    crash_after = int(os.environ.get("CRASH_AFTER", 0))  # 0: no crash
    start = time.monotonic()
    async for message in query(prompt=prompt, options=OPTIONS):
        now = time.monotonic() - start
        if isinstance(message, AssistantMessage):
            inside = message.parent_tool_use_id  # None: the coordinator
            for block in message.content:
                if isinstance(block, ToolUseBlock) and block.name == "Agent":
                    kind = block.input["subagent_type"]
                    counts[kind] = counts.get(kind, 0) + 1
                    names[block.id] = f"{kind} {counts[kind]}"
                    started[block.id] = now
                    prompts[block.id] = block.input["prompt"]
                    print(f"{now:5.1f}s -> {names[block.id]}: "
                          f"{block.input['prompt'][:60]}...")
                elif isinstance(block, ToolUseBlock):
                    tool = block.name.split("__")[-1]
                    who = names.get(inside, "coordinator, denied")  # the hook
                    calls[block.id] = f"[{who}] {tool}"
                    print(f"{now:5.1f}s    {calls[block.id]}",
                          *block.input.values())
                elif isinstance(block, TextBlock) and inside is None:
                    reply = block.text  # the last one is the answer
        elif isinstance(message, UserMessage) and isinstance(message.content,
                                                             list):
            for block in message.content:  # a tool's or a subagent's result
                done = getattr(block, "tool_use_id", None)
                if getattr(block, "is_error", False) and done in calls:
                    failures.append(
                        f"{calls[done]} failed: {failure(block.content)}")
                    print(f"{now:5.1f}s  ! {failures[-1]}")
                if done in started:
                    spans.append((started[done], now))
                    print(f"{now:5.1f}s <- {names[done]} done "
                          f"({now - started[done]:.1f}s)")
                    state.save(run_id, names[done], prompts[done],
                               text_of(block.content), found=sorted(FOUND),
                               failures=failures)
                    if len(state.done(run_id)) == crash_after:
                        print(f"{now:5.1f}s simulated crash")
                        raise SystemExit(1)
        elif isinstance(message, ResultMessage):
            try:
                report = parse(reply)
            except ValueError:  # not JSON: show it as it came
                print("\n" + reply)
            else:
                print("\n" + render(report))
                print("\nprovenance:", "; ".join(check(report)) or "ok")
                state.finish(run_id, report)
                print(f"saved research/runs/{run_id}/report.json")
            print(f"\nsubagents: {', '.join(names.values()) or 'none'}")
            work, clock = sum(b - a for a, b in spans), covered(spans)
            print(f"subagents worked {work:.0f}s in {clock:.0f}s of clock "
                  f"time: running together saved {work - clock:.0f}s")
            print(f"{now:.0f}s in all · {message.num_turns} turns · "
                  f"${message.total_cost_usd:.4f}")


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    if sys.argv[1] == "--resume":
        asyncio.run(main(sys.argv[2]))
    else:
        asyncio.run(main(state.start(sys.argv[1])))
