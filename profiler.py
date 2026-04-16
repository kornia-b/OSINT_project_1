from datetime import datetime, timezone

from connectors.geo_connector import geocode_city
from connectors.news_connector import fetch_news
from connectors.whois_connector import lookup_domain
from connectors.wikipedia_connector import lookup_wikipedia
from connectors.indian_news_connector import fetch_indian_news
from connectors.company_connector import fetch_company_data
from connectors.court_connector import fetch_court_data


def resolve_age_filter(exact_age, min_age, max_age) -> tuple[str, str]:
    """
    Returns (age_filter_label, age_query_context).
    Exact age takes full priority over range fields.
    """
    if exact_age is not None:
        return f"exact: {exact_age}", f"age {exact_age}"
    if min_age is not None and max_age is not None:
        return f"range: {min_age}-{max_age}", f"age {min_age} to {max_age}"
    if min_age is not None:
        return f"min only: {min_age}", f"age {min_age}"
    if max_age is not None:
        return f"max only: {max_age}", f"age {max_age}"
    return "none", ""


def build_profile(
    entity_name: str,
    city: str = None,
    domain: str = None,
    exact_age: int = None,
    min_age: int = None,
    max_age: int = None,
    debug: bool = False,
) -> dict:
    age_filter_label, age_query_context = resolve_age_filter(exact_age, min_age, max_age)

    # Append age context to search query so GNews results are age-aware
    search_query = f"{entity_name} {age_query_context}".strip() if age_query_context else entity_name

    location = geocode_city(city) if city else {"city": None, "lat": None, "lon": None}
    news_mentions = fetch_news(search_query)
    whois_data = lookup_domain(domain) if domain else {}
    wikipedia_data = lookup_wikipedia(entity_name)
    indian_news = fetch_indian_news(entity_name, debug=debug)
    wiki_summary = wikipedia_data.get("summary", "") if isinstance(wikipedia_data, dict) else ""
    company_data = fetch_company_data(entity_name, wiki_summary)
    court_data   = fetch_court_data(entity_name)

    return {
        "entity_name": entity_name,
        "location": location,
        "age_filter_applied": age_filter_label,
        "news_mentions": news_mentions,
        "indian_news": indian_news,
        "whois_data": whois_data,
        "wikipedia_data": wikipedia_data,
        "company_data": company_data,
        "court_data":   court_data,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
