import argparse
import json
import sys

from dotenv import load_dotenv

from profiler import build_profile

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="OSINT Entity Profiler — aggregate public intelligence on a named entity."
    )
    parser.add_argument("name", help="Full name of the entity to profile")
    parser.add_argument("--city", default=None, help="City associated with the entity")
    parser.add_argument("--domain", default=None, help="Domain name to run WHOIS lookup against")
    parser.add_argument(
        "--indent", type=int, default=2, help="JSON output indentation (default: 2)"
    )
    args = parser.parse_args()

    profile = build_profile(
        entity_name=args.name,
        city=args.city,
        domain=args.domain,
    )
    print(json.dumps(profile, indent=args.indent, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
