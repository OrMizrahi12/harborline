"""The hand-off: what a person needs to take over a case.

The person in the support-leads queue never sees the conversation,
so each field has to stand on its own.
"""

HANDOFF = {
    "description": (
        "Hand the case to a person in the support-leads queue; it "
        "returns an escalation ID. The person reads only this hand-off, "
        "never the conversation, so fill in every field."),
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string",
                            "description": "From get_customer, e.g. C-1035"},
            "order_id": {"type": "string",
                         "description": "The order, e.g. HL-10187, or none"},
            "root_cause": {"type": "string",
                           "description": "Why a person is needed"},
            "amount": {"type": "number",
                       "description": "The refund in question, or 0"},
            "recommended_action": {"type": "string",
                                   "description": "What to do next"},
            "summary": {"type": "string",
                        "description": "What the customer wants, and "
                                       "what you checked"},
        },
        "required": ["customer_id", "order_id", "root_cause", "amount",
                     "recommended_action", "summary"],
    },
}
