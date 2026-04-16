import os
import sys

import feedparser
import requests

SOURCES = [
    {
        "name": "The Hindu",
        "badge": "Hindu",
        "url": "https://www.thehindu.com/news/national/feeder/default.rss",
    },
    {
        "name": "NDTV",
        "badge": "NDTV",
        "url": "https://feeds.feedburner.com/ndtvnews-top-stories",
    },
    {
        "name": "Indian Express",
        "badge": "IE",
        "url": "https://indianexpress.com/feed/",
    },
    {
        "name": "Hindustan Times",
        "badge": "HT",
        "url": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
    },
]

# NewsAPI country-filtered Indian sources used as fallback
NEWSAPI_URL = "https://newsapi.org/v2/everything"
NEWSAPI_INDIAN_DOMAINS = "thehindu.com,ndtv.com,indianexpress.com,hindustantimes.com"

MAX_PER_SOURCE = 5


def _parse_published(entry) -> str:
    for attr in ("published", "updated"):
        value = getattr(entry, attr, None)
        if value:
            return value
    return ""



def _fetch_rss(entity_name: str, debug: bool) -> tuple[list[dict], list[str]]:
    """
    Fetch and filter RSS feeds. Returns (results, failed_source_names).
    feedparser never raises on HTTP failure — we must inspect feed.status
    and feed.bozo ourselves.
    """
    results = []
    failed = []

    for source in SOURCES:
        try:
            feed = feedparser.parse(source["url"])

            # feedparser sets bozo=True for malformed feeds and swallows HTTP
            # errors silently — check status explicitly when available.
            status = getattr(feed, "status", None)
            total = len(feed.entries)

            if debug:
                print(
                    f"[indian_news] {source['badge']:6s}  status={status}  "
                    f"entries={total}  bozo={feed.bozo}",
                    file=sys.stderr,
                )

            if status is not None and status not in (200, 301, 302):
                failed.append(source["name"])
                continue

            if total == 0:
                failed.append(source["name"])
                continue

            name_parts = [w for w in entity_name.split() if len(w) >= 4] or [entity_name]
            matched = 0
            for entry in feed.entries:
                if matched >= MAX_PER_SOURCE:
                    break
                title = (getattr(entry, "title", "") or "").strip()
                description = (getattr(entry, "summary", "") or getattr(entry, "description", "") or "")
                if debug:
                    print(f"[indian_news] Checking: {title[:60]}", file=sys.stderr)
                haystack = (title + " " + description).lower()
                if len(name_parts) >= 2:
                    match = all(part.lower() in haystack for part in name_parts)
                else:
                    match = any(part.lower() in haystack for part in name_parts)
                if not match:
                    continue
                if debug:
                    print(f"[indian_news] Match found: {title[:60]}", file=sys.stderr)
                results.append(
                    {
                        "title": title,
                        "source": source["name"],
                        "badge": source["badge"],
                        "url": getattr(entry, "link", ""),
                        "published_at": _parse_published(entry),
                    }
                )
                matched += 1

            if debug:
                print(f"[indian_news] Total matches from {source['name']}: {matched}", file=sys.stderr)

        except Exception as e:
            if debug:
                print(
                    f"[indian_news] {source['badge']:6s}  exception: {e}",
                    file=sys.stderr,
                )
            failed.append(source["name"])

    return results, failed


def _fetch_newsapi_fallback(entity_name: str, debug: bool) -> list[dict]:
    """
    Fallback to NewsAPI.org when RSS feeds are unavailable.
    Requires NEWS_API_KEY in environment.
    """
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        if debug:
            print("[indian_news] NewsAPI fallback skipped — NEWS_API_KEY not set", file=sys.stderr)
        return [{"error": "RSS feeds unavailable and NEWS_API_KEY not set for fallback."}]

    params = {
        "q": entity_name,
        "domains": NEWSAPI_INDIAN_DOMAINS,
        "language": "en",
        "pageSize": 10,
        "apiKey": api_key,
    }

    try:
        response = requests.get(NEWSAPI_URL, params=params, timeout=10)
        response.raise_for_status()
        articles = response.json().get("articles", [])

        if debug:
            print(f"[indian_news] NewsAPI fallback returned {len(articles)} article(s)", file=sys.stderr)

        return [
            {
                "title": a.get("title", "").strip(),
                "source": a.get("source", {}).get("name", "NewsAPI"),
                "badge": "API",
                "url": a.get("url", ""),
                "published_at": (a.get("publishedAt") or "")[:10],
            }
            for a in articles
        ]
    except requests.RequestException as e:
        if debug:
            print(f"[indian_news] NewsAPI fallback error: {e}", file=sys.stderr)
        return [{"error": f"NewsAPI fallback failed: {e}"}]


def fetch_indian_news(entity_name: str, debug: bool = False) -> list[dict]:
    results, failed = _fetch_rss(entity_name, debug)

    # Fall back to NewsAPI only when every RSS source failed
    if len(failed) == len(SOURCES):
        if debug:
            print("[indian_news] All RSS feeds failed — using NewsAPI fallback", file=sys.stderr)
        return _fetch_newsapi_fallback(entity_name, debug)

    return results
