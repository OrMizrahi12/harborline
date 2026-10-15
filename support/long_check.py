"""Long check: does a long conversation keep its facts?

    python -m support.long_check 2> runs/long_check.log

Eight messages from one customer. Like any long chat, it can't keep
everything word for word: older exchanges are folded into a short
running summary, and only the last two stay as they were. The last
message asks for facts from the start of the conversation.
"""

import asyncio
import textwrap

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions,
                              TextBlock, ToolUseBlock, query)
from dotenv import load_dotenv

from harborline import backend
from harborline.config import MODEL
from support import case_facts, gates
from support.agent import OPTIONS

TURNS = [
    "Hi, Sofia Fairbanks here (sofia.fairbanks@example.com). The round "
    "wall mirror from order HL-10158 arrived cracked. Can I get a refund?",
    "Thanks. I also changed my mind about the weighted blanket from "
    "HL-10131. Can you refund that too?",
    "And the garden tool set from HL-10193 has a broken handle. "
    "A refund for that one as well, please.",
    "How long until the money is back on my card?",
    "Do you refund the shipping when I change my mind?",
    "Do orders over $75 ship free?",
    "If I'd paid with a gift card, how would refunds work?",
    "For my records: list every refund, with the amount, the order and "
    "the refund reference.",
]
SUMMARIZER = ClaudeAgentOptions(model=MODEL, tools=[], setting_sources=[],
                                max_turns=1)


async def ask(prompt, options):
    """One call: the tools Claude used, and its last text."""
    calls, text = [], ""
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    calls.append(block.name.split("__")[-1])
                elif isinstance(block, TextBlock):
                    text = block.text
    return calls, text


async def fold(summary, exchange):
    """Fold the oldest exchange into the running summary."""
    _, text = await ask(
        "Update this running summary of a support chat with the next "
        "exchange, in 25 words or fewer.\n\n"
        f"Summary: {summary or '(empty)'}\n\n{exchange}", SUMMARIZER)
    return text


async def main():
    backend.reset()
    gates.start_case()
    case_facts.start_case()
    summary, recent, replies = "", [], []
    for number, message in enumerate(TURNS, 1):
        prompt = (case_facts.block() + "\n\n"
                  f"## The conversation so far (summary)\n{summary or '-'}"
                  "\n\n## The last messages\n" + "\n\n".join(recent) +
                  f"\n\n## The customer's new message\n{message}")
        calls, reply = await ask(prompt, OPTIONS)
        replies.append(reply)
        recent.append(f"Customer: {message}\nYou: {reply}")
        if len(recent) > 2:
            summary = await fold(summary, recent.pop(0))
        print(f"{number}  {', '.join(calls) or '-'}")
    print("\n" + textwrap.fill(f"summary: {summary}", 84) + "\n")
    print(textwrap.fill(replies[-1], 84, initial_indent="> ",
                        subsequent_indent="  ", max_lines=4) + "\n")
    last = replies[-1].replace(".00", "")  # $129.00 and $129 count the same
    kept, facts = 0, 0
    for refund in backend.refunds():  # the truth: the backend's ledger
        words = (f"${refund['amount']:g}", refund["order_id"],
                 refund["refund_id"])
        found = [w for w in words if w in last]
        kept, facts = kept + len(found), facts + len(words)
        print(f"{'  '.join(words):30} {len(found)}/3 in the last reply")
    print(f"\nfacts kept {kept}/{facts}")


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    asyncio.run(main())
