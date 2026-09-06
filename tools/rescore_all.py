"""
Re-score every account with the current scoring code.

Necessary after any change to scoring.py or use_case_fit.py: account_scores
rows are written at score time, so an unscored account keeps whatever the
code produced when it last ran. Mixing generations produces a table where
tier and score disagree.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3                                                  # noqa: E402
from src.database import DB_PATH                                # noqa: E402
from src.update_account_score import update_company_score       # noqa: E402


def main():
    conn = sqlite3.connect(DB_PATH)
    names = [r[0] for r in conn.execute("SELECT company_name FROM companies")]
    conn.close()

    import contextlib, io
    for n in names:
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                update_company_score(n)
            except Exception as exc:
                print(f"  FAILED {n}: {type(exc).__name__}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    print(f"Re-scored {len(names)} accounts.\n")
    print(f"{'company':30}{'staff':>8}{'score':>8}  {'tier':14}band")
    print("-" * 74)

    q = """SELECT co.company_name n, co.employee_count e, x.total_score t, x.tier
           FROM companies co JOIN account_scores x ON x.company_id = co.company_id
           ORDER BY x.total_score DESC"""

    for r in conn.execute(q):
        e = r["e"] or 0
        band = ("CORE" if 200 <= e <= 2000 else
                "adjacent" if 2000 < e <= 5000 else
                "upper-mid" if 5000 < e <= 15000 else
                "enterprise" if e > 15000 else "unknown")
        print(f'{r["n"][:28]:30}{e:>8}{r["t"]:>8}  {str(r["tier"]):14}{band}')

    conn.close()


if __name__ == "__main__":
    main()
