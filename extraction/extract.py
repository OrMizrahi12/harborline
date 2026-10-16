"""Turn a supplier document into data: Claude fills in a tool whose input schema is the output we want.

python -m extraction.extract data/invoices/dev/INV-D01.txt
"""

import json
import sys
from pathlib import Path

import anthropic
from anthropic import transform_schema
from dotenv import load_dotenv

from extraction import schema
from harborline.config import MAX_TOKENS, MODEL
from harborline.usage import log_usage

RULES = """Rules for every field:
- If the document doesn't state a value, use null. Never compute, infer or guess one.
- Tax and shipping are 0 when the document shows none.
- Dates as YYYY-MM-DD. US suppliers write numeric dates month first: 08/21/2026 is 2026-08-21.
  All other suppliers write them day first: 21/08/2026 is 2026-08-21, and 05.09.2026 is 2026-09-05.
- Amounts as plain numbers: "1.234,56" and "1,234.56" are both 1234.56.
- Currency as its ISO 4217 code, such as USD, GBP, EUR or CAD.
"""


def tool(name, description, model):
    """A strict tool whose input is one of the records in schema.py."""
    return {"name": name, "description": description, "strict": True, "input_schema": transform_schema(model)}


EXTRACT_METADATA = tool("extract_metadata", "Say what kind of document this is before any data is extracted from it.",
                        schema.Metadata)
RECORD_DOCUMENT = tool("record_document", "Record one supplier invoice or credit note: who sent it, its numbers "
                       "and dates, its lines and its totals.", schema.Document)


def call(client, text, tool):
    """One forced call; returns the input Claude gave the tool."""
    response = client.messages.create(
        model=MODEL, max_tokens=MAX_TOKENS, tools=[tool], tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": f"{RULES}\n<document>\n{text}\n</document>"}])
    log_usage(response, "extract")
    return next(b for b in response.content if b.type == "tool_use").input


def extract(client, path):
    text = Path(path).read_text()
    meta = call(client, text, EXTRACT_METADATA)
    if meta["doc_type"] not in ("invoice", "credit_note"):
        return "skipped", meta
    return "record_document", meta | call(client, text, RECORD_DOCUMENT)


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    name, data = extract(anthropic.Anthropic(), sys.argv[1])
    print(name, json.dumps(data, indent=2))
