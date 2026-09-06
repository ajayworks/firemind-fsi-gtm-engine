import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.database import get_connection


def show_accounts():
    conn = get_connection()
    conn.row_factory = __import__("sqlite3").Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.company_name,
            c.sector,
            s.total_score,
            s.tier,
            s.recommended_use_case,
            s.confidence
        FROM companies c
        LEFT JOIN account_scores s
            ON c.company_id = s.company_id
        ORDER BY s.total_score DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    print("\nFIREMIND FSI GTM ENGINE")
    print("-" * 70)

    for row in rows:
        print(
            row["company_name"],
            "|",
            row["sector"],
            "| Score:",
            row["total_score"],
            "| Tier:",
            row["tier"],
            "| Use case:",
            row["recommended_use_case"],
            "| Confidence:",
            row["confidence"]
        )


if __name__ == "__main__":
    show_accounts()