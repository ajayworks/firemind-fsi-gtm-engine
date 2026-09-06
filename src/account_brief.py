import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.database import get_connection
from src.persona_matcher import persona_fit_for_use_case


def build_account_brief(company_name):
    conn = get_connection()
    conn.row_factory = __import__("sqlite3").Row
    cursor = conn.cursor()

    # Get company + latest score
    cursor.execute("""
        SELECT
            c.company_id,
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
            s.confidence,
            s.fit_breakdown,
            c.account_source,
            c.employee_count
        FROM companies c
        LEFT JOIN account_scores s
            ON c.company_id = s.company_id
        WHERE c.company_name = ?
        ORDER BY s.calculated_at DESC
        LIMIT 1
    """, (company_name,))

    account = cursor.fetchone()

    if not account:
        print("Company not found.")
        conn.close()
        return

    company_id = account["company_id"]
    use_case = account["recommended_use_case"]

    # Get signals
    cursor.execute("""
        SELECT
            signal_type,
            signal_title,
            signal_description,
            signal_strength,
            confidence
        FROM signals
        WHERE company_id = ?
        ORDER BY signal_strength DESC
    """, (company_id,))

    signals = cursor.fetchall()

    # Get people
    cursor.execute("""
        SELECT
            p.full_name,
            p.job_title,
            p.persona_type,
            p.priority,
            p.linkedin_url,
            src.source_title AS verification_source_title,
            src.url AS verification_source_url,
            src.reliability AS verification_source_reliability
        FROM people p
        LEFT JOIN sources src
            ON p.source_id = src.source_id
        WHERE p.company_id = ?
    """, (company_id,))

    people = cursor.fetchall()

    conn.close()

    ranked_people = []

    for person in people:
        use_case_fit = persona_fit_for_use_case(
            person["persona_type"],
            use_case
        )

        total_priority = (
            person["priority"] * 2
            + use_case_fit
        )

        ranked_people.append({
            # NULL name = ephemeral mode; show the role instead
            "name": person["full_name"] or f'{person["job_title"]} (name not stored)',
            # whether a real name is held, so outreach can greet appropriately
            "name_stored": bool(person["full_name"]),
            "title": person["job_title"],
            "persona": person["persona_type"],
            "total_priority": total_priority,
            "linkedin_url": person["linkedin_url"],
            "verification_source_title": person["verification_source_title"],
            "verification_source_url": person["verification_source_url"],
            "verification_source_reliability": person[
                "verification_source_reliability"
            ],
        })

    ranked_people.sort(
        key=lambda x: x["total_priority"],
        reverse=True
    )

    # Simple value hypothesis for V1
    signal_types = {signal["signal_type"] for signal in signals}

    if "it_outage" in signal_types and "cloud_transformation" in signal_types:
        value_hypothesis = (
            f"{company_name} appears to be operating a large, evolving "
            "technology estate while also showing evidence of service "
            "disruption. Firemind may have a credible angle around "
            "reducing manual incident-management effort and improving "
            "operational resilience."
        )
    elif "cloud_transformation" in signal_types:
        value_hypothesis = (
            f"{company_name}'s cloud transformation may increase operational "
            "complexity, creating a potential fit for autonomous cloud and "
            "incident operations."
        )
    else:
        value_hypothesis = (
            "Further research is required before forming a strong "
            "Firemind value hypothesis."
        )

    # Next action - thresholds match the tier boundaries in scoring.py
    if account["total_score"] >= 62:
        next_action = "Contact now - tier 1 account"
    elif account["total_score"] >= 48:
        next_action = "Prepare targeted outreach"
    elif account["total_score"] >= 34:
        next_action = "Research deeper before contacting"
    else:
        next_action = "Monitor - insufficient evidence to prioritise"

    return {
        "account": account,
        "signals": signals,
        "people": ranked_people,
        "value_hypothesis": value_hypothesis,
        "next_action": next_action
    }


def print_account_brief(company_name):
    brief = build_account_brief(company_name)

    if not brief:
        return

    account = brief["account"]

    print("\nWHY THIS ACCOUNT?")
    print("=" * 70)

    print("\nACCOUNT")
    print(account["company_name"])
    print("Sector:", account["sector"])

    print("\nFIREMIND FIT")
    print("Score:", account["total_score"])
    print("Tier:", account["tier"])
    print("Confidence:", account["confidence"])

    print("\nRECOMMENDED USE CASE")
    print(account["recommended_use_case"])

    print("\nWHY NOW")

    for signal in brief["signals"][:5]:
        print(
            "-",
            signal["signal_type"],
            "|",
            signal["signal_title"]
        )

    print("\nTOP PEOPLE")

    for person in brief["people"][:3]:
        print(
            "-",
            person["name"],
            "|",
            person["title"],
            "|",
            person["persona"]
        )

    print("\nVALUE HYPOTHESIS")
    print(brief["value_hypothesis"])

    print("\nNEXT ACTION")
    print(brief["next_action"])


if __name__ == "__main__":
    print_account_brief("HSBC")