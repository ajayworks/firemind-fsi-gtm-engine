import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.web_research import research_company


def inspect_raw_research(company_name):
    print()
    print(f"RAW RESEARCH — {company_name}")
    print("=" * 80)

    results = research_company(
        company_name,
        refresh=False
    )

    if not results:
        print("No research results found.")
        return

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

        content = result.get(
            "content",
            ""
        )

        print()
        print("Content:")
        print(content[:1000])

        print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            'Usage: python3 -m src.inspect_raw_research '
            '"Company Name"'
        )
        sys.exit(1)

    company_name = sys.argv[1]

    inspect_raw_research(company_name)