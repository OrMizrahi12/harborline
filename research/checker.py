"""Lab 4's checks on a finished run's report.

    python -m research.checker <run_id>

The report must keep both return-rate figures with their sources, cite
only known and dated sources, keep a change over time out of the conflicts,
and say what isn't covered whenever a tool call failed during the run.
"""

import sys

from research import state
from research.provenance import check

S01 = "https://retail-signals.example/2026/03/return-rates-new-high"
S02 = "https://meridian-institute.example/reports/returns-benchmark-2025"
S03 = "https://meridian-institute.example/reports/returns-benchmark-2023"


def urls(topic):
    return {figure["url"] for figure in topic["figures"]}


def results(report, failures):
    """(check, passed) for each of the lab's targets."""
    contested = [urls(topic) for topic in report["contested"]]
    return [
        ("both return rates kept, each with its source",
         any({S01, S02} <= topic for topic in contested)),
        ("every claim from a known, dated source", check(report) == []),
        ("a change over time isn't filed as a conflict",
         not any({S02, S03} <= topic for topic in contested)),
        ("failed tool calls reported as not covered",
         not failures or bool(report.get("not_covered"))),
    ]


if __name__ == "__main__":
    run_id = sys.argv[1]
    failures = state.manifest(run_id).get("failures", [])
    checks = results(state.report(run_id), failures)
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
    print(f"{len(failures)} failed tool calls in the run")
    print("PASS" if all(passed for _, passed in checks) else "FAIL")
