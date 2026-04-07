import whois


def lookup_domain(domain: str) -> dict:
    if not domain:
        return {}

    try:
        w = whois.whois(domain)
        # whois returns an object; serialize relevant fields
        result = {}
        for key in ("domain_name", "registrar", "creation_date", "expiration_date",
                    "updated_date", "name_servers", "emails", "org", "country"):
            value = getattr(w, key, None)
            if value is None:
                continue
            # Convert lists/dates to strings for JSON serialization
            if isinstance(value, list):
                result[key] = [str(v) for v in value]
            else:
                result[key] = str(value)
        return result
    except Exception as e:
        return {"error": str(e)}