import os
import re
import json
import time
import requests
from dotenv import load_dotenv

_PROMPT_TEMPLATE = """You are a query parser for an intelligence platform called Nishk. The platform searches people by name, with optional city, domain, and age filters.

The user said: "{user_query}"

The user's previous searches (for context):
{search_history_summary}

Determine the user's intent and respond with ONLY valid JSON in one of these two formats:

FORMAT A — Single Subject Search:
If the user is asking about a specific person (named or described), respond with:
{{
  "intent": "single_search",
  "name": "extracted person name",
  "city": "extracted city or empty string",
  "domain": "ONLY include if user explicitly mentions a website domain (e.g. tesla.com, example.org). NEVER put job titles, descriptions, or company names here. If no website domain is mentioned, return empty string.",
  "exact_age": null or number,
  "min_age": null or number,
  "max_age": null or number,
  "interpretation": "Brief explanation of what you understood",
  "confidence": "high/medium/low"
}}

FORMAT B — Filter History:
If the user is asking to filter previous searches (e.g. "show high risk searches", "subjects from Mumbai I searched"), respond with:
{{
  "intent": "filter_history",
  "risk_level": "HIGH/MEDIUM/LOW or empty",
  "city_filter": "city or empty",
  "name_contains": "string or empty",
  "interpretation": "Brief explanation",
  "confidence": "high/medium/low"
}}

If you cannot determine intent, respond:
{{
  "intent": "unclear",
  "interpretation": "Why you could not parse",
  "suggestion": "What the user should clarify"
}}

Examples:
"Tell me about Nirav Modi" → {{"intent":"single_search","name":"Nirav Modi","city":"","domain":"","exact_age":null,"min_age":null,"max_age":null,"interpretation":"Direct name lookup","confidence":"high"}}
"the diamond merchant who fled to UK" → {{"intent":"single_search","name":"Nirav Modi","city":"","domain":"","exact_age":null,"min_age":null,"max_age":null,"interpretation":"Likely refers to Nirav Modi based on context","confidence":"medium"}}
"Vijay Mallya check his website kingfisher.com" → {{"intent":"single_search","name":"Vijay Mallya","city":"","domain":"kingfisher.com","exact_age":null,"min_age":null,"max_age":null,"interpretation":"Name with explicit domain","confidence":"high"}}
"show me high risk searches" → {{"intent":"filter_history","risk_level":"HIGH","city_filter":"","name_contains":"","interpretation":"Filter history by HIGH risk","confidence":"high"}}
"my Mumbai searches" → {{"intent":"filter_history","risk_level":"","city_filter":"Mumbai","name_contains":"","interpretation":"Filter history by city Mumbai","confidence":"high"}}
"weather in Delhi" → {{"intent":"unclear","interpretation":"Nishk searches people only","suggestion":"Try: 'Tell me about [person name]'"}}

Return ONLY the JSON. No markdown, no preamble."""

_DOMAIN_RE = re.compile(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z]{2,})+$')


def _validate_domain(domain) -> str:
    if not domain:
        return ""
    domain = str(domain).strip().lower()
    return domain if _DOMAIN_RE.match(domain) else ""


def _validate_city(city) -> str:
    if not city:
        return ""
    city = str(city).strip()
    if any(c.isdigit() for c in city):
        return ""
    if len(city) > 50:
        return ""
    return city


def _validate_age(age):
    if age is None:
        return None
    try:
        age = int(age)
        return age if 0 < age < 120 else None
    except (TypeError, ValueError):
        return None


def _validate(parsed: dict) -> dict:
    if parsed.get("intent") == "single_search":
        parsed["domain"]     = _validate_domain(parsed.get("domain"))
        parsed["city"]       = _validate_city(parsed.get("city"))
        parsed["exact_age"]  = _validate_age(parsed.get("exact_age"))
        parsed["min_age"]    = _validate_age(parsed.get("min_age"))
        parsed["max_age"]    = _validate_age(parsed.get("max_age"))
    return parsed


def parse_nlq(user_query: str, search_history: list = None) -> dict:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return {"intent": "unclear", "error": "missing_api_key", "interpretation": "API key not configured"}

    if search_history:
        history_summary = "\n".join(
            f"- {s.get('name', '')} ({s.get('city', '')})"
            for s in search_history[:5]
        )
    else:
        history_summary = "No previous searches"

    prompt = _PROMPT_TEMPLATE.format(
        user_query=user_query,
        search_history_summary=history_summary,
    )

    url = (
        "https://generativelanguage.googleapis.com"
        "/v1beta/models/gemini-2.5-flash:generateContent"
        f"?key={api_key}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 500},
    }

    for attempt in range(3):
        try:
            r = requests.post(url, json=payload, timeout=20)
            if r.status_code in (429, 503):
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
            r.raise_for_status()
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            return _validate(json.loads(text))

        except Exception as e:
            if attempt == 2:
                return {
                    "intent": "unclear",
                    "error": str(e)[:100],
                    "interpretation": "Service temporarily unavailable. Try again or use the form below.",
                }
