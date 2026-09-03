"""
PDF Report Generator — Owned by: Abhimanyu
Purpose: Turn one scan's results into a downloadable PDF compliance report.
"""

import json
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


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
    elements.append(Paragraph(f"Overall Status: {scan_row['overall_status']}", styles["Normal"]))
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
