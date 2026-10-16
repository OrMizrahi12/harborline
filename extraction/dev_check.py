"""Run the 12 dev documents through extract_checked() and compare them with labels.jsonl.

python -m extraction.dev_check
"""

import contextlib
import io
import json

import anthropic
from dotenv import load_dotenv

from extraction.validate import extract_checked
from harborline.config import DATA_DIR

FIELDS = ("doc_type", "invoice_number", "invoice_date", "due_date", "po_number", "currency", "tax", "shipping",
          "stated_total")


def same(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) < 0.005
    return a == b


def differences(result, label):
    wrong = [f"{field} {result[field]!r} (label {label[field]!r})" for field in FIELDS
             if field in result and not same(result[field], label[field])]
    for n, (got, want) in enumerate(zip(result.get("line_items", []), label["line_items"]), 1):
        wrong += [f"line {n} {key} {got[key]!r} (label {want[key]!r})" for key in ("quantity", "unit")
                  if not same(got[key], want[key])]
    return wrong


def main():
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    client = anthropic.Anthropic()
    labels = [json.loads(line) for line in (DATA_DIR / "invoices" / "labels.jsonl").open()]
    exact = errors = 0
    for label in [label for label in labels if label["split"] == "dev"]:
        with contextlib.redirect_stdout(io.StringIO()):  # keep the attempt lines out of the table
            result = extract_checked(client, DATA_DIR / label["path"])
        wrong = differences(result, label)
        exact += not wrong
        errors += len(wrong)
        print(f"{label['doc_id']}  {label['format']:6} {'; '.join(wrong) or 'ok'}")
    print(f"{exact} of 12 documents exact; {errors} wrong values")


if __name__ == "__main__":
    main()
