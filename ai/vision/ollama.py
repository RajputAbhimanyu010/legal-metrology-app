"""Optional local vision model adapter using Ollama; no Google Cloud required."""
import base64
import os
from typing import Optional
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")

PROMPT = """Read the visible declarations on this packaged product label.
Return plain text only. Preserve numbers, units, MRP, dates, manufacturer/packer/importer,
consumer-care phone/email, country of origin, net quantity and warnings.
Do not invent or infer text that is not visible. If something is unreadable, say [UNREADABLE]."""


def extract_with_ollama(image_path: str, timeout: int = 90) -> Optional[str]:
    if os.getenv("AI_OCR_ENABLED", "false").lower() != "true":
        return None
    try:
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        response = requests.post(
            f"{OLLAMA_URL.rstrip('/')}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": PROMPT, "images": [encoded], "stream": False,
                  "options": {"temperature": 0}},
            timeout=timeout,
        )
        response.raise_for_status()
        text = response.json().get("response", "").strip()
        return text or None
    except (OSError, requests.RequestException, ValueError, KeyError):
        return None
