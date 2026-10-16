"""Check an extracted record, and retry with the document, the failed output and the exact errors.

python -m extraction.validate data/invoices/dev/INV-D07.txt
"""

import json
import re
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from pydantic import ValidationError, field_validator, model_validator

from extraction import schema
from extraction.extract import EXTRACT_METADATA, RECORD_DOCUMENT, call

RETRY = """
Your last extraction of this document failed these checks:
{errors}
Your last extraction was:
{output}
Read the document again and extract it again. Fix what the checks found and keep the rest."""


class Checked(schema.Document):
    """The same record, plus checks that every correct extraction passes."""

    @field_validator("invoice_date", "due_date")
    @classmethod
    def iso_date(cls, value):
        if value is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("must be YYYY-MM-DD")
        return value

    @model_validator(mode="after")
    def lines_add_up(self):
        for n, item in enumerate(self.line_items, 1):
            if abs(item.quantity * item.unit_price - item.amount) > 0.01:
                raise ValueError(f"line {n}: quantity {item.quantity:g} x unit price {item.unit_price:g} is "
                                 f"{item.quantity * item.unit_price:.2f}, but the amount {item.amount:g} is "
                                 f"{item.amount / item.unit_price:g} x {item.unit_price:g}")
        return self


def problems(error):
    return "\n".join(f"- {'.'.join(map(str, e['loc'])) or 'record'}: {e['msg'].removeprefix('Value error, ')}"
                     for e in error.errors())


def totals(record):
    """calculated_total from the lines, tax and shipping; a conflict when the stated total disagrees."""
    lines = sum(item["amount"] for item in record["line_items"])
    calculated = round(lines + (record["tax"] or 0) + (record["shipping"] or 0), 2)
    stated = record["stated_total"]
    return calculated, stated is not None and abs(calculated - stated) > 0.01


def finish(record):
    """A record that passed the checks, with its totals and where it goes next."""
    calculated, conflict = totals(record)
    if record["stated_total"] is None:  # not in the document: no retry can find it
        status = "review: the document states no total"
    else:
        status = "review: the document's total disagrees" if conflict else "ok"
    return record | {"calculated_total": calculated, "conflict_detected": conflict, "status": status}


def extract_checked(client, path, tries=3):
    text = Path(path).read_text()
    meta = call(client, text, EXTRACT_METADATA)
    if meta["doc_type"] not in ("invoice", "credit_note"):
        return meta | {"status": "skipped"}
    note = ""
    for attempt in range(1, tries + 1):
        record = call(client, text, RECORD_DOCUMENT, note)
        try:
            Checked.model_validate(record)
        except ValidationError as error:  # a format or reading mistake: worth a retry
            print(f"attempt {attempt}: failed\n{problems(error)}")
            note = RETRY.format(errors=problems(error), output=json.dumps(record))
            continue
        print(f"attempt {attempt}: passed")
        return meta | finish(record)
    return meta | record | {"status": f"review: still failing after {tries} attempts"}


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    result = extract_checked(anthropic.Anthropic(), sys.argv[1])
    for item in result.get("line_items", []):
        print(f"  {item['quantity']:g} {item['unit']} {item['description']} @ {item['unit_price']:g} = {item['amount']:g}")
    keys = ("invoice_number", "stated_total", "calculated_total", "conflict_detected", "status")
    print(json.dumps({key: result.get(key) for key in keys}, indent=2))
