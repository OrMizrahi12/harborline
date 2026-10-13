# Harborline data

Everything in this folder is **synthetic and fictional**: the customers, orders,
suppliers, publishers, people, figures and web addresses are invented for this
course. Email addresses use the reserved `example.com` / `example.net` domains,
phone numbers use the fictional 555-01xx range, and every website uses an
`.example` address that does not exist.

Harborline's "today" is **2026-10-15** (`harborline/config.py`,
`BUSINESS_DATE`). Return windows and order ages are measured from that day.

| File | What it holds |
|---|---|
| `customers.json` | 60 customers. Two share the name Jordan Lee; one has no orders; one account is on review hold. |
| `products.json` | 40 products. Items whose name starts with "Clearance:" are Final Sale. |
| `orders.json` | 213 orders. Orders placed before July 15, 2026 come from the old warehouse system: their timestamps are Unix seconds and their status is a number (see `legacy/warehouse/codes.py`). Newer orders use ISO 8601 text. |
| `refund_policy.md` | The refund and returns policy that customers and support staff read. `harborline/policy.py` is the same policy as code. |
| `faults.json` | Simulated outages for the error-handling lessons (an order lookup that times out once; search words that time out). |
| `tickets/labeled_tickets.jsonl` | 50 support tickets, each labeled with the right outcome (`resolve` or `escalate`), the expected refunds, and a note. `split` is `dev` (20) for building prompts and `test` (30) for measuring. |
| `evals/tool_routing.jsonl` | 16 customer requests, each labeled with the tool that should handle it. |
| `invoices/dev/`, `invoices/batch/` | 112 supplier invoices as plain text: 12 for development and 100 for batch runs. Layouts vary: tables, letters, emails and scanned copies. |
| `invoices/labels.jsonl` | The correct extraction for every invoice (dates in ISO 8601, quantities in units, `null` where the document doesn't say). |
| `research/sources.json`, `research/docs/` | 14 sources on one question: "Should Harborline charge customers a fee for return shipping?" Some are web articles, some are Harborline internal documents. |
