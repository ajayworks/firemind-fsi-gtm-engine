import json
import sys
import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.confidence_score import calculate_account_confidence
from src.database import get_connection, get_company, get_signals
from src.scoring import (
    calculate_scale_score,
    calculate_technology_score,
    calculate_operational_pain,
    calculate_timing_score,
    calculate_total_score,
)
from src.use_case_fit import best_use_case_by_fit


def update_company_score(company_name):
    company = get_company(company_name)

    if not company:
        print("Company not found.")
        return

    signals = get_signals(company["company_id"])
    account_confidence = calculate_account_confidence(signals)

    scale_score = calculate_scale_score(
        employees=company["employee_count"] or 0,
        countries_operated=company["countries_operated"] or 0,
        technology_scale_score=company["technology_scale_score"] or 0
    )

    technology_score = calculate_technology_score(
        cloud_score=company["cloud_score"] or 0,
        infra_score=company["infra_score"] or 0,
        technical_team_score=company["technical_team_score"] or 0
    )

    operational_pain_score = calculate_operational_pain(signals)

    # The four-dimension screen from the research now drives this.
    # Previously use_case_fit came from counting signal keywords, which
    # rewarded whichever use case happened to have the most news coverage.
    (
        recommended_use_case,
        use_case_fit_score,
        fit_breakdown,
        all_use_case_results,
    ) = best_use_case_by_fit(company, signals)

    timing_score = calculate_timing_score(signals)

    account_source = (
        company["account_source"]
        if "account_source" in company.keys() else "unknown"
    )

    result = calculate_total_score(
        scale_score,
        technology_score,
        operational_pain_score,
        use_case_fit_score,
        timing_score,
        account_source=account_source,
        employees=company["employee_count"] or 0
    )

    conn = get_connection()
    cursor = conn.cursor()

    # Remove old saved scores for this company
    cursor.execute("""
        DELETE FROM account_scores
        WHERE company_id = ?
    """, (company["company_id"],))

    # Save the latest score
    cursor.execute("""
        INSERT INTO account_scores (
            company_id,
            scale_score,
            technology_score,
            operational_pain_score,
            use_case_fit_score,
            timing_score,
            total_score,
            tier,
            recommended_use_case,
            confidence,
            fit_breakdown
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        company["company_id"],
        scale_score,
        technology_score,
        operational_pain_score,
        use_case_fit_score,
        timing_score,
        result["total_score"],
        result["tier"],
        recommended_use_case,
        account_confidence,
        json.dumps(fit_breakdown),
    ))

    conn.commit()
    conn.close()

    print(f"\n{company_name} latest score saved.")
    print("Scale:", scale_score)
    print("Technology:", technology_score)
    print("Operational pain:", operational_pain_score)
    print("Use-case fit:", use_case_fit_score)
    print("Timing:", timing_score)
    print("ICP band:", result["icp_band"], f'(x{result["icp_multiplier"]})')
    print("Base:", result["base_score"],
          "| source:", result["account_source"],
          f'(x{result["source_multiplier"]})')
    print("Total:", result["total_score"])
    print("Tier:", result["tier"])
    print("Recommended use case:", recommended_use_case)
    print("Confidence:", account_confidence)
    print("\nUse-case fit breakdown:")
    for k, v in fit_breakdown.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage:")
        print('python3 src/update_account_score.py "Company Name"')
        sys.exit()

    company_name = sys.argv[1]

    update_company_score(company_name)