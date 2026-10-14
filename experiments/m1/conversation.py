"""A support chat in the terminal: every turn is kept, in order, and sent again."""

import anthropic
from dotenv import load_dotenv

from harborline import data
from harborline.config import MAX_TOKENS, MODEL
from harborline.usage import log_usage

load_dotenv()
client = anthropic.Anthropic()
system = (
    "You are Harborline's customer support assistant. "
    "Answer from this policy, in two sentences or fewer.\n\n" + data.refund_policy()
)
messages = []  # the whole conversation, oldest first: only ever appended to

while True:
    question = input("\nYou: ")
    if question in ("", "quit"):
        break
    messages.append({"role": "user", "content": question})
    response = client.messages.create(
        model=MODEL, max_tokens=MAX_TOKENS, system=system, messages=messages
    )
    record = log_usage(response, "1.2 conversation")
    if response.stop_reason != "end_turn":
        print("Stopped:", response.stop_reason)
        break
    messages.append({"role": "assistant", "content": response.content})  # as returned
    reply = "".join(block.text for block in response.content if block.type == "text")
    print("Claude:", reply)
    print(f"  [{response.stop_reason}] {record['input_tokens']:,} in, "
          f"{record['output_tokens']} out ({record['thinking_tokens']} thinking), "
          f"{len(messages)} messages kept")

print("History:", ", ".join(message["role"] for message in messages))
