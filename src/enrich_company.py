import sys

import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.save_company_enrichment import (
    save_employee_count,
    save_geography,
)
from src.save_technology_enrichment import save_technology_scores
from src.update_account_score import update_company_score


def enrich_company(company_name):
    print(f"\nENRICHING COMPANY: {company_name}")
    print("=" * 70)

    print("\n1. Updating employee count...")
    save_employee_count(company_name)

    print("\n2. Updating geographic reach...")
    save_geography(company_name)

    print("\n3. Updating technology evidence...")
    save_technology_scores(company_name)

    print("\n4. Recalculating account score...")
    update_company_score(company_name)

    print("\nENRICHMENT COMPLETE.")
    print("=" * 70)


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage:")
        print('python3 src/enrich_company.py "Company Name"')
        sys.exit()

    company_name = sys.argv[1]

    enrich_company(company_name)