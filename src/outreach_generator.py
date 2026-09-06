import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.database import get_connection
from src.account_brief_plus import build_evidence_brief


PERSONA_ANGLES = {
    "economic_buyer": (
        "business impact, resilience, operating efficiency and strategic risk"
    ),
    "technical_buyer": (
        "incident reduction, operational workload, infrastructure complexity and reliability"
    ),
    "champion": (
        "day-to-day operational burden, incident handling, automation and engineering efficiency"
    ),
    "risk_approver": (
        "operational resilience, control, auditability and permissioned automation"
    ),
    "influencer": (
        "architecture, integration, cloud complexity and operating-model design"
    ),
    "unknown": (
        "technology operations, resilience and automation"
    ),
}


SIGNAL_OPENERS = {
    "it_outage": (
        "I noticed the recent service disruption affecting {company}. "
        "That caught my attention because incident recovery and operational resilience "
        "are exactly where autonomous operations can become commercially relevant."
    ),

    "cloud_transformation": (
        "I noticed {company} is continuing to expand its cloud environment. "
        "As infrastructure becomes more distributed, the operational burden around "
        "monitoring, diagnosis and incident resolution usually increases as well."
    ),

    "operational_resilience": (
        "I noticed {company}'s current focus on operational resilience. "
        "We've been looking at where AI can support resilience without removing "
        "human control over sensitive operational actions."
    ),

    "ai_adoption": (
        "I noticed {company} is increasing its use of AI across the organisation. "
        "One area we've been researching is how that same direction can extend into "
        "IT operations while keeping appropriate controls and approvals."
    ),
}


def choose_best_signal(evidence):
    if not evidence:
        return None

    priority = {
        "it_outage": 5,
        "operational_resilience": 4,
        "cloud_transformation": 3,
        "infrastructure_modernisation": 3,
        "ai_adoption": 2,
    }

    return max(
        evidence,
        key=lambda item: (
            priority.get(item["signal_type"], 1),
            item["signal_strength"]
        )
    )


def generate_outreach(company_name):
    brief = build_evidence_brief(company_name)

    if not brief:
        return None

    account = brief["account"]
    people = brief["people"]
    evidence = brief["evidence"]

    # No stakeholder identified means no draft. Inventing a generic
    # "Technology Leader" recipient would produce a message addressed to
    # nobody - the engine should decline rather than fabricate.
    if not people:
        return None

    person = people[0]
    recipient_title = person["title"]
    persona = person["persona"]

    # In ephemeral mode no name is held, so greet generically rather than
    # pasting the job title into the salutation.
    recipient_name = (
        person["name"] if person.get("name_stored", True) else "there"
    )

    strongest_signal = choose_best_signal(evidence)

    if strongest_signal:
        opener_template = SIGNAL_OPENERS.get(
            strongest_signal["signal_type"]
        )

        if opener_template:
            opener = opener_template.format(
                company=company_name
            )
        else:
            opener = (
                f"I've been researching {company_name}'s technology operations "
                "and some of the changes happening across the estate."
            )

        evidence_url = strongest_signal["url"]

    else:
        opener = (
            f"I've been researching {company_name}'s technology operations."
        )
        evidence_url = None

    persona_angle = PERSONA_ANGLES.get(
        persona,
        PERSONA_ANGLES["unknown"]
    )

    # "ict_incident_classification" -> "ICT Incident Classification"
    ACRONYMS = {"ict", "dora", "kyc", "jml", "sre", "finops"}
    use_case = " ".join(
        word.upper() if word in ACRONYMS else word.capitalize()
        for word in account["recommended_use_case"].split("_")
    )

    subject = f"{company_name} — {use_case}"

    message = f"""Hi {recipient_name},

{opener}

Given your role as {recipient_title}, I thought the most relevant angle may be around {persona_angle}.

Firemind is working on autonomous operations for enterprise IT environments, and based on the signals we've identified at {company_name}, there may be a relevant conversation around {use_case}.

The idea isn't simply full automation — it's using permissioned autonomous actions where outcomes can be verified and human oversight retained where needed.

Would you be open to a short conversation?

Best,
Ajay
"""

    return {
        "recipient_name": recipient_name,
        "recipient_title": recipient_title,
        "persona": persona,
        "subject": subject,
        "message": message,
        "evidence_url": evidence_url,
    }

def save_outreach_draft(company_name, outreach):
    if not outreach:
        return False

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT company_id
        FROM companies
        WHERE company_name = ?
    """, (company_name,))

    company = cursor.fetchone()

    if not company:
        conn.close()
        return False

    company_id = company[0]

    cursor.execute("""
        SELECT person_id
        FROM people
        WHERE company_id = ?
        AND full_name = ?
        LIMIT 1
    """, (
        company_id,
        outreach["recipient_name"]
    ))

    person = cursor.fetchone()

    person_id = person[0] if person else None

    cursor.execute("""
        INSERT INTO outreach (
            company_id,
            person_id,
            channel,
            message_version,
            subject_line,
            message_body,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        company_id,
        person_id,
        "email",
        "v1",
        outreach["subject"],
        outreach["message"],
        "draft"
    ))

    conn.commit()
    conn.close()

    return True

if __name__ == "__main__":
    result = generate_outreach("HSBC")

    if result:
        print("\nPERSONALISED OUTREACH DRAFT")
        print("=" * 70)

        print("\nRecipient:")
        print(
            result["recipient_name"],
            "|",
            result["recipient_title"],
            "|",
            result["persona"]
        )

        print("\nSubject:")
        print(result["subject"])

        print("\nMessage:")
        print(result["message"])

        print("\nEvidence:")
        print(result["evidence_url"])