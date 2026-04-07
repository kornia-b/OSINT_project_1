import os
import requests


GNEWS_API_URL = "https://gnews.io/api/v4/search"


def fetch_news(entity_name: str, max_results: int = 5) -> list[dict]:
    api_key = os.getenv("GNEWS_API_KEY")
    if not api_key:
        return [{"error": "GNEWS_API_KEY not set in environment"}]

    params = {
        "q": entity_name,
        "lang": "en",
        "max": max_results,
        "token": api_key,
    }

    try:
        response = requests.get(GNEWS_API_URL, params=params, timeout=10)
        response.raise_for_status()
        articles = response.json().get("articles", [])
        return [
            {
                "title": a.get("title"),
                "description": a.get("description"),
                "url": a.get("url"),
                "published_at": a.get("publishedAt"),
                "source": a.get("source", {}).get("name"),
            }
            for a in articles
        ]
    except requests.RequestException as e:
        return [{"error": str(e)}]