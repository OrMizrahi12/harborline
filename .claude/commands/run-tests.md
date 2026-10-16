---
description: Run one test file, then the whole suite, and summarize the result
argument-hint: [test-file]
allowed-tools: Bash(.venv/bin/python -m pytest *)
---

Run .venv/bin/python -m pytest -q $ARGUMENTS, then the whole suite with .venv/bin/python -m pytest -q.
Report the pass and fail counts of each run. For a failure, name the test and the line that failed.
