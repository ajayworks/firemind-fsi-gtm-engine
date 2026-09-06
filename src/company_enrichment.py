import os
import re

from dotenv import load_dotenv
from tavily import TavilyClient

SOURCE_PRIORITY = {
    "annual_report": 5,
    "company_website": 5,
    "regulator": 5,
    "reputable_news": 4,
    "industry_database": 3,
    "linkedin": 2,
    "wikipedia": 1,
    "other": 1,
}

def classify_source(url):
    url = url.lower()

    if "barclays.com" in url:
        return "company_website"

    if "annualreports.com" in url:
        return "annual_report"

    if "reveliolabs.com" in url:
        return "industry_database"

    if "linkedin.com" in url:
        return "linkedin"

    if "wikipedia.org" in url:
        return "wikipedia"

    return "other"


load_dotenv()

API_KEY = os.getenv("TAVILY_API_KEY")

# The key is only needed for live research; the demo database works without it.
client = TavilyClient(api_key=API_KEY) if API_KEY else None

def safe_search(client, **kwargs):
    """
    Wrapper around the research API.

    Quota exhaustion, an expired key or a network failure are ordinary
    operating conditions for a research pipeline, not crashes. Returning an
    empty result set lets the run continue and report which accounts are
    missing evidence, rather than dropping a stack trace on the user and
    losing the work already done.
    """
    if client is None:
        raise ValueError("TAVILY_API_KEY not found. Live research needs an API key; the demo database does not.")
    try:
        return client.search(**kwargs)

    except Exception as exc:
        name = type(exc).__name__

        if "Forbidden" in name or "usage limit" in str(exc).lower():
            print(
                "  [research] API quota exhausted - continuing without new "
                "evidence for this step."
            )
        elif "Unauthorized" in name or "401" in str(exc):
            print("  [research] API key rejected. Check TAVILY_API_KEY in .env")
        else:
            print(f"  [research] lookup failed ({name}) - continuing.")

        return {"results": []}



def find_employee_count(company_name):
    query = f'"{company_name}" employees annual report headcount'

    response = safe_search(client, 
        query=query,
        search_depth="advanced",
        max_results=5
    )

    results = response.get("results", [])

    patterns = [
        r"([\d,]+)\s+employees",
        r"employs\s+([\d,]+)",
        r"workforce of\s+([\d,]+)",
        r"headcount of\s+([\d,]+)",
    ]

    candidates = []

    for result in results:
        text = (
            f'{result.get("title", "")} '
            f'{result.get("content", "")}'
        )

        for pattern in patterns:
            matches = re.findall(
                pattern,
                text,
                re.IGNORECASE
            )

            for match in matches:
                try:
                    number = int(
                        match.replace(",", "")
                    )

                    if number >= 100:
                        source_url = result.get("url", "")
                        source_type = classify_source(source_url)
                        candidates.append({
                            "employee_count": number,
                            "source_title": result.get("title"),
                            "source_url": source_url,
                            "source_type": source_type,
                            "source_priority": SOURCE_PRIORITY[source_type],
                        })

                except ValueError:
                    pass
    candidates.sort(
    key=lambda x: x["source_priority"],
    reverse=True
)

    return candidates


if __name__ == "__main__":
    company = "Barclays"

    results = find_employee_count(company)

    print(f"\nEMPLOYEE COUNT CANDIDATES — {company}")
    print("=" * 70)
    

    for result in results:
        print(
            "Employees:",
            result["employee_count"]
        )

        print(
            "Source:",
            result["source_title"]
        )

        print(
            "URL:",
            result["source_url"]
        )

        print("-" * 70)
        print("Source type:", result["source_type"])
        print("Priority:", result["source_priority"])