"""
Backend API — Owned by: Anurag (integration) + Abhimanyu (report/testing)
Purpose: Connects OCR -> Rules Engine -> Database -> Frontend.

Run with:
    pip install -r requirements.txt --break-system-packages
    uvicorn backend.main:app --reload

Then open http://127.0.0.1:8000/docs to test the API directly.

First-time setup: run `python3 backend/auth.py` once to create the
default admin account (admin / admin123) before logging in.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# allow importing sibling folders (ocr/, rules_engine/)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ocr.extract_text import extract_text_from_image, get_full_text
from rules_engine.checker import run_all_checks, calculate_pixels_per_mm
from backend.report import generate_pdf_report, generate_docx_report
from backend.auth import (
    init_users_table, create_user, verify_user,
    create_access_token, decode_access_token,
)

app = FastAPI(title="Legal Metrology Compliance Checker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploaded_images"
REPORT_DIR = "reports"
TEST_IMAGES_DIR = "test_images"
DB_PATH = "compliance.db"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(TEST_IMAGES_DIR, exist_ok=True)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_name TEXT,
            image_path TEXT,
            scanned_by TEXT,
            scan_time TEXT,
            compliance_score REAL,
            overall_status TEXT,
            checks_json TEXT
        )
    """)
    conn.commit()

    # Migration safety net: if this is an EXISTING compliance.db created
    # before image_path/scanned_by existed (e.g. from testing earlier
    # versions of this app), CREATE TABLE IF NOT EXISTS above does nothing
    # for a table that already exists — so add the missing columns here
    # instead of letting every /scan request fail with "no such column".
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(scans)").fetchall()}
    if "image_path" not in existing_columns:
        conn.execute("ALTER TABLE scans ADD COLUMN image_path TEXT")
    if "scanned_by" not in existing_columns:
        conn.execute("ALTER TABLE scans ADD COLUMN scanned_by TEXT")
    conn.commit()
    conn.close()


init_db()
init_users_table()


# ---------------- Auth helpers ----------------

def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Reads the 'Authorization: Bearer <token>' header, validates the JWT,
    and returns {"username": ..., "role": ...}. Raises 401 if missing/invalid.
    Every protected endpoint below takes this as a dependency.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"username": payload["sub"], "role": payload["role"]}


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    """Returns a JWT access token on valid username/password."""
    role = verify_user(username, password)
    if not role:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token(username, role)
    return {"access_token": token, "role": role, "username": username}


@app.post("/register")
def register(
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("officer"),
    authorization: Optional[str] = Header(None),
):
    """Admin-only: create a new officer/admin account."""
    requester = get_current_user(authorization)
    if requester["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create new users")
    created = create_user(username, password, role)
    if not created:
        raise HTTPException(status_code=400, detail="Username already exists")
    return {"status": "created", "username": username, "role": role}


# ---------------- Core scanning ----------------

@app.post("/scan")
async def scan_product(
    file: UploadFile = File(...),
    coin_left_x: Optional[float] = Form(None),
    coin_right_x: Optional[float] = Form(None),
    coin_type: Optional[str] = Form("₹5"),
    authorization: Optional[str] = Header(None),
):
    """
    Upload a product image -> runs OCR -> runs rules engine ->
    saves to DB -> returns the compliance checklist.
    Requires a valid login token; the scan is tagged with who performed it.
    """
    user = get_current_user(authorization)

    # Save uploaded image with a unique name so two officers scanning a
    # "chips.jpg" on the same day don't overwrite each other's evidence photo
    safe_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Also copy every uploaded photo into test_images/ so the dataset of
    # real product photos grows over time as officers use the app.
    # IMPORTANT — honest note: this does NOT retrain or fine-tune the OCR
    # model automatically. EasyOCR is a pretrained model that doesn't
    # learn from new images at runtime. This just builds up a labeled
    # collection of real photos (named by their compliance result) that
    # the team could later use to manually evaluate accuracy or, as a
    # separate future project, fine-tune a custom OCR/detection model.
    # Saying that plainly in your demo is better than implying live
    # learning that isn't actually happening.
    import shutil
    test_image_name = f"{safe_name}"  # renamed with FAIL/PASS prefix after scan, see below
    test_image_path = os.path.join(TEST_IMAGES_DIR, test_image_name)
    shutil.copy(file_path, test_image_path)

    # OCR
    blocks = extract_text_from_image(file_path)
    full_text = get_full_text(blocks)

    # Calibration from coin taps, if provided
    pixels_per_mm = None
    if coin_left_x is not None and coin_right_x is not None:
        pixels_per_mm = calculate_pixels_per_mm(coin_left_x, coin_right_x, coin_type)

    # Rules check (pass text_blocks + calibration so font-size check can run)
    result = run_all_checks(full_text, text_blocks=blocks, pixels_per_mm=pixels_per_mm)

    # Rename the test_images copy to include the result in its filename —
    # e.g. "NONCOMPLIANT_20260906_chips.jpg" — so the growing dataset is
    # self-documenting (matches the naming convention Suha was asked to
    # use for manually-collected test photos, e.g. missing_mrp_snack_1.jpg)
    status_prefix = result["overall_status"].replace("-", "")
    labeled_name = f"{status_prefix}_{test_image_name}"
    os.rename(test_image_path, os.path.join(TEST_IMAGES_DIR, labeled_name))

    # Save to DB — including WHO scanned it and WHERE the evidence photo lives
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO scans
           (image_name, image_path, scanned_by, scan_time, compliance_score, overall_status, checks_json)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (file.filename, file_path, user["username"], datetime.now().isoformat(),
         result["compliance_score"], result["overall_status"], json.dumps(result["checks"]))
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
def get_history(
    q: Optional[str] = None,
    status: Optional[str] = None,
    authorization: Optional[str] = Header(None),
):
    """
    Returns past scans for the dashboard — with search/filter support.
    - q: substring match on product/image name (search by product name)
    - status: exact match on overall_status (COMPLIANT / NON-COMPLIANT / EXEMPT)
    Officers see only their own scans; admins see everyone's — this is
    the role-based access control in action, not just a login screen.
    """
    user = get_current_user(authorization)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM scans WHERE 1=1"
    params = []

    if user["role"] != "admin":
        query += " AND scanned_by = ?"
        params.append(user["username"])

    if q:
        query += " AND image_name LIKE ?"
        params.append(f"%{q}%")

    if status:
        query += " AND overall_status = ?"
        params.append(status)

    query += " ORDER BY scan_time DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/image/{scan_id}")
def get_scan_image(scan_id: int, authorization: Optional[str] = Header(None)):
    """
    Serves the original evidence photo for a scan — this is the
    'attachment of photographs and supporting evidence' requirement.
    """
    user = get_current_user(authorization)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Scan not found")
    if user["role"] != "admin" and row["scanned_by"] != user["username"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this scan's evidence")
    if not row["image_path"] or not os.path.exists(row["image_path"]):
        raise HTTPException(status_code=404, detail="Evidence image not found on disk")

    return FileResponse(row["image_path"])


@app.get("/report/{scan_id}")
def get_report(scan_id: int, format: str = "pdf", authorization: Optional[str] = Header(None)):
    """
    Generates AND DIRECTLY RETURNS a compliance report file for one scan.
    format: "pdf" (fixed layout) or "docx" (editable — per the
    'editable formats' requirement in the problem statement).

    IMPORTANT: this returns the actual file bytes (not a server-side path)
    so it works correctly regardless of which machine/folder the frontend
    happens to be running from.
    """
    user = get_current_user(authorization)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Scan not found")
    if user["role"] != "admin" and row["scanned_by"] != user["username"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this scan's report")

    if format == "docx":
        path = generate_docx_report(dict(row), REPORT_DIR)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        download_name = f"compliance_report_{scan_id}.docx"
    else:
        path = generate_pdf_report(dict(row), REPORT_DIR)
        media_type = "application/pdf"
        download_name = f"compliance_report_{scan_id}.pdf"

    return FileResponse(path, media_type=media_type, filename=download_name)


@app.get("/history/product/{product_name}")
def get_product_history(product_name: str, authorization: Optional[str] = Header(None)):
    """
    Returns EVERY past scan of one specific product (matched by name),
    ordered oldest-to-newest — so an officer can see a product's full
    compliance history/trend over time, not just its latest scan.
    """
    user = get_current_user(authorization)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM scans WHERE image_name = ?"
    params = [product_name]
    if user["role"] != "admin":
        query += " AND scanned_by = ?"
        params.append(user["username"])
    query += " ORDER BY scan_time ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/")
def root():
    return {"status": "Legal Metrology Compliance Checker API is running"}
