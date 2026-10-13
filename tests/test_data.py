"""The synthetic data is complete and consistent."""

import re

from harborline import data


def test_counts():
    assert len(data.customers()) == 60
    assert len(data.products()) == 40
    assert len(data.orders()) > 200
    assert len(data.tickets()) == 50
    assert len(data.invoice_labels()) == 112
    assert len(data.research_sources()) == 14


def test_ids_are_unique():
    for rows, key in [(data.customers(), "customer_id"), (data.orders(), "order_id"),
                      (data.tickets(), "ticket_id"), (data.invoice_labels(), "doc_id")]:
        ids = [row[key] for row in rows]
        assert len(ids) == len(set(ids)), key


def test_every_order_belongs_to_a_customer():
    customer_ids = {c["customer_id"] for c in data.customers()}
    skus = {p["sku"] for p in data.products()}
    for order in data.orders():
        assert order["customer_id"] in customer_ids
        assert all(item["sku"] in skus for item in order["items"])


def test_order_totals_add_up():
    for order in data.orders():
        subtotal = sum(i["unit_price"] * i["quantity"] for i in order["items"])
        assert round(subtotal + order["shipping_fee"], 2) == order["total"], order["order_id"]


def test_people_are_fictional():
    for customer in data.customers():
        assert customer["email"].endswith(("@example.com", "@example.net"))
        assert re.fullmatch(r"\+1-555-01\d\d", customer["phone"])


def test_every_invoice_file_exists():
    for label in data.invoice_labels():
        assert data.invoice_text(label["doc_id"]).strip()


def test_every_research_source_exists():
    for source in data.research_sources():
        text = data.research_document(source["id"])
        assert source["title"] in text
