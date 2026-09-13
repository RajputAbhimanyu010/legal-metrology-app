"""End-to-end AI-assisted extraction pipeline."""
from typing import Any, Dict
from ai.ocr.engine import extract as ocr_extract
from ai.vision.ollama import extract_with_ollama
from ai.nlp.fields import extract_fields


def analyze_image(image_path: str) -> Dict[str, Any]:
    ocr = ocr_extract(image_path)
    ai_text = extract_with_ollama(image_path)
    combined = "\n".join(x for x in [ocr["text"], ai_text] if x)
    return {
        "ocr": ocr,
        "ai_text": ai_text,
        "combined_text": combined,
        "fields": extract_fields(combined),
        "ai_enabled": ai_text is not None,
    }
