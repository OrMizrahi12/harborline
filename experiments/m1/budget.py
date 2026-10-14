"""How much of the context window does one request use?

Counting tokens is free, and it doesn't run the model.
"""
import anthropic
from dotenv import load_dotenv

from harborline import data
from harborline.config import DATA_DIR, MODEL

load_dotenv()
client = anthropic.Anthropic()

model = client.models.retrieve(MODEL)
window = model.max_input_tokens
print(f"{MODEL}: window {window:,}, max output {model.max_tokens:,}")

role = "You are Harborline's customer support assistant."
policy = data.refund_policy()
orders = (DATA_DIR / "orders.json").read_text(encoding="utf-8")
ticket = data.tickets()[2]["message"]  # T-003, a refund request

systems = {
    "role": role,
    "role + policy": role + "\n\n" + policy,
    "role + policy + orders": role + "\n\n" + policy + "\n\n" + orders,
}
for name, system in systems.items():
    count = client.messages.count_tokens(
        model=MODEL,
        system=system,
        messages=[{"role": "user", "content": ticket}],
    )
    used = count.input_tokens
    print(f"{name:<24}{used:>8,} tokens {used / window:>7.2%}")
