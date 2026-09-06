import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.database import get_connection


def show_research(company_name):
    conn = get_connection()
    conn.row_factory = __import__("sqlite3").Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.company_name,
            s.signal_type,
            s.signal_title,
            s.signal_description,
            s.signal_strength,
            s.confidence,
            s.suggested_use_case,
            src.source_title,
            src.publisher,
            src.url,
            src.published_date,
            src.reliability
        FROM signals s
        JOIN companies c
            ON s.company_id = c.company_id
        LEFT JOIN sources src
            ON s.source_id = src.source_id
        WHERE c.company_name = ?
        ORDER BY s.signal_date DESC
    """, (company_name,))

    rows = cursor.fetchall()
    conn.close()

    print(f"\nRESEARCH EVIDENCE — {company_name}")
    print("=" * 70)

    if not rows:
        print("No research found.")
        return

    for row in rows:
        print("\nSignal:", row["signal_type"])
        print("Title:", row["signal_title"])
        print("Strength:", row["signal_strength"])
        print("Confidence:", row["confidence"])
        print("Use case:", row["suggested_use_case"])
        print("Description:", row["signal_description"])
        print("Source:", row["source_title"])
        print("Publisher:", row["publisher"])
        print("Published:", row["published_date"])
        print("Reliability:", row["reliability"])
        print("URL:", row["url"])
        print("-" * 70)


if __name__ == "__main__":
    show_research("HSBC")