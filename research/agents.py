"""The research subagents, defined once and shared.

Each AgentDefinition is a subagent the coordinator can start with the
Agent tool: when to use it (description), how it works (prompt), what
it may use (tools) and which model runs it. Each gets only its role's tools.
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
    description="Reads sources a search found and returns findings as "
                "JSON: each claim with its evidence and its source's details.",
    prompt="You read sources with load_document. Return only a JSON array, "
           "one object per finding, with these keys: claim (one sentence), "
           "evidence (the source's exact words, at most 30), and url, "
           "publisher, published and method, copied from the source's "
           "details. Only what sources say.",
    tools=["mcp__research__load_document"],
    model="haiku",
)
SYNTHESIZER = AgentDefinition(
    description="Writes the answer from findings it is given, and checks "
                "figures against their sources. It can't search or read.",
    prompt="You write the answer for Harborline's managers from the "
           "findings in your prompt, and nothing else. Before you keep a "
           "figure, check it with verify_fact against its url; drop what "
           "doesn't match. If the answer needs a source you weren't given, "
           "say what is missing at the end. Keep each claim with its "
           "publisher and date. Where findings disagree, show both. At "
           "most eight lines, one claim per line.",
    tools=["mcp__research__verify_fact"],
    model="haiku",
)
AGENTS = {"searcher": SEARCHER, "analyst": ANALYST,
          "synthesizer": SYNTHESIZER}
