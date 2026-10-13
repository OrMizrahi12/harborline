"""Count the tokens in one or more files, and what sending them would cost.

Counting tokens is a separate API endpoint: it needs your API key, and it
does not run the model.

Run it from the repository folder:
    python -m scripts.count_tokens data/refund_policy.md data/orders.json
"""

import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from harborline.config import MODEL
from harborline.costs import PRICES, estimate_cost


def count_tokens(client, text):
    result = client.messages.count_tokens(
        model=MODEL,
        messages=[{"role": "user", "content": text}],
    )
    return result.input_tokens


def main(paths):
    if not paths:
        print(__doc__)
        return 1

    load_dotenv()  # reads ANTHROPIC_API_KEY from .env
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("No API key found. Copy .env.example to .env and add your key.")
        return 1
    client = anthropic.Anthropic()

    print(f"Tokens counted for {MODEL}. Cost = sending the file once as input.")
    for path in paths:
        text = Path(path).read_text(encoding="utf-8")
        tokens = count_tokens(client, text)
        print(f"\n{path}: {len(text):,} characters, {tokens:,} tokens")
        for model in PRICES:
            normal = estimate_cost(model, tokens)
            batch = estimate_cost(model, tokens, batch=True)
            print(f"  {model:<18} ${normal:.5f}   (batch ${batch:.5f})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
