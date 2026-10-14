"""The API keeps no memory: each request must carry the conversation."""
import anthropic
from dotenv import load_dotenv

from harborline import data
from harborline.config import MAX_TOKENS, MODEL

load_dotenv()
client = anthropic.Anthropic()
SYSTEM = "You are Harborline's support assistant. Reply in two sentences."


def ask(label, messages):
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        messages=messages,
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    tokens = response.usage.input_tokens
    print(f"--- {label}: messages={len(messages)}, input_tokens={tokens}")
    print(text + "\n")
    return response


first = {"role": "user", "content": data.tickets()[2]["message"]}
reply = ask("first request", [first])

question = {"role": "user", "content": "Which order did I mention?"}
ask("new request, no history", [question])

answer = {"role": "assistant", "content": reply.content}
ask("new request, full history", [first, answer, question])
