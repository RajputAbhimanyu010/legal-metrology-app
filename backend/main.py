"""
Backend API — Owned by: Anurag (integration) + Abhimanyu (report/testing)
Purpose: Connects OCR -> Rules Engine -> Database -> Frontend.

Run with:
    pip install fastapi uvicorn python-multipart reportlab --break-system-packages
    uvicorn backend.main:app --reload

Then open http://127.0.0.1:8000/docs to test the API directly.
"""

import os
import sqlite3
import sys
from datetime import datetime

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

# allow importing sibling folders (ocr/, rules_engine/)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ocr.extract_text import extract_text_from_image, get_full_text
from rules_engine.checker import run_all_checks
from backend.report import generate_pdf_report

app = FastAPI(title="Legal Metrology Compliance Checker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploaded_images"
REPORT_DIR = "reports"
DB_PATH = "compliance.db"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_name TEXT,
            scan_time TEXT,
            compliance_score REAL,
            overall_status TEXT,
            checks_json TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


@app.post("/scan")
async def scan_product(file: UploadFile = File(...)):
    """
    Upload a product image -> runs OCR -> runs rules engine ->
    saves to DB -> returns the compliance checklist.
    """
    # Save uploaded image
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # OCR
    blocks = extract_text_from_image(file_path)
    full_text = get_full_text(blocks)

    # Rules check
    result = run_all_checks(full_text)

    # Save to DB
    import json
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO scans (image_name, scan_time, compliance_score, overall_status, checks_json) VALUES (?, ?, ?, ?, ?)",
        (file.filename, datetime.now().isoformat(), result["compliance_score"], result["overall_status"], json.dumps(result["checks"]))
    )
    conn.commit()
    scan_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    return {
        "scan_id": scan_id,
        "image_name": file.filename,
        "extracted_text": full_text,
        **result
    }


@app.get("/history")
def get_history():
    """Returns all past scans for the dashboard."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM scans ORDER BY scan_time DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/report/{scan_id}")
def get_report(scan_id: int):
    """Generates and returns a PDF compliance report for one scan."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    conn.close()

    if not row:
        return {"error": "Scan not found"}

    pdf_path = generate_pdf_report(dict(row), REPORT_DIR)
    return {"pdf_path": pdf_path}


@app.get("/")
def root():
    return {"status": "Legal Metrology Compliance Checker API is running"}
