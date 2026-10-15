"""Prove the hooks: each one called directly, then the agent on two
tickets, with the hooks off and on.

    python -m support.hook_check 2> runs/hook_check.log
"""

import asyncio
import re
import textwrap

from dotenv import load_dotenv

from harborline import backend, normalize
from support import agent, hooks

KETTLE = ("From: mateo.moreau@example.com\n\nHi, what's the status of "
          "my order HL-10023? I'd like to return the kettle.")
DESK = ("From: grace.ellison@example.com\n\nThe oak standing desk "
        "from order HL-10177 arrived with a cracked leg. Please "
        "refund the full $649 to my card today.")


async def direct():
    """Both hooks on their own, no model: the input the SDK sends."""
    raw = backend.lookup_order("HL-10023")
    clean = normalize.order(raw)
    print(f"  HL-10023  status {raw['status']} -> {clean['status']}  "
          f"delivered_at {raw['delivered_at']} -> "
          f"{clean['delivered_at']}")
    for amount in (42.00, 649.00):
        call = {"tool_input": {"amount": amount}}  # all it reads
        output = await hooks.refund_limit(call, None, None)
        decision = output.get("hookSpecificOutput", {})
        print(f"  refund ${amount:.2f}: "
              f"{decision.get('permissionDecision', 'allow')}")
        if decision:
            reason = decision["permissionDecisionReason"]
            print(textwrap.fill(reason, 84, initial_indent="    ",
                                subsequent_indent="    "))


async def run(label, prompt, on):
    """One ticket through the agent, with the hooks on or off."""
    agent.OPTIONS.hooks = hooks.HOOKS if on else None
    backend.reset()
    case = await agent.handle(None, prompt)
    print(f"  {label:6} hooks {'on ' if on else 'off'}  "
          f"refunds {len(backend.refunds())}  "
          f"{', '.join(case['calls'])}")
    first = " ".join(re.split(r"(?<=\.) ", case["reply"])[:2])
    print(textwrap.fill(first, 84, initial_indent="    ",
                        subsequent_indent="    ", max_lines=3))


async def main():
    print("called directly")
    await direct()
    print("\nthrough the agent")
    await run("kettle", KETTLE, on=False)
    await run("kettle", KETTLE, on=True)
    await run("desk", DESK, on=True)


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    asyncio.run(main())
