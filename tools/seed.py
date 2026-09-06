import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.database import get_connection


companies = [
    ("HSBC", "bank", "UK", "https://www.hsbc.com"),
    ("Barclays", "bank", "UK", "https://home.barclays"),
    ("NatWest Group", "bank", "UK", "https://www.natwestgroup.com"),
    ("Aviva", "insurer", "UK", "https://www.aviva.com"),
    ("Legal & General", "asset_manager", "UK", "https://group.legalandgeneral.com"),
]


def seed_companies():
    conn = get_connection()
    cursor = conn.cursor()

    for name, sector, country, website in companies:

        cursor.execute("""
            INSERT OR IGNORE INTO companies (
                company_name,
                sector,
                hq_country,
                website
            )
            VALUES (?, ?, ?, ?)
        """, (
            name,
            sector,
            country,
            website
        ))

    conn.commit()
    conn.close()

    print("Seed companies added.")


if __name__ == "__main__":
    seed_companies()