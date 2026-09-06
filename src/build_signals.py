import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.filter_results import filter_results


USE_CASE_MAP = {
    "it_outage": "incident_lifecycle_management",
    "service_disruption": "incident_lifecycle_management",
    "operational_resilience": "incident_lifecycle_management",
    "cloud_transformation": "cloud_operations",
    "infrastructure_modernisation": "cloud_operations",
    "ai_adoption": "other_autonomous_operations",
    "automation_programme": "other_autonomous_operations",
    "cost_reduction": "finops",
    "sre_hiring": "incident_lifecycle_management",
    "devops_hiring": "cloud_operations",
}


STRENGTH_MAP = {
    "it_outage": 5,
    "service_disruption": 4,
    "operational_resilience": 4,
    "cloud_transformation": 4,
    "infrastructure_modernisation": 4,
    "ai_adoption": 3,
    "automation_programme": 3,
    "cost_reduction": 3,
    "sre_hiring": 4,
    "devops_hiring": 3,
}


# Sources that are not events.
#
# A status page, a vendor's own marketing post or an undated corporate PDF
# cannot support a "why now" claim. Presenting a Downdetector widget as market
# intelligence makes the whole list look credulous, so these are rejected
# before they can become a signal.
LOW_QUALITY_DOMAINS = (
    # status widgets - a live outage page is not a dated event
    "downdetector", "isitdownrightnow", "statuspage", "status.",
    # user-generated
    "glassdoor", "indeed.com", "reddit.com", "quora.com",
    "facebook.com", "pinterest.", "tiktok.",
    # content farms and AI-rewritten aggregators. A real event behind an
    # unciteable source is still unciteable - if the outage is genuine it
    # will also be reported somewhere a buyer would recognise.
    "evrimagaci.org", "medium.com/@", "substack.com",
    "newsbreak.com", "247wallst", "simplywall.st",
)

# LinkedIn posts are usually vendor marketing rather than reporting. Company
# pages and job posts are fine; individual activity posts are not.
LOW_QUALITY_PATTERNS = (
    "linkedin.com/posts/",
    "/status/",
)

# A title that is only the company's own name carries no event.
def _title_is_substantive(title, company_name):
    cleaned = (title or "").strip()

    if len(cleaned) < 25:
        return False

    # "PARAGON BANKING GROUP PLC" - the company name and nothing else
    stripped = cleaned.upper()
    for token in ("PLC", "LTD", "LIMITED", "GROUP", "UK", "|", "-"):
        stripped = stripped.replace(token, " ")
    stripped = " ".join(stripped.split())

    company_tokens = set(company_name.upper().split())
    title_tokens = set(stripped.split())

    # Nothing in the title beyond the company's own name
    return bool(title_tokens - company_tokens)


def is_usable_source(url, title, company_name):
    """Reject sources that cannot support a dated 'why now' claim."""
    u = (url or "").lower()

    if any(d in u for d in LOW_QUALITY_DOMAINS):
        return False, "status page or non-editorial source"

    if any(p in u for p in LOW_QUALITY_PATTERNS):
        return False, "social post rather than reporting"

    if not _title_is_substantive(title, company_name):
        return False, "title carries no event"

    return True, None


def build_candidate_signals(company_name, refresh=False):
    results = filter_results(
        company_name,
        refresh=refresh
    )

    candidates = []

    rejected = []

    for result in results:

        usable, reason = is_usable_source(
            result["url"], result["title"], company_name
        )

        if not usable:
            rejected.append((result["title"][:60], reason))
            continue

        for signal_type, matched_keywords in result["matches"].items():

            candidate = {
                "company": company_name,
                "signal_type": signal_type,
                "signal_title": result["title"],
                "signal_strength": STRENGTH_MAP.get(signal_type, 2),
                "confidence": "medium",
                "suggested_use_case": USE_CASE_MAP.get(
                    signal_type,
                    "unknown"
                ),
                "matched_keywords": matched_keywords,
                "source_url": result["url"],
                "evidence": result["content"][:500],
            }

            candidates.append(candidate)

    if rejected:
        print(f"  [signals] rejected {len(rejected)} low-quality source(s):")
        for title, reason in rejected[:5]:
            print(f"    - {title} ({reason})")

    return candidates


if __name__ == "__main__":

    company = "HSBC"

    candidates = build_candidate_signals(company)

    print(f"\nCANDIDATE SIGNALS — {company}")
    print("=" * 70)

    print(f"\nCandidate signals generated: {len(candidates)}")

    for candidate in candidates:

        print("\nSignal:", candidate["signal_type"])
        print("Title:", candidate["signal_title"])
        print("Strength:", candidate["signal_strength"])
        print("Confidence:", candidate["confidence"])
        print("Use case:", candidate["suggested_use_case"])
        print(
            "Keywords:",
            ", ".join(candidate["matched_keywords"])
        )
        print("Source:", candidate["source_url"])

        print("-" * 70)