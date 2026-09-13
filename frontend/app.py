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
:root { --navy:#123f7a; --navy2:#0d315e; --blue:#2f75c8; --green:#25a66a; --red:#e64b4b; --amber:#e7a625; --purple:#7650d9; --ink:#17365d; --muted:#667085; --line:#d8e3ef; --soft:#f5f9fd; }
.stApp { background: linear-gradient(180deg,#f7fbff 0%,#ffffff 45%); color:var(--ink); }
[data-testid="stSidebar"] { background: linear-gradient(180deg,#0b203d 0%,#102d51 100%); }
[data-testid="stSidebar"] * { color:#fff !important; }
.block-container { padding-top:1rem; max-width:1400px; }
.hero { background:linear-gradient(90deg,#0e3b72,#145a9c); color:white; padding:16px 24px; border-radius:9px; box-shadow:0 4px 16px rgba(18,63,122,.16); margin-bottom:16px; }
.hero h1 { font-size:28px; margin:0; color:white; }
.hero p { margin:4px 0 0; opacity:.88; }
.card { background:white; border:1px solid var(--line); border-radius:9px; padding:18px; box-shadow:0 2px 9px rgba(18,63,122,.06); height:100%; }
.card h3 { color:var(--navy); font-size:17px; margin:0 0 8px; }
.card p,.card li { color:#44546a; font-size:14px; }
.section-title { color:var(--navy); font-weight:750; font-size:20px; margin:10px 0; }
.badge { display:inline-block; padding:5px 10px; border-radius:20px; font-weight:700; font-size:12px; }
.badge-green { background:#e9f8ef; color:#16854f; } .badge-red { background:#fff0f0; color:#c73535; } .badge-amber { background:#fff7e6; color:#a46b00; }
.score-ring { border:7px solid #25a66a; width:130px; height:130px; border-radius:50%; display:flex; flex-direction:column; align-items:center; justify-content:center; margin:auto; background:#f6fffa; }
.score-ring b { font-size:29px; color:#16854f; } .score-ring span { color:#607083; font-size:12px; }
.small-muted { color:#667085; font-size:12px; }
.check-row { border:1px solid var(--line); border-radius:8px; padding:9px 12px; margin:6px 0; background:#fff; }
.image-frame { border:1px solid var(--line); border-radius:8px; padding:6px; background:#fff; }
[data-testid="stMetric"] { background:white; border:1px solid var(--line); padding:10px 12px; border-radius:8px; }
button[kind="primary"] { background:#1469b8; }
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
            st.markdown(f'<div class="score-ring"><b>{score}</b><span>/ 100 points</span></div>', unsafe_allow_html=True)
        else:
            st.info("Score not applicable")
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

    st.markdown('<div class="section-title">OCR / AI Extraction</div>', unsafe_allow_html=True)
    st.text_area("Extracted text used by the rules engine", result.get("extracted_text", ""), height=150, key=f"ocr_{key_prefix}")
    if result.get("ai_extracted_text"):
        with st.expander("AI vision extraction"):
            st.text(result["ai_extracted_text"])
    ai = result.get("ai_analysis") or {}
    if ai.get("analysis"):
        with st.expander("AI visual review & recommendations"):
            analysis = ai["analysis"]
            if isinstance(analysis, dict):
                if analysis.get("product_name") or analysis.get("brand"):
                    st.write(f"**Product/Brand:** {analysis.get('product_name','')} {analysis.get('brand','')}")
                for label in ["visible_declarations", "possible_issues", "recommendations", "tamper_or_editing_signals"]:
                    values = analysis.get(label)
                    if values:
                        st.write(f"**{label.replace('_',' ').title()}**")
                        for value in values if isinstance(values, list) else [values]:
                            st.write(f"- {value}")
                if analysis.get("label_readability"):
                    st.write(f"**AI readability:** {analysis['label_readability']}")
            else:
                st.code(str(analysis))


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
    st.markdown('<div class="hero"><h1>Legal Metrology Compliance Checker</h1><p>AI-assisted packaged commodity compliance inspection</p></div>', unsafe_allow_html=True)
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
    st.caption(f"Welcome, {st.session_state['username']} · {st.session_state['role']}")
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
    st.markdown('<div class="section-title">AI-assisted packaged commodity inspection</div>', unsafe_allow_html=True)
    st.write("Upload a label photo, check the actual image quality, extract declarations using OCR + optional AI vision, evaluate deterministic Legal Metrology rules, and export evidence-ready PDF/Word reports.")
    cards = [
        ("🧠", "Improved OCR", ["Multiple preprocessing passes", "Noise reduction & contrast enhancement", "Upscaling for small text", "Duplicate detection removal"]),
        ("✦", "AI Integration (Optional)", ["Local Ollama + Gemma vision", "Optional Gemini REST provider", "AI extraction + visual review", "AI kept separate for audit"]),
        ("⌂", "Home / Workflow", ["Upload → Check → Analyze", "Image quality pre-check", "Deterministic scoring", "Evidence-first reporting"]),
        ("▧", "Test Images", ["Compliant sample", "Missing MRP", "Missing consumer care", "Blurred label"]),
        ("▤", "Reports", ["PDF + editable Word", "Original test image included", "Points scored", "Detailed analysis & recommendations"]),
    ]
    row = st.columns(5)
    for col, (icon,title,items) in zip(row,cards):
        with col:
            st.markdown(f'<div class="card"><h3>{icon} {title}</h3><ul>{"".join(f"<li>{x}</li>" for x in items)}</ul></div>', unsafe_allow_html=True)
    st.markdown("### Recommended workflow")
    c1,c2,c3,c4 = st.columns(4)
    for col, n, title, text in [(c1,"1","Upload","Choose the product-label image."),(c2,"2","Check","Run image quality + OCR + AI vision."),(c3,"3","Analyze","Review PASS/WARN/FAIL and score."),(c4,"4","Export","Download PDF/Word with image evidence.")]:
        col.markdown(f'<div class="card"><h3>{n}. {title}</h3><p>{text}</p></div>', unsafe_allow_html=True)

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
                with st.spinner("Checking image → OCR → AI vision → rules engine → report data..."):
                    try:
                        r = api_post("/scan", files=files, data=data, timeout=180)
                        if r.status_code == 200:
                            st.session_state["last_scan_result"] = r.json()
                            st.session_state["last_upload_name"] = uploaded_file.name
                            st.success("Inspection completed. The uploaded image has been checked and saved as evidence.")
                        else: st.error(r.text)
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
    st.markdown('<div class="section-title">Settings & AI Configuration</div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><h3>AI architecture</h3><p><b>OCR:</b> EasyOCR + preprocessing ensemble. <b>Vision AI:</b> optional Ollama/Gemma and optional Gemini REST. <b>Compliance:</b> deterministic rules engine. <b>Reports:</b> original evidence image + points + analysis.</p><p>AI suggestions are advisory and remain separate from the legal rules used for the final score.</p></div>', unsafe_allow_html=True)
    st.code("AI_OCR_ENABLED=true\nOLLAMA_URL=http://127.0.0.1:11434\nOLLAMA_MODEL=gemma3:4b\nGEMINI_ENABLED=false\nGEMINI_API_KEY=...\nGEMINI_MODEL=gemini-2.5-flash", language="bash")
    st.info("For a privacy-first demo, keep Gemini disabled and run Ollama locally. For production/legal use, verify the current Legal Metrology rules and independently review AI findings.")

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
