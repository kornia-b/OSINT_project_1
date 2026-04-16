import re


def fetch_company_data(entity_name: str, wikipedia_summary: str = "") -> dict:
    if not wikipedia_summary:
        return {
            "organisations_found": [],
            "total_found": 0,
            "source": "wikipedia_extraction",
            "error": "no_wikipedia_summary",
        }

    org_indicators = [
        "Limited", "Ltd", "Bank", "Corporation",
        "Corp", "Industries", "Enterprises",
        "Foundation", "Institute", "University",
        "Ministry", "Department", "Commission",
        "Holdings", "Group", "International",
        "National", "Federal", "Reserve",
        "Exchange", "Association", "Council",
    ]

    sentences = wikipedia_summary.split(".")
    organisations = []

    for sentence in sentences:
        for indicator in org_indicators:
            pattern = r'([A-Z][a-zA-Z\s]+' + indicator + r')'
            matches = re.findall(pattern, sentence)
            for match in matches:
                match = match.strip()
                if 5 < len(match) < 60 and match not in organisations:
                    organisations.append(match)

    found = organisations[:8]
    return {
        "organisations_found": found,
        "total_found": len(found),
        "source": "wikipedia_extraction",
        "error": "none",
    }
