"""OCR + optional AI vision pipeline for packaged-product labels.

The deterministic OCR path uses EasyOCR with multiple preprocessing passes.
Optional local AI (Ollama) and optional Gemini REST support can independently
read/analyse the image. AI output is advisory and is never allowed to invent
legal rules; the rules engine remains the compliance authority.
"""
import base64
import json
import os
import re
from typing import Dict, List, Optional, Any

import cv2
import easyocr
import numpy as np
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

LANGUAGES = [x.strip() for x in os.getenv("OCR_LANGUAGES", "en").split(",") if x.strip()]
MAX_IMAGE_WIDTH = int(os.getenv("OCR_MAX_WIDTH", "2200"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
AI_OCR_ENABLED = os.getenv("AI_OCR_ENABLED", "false").lower() == "true"
GEMINI_ENABLED = os.getenv("GEMINI_ENABLED", "false").lower() == "true"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

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
        "quality": quality,
        "width": w,
        "height": h,
        "brightness": round(brightness, 1),
        "contrast": round(contrast, 1),
        "sharpness": round(sharpness, 1),
        "issues": issues,
    }


def _preprocess_variants(image: np.ndarray) -> List[np.ndarray]:
    """Create OCR-friendly variants without destroying the original."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    denoise = cv2.fastNlMeansDenoising(clahe, None, 7, 7, 21)
    adaptive = cv2.adaptiveThreshold(
        denoise, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11
    )
    up = cv2.resize(image, None, fx=1.35, fy=1.35, interpolation=cv2.INTER_CUBIC)
    up_gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)
    up_gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(up_gray)
    return [image, clahe, adaptive, up, up_gray]


def _normalize_text(text: str) -> str:
    text = text.replace("|", "I")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _iou(a, b) -> float:
    ax1, ay1 = min(p[0] for p in a), min(p[1] for p in a)
    ax2, ay2 = max(p[0] for p in a), max(p[1] for p in a)
    bx1, by1 = min(p[0] for p in b), min(p[1] for p in b)
    bx2, by2 = max(p[0] for p in b), max(p[1] for p in b)
    ix1, iy1, ix2, iy2 = max(ax1, bx1), max(ay1, by1), min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1, (bx2 - bx1) * (by2 - by1))
    return inter / (area_a + area_b - inter)


def _merge_blocks(all_blocks: List[dict]) -> List[dict]:
    kept = []
    for block in sorted(all_blocks, key=lambda x: x["confidence"], reverse=True):
        if not block["text"]:
            continue
        duplicate = False
        for old in kept:
            if _iou(block["bbox"], old["bbox"]) > 0.55 and block["text"].lower() == old["text"].lower():
                duplicate = True
                break
        if not duplicate:
            kept.append(block)
    kept.sort(key=lambda b: (min(p[1] for p in b["bbox"]), min(p[0] for p in b["bbox"])))
    return kept


def extract_text_from_image(image_path: str) -> List[dict]:
    image = _load_image(image_path)
    reader = _get_reader()
    collected = []
    for variant in _preprocess_variants(image):
        try:
            results = reader.readtext(
                variant, detail=1, paragraph=False,
                text_threshold=0.55, low_text=0.25, link_threshold=0.25
            )
        except Exception:
            continue
        for bbox, text, confidence in results:
            text = _normalize_text(text)
            if text:
                collected.append({"text": text, "bbox": bbox, "confidence": round(float(confidence), 4)})
    return _merge_blocks(collected)


def get_full_text(blocks: List[dict]) -> str:
    return "\n".join(b["text"] for b in blocks)


def _image_b64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def _vision_prompt(task: str) -> str:
    return (
        "You are an inspection assistant for packaged commodities in India. "
        "Inspect only what is visibly supported by the supplied product-label image. "
        "Do not invent text, measurements, legal clauses, or facts. "
        "The deterministic rules engine is the legal authority; your job is visual assistance.\n\n"
        + task
    )


def _ollama_generate(image_b64: str, prompt: str, timeout: int = 90) -> Optional[str]:
    try:
        r = requests.post(
            f"{OLLAMA_URL.rstrip('/')}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": _vision_prompt(prompt),
                "images": [image_b64],
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=timeout,
        )
        r.raise_for_status()
        return _normalize_text(r.json().get("response", "")) or None
    except Exception:
        return None


def _gemini_generate(image_b64: str, prompt: str, timeout: int = 90) -> Optional[str]:
    if not GEMINI_ENABLED or not GEMINI_API_KEY:
        return None
    try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        )
        payload = {
            "contents": [{"parts": [
                {"text": _vision_prompt(prompt)},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
            ]}],
            "generationConfig": {"temperature": 0},
        }
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        return _normalize_text(" ".join(p.get("text", "") for p in parts)) or None
    except Exception:
        return None


def ai_extract_text(image_path: str, timeout: int = 90) -> Optional[str]:
    """Run enabled vision readers and combine their independent text output."""
    if not (AI_OCR_ENABLED or GEMINI_ENABLED):
        return None
    image_b64 = _image_b64(image_path)
    prompt = (
        "Read every visible declaration on this packaged product label. Preserve numbers, units, "
        "MRP, dates, manufacturer/packer/importer, consumer-care phone/email, country of origin "
        "and warnings. Return plain text only."
    )
    outputs = []
    if AI_OCR_ENABLED:
        text = _ollama_generate(image_b64, prompt, timeout)
        if text:
            outputs.append(f"[Ollama {OLLAMA_MODEL}] {text}")
    if GEMINI_ENABLED:
        text = _gemini_generate(image_b64, prompt, timeout)
        if text:
            outputs.append(f"[Gemini {GEMINI_MODEL}] {text}")
    return "\n".join(outputs) or None


def ai_analyze_label(image_path: str, timeout: int = 90) -> Dict[str, Any]:
    """Optional multi-purpose vision analysis for quality, label structure and audit notes."""
    result: Dict[str, Any] = {
        "enabled": bool(AI_OCR_ENABLED or GEMINI_ENABLED),
        "providers": [],
        "analysis": None,
    }
    if AI_OCR_ENABLED:
        result["providers"].append(f"Ollama/{OLLAMA_MODEL}")
    if GEMINI_ENABLED:
        result["providers"].append(f"Gemini/{GEMINI_MODEL}")
    if not result["enabled"]:
        return result

    image_b64 = _image_b64(image_path)
    prompt = (
        "Return a concise JSON object with these keys: product_name, brand, visible_declarations, "
        "possible_issues, label_readability, tamper_or_editing_signals, recommendations. "
        "visible_declarations must be an array of short strings. possible_issues and recommendations "
        "must be arrays. label_readability must be GOOD, FAIR, or POOR. "
        "tamper_or_editing_signals must be an array. Do not claim fraud or tampering as fact; "
        "only report visible signals. Return JSON only."
    )
    raw = None
    provider = None
    if AI_OCR_ENABLED:
        raw = _ollama_generate(image_b64, prompt, timeout)
        provider = f"Ollama/{OLLAMA_MODEL}" if raw else None
    if not raw and GEMINI_ENABLED:
        raw = _gemini_generate(image_b64, prompt, timeout)
        provider = f"Gemini/{GEMINI_MODEL}" if raw else None

    if not raw:
        return result
    cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
    try:
        parsed = json.loads(cleaned)
    except Exception:
        parsed = {"raw": raw}
    result["analysis"] = parsed
    result["provider_used"] = provider
    return result


def build_combined_text(ocr_blocks: List[dict], ai_text: Optional[str]) -> str:
    ocr_text = get_full_text(ocr_blocks)
    if not ai_text:
        return ocr_text
    return f"{ocr_text}\n{ai_text}".strip()


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "test_images/compliant_label.png"
    blocks = extract_text_from_image(path)
    print("--- OCR ---")
    for b in blocks:
        print(f"[{b['confidence']:.2f}] {b['text']}")
    ai_text = ai_extract_text(path)
    if ai_text:
        print("\n--- AI VISION TEXT ---\n" + ai_text)
    print("\n--- IMAGE QUALITY ---")
    print(json.dumps(assess_image_quality(path), indent=2))
