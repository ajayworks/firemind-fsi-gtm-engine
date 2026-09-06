import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.database import get_connection
from src.extract_actual_titles import enrich_people
from src.persona_matcher import (
    classify_persona,
    get_persona_priority,
)
from src import privacy


def save_verified_people(company_name):
    """
    Returns the discovered people so the caller can use them in-session.

    What gets WRITTEN depends on the personal-data mode:
      demo       nothing is written
      ephemeral  role, persona and source are written; the name is not
      persisted  the name is written with a retention expiry

    The return value always contains the names, so a live demo can show real
    discovery working without the database ever holding the data.
    """
    mode = privacy.current_mode()
    people = enrich_people(company_name)

    if not privacy.may_write_people(mode):
        print(
            f"[{mode}] Discovery ran and returned {len(people)} people. "
            "Nothing written - demo mode uses synthetic records only."
        )
        return people

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

    saved = 0

    for person in people:

        actual_title = person["actual_title"]

        # Only save people whose title we verified
        if not actual_title:
            continue

        persona = classify_persona(actual_title)
        priority = get_persona_priority(persona)

        # Data minimisation: the name is only written in persisted mode.
        # The pseudonymous reference lets us recognise the same person on a
        # later run without holding their identity.
        person_ref = privacy.pseudonymise(company_name, person["name"])

        stored_name = person["name"] if privacy.may_store_names(mode) else None
        stored_link = primary_source["url"] if privacy.may_store_names(mode) else None
        expires_at = privacy.retention_expiry() if privacy.may_store_names(mode) else None

        primary_source = person["sources"][0]

        # Save / reuse the public source that verified this person
        cursor.execute("""
            SELECT source_id
            FROM sources
            WHERE url = ?
        """, (
            primary_source["url"],
        ))

        existing_source = cursor.fetchone()

        if existing_source:
            source_id = existing_source[0]

        else:
            cursor.execute("""
                INSERT INTO sources (
                    source_type,
                    source_title,
                    url,
                    reliability
                )
                VALUES (?, ?, ?, ?)
            """, (
                "person_verification",
                primary_source["title"],
                primary_source["url"],
                "medium"
            ))

            source_id = cursor.lastrowid

        cursor.execute("""
            SELECT person_id
            FROM people
            WHERE company_id = ?
            AND person_ref = ?
        """, (
            company_id,
            person_ref
        ))

        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE people
                SET job_title = ?,
                    persona_type = ?,
                    priority = ?,
                    relevance_reason = ?,
                    source_id = ?,
                    full_name = ?,
                    linkedin_url = ?,
                    retention_expires_at = ?,
                    last_verified_at = CURRENT_TIMESTAMP
                WHERE person_id = ?
            """, (
                    actual_title,
                    persona,
                    priority,
                    f"Verified public-source match for {actual_title}",
                    source_id,
                    stored_name,
                    stored_link,
                    expires_at,
                    existing[0]
                ))

        else:
            cursor.execute("""
                INSERT INTO people (
                    company_id,
                    person_ref,
                    full_name,
                    job_title,
                    persona_type,
                    priority,
                    relevance_reason,
                    source_id,
                    linkedin_url,
                    retention_expires_at,
                    last_verified_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                    company_id,
                    person_ref,
                    stored_name,
                    actual_title,
                    persona,
                    priority,
                    f"Verified public-source match for {actual_title}",
                    source_id,
                    stored_link,
                    expires_at
            ))

        saved += 1

    conn.commit()
    conn.close()

    if privacy.may_store_names(mode):
        print(
            f"{saved} people saved for {company_name} WITH names "
            f"(retention expires {privacy.retention_expiry()})."
        )
    else:
        print(
            f"{saved} role records saved for {company_name}. "
            "Names were not written to the database."
        )

    return people


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            'Usage: python3 -m src.save_verified_people '
            '"Company Name"'
        )
        sys.exit(1)

    company = sys.argv[1]

    save_verified_people(company)