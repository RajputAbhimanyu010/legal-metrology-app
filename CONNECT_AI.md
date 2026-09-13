The layer is intentionally modular:
- preprocessing: image enhancement variants for OCR
- ocr: adapter to the project's existing OCR engine
- vision: optional local Ollama + Gemma 3 vision extraction (no Google Cloud)
- nlp: conservative field extraction from OCR/AI text
- inference: one pipeline entry point

The deterministic rules engine should remain responsible for compliance scoring; AI only assists extraction/normalization.