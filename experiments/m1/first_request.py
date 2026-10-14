"""One request: a system prompt, a user turn and max_tokens."""
import anthropic
from dotenv import load_dotenv

from harborline import data
from harborline.config import MODEL

MAX_TOKENS = 1024  # the ceiling for this reply, thinking included

load_dotenv()
client = anthropic.Anthropic()

system = (
    "You are Harborline's customer support assistant. "
    "Answer in two sentences or fewer.\n\n" + data.refund_policy()
)
ticket = data.tickets()[2]["message"]  # T-003, a refund request

response = client.messages.create(
    model=MODEL,
    max_tokens=MAX_TOKENS,
    system=system,
    messages=[{"role": "user", "content": ticket}],
)

for block in response.content:
    print(f"[{block.type}]", getattr(block, "text", ""))

usage = response.usage
details = usage.output_tokens_details
thinking = details.thinking_tokens if details else 0
print("stop_reason:", response.stop_reason)
print(f"output {usage.output_tokens} of {MAX_TOKENS}"
      f" (thinking {thinking}), input {usage.input_tokens}")
