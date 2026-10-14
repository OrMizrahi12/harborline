"""Log what each API call used and cost: one JSON line per call.

From Lesson 1.2 on, every response goes through log_usage().
The log is runs/usage.jsonl (runs/ is in .gitignore).
"""

import json
from datetime import datetime, timezone

from harborline.config import ROOT_DIR
from harborline.costs import estimate_cost

USAGE_LOG = ROOT_DIR / "runs" / "usage.jsonl"


def log_usage(response, label):
    """Append one response's usage to the log, and return the record."""
    usage = response.usage
    details = usage.output_tokens_details
    record = {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "label": label,
        "request_id": response._request_id,
        "model": response.model,
        "stop_reason": response.stop_reason,
        "input_tokens": usage.input_tokens,
        "cache_read_tokens": usage.cache_read_input_tokens or 0,
        "cache_write_tokens": usage.cache_creation_input_tokens or 0,
        "output_tokens": usage.output_tokens,
        "thinking_tokens": details.thinking_tokens if details else 0,
    }
    # Prices come from costs.py (no cache writes yet: Module 1 never writes a cache).
    cost = estimate_cost(response.model, usage.input_tokens,
                         usage.output_tokens, record["cache_read_tokens"])
    record["cost_usd"] = round(cost, 8)
    USAGE_LOG.parent.mkdir(exist_ok=True)
    with USAGE_LOG.open("a", encoding="utf-8") as log:
        log.write(json.dumps(record) + "\n")
    return record
