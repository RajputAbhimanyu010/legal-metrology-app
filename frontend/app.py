"""Streamlit UI styled after the supplied Legal Metrology reference mockup."""
import io
import json
import os
from pathlib import Path

import requests
import streamlit as st
from PIL import Image

try:
    from streamlit_image_coordinates import streamlit_image_coordinates
    HAS_CLICK_SUPPORT = True
except ImportError:
    HAS_CLICK_SUPPORT = False

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
ROOT_DIR = Path(__file__).resolve().parents[1]
TEST_IMAGES_DIR = ROOT_DIR / "test_images"

st.set_page_config(page_title="Legal Metrology Compliance Checker", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
:root { --navy:#123b68; --navy2:#0b2949; --blue:#1d6fa5; --cyan:#2f8fb8; --green:#168a5a; --red:#c93c45; --amber:#b77b12; --ink:#17324d; --muted:#607286; --line:#c9d9e8; --soft:#eef5fb; --panel:#f8fbfe; }
.stApp { background:linear-gradient(135deg,#eaf3fb 0%,#f6f9fc 48%,#edf4f8 100%); color:var(--ink); }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#082746 0%,#0e3c63 55%,#123f67 100%); }
[data-testid="stSidebar"] * { color:#fff !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { background:rgba(255,255,255,.07); border-radius:8px; padding:7px 10px; margin:3px 0; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background:rgba(255,255,255,.14); }
.block-container { padding-top:1rem; max-width:1400px; }
.hero { background:linear-gradient(105deg,#0b3155,#176b98); color:white; padding:24px 28px; border-radius:14px; box-shadow:0 8px 24px rgba(10,45,75,.18); margin-bottom:18px; border:1px solid rgba(255,255,255,.15); }
.hero h1 { font-size:30px; margin:0; color:white; }
.hero p { margin:6px 0 0; color:#e5f4ff; opacity:.95; }
.card { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:18px; box-shadow:0 4px 14px rgba(22,58,91,.08); height:100%; }
.card:hover { border-color:#91b9d4; box-shadow:0 7px 18px rgba(22,58,91,.12); }
.card h3 { color:var(--navy); font-size:17px; margin:0 0 8px; }
.card p,.card li { color:#425a70; font-size:14px; line-height:1.55; }
.section-title { color:#0d3b66; font-weight:800; font-size:22px; margin:14px 0 10px; }
.subtle { background:#e4f0f8; border-left:5px solid #2f8fb8; padding:13px 16px; border-radius:8px; color:#294b66; margin:10px 0 18px; }
.quick { background:linear-gradient(135deg,#ffffff,#e8f3fa); border:1px solid #bfd4e5; border-radius:12px; padding:18px; }
.badge { display:inline-block; padding:5px 10px; border-radius:20px; font-weight:700; font-size:12px; }
.badge-green { background:#dff5e9; color:#147447; } .badge-red { background:#ffe5e7; color:#ae2834; } .badge-amber { background:#fff0ce; color:#8f6200; }
.score-box { background:#e8f4fb; border:1px solid #b9d3e5; border-radius:12px; padding:18px; text-align:center; }
.score-box b { font-size:32px; color:#0c5b85; }
.small-muted { color:#607286; font-size:12px; }
.check-row { border:1px solid #c8d8e6; border-radius:9px; padding:11px 13px; margin:7px 0; background:#f7fbfe; }
.image-frame { border:1px solid #b9cfdf; border-radius:10px; padding:7px; background:#f7fbfe; }
[data-testid="stMetric"] { background:#e8f2f8; border:1px solid #bfd4e4; padding:11px 13px; border-radius:10px; }
[data-testid="stMetricLabel"] { color:#36556f !important; }
[data-testid="stMetricValue"] { color:#0d456b !important; }
button[kind="primary"] { background:#12679b !important; border-color:#12679b !important; color:#ffffff !important; }
button[kind="primary"]:hover { background:#0d527e !important; border-color:#0d527e !important; color:#ffffff !important; }

/* Clear, visible secondary controls */
button[kind="secondary"],
div.stButton > button:not([kind="primary"]),
div.stFormSubmitButton > button:not([kind="primary"]) {
    background:#e8f2fb !important;
    color:#123f7a !important;
    border:1px solid #9fc2e3 !important;
    border-radius:7px !important;
    font-weight:650 !important;
}
button[kind="secondary"]:hover,
div.stButton > button:not([kind="primary"]):hover,
div.stFormSubmitButton > button:not([kind="primary"]):hover {
    background:#d3e7f8 !important;
    color:#0d315e !important;
    border-color:#6ea4d1 !important;
}

/* Report download buttons */
[data-testid="stDownloadButton"] button {
    background:#1769aa !important;
    color:#ffffff !important;
    border:1px solid #1769aa !important;
    border-radius:7px !important;
    font-weight:700 !important;
}
[data-testid="stDownloadButton"] button:hover {
    background:#0d527e !important;
    color:#ffffff !important;
    border-color:#0d527e !important;
}

/* Keep extracted OCR text easy to read */
.stTextArea textarea {
    background:#f8fbff !important;
    color:#17365d !important;
    border:1px solid #b8cde2 !important;
}
</style>
""", unsafe_allow_html=True)


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def api_get(path, **kwargs):
    return requests.get(f"{API_URL}{path}", headers=auth_headers(), timeout=kwargs.pop("timeout", 30), **kwargs)


def api_post(path, **kwargs):
    return requests.post(f"{API_URL}{path}", headers=auth_headers(), timeout=kwargs.pop("timeout", 30), **kwargs)


def status_badge(status):
    if status == "COMPLIANT":
        return '<span class="badge badge-green">✓ COMPLIANT</span>'
    if status == "NON-COMPLIANT":
        return '<span class="badge badge-red">✕ NON-COMPLIANT</span>'
    return '<span class="badge badge-amber">ℹ EXEMPT</span>'


def show_result(result, key_prefix="result"):
    status = result.get("overall_status", "N/A")
    st.markdown(status_badge(status), unsafe_allow_html=True)
    cols = st.columns([1.25, 1, 1, 1.25])
    score = result.get("compliance_score")
    with cols[0]:
        if score is not None:
            st.markdown(f'<div class="score-box"><div class="small-muted">Compliance Score</div><b>{score}%</b><div class="small-muted">out of 100</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="score-box"><div class="small-muted">Compliance Score</div><b>N/A</b></div>', unsafe_allow_html=True)
    cols[1].metric("Points Scored", f"{result.get('points_earned','N/A')} / {result.get('max_points','N/A')}")
    cols[2].metric("Fields Scored", result.get("total_checks_scored", "N/A"))
    quality = result.get("image_quality", {})
    cols[3].metric("Image Quality", quality.get("quality", "N/A"))

    st.markdown('<div class="section-title">Compliance Analysis</div>', unsafe_allow_html=True)
    for check in result.get("checks", []):
        status_icon = {"PASS":"✅", "WARN":"⚠️", "FAIL":"❌", "INFO":"ℹ️"}.get(check.get("status"), "•")
        st.markdown(f'<div class="check-row"><b>{status_icon} {check.get("field")}</b> &nbsp; <span class="small-muted">{check.get("status")}</span><br>{check.get("detail")}</div>', unsafe_allow_html=True)

    quality = result.get("image_quality") or {}
    if quality:
        with st.expander("Image quality pre-check"):
            st.write({k:v for k,v in quality.items() if k != "issues"})
            if quality.get("issues"):
                st.warning("; ".join(quality["issues"]))
            else:
                st.success("Image passed the basic resolution, lighting, contrast and sharpness checks.")

    st.markdown('<div class="section-title">OCR Extracted Information</div>', unsafe_allow_html=True)
    st.text_area("Text extracted from the product label", result.get("extracted_text", ""), height=150, key=f"ocr_{key_prefix}")


def download_reports(scan_id, key_prefix):
    st.markdown('<div class="section-title">Report Export</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    for col, fmt, label, mime in [
        (c1, "pdf", "📄 Download PDF Report", "application/pdf"),
        (c2, "docx", "📝 Download Editable Word Report", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ]:
        with col:
            try:
                r = api_get(f"/report/{scan_id}", params={"format":fmt}, timeout=60)
                if r.status_code == 200:
                    ext = "pdf" if fmt == "pdf" else "docx"
                    st.download_button(label, r.content, file_name=f"compliance_report_{scan_id}.{ext}", mime=mime, key=f"{key_prefix}_{fmt}", use_container_width=True)
                else:
                    st.error("Could not generate this report.")
            except requests.RequestException as e:
                st.error(f"Backend not reachable: {e}")


# ---------------- LOGIN ----------------
if "token" not in st.session_state:
    st.markdown('<div class="hero"><h1>Legal Metrology Compliance Checker</h1><p>Packaged commodity compliance inspection</p></div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.markdown('<div class="card"><h3>🔐 Secure Officer Login</h3><p>Sign in to scan labels, review evidence and export audit-ready reports.</p></div>', unsafe_allow_html=True)
    with c2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)
        if submitted:
            try:
                resp = requests.post(f"{API_URL}/login", data={"username":username,"password":password}, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state.update(token=data["access_token"], username=data["username"], role=data["role"])
                    st.rerun()
                else:
                    st.error("Incorrect username or password.")
            except requests.RequestException:
                st.error("Cannot reach the backend. Start FastAPI first.")
    st.caption("First run: `python backend/auth.py` creates the default admin account (admin / admin123). Change it before real deployment.")
    st.stop()

# ---------------- SHELL ----------------
with st.sidebar:
    st.markdown("## 🛡️ Legal Metrology")
    st.markdown(f"**{st.session_state['username']}** · {st.session_state['role'].title()}")
    nav = ["Home", "Upload Image", "Test Images", "Reports", "History", "Settings"]
    if st.session_state["role"] == "admin":
        nav.append("Admin Users")
    page = st.radio("Navigation", nav, label_visibility="collapsed")
    st.divider()
    if st.button("Log out", use_container_width=True):
        st.session_state.clear(); st.rerun()

st.markdown('<div class="hero"><h1>Legal Metrology Compliance Checker</h1><p>Packaged Commodities Compliance Report & Inspection Dashboard</p></div>', unsafe_allow_html=True)

# ---------------- HOME ----------------
if page == "Home":
    st.markdown('<div class="section-title">Inspection Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtle"><b>Legal Metrology packaged-commodity checker</b><br>Upload a product-label image to run image-quality checks, OCR extraction, deterministic compliance checks and evidence-ready reporting.</div>', unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    for col, icon, title, text in [
        (c1,"📷","Inspect a label","Upload a clear product-label image and verify the declarations visible on the package."),
        (c2,"✓","Check compliance","OCR reads the label and the rules engine evaluates the configured Legal Metrology requirements."),
        (c3,"📄","Create evidence report","Review the score, findings and original test image, then export PDF or editable Word."),
    ]:
        with col:
            st.markdown(f'<div class="card"><h3>{icon} {title}</h3><p>{text}</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Quick start</div>', unsafe_allow_html=True)
    q1,q2 = st.columns(2)
    with q1:
        st.markdown('<div class="quick"><h3>Start a new inspection</h3><p>Go to <b>Upload Image</b> and select the product-label photo you want to check.</p></div>', unsafe_allow_html=True)
    with q2:
        st.markdown('<div class="quick"><h3>Review previous inspections</h3><p>Use <b>History</b> to view earlier scans, findings, scores and evidence images.</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Included sample tests</div>', unsafe_allow_html=True)
    a,b,c,d = st.columns(4)
    for col, title, detail in [
        (a,"Compliant label","Expected declarations present"),
        (b,"Missing MRP","Tests missing-price detection"),
        (c,"Missing consumer care","Tests contact-detail detection"),
        (d,"Blurred label","Tests image-quality warning"),
    ]:
        col.markdown(f'<div class="card"><h3>{title}</h3><p>{detail}</p></div>', unsafe_allow_html=True)

# ---------------- UPLOAD ----------------
elif page == "Upload Image":
    st.markdown('<div class="section-title">1. Upload & Check Product Image</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Choose product label image", type=["jpg","jpeg","png"], help="Use a clear, well-lit image with the full label visible.")
    if uploaded_file:
        left,right = st.columns([1.1,1])
        with left:
            st.markdown("**Uploaded test image**")
            st.markdown('<div class="image-frame">', unsafe_allow_html=True)
            st.image(uploaded_file, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with right:
            with st.expander("Optional: coin calibration for font-size check"):
                st.caption("Place an Indian coin next to the label before taking the photo. Click its left and right edges to calibrate pixels/mm.")
                use_calibration = st.checkbox("I included a coin in this image")
                coin_left_x = coin_right_x = None
                coin_type = "₹5"
                if use_calibration:
                    coin_type = st.selectbox("Coin type", ["₹5","₹1","₹2","₹10"])
                    if HAS_CLICK_SUPPORT:
                        image_for_click = Image.open(io.BytesIO(uploaded_file.getvalue()))
                        if "coin_clicks" not in st.session_state: st.session_state["coin_clicks"] = []
                        click = streamlit_image_coordinates(image_for_click, key="coin_click_img")
                        if click is not None:
                            last = st.session_state.get("_last_click")
                            if click != last:
                                st.session_state["_last_click"] = click
                                st.session_state["coin_clicks"].append(click["x"])
                                st.session_state["coin_clicks"] = st.session_state["coin_clicks"][-2:]
                        if len(st.session_state["coin_clicks"]) == 2:
                            coin_left_x, coin_right_x = sorted(st.session_state["coin_clicks"])
                            st.success(f"Coin edges: {coin_left_x}px → {coin_right_x}px")
                        else: st.info(f"Clicks: {len(st.session_state['coin_clicks'])}/2")
                        if st.button("Reset coin marks"): st.session_state["coin_clicks"]=[]; st.rerun()
                    else:
                        st.warning("Click support is not installed; use manual pixel values or skip calibration.")
                        coin_left_x = st.number_input("Coin left edge (px)", min_value=0, value=0)
                        coin_right_x = st.number_input("Coin right edge (px)", min_value=0, value=100)
            if st.button("🔍 Run Compliance Check", type="primary", use_container_width=True):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                data = {"coin_left_x":coin_left_x,"coin_right_x":coin_right_x,"coin_type":coin_type} if use_calibration else {}
                with st.spinner("Checking image → fast OCR → rules engine → report data..."):
                    try:
                        r = api_post("/scan", files=files, data=data, timeout=60)
                        if r.status_code == 200:
                            st.session_state["last_scan_result"] = r.json()
                            st.session_state["last_upload_name"] = uploaded_file.name
                            st.success("Inspection completed. The uploaded image has been checked and saved as evidence.")
                        else: st.error(r.text)
                    except requests.Timeout:
                        st.error("The OCR scan timed out. The first EasyOCR run can take longer while its model loads; check the backend terminal for [OCR] timing. Retry once the model is loaded.")
                    except requests.RequestException as e: st.error(f"Backend error: {e}")

    if st.session_state.get("last_scan_result"):
        result = st.session_state["last_scan_result"]
        st.divider()
        st.markdown('<div class="section-title">2. Compliance Result</div>', unsafe_allow_html=True)
        # Show the exact uploaded image again beside the score.
        cimg,cres = st.columns([1.1,1.4])
        with cimg:
            try:
                img_resp = api_get(f"/image/{result['scan_id']}", timeout=15)
                if img_resp.status_code == 200: st.image(img_resp.content, caption="Evidence image used for this report", use_container_width=True)
            except requests.RequestException: pass
        with cres:
            show_result(result, "latest")
        download_reports(result["scan_id"], "latest_report")

# ---------------- TEST IMAGES ----------------
elif page == "Test Images":
    st.markdown('<div class="section-title">2. Test Images (examples)</div>', unsafe_allow_html=True)
    st.write("Run the included sample labels through the same upload/check pipeline. These are synthetic test images, not official packaging.")
    samples = [
        ("compliant_label.png","Compliant Label"),("missing_mrp.png","Missing MRP"),
        ("missing_consumer_care.png","Missing Consumer Care"),("blurred_label.png","Blurred Label")]
    cols = st.columns(2)
    for col,(filename,title) in zip(cols*2,samples):
        path = TEST_IMAGES_DIR/filename
        with col:
            if path.exists():
                st.markdown(f"### {title}")
                st.image(str(path), use_container_width=True)
                st.caption(filename)
            else: st.warning(f"Missing {filename}")

# ---------------- REPORTS ----------------
elif page == "Reports":
    st.markdown('<div class="section-title">3. Report Export (PDF / Word)</div>', unsafe_allow_html=True)
    try:
        history = api_get("/history").json()
    except Exception:
        history = []
    if not history:
        st.info("No generated reports yet. Run a compliance check first.")
    for h in history:
        with st.expander(f"Report #{h['id']} · {h['image_name']} · {h['overall_status']} · {h.get('compliance_score','N/A')}%"):
            c1,c2 = st.columns([1,2])
            with c1:
                try:
                    r = api_get(f"/image/{h['id']}", timeout=15)
                    if r.status_code == 200: st.image(r.content, use_container_width=True)
                except requests.RequestException: pass
            with c2:
                st.write(f"**Points:** {h.get('points_earned','N/A')} / {h.get('max_points','N/A')}")
                st.write(f"**Scanned by:** {h.get('scanned_by','N/A')}")
                st.write(f"**Time:** {h.get('scan_time','N/A')}")
                download_reports(h["id"], f"history_report_{h['id']}")

# ---------------- HISTORY ----------------
elif page == "History":
    st.markdown('<div class="section-title">Scan History</div>', unsafe_allow_html=True)
    c1,c2 = st.columns([2,1])
    q = c1.text_input("Search product / image name")
    status = c2.selectbox("Filter status", ["All","COMPLIANT","NON-COMPLIANT","EXEMPT"])
    params = ({"q":q} if q else {})
    if status != "All": params["status"] = status
    try:
        resp = api_get("/history", params=params)
        history = resp.json()
        a,b,c,d = st.columns(4)
        a.metric("Total Scans",len(history)); b.metric("Compliant",sum(x["overall_status"]=="COMPLIANT" for x in history)); c.metric("Non-Compliant",sum(x["overall_status"]=="NON-COMPLIANT" for x in history))
        scores=[x["compliance_score"] for x in history if x.get("compliance_score") is not None]; d.metric("Average Score",f"{sum(scores)/len(scores):.1f}%" if scores else "N/A")
        for h in history:
            with st.expander(f"{h['image_name']} · {h['overall_status']} · {h.get('compliance_score','N/A')}% · {h['scan_time'][:19]}"):
                c1,c2 = st.columns([1,2])
                with c1:
                    r=api_get(f"/image/{h['id']}",timeout=15)
                    if r.status_code==200: st.image(r.content, use_container_width=True)
                with c2:
                    st.markdown(status_badge(h["overall_status"]), unsafe_allow_html=True)
                    st.write(f"**Points:** {h.get('points_earned','N/A')} / {h.get('max_points','N/A')}")
                    st.write(f"**Scanned by:** {h.get('scanned_by','N/A')}")
                    checks=json.loads(h.get("checks_json") or "[]")
                    for check in checks: st.write(f"- {check['status']}: {check['field']} — {check['detail']}")
    except requests.RequestException:
        st.error("Backend not reachable.")

# ---------------- SETTINGS ----------------
elif page == "Settings":
    st.markdown('<div class="section-title">Application Settings</div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><h3>Inspection configuration</h3><p>This version uses local image-quality checks, OCR and the deterministic Legal Metrology rules engine. No external AI service is required.</p><p><b>OCR:</b> EasyOCR &nbsp; · &nbsp; <b>Compliance:</b> deterministic rules &nbsp; · &nbsp; <b>Reports:</b> PDF + editable Word</p></div>', unsafe_allow_html=True)
    st.info("For faster testing, use a clear, tightly cropped label image. The first OCR run may take longer while the OCR model loads; later scans are normally faster.")

# ---------------- ADMIN ----------------
elif page == "Admin Users":
    st.markdown('<div class="section-title">Admin: Manage Users</div>', unsafe_allow_html=True)
    with st.form("create_user_form"):
        new_username=st.text_input("New username"); new_password=st.text_input("New password",type="password"); new_role=st.selectbox("Role",["officer","admin"])
        if st.form_submit_button("Create user", type="primary"):
            try:
                r=api_post("/register",data={"username":new_username,"password":new_password,"role":new_role},timeout=15)
                if r.status_code==200: st.success(f"User '{new_username}' created.")
                else: st.error(r.json().get("detail","Could not create user."))
            except requests.RequestException: st.error("Backend not reachable.")
