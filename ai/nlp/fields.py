"""Conservative, explainable field extraction from OCR/vision text."""
import re
from typing import Dict


def _first(pattern: str, text: str):
    m = re.search(pattern, text, re.I | re.M)
    return m.group(1).strip() if m else None


def extract_fields(text: str) -> Dict[str, str]:
    fields = {}
    patterns = {
        "mrp": r"(?:MRP|M\.R\.P\.?)\s*[:\-]?\s*(₹?\s*[\d,.]+(?:\s*\([^\n)]*\))?)",
        "net_quantity": r"(?:Net\s*(?:Quantity|Qty)|Net)\s*[:\-]?\s*([^\n]+)",
        "manufacture_date": r"(?:Mfd\.?|Manufactured|Date\s*of\s*Manufacture)\s*[:\-]?\s*([^\n]+)",
        "best_before": r"(?:Best\s*Before|Use\s*By|Expiry)\s*[:\-]?\s*([^\n]+)",
        "consumer_care": r"(?:Consumer\s*Care|Customer\s*Care|Customer\s*Service)\s*[:\-]?\s*([^\n]+)",
    }
    for key, pattern in patterns.items():
        value = _first(pattern, text)
        if value:
            fields[key] = value
    return fields
