import re

import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.discover_people import discover_people

def extract_name(source_title, company_name):
    company = re.escape(company_name)

    name_pattern = (
        r"([A-Z][A-Za-z'’-]+"
        r"(?:\s+[A-Z][A-Za-z'’-]+){1,3})"
    )

    patterns = [
        # Company appoints <name> as <title> ...
        rf"{company}\s+(?:appoints|appointed|names|named|announces)\s+"
        rf"{name_pattern}\s+as\b",

        # Company names <name> as <title> ...
        rf"{company}\s+(?:names|appoints|announces)\s+"
        rf"{name_pattern}\s+as\b",

        # <name> - <title> | LinkedIn
        rf"^{name_pattern}\s+[–—-]\s+",

        # <name> | Senior management | <company>
        rf"^{name_pattern}\s*\|",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            source_title,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip().title()

    return None


def build_verification_queue(company_name):
    results = discover_people(company_name)

    candidates = []

    for result in results:
        name = extract_name(result["source_title"],company_name)

        # If we cannot confidently identify a person's name,
        # don't allow it into the candidate list.
        if not name:
            continue

        candidates.append({
            "name": name,
            "searched_title": result["target_title"],
            "persona": result["persona"],
            "priority": result["priority"],
            "source_title": result["source_title"],
            "source_url": result["source_url"],
            "status": "needs_review",
        })

    return candidates


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            'Usage: python3 -m src.verify_people '
            '"Company Name"'
        )
        sys.exit(1)

    company = sys.argv[1]

    candidates = build_verification_queue(company)

    print(f"\nPEOPLE VERIFICATION QUEUE — {company}")
    print("=" * 70)

    print("Candidates:", len(candidates))

    for person in candidates:
        print("\nName:", person["name"])
        print("Searched role:", person["searched_title"])
        print("Persona:", person["persona"])
        print("Priority:", person["priority"])
        print("Source:", person["source_title"])
        print("URL:", person["source_url"])
        print("Status:", person["status"])
        print("-" * 70)