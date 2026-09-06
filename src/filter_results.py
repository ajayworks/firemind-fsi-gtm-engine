import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.web_research import research_company


SIGNAL_KEYWORDS = {
    "it_outage": [
        "outage",
        "downtime",
        "service disruption",
        "systems outage",
        "service unavailable",
        "banking outage",
    ],

    "cloud_transformation": [
        "cloud transformation",
        "cloud migration",
        "google cloud",
        "aws",
        "azure",
        "hybrid cloud",
        "public cloud",
        "private cloud",
        "cloud-first",
        "cloud first",
        "multi-cloud",
        "multicloud",
    ],

    "infrastructure_modernisation": [
        "legacy infrastructure",
        "application estate",
        "technology estate",
        "infrastructure modernisation",
        "infrastructure modernization",
        "platform engineering",
    ],

    "operational_resilience": [
        "operational resilience",
        "disaster recovery",
        "service recovery",
        "business continuity",
    ],

    "ai_adoption": [
        "artificial intelligence",
        "generative ai",
        "genai",
        "agentic ai",
    ],

    "sre_hiring": [
        "site reliability engineer",
        "site reliability engineering",
        "sre role",
        "sre hiring",
        "sre engineer",
        "sre engineering",
    ],

    "devops_hiring": [
        "devops engineer",
        "devops hiring",
    ],

    "automation_programme": [
        "automation programme",
        "automation program",
        "automated operations",
        "intelligent automation",
        "automation strategy",
        "automation initiative",
    ],

    "cost_reduction": [
        "cost reduction",
        "reduce costs",
        "cost savings",
        "efficiency improvement",
        "efficiency programme",
    ],
}


def classify_result(result):
    title = result.get("title", "")
    content = result.get("content", "")

    title_lower = title.lower()
    content_lower = content.lower()

    search_text = f"{title_lower} {content_lower}"

    matches = {}

    for signal_type, keywords in SIGNAL_KEYWORDS.items():

        matched_keywords = []

        for keyword in keywords:
            if keyword.lower() in search_text:
                matched_keywords.append(keyword)

        if matched_keywords:
            matches[signal_type] = matched_keywords

    # Extra guardrail for outage classification
    outage_terms = [
        "outage",
        "downtime",
        "service disruption",
        "systems outage",
        "service unavailable",
        "banking outage",
    ]

    if not any(term in title_lower for term in outage_terms):
        matches.pop("it_outage", None)

    return matches

def is_company_specific(result, company_name):
    title = result.get("title", "").lower()
    content = result.get("content", "").lower()

    company = company_name.lower()

    # Strongest case: company appears in title
    if company in title:
        return True

    # Otherwise require company to appear several times in content
    if content.count(company) >= 2:
        return True

    return False

def filter_results(company_name, refresh=False):
    results = research_company(
        company_name,
        refresh=refresh
    )

    filtered = []

    for result in results:
        # Ignore generic articles that are not really about this company
        if not is_company_specific(result, company_name):
            continue

        matches = classify_result(result)

        if matches:
            filtered.append({
                "title": result.get("title"),
                "url": result.get("url"),
                "content": result.get("content"),
                "matches": matches,
            })

    return filtered


if __name__ == "__main__":

    company = "HSBC"

    results = filter_results(company)

    print(f"\nFIREMIND-RELEVANT RESULTS — {company}")
    print("=" * 70)

    print(f"\nRelevant results found: {len(results)}")

    for result in results:

        print("\nTITLE:")
        print(result["title"])

        print("\nMATCHED SIGNALS:")

        for signal_type, keywords in result["matches"].items():
            print(
                f"  {signal_type}: "
                f"{', '.join(keywords)}"
            )

        print("\nURL:")
        print(result["url"])

        print("-" * 70)