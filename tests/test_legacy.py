"""The old warehouse code still works the way it always did."""

import legacy.warehouse as warehouse
from legacy.warehouse import codes, shipping


def test_status_codes_have_names():
    assert codes.status_name(3) == "shipped"
    assert codes.status_name(4) == "delivered"
    assert codes.status_name(42) == "unknown"
    assert codes.status_name(9).upper() == "CANCELLED"


def test_reading_a_legacy_record():
    raw = {"order_id": "HL-10001", "placed_at": 1751464800, "status": 4, "delivered_at": None}
    record = warehouse.load_record(raw)
    assert record["placed_at"].startswith("2025-07-02")
    assert record["status"] == "delivered"
    assert raw["status"] == 4  # the original is not changed


def test_free_shipping_starts_at_75_dollars():
    assert warehouse.shipping_quote(80.00) == 0.0
    assert shipping.quote(75.00) == 0.0  # $75.00 exactly ships free
    assert shipping.quote(74.99) == 6.95
    assert shipping.quote(80.00, zone="canada") == 14.50
