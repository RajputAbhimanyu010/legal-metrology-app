"""
Report Generators — Owned by: Abhimanyu
Purpose: Turn one scan's results into downloadable compliance reports —
both a fixed PDF and an editable DOCX (per the problem statement's
"PDF and editable formats" requirement).
"""

import json
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from docx import Document
from docx.shared import Pt, RGBColor


def generate_pdf_report(scan_row: dict, output_dir: str) -> str:
    """
    scan_row: a dict with keys id, image_name, scan_time, compliance_score,
              overall_status, checks_json
    Returns the path to the generated PDF.
    """
    styles = getSampleStyleSheet()
    file_name = f"report_{scan_row['id']}.pdf"
    file_path = os.path.join(output_dir, file_name)

    doc = SimpleDocTemplate(file_path, pagesize=A4)
    elements = []

    elements.append(Paragraph("Legal Metrology Compliance Report", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Product Image: {scan_row['image_name']}", styles["Normal"]))
    elements.append(Paragraph(f"Scan Time: {scan_row['scan_time']}", styles["Normal"]))
    if scan_row.get("scanned_by"):
        elements.append(Paragraph(f"Scanned By: {scan_row['scanned_by']}", styles["Normal"]))
    elements.append(Paragraph(f"Overall Status: {scan_row['overall_status']}", styles["Normal"]))
    if scan_row.get("compliance_score") is not None:
        elements.append(Paragraph(f"Compliance Score: {scan_row['compliance_score']}%", styles["Normal"]))
    elements.append(Spacer(1, 20))

    checks = json.loads(scan_row["checks_json"])
    table_data = [["Field", "Status", "Detail"]]
    for c in checks:
        table_data.append([c["field"], c["status"], c["detail"]])

    table = Table(table_data, colWidths=[120, 70, 280])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(table)

    doc.build(elements)
    return file_path


def generate_docx_report(scan_row: dict, output_dir: str) -> str:
    """
    Editable Word (.docx) version of the same compliance report — lets an
    enforcement officer tweak wording/add notes before finalizing, unlike
    the fixed PDF. Satisfies the "editable formats" requirement.
    """
    file_name = f"report_{scan_row['id']}.docx"
    file_path = os.path.join(output_dir, file_name)

    doc = Document()

    title = doc.add_heading("Legal Metrology Compliance Report", level=1)

    doc.add_paragraph(f"Product Image: {scan_row['image_name']}")
    doc.add_paragraph(f"Scan Time: {scan_row['scan_time']}")
    if scan_row.get("scanned_by"):
        doc.add_paragraph(f"Scanned By: {scan_row['scanned_by']}")
    doc.add_paragraph(f"Overall Status: {scan_row['overall_status']}")
    if scan_row.get("compliance_score") is not None:
        doc.add_paragraph(f"Compliance Score: {scan_row['compliance_score']}%")

    doc.add_heading("Checklist", level=2)

    checks = json.loads(scan_row["checks_json"])
    table = doc.add_table(rows=1, cols=3)
    table.style = "Light Grid Accent 1"
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Field"
    hdr_cells[1].text = "Status"
    hdr_cells[2].text = "Detail"

    status_colors = {
        "PASS": RGBColor(0x1e, 0x7e, 0x34),
        "FAIL": RGBColor(0xc0, 0x39, 0x2b),
        "WARN": RGBColor(0xb9, 0x77, 0x0e),
        "INFO": RGBColor(0x5d, 0x6d, 0x7e),
    }

    for c in checks:
        row_cells = table.add_row().cells
        row_cells[0].text = c["field"]
        row_cells[1].text = c["status"]
        row_cells[2].text = c["detail"]
        # Color the status cell so it's easy to scan visually, same as
        # the PASS/FAIL/WARN icons in the app itself
        run = row_cells[1].paragraphs[0].runs[0] if row_cells[1].paragraphs[0].runs else row_cells[1].paragraphs[0].add_run(c["status"])
        color = status_colors.get(c["status"])
        if color:
            run.font.color.rgb = color
            run.font.bold = True

    doc.add_paragraph()
    doc.add_paragraph(
        "Officer notes (editable): _______________________________________________"
    )

    doc.save(file_path)
    return file_path
