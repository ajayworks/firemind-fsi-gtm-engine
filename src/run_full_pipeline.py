import sys
from pathlib import Path

# Allow both `python3 -m src.run_full_pipeline` and
# `python3 src/run_full_pipeline.py` - running a script inside src/ puts
# src/ on the path rather than the repo root, which breaks `from src.x`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.add_company import add_company
from src.web_research import research_company
from src.save_research_signals import save_signals
from src.enrich_company import enrich_company
from src.save_verified_people import save_verified_people


def run_pipeline(company_name, refresh=False):
    add_company(company_name)
    print(f"\nRUNNING GTM PIPELINE FOR: {company_name}")
    print("=" * 70)

    steps = [
        ("0. Preparing research cache",
         lambda: research_company(company_name, refresh=refresh)),
        ("1. Researching and saving signals",
         lambda: save_signals(company_name)),
        ("2. Enriching company and updating score",
         lambda: enrich_company(company_name)),
        ("3. Discovering and saving verified people",
         lambda: save_verified_people(company_name)),
    ]

    failed = []

    for label, step in steps:
        print(f"\n{label}...")
        try:
            step()
        except Exception as exc:
            # One failed step should not discard the work already done, and
            # should not stop the remaining accounts in a batch run.
            print(f"  SKIPPED - {type(exc).__name__}: {str(exc)[:120]}")
            failed.append(label)

    if failed:
        print(f"\nPIPELINE FINISHED WITH {len(failed)} SKIPPED STEP(S):")
        for f in failed:
            print(f"  - {f}")
    else:
        print("\nPIPELINE COMPLETE.")
    print("=" * 70)


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage:")
        print('python3 -m src.run_full_pipeline "Company Name"')
        print('python3 -m src.run_full_pipeline "Company Name" --refresh')
        sys.exit()

    company_name = sys.argv[1]
    refresh = "--refresh" in sys.argv

    run_pipeline(company_name, refresh=refresh)