"""Provenance: every claim in the report keeps its source.

The synthesizer returns the report as JSON. render() turns it into the
report people read: the answer first, then what the sources agree on, then
what they don't, as a table with each figure's source, date and method.
check() lists what breaks provenance before anyone reads it.
"""

import json

from harborline import data

SHAPE = (
    'Return only JSON: {"answer": "two or three sentences", '
    '"established": [{"claim": ..., "url": ..., "published": ...}], '
    '"contested": [{"topic": ..., "why": "why the figures differ", '
    '"figures": [{"value": ..., "url": ..., "published": ..., '
    '"method": ...}]}], "not_covered": "what and why, or empty"}. At '
    'most six established claims and three contested topics, the most '
    'important first, one sentence each.')


def parse(text):
    """The report: the JSON object in a reply, whatever surrounds it."""
    return json.loads(text[text.find("{"):text.rfind("}") + 1])


def sources():
    return {source["url"]: source for source in data.research_sources()}


def cite(item):
    source = sources().get(item["url"], {})
    flag = "" if source.get("method", "none stated") != "none stated" \
        else " (no method stated)"
    return f"{source.get('publisher', item['url'])}, {item['published']}{flag}"


def render(report):
    lines = ["## Answer", report["answer"], "", "## Established"]
    lines += [f"- {item['claim']} ({cite(item)})"
              for item in report["established"]]
    lines += ["", "## Contested"]
    for topic in report["contested"]:
        lines += [f"**{topic['topic']}**: {topic['why']}", "",
                  "| Figure | Source | Method |", "|---|---|---|"]
        lines += [f"| {f['value']} | {cite(f)} | {f['method']} |"
                  for f in topic["figures"]]
        lines.append("")
    if report.get("not_covered"):
        lines += ["## Not covered", report["not_covered"]]
    return "\n".join(lines)


def check(report):
    """What breaks provenance: unknown sources, missing dates, lone figures."""
    known, problems = sources(), []
    items = report["established"] + [
        figure for topic in report["contested"] for figure in topic["figures"]]
    for item in items:
        if item.get("url") not in known:
            problems.append(f"unknown source: {item.get('url')}")
        elif not item.get("published"):
            problems.append(f"no date: {item['url']}")
    for topic in report["contested"]:
        if len(topic["figures"]) < 2:
            problems.append(f"contested with one figure: {topic['topic']}")
    return problems
