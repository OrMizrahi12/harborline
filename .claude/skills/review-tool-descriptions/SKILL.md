---
description: Review the tool descriptions in a file against the team's tool rules. Use when tool definitions change.
argument-hint: [file]
context: fork
agent: Explore
background: false
allowed-tools: Read Grep Glob
---

Review every tool description in $ARGUMENTS. For each tool, check that it:
1. says what the tool returns,
2. says when to use it instead of a similar tool,
3. reports errors through harborline/tool_errors.py.

Answer with one line per tool: its name, then OK or the gap and a suggested fix.
Change no files.
