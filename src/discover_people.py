import os

from dotenv import load_dotenv
from tavily import TavilyClient

import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.persona_matcher import (
    classify_persona,
    get_persona_priority,
)


load_dotenv()

API_KEY = os.getenv("TAVILY_API_KEY")

# The key is only needed for live research; the demo database works without it.
client = TavilyClient(api_key=API_KEY) if API_KEY else None

def safe_search(client, **kwargs):
    """
    Wrapper around the research API.

    Quota exhaustion, an expired key or a network failure are ordinary
    operating conditions for a research pipeline, not crashes. Returning an
    empty result set lets the run continue and report which accounts are
    missing evidence, rather than dropping a stack trace on the user and
    losing the work already done.
    """
    if client is None:
        raise ValueError("TAVILY_API_KEY not found. Live research needs an API key; the demo database does not.")
    try:
        return client.search(**kwargs)

    except Exception as exc:
        name = type(exc).__name__

        if "Forbidden" in name or "usage limit" in str(exc).lower():
            print(
                "  [research] API quota exhausted - continuing without new "
                "evidence for this step."
            )
        elif "Unauthorized" in name or "401" in str(exc):
            print("  [research] API key rejected. Check TAVILY_API_KEY in .env")
        else:
            print(f"  [research] lookup failed ({name}) - continuing.")

        return {"results": []}



# Ordered by how well the role matches the tier-1 workflows the research
# identified: incident lifecycle, ICT incident classification, DORA
# reporting and audit evidence collection are all IT-adjacent, and the
# accountable individual for them sits in operational resilience or IT ops.
#
# PRIORITY_TITLES run on every account. The rest run only on accounts that
# already score well, because people discovery was 16 of the 22 API credits
# per company - 73% of spend on the least reliable step.
PRIORITY_TITLES = [
    "Director of Operational Resilience",
    "Head of IT Operations",
    "Chief Information Officer",
    "Head of Site Reliability Engineering",
]

SECONDARY_TITLES = [
    "Chief Technology Officer",
    "Head of Infrastructure",
    "Head of Cloud",
    "Head of Technology Operations",
]

TARGET_TITLES = PRIORITY_TITLES + SECONDARY_TITLES


def discover_people(company_name, deep=False):
    people = []

    titles = TARGET_TITLES if deep else PRIORITY_TITLES

    for target_title in titles:

        query = f'''
        "{company_name}" "{target_title}"
        LinkedIn OR company website OR conference
        '''

        response = safe_search(client, 
            query=query,
            search_depth="advanced",
            max_results=5
        )

        for result in response.get("results", []):

            title = result.get("title", "")
            content = result.get("content", "")
            url = result.get("url", "")

            text = f"{title} {content}".lower()

            if company_name.lower() not in text:
                continue

            if target_title.lower() not in text:
                continue

            persona = classify_persona(target_title)
            priority = get_persona_priority(persona)

            people.append({
                "target_title": target_title,
                "persona": persona,
                "priority": priority,
                "source_title": title,
                "source_url": url,
                "content": content[:500],
            })

    return people


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            'Usage: python3 -m src.discover_people '
            '"Company Name"'
        )
        sys.exit(1)

    company = sys.argv[1]

    results = discover_people(company)

    print(f"\nPERSONA DISCOVERY — {company}")
    print("=" * 70)

    print("Matches found:", len(results))

    for person in results:

        print("\nTarget title:", person["target_title"])
        print("Persona:", person["persona"])
        print("Priority:", person["priority"])
        print("Source title:", person["source_title"])
        print("Source:", person["source_url"])
        print("-" * 70)