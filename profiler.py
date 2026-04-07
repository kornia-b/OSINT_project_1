from datetime import datetime, timezone

from connectors.geo_connector import geocode_city
from connectors.news_connector import fetch_news
from connectors.whois_connector import lookup_domain


def build_profile(entity_name: str, city: str = None, domain: str = None) -> dict:
    location = geocode_city(city) if city else {"city": None, "lat": None, "lon": None}
    news_mentions = fetch_news(entity_name)
    whois_data = lookup_domain(domain) if domain else {}

    return {
        "entity_name": entity_name,
        "location": location,
        "news_mentions": news_mentions,
        "whois_data": whois_data,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
