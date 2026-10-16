"""The research subagents, defined once and shared.

Each AgentDefinition is a subagent the coordinator can start with the
Agent tool: when to use it (description), how it works (prompt), what
it may use (tools) and which model runs it. Each gets only its role's tools.
"""

from claude_agent_sdk import AgentDefinition

from research.provenance import SHAPE

SEARCHER = AgentDefinition(
    description="Finds sources on the web for one research question. "
                "Returns the URLs worth reading, with publisher and date.",
    prompt="You search the web with search_web. Return a short list of "
           "the most relevant sources: URL, publisher, date, and one line "
           "on what each covers. Don't read the pages. If a search fails, "
           "follow its alternatives. If it still fails, say so: what "
           "failed, the query, and any partial results. Never report a "
           "failed search as finding nothing.",
    tools=["mcp__research__search_web"],
    model="haiku",
)
ANALYST = AgentDefinition(
    description="Reads sources a search found and returns findings as "
                "JSON: each claim with its evidence and its source's details.",
    prompt="You read sources with load_document. Return only a JSON array, "
           "one object per finding, with these keys: claim (one sentence), "
           "evidence (the source's exact words, at most 30), url, "
           "publisher, published and method (copied from the source's "
           "details), and relevance (0 to 1: how much it bears on the "
           "question). Only what sources say; no reasoning.",
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
           "say so in not_covered, and also any part your prompt marks as "
           "not covered, with why. Every claim keeps its url and date. "
           "Where figures disagree, keep them all under contested with "
           "their sources, and say why they differ (another measure, "
           "sample or method). Figures from different years show a change "
           "over time, not a conflict: put them under established with "
           "their dates. A source with no stated method can't settle a "
           "conflict on its own. " + SHAPE,
    tools=["mcp__research__verify_fact"],
    model="haiku",
)
AGENTS = {"searcher": SEARCHER, "analyst": ANALYST,
          "synthesizer": SYNTHESIZER}
