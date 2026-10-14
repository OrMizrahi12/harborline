"""6 tools or 18: does Claude still pick the right one? 3 tries each.

    python -m experiments.m2.tool_count
"""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import anthropic
from dotenv import load_dotenv

from experiments.m2.routing_eval import HELD_OUT, TRIES, correct, decide
from harborline import data
from loop.tools import TOOLS

# Twelve more tools a support team might add. Short descriptions keep
# this file small. None of them ever runs: decide() only runs lookups.
EXTRA = [  # (name, what it does, its inputs)
    ("cancel_order", "Cancel an order that has not shipped yet.",
     "order_id"),
    ("update_address", "Change the delivery address of an order that "
     "has not shipped.", "order_id address"),
    ("update_email", "Change the email address on the customer's "
     "account.", "customer_id email"),
    ("update_phone", "Change the phone number on the customer's "
     "account.", "customer_id phone"),
    ("reset_password", "Email the customer a link to reset their "
     "password.", "customer_id"),
    ("create_return_label", "Create a prepaid label for sending an "
     "item back.", "order_id sku"),
    ("issue_store_credit", "Give store credit as a goodwill gesture. "
     "It is not a refund.", "customer_id amount"),
    ("apply_coupon", "Apply a discount code to an order that has not "
     "shipped.", "order_id code"),
    ("get_product", "Get a product by SKU: name, price, category and "
     "whether it is final sale.", "sku"),
    ("estimate_delivery", "Estimate when a product would arrive at a "
     "postal code, before it is bought.", "sku postal_code"),
    ("add_case_note", "Add an internal note to the customer's support "
     "case.", "customer_id note"),
    ("get_loyalty_points", "Get the customer's loyalty points "
     "balance.", "customer_id"),
]
MORE = TOOLS + [{"name": name, "description": text, "input_schema": {
    "type": "object", "required": fields.split(),
    "properties": {field: {"type": "string"} for field in fields.split()},
}} for name, text, fields in EXTRA]


def show(label, values):
    print(f"{label:13}" + "".join(f"{value:>11}" for value in values))


if __name__ == "__main__":
    load_dotenv()
    client = anthropic.Anthropic()
    pool = ThreadPoolExecutor(2 * TRIES)  # both sets side by side
    labeled = [(c["id"], "C-1046", c["request"], c["expected_tool"], {})
               for c in data.tool_routing_cases()]
    cases, extras = labeled + HELD_OUT, [e[0] for e in EXTRA]
    totals = [Counter(), Counter()]  # one per tool set
    for n, (case_id, customer, request, want, needs) in enumerate(cases):
        jobs = [[pool.submit(decide, client, customer, request, want,
                             f"{len(tools)} tools", tools)
                 for _ in range(TRIES)] for tools in (TOOLS, MORE)]
        scores, missed = [], ""
        for total, column in zip(totals, jobs):
            right = 0
            for got, given, records in (job.result() for job in column):
                total["calls"] += len(records)
                total["tokens"] += sum(r["input_tokens"] for r in records)
                total["cost"] += sum(r["cost_usd"] for r in records)
                total["extra"] += got in extras
                total["text"] += got.startswith("(")
                if correct(got, given, want, needs, customer):
                    right += 1
                else:
                    missed = got
            total[case_id[0]] += right  # R: labeled, H: held-out
            scores.append(f"{right}/{TRIES}")
        if scores[0] != scores[1]:
            print(f"\r{case_id:4} {want:17}  {'  '.join(scores)}  "
                  + missed[:20])
        print(f"\r{n + 1}/{len(cases)} requests", end="", flush=True)

    print("\n")
    r, h = TRIES * len(labeled), TRIES * len(HELD_OUT)  # 48 and 24
    show("", ["6 tools", "18 tools"])
    show("labeled", [f"{t['R']}/{r}" for t in totals])
    show("held-out", [f"{t['H']}/{h}" for t in totals])
    show("extra picked", [t["extra"] for t in totals])
    show("text replies", [t["text"] for t in totals])
    show("in per call", [f"{t['tokens'] // t['calls']:,}"
                         for t in totals])
    show("cost", [f"${t['cost']:.4f}" for t in totals])
