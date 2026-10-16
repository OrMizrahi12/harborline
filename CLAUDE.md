# Harborline

A fictional online retailer: shared code in harborline/, one folder per system.

## Commands
- Tests: .venv/bin/python -m pytest -q
- One test file: .venv/bin/python -m pytest -q tests/test_policy.py

## Conventions
@docs/conventions/money.md
@docs/conventions/dates.md

## Testing
- pytest; tests for harborline/<module>.py go in tests/test_<module>*.py.
- Name each test for the behavior it checks; one behavior per test, with the exact expected value.
- Fixtures: build small dicts inside the test, like tests/test_partner_dates.py. Never read or edit data/*.json.
- Worth a test: each input shape a function accepts, its edges, and its error path with the message.
- Not worth a test: what an existing test already checks, or what Python itself guarantees.

## Commits
- One line that says what changed.
