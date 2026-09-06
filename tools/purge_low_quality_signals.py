"""
Remove signals already saved from sources that cannot support a "why now".

The source filter in build_signals.py applies to new research runs. Anything
collected before it existed is still in the database, so this removes it.
Run once after upgrading, then re-score.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3                                          # noqa: E402
from src.database import DB_PATH                        # noqa: E402
from src.build_signals import is_usable_source          # noqa: E402


def main(dry_run=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT s.signal_id, s.signal_title, co.company_name, src.url
        FROM signals s
        JOIN companies co ON co.company_id = s.company_id
        LEFT JOIN sources src ON src.source_id = s.source_id
    """).fetchall()

    doomed = []

    for r in rows:
        usable, reason = is_usable_source(
            r["url"] or "", r["signal_title"] or "", r["company_name"]
        )
        if not usable:
            doomed.append((r["signal_id"], r["company_name"],
                           (r["signal_title"] or "")[:55], reason))

    if not doomed:
        print("No low-quality signals found.")
        return

    print(f"{len(doomed)} signal(s) to remove:\n")
    for _, co, title, reason in doomed:
        print(f"  {co[:26]:28}{title:57}{reason}")

    if dry_run:
        print("\nDry run - nothing deleted. Re-run without --dry-run to apply.")
        return

    conn.executemany(
        "DELETE FROM signals WHERE signal_id = ?",
        [(d[0],) for d in doomed]
    )
    conn.commit()
    print(f"\nDeleted {len(doomed)} signal(s). Re-score before exporting.")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
