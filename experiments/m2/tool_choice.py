"""One request, five tool_choice settings: what comes back?

    python -m experiments.m2.tool_choice                 (Haiku 5.5)
    python -m experiments.m2.tool_choice claude-sonnet-5-5
"""

import sys
import textwrap

import anthropic
from dotenv import load_dotenv

from harborline.config import MAX_TOKENS, MODEL
from harborline.usage import log_usage
from loop.tools import TOOLS

REQUEST = ("Signed-in customer: C-1046\n\n"
           "I need a supervisor to sign off on a refund over $500.")
ASK = " Use the escalate_to_human tool."
# Strict tools: Claude's input always matches the schema (Lesson 7.1).
STRICT = [tool | {"strict": True, "input_schema": tool["input_schema"]
                  | {"additionalProperties": False}} for tool in TOOLS]
CHOICES = [  # (row, tool_choice, tools, added to the request)
    ("auto", {"type": "auto"}, TOOLS, ""),
    ("any", {"type": "any"}, TOOLS, ""),
    ("tool", {"type": "tool", "name": "escalate_to_human"}, TOOLS, ""),
    ("none", {"type": "none"}, TOOLS, ""),
    ("asked", {"type": "auto"}, STRICT, ASK),  # where forcing fails
]

if __name__ == "__main__":
    load_dotenv()
    model = sys.argv[1] if len(sys.argv) > 1 else MODEL
    print(f"{model}\n")
    client = anthropic.Anthropic()
    cost = 0.0
    for row, choice, tools, extra in CHOICES:
        try:
            response = client.messages.create(
                model=model, max_tokens=MAX_TOKENS, tools=tools,
                tool_choice=choice,
                messages=[{"role": "user", "content": REQUEST + extra}],
            )
        except anthropic.BadRequestError as error:  # nothing was run
            print(textwrap.fill(error.body["error"]["message"], 60,
                                initial_indent=f"{row:6} 400  ",
                                subsequent_indent=" " * 12))
            continue
        record = log_usage(response, f"2.3 tool_choice {row}")
        cost += record["cost_usd"]
        kinds = ", ".join(block.type for block in response.content)
        print(f"{row:6} {response.stop_reason:9}"
              f"{record['input_tokens']:>6,} in  {kinds}")
        for block in response.content:  # by type, never by position
            if block.type == "text":
                print("       " + textwrap.shorten(block.text, 52))
            elif block.type == "tool_use":
                shown = f"{block.name} {block.input}"
                print("       " + textwrap.shorten(shown, 52))
    print(f"\n${cost:.4f}")
