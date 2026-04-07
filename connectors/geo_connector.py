import requests


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def geocode_city(city: str) -> dict:
    if not city:
        return {"city": None, "lat": None, "lon": None}

    params = {
        "q": city,
        "format": "json",
        "limit": 1,
    }
    headers = {"User-Agent": "OSINT-Entity-Profiler/1.0"}

    try:
        response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        results = response.json()
        if results:
            return {
                "city": city,
                "lat": float(results[0]["lat"]),
                "lon": float(results[0]["lon"]),
            }
        return {"city": city, "lat": None, "lon": None}
    except requests.RequestException as e:
        return {"city": city, "lat": None, "lon": None, "error": str(e)}