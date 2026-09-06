"""
Export a priority target list from the scored pipeline.

Produces a document a business developer can act on: ranked accounts, the
reason to call now, the workflow to lead with, the role to approach and the
opening line - each traceable to a dated public source.

Usage:
    python3 tools/export_target_list.py
    python3 tools/export_target_list.py --top 25
    python3 tools/export_target_list.py --exclude-large --out My-List.md
"""

import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import DB_PATH                        # noqa: E402
from src.outreach_generator import generate_outreach    # noqa: E402

ACRONYMS = {"ict", "dora", "kyc", "jml", "sre", "it"}

# Mixed-case names that title-casing would mangle.
SPECIAL_CASE = {"finops": "FinOps"}

# Workflows the buyer research validated as tier 1. Anything else is
# adjacent - the engine can still recommend it where the evidence points
# that way, but the distinction has to be visible, because the report
# recommends leading with the validated set.
RESEARCH_VALIDATED = {
    "incident_lifecycle_management",
    "ict_incident_classification",
    "dora_reporting",
    "audit_evidence_collection",
    "access_recertification",
    "joiner_mover_leaver",
}

# Sources that evidence hiring rather than an event. Legitimate signals, but
# a job advert is not the same kind of "why now" as an outage.
HIRING_SOURCES = ("builtin.com", "simplify.jobs", "linkedin.com/jobs",
                  "totaljobs", "reed.co.uk", "efinancialcareers")


def pretty(value):
    return " ".join(
        SPECIAL_CASE.get(w.lower())
        or (w.upper() if w.lower() in ACRONYMS else w.capitalize())
        for w in str(value or "").split("_")
    )


def validation_mark(use_case):
    return "" if use_case in RESEARCH_VALIDATED else " *"


def fetch_accounts(conn, exclude_large=False, top=None, include_deprioritised=False):
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT co.company_id, co.company_name, co.sector, co.employee_count,
               co.account_source, s.total_score, s.tier, s.recommended_use_case,
               s.confidence, s.fit_breakdown, s.use_case_fit_score
        FROM companies co
        JOIN account_scores s ON s.company_id = co.company_id
        WHERE s.total_score > 0
        ORDER BY s.total_score DESC
    """).fetchall()

    accounts = [dict(r) for r in rows]

    if not include_deprioritised:
        accounts = [a for a in accounts if a["tier"] != "deprioritised"]

    if exclude_large:
        accounts = [a for a in accounts if (a["employee_count"] or 0) <= 50000]

    return accounts[:top] if top else accounts


def top_signal(conn, company_id):
    conn.row_factory = sqlite3.Row
    row = conn.execute("""
        SELECT s.signal_title, s.signal_date, src.url
        FROM signals s
        LEFT JOIN sources src ON src.source_id = s.source_id
        WHERE s.company_id = ?
        ORDER BY s.signal_strength DESC, s.signal_date DESC
        LIMIT 1
    """, (company_id,)).fetchone()
    return dict(row) if row else None


def target_role(conn, company_id):
    conn.row_factory = sqlite3.Row
    row = conn.execute("""
        SELECT job_title, persona_type FROM people
        WHERE company_id = ? ORDER BY priority DESC LIMIT 1
    """, (company_id,)).fetchone()
    return dict(row) if row else None


def build(conn, accounts):
    o = []
    a_ = o.append

    a_("# UK Financial Services — Priority Account List")
    a_("")
    a_(f'*Generated {date.today().strftime("%d %B %Y")} by the Firemind FSI GTM Engine.*')
    a_("")
    a_("Accounts are scored on five components — scale, technology estate, "
       "operational pain, use-case fit and timing — with a multiplier for how the "
       "account entered the pipeline. Company size is scored as a **band centred "
       "on the mid-size segment**, not a ladder: tier-1 banks are a different "
       "sales motion and rank lower by design.")
    a_("")
    a_("Use-case fit applies a four-dimension screen taken from buyer interviews: "
       "**capability adds, permission multiplies, data readiness gates.** An "
       "account failing either gate scores zero on fit regardless of the other "
       "dimensions, and the reason is stated rather than hidden.")
    a_("")
    a_("---")
    a_("")
    a_("## Ranked list")
    a_("")
    a_("| # | Account | Staff | Tier | Lead with | Target role |")
    a_("|---|---|---:|---|---|---|")

    for i, a in enumerate(accounts, 1):
        role = target_role(conn, a["company_id"])
        role_label = pretty(role["job_title"]) if role else "*discovery needed*"
        staff = f'{a["employee_count"]:,}' if a["employee_count"] else "—"
        a_(f'| {i} | **{a["company_name"]}** | {staff} | {pretty(a["tier"])} '
           f'| {pretty(a["recommended_use_case"])}'
           f'{validation_mark(a["recommended_use_case"])} | {role_label} |')

    a_("")
    a_("`*` marks a workflow **not validated by the buyer research**. The "
       "engine recommends it where the account's evidence points that way, but "
       "the interviews and survey supported incident lifecycle management, ICT "
       "incident classification, DORA reporting and audit evidence collection. "
       "Lead with a starred workflow only after qualifying it.")
    a_("")
    a_("---")
    a_("")
    a_("## Top accounts — detail")
    a_("")

    evidenced = [a for a in accounts
                 if not json.loads(a["fit_breakdown"] or "{}").get("gated")]
    gated = [a for a in accounts
             if json.loads(a["fit_breakdown"] or "{}").get("gated")]

    for i, a in enumerate(evidenced[:8], 1):
        sig = top_signal(conn, a["company_id"])
        role = target_role(conn, a["company_id"])
        fit = json.loads(a["fit_breakdown"] or "{}")

        a_(f'### {i}. {a["company_name"]}')
        a_("")
        a_(f'**Score {a["total_score"]} · {pretty(a["tier"])} · '
           f'evidence confidence {a["confidence"]}**')
        a_("")

        if sig:
            when = f' ({sig["signal_date"]})' if sig["signal_date"] else ""
            url = (sig["url"] or "").lower()
            label = ("**Hiring signal.**"
                     if any(h in url for h in HIRING_SOURCES)
                     else "**Why now.**")
            a_(f'{label} {sig["signal_title"]}{when}')
            if sig["url"]:
                a_("")
                a_(f'  Source: {sig["url"]}')
            a_("")

        uc = a["recommended_use_case"]
        if uc in RESEARCH_VALIDATED:
            a_(f'**Lead with.** {pretty(uc)}')
        else:
            a_(f'**Lead with.** {pretty(uc)} — *adjacent workflow, not '
               "validated by the buyer research. Qualify before leading with "
               "it.*")
        a_("")

        if fit.get("gated"):
            a_(f'**Caution.** Use-case fit is gated: {fit["gate_reason"]} '
               "Qualify by phone before investing outreach effort.")
            a_("")
        elif fit:
            a_(f'**Fit reasoning.** Verifiability {fit["verifiability"]}/7 · '
               f'data readiness {fit["data_readiness"]}/9 · '
               f'reachability {fit["system_reachability"]}/9 · '
               f'permission ×{fit["permission_multiplier"]} '
               f'→ fit {a["use_case_fit_score"]}')
            a_("")

        if role:
            a_(f'**Approach.** {pretty(role["job_title"])} '
               f'({pretty(role["persona_type"])})')
        else:
            a_("**Approach.** No stakeholder identified — run discovery first.")
        a_("")

        draft = generate_outreach(a["company_name"])
        if draft:
            parts = [p for p in draft["message"].strip().split("\n\n") if p]
            if len(parts) > 1:
                a_(f'**Opening line.** "{parts[1].strip()}"')
                a_("")
        a_("")

    if gated:
        a_("---")
        a_("")
        a_("## Qualify before working")
        a_("")
        a_("These accounts sit in the target segment but the engine could not "
           "establish that the workflow is reachable. That is a research gap, "
           "not a verdict — qualify by phone rather than dropping them.")
        a_("")
        for a in gated:
            fit = json.loads(a["fit_breakdown"] or "{}")
            staff = f'{a["employee_count"]:,}' if a["employee_count"] else "—"
            a_(f'- **{a["company_name"]}** ({staff} staff) — '
               f'{fit.get("gate_reason", "insufficient evidence")}')
        a_("")

    a_("---")
    a_("")
    a_("## Stakeholder coverage")
    a_("")
    with_people = sum(1 for a in accounts if target_role(conn, a["company_id"]))
    a_(f"**{with_people} of {len(accounts)} accounts have an identified "
       "stakeholder.**")
    a_("")
    a_("Role discovery verifies a name against a public appointment "
       "announcement before recording it. Mid-size institutions rarely publish "
       "those, so verification succeeds for large banks and fails for the "
       "target segment — the same coverage asymmetry that depresses the "
       "evidence scores above.")
    a_("")
    a_("The engine will not guess. An unverified name attached to a real "
       "person at a named employer is worse than an empty field, so accounts "
       "without a confirmed stakeholder are marked for discovery rather than "
       "populated speculatively. Closing this needs a verified contact source "
       "rather than public search.")
    a_("")

    a_("---")
    a_("")
    a_("## Method and limitations")
    a_("")
    a_("- Every score traces to a dated public source. Nothing is inferred "
       "without evidence.")
    a_("- **Absence of signal is not absence of pain.** Mid-size institutions "
       "generate far less public reporting than tier-1 banks, so a low score may "
       "reflect thin coverage rather than poor fit. Low-confidence accounts "
       "should be qualified by phone, not dropped.")
    a_("- Operational pain and timing count only the strongest signals, never "
       "the total volume, so press coverage cannot stand in for need.")
    a_("- Account source is operator-supplied and every account here is marked "
       "`unknown`. Existing consulting customers would rank materially higher "
       "once identified — that data sits inside Firemind, not in public sources.")
    a_("")

    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=None)
    ap.add_argument("--exclude-large", action="store_true")
    ap.add_argument("--include-deprioritised", action="store_true")
    ap.add_argument("--out", default="Target-Account-List.md")
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH)
    accounts = fetch_accounts(conn, args.exclude_large, args.top,
                              args.include_deprioritised)

    if not accounts:
        print("No scored accounts found. Run the pipeline first.")
        return

    Path(args.out).write_text(build(conn, accounts))
    conn.close()
    print(f"Wrote {args.out} — {len(accounts)} accounts.")


if __name__ == "__main__":
    main()
