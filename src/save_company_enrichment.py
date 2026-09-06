import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.database import get_connection
from src.company_enrichment import find_employee_count
from src.geography_enrichment import find_countries_operated

def choose_employee_count(company_name):
    candidates = find_employee_count(company_name)

    if not candidates:
        return None

    # Keep only realistic group-level counts
    plausible = [
        c for c in candidates
        if 1000 <= c["employee_count"] <= 500000
    ]

    if not plausible:
        return None

    # Highest source priority first
    best_priority = max(
        c["source_priority"]
        for c in plausible
    )

    top_candidates = [
        c for c in plausible
        if c["source_priority"] == best_priority
    ]

    # If multiple values come from the same strong source class,
    # use the median-ish middle value to reduce noise.
    top_candidates.sort(
        key=lambda x: x["employee_count"]
    )

    best = top_candidates[
        len(top_candidates) // 2
    ]

    return best


def save_employee_count(company_name):
    best = choose_employee_count(company_name)

    if not best:
        print("No reliable employee count found.")
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE companies
        SET employee_count = ?
        WHERE company_name = ?
    """, (
        best["employee_count"],
        company_name
    ))

    cursor.execute("""
        INSERT INTO sources (
            source_type,
            source_title,
            url,
            publisher,
            snippet,
            reliability
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        "company_enrichment",
        best["source_title"],
        best["source_url"],
        None,
        f'Employee count evidence: {best["employee_count"]}',
        best["source_type"]
    ))

    conn.commit()
    conn.close()

    print(f'\nSaved employee count for {company_name}')
    print("Employees:", best["employee_count"])
    print("Source type:", best["source_type"])
    print("Source:", best["source_title"])
    print("URL:", best["source_url"])


if __name__ == "__main__":
    save_employee_count("Barclays")

def save_geography(company_name):
    result = find_countries_operated(company_name)

    if not result:
        print(
            f"No reliable geographic footprint found for {company_name}."
        )
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE companies
        SET countries_operated = ?
        WHERE company_name = ?
    """, (
        result["countries_operated"],
        company_name
    ))

    cursor.execute("""
        INSERT INTO sources (
            source_type,
            source_title,
            url,
            reliability
        )
        VALUES (?, ?, ?, ?)
    """, (
        "company_website",
        result["title"],
        result["url"],
        "high"
    ))

    conn.commit()
    conn.close()

    print(
        f"Saved geographic reach for {company_name}"
    )

    print(
        "Markets/countries:",
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