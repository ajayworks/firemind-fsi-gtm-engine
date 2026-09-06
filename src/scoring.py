from datetime import date


CONFIDENCE_MULTIPLIER = {
    "high": 1.0,
    "medium": 0.75,
    "low": 0.40,
    "unverified": 0.0,
}

STRENGTH_MULTIPLIER = {
    1: 0.25,
    2: 0.50,
    3: 0.75,
    4: 1.00,
    5: 1.25,
}


def freshness_multiplier(signal_date):
    if not signal_date:
        return 0.5

    age_days = (date.today() - signal_date).days

    if age_days <= 90:
        return 1.0
    elif age_days <= 180:
        return 0.8
    elif age_days <= 365:
        return 0.6
    elif age_days <= 730:
        return 0.3
    else:
        return 0.1


def calculate_scale_score(
    employees,
    countries_operated,
    technology_scale_score=0
):
    """
    Operational footprint: 0-15.

    Deliberately NOT a proxy for headcount. Headcount determines whether an
    account is in the ICP at all, and that is applied as a multiplier in
    calculate_total_score() - scoring it here too would penalise the same
    fact twice.

    What this measures is how much operational surface area exists to
    automate: jurisdictions, and the scale of the technology estate.
    """
    # Multi-jurisdiction operations create regulatory and reporting overhead -
    # the pain this product addresses. But a 60-country footprint means a
    # global procurement function and a much longer path to a first deal.
    if 2 <= countries_operated <= 10:
        geography_score = 8

    elif 11 <= countries_operated <= 25:
        geography_score = 5

    elif countries_operated == 1:
        geography_score = 4

    elif countries_operated > 25:
        geography_score = 2

    else:
        geography_score = 0

    return min(geography_score + (technology_scale_score or 0), 15)


def calculate_technology_score(cloud_score, infra_score, technical_team_score):
    return min(
        cloud_score + infra_score + technical_team_score,
        25
    )


PAIN_SIGNAL_WEIGHTS = {
    # DORA and regulatory change are the obligations that actually bind here.
    # The EU AI Act is deliberately absent: it was deferred, and these
    # workflows are not Annex III high-risk use cases. Selling on the AI Act
    # was the positioning error the research corrected.
    "dora_programme": 7,
    "regulatory_change": 5,
    "ai_governance_initiative": 3,
    "it_outage": 8,
    "service_disruption": 6,
    "incident_management_pressure": 7,
    "cost_reduction": 5,
    "operational_efficiency": 4,
    "restructuring": 4,
    "sre_hiring": 3,
    "devops_hiring": 2,
    "cloud_hiring": 2,
    "infrastructure_hiring": 3,
    "managed_services": 3,
    "outsourcing_change": 3,
    "operational_resilience": 4,
}


# Only the strongest N signals count. Without this cap, operational pain
# measures PRESS COVERAGE rather than pain: large institutions generate far
# more public reporting, so they accumulate more signals and out-score
# mid-size firms that have the same problems and less journalism about them.
# Observed in the demo data: >50k-employee firms averaged 5.75 signals
# against 1.9 for mid-size, producing 4x the pain score.
MAX_SCORING_SIGNALS_PAIN = 4
MAX_SCORING_SIGNALS_TIMING = 3


def calculate_operational_pain(signals):
    scored = []

    for signal in signals:
        base_weight = PAIN_SIGNAL_WEIGHTS.get(signal["signal_type"], 0)

        strength = STRENGTH_MULTIPLIER.get(
            signal.get("signal_strength", 1), 0.25
        )

        confidence = CONFIDENCE_MULTIPLIER.get(
            signal.get("confidence", "unverified"), 0
        )

        freshness = freshness_multiplier(
            signal.get("signal_date")
        )

        points = base_weight * strength * confidence * freshness
        scored.append(points)

    # Strength of the best evidence, not volume of evidence
    top = sorted(scored, reverse=True)[:MAX_SCORING_SIGNALS_PAIN]

    return min(round(sum(top), 2), 25)


TIMING_SIGNAL_WEIGHTS = {
    "new_cto": 2,
    "new_cio": 2,
    "leadership_change": 1,
    "cloud_transformation": 2,
    "cloud_migration": 2,
    "infrastructure_modernisation": 2,
    "automation_programme": 2,
    "ai_adoption": 2,
    "agentic_ai_initiative": 2,
    "operational_resilience": 2,
    "dora_programme": 2,
    "it_outage": 2,
    "service_disruption": 2,
    "technology_investment": 1,
    "managed_services": 1,
    "vendor_change": 2,
    "outsourcing_change": 2,
    "acquisition": 1,
    "merger": 1,
}


def calculate_timing_score(signals):
    scored = []

    for signal in signals:
        base_weight = TIMING_SIGNAL_WEIGHTS.get(signal["signal_type"], 0)

        confidence = CONFIDENCE_MULTIPLIER.get(
            signal.get("confidence", "unverified"), 0
        )

        freshness = freshness_multiplier(
            signal.get("signal_date")
        )

        scored.append(base_weight * confidence * freshness)

    top = sorted(scored, reverse=True)[:MAX_SCORING_SIGNALS_TIMING]

    return min(round(sum(top), 2), 10)


def calculate_use_case_fit(
    verifiability,
    data_readiness,
    system_reachability,
    permission_ceiling
):
    """
    Capability adds. Permission multiplies. Readiness gates.

    Kept for direct/manual scoring. The pipeline calls
    use_case_fit.calculate_use_case_fit_for_account(), which derives these
    four inputs from account evidence rather than taking them as arguments.
    """
    from src.use_case_fit import PERMISSION_MULTIPLIER

    # Gate: no usable data or no reachable system means no deal, regardless
    # of how verifiable or permissible the workflow is in principle.
    if data_readiness < 3 or system_reachability < 3:
        return 0.0

    raw = verifiability + data_readiness + system_reachability

    multiplier = PERMISSION_MULTIPLIER.get(permission_ceiling, 0.5)

    return min(round(raw * multiplier, 2), 25)


# ICP fit acts on the whole score, not as one component among five.
#
# The partner defined the segment at touchpoint 1: 200-2,000 staff, >=~$100M
# revenue, already comfortable buying vendor services. An organisation outside
# that band is not a weaker prospect - it is a DIFFERENT SALES MOTION.
# A 90,000-person bank has procurement cycles measured in quarters, incumbent
# vendors and an internal platform team that would build this instead.
#
# Treating ICP as 15 of 100 points let large institutions out-rank the target
# segment on evidence volume alone. Treating it as a multiplier makes the
# segment structural - the same shape as the permission ceiling in
# use_case_fit.py, and for the same reason: some constraints cap what an
# opportunity can be worth rather than contributing points to it.
ICP_MULTIPLIER = {
    "core":        1.00,   # 200-2,000 staff - the stated ICP
    "adjacent":    0.75,   # 2,000-5,000 - viable, longer cycle
    "upper_mid":   0.50,   # 5,000-15,000 - stretch
    "enterprise":  0.25,   # >15,000 - different motion entirely
    "too_small":   0.30,   # <200 - unlikely to have the volume or budget
    "unknown":     0.50,   # headcount not established - qualify before working
}


def icp_band(employees):
    """Which segment band an account falls into, per the partner's ICP."""
    if not employees:
        return "unknown"
    if 200 <= employees <= 2000:
        return "core"
    if 2000 < employees <= 5000:
        return "adjacent"
    if 5000 < employees <= 15000:
        return "upper_mid"
    if employees > 15000:
        return "enterprise"
    return "too_small"


# Relationship acts on the whole score rather than adding to it, because an
# existing commercial relationship shortens EVERY stage of the funnel - it
# does not contribute a fixed number of points at one stage.
SOURCE_MULTIPLIER = {
    "existing_customer": 1.35,
    "partner_sourced": 1.15,
    "net_new": 1.00,
    "unknown": 1.00,
}


def apply_source_multiplier(total, account_source):
    """Expansion and partner-sourced accounts outrank equivalent cold ones."""
    return round(total * SOURCE_MULTIPLIER.get(account_source or "unknown", 1.0), 2)


def assign_tier(score):
    # Calibrated against the observed score distribution rather than an
    # arbitrary /100 scale. Thresholds set so roughly the top quartile is
    # tier_1: a prioritisation tool that deprioritises most of its own
    # pipeline gives the user nothing to act on.
    # Calibrated against the current pipeline. These need one recalibration
    # after the account list is enriched - the ICP segment is precisely the
    # segment public reporting covers worst, so scores are depressed until
    # research coverage improves.
    if score >= 30:
        return "tier_1"
    elif score >= 22:
        return "tier_2"
    elif score >= 14:
        return "tier_3"
    else:
        return "deprioritised"


def calculate_total_score(
    scale_score,
    technology_score,
    operational_pain_score,
    use_case_fit_score,
    timing_score,
    account_source="unknown",
    employees=0
):
    base = (
        scale_score
        + technology_score
        + operational_pain_score
        + use_case_fit_score
        + timing_score
    )

    band = icp_band(employees)
    icp_mult = ICP_MULTIPLIER[band]
    source_mult = SOURCE_MULTIPLIER.get(account_source or "unknown", 1.0)

    total = round(base * icp_mult * source_mult, 2)

    return {
        "base_score": round(base, 2),
        "icp_band": band,
        "icp_multiplier": icp_mult,
        "account_source": account_source or "unknown",
        "source_multiplier": source_mult,
        "total_score": total,
        "tier": assign_tier(total),
    }


if __name__ == "__main__":
    test_signals = [
        {
            "signal_type": "it_outage",
            "signal_strength": 4,
            "confidence": "high",
            "signal_date": date(2026, 8, 15),
        },
        {
            "signal_type": "cloud_transformation",
            "signal_strength": 3,
            "confidence": "high",
            "signal_date": date(2026, 7, 1),
        },
    ]

    scale = calculate_scale_score(
        employees=5000,
        countries_operated=5,
        technology_scale_score=5
    )

    technology = calculate_technology_score(
        cloud_score=8,
        infra_score=8,
        technical_team_score=5
    )

    pain = calculate_operational_pain(test_signals)

    use_case = calculate_use_case_fit(
        verifiability=7,
        data_readiness=5,
        system_reachability=5,
        permission_ceiling=4
    )

    timing = calculate_timing_score(test_signals)

    result = calculate_total_score(
        scale,
        technology,
        pain,
        use_case,
        timing
    )

    print("Scale:", scale)
    print("Technology:", technology)
    print("Operational pain:", pain)
    print("Use-case fit:", use_case)
    print("Timing:", timing)
    print("Final result:", result)