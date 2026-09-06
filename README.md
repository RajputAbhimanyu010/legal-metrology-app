# Legal Metrology Compliance Checker

Automatically checks packaged commodity labels against the Legal
Metrology (Packaged Commodities) Rules, 2011 by scanning a photo.

## Requirement coverage (mapped to the problem statement)

| Requirement | Status | Where |
|---|---|---|
| Image upload and product scanning | Done | `frontend/app.py`, `backend/main.py` `/scan` |
| Extraction of declarations from labels | Done | `ocr/extract_text.py` (EasyOCR) |
| Detection of mandatory declarations | Done | `rules_engine/checker.py` |
| Font size and readability analysis | Done | `rules_engine/checker.py` `check_font_size()` (coin-based calibration) |
| Detection of missing/non-standard declarations | Done | `rules_engine/checker.py` |
| Compliance/non-compliance report generation | Done | `backend/report.py` (PDF) |
| Editable report format | Done | `backend/report.py` `generate_docx_report()` (Word) |
| Attachment of photographs/evidence | Done | `backend/main.py` `/image/{scan_id}`, shown in dashboard |
| Repository of scanned products + history | Done | SQLite `scans` table, `/history` |
| Role-based user access & secure authentication | Done | `backend/auth.py`, JWT + PBKDF2, officer/admin roles |
| Search and retrieval of past scans | Done | `/history?q=...&status=...`, dashboard search bar |
| Dashboard for enforcement officials | Done | `frontend/app.py` Dashboard tab |
| Technical documentation | Done | `ARCHITECTURE.md` |

## Team ownership

| Folder / Task | Owner(s) | What's in it |
|---|---|---|
| `ocr/` | Anurag | Reads text off a product label image (EasyOCR), resizes large images |
| `rules_engine/` | Abhimanyu (built on Anshi's legal research) | Checks extracted text against Legal Metrology Rules 2011; see `LEGAL_REFERENCE.md` |
| `backend/main.py`, `backend/auth.py` | Anurag + You | FastAPI server, JWT auth, role-based access, search/filter |
| `backend/report.py` | Abhimanyu | PDF + editable DOCX report generation |
| `frontend/` | Ashish + Shikhar | Login screen, upload/results tab, dashboard tab, admin user-management tab |
| `test_images/` | Suha | Real product photos (compliant + intentionally tampered) for testing/demo |
| `rules_engine/LEGAL_REFERENCE.md` | Anshi | Exact Rule 6/7 citations, font-size table, exemptions |
| `ARCHITECTURE.md` | Whole team (compile together) | System architecture + deployment framework writeup |

## Setup (run once)

```bash
pip install -r requirements.txt --break-system-packages
python3 backend/auth.py   # creates compliance.db + default admin account
```

Default login: `admin` / `admin123` (role: admin). Create officer
accounts from the app's "Admin: Manage Users" tab after logging in,
or call `create_user("name", "password", "officer")` from
`backend/auth.py` directly. **Change the default password before
any real deployment.**

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
[Product Photo + optional coin for calibration]
      |
  ocr/extract_text.py        -- reads all text off the label
      |
  rules_engine/checker.py    -- checks text against Rule 6/7
      |
  backend/main.py            -- saves to DB, enforces login/roles
      |
  backend/report.py          -- turns results into PDF or DOCX
      |
  frontend/app.py            -- login, upload, results, dashboard, admin
```

## About the coin-based font-size calibration

Government-set letter-height minimums are in millimeters, but a photo
only gives pixels. To convert one to the other, place any Indian coin
next to the label before taking the photo, then in the app: check
"I included a coin in this photo", pick which coin, and **click
directly on its left edge, then its right edge** in the displayed
image (via `streamlit-image-coordinates` — install it for this to
work as click-to-mark; without it, the app falls back to manually
typing pixel numbers, which is far less accurate). Since coins are
minted to a fixed government-standard diameter, this gives an accurate
pixels-per-mm ratio for that specific photo.

## Known limitations (state these honestly in the demo/PPT)

- OCR accuracy depends on photo quality — glare, blur, tiny warning
  text, and multi-language labels can all reduce accuracy
- Font-size accuracy depends on the user correctly marking the coin's
  edges
- Country-of-origin/exemption detection is keyword-based, not true
  image classification
- Legal values in `rules_engine/checker.py` were researched from Rule
  6/7 and official FAQs — re-verify against the current consolidated
  text on indiacode.nic.in before real-world use (see
  `rules_engine/LEGAL_REFERENCE.md` for the open items list)

## Quick tests without the full app

```bash
python3 rules_engine/checker.py                    # rules engine, standalone
python3 ocr/extract_text.py test_images/sample1.jpg # OCR, standalone
python3 backend/auth.py                             # creates DB + default admin
```
