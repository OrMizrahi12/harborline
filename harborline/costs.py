"""What an API call costs, before you send it and after it returns.

Prices are US dollars per million tokens (MTok), from Anthropic's pricing
(checked 2026-10-13). Prices change: check them again before you rely on them.
"""

PRICES = {
    # model: input, output, and cache reads as a share of the input price
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_read": 0.10},
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_read": 0.05},
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_read": 0.05},
}

# Claude Haiku 5.5 charges more when one prompt is over 100,000 tokens.
LONG_PROMPT_TOKENS = 100_000
LONG_PROMPT_PRICES = {
    "claude-haiku-5-5": {"input": 0.50, "output": 2.50},
}

# The Message Batches API charges half price.
BATCH_DISCOUNT = 0.50


def estimate_cost(model, input_tokens, output_tokens=0, cache_read_tokens=0, batch=False):
    """Estimate the cost of one request, in US dollars.

    input_tokens counts the prompt tokens that were not read from the cache.
    """
    price = dict(PRICES[model])
    prompt_tokens = input_tokens + cache_read_tokens
    if prompt_tokens > LONG_PROMPT_TOKENS and model in LONG_PROMPT_PRICES:
        price.update(LONG_PROMPT_PRICES[model])

    cost = (
        input_tokens * price["input"]
        + cache_read_tokens * price["input"] * price["cache_read"]
        + output_tokens * price["output"]
    ) / 1_000_000

    if batch:
        cost *= BATCH_DISCOUNT
    return cost
