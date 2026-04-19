def calculate_risk(profile):
    score = 0
    flags = []
    evidence = []

    # --- COURT RECORDS (highest weight) ---
    cases = profile.get("court_data", {}).get("cases_found", [])
    court_flags = profile.get("court_data", {}).get("flags", [])

    criminal_case_keywords = [
        "fraud", "cheating", "corruption",
        "laundering", "criminal", "pmla",
        "cbi", "enforcement directorate",
        "embezzlement", "forgery", "scam",
        "cheated", "bail", "extradition",
        "income tax", "tax evasion",
        "black money", "economic offence",
        "fera", "fema", "hawala",
        "proceeds of crime", "attachment"
    ]

    criminal_courts = [
        "cbi", "special court", "cbi special",
        "economic offences", "pmla"
    ]

    criminal_cases = []
    civil_cases = []

    for case in cases:
        title   = (case.get("title")   or "").lower()
        summary = (case.get("summary") or "").lower()
        court   = (case.get("court")   or "").lower()
        combined = title + " " + summary + " " + court

        is_criminal = (
            any(k in combined for k in criminal_case_keywords)
            or any(c in court for c in criminal_courts)
        )

        if is_criminal:
            criminal_cases.append(case)
        else:
            civil_cases.append(case)

    if len(criminal_cases) >= 3:
        score += 40
        flags.append("MULTIPLE CRIMINAL CASES")
        evidence.append(f"{len(criminal_cases)} criminal cases found")
    elif len(criminal_cases) >= 1:
        score += 25
        flags.append("CRIMINAL CASE FOUND")
        evidence.append(f"{len(criminal_cases)} criminal case found")

    if civil_cases:
        evidence.append(f"{len(civil_cases)} civil/corporate case(s) (not scored)")

    if len(criminal_cases) >= 2 and "Multiple courts" in court_flags:
        score += 15
        flags.append("MULTIPLE CRIMINAL JURISDICTIONS")
        evidence.append("Criminal cases span multiple courts")

    # --- NEWS ANALYSIS (medium weight) ---
    news = profile.get("news_mentions", [])
    news_text = " ".join([
        (n.get("title", "") + " " + n.get("description", ""))
        for n in news
    ]).lower()

    criminal_keywords = [
        "fraud", "scam", "arrested", "convicted",
        "laundering", "corruption", "cheating",
        "embezzlement", "fugitive", "accused",
        "criminal", "fir", "cbi", "ed ", "pmla",
        "extradition", "bail", "charge sheet"
    ]

    keyword_hits = [k for k in criminal_keywords if k in news_text]

    if len(keyword_hits) >= 3:
        score += 30
        flags.append("CRIMINAL NEWS COVERAGE")
        evidence.append(f"Keywords found: {', '.join(keyword_hits[:3])}")
    elif len(keyword_hits) >= 2:
        score += 20
        flags.append("SUSPICIOUS NEWS COVERAGE")
        evidence.append(f"Keywords found: {', '.join(keyword_hits)}")
    elif len(keyword_hits) >= 1:
        score += 10
        evidence.append(f"News keyword found: {keyword_hits[0]}")

    # --- WHOIS ANALYSIS (medium weight) ---
    whois = profile.get("whois_data", {})

    if whois:
        org = str(whois.get("org") or "").lower()
        country = str(whois.get("country") or "").upper()

        privacy_indicators = [
            "proxy", "privacy", "redacted",
            "whoisguard", "domains by proxy",
            "perfect privacy"
        ]

        offshore_countries = ["VG", "KY", "MU", "SC", "PA", "IM", "JE", "BZ", "IS"]

        if any(p in org for p in privacy_indicators):
            score += 8
            flags.append("PRIVACY PROTECTED DOMAIN")
            evidence.append("Domain ownership concealed via proxy")

        if country in offshore_countries:
            score += 20
            flags.append("OFFSHORE DOMAIN")
            evidence.append(f"Domain registered in {country} — offshore jurisdiction")

        if country not in ["IN", ""] and country:
            evidence.append(f"Domain registered outside India ({country})")

    # --- WIKIPEDIA ANALYSIS (low weight) ---
    wiki = profile.get("wikipedia_data", {})

    if wiki.get("found"):
        wiki_text = (wiki.get("summary") or "").lower()
        wiki_keywords = [
            "fraud", "convicted", "arrested",
            "fugitive", "scam", "corruption",
            "laundering", "criminal", "accused",
            "charged", "embezzlement", "cheating"
        ]
        wiki_hits = [k for k in wiki_keywords if k in wiki_text]
        if len(wiki_hits) >= 3:
            score += 25
            flags.append("CRIMINAL WIKIPEDIA PROFILE")
            evidence.append(f"Wikipedia mentions: {', '.join(wiki_hits[:4])}")
        elif len(wiki_hits) >= 1:
            score += 10
            evidence.append(f"Wikipedia mentions: {', '.join(wiki_hits)}")

    # --- ORGANISATION ANALYSIS (low weight) ---
    companies = profile.get("company_data", {}).get("organisations_found", [])

    if len(companies) >= 5:
        score += 10
        flags.append("HIGH ORGANISATION COUNT")
        evidence.append(f"Linked to {len(companies)} organisations")

    # --- CALCULATE FINAL RISK LEVEL ---
    score = max(0, min(score, 100))

    if score >= 60:
        risk_level = "HIGH"
        risk_colour = "#ff5252"
        risk_emoji = "🔴"
    elif score >= 30:
        risk_level = "MEDIUM"
        risk_colour = "#ffab40"
        risk_emoji = "🟡"
    else:
        risk_level = "LOW"
        risk_colour = "#69f0ae"
        risk_emoji = "🟢"

    return {
        "risk_level": risk_level,
        "risk_score": score,
        "risk_colour": risk_colour,
        "risk_emoji": risk_emoji,
        "flags": flags,
        "evidence": evidence,
    }
