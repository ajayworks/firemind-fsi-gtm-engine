import os
import json
from pathlib import Path

from dotenv import load_dotenv
from tavily import TavilyClient


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


CACHE_DIR = Path("data/research_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def research_company(company_name, refresh=False):

    normalised_name = " ".join(
        company_name.strip().lower().split()
    )

    cache_key = normalised_name.replace(" ", "_")

    cache_file = CACHE_DIR / f"{cache_key}.json"

    # Use saved results unless we explicitly refresh
    if cache_file.exists() and not refresh:
        with open(cache_file, "r") as f:
            return json.load(f)

    # TWO queries, deliberately.
    #
    # The original single query was weighted toward cloud and transformation
    # news. Those signal types carry ZERO operational-pain weight - correctly,
    # since a cloud migration is a reason to call now, not evidence of pain -
    # so the pipeline was collecting evidence that could not score on 25 of
    # the 100 available points.
    #
    # Query 1 looks for pain: outages, incidents, regulatory pressure, cost
    # and restructuring. Query 2 looks for the technology estate, which feeds
    # the technology score and system reachability.
    pain_query = f"""
    {company_name} UK financial services
    outage incident service disruption operational resilience
    DORA regulatory reporting compliance failure
    cost reduction restructuring outsourcing managed services
    """

    estate_query = f"""
    {company_name} UK financial services
    cloud migration infrastructure modernisation
    AWS Azure platform engineering SRE DevOps hiring
    digital transformation technology investment
    """

    results = []
    seen_urls = set()

    for query in (pain_query, estate_query):
        response = safe_search(
            client,
            query=query,
            search_depth="advanced",
            max_results=8
        )

        for item in response.get("results", []):
            url = item.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                results.append(item)

    with open(cache_file, "w") as f:
        json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    results = research_company("HSBC", refresh=True)

    print(f"Saved {len(results)} HSBC results.")