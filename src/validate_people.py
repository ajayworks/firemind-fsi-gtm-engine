import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.verify_people import build_verification_queue


def is_valid_name(name):
    bad_terms = [
        "hsbc",
        "cio",
        "cto",
        "chief",
        "leading",
        "data",
        "ai",
        "bank",
        "technology",
        "post",
        "profile",
        "linkedin",
        "article",
        "news",
    ]

    name_lower = name.lower()

    # Reject obvious article-title fragments
    if any(term in name_lower for term in bad_terms):
        return False

    # Normal person names should usually be 2–4 words
    word_count = len(name.split())

    if word_count < 2 or word_count > 4:
        return False

    return True


def validate_people(company_name):
    candidates = build_verification_queue(company_name)

    validated = {}

    for candidate in candidates:

        name = candidate["name"]

        if not is_valid_name(name):
            continue

        # Deduplicate by person name
        key = name.lower()

        if key not in validated:
            validated[key] = {
                "name": name,
                "searched_title": candidate["searched_title"],
                "persona": candidate["persona"],
                "priority": candidate["priority"],
                "sources": [
                    {
                        "title": candidate["source_title"],
                        "url": candidate["source_url"],
                    }
                ],
                "status": "candidate_verified",
            }

        else:
            validated[key]["sources"].append({
                "title": candidate["source_title"],
                "url": candidate["source_url"],
            })

    return list(validated.values())


if __name__ == "__main__":
    people = validate_people("HSBC")

    print("\nVALIDATED PEOPLE — HSBC")
    print("=" * 70)

    print("Validated candidates:", len(people))

    for person in people:

        print("\nName:", person["name"])
        print("Searched role:", person["searched_title"])
        print("Persona:", person["persona"])
        print("Priority:", person["priority"])
        print("Supporting sources:", len(person["sources"]))

        for source in person["sources"]:
            print("  -", source["title"])
            print("   ", source["url"])

        print("Status:", person["status"])
        print("-" * 70)