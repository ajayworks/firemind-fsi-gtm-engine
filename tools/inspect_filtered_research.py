import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.web_research import research_company
from src.filter_results import classify_result, is_company_specific


def inspect_filtered_research(company_name):
    results = research_company(
        company_name,
        refresh=False
    )

    print()
    print(f"FILTER INSPECTION — {company_name}")
    print("=" * 80)

    for index, result in enumerate(results, start=1):

        title = result.get("title", "")
        content = result.get("content", "")

        company_specific = is_company_specific(
            result,
            company_name
        )

        matches = classify_result(result)

        print()
        print(f"RESULT {index}")
        print("-" * 80)

        print("Title:")
        print(title)

        print()
        print("Company specific:")
        print(company_specific)

        print()
        print("Detected signal matches:")
        print(matches)

        print()
        print("WOULD PASS FILTER:")
        print(
            company_specific and bool(matches)
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            'Usage: python3 -m src.inspect_filtered_research '
            '"Company Name"'
        )
        sys.exit(1)

    inspect_filtered_research(sys.argv[1])