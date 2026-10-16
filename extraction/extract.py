"""Turn a supplier document into data: Claude fills in a tool whose input schema is the output we want.

python -m extraction.extract data/invoices/dev/INV-D01.txt
"""

import json
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from harborline.config import MAX_TOKENS, MODEL
from harborline.usage import log_usage

ITEM = {
    "type": "object",
    "properties": {
        "description": {"type": "string"},
        "quantity": {"type": "number"},
        "unit_price": {"type": "number"},
        "amount": {"type": "number"},
    },
    "required": ["description", "quantity", "unit_price", "amount"],
    "additionalProperties": False,
}


def record_tool(name, kind, number):
    """A strict tool for one kind of document: its input is the data we keep."""
    return {
        "name": name,
        "description": f"Record one supplier {kind}: who sent it, its number and date, its lines and its total.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "supplier_name": {"type": "string"},
                number: {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "currency": {"type": "string", "description": "ISO 4217 code, such as USD"},
                "line_items": {"type": "array", "items": ITEM},
                "stated_total": {"type": "number", "description": "The total the document states"},
            },
            "required": ["supplier_name", number, "date", "currency", "line_items", "stated_total"],
            "additionalProperties": False,
        },
    }


RECORD_INVOICE = record_tool("record_invoice", "invoice", "invoice_number")
RECORD_CREDIT_NOTE = record_tool("record_credit_note", "credit note", "credit_note_number")
EXTRACT_METADATA = {
    "name": "extract_metadata",
    "description": "Say what kind of document this is before any data is extracted from it.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "doc_type": {"type": "string", "enum": ["invoice", "credit_note", "other"]},
            "supplier_name": {"type": "string"},
        },
        "required": ["doc_type", "supplier_name"],
        "additionalProperties": False,
    },
}
RECORDERS = {"invoice": RECORD_INVOICE, "credit_note": RECORD_CREDIT_NOTE}


def call(client, text, tools, choice):
    """One request; returns the name and the input of the tool Claude called."""
    response = client.messages.create(
        model=MODEL, max_tokens=MAX_TOKENS, tools=tools, tool_choice=choice,
        messages=[{"role": "user", "content": f"<document>\n{text}\n</document>"}])
    log_usage(response, "extract")
    block = next(b for b in response.content if b.type == "tool_use")
    return block.name, block.input


def extract(client, path):
    text = Path(path).read_text()
    _, meta = call(client, text, [EXTRACT_METADATA], {"type": "tool", "name": "extract_metadata"})
    if meta["doc_type"] not in RECORDERS:
        return "skipped", meta
    tool = RECORDERS[meta["doc_type"]]
    return call(client, text, [tool], {"type": "tool", "name": tool["name"]})


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    name, data = extract(anthropic.Anthropic(), sys.argv[1])
    print(name, json.dumps(data, indent=2))
    if "line_items" in data:
        lines = round(sum(item["amount"] for item in data["line_items"]), 2)
        print(f"lines add up to {lines:,.2f}; stated total {data['stated_total']:,.2f}")
