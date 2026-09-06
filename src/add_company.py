import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.database import get_connection
from src.sector_classifier import infer_sector

def normalise_company_name(company_name):
    cleaned = " ".join(
        company_name.strip().split()
    )

    return cleaned

def add_company(
    company_name,
    sector=None,
    hq_country="United Kingdom"
):
    company_name = normalise_company_name(
        company_name
    )

    if sector is None:
        sector = infer_sector(company_name)

    conn = get_connection()
    cursor = conn.cursor()

    # Check whether company already exists
    cursor.execute("""
        SELECT company_id, company_name
        FROM companies
        WHERE LOWER(company_name) = LOWER(?)
    """, (company_name,))

    existing = cursor.fetchone()

    if existing:
        conn.close()

        print(
            f"{existing[1]} already exists "
            f"(company_id={existing[0]})"
        )

        return existing[0]

    # Add new company
    cursor.execute("""
        INSERT INTO companies (
            company_name,
            sector,
            hq_country,
            countries_operated,
            technology_scale_score,
            cloud_score,
            infra_score,
            technical_team_score
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        company_name,
        sector,
        hq_country,
        0,
        0,
        0,
        0,
        0
    ))

    company_id = cursor.lastrowid

    conn.commit()
    conn.close()

    print(
        f"Added {company_name} "
        f"(company_id={company_id})"
    )

    return company_id


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            'Usage: python3 -m src.add_company "Company Name"'
        )
        sys.exit(1)

    company_name = sys.argv[1]

    add_company(company_name)