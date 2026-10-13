"""Read Harborline's synthetic data from the data/ folder.

Every function returns plain Python lists, dicts and strings.
"""

import json

from harborline.config import DATA_DIR


def _read_json(relative_path):
    return json.loads((DATA_DIR / relative_path).read_text(encoding="utf-8"))


def _read_jsonl(relative_path):
    lines = (DATA_DIR / relative_path).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def customers():
    return _read_json("customers.json")


def products():
    return _read_json("products.json")


def orders():
    return _read_json("orders.json")


def faults():
    """Simulated outages used by the error-handling lessons."""
    return _read_json("faults.json")


def refund_policy():
    return (DATA_DIR / "refund_policy.md").read_text(encoding="utf-8")


def tickets():
    """The labeled support tickets (for measuring first-contact resolution)."""
    return _read_jsonl("tickets/labeled_tickets.jsonl")


def tool_routing_cases():
    """Requests labeled with the tool that should handle them."""
    return _read_jsonl("evals/tool_routing.jsonl")


def invoice_labels():
    """The correct extraction for every supplier invoice."""
    return _read_jsonl("invoices/labels.jsonl")


def invoice_text(doc_id):
    """The raw text of one invoice, e.g. invoice_text("INV-0001")."""
    for label in invoice_labels():
        if label["doc_id"] == doc_id:
            return (DATA_DIR / label["path"]).read_text(encoding="utf-8")
    raise KeyError(doc_id)


def research_sources():
    """Metadata for every research source (title, publisher, date, URL)."""
    return _read_json("research/sources.json")


def research_document(source_id):
    """The full text of one research source, e.g. research_document("S01")."""
    for source in research_sources():
        if source["id"] == source_id:
            return (DATA_DIR / source["path"]).read_text(encoding="utf-8")
    raise KeyError(source_id)
