"""Marketplace partner dates: US month/day, Eastern time, optional time."""

import pytest

from harborline import normalize


def test_partner_datetime_in_daylight_time_becomes_utc():
    assert normalize.to_utc("10/08/2026 2:30 PM ET") == "2026-10-08T18:30:00Z"


def test_partner_datetime_in_standard_time_becomes_utc():
    assert normalize.to_utc("01/02/2026 9:05 AM ET") == "2026-01-02T14:05:00Z"


def test_partner_midnight_in_daylight_time_becomes_utc():
    assert normalize.to_utc("10/08/2026 12:00 AM ET") == "2026-10-08T04:00:00Z"


def test_partner_date_without_time_stays_a_plain_date():
    assert normalize.to_utc("10/08/2026") == "2026-10-08"


def test_partner_day_is_never_read_as_month():
    # 13 cannot be a month, so this only works if the first number is the month.
    assert normalize.to_utc("01/13/2026 12:00 AM ET") == "2026-01-13T05:00:00Z"


def test_partner_value_that_does_not_parse_raises_with_the_value():
    with pytest.raises(ValueError, match="13/45/2026 2:30 PM ET"):
        normalize.to_utc("13/45/2026 2:30 PM ET")


def test_order_converts_partner_dates_in_all_three_fields():
    record = {
        "placed_at": "10/08/2026 2:30 PM ET",
        "promised_by": "10/10/2026",
        "delivered_at": "01/02/2026 9:05 AM ET",
        "status": "delivered",
    }
    clean = normalize.order(record)
    assert clean["placed_at"] == "2026-10-08T18:30:00Z"
    assert clean["promised_by"] == "2026-10-10"
    assert clean["delivered_at"] == "2026-01-02T14:05:00Z"
