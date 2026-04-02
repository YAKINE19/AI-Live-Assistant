"""Web page content extraction tool."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import httpx
from langchain_core.tools import tool
from bs4 import BeautifulSoup
from config import settings

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _clean_text(text: str) -> str:
    """Remove excess whitespace and clean extracted text."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def _extract_content(html: str, url: str) -> str:
    """Extract meaningful text content from HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise elements
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "advertisement", "noscript", "iframe",
                     "form", "button", "input", "select"]):
        tag.decompose()

    # Try to find main content area
    main_content = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id=re.compile(r"(content|main|article|post)", re.I))
        or soup.find(class_=re.compile(r"(content|main|article|post|body)", re.I))
    )

    target = main_content if main_content else soup.body or soup

    # Get title
    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = f"Page Title: {title_tag.get_text(strip=True)}\n\n"

    # Extract text
    text = target.get_text(separator="\n")
    cleaned = _clean_text(text)

    # Truncate to max length
    if len(cleaned) > settings.MAX_SCRAPE_LENGTH:
        cleaned = cleaned[: settings.MAX_SCRAPE_LENGTH] + "\n\n[Content truncated...]"

    return f"URL: {url}\n{title}{cleaned}"


@tool
def scrape_webpage(url: str) -> str:
    """
    Extract and read the text content from a webpage URL.
    Use this to get detailed information from a specific webpage found in search results.
    Provide the full URL including https://.

    Args:
        url: The full URL of the webpage to scrape

    Returns:
        The extracted text content of the webpage
    """
    if not url.startswith(("http://", "https://")):
        return f"Invalid URL: '{url}'. URL must start with http:// or https://"

    try:
        with httpx.Client(
            headers=HEADERS,
            timeout=15.0,
            follow_redirects=True,
        ) as client:
            response = client.get(url)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return f"Cannot extract content: page is not HTML (type: {content_type})"

        return _extract_content(response.text, url)

    except httpx.TimeoutException:
        return f"Timeout: Could not load '{url}' within 15 seconds."
    except httpx.HTTPStatusError as e:
        return f"HTTP error {e.response.status_code} when accessing '{url}'"
    except Exception as e:
        return f"Failed to scrape '{url}': {str(e)}"
