"""Build public job queries and read search-result pages. This does not sign in."""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from app.config import TRACK_QUERY, TRACKS

SEARCH_URL = "https://html.duckduckgo.com/html/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def build_queries(locations: list[str], tracks: list[str], year: int = 2026) -> list[dict[str, str]]:
    queries: list[dict[str, str]] = []
    for location in locations:
        for track in tracks:
            phrase = TRACK_QUERY[track]
            queries.append(
                {
                    "location": location,
                    "track": track,
                    "query": f"{location} {phrase} {year}",
                }
            )
    return queries


def unwrap_url(href: str) -> str:
    """Turn a search redirect into the public target, or return a direct http(s) link."""
    if href.startswith("//"):
        href = "https:" + href
    parsed = urllib.parse.urlparse(href)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        target = urllib.parse.parse_qs(parsed.query).get("uddg", [""])[0]
        parsed = urllib.parse.urlparse(target)
    if parsed.scheme in ("http", "https") and parsed.netloc != "":
        return urllib.parse.urlunparse(parsed)
    return ""


class ResultParser(HTMLParser):
    """Collect title links and the snippet that follows each one."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._capture = ""
        self._href = ""
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attr = {key: value or "" for key, value in attrs}
        classes = attr.get("class", "").split()
        if "result__a" in classes:
            self._capture = "title"
            self._href = attr.get("href", "")
            self._buffer = []
        elif "result__snippet" in classes:
            self._capture = "snippet"
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._capture == "":
            return
        text = " ".join("".join(self._buffer).split())
        if self._capture == "title" and text:
            url = unwrap_url(self._href)
            if url:
                self.results.append({"title": text[:200], "url": url[:500], "summary": ""})
        elif self._capture == "snippet" and self.results and text:
            self.results[-1]["summary"] = text[:400]
        self._capture = ""
        self._buffer = []


def parse_results(html: str) -> list[dict[str, str]]:
    parser = ResultParser()
    parser.feed(html)
    parser.close()
    return parser.results


def fetch_search_html(query: str, timeout: float = 12) -> str:
    body = urllib.parse.urlencode({"q": query}).encode("utf-8")
    request = urllib.request.Request(
        SEARCH_URL,
        data=body,
        headers={"content-type": "application/x-www-form-urlencoded", "user-agent": USER_AGENT},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def search_public(
    locations: list[str],
    tracks: list[str],
    limit: int,
    fetch=fetch_search_html,
) -> list[dict[str, str]]:
    """Return at most `limit` unique public result rows. A failed query is skipped."""
    chosen = [track for track in tracks if track in TRACKS]
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in build_queries(locations, chosen):
        if len(found) >= limit:
            break
        try:
            html = fetch(item["query"])
        except (OSError, urllib.error.URLError, TimeoutError):
            continue
        for row in parse_results(html):
            if row["url"] in seen:
                continue
            seen.add(row["url"])
            host = urllib.parse.urlparse(row["url"]).hostname or "公开页面"
            found.append(
                {
                    "title": row["title"],
                    "company": host.removeprefix("www."),
                    "location": item["location"],
                    "url": row["url"],
                    "track": item["track"],
                    "summary": row["summary"] or "公开检索结果，打开页面后再核对是否仍在招聘。",
                }
            )
            if len(found) >= limit:
                break
    return found
