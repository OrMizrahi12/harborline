"""Cost estimates match the price table."""

import pytest

from harborline.costs import estimate_cost


def test_haiku_prices():
    # $0.10 per million input tokens, $0.50 per million output tokens
    assert estimate_cost("claude-haiku-5-5", 100_000) == pytest.approx(0.01)
    assert estimate_cost("claude-haiku-5-5", 1_000, 100_000) == pytest.approx(0.0501)


def test_batch_is_half_price():
    normal = estimate_cost("claude-haiku-5-5", 20_000, 2_000)
    assert estimate_cost("claude-haiku-5-5", 20_000, 2_000, batch=True) == pytest.approx(normal / 2)


def test_cache_reads_are_cheap():
    # a cache read costs 10% of the input price
    assert estimate_cost("claude-haiku-5-5", 0, cache_read_tokens=100_000) == pytest.approx(0.001)


def test_long_prompts_cost_more_on_haiku():
    short = estimate_cost("claude-haiku-5-5", 100_000)
    long = estimate_cost("claude-haiku-5-5", 100_001)
    assert long > short * 4


def test_bigger_models_cost_more():
    tokens = (10_000, 1_000)
    assert (estimate_cost("claude-haiku-5-5", *tokens)
            < estimate_cost("claude-sonnet-5-5", *tokens)
            < estimate_cost("claude-opus-5-5", *tokens))
