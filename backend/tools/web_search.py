"""DuckDuckGo web search tool."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.tools import tool
from duckduckgo_search import DDGS
from config import settings


@tool
def web_search(query: str) -> str:
    """
    Search the web using DuckDuckGo for current, real-time information.
    Use this when you need up-to-date facts, news, or information you don't know.
    Returns titles, URLs, and snippets from search results.

    Args:
        query: The search query to look up

    Returns:
        Formatted search results with titles, URLs, and descriptions
    """
    try:
        results = []
        with DDGS() as ddgs:
            raw_results = list(
                ddgs.text(query, max_results=settings.MAX_SEARCH_RESULTS)
            )

        if not raw_results:
            return f"No results found for query: '{query}'"

        output_lines = [f"Search results for: '{query}'\n"]
        for i, r in enumerate(raw_results, 1):
            title = r.get("title", "No title")
            href = r.get("href", "")
            body = r.get("body", "No description")
            output_lines.append(
                f"[{i}] {title}\n    URL: {href}\n    {body}\n"
            )

        return "\n".join(output_lines)

    except Exception as e:
        return f"Web search failed: {str(e)}. Try rephrasing your query."


@tool
def news_search(query: str) -> str:
    """
    Search for recent news articles using DuckDuckGo News.
    Use this for latest news, current events, and recent developments.

    Args:
        query: The news topic to search for

    Returns:
        Recent news articles with titles, URLs, dates, and summaries
    """
    try:
        with DDGS() as ddgs:
            raw_results = list(
                ddgs.news(query, max_results=settings.MAX_SEARCH_RESULTS)
            )

        if not raw_results:
            return f"No news found for: '{query}'"

        output_lines = [f"Recent news for: '{query}'\n"]
        for i, r in enumerate(raw_results, 1):
            title = r.get("title", "No title")
            url = r.get("url", "")
            date = r.get("date", "Unknown date")
            body = r.get("body", "No summary")
            source = r.get("source", "Unknown source")
            output_lines.append(
                f"[{i}] {title}\n    Source: {source} | Date: {date}\n    URL: {url}\n    {body}\n"
            )

        return "\n".join(output_lines)

    except Exception as e:
        return f"News search failed: {str(e)}"
