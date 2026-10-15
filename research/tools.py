"""Research tools, served in-process to the Agent SDK.

search_web finds sources by keyword. load_document returns one source that
a search found, with its details. verify_fact checks one claim against one
source. Our "web" is data/research/: 14 fixed sources on one question, so
the same query always finds the same pages, and a search costs nothing.

    python -m research.tools "return fee"
"""

import json
import re
import sys

from claude_agent_sdk import create_sdk_mcp_server, tool

from harborline import data

FOUND = set()  # URLs that search_web returned in this run
COMMON = {"the", "a", "an", "of", "and", "or", "for", "to", "in", "on",
          "is", "are", "do", "does", "what", "how", "should", "we"}


def words(text):
    return set(re.findall(r"[a-z0-9]+", text.lower())) - COMMON


def search(query, limit=5):
    """The best matches: title, URL, publisher, date and a snippet."""
    wanted = words(query)
    hits = []
    for source in data.research_sources():
        page = data.research_document(source["id"])
        score = len(wanted & words(source["title"] + " " + page))
        if score:
            hits.append((score, {
                "title": source["title"], "url": source["url"],
                "publisher": source["publisher"],
                "published": source["published"],
                "snippet": page.split("\n\n")[2][:200]}))
    hits.sort(key=lambda hit: -hit[0])
    return [hit for _, hit in hits[:limit]]


def load(url):
    """One source a search found: its details, then its text."""
    if url not in FOUND:
        raise PermissionError(url)
    for source in data.research_sources():
        if source["url"] == url:
            details = {key: source[key] for key in
                       ("url", "publisher", "published", "method")}
            return json.dumps(details) + "\n\n" + \
                data.research_document(source["id"])
    raise KeyError(url)


def verify(claim, url):
    """The source's sentences that share the most words with the claim."""
    for source in data.research_sources():
        if source["url"] == url:
            page = data.research_document(source["id"])
            break
    else:
        raise KeyError(url)
    wanted = words(claim)
    sentences = re.split(r"(?<=[.!?])\s+", page)
    scored = sorted(sentences, key=lambda s: -len(wanted & words(s)))
    return [s for s in scored[:3] if len(wanted & words(s)) >= 3]


def reply(text, error=False):
    result = {"content": [{"type": "text", "text": text}]}
    return result | {"is_error": True} if error else result


@tool("search_web", "Search the web. Returns up to 5 results: title, URL, "
      "publisher, date published and a short snippet. Use short keyword "
      "queries, one topic per search.", {"query": str})
async def search_web(args):
    hits = search(args["query"])
    FOUND.update(hit["url"] for hit in hits)
    return reply(json.dumps(hits, indent=1))


@tool("load_document", "Load one source that search_web returned, by its "
      "URL. Returns the source's details (url, publisher, published, "
      "method) as JSON, then its full text. It loads only URLs a search "
      "returned in this run.", {"url": str})
async def load_document(args):
    try:
        return reply(load(args["url"]))
    except PermissionError:
        return reply(f"{args['url']} wasn't returned by search_web in this "
                     "run. Load a URL from the search results.", error=True)
    except KeyError:
        return reply(f"No source at {args['url']}.", error=True)


@tool("verify_fact", "Check one claim against the source it cites. Returns "
      "up to 3 sentences from that source that match the claim, or none. "
      "It doesn't search or return whole pages.",
      {"claim": str, "url": str})
async def verify_fact(args):
    try:
        found = verify(args["claim"], args["url"])
    except KeyError:
        return reply(f"No source at {args['url']}.", error=True)
    return reply(json.dumps(found, indent=1) if found else
                 "No sentence in this source matches the claim.")


server = create_sdk_mcp_server(
    "research", version="1.0.0",
    tools=[search_web, load_document, verify_fact])

if __name__ == "__main__":
    for hit in search(sys.argv[1]):
        print(hit["published"], hit["publisher"], hit["url"])
