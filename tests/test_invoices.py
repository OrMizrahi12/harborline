"""The invoice labels are internally consistent."""

from harborline import data


def test_line_items_add_up_to_the_subtotal():
    for label in data.invoice_labels():
        total = round(sum(item["amount"] for item in label["line_items"]), 2)
        assert total == label["subtotal"], label["doc_id"]
        for item in label["line_items"]:
            assert round(item["quantity"] * item["unit_price"], 2) == item["amount"]


def test_conflicts_are_flagged():
    for label in data.invoice_labels():
        calculated = round(label["subtotal"] + label["tax"] + label["shipping"], 2)
        assert calculated == label["calculated_total"]
        if label["stated_total"] is not None:
            assert label["conflict_detected"] == (label["stated_total"] != calculated), label["doc_id"]


def test_the_set_has_the_hard_cases():
    labels = data.invoice_labels()
    assert sum(1 for x in labels if x["split"] == "batch") == 100
    assert sum(1 for x in labels if x["conflict_detected"]) >= 8
    assert sum(1 for x in labels if x["stated_total"] is None) >= 2
    assert sum(1 for x in labels if x["oversized"]) == 2
    assert sum(1 for x in labels if x["po_number"] is None) >= 30
    assert {x["doc_type"] for x in labels} == {"invoice", "credit_note", "other"}
    assert {x["format"] for x in labels} == {"table", "prose", "email", "scan"}
