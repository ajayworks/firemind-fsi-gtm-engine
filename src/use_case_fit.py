"""
Four-dimension use-case fit screen.

This is the scoring model from the buyer-side study: a workflow is sellable
only where all four conditions hold at once.

The four dimensions split into two kinds, and the split matters:

  WORKFLOW properties  - intrinsic to the task, constant across accounts.
                         Derived from interview and survey evidence.
      verifiability     can a supervisor confirm the end-state was correct
                        WITHOUT re-performing the work?
      permission_ceiling how much autonomy would a regulated firm actually
                        authorise for this task?

  ACCOUNT properties   - vary by company, derived from collected evidence.
      data_readiness    is the underlying data complete and structured enough?
      system_reachability can the engine actually connect to the systems
                        where this work happens?

Capability adds. Permission multiplies. Readiness gates.
A workflow nobody will authorise is worth nothing regardless of how well
the engine performs it.
"""

# ---------------------------------------------------------------------------
# WORKFLOW PROPERTIES - from the research, not from the account
# ---------------------------------------------------------------------------
# verifiability      0-7   outcome checkable without redoing the work
# permission_ceiling 0-5   autonomy a regulated firm would actually grant
#
# The tier-1 group scores high on both: internal, IT-adjacent work with a
# checkable end-state. Customer-facing and judgement-bearing work scores
# high on capability but is capped hard by permission - the central finding.

USE_CASE_PROPERTIES = {
    # --- Tier 1: verifiable end-state, reachable systems, internal work ---
    "incident_lifecycle_management": {"verifiability": 7, "permission_ceiling": 4},
    "ict_incident_classification":   {"verifiability": 7, "permission_ceiling": 4},
    "audit_evidence_collection":     {"verifiability": 7, "permission_ceiling": 4},
    "dora_reporting":                {"verifiability": 6, "permission_ceiling": 4},

    # --- Tier 2: reinstated after the partner confirmed identity-system
    #     connectivity (Active Directory / Entra / Okta / SailPoint) ---
    "access_recertification":        {"verifiability": 6, "permission_ceiling": 3},
    "joiner_mover_leaver":           {"verifiability": 6, "permission_ceiling": 3},

    # --- Tier 3: verifiable, but touches financial records ---
    "reconciliation":                {"verifiability": 6, "permission_ceiling": 2},

    # --- Adjacent: not validated by this research. Scored conservatively
    #     so it cannot outrank an evidenced tier-1 workflow. ---
    "cloud_operations":              {"verifiability": 5, "permission_ceiling": 3},
    "finops":                        {"verifiability": 5, "permission_ceiling": 3},

    "other_autonomous_operations":   {"verifiability": 3, "permission_ceiling": 2},
    "unknown":                       {"verifiability": 0, "permission_ceiling": 0},
}

# Permission acts as a ceiling on the whole score, not as an addend.
# NOTE: a ceiling of 5 is intentionally unreachable for every use case in
# the map above. Only ~10% of survey ratings permitted unsupervised action,
# and none of it in a workflow with external consequence. The level exists
# in the scale because the model should be able to represent it, not
# because any workflow currently earns it.
PERMISSION_MULTIPLIER = {
    0: 0.00,   # would not be authorised at all
    1: 0.30,   # suggestion only
    2: 0.50,   # recommend, human executes
    3: 0.70,   # act with approval on every action
    4: 0.85,   # act with post-hoc review
    5: 1.00,   # act unsupervised within defined bounds
}

# Evidence that the systems this use case runs in are reachable.
USE_CASE_SYSTEM_SIGNALS = {
    "incident_lifecycle_management": ["it_outage", "service_disruption",
                                      "incident_management_pressure", "sre_hiring",
                                      "devops_hiring"],
    "ict_incident_classification":   ["it_outage", "operational_resilience",
                                      "dora_programme"],
    "dora_reporting":                ["dora_programme", "operational_resilience",
                                      "regulatory_change"],
    "audit_evidence_collection":     ["operational_resilience", "regulatory_change",
                                      "dora_programme"],
    "access_recertification":        ["regulatory_change", "restructuring",
                                      "acquisition", "merger"],
    "joiner_mover_leaver":           ["restructuring", "rapid_growth",
                                      "acquisition", "merger"],
    "reconciliation":                ["cost_reduction", "operational_efficiency"],
    "cloud_operations":              ["cloud_transformation", "cloud_migration",
                                      "multi_cloud_adoption",
                                      "infrastructure_modernisation"],
    "finops":                        ["cost_reduction", "cloud_transformation"],
}


def score_data_readiness(company, signals):
    """
    0-9. Can the data support the work at all?

    Section 6: data readiness gates feasibility BEFORE governance gates
    permission. An account with no evidence of a modern data estate cannot
    run autonomous operations however willing it is.
    """
    score = 0

    # Platform maturity - a proxy for structured, accessible operational data
    cloud = company["cloud_score"] or 0
    infra = company["infra_score"] or 0
    score += min((cloud + infra) / 4.0, 5)

    # An in-house technical team maintains the data that automation depends on
    if (company["technical_team_score"] or 0) >= 5:
        score += 2
    elif (company["technical_team_score"] or 0) >= 2:
        score += 1

    # Active modernisation implies the estate is being made tractable
    types = {s["signal_type"] for s in signals}
    if types & {"infrastructure_modernisation", "cloud_migration",
                "digital_transformation"}:
        score += 2

    return min(round(score, 2), 9)


def score_system_reachability(company, signals, use_case):
    """
    0-9. Can the engine connect to where this work actually happens?

    Evidence-led: a use case is reachable where the account shows signals
    from the systems that use case runs in.
    """
    relevant = USE_CASE_SYSTEM_SIGNALS.get(use_case, [])
    types = {s["signal_type"] for s in signals}

    matches = len(types & set(relevant))

    if matches >= 3:
        score = 7
    elif matches == 2:
        score = 5
    elif matches == 1:
        score = 3
    else:
        score = 0

    # Cloud-hosted estates are reachable by API rather than by project
    if (company["cloud_score"] or 0) >= 6:
        score += 2

    return min(score, 9)


def calculate_use_case_fit_for_account(company, signals, use_case):
    """
    Returns (fit_score, breakdown_dict).

    The breakdown is returned so the app can show WHY an account scored as
    it did. Section 6: transparency has to be intelligibility, not disclosure
    - a number with no reasoning behind it does not earn trust.
    """
    props = USE_CASE_PROPERTIES.get(use_case, USE_CASE_PROPERTIES["unknown"])

    verifiability = props["verifiability"]
    permission_ceiling = props["permission_ceiling"]
    data_readiness = score_data_readiness(company, signals)
    system_reachability = score_system_reachability(company, signals, use_case)

    breakdown = {
        "verifiability": verifiability,
        "permission_ceiling": permission_ceiling,
        "data_readiness": data_readiness,
        "system_reachability": system_reachability,
        "gated": False,
        "gate_reason": None,
    }

    # ---- Gate 1: feasibility ------------------------------------------------
    if data_readiness < 3:
        breakdown["gated"] = True
        breakdown["gate_reason"] = (
            "Insufficient evidence of a data estate that could support "
            "autonomous execution."
        )
        return 0.0, breakdown

    if system_reachability < 3:
        breakdown["gated"] = True
        breakdown["gate_reason"] = (
            "No evidence the engine could reach the systems this workflow "
            "runs in."
        )
        return 0.0, breakdown

    # ---- Capability adds ----------------------------------------------------
    raw = verifiability + data_readiness + system_reachability   # max 25

    # ---- Permission multiplies ---------------------------------------------
    multiplier = PERMISSION_MULTIPLIER.get(permission_ceiling, 0.5)
    fit = min(round(raw * multiplier, 2), 25)

    breakdown["raw_capability"] = round(raw, 2)
    breakdown["permission_multiplier"] = multiplier

    return fit, breakdown


def best_use_case_by_fit(company, signals, candidate_use_cases=None):
    """
    Picks the use case with the highest fit for THIS account.

    Replaces keyword counting: a use case now wins because the account can
    actually run it and would authorise it, not because matching words
    appeared in the news.
    """
    if candidate_use_cases is None:
        candidate_use_cases = [
            uc for uc in USE_CASE_PROPERTIES
            if uc not in ("unknown", "other_autonomous_operations")
        ]

    results = {}
    for uc in candidate_use_cases:
        fit, breakdown = calculate_use_case_fit_for_account(company, signals, uc)
        results[uc] = {"fit": fit, "breakdown": breakdown}

    best = max(results, key=lambda uc: results[uc]["fit"])

    return best, results[best]["fit"], results[best]["breakdown"], results
