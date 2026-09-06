SECTORS = [
    "bank",
    "building_society",
    "insurer",
    "insurance_broker",
    "wealth_manager",
    "asset_manager",
    "payments",
    "fintech",
    "specialty_finance",
    "credit_management",
    "financial_market_infrastructure",
    "financial_services_technology",
    "other_financial_services",
]

SIGNAL_TYPES = [
    "cloud_transformation",
    "cloud_migration",
    "multi_cloud_adoption",
    "infrastructure_modernisation",
    "it_outage",
    "service_disruption",
    "incident_management_pressure",
    "sre_hiring",
    "devops_hiring",
    "cloud_hiring",
    "infrastructure_hiring",
    "ai_hiring",
    "cost_reduction",
    "operational_efficiency",
    "restructuring",
    "automation_programme",
    "ai_adoption",
    "agentic_ai_initiative",
    "ai_governance_initiative",
    "operational_resilience",
    "dora_programme",
    "regulatory_change",
    "managed_services",
    "outsourcing_change",
    "vendor_change",
    "technology_investment",
    "digital_transformation",
    "leadership_change",
    "new_cto",
    "new_cio",
    "acquisition",
    "merger",
    "rapid_growth",
    "other",
]

PERSONA_TYPES = [
    "economic_buyer",
    "technical_buyer",
    "business_buyer",
    "champion",
    "influencer",
    "user",
    "blocker",
    "procurement",
    "risk_approver",
    "unknown",
]

CONFIDENCE_LEVELS = [
    "high",
    "medium",
    "low",
    "unverified",
]

ACCOUNT_TIERS = [
    "tier_1",
    "tier_2",
    "tier_3",
    "deprioritised",
]

PIPELINE_STAGES = [
    "target",
    "researched",
    "qualified",
    "contact_identified",
    "outreach_ready",
    "contacted",
    "engaged",
    "discovery_booked",
    "discovery_completed",
    "qualified_opportunity",
    "solution_discussion",
    "pilot_discussion",
    "proposal",
    "negotiation",
    "closed_won",
    "closed_lost",
    "nurture",
    "disqualified",
]

FIREMIND_USE_CASES = [
    "incident_lifecycle_management",
    "ict_incident_classification",
    "dora_reporting",
    "audit_evidence_collection",
    "access_recertification",
    "joiner_mover_leaver",
    "reconciliation",
    "cloud_operations",
    "finops",
    "other_autonomous_operations",
    "unknown",
]

# How this account entered the pipeline.
# Firemind is an AWS consulting partner with an existing customer base, and
# expansion into it is a cheaper motion than net-new acquisition: the
# commercial relationship exists, the data estate is already understood, and
# procurement has been through once already.
ACCOUNT_SOURCES = [
    "existing_customer",    # already a consulting client
    "partner_sourced",      # AWS co-sell, marketplace or partner referral
    "net_new",              # cold, sourced from public signals
    "unknown",
]
