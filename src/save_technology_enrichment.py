import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.database import get_connection
from src.technology_enrichment import technology_evidence


def save_technology_scores(company_name):
    result = technology_evidence(company_name)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE companies
        SET cloud_score = ?,
            infra_score = ?,
            technical_team_score = ?
        WHERE company_name = ?
    """, (
        result["cloud_score"],
        result["infra_score"],
        result["technical_team_score"],
        company_name
    ))

    conn.commit()
    conn.close()

    print(f"\nTechnology enrichment saved for {company_name}")
    print("Cloud score:", result["cloud_score"])
    print("Infrastructure score:", result["infra_score"])
    print("Technical team score:", result["technical_team_score"])

    print("\nCloud evidence:")
    for item in result["cloud_evidence"]:
        print("-", item)

    print("\nInfrastructure evidence:")
    for item in result["infra_evidence"]:
        print("-", item)

    print("\nTechnical team evidence:")
    for item in result["team_evidence"]:
        print("-", item)


if __name__ == "__main__":
    save_technology_scores("Barclays")