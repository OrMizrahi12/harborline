"""Measure the support agent on the labeled tickets.

FCR (first-contact resolution): solved with no person involved and
exactly the refunds the label expects. Escalation recall: of the
tickets that need a person, how many got one. Wrong refunds: money
paid that the label doesn't expect.

A ticket can have follow-ups: the customer's answers to a question
(an email, an order number). Each one goes into the same session.

    python -m support.evaluate               # the 20 dev tickets
    python -m support.evaluate --split all   # all 50: dev and test
"""

import argparse
import asyncio

from dotenv import load_dotenv

from harborline import backend, data
from support.agent import handle

TARGET = {"fcr": 0.80, "recall": 1.0, "wrong": 0}  # Lab 3's bar


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


async def conversation(ticket):
    """The first message, then each follow-up in the same session."""
    case = await handle(ticket["ticket_id"])
    calls, cost = list(case["calls"]), case["result"].total_cost_usd
    for follow_up in ticket["follow_ups"]:
        session = case["result"].session_id
        case = await handle(ticket["ticket_id"], prompt=follow_up,
                            resume=session)
        calls += case["calls"]
        cost += case["result"].total_cost_usd
    return calls, cost


def totals(rows):
    """FCR, escalation recall and wrong refunds for some tickets."""
    needed = [r for r in rows if r["outcome"] == "escalate"]
    return {"tickets": len(rows),
            "resolved": sum(r["verdict"] == "resolved" for r in rows),
            "needed": len(needed),
            "escalated": sum(r["verdict"] == "escalated" for r in needed),
            "wrong": sum(r["wrong"] for r in rows),
            "cost": sum(r["cost"] for r in rows)}


def line(name, t):
    return (f"{name:5} FCR {t['resolved']}/{t['tickets']} "
            f"({t['resolved'] / t['tickets']:.0%}) "
            f"· escalation recall {t['escalated']}/{t['needed']} "
            f"· wrong refunds {t['wrong']} · ${t['cost']:.4f}")


def meets(t):
    """Does a run reach the target?"""
    return (t["resolved"] >= TARGET["fcr"] * t["tickets"]
            and t["escalated"] >= TARGET["recall"] * t["needed"]
            and t["wrong"] <= TARGET["wrong"])


async def main(split):
    tickets = [t for t in data.tickets()
               if split == "all" or t["split"] == split]
    rows = []
    for ticket in tickets:
        backend.reset()  # empty refund and escalation ledgers
        calls, cost = await conversation(ticket)
        label = ticket["label"]
        verdict, bad = grade(label, backend.refunds(),
                             backend.escalations())
        rows.append({"split": ticket["split"], "outcome": label["outcome"],
                     "verdict": verdict, "wrong": bad, "cost": cost})
        print(f"{ticket['ticket_id']}  {verdict:25} ${cost:.4f}  "
              f"{', '.join(calls)}")
    print()
    for name in ("dev", "test"):
        part = [r for r in rows if r["split"] == name]
        if part and split == "all":
            print(line(name, totals(part)))
    every = totals(rows)
    print(line(split, every))
    print("target: FCR 80% · escalation recall 100% · wrong refunds 0 ->",
          "PASS" if meets(every) else "FAIL")


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["dev", "test", "all"],
                        default="dev")
    asyncio.run(main(parser.parse_args().split))
