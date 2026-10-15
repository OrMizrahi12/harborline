"""The research subagents, defined once and shared.

Each AgentDefinition is a subagent the coordinator can start with the
Agent tool: when to use it (description), how it works (prompt), what
it may use (tools) and which model runs it.
"""

from claude_agent_sdk import AgentDefinition

SEARCHER = AgentDefinition(
    description="Finds sources on the web for one research question. "
                "Returns the URLs worth reading, with publisher and date.",
    prompt="You search the web with search_web. Return a short list of "
           "the most relevant sources: URL, publisher, date, and one line "
           "on what each covers. Don't read the pages.",
    tools=["mcp__research__search_web"],
    model="haiku",
)
ANALYST = AgentDefinition(
    description="Reads web pages and returns findings as JSON: each "
                "claim with its evidence and its source's details.",
    prompt="You read pages with fetch_url. Return only a JSON array, one "
           "object per finding, with these keys: claim (one sentence), "
           "evidence (the page's exact words, at most 30), url, "
           "publisher, published (the page's date), method (how the "
           "source got its figure, from the page). Only what pages say.",
    tools=["mcp__research__fetch_url"],
    model="haiku",
)
SYNTHESIZER = AgentDefinition(
    description="Writes the answer from findings it is given. It has no "
                "tools: everything it uses must be in its prompt.",
    prompt="You write the answer for Harborline's managers from the "
           "findings in your prompt, and nothing else. Keep each claim "
           "with its publisher and date. Where findings disagree, show "
           "both. At most eight lines, one claim per line.",
    tools=[],
    model="haiku",
)
AGENTS = {"searcher": SEARCHER, "analyst": ANALYST,
          "synthesizer": SYNTHESIZER}
