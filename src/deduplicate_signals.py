import sys
from pathlib import Path

# Running a script directly puts its own folder on sys.path rather than the
# repo root, which breaks `from src.x import ...`. This makes both
# `python3 -m src.module` and `python3 src/module.py` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from src.build_signals import build_candidate_signals


EVENT_GROUPS = {
    "it_outage": "outage_event",
    "cloud_transformation": "cloud_event",
    "ai_adoption": "ai_event",
    "automation_programme": "automation_event",
    "operational_resilience": "resilience_event",
    "infrastructure_modernisation": "infra_event",
}


def normalise_title(title):
    title = title.lower()

    remove_words = [
        "hsbc",
        "uk",
        "bank",
        "banking",
        "services",
        "service",
        "after",
        "following",
        "shows",
        "says",
        "and",
        "with",
        "the",
    ]

    for word in remove_words:
        title = title.replace(word, " ")

    return " ".join(title.split())


def deduplicate_signals(company_name, refresh=False):
    candidates = build_candidate_signals(
        company_name,
        refresh=refresh
    )

    deduplicated = {}

    for candidate in candidates:

        signal_type = candidate["signal_type"]
        title = normalise_title(candidate["signal_title"])

        # Group known event families
        event_group = EVENT_GROUPS.get(signal_type)

        if event_group:
            key = f"{signal_type}_{event_group}"
        else:
            key = f"{signal_type}_{title}"

        if key not in deduplicated:
            deduplicated[key] = {
                "company": company_name,
                "signal_type": signal_type,
                "signal_title": candidate["signal_title"],
                "signal_strength": candidate["signal_strength"],
                "confidence": candidate["confidence"],
                "suggested_use_case": candidate["suggested_use_case"],
                "sources": [candidate["source_url"]],
                "evidence": [candidate["evidence"]],
            }

        else:
            if candidate["source_url"] not in deduplicated[key]["sources"]:
                deduplicated[key]["sources"].append(
                    candidate["source_url"]
                )

            deduplicated[key]["evidence"].append(
                candidate["evidence"]
            )

            deduplicated[key]["signal_strength"] = max(
                deduplicated[key]["signal_strength"],
                candidate["signal_strength"]
            )

    return list(deduplicated.values())


if __name__ == "__main__":
    company = "HSBC"

    signals = deduplicate_signals(company)

    print(f"\nDEDUPLICATED SIGNALS — {company}")
    print("=" * 70)

    print(f"\nUnique signals: {len(signals)}")

    for signal in signals:
        print("\nSignal:", signal["signal_type"])
        print("Title:", signal["signal_title"])
        print("Strength:", signal["signal_strength"])
        print("Confidence:", signal["confidence"])
        print("Use case:", signal["suggested_use_case"])
        print("Supporting sources:", len(signal["sources"]))

        for source in signal["sources"]:
            print("  -", source)

        print("-" * 70)