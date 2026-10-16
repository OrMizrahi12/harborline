"""Lab 4's self-check: the run's state and the report checker, offline."""

import pytest

from research import checker, state
from research.checker import S01, S02, S03

S13 = "https://checkoutline.example/half-gets-sent-back"


def figure(url, published="2025-11-04"):
    return {"value": "x", "url": url, "published": published,
            "method": "as the source states"}


def report(contested, not_covered=""):
    return {"answer": "a", "established": [], "contested": contested,
            "not_covered": not_covered}


RATES = {"topic": "Return rate", "why": "value vs units",
         "figures": [figure(S01, "2026-03-12"), figure(S02)]}


@pytest.fixture(autouse=True)
def runs(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "RUNS", tmp_path)


def passed(checks):
    return [ok for _, ok in checks]


def test_a_good_report_passes_every_check():
    assert all(passed(checker.results(report([RATES]), [])))


def test_one_return_rate_alone_fails():
    one = {**RATES, "figures": [figure(S01, "2026-03-12"),
                                figure(S13, "2026-02-03")]}
    assert passed(checker.results(report([one]), [])) == [
        False, True, True, True]


def test_two_years_of_one_benchmark_are_not_a_conflict():
    years = {"topic": "Meridian", "why": "?",
             "figures": [figure(S02), figure(S03, "2024-01-22")]}
    assert passed(checker.results(report([RATES, years]), []))[2] is False


def test_a_failed_search_needs_a_not_covered_line():
    failures = ["[searcher 1] search_web failed: timeout"]
    assert passed(checker.results(report([RATES]), failures))[3] is False
    assert passed(checker.results(report([RATES], "fraud"), failures))[3]


def test_the_report_and_the_failures_are_saved_with_the_run():
    run_id = state.start("q")
    state.save(run_id, "searcher 1", "p", "r", failures=["x failed: timeout"])
    state.finish(run_id, report([RATES]))
    assert state.manifest(run_id)["failures"] == ["x failed: timeout"]
    assert state.report(run_id)["contested"][0]["topic"] == "Return rate"
