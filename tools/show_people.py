import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.database import get_connection
from src.persona_matcher import persona_fit_for_use_case


def show_people(company_name):
    conn = get_connection()
    conn.row_factory = __import__("sqlite3").Row
    cursor = conn.cursor()

    # Get latest recommended use case
    cursor.execute("""
        SELECT recommended_use_case
        FROM account_scores
        WHERE company_id = (
            SELECT company_id
            FROM companies
            WHERE company_name = ?
        )
        ORDER BY calculated_at DESC
        LIMIT 1
    """, (company_name,))

    score_row = cursor.fetchone()

    if not score_row:
        print("No account score found.")
        conn.close()
        return

    recommended_use_case = score_row["recommended_use_case"]

    # Get people
    cursor.execute("""
        SELECT
            full_name,
            job_title,
            persona_type,
            priority,
            linkedin_url
        FROM people
        WHERE company_id = (
            SELECT company_id
            FROM companies
            WHERE company_name = ?
        )
    """, (company_name,))

    rows = cursor.fetchall()
    conn.close()

    ranked = []

    for row in rows:
        use_case_fit = persona_fit_for_use_case(
            row["persona_type"],
            recommended_use_case
        )

        total_priority = (
            row["priority"] * 2
            + use_case_fit
        )

        ranked.append({
            "name": row["full_name"],
            "title": row["job_title"],
            "persona": row["persona_type"],
            "priority": row["priority"],
            "use_case_fit": use_case_fit,
            "total_priority": total_priority,
            "linkedin": row["linkedin_url"],
        })

    ranked.sort(
        key=lambda x: x["total_priority"],
        reverse=True
    )

    print(f"\nPEOPLE — {company_name}")
    print("=" * 70)
    print("Recommended use case:", recommended_use_case)

    for person in ranked:
        print("\nName:", person["name"])
        print("Title:", person["title"])
        print("Persona:", person["persona"])
        print("Priority:", person["priority"])
        print("Use-case fit:", person["use_case_fit"])
        print("Total priority:", person["total_priority"])
        print("LinkedIn:", person["linkedin"])
        print("-" * 70)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            'Usage: python3 -m src.show_people '
            '"Company Name"'
        )
        sys.exit(1)

    company_name = sys.argv[1]

    show_people(company_name)