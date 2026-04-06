# OSINT Entity Profiler

A Python CLI tool that queries multiple public data sources to generate
a structured intelligence profile for a given entity (person/organization).

Built as a learning project and prototype for a bigger project.

## Modules
- `connectors/news_connector.py` — GNews API
- `connectors/geo_connector.py` — OpenStreetMap Nominatim
- `connectors/whois_connector.py` — WHOIS lookup
- `profiler.py` — Aggregator
- `main.py` — CLI entry point

## Usage
```bash
python main.py --name "Raj Kumar" --city "Mumbai"
```
