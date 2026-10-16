from harborline import normalize


def test_unix_seconds_become_utc_iso_string():
    assert normalize.to_utc(1767225600) == "2026-01-01T00:00:00Z"


def test_unix_seconds_with_a_fraction_drop_the_fraction():
    assert normalize.to_utc(1767225600.9) == "2026-01-01T00:00:00Z"


def test_iso_datetime_with_offset_becomes_utc():
    assert normalize.to_utc("2026-10-08T10:30:00-04:00") == "2026-10-08T14:30:00Z"


def test_order_maps_numeric_status_code_to_its_name():
    clean = normalize.order({"status": 3})
    assert clean["status"] == "shipped"


def test_order_leaves_the_input_record_unchanged():
    record = {"placed_at": 1767225600, "status": 3}
    normalize.order(record)
    assert record == {"placed_at": 1767225600, "status": 3}
