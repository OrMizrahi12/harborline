"""Provenance checks on hand-written reports, without calling Claude."""

from research.provenance import check, parse, render

S01 = "https://retail-signals.example/2026/03/return-rates-new-high"
S02 = "https://meridian-institute.example/reports/returns-benchmark-2025"
S13 = "https://checkoutline.example/half-gets-sent-back"


def figure(value, url, published):
    return {"value": value, "url": url, "published": published,
            "method": "as the source states"}


REPORT = {
    "answer": "Not a blanket fee.",
    "established": [{"claim": "About half of online orders come back.",
                     "url": S13, "published": "2026-02-03"}],
    "contested": [{"topic": "Return rate", "why": "value vs units",
                   "figures": [figure("24.0% of value", S01, "2026-03-12"),
                               figure("17.6% of units", S02, "2025-11-04")]}],
    "not_covered": "",
}


def test_both_figures_keep_their_sources_in_the_table():
    table = render(REPORT)
    assert "| 24.0% of value | Retail Signals Weekly, 2026-03-12 |" in table
    assert "| 17.6% of units | Meridian Commerce Institute, 2025-11-04 |" \
        in table


def test_a_source_with_no_method_is_flagged():
    assert "(no method stated)" in render(REPORT)


def test_check_finds_unknown_sources_and_lone_figures():
    broken = {**REPORT, "contested": [{
        "topic": "Fee effect", "why": "?",
        "figures": [figure("18%", "https://made-up.example", "2026-01-01")]}]}
    assert check(REPORT) == []
    assert check(broken) == ["unknown source: https://made-up.example",
                             "contested with one figure: Fee effect"]


def test_parse_finds_the_report_inside_other_text():
    assert parse('Here it is:\n```json\n{"answer": "x"}\n```') == \
        {"answer": "x"}
