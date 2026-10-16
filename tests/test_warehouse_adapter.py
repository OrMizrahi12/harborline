"""A legacy warehouse record comes out in the same shape as a web order."""

from devtools.warehouse_adapter import to_order


def test_epoch_dates_and_status_code_become_utc_and_a_name():
    raw = {
        "order_id": "HL-20001",
        "placed_at": 1767225600,      # 2026-01-01T00:00:00Z
        "delivered_at": 1767268800,   # 2026-01-01T12:00:00Z
        "promised_by": 1767225600,
        "status": 3,
    }
    result = to_order(raw)
    assert result["order_id"] == "HL-20001"
    assert result["placed_at"] == "2026-01-01T00:00:00Z"
    assert result["delivered_at"] == "2026-01-01T12:00:00Z"
    assert result["promised_by"] == "2026-01-01T00:00:00Z"
    assert result["status"] == "shipped"


def test_missing_dates_stay_none_unknown_codes_say_unknown_and_input_is_untouched():
    raw = {
        "order_id": "HL-20002",
        "placed_at": 0,               # 1970-01-01T00:00:00Z
        "delivered_at": None,
        "promised_by": None,
        "status": 42,
    }
    snapshot = dict(raw)
    result = to_order(raw)
    assert result["placed_at"] == "1970-01-01T00:00:00Z"
    assert result["delivered_at"] is None
    assert result["promised_by"] is None
    assert result["status"] == "unknown"
    assert raw == snapshot
