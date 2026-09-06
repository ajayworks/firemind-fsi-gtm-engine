import re

PERSONA_RULES = {
    "economic_buyer": [
        "chief information officer",
        "cio",
        "chief technology officer",
        "cto",
        "chief operating officer",
        "coo",
        "chief ai officer",
    ],

    "technical_buyer": [
        "head of infrastructure",
        "director of infrastructure",
        "vp infrastructure",
        "head of cloud",
        "director of cloud",
        "head of platform",
        "head of engineering",
        "head of it operations",
        "director of it operations",
        "head of technology operations",
    ],

    "champion": [
        "head of sre",
        "site reliability",
        "platform engineering",
        "cloud operations",
        "devops",
        "service management",
    ],

    "risk_approver": [
        "operational resilience",
        "technology risk",
        "it risk",
        "operational risk",
        "cyber risk",
    ],

    "influencer": [
        "enterprise architect",
        "cloud architect",
        "solutions architect",
        "technology transformation",
        "digital transformation",
    ],
}

PERSONA_PRIORITY = {
    "economic_buyer": 5,
    "technical_buyer": 5,
    "champion": 4,
    "risk_approver": 4,
    "influencer": 3,
    "unknown": 1,
}

USE_CASE_PERSONA_MAP = {
    "incident_lifecycle_management": [
        "technical_buyer",
        "champion",
        "economic_buyer",
        "risk_approver",
    ],
    "cloud_operations": [
        "technical_buyer",
        "champion",
        "economic_buyer",
        "influencer",
    ],
    "dora_reporting": [
        "risk_approver",
        "economic_buyer",
        "technical_buyer",
    ],
    "audit_evidence_collection": [
        "risk_approver",
        "technical_buyer",
        "influencer",
    ],
}

def get_persona_priority(persona):
    return PERSONA_PRIORITY.get(persona, 1)


def persona_fit_for_use_case(persona, use_case):
    preferred_personas = USE_CASE_PERSONA_MAP.get(use_case, [])

    if persona not in preferred_personas:
        return 0

    position = preferred_personas.index(persona)

    return max(5 - position, 1)

def classify_persona(job_title):
    title = job_title.lower()

    for persona, keywords in PERSONA_RULES.items():
        for keyword in keywords:

            # Acronyms must match whole words only
            if keyword in ["cto", "cio", "coo"]:
                if re.search(rf"\b{keyword}\b", title):
                    return persona

            # Normal phrases can use substring matching
            elif keyword in title:
                return persona

    return "unknown"


if __name__ == "__main__":

    use_case = "incident_lifecycle_management"

    test_titles = [
        "Chief Technology Officer",
        "Head of Infrastructure",
        "Director of Operational Resilience",
        "Head of Site Reliability Engineering",
        "Enterprise Architect",
        "Finance Manager",
    ]

    for title in test_titles:
        persona = classify_persona(title)
        priority = get_persona_priority(persona)
        use_case_fit = persona_fit_for_use_case(persona, use_case)

        print(
            title,
            "→",
            persona,
            "| priority:",
            priority,
            "| use-case fit:",
            use_case_fit
        )