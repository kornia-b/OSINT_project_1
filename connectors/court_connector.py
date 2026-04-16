import os
import re
from datetime import datetime, timezone

import requests

SEARCH_URL = "https://api.indiankanoon.org/search/"
TIMEOUT = 10
MAX_RESULTS = 5

DOC_TYPE_MAP = {
    "1001": "Supreme Court Order",
    "1004": "High Court Judgment",
    "1198": "Tribunal Order",
    "1010": "District Court Order",
}

DATE_IN_TITLE = re.compile(r'on (\d{1,2} \w+,? \d{4})', re.IGNORECASE)


def _strip_html(text) -> str:
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', '', str(text))
    return re.sub(r'\s+', ' ', clean).strip()


CRIMINAL_KEYWORDS = {
    "criminal", "fraud", "cheating", "corruption",
    "money laundering", "pmla", "cbi",
}
BAIL_KEYWORD = "bail"


def _flag_title(title: str) -> list[str]:
    t = title.lower()
    flags = []
    if any(kw in t for kw in CRIMINAL_KEYWORDS):
        flags.append("Active criminal case found")
    if BAIL_KEYWORD in t:
        flags.append("Bail application found")
    return flags


def _is_recent(date_str: str) -> bool:
    """Return True if date_str is within the last 2 years."""
    if not date_str:
        return False
    for fmt in ("%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%Y"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            return (now - dt).days <= 730
        except ValueError:
            continue
    return False


def fetch_court_data(entity_name: str) -> dict:
    api_key = os.getenv("INDIAN_KANOON_API_KEY", "").strip()
    if not api_key:
        return {
            "error": "missing_api_key",
            "cases_found": [],
            "total_found": 0,
            "flags": [],
        }

    headers = {
        "User-Agent": "OSINT-Profiler/1.0",
        "Authorization": "Token " + api_key,
    }

    try:
        r = requests.post(
            SEARCH_URL,
            data={"formInput": entity_name, "pagenum": 0},
            headers=headers,
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        return {
            "error": "request_failed",
            "cases_found": [],
            "total_found": 0,
            "flags": [],
        }

    if r.status_code == 429:
        return {
            "error": "rate_limited",
            "cases_found": [],
            "total_found": 0,
            "flags": [],
        }

    try:
        r.raise_for_status()
        data = r.json()
    except Exception:
        return {
            "error": "request_failed",
            "cases_found": [],
            "total_found": 0,
            "flags": [],
        }

    docs = data.get("docs", [])[:MAX_RESULTS]
    cases_found = []
    for doc in docs:
        title     = _strip_html(doc.get("title")    or "")
        court     = _strip_html(doc.get("docsource") or "")
        headline  = _strip_html(doc.get("headline")  or "")
        summary   = headline[:150] + ("…" if len(headline) > 150 else "")

        # Date: prefer explicit field, fall back to extracting from title
        date = str(doc.get("date") or "").strip()
        if not date:
            m = DATE_IN_TITLE.search(title)
            date = m.group(1) if m else ""

        # doc_type: numeric codes → human-readable label
        doc_type = DOC_TYPE_MAP.get(
            str(doc.get("doctype") or ""),
            "Court Document",
        )

        cits     = doc.get("citations") or []
        citation = str(cits[0]) if cits else ""
        tid      = doc.get("tid") or ""
        url      = "https://indiankanoon.org/doc/" + str(tid) + "/" if tid else ""

        cases_found.append({
            "title":     title,
            "court":     court,
            "date":      date,
            "doc_type":  doc_type,
            "citation":  citation,
            "summary":   summary,
            "url":       url,
        })

    # ── Auto-flags ────────────────────────────────────────────────────────────
    flags_set: set[str] = set()
    courts_seen: set[str] = set()

    for case in cases_found:
        for flag in _flag_title(case["title"]):
            flags_set.add(flag)
        if case["court"]:
            courts_seen.add(case["court"])
        if _is_recent(case["date"]):
            flags_set.add("Recent filing")

    if len(courts_seen) >= 3:
        flags_set.add("Multiple courts")

    if not cases_found:
        return {
            "error": "none",
            "cases_found": [],
            "total_found": 0,
            "flags": [],
        }

    return {
        "error": "none",
        "cases_found": cases_found,
        "total_found": len(cases_found),
        "flags": sorted(flags_set),
    }
