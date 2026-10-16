"""Run state on disk, checked without calling Claude."""

import pytest

from research import state


@pytest.fixture(autouse=True)
def runs(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "RUNS", tmp_path)  # never touch real runs


def test_reports_come_back_in_the_order_they_were_saved():
    run_id = state.start("Should we charge for returns?")
    state.save(run_id, "searcher 1", "find sources", "[3 URLs]")
    state.save(run_id, "analyst 1", "read them", "[5 findings]")
    assert [r["name"] for r in state.done(run_id)] == ["searcher 1",
                                                       "analyst 1"]
    assert state.manifest(run_id)["question"] == \
        "Should we charge for returns?"


def test_the_manifest_keeps_what_the_run_needs_to_continue():
    run_id = state.start("q")
    state.save(run_id, "searcher 1", "p", "r", found=["https://a.example"])
    assert state.manifest(run_id)["found"] == ["https://a.example"]


def test_a_new_run_starts_with_nothing_done():
    assert state.done(state.start("q")) == []
