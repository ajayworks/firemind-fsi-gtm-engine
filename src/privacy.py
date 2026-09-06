"""
Personal-data handling for stakeholder records.

WHY THIS MODULE EXISTS
----------------------
Account signals are public corporate information. Stakeholder records are
personal data about identifiable people who never asked to be in a sales
database. Those two things need different handling, and most GTM tooling
treats them identically.

The design principle is data minimisation. Ask what the engine actually
needs a person record FOR:

    - which roles exist at this account          -> job title
    - who to aim the message at                  -> persona classification
    - can the claim be checked                   -> source URL
    - who to actually contact                    -> name  <-- only at send time

Only the last of those needs a name, and only at the moment of outreach.
So by default the engine stores the role map and resolves the individual
just-in-time, holding the name in memory for the session and never writing
it to disk.

MODES
-----
demo       Synthetic records only. Live lookups do not write. Default, and
           what a cloned repo runs.
ephemeral  Live discovery. Role, persona and source are persisted; names are
           held in session memory only and never written to the database.
persisted  Live discovery with names stored. Requires explicit opt-in, stamps
           a retention expiry on every record, and is subject to purge.

Set with the GTM_PERSONAL_DATA_MODE environment variable.
"""

import hashlib
import os
from datetime import date, timedelta

DEMO = "demo"
EPHEMERAL = "ephemeral"
PERSISTED = "persisted"

VALID_MODES = (DEMO, EPHEMERAL, PERSISTED)

# Days a stored name may be retained before purge_expired() removes it.
# Short by design: a contact record that has gone stale is a liability with
# no offsetting sales value.
DEFAULT_RETENTION_DAYS = 30


def current_mode():
    mode = os.getenv("GTM_PERSONAL_DATA_MODE", DEMO).strip().lower()

    if mode not in VALID_MODES:
        raise ValueError(
            f"GTM_PERSONAL_DATA_MODE must be one of {VALID_MODES}, got {mode!r}"
        )

    return mode


def may_write_people(mode=None):
    """Demo mode never writes discovered people."""
    return (mode or current_mode()) in (EPHEMERAL, PERSISTED)


def may_store_names(mode=None):
    """Only the explicit opt-in mode writes a name to disk."""
    return (mode or current_mode()) == PERSISTED


def pseudonymise(company_name, full_name):
    """
    Stable, non-reversible reference for a person.

    Lets the engine recognise 'the same person as last run' for dedupe and
    update, without holding the name. Salted per company so the same
    reference cannot be correlated across accounts.
    """
    digest = hashlib.sha256(
        f"{company_name.strip().lower()}::{full_name.strip().lower()}".encode()
    ).hexdigest()

    return f"P-{digest[:10].upper()}"


def retention_expiry(days=DEFAULT_RETENTION_DAYS):
    return (date.today() + timedelta(days=days)).isoformat()


def display_label(full_name, job_title, mode=None):
    """
    What the UI shows. In ephemeral mode the name exists in memory for the
    session, so it can be displayed - it simply is not written to disk.
    """
    if (mode or current_mode()) == DEMO:
        return full_name or job_title or "Sample contact"

    return full_name or f"{job_title} (name resolved at outreach)"


# ---------------------------------------------------------------------------
# Purge operations
# ---------------------------------------------------------------------------

def purge_expired(conn):
    """Delete stored names past their retention window. Role data survives."""
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE people
        SET full_name = NULL,
            linkedin_url = NULL,
            email = NULL,
            retention_expires_at = NULL
        WHERE retention_expires_at IS NOT NULL
          AND retention_expires_at < ?
    """, (date.today().isoformat(),))

    purged = cursor.rowcount
    conn.commit()

    return purged


def purge_all_personal_data(conn):
    """
    Remove every stored name, link and email, keeping the role map intact.
    Wired to a button in the app: a data-protection control nobody can use
    is not a control.
    """
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE people
        SET full_name = NULL,
            linkedin_url = NULL,
            email = NULL,
            retention_expires_at = NULL
    """)

    purged = cursor.rowcount
    conn.commit()

    return purged


NOTICE = (
    "Stakeholder discovery returns personal data about identifiable people. "
    "This prototype defaults to storing role and persona only, resolving "
    "individuals at outreach time. Storing names requires explicit opt-in "
    "and is subject to a {days}-day retention limit."
).format(days=DEFAULT_RETENTION_DAYS)
