"""Measure the support agent on the labeled dev tickets.

FCR (first-contact resolution): solved with no person involved and
exactly the refunds the label expects. Escalation recall: of the
tickets that need a person, how many got one. Wrong refunds: money
paid that the label doesn't expect.

    python -m support.evaluate
"""

import asyncio

from dotenv import load_dotenv

from harborline import backend, data
from support.agent import handle


def grade(label, refunds, escalations):
    """The ticket's verdict, and how many refunds were wrong."""
    paid = sorted((r["order_id"], r["amount"]) for r in refunds)
    expected = sorted((r["order_id"], r["amount"])
                      for r in label["expected_refunds"])
    wrong = len([p for p in paid if p not in expected])
    if label["outcome"] == "escalate":
        verdict = "escalated" if escalations else "missed escalation"
    elif escalations:
        verdict = "escalated, could resolve"
    elif paid != expected:
        verdict = "wrong refund" if wrong else "refund missing"
    else:
        verdict = "resolved"
    return verdict, wrong


async def main():
    tickets = [t for t in data.tickets() if t["split"] == "dev"]
    resolved = escalated = needed = wrong = 0
    cost = 0.0
    for ticket in tickets:
        backend.reset()  # empty refund and escalation ledgers
        case = await handle(ticket["ticket_id"])
        label, result = ticket["label"], case["result"]
        verdict, bad = grade(label, backend.refunds(),
                             backend.escalations())
        resolved += verdict == "resolved"
        needed += label["outcome"] == "escalate"
        escalated += verdict == "escalated"
        wrong += bad
        cost += result.total_cost_usd
        print(f"{ticket['ticket_id']}  {verdict:25} "
              f"{result.num_turns:2} turns  ${result.total_cost_usd:.4f}  "
              f"{', '.join(case['calls'])}")
    print(f"\nFCR {resolved}/{len(tickets)} ({resolved / len(tickets):.0%}) "
          f"· escalation recall {escalated}/{needed} "
          f"· wrong refunds {wrong} · ${cost:.4f}")


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    asyncio.run(main())
