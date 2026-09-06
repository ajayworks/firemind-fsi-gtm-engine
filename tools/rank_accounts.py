import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.database import get_connection


def rank_accounts():
    conn = get_connection()
    conn.row_factory = __import__("sqlite3").Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.company_name,
            c.sector,
            s.scale_score,
            s.technology_score,
            s.operational_pain_score,
            s.use_case_fit_score,
            s.timing_score,
            s.total_score,
            s.tier,
            s.recommended_use_case,
            s.confidence
        FROM companies c
        JOIN account_scores s
            ON c.company_id = s.company_id
        ORDER BY s.total_score DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    print("\nFIREMIND FSI ACCOUNT RANKING")
    print("=" * 100)

    rank = 1

    for row in rows:
        print(
            f'{rank}. {row["company_name"]}'
            f' | Score: {row["total_score"]}'
            f' | Tier: {row["tier"]}'
            f' | Use case: {row["recommended_use_case"]}'
            f' | Confidence: {row["confidence"]}'
        )

        print(
            f'   Scale {row["scale_score"]}/15'
            f' | Technology {row["technology_score"]}/25'
            f' | Pain {row["operational_pain_score"]}/25'
            f' | Use-case {row["use_case_fit_score"]}/25'
            f' | Timing {row["timing_score"]}/10'
        )

        print("-" * 100)

        rank += 1


if __name__ == "__main__":
    rank_accounts()