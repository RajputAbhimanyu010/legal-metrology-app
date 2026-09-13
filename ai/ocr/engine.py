"""Adapter around the project's existing robust OCR implementation."""
from typing import Any, Dict, List


def extract(image_path: str) -> Dict[str, Any]:
    # Import lazily so the AI package can be imported even when OCR dependencies
    # are not installed yet.
    from ocr.extract_text import extract_text_from_image, get_full_text
    blocks: List[dict] = extract_text_from_image(image_path)
    return {"blocks": blocks, "text": get_full_text(blocks), "engine": "EasyOCR multi-pass"}
