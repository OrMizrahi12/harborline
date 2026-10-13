# Harborline

Harborline is a fictional mid-size online retailer. It sells home, kitchen, bedding, electronics, outdoor and office goods to customers in the United States and Canada.

This repository is the starting point of the course project for **Claude Certified Architect – Foundations (CCAR-F)**. Module by module, you build six systems on top of it, one for each of the exam's scenarios. Everything here, from the customers to the supplier invoices, is synthetic and fictional.

This is independent training material. It is not affiliated with or endorsed by Anthropic.

## The six systems you will build

| Module | What Harborline gains | Folder | Exam scenario |
|---|---|---|---|
| 1 | A tool-using agent loop on the Messages API | `loop/` | Foundations for every scenario |
| 2 | `harborline-mcp`: an MCP server for customers, orders and refunds | `mcp_server/` | Tools for Scenarios 1 and 4 |
| 3 | The support resolution agent, with gates, hooks and escalation | `support/` | Scenario 1: Customer Support Resolution Agent |
| 4 | A coordinator and research subagents that write a cited report | `research/` | Scenario 3: Multi-Agent Research System |
| 5 | Claude Code set up for a team, and a codebase explorer agent | `.claude/`, `devtools/` | Scenarios 2 and 4: Code Generation, Developer Productivity |
| 6 | A pull-request review pipeline in GitHub Actions | `.github/`, `ci/` | Scenario 5: Claude Code for Continuous Integration |
| 7 | A supplier-invoice extraction pipeline | `extraction/` | Scenario 6: Structured Data Extraction |

## What is here now

```
harborline/        the shared code every system uses
  config.py        settings: the default model, max_tokens, Harborline's "today"
  data.py          reads the files in data/
  backend.py       the backend a support agent works with: customers, orders, refunds, escalations
  policy.py        the refund policy as rules a program can check
  errors.py        the kinds of failure the backend reports
  costs.py         what a request costs, from its token counts
legacy/warehouse/  code from the old warehouse system (you explore it in Modules 2 and 5)
data/              customers, orders, the refund policy, labeled tickets, invoices, research sources
scripts/           check_setup.py and count_tokens.py
tests/             tests that run offline, with no API key
```

`data/README.md` describes every data file.

## Set up

You need Python 3.12 or newer and git (see the setup guide for your operating system).

```bash
git clone https://github.com/OrMizrahi12/harborline-starter.git harborline
cd harborline
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest
python -m scripts.check_setup
```

On Windows, use `py -3.12 -m venv .venv` if `python3` is not found.

`pytest` should report every test as passed. The tests need no API key and make no API calls.

## Your API key

From Module 1 on, the code calls the Claude API with your own key.

```bash
cp .env.example .env               # Windows: copy .env.example .env
```

Open `.env` and paste your key after `ANTHROPIC_API_KEY=`. `.env` is in `.gitignore`, so git never commits it. Never paste the key into code.

## Cost habits

The course keeps API costs low. Most lessons cost a fraction of a cent.

- **Start with the cheapest model that does the job.** `config.MODEL` is `claude-haiku-5-5`. Step up to a larger model only when a test shows you need it.
- **Keep `max_tokens` small,** but leave room: on Claude Haiku 5.5, thinking counts toward `max_tokens`.
- **Count tokens before a big run.** Counting doesn't run the model:
  ```bash
  python -m scripts.count_tokens data/refund_policy.md data/orders.json
  ```
- **Send only what the task needs:** one ticket, one invoice, one source, not the whole folder.
- **Use the Message Batches API for volume.** It costs half as much when you can wait for the results.

## Make it your own

Push your work to your own GitHub repository, so you keep your history and can run the CI module later:

```bash
git remote rename origin upstream
gh repo create harborline --private --source . --remote origin --push
```
