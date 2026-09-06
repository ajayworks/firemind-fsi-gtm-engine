def infer_sector(company_name):
    name = company_name.lower()

    if "building society" in name:
        return "building_society"

    if "bank" in name or "banking" in name:
        return "bank"

    if "insurance" in name or "assurance" in name:
        return "insurer"

    if "wealth" in name:
        return "wealth_manager"

    if "asset management" in name:
        return "asset_manager"

    if "payments" in name or "payment" in name:
        return "payments"

    return "other_financial_services"