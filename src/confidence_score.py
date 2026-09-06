SIGNAL_CONFIDENCE_WEIGHTS = {
    "high": 1.0,
    "medium": 0.65,
    "low": 0.30,
    "unverified": 0.0,
}

SOURCE_RELIABILITY_WEIGHTS = {
    "primary": 1.0,
    "high": 0.85,
    "medium": 0.65,
    "low": 0.30,
    None: 0.40,
}


def calculate_account_confidence(signals):
    if not signals:
        return "low"

    scores = []

    for signal in signals:
        signal_confidence = SIGNAL_CONFIDENCE_WEIGHTS.get(
            signal.get("confidence", "unverified"),
            0
        )

        source_reliability = SOURCE_RELIABILITY_WEIGHTS.get(
            signal.get("source_reliability"),
            0.40
        )

        combined = (
            signal_confidence * 0.65
            + source_reliability * 0.35
        )

        scores.append(combined)

    average = sum(scores) / len(scores)

    # Evidence coverage bonus
    if len(signals) >= 5:
        coverage_bonus = 0.10
    elif len(signals) >= 3:
        coverage_bonus = 0.06
    elif len(signals) >= 2:
        coverage_bonus = 0.03
    else:
        coverage_bonus = 0

    adjusted = min(
        average + coverage_bonus,
        1.0
    )

    if adjusted >= 0.80:
        return "high"

    elif adjusted >= 0.55:
        return "medium"

    return "low"