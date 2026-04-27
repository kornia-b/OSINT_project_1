import os
import re
import json
import time
import requests
from dotenv import load_dotenv

_EMPTY = {
    "executive_summary": "",
    "key_findings": [],
    "associates_identified": [],
    "timeline_highlights": [],
    "investigative_leads": [],
    "confidence_note": "",
    "generated_by": "Gemini 2.5 Flash",
    "error": "none",
}

_PROMPT_TEMPLATE = """You are an intelligence analyst at an Indian law enforcement agency. You have been given aggregated open-source intelligence data about a subject. Analyse this data and produce a structured intelligence brief.

Subject data:
{profile_json}

Produce a JSON response with exactly these fields:

1. executive_summary: A 2-3 sentence professional summary of who this subject is and why they are of interest. No speculation. Only facts from the provided data.

2. key_findings: Array of 3-5 bullet points of the most significant facts. Each string under 20 words.

3. associates_identified: Array of names of other people mentioned in news/Wikipedia who appear connected to the subject. Empty array if none. Extract actual names only.

4. timeline_highlights: Array of significant dated events in format "YYYY: event description". Max 5 items. Order chronologically.

5. investigative_leads: Array of 2-4 concrete next steps an analyst should take. Each should be actionable and specific.

6. confidence_note: One sentence about the reliability of this assessment based on data sources available.

CRITICAL FORMATTING RULES:
- Use only single quotes ' inside string values
- NEVER use double quotes inside string content
- Keep each string value under 250 characters
- Escape any backslashes as \\\\
- Do NOT include line breaks within string values
- Return ONLY valid parseable JSON
- No markdown, no code fences, no commentary"""


def clean_gemini_json(text: str) -> str:
    """Clean Gemini response before JSON parsing."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return text


def extract_fields_with_regex(text: str) -> dict:
    """Last resort field extraction if JSON parsing fails entirely."""
    result = {
        "executive_summary": "",
        "key_findings": [],
        "associates_identified": [],
        "timeline_highlights": [],
        "investigative_leads": [],
        "confidence_note": "Partial parse — some fields may be missing.",
    }

    m = re.search(r'"executive_summary"\s*:\s*"([^"]{0,800})"', text, re.DOTALL)
    if m:
        result["executive_summary"] = m.group(1).strip()

    findings_match = re.search(r'"key_findings"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    if findings_match:
        items = re.findall(r'"([^"]{5,200})"', findings_match.group(1))
        result["key_findings"] = items[:5]

    assoc_match = re.search(r'"associates_identified"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    if assoc_match:
        items = re.findall(r'"([^"]{2,80})"', assoc_match.group(1))
        result["associates_identified"] = items[:10]

    tl_match = re.search(r'"timeline_highlights"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    if tl_match:
        items = re.findall(r'"([^"]{5,200})"', tl_match.group(1))
        result["timeline_highlights"] = items[:7]

    leads_match = re.search(r'"investigative_leads"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    if leads_match:
        items = re.findall(r'"([^"]{5,200})"', leads_match.group(1))
        result["investigative_leads"] = items[:5]

    return result


def _call_gemini(payload: dict, url: str, max_retries: int = 2) -> dict:
    for attempt in range(max_retries + 1):
        try:
            r = requests.post(url, json=payload, timeout=30)
            if r.status_code == 429:
                if attempt < max_retries:
                    time.sleep(5 * (attempt + 1))
                    continue
            r.raise_for_status()
            return r.json()
        except requests.HTTPError:
            if attempt == max_retries:
                raise
    return None


def generate_ai_brief(profile: dict) -> dict:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return dict(_EMPTY, error="missing_api_key", generated_by="Gemini 2.5 Flash")

    trimmed = {
        "entity_name": profile.get("entity_name"),
        "location": profile.get("location"),
        "wikipedia_summary": profile.get("wikipedia_data", {}).get("summary", "")[:1500],
        "news_titles": [
            n.get("title", "")
            for n in profile.get("news_mentions", [])
        ],
        "indian_news_titles": [
            n.get("title", "")
            for n in profile.get("indian_news", [])
        ],
        "court_cases": [
            {"title": c.get("title"), "court": c.get("court"), "date": c.get("date")}
            for c in profile.get("court_data", {}).get("cases_found", [])
        ],
        "whois": profile.get("whois_data", {}),
        "organisations": profile.get("company_data", {}).get("organisations_found", []),
        "risk_assessment": profile.get("risk_assessment", {}),
    }

    prompt = _PROMPT_TEMPLATE.format(profile_json=json.dumps(trimmed, ensure_ascii=False))

    url = (
        "https://generativelanguage.googleapis.com"
        "/v1beta/models/gemini-2.5-flash:generateContent"
        f"?key={api_key}"
    )

    print(f"DEBUG URL: {url[:100]}")

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2000},
    }

    try:
        data = _call_gemini(payload, url)
        text = data["candidates"][0]["content"]["parts"][0]["text"]

        print("=" * 60)
        print("RAW GEMINI RESPONSE:")
        print(text[:2000])
        print("=" * 60)
        print(f"Total length: {len(text)}")
        print(f"Starts with: {text[:50]}")
        print(f"Ends with: {text[-50:]}")
        print("=" * 60)

        try:
            cleaned = clean_gemini_json(text)
            brief = json.loads(cleaned)
            brief["error"] = "none"
        except json.JSONDecodeError:
            brief = extract_fields_with_regex(text)
            brief["error"] = "partial_parse"
            brief["generated_by"] = "Gemini 2.5 Flash (recovered)"

        if "generated_by" not in brief:
            brief["generated_by"] = "Gemini 2.5 Flash"

        return brief

    except Exception as e:
        return dict(_EMPTY, error=f"api_failed: {str(e)[:100]}", generated_by="Gemini 2.5 Flash")
