"""The research tools' limits, checked without calling Claude."""

import json

import pytest

from research import tools

FEE_STUDY = "https://retail-signals.example/2026/05/charging-for-returns"


def test_load_refuses_a_url_no_search_returned():
    tools.FOUND.clear()
    with pytest.raises(PermissionError):
        tools.load(FEE_STUDY)


def test_load_returns_the_details_then_the_text():
    tools.FOUND.clear()
    tools.FOUND.update(hit["url"] for hit in tools.search("charging returns"))
    details, text = tools.load(FEE_STUDY).split("\n\n", 1)
    assert json.loads(details)["publisher"] == "Retail Signals Weekly"
    assert text


def test_verify_finds_the_sentence_behind_a_figure():
    found = tools.verify("return volume fell a median 18%", FEE_STUDY)
    assert any("18%" in sentence for sentence in found)


def test_verify_finds_nothing_for_an_unrelated_claim():
    assert tools.verify("the warehouse opens at noon", FEE_STUDY) == []
