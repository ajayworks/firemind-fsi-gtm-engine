import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.database import get_connection
from src.deduplicate_signals import deduplicate_signals


def save_signals(company_name, refresh=False):
    signals = deduplicate_signals(
        company_name,
        refresh=refresh
    )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT company_id
        FROM companies
        WHERE company_name = ?
    """, (company_name,))

    company = cursor.fetchone()

    if not company:
        print("Company not found.")
        conn.close()
        return

    company_id = company[0]

    if refresh:
        cursor.execute("""
            DELETE FROM signals
            WHERE company_id = ?
            AND is_verified = 0
            AND firemind_relevance = ?
        """, (
            company_id,
            "Automatically identified from public account research."
        ))

        print(
            f"Removed old automated signals for {company_name} "
            "before refresh."
        )

    saved_count = 0

    for signal in signals:

        # Use first source as primary source for V1
        primary_url = signal["sources"][0]

        cursor.execute("""
            SELECT source_id
            FROM sources
            WHERE url = ?
        """, (primary_url,))

        existing_source = cursor.fetchone()

        if existing_source:
            source_id = existing_source[0]

        else:
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
                "web_research",
                signal["signal_title"],
                primary_url,
                None,
                signal["evidence"][0][:500],
                "medium"
            ))

            source_id = cursor.lastrowid

        # Avoid inserting duplicate signal types for this company
        cursor.execute("""
            SELECT signal_id
            FROM signals
            WHERE company_id = ?
            AND signal_type = ?
            AND signal_title = ?
        """, (
            company_id,
            signal["signal_type"],
            signal["signal_title"]
        ))

        existing_signal = cursor.fetchone()

        if existing_signal:
            print(
                f'Skipping duplicate signal: '
                f'{signal["signal_type"]} — '
                f'{signal["signal_title"]}'
            )
            continue

        cursor.execute("""
            INSERT INTO signals (
                company_id,
                signal_type,
                signal_title,
                signal_description,
                signal_strength,
                firemind_relevance,
                suggested_use_case,
                is_verified,
                confidence,
                source_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            signal["signal_type"],
            signal["signal_title"],
            signal["evidence"][0][:500],
            signal["signal_strength"],
            "Automatically identified from public account research.",
            signal["suggested_use_case"],
            0,
            signal["confidence"],
            source_id
        ))

        saved_count += 1

    conn.commit()
    conn.close()

    print(f"{saved_count} signals saved for {company_name}.")


if __name__ == "__main__":
    save_signals("HSBC")