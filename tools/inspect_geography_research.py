import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.web_research import client


def inspect_geography_research(company_name):
    query = (
        f'"{company_name}" global footprint '
        f'operates in countries markets annual report'
    )

    response = client.search(
        query=query,
        search_depth="advanced",
        max_results=8
    )

    results = response.get("results", [])

    print()
    print(f"GEOGRAPHY RAW RESEARCH — {company_name}")
    print("=" * 80)

    for index, result in enumerate(results, start=1):
        print()
        print(f"RESULT {index}")
        print("-" * 80)

        print(
            "Title:",
            result.get("title", "")
        )

        print(
            "URL:",
            result.get("url", "")
        )

        print()
        print("Content:")

        content = result.get(
            "content",
            ""
        )

        print(content[:1500])


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            'Usage: python3 -m src.inspect_geography_research '
            '"Company Name"'
        )
        sys.exit(1)

    inspect_geography_research(sys.argv[1])