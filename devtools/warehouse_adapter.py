"""Turn a legacy warehouse record into the order shape harborline.normalize.order() returns.

load_record() reads the legacy record (Unix seconds, numeric status codes);
order() then makes the dates UTC ISO 8601 and the status a name.
"""

from harborline.normalize import order
from legacy.warehouse import load_record


def to_order(raw):
    """A legacy warehouse record -> the order dict harborline.normalize.order() returns."""
    return order(load_record(raw))
