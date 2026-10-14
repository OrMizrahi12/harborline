"""Four ways to decide that the loop is done. Only one is right.

Runs the real loop once, then asks each stop rule where it would
have ended that same run.

    python -m experiments.m1.antipatterns T-003
"""

import re
import sys

import anthropic
from dotenv import load_dotenv

from loop.agent import first_message, run


def text_of(response):
    return " ".join(b.text for b in response.content
                    if b.type == "text")


def done_words(response, turn):  # 1. read the reply for "done"
    words = r"\b(done|resolved|all set)\b"
    return re.search(words, text_of(response), re.IGNORECASE) is not None


def fixed_cap(response, turn):  # 2. stop after a fixed count
    return turn == 2


def any_text(response, turn):  # 3. any text means finished
    return text_of(response) != ""


def stop_reason(response, turn):  # the rule that works
    return response.stop_reason == "end_turn"


def where_it_stops(rule, responses):
    for turn, response in enumerate(responses, 1):
        if rule(response, turn):
            return turn
    return None


load_dotenv()
responses = run(anthropic.Anthropic(), [first_message(sys.argv[1])])
print()
for rule in (stop_reason, done_words, fixed_cap, any_text):
    turn = where_it_stops(rule, responses)
    if turn is None:
        print(f"{rule.__name__:11} never stops: it missed the end_turn")
        continue
    response = responses[turn - 1]
    verdict = "OK" if response.stop_reason == "end_turn" else "WRONG"
    print(f"{rule.__name__:11} turn {turn}, {response.stop_reason}: "
          f"{verdict}")
    print(f"{'':11} customer gets: {text_of(response)[:50]!r}")
