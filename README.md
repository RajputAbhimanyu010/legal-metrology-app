# legal-metrology-app
SIH project - Legal Metrology Compliance Checker
# Legal Metrology Compliance Checker — Starter Project

## Team ownership

| Folder | Owner(s) | What's in it |
|---|---|---|
| `ocr/` | Anurag | Reads text off a product label image (EasyOCR) |
| `rules_engine/` | Abhimanyu | Checks extracted text against Legal Metrology Rules 2011 |
| `backend/` | Anurag + Abhimanyu | FastAPI server: connects OCR → rules → database, PDF reports |
| `frontend/` | Ashish + Shikhar | Streamlit UI: upload screen + dashboard (replace/extend freely) |
| `test_images/` | Suha | Real product photos (compliant + tampered) for testing/demo |

## Setup (run once)

```bash
pip install -r requirements.txt --break-system-packages
```

## Running the app (two terminals)

**Terminal 1 — Backend:**
```bash
uvicorn backend.main:app --reload
```
Visit http://127.0.0.1:8000/docs to test the API directly.

**Terminal 2 — Frontend:**
```bash
streamlit run frontend/app.py
```

## How it fits together

```
[Product Photo]
      ↓
  ocr/extract_text.py   (Anurag)  — reads all text off the label
      ↓
  rules_engine/checker.py (Abhimanyu) — checks text against the law
      ↓
  backend/main.py  — saves to database, returns results as JSON
      ↓
  backend/report.py (Abhimanyu) — turns results into a PDF report
      ↓
  frontend/app.py (Ashish/Shikhar) — shows results + dashboard to the user
```

## Still TODO (assign as needed)

- [ ] **Anshi**: Fill in exact font-size thresholds (mm) in `rules_engine/checker.py` → `FONT_SIZE_RULES`, and confirm all regex patterns match the real Rules wording
- [ ] **Suha**: Add 15-20 real product photos to `test_images/` (mix of compliant + intentionally tampered)
- [ ] Font-size/readability check is a placeholder — needs pixel-to-mm calibration logic (use a reference object in the photo, or ask user to input pack dimensions)
- [ ] Add login/role-based access (Officer vs Admin) before final submission if time allows
- [ ] Replace Streamlit frontend with React version if time allows (optional — Streamlit is fine for MVP demo)

## Quick test without the full app

Test the rules engine alone:
```bash
python3 rules_engine/checker.py
```

Test OCR alone (after installing easyocr):
```bash
python3 ocr/extract_text.py test_images/sample1.jpg
```

