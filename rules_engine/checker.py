"""
Rules Engine — Owned by: Abhimanyu (built on Anshi's legal research)
Purpose: Take extracted OCR text + text blocks, check against
Legal Metrology (Packaged Commodities) Rules 2011, return a
compliance checklist.

Source: https://consumeraffairs.gov.in/pages/legal-metrology-act
        Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6 & Rule 7
        + official FAQs issued by Dept. of Consumer Affairs, Legal Metrology
        Division (latest update referenced: Nov 2025)

NOTE ON SCOPE: The Rules have many amendments (2017 country-of-origin
insertion, 2017 font-size table substitution, 2026 e-commerce amendment,
etc.). The values below reflect the Rule 6/7 text as commonly published
and cited in the official FAQs at the time of writing. For a real
enforcement tool this should be re-verified against the latest
consolidated/amended text on indiacode.nic.in before production use —
flagging this explicitly in the PPT as a known limitation is honest and
expected at this stage.
"""

import re


# ---- Font size thresholds (Rule 7(2) + Table-I) ----
# Table-I: Minimum height of NUMERAL, when net quantity is declared by
# weight or volume. Two columns: "normal case" vs "when blown, formed,
# molded, embossed or perforated on container" (e.g. glass bottles).
# We check against the NORMAL CASE numbers since that's what a printed
# paper/plastic label almost always is.
#   Sr.1: Up to 200 g/ml                -> 1mm  (2mm if embossed/blown etc.)
#   Sr.2: Above 200 g/ml, up to 500g/ml -> 2mm  (4mm if embossed/blown etc.)
#   Sr.3: Above 500 g/ml                -> 4mm  (6mm if embossed/blown etc.)
# There is NO separate "above 1kg" tier — above 500g/ml is one single tier.
FONT_SIZE_RULES = [
    {"max_quantity_g_ml": 200, "min_height_mm": 1, "min_height_mm_embossed": 2},
    {"max_quantity_g_ml": 500, "min_height_mm": 2, "min_height_mm_embossed": 4},
    {"max_quantity_g_ml": float("inf"), "min_height_mm": 4, "min_height_mm_embossed": 6},
]

# Rule 7(3): general (non-numeral) letters in any declaration — separate,
# lower bar than the numeral table above.
MIN_LETTER_HEIGHT_MM = 1
MIN_LETTER_HEIGHT_MM_EMBOSSED = 2

# Per official FAQ: the numeral-height requirement applies ONLY to the MRP
# VALUE itself (e.g. the "120" in "MRP Rs 120"), not to prefix/suffix text
# like "MRP Rs." or "Inclusive of all taxes" — those just need the general
# 1mm letter-height minimum, not the Table-I numeral minimum.

# ---- Per-photo calibration using an Indian coin ----
# Indian coins are minted to fixed, government-standardized diameters, so
# any coin of a given denomination is a reliable size reference. The user
# places one coin next to the label in the photo, selects which coin it
# was, then taps its left and right edge — we use that to calculate
# pixels_per_mm for THIS photo specifically.
COIN_DIAMETERS_MM = {
    "₹1": 21.93,
    "₹2": 27.0,
    "₹5": 23.0,
    "₹10": 27.0,
}
DEFAULT_COIN = "₹5"


def calculate_pixels_per_mm(coin_left_x: float, coin_right_x: float, coin_type: str = DEFAULT_COIN) -> float:
    """
    coin_left_x, coin_right_x: pixel x-coordinates the user tapped on the
    left and right edge (diameter) of the coin in the uploaded photo.
    coin_type: which coin was used, e.g. "₹5" — looked up in COIN_DIAMETERS_MM.
    """
    coin_diameter_mm = COIN_DIAMETERS_MM.get(coin_type, COIN_DIAMETERS_MM[DEFAULT_COIN])
    coin_pixel_width = abs(coin_right_x - coin_left_x)
    if coin_pixel_width == 0:
        return None
    return coin_pixel_width / coin_diameter_mm


def get_min_font_height_mm(net_quantity_value: float) -> float:
    """Looks up the minimum required letter height (mm) for a given net quantity."""
    for rule in FONT_SIZE_RULES:
        if net_quantity_value <= rule["max_quantity_g_ml"]:
            return rule["min_height_mm"]
    return FONT_SIZE_RULES[-1]["min_height_mm"]


def check_font_size(text_blocks: list, net_quantity_value: float = None, pixels_per_mm: float = None):
    """
    text_blocks: list of {"text": str, "bbox": [[x,y],...], "confidence": float}
                 — this is exactly what ocr/extract_text.py returns.
    net_quantity_value: the numeric net quantity (e.g., 500 for "500g"),
                         used to look up which threshold applies.
    pixels_per_mm: calculated per-photo from the card calibration
                   (see calculate_pixels_per_mm). If not provided,
                   font-size check is skipped.
    """
    if not text_blocks:
        return {"field": "Font Size", "status": "INFO", "detail": "No text blocks provided to check"}

    if net_quantity_value is None:
        return {"field": "Font Size", "status": "INFO", "detail": "Net quantity unknown — cannot determine required font size"}

    if not pixels_per_mm:
        return {"field": "Font Size", "status": "INFO", "detail": "No card calibration provided — tap the card edges to enable font-size check"}

    min_required_mm = get_min_font_height_mm(net_quantity_value)

    # Find blocks that look like they contain MRP or quantity (the declarations
    # this rule actually applies to) rather than checking every word on the label
    relevant_blocks = [
        b for b in text_blocks
        if re.search(r'(MRP|M\.R\.P|Rs\.?|\d+\s?(g|kg|ml|l)\b)', b["text"], re.IGNORECASE)
    ]

    if not relevant_blocks:
        return {"field": "Font Size", "status": "INFO", "detail": "Could not locate MRP/quantity text block to measure"}

    smallest_found_mm = None
    for block in relevant_blocks:
        ys = [point[1] for point in block["bbox"]]
        pixel_height = max(ys) - min(ys)
        real_height_mm = round(pixel_height / pixels_per_mm, 2)
        if smallest_found_mm is None or real_height_mm < smallest_found_mm:
            smallest_found_mm = real_height_mm

    if smallest_found_mm >= min_required_mm:
        return {
            "field": "Font Size",
            "status": "PASS",
            "detail": f"Text height ~{smallest_found_mm}mm meets minimum {min_required_mm}mm"
        }
    return {
        "field": "Font Size",
        "status": "FAIL",
        "detail": f"Text height ~{smallest_found_mm}mm is below required minimum {min_required_mm}mm"
    }


def check_mrp(full_text: str):
    """
    Rule 6(1)(f): retail sale price must be declared, inclusive of all taxes.
    Per official FAQ (Q.44): the letter case for "inclusive of all taxes"
    may be upper, lower, or sentence case — no fixed case is mandated, so
    the regex below is intentionally case-insensitive.
    """
    has_mrp = bool(re.search(r'\bM\.?R\.?P\.?\b|\bMaximum Retail Price\b', full_text, re.IGNORECASE))
    has_tax_line = bool(re.search(r'inclusive of all taxes', full_text, re.IGNORECASE))
    if not has_mrp:
        return {"field": "MRP", "status": "FAIL", "detail": "MRP not found on label"}
    if not has_tax_line:
        return {"field": "MRP", "status": "WARN", "detail": "MRP found but missing 'Inclusive of all taxes' declaration"}
    return {"field": "MRP", "status": "PASS", "detail": "MRP present with tax declaration"}


def check_net_quantity(full_text: str):
    """
    Rule 6(1)(c): net quantity must be declared in the STANDARD unit of
    weight or measure (g/kg for weight, ml/l for volume), or as a count
    if sold by number. Vague terms like "approx" or "around" are not
    compliant (Numeration Rules, 2011) — flagged separately below.
    """
    match = re.search(r'(\d+(\.\d+)?)\s?(g|kg|ml|l|gm|litre|liter)\b', full_text, re.IGNORECASE)
    has_vague_qualifier = bool(re.search(r'\b(approx|approximately|around|about)\b', full_text, re.IGNORECASE))

    if not match:
        return {"field": "Net Quantity", "status": "FAIL", "detail": "Net quantity not found"}
    if has_vague_qualifier:
        return {"field": "Net Quantity", "status": "WARN", "detail": f"Found '{match.group(0)}' but label uses a vague qualifier (e.g. 'approx') which is not permitted"}
    return {"field": "Net Quantity", "status": "PASS", "detail": f"Found: {match.group(0)}"}


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
    """
    Rule 6(2): every package shall bear the NAME, ADDRESS, TELEPHONE NUMBER,
    and E-MAIL ADDRESS of the person/office to contact for consumer
    complaints. Strictly, all four are required — but the official FAQs
    treat "a non-functional phone number or missing email" as the most
    common real-world violation, so we check for phone AND email
    specifically (both, not just one) and flag partial info as WARN.
    """
    has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', full_text))
    has_phone = bool(re.search(r'(\+?91[-\s]?)?(\d[-\s]?){10}', full_text))

    if has_email and has_phone:
        return {"field": "Consumer Care", "status": "PASS", "detail": "Both phone and email found"}
    if has_email or has_phone:
        missing = "phone number" if has_email else "email address"
        return {"field": "Consumer Care", "status": "WARN", "detail": f"Found only one contact method — {missing} appears to be missing"}
    return {"field": "Consumer Care", "status": "FAIL", "detail": "No phone/email found for consumer complaints"}


def check_manufacturer_info(full_text: str):
    """
    Rule 6(1)(a): name & address of manufacturer; if manufacturer isn't
    the packer, both manufacturer AND packer; for imported goods, the
    importer's name & address (country of origin is checked separately —
    per official FAQ, importer details + country of origin together are
    sufficient for imported products, the foreign manufacturer's address
    is not required).
    Explanation I to Rule 6(1)(a): if a name/address appears WITHOUT the
    qualifying words "manufactured by"/"packed by", it is presumed to be
    the manufacturer's — so a bare company name+address can also count,
    but we flag it as a WARN since it's ambiguous without explicit wording.
    """
    if re.search(r'(Manufactured by|Marketed by|Packed by|Mfg\.? by|Imported by)', full_text, re.IGNORECASE):
        return {"field": "Manufacturer Info", "status": "PASS", "detail": "Manufacturer/packer/importer declaration found"}
    return {"field": "Manufacturer Info", "status": "FAIL", "detail": "Manufacturer/packer/importer name & address not found"}


def check_country_of_origin(full_text: str):
    """
    Rule 6(1)(aa) (inserted 2017): country of origin/manufacture/assembly
    is mandatory ONLY for imported products. Domestic (India-made) products
    are NOT required to declare it (per official FAQ), though some do so
    voluntarily. Since OCR text alone can't tell us if a product is
    imported, absence of this field is informational, not a violation,
    unless other signals (e.g. importer name, foreign address) suggest
    the product is imported.
    """
    if re.search(r'(Country of Origin|Made in|Manufactured in)', full_text, re.IGNORECASE):
        return {"field": "Country of Origin", "status": "PASS", "detail": "Found"}
    is_likely_imported = bool(re.search(r'Imported by', full_text, re.IGNORECASE))
    if is_likely_imported:
        return {"field": "Country of Origin", "status": "FAIL", "detail": "Label indicates an importer but no Country of Origin declared — mandatory for imported goods"}
    return {"field": "Country of Origin", "status": "INFO", "detail": "Not found — only mandatory for imported goods"}


# ---- Exemptions (Rule 3 & Rule 26) — cases where these mandatory
# declarations DON'T apply at all. Important to document as a known
# limitation: our OCR-based checker cannot reliably detect these exempt
# categories on its own (e.g. it can't weigh the product or confirm it's
# sold to an industrial buyer), so a flagged "violation" on an exempt
# product would be a FALSE POSITIVE. Worth mentioning explicitly in the
# demo/PPT rather than glossing over it.
#   - Packages sold by weight/measure of 10g/10ml or less (except tobacco)
#     are exempt from Unit Sale Price declaration (Rule 26)
#   - Fast food packed by a hotel/restaurant/similar body for direct sale
#   - Scheduled & non-scheduled drugs under the Drugs (Price Control)
#     Order, 1995
#   - Agricultural farm produce in packages above 50 kg
#   - Thread sold as coils to handloom weavers
#   - Packages above 25 kg/25 litre (50 kg/litre for cement & fertilizer)
#     — exempt from these specific retail declaration requirements
#   - Institutional/industrial packages, PROVIDED they are clearly and
#     prominently marked "Not for Retail Sale"
EXEMPTION_NOTES = {
    "under_10g_10ml": "Packages of 10g/10ml or less (except tobacco) are exempt from Unit Sale Price declaration.",
    "fast_food": "Fast food packed by a hotel/restaurant/similar body for direct sale is exempt.",
    "scheduled_drugs": "Scheduled and non-scheduled drugs under the Drugs (Price Control) Order, 1995 are exempt.",
    "agri_above_50kg": "Agricultural farm produce in packages above 50 kg is exempt.",
    "handloom_thread": "Thread sold in coil form to handloom weavers is exempt.",
    "bulk_above_25kg": "Packages above 25 kg/25 litre (50 kg/litre for cement & fertilizer) are exempt from these retail declaration requirements.",
    "not_for_retail_sale": "Institutional/industrial packages marked 'Not for Retail Sale' are exempt from these mandatory declarations.",
}


def check_not_for_retail_sale(full_text: str):
    """
    If a package is explicitly marked 'Not for Retail Sale', it is an
    institutional/industrial package exempt from ALL the mandatory
    declarations checked above — so we surface this as a special case
    rather than flagging missing fields as violations.
    """
    if re.search(r'not\s+for\s+retail\s+sale', full_text, re.IGNORECASE):
        return {"field": "Exemption Check", "status": "INFO", "detail": "Marked 'Not for Retail Sale' — exempt from mandatory declarations under Rule 3"}
    return None


def extract_net_quantity_value(full_text: str):
    """Pulls out just the number from something like '500g' -> 500.0"""
    match = re.search(r'(\d+(\.\d+)?)\s?(g|kg|ml|l|gm)\b', full_text, re.IGNORECASE)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(3).lower()
    # normalize kg/l to g/ml so it matches FONT_SIZE_RULES thresholds
    if unit in ("kg", "l"):
        value *= 1000
    return value


def run_all_checks(full_text: str, text_blocks: list = None, pixels_per_mm: float = None):
    """
    Runs every check and returns a list of results — this is what the API returns.
    text_blocks (optional): pass the raw OCR blocks (with bbox info) to also
    run the font-size check.
    pixels_per_mm (optional): from calculate_pixels_per_mm(), based on the
    user's card-edge taps for this specific photo.
    """
    # If the package is explicitly marked "Not for Retail Sale", it's an
    # institutional/industrial package — exempt from all mandatory
    # declarations, so we short-circuit and don't run the usual checks
    # (which would otherwise wrongly flag it as non-compliant).
    exemption = check_not_for_retail_sale(full_text)
    if exemption:
        return {
            "checks": [exemption],
            "compliance_score": None,
            "overall_status": "EXEMPT"
        }

    checks = [
        check_manufacturer_info(full_text),
        check_net_quantity(full_text),
        check_mrp(full_text),
        check_mfg_date(full_text),
        check_consumer_care(full_text),
        check_country_of_origin(full_text),
    ]

    if text_blocks is not None:
        qty_value = extract_net_quantity_value(full_text)
        checks.append(check_font_size(text_blocks, qty_value, pixels_per_mm))

    # Scoring: count PASS/WARN/FAIL toward the total (a WARN is a partial
    # compliance issue, not a free pass); INFO items (like "Country of
    # Origin not applicable") are excluded since they're not violations.
    # WARN counts as half-credit — it means something is present but
    # incomplete/incorrect, which is better than missing entirely (FAIL)
    # but still not fully compliant (PASS).
    #
    # Scoring criteria (shown to the user, not just computed silently):
    #   PASS = 1 point   | field fully meets the legal requirement
    #   WARN = 0.5 point | field present but incomplete/incorrect
    #   FAIL = 0 points  | field missing or clearly non-compliant
    #   INFO = excluded  | not applicable to this product, not scored
    scoring_relevant = [c for c in checks if c["status"] in ("PASS", "WARN", "FAIL")]
    total_checks = len(scoring_relevant)
    points_earned = sum(1 if c["status"] == "PASS" else 0.5 if c["status"] == "WARN" else 0 for c in scoring_relevant)
    max_points = total_checks  # each scored check is worth 1 point max
    score = round((points_earned / total_checks) * 100, 1) if total_checks else 0
    has_any_fail_or_warn = any(c["status"] in ("FAIL", "WARN") for c in checks)

    return {
        "checks": checks,
        "compliance_score": score,
        "points_earned": points_earned,
        "max_points": max_points,
        "total_checks_scored": total_checks,
        "scoring_criteria": {
            "PASS": "1 point — field fully meets the legal requirement",
            "WARN": "0.5 point — field present but incomplete or incorrect",
            "FAIL": "0 points — field missing or non-compliant",
            "INFO": "not scored — not applicable to this product",
        },
        "overall_status": "NON-COMPLIANT" if has_any_fail_or_warn else "COMPLIANT"
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

    # Fake OCR blocks to test the font-size check standalone
    fake_text_blocks = [
        {"text": "MRP Rs 120", "bbox": [[10, 100], [90, 100], [90, 130], [10, 130]], "confidence": 0.95},
        {"text": "Net Wt: 500g", "bbox": [[10, 140], [90, 140], [90, 152], [10, 152]], "confidence": 0.9},
    ]

    # Simulate user tapping the left/right edge of a ₹10 coin in the same photo
    # Say the coin appeared 162px wide in this photo (27mm diameter)
    fake_pixels_per_mm = calculate_pixels_per_mm(coin_left_x=50, coin_right_x=212, coin_type="₹10")
    print(f"Calculated pixels_per_mm from coin: {fake_pixels_per_mm}")

    result = run_all_checks(sample_text, text_blocks=fake_text_blocks, pixels_per_mm=fake_pixels_per_mm)
    import json
    print(json.dumps(result, indent=2))
