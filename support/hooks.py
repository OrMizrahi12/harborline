"""Hooks: rules that run on every tool call, whatever Claude decides.

A PreToolUse hook sees a call before it runs, and can deny it.
A PostToolUse hook sees the result before Claude does, and can
replace it.
"""

import json

from claude_agent_sdk import HookMatcher

from harborline import normalize
from support import case_facts

REFUND_LIMIT = 500.00  # above this, a support lead approves


async def refund_limit(input_data, tool_use_id, context):
    """Deny a refund above the limit, and send Claude to a person."""
    amount = float(input_data["tool_input"].get("amount", 0))
    if amount <= REFUND_LIMIT:
        return {}
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"Refunds above ${REFUND_LIMIT:.0f} need a support lead. "
            "Call escalate_to_human instead; don't retry."),
    }}


async def normalize_order(input_data, tool_use_id, context):
    """Give Claude one format, and only the fields that matter."""
    try:
        record = json.loads(input_data["tool_response"][0]["text"])
    except (KeyError, IndexError, TypeError, ValueError):
        return {}  # not the JSON we expect: leave it as it is
    if "order_id" not in record:
        return {}  # an error, not an order
    clean = case_facts.trim(normalize.order(record))
    return {"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "updatedToolOutput": [{"type": "text",
                               "text": json.dumps(clean)}],
    }}


HOOKS = {
    "PreToolUse": [HookMatcher(
        matcher="mcp__harborline__process_refund",
        hooks=[refund_limit])],
    "PostToolUse": [HookMatcher(
        matcher="mcp__harborline__lookup_order",
        hooks=[normalize_order]),
        HookMatcher(matcher="mcp__harborline__.*",
                    hooks=[case_facts.record])],
}
