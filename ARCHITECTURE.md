# Technical Documentation — Software Architecture & Deployment Framework

Legal Metrology Compliance Checker — SIH Problem Statement ID 26034

## 1. Overview

This system automatically checks whether a packaged commodity's label
complies with the Legal Metrology (Packaged Commodities) Rules, 2011,
by scanning a photo of the product label.

## 2. Architecture Diagram (text form)

```
┌─────────────────┐
│   Streamlit UI    │  <- login, upload, dashboard, admin panel
│  (frontend/app.py)│
└─────────┬─────────┘
          │ HTTPS/HTTP (JSON, multipart form-data)
          │ Authorization: Bearer <JWT>
          ▼
┌─────────────────────────────┐
│      FastAPI Backend          │
│      (backend/main.py)        │
│  ┌──────────┐  ┌───────────┐  │
│  │  /login   │  │  /scan     │  │
│  │  /register│  │  /history  │  │
│  │           │  │  /image/id │  │
│  │           │  │  /report/id│  │
│  └──────────┘  └───────────┘  │
└──────┬────────────┬───────────┘
       │             │
       ▼             ▼
┌─────────────┐  ┌─────────────────────┐
│ auth.py      │  │ ocr/extract_text.py │
│ (JWT + PBKDF2)│  │ (EasyOCR)            │
└──────┬───────┘  └──────────┬──────────┘
       │                     ▼
       │          ┌─────────────────────┐
       │          │ rules_engine/checker │
       │          │ .py (Rule 6/7 logic) │
       │          └──────────┬──────────┘
       │                     ▼
       │          ┌─────────────────────┐
       │          │ backend/report.py    │
       │          │ (PDF + DOCX export)  │
       │          └──────────┬──────────┘
       ▼                     ▼
┌───────────────────────────────────┐
│         SQLite (compliance.db)      │
│  tables: users, scans                │
└───────────────────────────────────┘
       │
       ▼
┌───────────────────────────────────┐
│  Filesystem: uploaded_images/,      │
│  reports/ (evidence photos, PDFs,    │
│  DOCX files)                          │
└───────────────────────────────────┘
```

## 3. Component Breakdown

| Component | File(s) | Responsibility |
|---|---|---|
| Frontend | `frontend/app.py` | Login screen, image upload, coin-based calibration UI, results display, dashboard with search/filter, admin user management |
| Authentication | `backend/auth.py` | Password hashing (PBKDF2-SHA256), JWT issuance/validation, role storage (officer/admin) |
| API layer | `backend/main.py` | REST endpoints, request validation, orchestrates OCR → rules engine → DB → report generation, enforces role-based access |
| OCR | `ocr/extract_text.py` | Extracts text + bounding boxes from label images using EasyOCR; resizes large images for speed |
| Rules Engine | `rules_engine/checker.py` | Encodes Legal Metrology Rule 6/7 requirements as executable checks; computes compliance score |
| Report Generation | `backend/report.py` | Produces fixed PDF (ReportLab) and editable DOCX (python-docx) compliance reports |
| Data storage | SQLite (`compliance.db`) | `users` table (accounts/roles), `scans` table (results, evidence photo path, who scanned it, timestamp) |
| File storage | `uploaded_images/`, `reports/` | Evidence photos and generated reports on local disk |

## 4. Data Flow (one scan, end to end)

1. Officer logs in → receives a JWT access token (valid 12 hours)
2. Officer uploads a label photo, optionally marks a reference coin's edges for font-size calibration
3. Frontend sends the image (+ coin data) to `POST /scan` with the JWT in the Authorization header
4. Backend saves the image to `uploaded_images/`, runs OCR to extract text + bounding boxes
5. Extracted text is passed to the rules engine, which checks it against Rule 6/7 requirements and returns a checklist + compliance score
6. Result is saved to the `scans` table (including who scanned it and the evidence photo path)
7. Frontend displays the checklist; officer can request a PDF or editable DOCX report on demand
8. Dashboard tab lets officers search their own scan history (admins see all), filter by status, and view the original evidence photo per scan

## 5. Role-Based Access Control

| Role | Can do |
|---|---|
| Officer | Scan products, view/search their own scan history, download their own reports |
| Admin | Everything an officer can, PLUS view all officers' scan history, create new user accounts |

Enforced server-side in `backend/main.py` (not just hidden in the UI) — every protected endpoint validates the JWT and checks `role`/`scanned_by` before returning data.

## 6. Deployment Framework (current: local/demo)

- **Backend**: run via `uvicorn backend.main:app --reload` — a single-process ASGI server suitable for a demo/pilot
- **Frontend**: run via `streamlit run frontend/app.py` — connects to the backend over HTTP on localhost
- **Database**: SQLite file (`compliance.db`) — zero setup, fine for a pilot; would move to PostgreSQL for multi-officer concurrent production use
- **File storage**: local filesystem (`uploaded_images/`, `reports/`) — would move to cloud object storage (S3/GCS) for a real multi-server deployment

### Path to production deployment (documented, not yet implemented)

- Containerize backend + frontend with Docker; deploy behind a reverse proxy (Nginx) with HTTPS
- Move SQLite → PostgreSQL for concurrent multi-user write safety
- Move local file storage → cloud object storage (S3-compatible) for evidence photos and reports
- Move JWT secret key out of source code into an environment variable / secrets manager
- Add rate limiting and request logging for an enforcement/audit trail
- Consider GPU-backed OCR (EasyOCR with `gpu=True`) for faster processing at scale

## 7. Known Limitations (honest, not hidden)

- OCR accuracy depends on photo quality (lighting, glare, angle, wrinkled packaging) — not 100% reliable on every real-world photo
- Font-size calibration relies on the user correctly marking a coin's edges in the photo; accuracy is only as good as that manual step
- Country-of-origin and exemption detection rely on keyword matching in OCR text, not true image/product classification
- Rules engine values were researched from Rule 6/7 and official FAQs at a point in time — should be re-verified against the current consolidated Rules text before any real deployment (see `rules_engine/LEGAL_REFERENCE.md`)
- Single-server, single-database local setup — not yet built for high-concurrency production load
