"""Case check: several requests in one message, and hand-offs a person
can act on without the conversation.

    python -m support.case_check 2> runs/case_check.log
"""

import asyncio
import textwrap

from claude_agent_sdk import AssistantMessage, TextBlock, ToolUseBlock, query
from dotenv import load_dotenv

from harborline import backend
from loop.agent import first_message
from support import gates
from support.agent import OPTIONS

MULTI = {  # ticket -> its other order, and words that answer its question
    "T-004": ("HL-10203", ["5 business days"]),              # refund time
    "T-007": ("HL-10198", ["adrian.oyelaran@example.com"]),  # email on file
    "T-016": ("HL-10202", ["not refunded", "n't refunded",    # shipping
                           "don't refund"]),
}
HANDOFF = ("T-005", "T-022", "T-023")
FIELDS = ("customer_id", "order_id", "reason", "amount",
          "recommended_action")


async def run(ticket_id):
    """One ticket: the tools called in each turn, and the reply."""
    gates.start_case()
    turns, reply = {}, ""
    prompt = first_message(ticket_id)["content"]
    async for message in query(prompt=prompt, options=OPTIONS):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):  # one message, one turn
                    turns.setdefault(message.message_id, []).append(
                        block.name.split("__")[-1])
                elif isinstance(block, TextBlock):
                    reply = block.text
    return list(turns.values()), reply


async def main():
    answered = complete = 0
    for ticket_id, (other, answer) in MULTI.items():
        backend.reset()
        turns, reply = await run(ticket_id)
        got = [bool(backend.refunds()), other in reply,
               any(words in reply for words in answer)]
        answered += sum(got)
        print(f"{ticket_id}  answered {sum(got)}/3  "
              + " | ".join(" + ".join(turn) for turn in turns))
    for ticket_id in HANDOFF:
        backend.reset()
        await run(ticket_id)
        case = (backend.escalations() or [{}])[0]
        missing = [f for f in FIELDS if case.get(f) in (None, "")]
        complete += bool(case) and not missing
        print(f"{ticket_id}  hand-off  missing: {', '.join(missing) or '-'}")
        print(textwrap.fill(f"next: {case.get('recommended_action')}", 84,
                            initial_indent="  ", subsequent_indent="  ",
                            max_lines=2))
    print(f"\nrequests answered {answered}/{3 * len(MULTI)} · "
          f"hand-offs complete {complete}/{len(HANDOFF)}")


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    asyncio.run(main())
