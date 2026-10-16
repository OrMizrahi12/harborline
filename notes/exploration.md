# Refund path: exploration

Phase 1 map, read-only. Three entry points reach the refund tool; only the MCP path pays.

## Path: support/ (customer chat agent)
1. support/agent.py:41 `handle()` runs `query()` with OPTIONS (agent.py:27-38), which wires HOOKS and the harborline MCP server.
2. support/hooks.py:18 `refund_limit` (PreToolUse on `mcp__harborline__process_refund`) reads `tool_input["amount"]` and denies above `REFUND_LIMIT` (hooks.py:15).
3. support/tools.py:53 `process_refund` -> `reply()` (tools.py:20) -> `gates.process_refund`.
4. support/gates.py:138 `process_refund` -> `check()` (gates.py:102): verified-customer and owner check.
5. support/gates.py:140 hands off to `backend.process_refund` (harborline/backend.py:111).
6. support/hooks.py:52 and support/case_facts.py:35 record `refund_id` and `amount` (case_facts.py:46-49).

## Path: mcp_server/ (MCP tool)
1. mcp_server/server.py:60-64 `process_refund(order_id, reason, amount, sku=None)`; description from loop/tools.py:70-87.
2. server.py:33-41 `call()` wraps `BackendError` as `isError`.
3. server.py:61 hands off to `backend.process_refund` (backend.py:111) with `opened=False`.
4. server.py:67-70 `refund_policy` resource: text read only.

## Path: loop/ (three entry points)
- **loop/mcp_agent.py** (only path that pays): `main()` :146 -> `run()` :102 -> `run_call()` :73 -> `guard()` :48. `guard()` :52-59 blocks `process_refund` above the limit. `run_call()` :89 calls `session.call_tool`, the handoff to mcp_server/. `escalate_to_human` runs locally (mcp_agent.py:63-65).
- **loop/agent.py**: `run()` :78 uses `ROLE_TOOLS` :29 (no `process_refund`). `check_refund` goes through `run_tool()` (tools.py:168) -> `check_refund()` (tools.py:149) -> policy.py:58.
- **loop/workflow.py**: `handle()` :73 -> `route()` :49 -> `backend.get_customer` / `lookup_order` (:81-82) -> `write()` :61. Text only; never pays.

## Shared core: harborline/
- harborline/backend.py:111 `process_refund`: amount > 0 check (:113), `_find_order` (:68), review hold, `policy.check_refund` (:120), cap at `decision["refund"]` (:123), cumulative-paid check (:126), append to `_refunds`.
- harborline/policy.py:58 `check_refund`: the only place a refund amount is computed.

## Convention check (docs/conventions)
- **Amounts**: no caller computes a refund amount. Callers forward the model's `amount`, and the cap comes from `policy.check_refund` downstream. Hook and guard checks compare the claimed amount against the $500 limit; they do not compute one.
- **Dates**: support/ reads dates through `harborline.normalize.order` (hooks.py:40, case_facts.py:51 and :66). loop/ never parses order dates. backend.py and policy.py parse via `policy.as_date` (policy.py:27-40), not `normalize`. This is a possible break of the dates rule in harborline/, outside the three folders mapped here.

## Open questions
1. **Per-call limit gap**: the $500 hook checks each call, and the cumulative check is only in backend.py:126. Two $400 refunds on a $649 order each pass the hook. Not covered by hook_check.py (it tries only 42 and 649).
   - **Answer:** Each $400 call passes the hook and `guard()`, since both read only the current amount. The second $400 is blocked by backend.py:126 (`paid + amount > total`): "the most left is $249.00". Gap: $450 then $199 on the $649 order passes both checks (649 <= 649.005), so the $500 approval rule is never applied to the running total. `policy.needs_approval` (policy.py:42-44) is called only from tests/test_policy.py:70-71. No test covers a split above $500. Source: backend.py:120-129 (read directly); the rest from a subagent report, unverified by running code.
2. **Two copies of the limit**: support/hooks.py:15 `REFUND_LIMIT` and harborline/config.py:21 `REFUND_APPROVAL_LIMIT`, both 500.00. They can drift.
3. **Uncaught parse error**: hooks.py:20 `float()` on a non-numeric amount raises an uncaught `ValueError`.
4. **Opened electronics**: `opened` is not exposed by the MCP tool, so opened electronics cannot be refunded through it. Gap, not a convention break.
5. **Reason duplication**: the `Reason` Literal (server.py:28-30) matches `policy.REASONS` by comment only.
6. **Unused handler**: loop/tools.py `HANDLERS` maps `process_refund` to the backend, but no loop/ entry point offers it to Claude.
7. **Date parsing in harborline/**: confirm whether `normalize` is used anywhere on the refund path, or only `policy.as_date`.
