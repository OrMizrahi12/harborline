"""Tool errors that say what kind of failure it was.

run_tool sends one of these back with is_error true, so Claude can
choose its next move: try again, fix the input, explain, or hand off.
"""

import json

from harborline.errors import BackendError


def tool_error(error: BackendError) -> str:
    """The content of the tool_result for one backend error, as JSON."""
    body = {
        "errorCategory": error.kind,  # transient, validation, ...
        "isRetryable": error.retryable,  # True only for transient
        "message": str(error),
    }
    if error.kind == "business":  # the policy said no: don't retry
        reason = str(error).removeprefix("Refund not allowed: ")
        body["retriable"] = False
        body["customerReason"] = reason[0].upper() + reason[1:]
    return json.dumps(body)
