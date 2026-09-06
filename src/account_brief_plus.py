import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.database import get_connection
from src.account_brief import build_account_brief
from src.technology_enrichment import technology_evidence


def build_evidence_brief(company_name):
    brief = build_account_brief(company_name)

    if not brief:
        return None

    technology = technology_evidence(company_name)

    conn = get_connection()
    conn.row_factory = __import__("sqlite3").Row
    cursor = conn.cursor()

    company_id = brief["account"]["company_id"]

    cursor.execute("""
        SELECT
            s.signal_type,
            s.signal_title,
            s.signal_strength,
            src.url,
            src.publisher
        FROM signals s
        LEFT JOIN sources src
            ON s.source_id = src.source_id
        WHERE s.company_id = ?
        ORDER BY s.signal_strength DESC
    """, (company_id,))

    evidence = cursor.fetchall()


    # Get account enrichment / provenance sources
    cursor.execute("""
        SELECT
            source_type,
            source_title,
            url,
            reliability
        FROM sources
        WHERE source_type IN (
            'industry_database',
            'company_website',
            'annual_report'
        )
        AND LOWER(source_title) LIKE LOWER(?)
        ORDER BY source_id DESC
        LIMIT 10
    """, (f"%{company_name}%",))

    raw_enrichment_sources = cursor.fetchall()

    enrichment_sources = []

    for source in raw_enrichment_sources:
        source_title = source["source_title"].lower()
        source_type = source["source_type"]

        evidence_type = "Account enrichment"

        if (
            "employee" in source_title
            or "headcount" in source_title
            or source_type == "industry_database"
        ):
            evidence_type = "Employee count"

        elif (
            "global network" in source_title
            or "global footprint" in source_title
            or "countries" in source_title
            or "markets" in source_title
        ):
            evidence_type = "Geographic reach"

        elif (
            "cloud" in source_title
            or "technology" in source_title
            or "infrastructure" in source_title
        ):
            evidence_type = "Technology evidence"

        enrichment_sources.append({
            "evidence_type": evidence_type,
            "source_type": source["source_type"],
            "source_title": source["source_title"],
            "url": source["url"],
            "reliability": source["reliability"],
        })

    conn.close()

    signal_types = {
        row["signal_type"]
        for row in evidence
    }

    if (
        "it_outage" in signal_types
        and "cloud_transformation" in signal_types
    ):
        conversation_opener = (
            f"I noticed {company_name} is continuing to expand its cloud "
            "and AI footprint while also managing operational resilience "
            "and service disruption. We've been researching where "
            "permissioned autonomous operations can reduce incident-handling "
            "effort without removing human control."
        )

    elif "cloud_transformation" in signal_types:
        conversation_opener = (
            f"I noticed {company_name} is continuing to expand its cloud "
            "environment. We're looking at where autonomous operations can "
            "help large financial institutions manage increasing "
            "infrastructure complexity."
        )

    else:
        conversation_opener = (
            f"We've been researching how financial institutions such as "
            f"{company_name} are approaching AI-enabled IT operations, "
            "particularly where human approval remains important."
        )

    brief["evidence"] = evidence
    brief["enrichment_sources"] = enrichment_sources
    brief["technology_evidence"] = technology
    brief["conversation_opener"] = conversation_opener

    return brief


def print_evidence_brief(company_name):
    brief = build_evidence_brief(company_name)

    if not brief:
        return

    account = brief["account"]

    print("\nFIREMIND GTM ACCOUNT BRIEF")
    print("=" * 70)

    print("\nACCOUNT")
    print(account["company_name"])

    print("\nFIT")
    print(
        f'{account["total_score"]}/100 | '
        f'{account["tier"]} | '
        f'{account["confidence"]}'
    )

    print("\nRECOMMENDED USE CASE")
    print(account["recommended_use_case"])

    print("\nWHY NOW")

    for item in brief["evidence"][:5]:
        print(
            "-",
            item["signal_type"],
            "|",
            item["signal_title"]
        )

        if item["url"]:
            print(" ", item["url"])

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

    print("\nCONVERSATION OPENER")
    print(brief["conversation_opener"])

    print("\nNEXT ACTION")
    print(brief["next_action"])


if __name__ == "__main__":
    print_evidence_brief("HSBC")