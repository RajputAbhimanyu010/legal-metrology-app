"""
Rules Engine — Owned by: Abhimanyu
Purpose: Take extracted OCR text + text blocks, check against
Legal Metrology (Packaged Commodities) Rules 2011, return a
compliance checklist.

Fill in / refine the regex patterns using Anshi's checklist doc.
"""

import re


# ---- Font size thresholds (mm) from the Rules Schedule ----
# TODO: Anshi to confirm exact values — placeholder structure below.
FONT_SIZE_RULES = [
    {"max_quantity_g_ml": 200, "min_height_mm": 1},
    {"max_quantity_g_ml": 500, "min_height_mm": 2},
    {"max_quantity_g_ml": 1000, "min_height_mm": 4},
    {"max_quantity_g_ml": float("inf"), "min_height_mm": 6},
]


def check_mrp(full_text: str):
    has_mrp = bool(re.search(r'\bM\.?R\.?P\.?\b|\bMaximum Retail Price\b', full_text, re.IGNORECASE))
    has_tax_line = bool(re.search(r'inclusive of all taxes', full_text, re.IGNORECASE))
    if not has_mrp:
        return {"field": "MRP", "status": "FAIL", "detail": "MRP not found on label"}
    if not has_tax_line:
        return {"field": "MRP", "status": "WARN", "detail": "MRP found but missing 'Inclusive of all taxes'"}
    return {"field": "MRP", "status": "PASS", "detail": "MRP present with tax declaration"}


def check_net_quantity(full_text: str):
    match = re.search(r'(\d+(\.\d+)?)\s?(g|kg|ml|l|gm|litre|liter)\b', full_text, re.IGNORECASE)
    if match:
        return {"field": "Net Quantity", "status": "PASS", "detail": f"Found: {match.group(0)}"}
    return {"field": "Net Quantity", "status": "FAIL", "detail": "Net quantity not found"}


def check_mfg_date(full_text: str):
    # matches things like 05/2024, May 2024, 2024-05 etc.
    patterns = [
        r'\b(0[1-9]|1[0-2])[/-]\d{4}\b',
        r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s?\d{4}\b',
    ]
    for p in patterns:
        if re.search(p, full_text, re.IGNORECASE):
            return {"field": "Manufacture Date", "status": "PASS", "detail": "Date found"}
    return {"field": "Manufacture Date", "status": "FAIL", "detail": "Month/Year of manufacture not found"}


def check_consumer_care(full_text: str):
    has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', full_text))
    has_phone = bool(re.search(r'(\+?91[-\s]?)?(\d[-\s]?){10}', full_text))
    if has_email or has_phone:
        return {"field": "Consumer Care", "status": "PASS", "detail": "Contact info found"}
    return {"field": "Consumer Care", "status": "FAIL", "detail": "No phone/email found for consumer complaints"}


def check_manufacturer_info(full_text: str):
    # crude heuristic — looks for common keywords indicating manufacturer block
    if re.search(r'(Manufactured by|Marketed by|Packed by|Mfg\.? by)', full_text, re.IGNORECASE):
        return {"field": "Manufacturer Info", "status": "PASS", "detail": "Manufacturer declaration found"}
    return {"field": "Manufacturer Info", "status": "FAIL", "detail": "Manufacturer/packer name & address not found"}


def check_country_of_origin(full_text: str):
    if re.search(r'(Country of Origin|Made in)', full_text, re.IGNORECASE):
        return {"field": "Country of Origin", "status": "PASS", "detail": "Found"}
    return {"field": "Country of Origin", "status": "INFO", "detail": "Not found — only required for imported goods"}


def run_all_checks(full_text: str):
    """Runs every check and returns a list of results — this is what the API returns."""
    checks = [
        check_manufacturer_info(full_text),
        check_net_quantity(full_text),
        check_mrp(full_text),
        check_mfg_date(full_text),
        check_consumer_care(full_text),
        check_country_of_origin(full_text),
    ]

    total = len([c for c in checks if c["status"] in ("PASS", "FAIL")])
    passed = len([c for c in checks if c["status"] == "PASS"])
    score = round((passed / total) * 100, 1) if total else 0

    return {
        "checks": checks,
        "compliance_score": score,
        "overall_status": "COMPLIANT" if score == 100 else "NON-COMPLIANT"
    }


# Quick manual test
if __name__ == "__main__":
    sample_text = """
    Marketed by ABC Foods Pvt Ltd, Delhi.
    Net Wt: 500g
    MRP Rs 120 Inclusive of all taxes
    Mfg Date: 05/2024
    Customer Care: 1800-123-4567
    """
    result = run_all_checks(sample_text)
    import json
    print(json.dumps(result, indent=2))
