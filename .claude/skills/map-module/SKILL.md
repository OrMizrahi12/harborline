---
description: Map a Python package's public names and where each one is really defined. Use when someone asks what a module exports or where a name comes from.
argument-hint: [module]
context: fork
agent: Explore
background: false
allowed-tools: mcp__codemap__list_public_names mcp__codemap__trace_export Read
disallowed-tools: Write Edit Bash
---

Map the package $ARGUMENTS:
1. List its public names with list_public_names.
2. For each name that comes from another module, find its real definition with trace_export.
3. Answer with one table: name, defined in (file:line), original name if it was renamed.
Change no files.
