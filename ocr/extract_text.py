"""Fast OCR and image-quality checks for packaged-product labels."""
import json
import os
import re
import time
from typing import Any, Dict, List

import cv2
import easyocr
import numpy as np

LANGUAGES = [x.strip() for x in os.getenv("OCR_LANGUAGES", "en").split(",") if x.strip()]
MAX_IMAGE_WIDTH = 1600
OCR_PASSES = 1
_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(LANGUAGES, gpu=False, verbose=False)
    return _reader


def _load_image(path: str) -> np.ndarray:
    data = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not decode image: {path}")
    h, w = image.shape[:2]
    if w > MAX_IMAGE_WIDTH:
        scale = MAX_IMAGE_WIDTH / w
        image = cv2.resize(image, (MAX_IMAGE_WIDTH, int(h * scale)), interpolation=cv2.INTER_AREA)
    return image


def assess_image_quality(image_path: str) -> Dict[str, Any]:
    """Fast objective pre-check for resolution, brightness, contrast and blur."""
    image = _load_image(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    issues = []
    if min(w, h) < 600:
        issues.append("Low image resolution")
    if brightness < 55:
        issues.append("Image is too dark")
    elif brightness > 225:
        issues.append("Image may be overexposed")
    if contrast < 25:
        issues.append("Low contrast")
    if sharpness < 60:
        issues.append("Image may be blurred")
    quality = "GOOD" if not issues else ("FAIR" if len(issues) <= 2 else "POOR")
    return {
        "quality": quality, "width": int(w), "height": int(h),
        "brightness": round(brightness, 1), "contrast": round(contrast, 1),
        "sharpness": round(sharpness, 1), "issues": issues,
    }


def _normalize_text(text: str) -> str:
    text = text.replace("|", "I")
    return re.sub(r"\s+", " ", text).strip()


def _merge_blocks(blocks: List[dict]) -> List[dict]:
    # One OCR pass means duplicate detection is only a lightweight safety net.
    kept = []
    seen = set()
    for block in blocks:
        key = block["text"].lower()
        if key and key not in seen:
            kept.append(block)
            seen.add(key)
    kept.sort(key=lambda b: (min(p[1] for p in b["bbox"]), min(p[0] for p in b["bbox"])))
    return kept


def extract_text_from_image(image_path: str) -> List[dict]:
    """Run one cached EasyOCR pass on the original image."""
    t0 = time.perf_counter()
    image = _load_image(image_path)
    reader = _get_reader()
    try:
        results = reader.readtext(
            image, detail=1, paragraph=False,
            text_threshold=0.55, low_text=0.25, link_threshold=0.25,
        )
    except Exception as exc:
        print(f"[OCR] failed: {exc}")
        raise

    blocks = []
    for bbox, text, confidence in results:
        text = _normalize_text(text)
        if not text:
            continue
        # Convert NumPy scalar/array values to plain Python types so FastAPI
        # can safely serialize the response.
        safe_bbox = [[int(round(float(p[0]))), int(round(float(p[1])))] for p in bbox]
        blocks.append({"text": text, "bbox": safe_bbox, "confidence": float(round(float(confidence), 4))})
    blocks = _merge_blocks(blocks)
    print(f"[OCR] 1 pass, {len(blocks)} text blocks, {time.perf_counter() - t0:.1f}s")
    return blocks


def get_full_text(blocks: List[dict]) -> str:
    return "\n".join(str(b["text"]) for b in blocks)


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "test_images/compliant_label.png"
    blocks = extract_text_from_image(path)
    print("--- OCR ---")
    for b in blocks:
        print(f"[{b['confidence']:.2f}] {b['text']}")
    print("\n--- IMAGE QUALITY ---")
    print(json.dumps(assess_image_quality(path), indent=2))
