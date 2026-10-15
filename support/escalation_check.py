"""Escalation check: five dev tickets and the call the agent makes.

    python -m support.escalation_check 2> runs/escalation_check.log
"""

import asyncio
import re
import textwrap

from dotenv import load_dotenv

from harborline import backend
from support.agent import handle

TICKETS = {  # ticket -> the right call
    "T-005": "escalate",  # asks for a person
    "T-022": "escalate",  # asks for a real person
    "T-023": "escalate",  # a price drop: the policy is silent
    "T-017": "resolve",   # annoyed, but in scope
    "T-015": "ask",       # a name two customers share
}
ASKED_FOR_PERSON = ("T-005", "T-022")


def outcome(calls):
    """What the agent did: handed over, solved, or asked first."""
    if backend.escalations():
        return "escalate"
    if "lookup_order" in calls or backend.refunds():
        return "resolve"
    return "ask"


async def main():
    right = at_once = 0
    for ticket_id, want in TICKETS.items():
        backend.reset()  # empty refund and escalation ledgers
        case = await handle(ticket_id)
        calls = case["calls"]
        got = outcome(calls)
        right += got == want
        looked_first = ("lookup_order" in calls and "escalate_to_human"
                        in calls and calls.index("lookup_order")
                        < calls.index("escalate_to_human"))
        if ticket_id in ASKED_FOR_PERSON and got == "escalate":
            at_once += not looked_first
        print(f"{ticket_id}  want {want:8}  got {got:8}  "
              f"{', '.join(calls)}")
        first = " ".join(re.split(r"(?<=\.) ", case["reply"])[:2])
        print(textwrap.fill(first, 84, initial_indent="  ",
                            subsequent_indent="  ", max_lines=2))
    print(f"\nright call {right}/{len(TICKETS)} · asked for a person, "
          f"handed over at once {at_once}/{len(ASKED_FOR_PERSON)}")


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    asyncio.run(main())
