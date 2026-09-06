import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.web_research import research_company


TECH_KEYWORDS = {
    "cloud": [
        "aws",
        "azure",
        "google cloud",
        "public cloud",
        "private cloud",
        "hybrid cloud",
        "cloud migration",
        "cloud transformation",
    ],
    "infrastructure": [
        "infrastructure",
        "application estate",
        "technology estate",
        "platform engineering",
        "site reliability",
        "sre",
        "devops",
        "data centre",
        "data center",
    ],
    "technical_teams": [
        "site reliability engineering",
        "platform engineering",
        "cloud engineering",
        "devops",
        "infrastructure engineering",
        "technology operations",
    ],
}


def technology_evidence(company_name):
    results = research_company(company_name)

    combined_text = " ".join(
        f'{r.get("title", "")} {r.get("content", "")}'
        for r in results
    ).lower()

    cloud_matches = [
        keyword
        for keyword in TECH_KEYWORDS["cloud"]
        if keyword in combined_text
    ]

    infra_matches = [
        keyword
        for keyword in TECH_KEYWORDS["infrastructure"]
        if keyword in combined_text
    ]

    team_matches = [
        keyword
        for keyword in TECH_KEYWORDS["technical_teams"]
        if keyword in combined_text
    ]

    cloud_score = min(len(set(cloud_matches)) * 2, 10)
    infra_score = min(len(set(infra_matches)) * 2, 10)
    technical_team_score = min(len(set(team_matches)), 5)

    return {
        "cloud_score": cloud_score,
        "infra_score": infra_score,
        "technical_team_score": technical_team_score,
        "cloud_evidence": sorted(set(cloud_matches)),
        "infra_evidence": sorted(set(infra_matches)),
        "team_evidence": sorted(set(team_matches)),
    }


if __name__ == "__main__":
    company = "Barclays"

    result = technology_evidence(company)

    print(f"\nTECHNOLOGY EVIDENCE — {company}")
    print("=" * 70)

    print("Cloud score:", result["cloud_score"])
    print("Cloud evidence:", result["cloud_evidence"])

    print("\nInfrastructure score:", result["infra_score"])
    print("Infrastructure evidence:", result["infra_evidence"])

    print("\nTechnical team score:", result["technical_team_score"])
    print("Technical team evidence:", result["team_evidence"])