---
paths:
  - "devtools/**"
---

# Developer tools

- Agent SDK agents here load no Claude Code settings: setting_sources=[].
- Give each agent an explicit tools list, allowed_tools, permission_mode="dontAsk" and a max_budget_usd.
- MCP tool descriptions say what the tool returns and when to use it instead of Grep.
