import re

import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.validate_people import validate_people


TITLE_PATTERNS = [
    r"chief technology officer",
    r"\bcto\b",

    r"chief information officer",
    r"\bcio\b",

    r"chief ai officer",

    r"head of infrastructure",
    r"head of cloud strategy and transformation",
    r"head of cloud",
    r"head of it operations",
    r"head of technology operations",
    r"head of site reliability engineering",
    r"director of operational resilience",
]


def extract_actual_title(source_title):
    text = source_title.lower()

    for pattern in TITLE_PATTERNS:
        match = re.search(pattern, text)

        if match:
            title = match.group(0).lower()

            if title == "cto":
                return "Chief Technology Officer"

            if title == "cio":
                return "Chief Information Officer"

            return title.title()

    return None


def enrich_people(company_name):
    people = validate_people(company_name)

    enriched = []

    for person in people:
        actual_title = None

        for source in person["sources"]:
            found_title = extract_actual_title(
                source["title"]
            )

            if found_title:
                actual_title = found_title
                break

        enriched.append({
            "name": person["name"],
            "searched_title": person["searched_title"],
            "actual_title": actual_title,
            "persona": person["persona"],
            "priority": person["priority"],
            "sources": person["sources"],
            "status": (
                "title_verified"
                if actual_title
                else "needs_manual_title_review"
            ),
        })

    return enriched


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            'Usage: python3 -m src.extract_actual_titles '
            '"Company Name"'
        )
        sys.exit(1)

    company = sys.argv[1]

    people = enrich_people(company)

    print(f"\nENRICHED PEOPLE — {company}")
    print("=" * 70)

    for person in people:
        print("\nName:", person["name"])
        print("Searched title:", person["searched_title"])
        print("Actual title:", person["actual_title"])
        print("Persona:", person["persona"])
        print("Priority:", person["priority"])
        print("Status:", person["status"])

        for source in person["sources"]:
            print(" -", source["title"])
            print("  ", source["url"])

        print("-" * 70)