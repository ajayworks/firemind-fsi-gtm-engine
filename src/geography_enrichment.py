

def safe_search(client, **kwargs):
    """
    Wrapper around the research API.

    Quota exhaustion, an expired key or a network failure are ordinary
    operating conditions for a research pipeline, not crashes. Returning an
    empty result set lets the run continue and report which accounts are
    missing evidence, rather than dropping a stack trace on the user and
    losing the work already done.
    """
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

import re

import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.web_research import client


def find_countries_operated(company_name):
    query = (
        f'"{company_name}" global footprint '
        f'operates in countries markets annual report'
    )

    response = safe_search(client, 
        query=query,
        search_depth="advanced",
        max_results=8
    )

    results = response.get("results", [])

    patterns = [
        r"operates in\s+(?:over\s+)?(\d+)\+?\s+(?:countries|markets)",
        r"operating in\s+(?:over\s+)?(\d+)\+?\s+(?:countries|markets)",
        r"present in\s+(?:over\s+)?(\d+)\+?\s+(?:countries|markets)",
        r"presence in\s+(?:over\s+)?(\d+)\+?\s+(?:countries|markets)",
        r"across\s+(?:over\s+)?(\d+)\+?\s+(?:countries|markets)",
        r"spans\s+(?:over\s+)?(\d+)\+?\s+(?:countries|markets)",
        r"footprint (?:in|across)\s+(?:over\s+)?(\d+)\+?\s+(?:countries|markets)",
        r"network (?:in|across)\s+(?:over\s+)?(\d+)\+?\s+(?:countries|markets)",
        r"serves clients in\s+(?:over\s+)?(\d+)\+?\s+(?:countries|markets)",
    ]

    candidates = []

    for result in results:
        title = result.get("title", "")
        content = result.get("content", "")
        url = result.get("url", "")

        text = f"{title} {content}".lower()

        for pattern in patterns:
            match = re.search(pattern, text)

            if match:
                countries = int(match.group(1))

                if 1 <= countries <= 250:
                    candidates.append({
                        "countries_operated": countries,
                        "title": title,
                        "url": url,
                    })

    if not candidates:
        return None

    # Group results by detected country count
    counts = {}

    for item in candidates:
        number = item["countries_operated"]

        if number not in counts:
            counts[number] = []

        counts[number].append(item)

    # Prefer the number supported by the most results
    best_number = max(
        counts,
        key=lambda number: (
            len(counts[number]),
            number
        )
    )

    return counts[best_number][0]


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            'Usage: python3 -m src.geography_enrichment '
            '"Company Name"'
        )
        sys.exit(1)

    company_name = sys.argv[1]

    result = find_countries_operated(company_name)

    print()
    print(f"GEOGRAPHY ENRICHMENT — {company_name}")
    print("=" * 70)

    if result:
        print(
            "Countries operated:",
            result["countries_operated"]
        )

        print(
            "Source:",
            result["title"]
        )

        print(
            "URL:",
            result["url"]
        )

    else:
        print(
            "No reliable geographic footprint found."
        )