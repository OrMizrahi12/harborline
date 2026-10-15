"""Research tools, served in-process to the Agent SDK.

search_web finds sources by keyword; fetch_url returns one page in full.
Our "web" is data/research/: 14 fixed sources on one question, so the
same query always finds the same pages, and a search costs nothing.

    python -m research.tools "return fee"
"""

import json
import re
import sys

from claude_agent_sdk import create_sdk_mcp_server, tool

from harborline import data

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


def fetch(url):
    """One page in full, by its URL."""
    for source in data.research_sources():
        if source["url"] == url:
            return data.research_document(source["id"])
    raise KeyError(url)


def reply(text, error=False):
    result = {"content": [{"type": "text", "text": text}]}
    return result | {"is_error": True} if error else result


@tool("search_web", "Search the web. Returns up to 5 results: title, URL, "
      "publisher, date published and a short snippet. Use short keyword "
      "queries, one topic per search.", {"query": str})
async def search_web(args):
    return reply(json.dumps(search(args["query"]), indent=1))


@tool("fetch_url", "Fetch one web page by its URL and return its full "
      "text. Use it on URLs that search_web returned.", {"url": str})
async def fetch_url(args):
    try:
        return reply(fetch(args["url"]))
    except KeyError:
        return reply(f"No page at {args['url']}.", error=True)


server = create_sdk_mcp_server("research", version="1.0.0",
                               tools=[search_web, fetch_url])

if __name__ == "__main__":
    for hit in search(sys.argv[1]):
        print(hit["published"], hit["publisher"], hit["url"])
