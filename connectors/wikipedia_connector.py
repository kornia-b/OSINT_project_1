import requests

WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"


def lookup_wikipedia(entity_name: str) -> dict:
    slug = entity_name.strip().replace(" ", "_")
    url = WIKI_SUMMARY_URL.format(slug)
    headers = {"User-Agent": "OSINT-Entity-Profiler/1.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 404:
            return {"found": False}

        response.raise_for_status()
        data = response.json()

        # The REST summary endpoint does not expose categories or aliases
        # directly, but does expose titles (redirects/aliases via "titles.normalized")
        aliases = []
        titles = data.get("titles", {})
        normalized = titles.get("normalized")
        if normalized and normalized != entity_name:
            aliases.append(normalized)

        thumbnail = ""
        if data.get("thumbnail"):
            thumbnail = data["thumbnail"].get("source", "")
        # Fall back to originalimage if thumbnail is absent
        if not thumbnail and data.get("originalimage"):
            thumbnail = data["originalimage"].get("source", "")

        return {
            "found": True,
            "summary": data.get("extract", ""),
            "aliases": aliases,
            "categories": [],          # not available from summary endpoint
            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "thumbnail": thumbnail,
        }

    except requests.RequestException as e:
        return {"found": False, "error": str(e)}
