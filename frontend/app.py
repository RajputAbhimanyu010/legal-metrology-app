"""
Frontend — Legal Metrology Compliance Checker
Covers: login, scan/results (Ashish), dashboard/history (Shikhar),
admin user management. Consolidated final version.

Run with:
    streamlit run frontend/app.py

Backend must be running first:
    uvicorn backend.main:app --reload

Default login: admin / admin123 (run `python backend/auth.py` once first).
"""

import requests
import streamlit as st
from collections import defaultdict
from PIL import Image
import io

try:
    from streamlit_image_coordinates import streamlit_image_coordinates
    HAS_CLICK_SUPPORT = True
except ImportError:
    HAS_CLICK_SUPPORT = False

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Legal Metrology Compliance Checker", layout="wide")


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


# ---------------- LOGIN GATE ----------------
if "token" not in st.session_state:
    st.title("Legal Metrology Compliance Checker")
    st.subheader("Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        try:
            resp = requests.post(f"{API_URL}/login", data={"username": username, "password": password})
            if resp.status_code == 200:
                data = resp.json()
                st.session_state["token"] = data["access_token"]
                st.session_state["username"] = data["username"]
                st.session_state["role"] = data["role"]
                st.rerun()
            else:
                st.error("Incorrect username or password.")
        except requests.exceptions.ConnectionError:
            st.error("Cannot reach the backend. Make sure `uvicorn backend.main:app --reload` is running.")

    st.caption(
        "First time running this? In a terminal run `python backend/auth.py` once "
        "to create the default admin account (admin / admin123)."
    )
    st.stop()


# ---------------- LOGGED IN ----------------
with st.sidebar:
    st.write(f"Logged in as **{st.session_state['username']}** ({st.session_state['role']})")
    if st.button("Log out"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

st.title("Legal Metrology Compliance Checker")

tab_labels = ["Scan a Product", "Dashboard / History", "Product History"]
if st.session_state["role"] == "admin":
    tab_labels.append("Admin: Manage Users")
tab_objs = st.tabs(tab_labels)
tab1, tab2, tab3 = tab_objs[0], tab_objs[1], tab_objs[2]

# ============================================================
# TAB 1: Scan a Product
# ============================================================
with tab1:
    st.subheader("Upload a product label image")
    uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        with st.expander("Optional: enable accurate Font Size check (place a coin in the photo)"):
            st.caption("Place an Indian coin next to the label BEFORE taking the photo (Rs 5 recommended).")
            use_calibration = st.checkbox("I included a coin in this photo")
            coin_left_x, coin_right_x, coin_type = None, None, "₹5"

            if use_calibration:
                coin_type = st.selectbox("Which coin did you use?", ["₹5", "₹1", "₹2", "₹10"])

                if HAS_CLICK_SUPPORT:
                    st.write("Click the LEFT edge of the coin, then the RIGHT edge, directly on the image below.")
                    if "coin_clicks" not in st.session_state:
                        st.session_state["coin_clicks"] = []

                    # streamlit_image_coordinates needs a PIL Image (or path/array),
                    # not the raw Streamlit UploadedFile object — convert it first.
                    pil_image_for_click = Image.open(io.BytesIO(uploaded_file.getvalue()))
                    click = streamlit_image_coordinates(pil_image_for_click, key="coin_click_img")

                    if click is not None:
                        last = st.session_state.get("_last_click")
                        if click != last:
                            st.session_state["_last_click"] = click
                            st.session_state["coin_clicks"].append(click["x"])
                            st.session_state["coin_clicks"] = st.session_state["coin_clicks"][-2:]

                    clicks = st.session_state["coin_clicks"]
                    if len(clicks) == 2:
                        coin_left_x, coin_right_x = min(clicks), max(clicks)
                        st.success(f"Coin edges marked: {coin_left_x}px to {coin_right_x}px")
                    else:
                        st.info(f"Clicks registered so far: {len(clicks)}/2")

                    if st.button("Reset coin clicks"):
                        st.session_state["coin_clicks"] = []
                        st.rerun()
                else:
                    st.warning(
                        "Click-to-mark is not installed. Run `pip install streamlit-image-coordinates` "
                        "and restart the app for this to work properly. Using manual number entry for now "
                        "(less accurate — or just skip calibration, it's optional)."
                    )
                    st.image(uploaded_file, caption="Uploaded label (for reference)", width=400)
                    col_a, col_b = st.columns(2)
                    with col_a:
                        coin_left_x = st.number_input("Coin LEFT edge (pixel x)", min_value=0, value=0)
                    with col_b:
                        coin_right_x = st.number_input("Coin RIGHT edge (pixel x)", min_value=0, value=100)
            else:
                st.image(uploaded_file, caption="Uploaded label", width=300)

        if use_calibration:
            st.image(uploaded_file, caption="Uploaded label", width=300)

        if st.button("Run Compliance Check", type="primary"):
            with st.spinner("Scanning label... (this can take a few seconds)"):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                data = {}
                if use_calibration:
                    data = {"coin_left_x": coin_left_x, "coin_right_x": coin_right_x, "coin_type": coin_type}
                try:
                    response = requests.post(f"{API_URL}/scan", files=files, data=data, headers=auth_headers(), timeout=120)
                    if response.status_code == 200:
                        st.session_state["last_scan_result"] = response.json()
                    elif response.status_code == 401:
                        st.error("Session expired. Please log out and log in again.")
                    else:
                        st.error(f"Something went wrong: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Cannot reach the backend. Make sure `uvicorn backend.main:app --reload` is running.")

        if "last_scan_result" in st.session_state:
            result = st.session_state["last_scan_result"]

            if result["overall_status"] == "EXEMPT":
                st.info(f"This product is EXEMPT from mandatory declarations - {result['checks'][0]['detail']}")
            else:
                status_color = "success" if result["overall_status"] == "COMPLIANT" else "error"
                getattr(st, status_color)(f"Overall Status: {result['overall_status']}")

                # ---- Score breakdown (what was asked for) ----
                st.write("### Compliance Score")
                col1, col2, col3 = st.columns(3)
                col1.metric("Score", f"{result['compliance_score']}%")
                col2.metric("Points Earned", f"{result['points_earned']} / {result['max_points']}")
                col3.metric("Fields Scored", result["total_checks_scored"])

                with st.expander("How is this score calculated?"):
                    for status, meaning in result["scoring_criteria"].items():
                        st.write(f"**{status}**: {meaning}")
                    st.caption(
                        "Score = (points earned across all scored fields) / (max possible points) x 100. "
                        "Fields marked INFO (not applicable to this product, e.g. Country of Origin on a "
                        "domestic product) are not counted toward the score either way."
                    )

            st.write("### Checklist")
            for check in result["checks"]:
                label = f"**[{check['status']}] {check['field']}** - {check['detail']}"
                if check["status"] == "PASS":
                    st.success(label, icon="✅")
                elif check["status"] == "WARN":
                    st.warning(label, icon="⚠️")
                elif check["status"] == "FAIL":
                    st.error(label, icon="❌")
                else:
                    st.info(label, icon="ℹ️")

            st.write("### Raw Extracted Text")
            st.text(result["extracted_text"])

            if result["overall_status"] != "EXEMPT":
                st.write("### Download Compliance Report")
                col_pdf, col_docx = st.columns(2)

                with col_pdf:
                    try:
                        r = requests.get(
                            f"{API_URL}/report/{result['scan_id']}",
                            params={"format": "pdf"}, headers=auth_headers(), timeout=30
                        )
                        if r.status_code == 200:
                            st.download_button(
                                "Download PDF Report", data=r.content,
                                file_name=f"compliance_report_{result['scan_id']}.pdf",
                                mime="application/pdf", key="pdf_dl"
                            )
                        else:
                            st.error("Could not generate PDF report.")
                    except requests.exceptions.ConnectionError:
                        st.error("Backend not reachable for report generation.")

                with col_docx:
                    try:
                        r = requests.get(
                            f"{API_URL}/report/{result['scan_id']}",
                            params={"format": "docx"}, headers=auth_headers(), timeout=30
                        )
                        if r.status_code == 200:
                            st.download_button(
                                "Download Editable Word Report (.docx)", data=r.content,
                                file_name=f"compliance_report_{result['scan_id']}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key="docx_dl"
                            )
                        else:
                            st.error("Could not generate Word report.")
                    except requests.exceptions.ConnectionError:
                        st.error("Backend not reachable for report generation.")

                st.caption(
                    "The Word (.docx) report is fully editable in Microsoft Word / Google Docs "
                    "(text, table, notes field). The PDF is a fixed, final-format version for official records."
                )

# ============================================================
# TAB 2: Dashboard / History (flat list, all scans)
# ============================================================
with tab2:
    st.subheader("Scan History")

    col_search, col_status = st.columns([2, 1])
    with col_search:
        search_query = st.text_input("Search by product/image name", key="dash_search")
    with col_status:
        status_filter = st.selectbox("Filter by status", ["All", "COMPLIANT", "NON-COMPLIANT", "EXEMPT"], key="dash_status")

    params = {}
    if search_query:
        params["q"] = search_query
    if status_filter != "All":
        params["status"] = status_filter

    try:
        resp = requests.get(f"{API_URL}/history", params=params, headers=auth_headers(), timeout=30)
        if resp.status_code == 401:
            st.error("Session expired. Please log out and log in again.")
        else:
            history = resp.json()
            if history:
                total_scans = len(history)
                violation_count = sum(1 for h in history if h["overall_status"] == "NON-COMPLIANT")
                compliant_count = sum(1 for h in history if h["overall_status"] == "COMPLIANT")
                avg_score = sum(h["compliance_score"] for h in history if h["compliance_score"] is not None) / max(
                    1, sum(1 for h in history if h["compliance_score"] is not None)
                )

                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("Total Scans", total_scans)
                col_b.metric("Compliant", compliant_count)
                col_c.metric("Non-Compliant", violation_count)
                col_d.metric("Average Score", f"{avg_score:.1f}%")

                st.write("---")

                for h in history:
                    with st.expander(f"{h['image_name']} - {h['overall_status']} - Score: {h.get('compliance_score', 'N/A')}% ({h['scan_time'][:19]})"):
                        col_img, col_info = st.columns([1, 2])
                        with col_img:
                            try:
                                img_resp = requests.get(f"{API_URL}/image/{h['id']}", headers=auth_headers(), timeout=10)
                                if img_resp.status_code == 200:
                                    st.image(img_resp.content, caption="Evidence photo", width=200)
                            except requests.exceptions.ConnectionError:
                                pass
                        with col_info:
                            st.write(f"**Scanned by:** {h.get('scanned_by', 'N/A')}")
                            st.write(f"**Scan time:** {h['scan_time']}")
                            st.write(f"**Score:** {h.get('compliance_score', 'N/A')}%")
                            st.write(f"**Status:** {h['overall_status']}")
            else:
                st.info("No scans found matching your search/filter.")
    except requests.exceptions.ConnectionError:
        st.error("Backend not reachable. Run: uvicorn backend.main:app --reload")

# ============================================================
# TAB 3: Product History (grouped — full history of ONE product)
# ============================================================
with tab3:
    st.subheader("View full history of a specific product")
    st.caption(
        "See every past scan of the same product over time — useful for spotting "
        "whether a manufacturer fixed a violation after a previous inspection."
    )

    try:
        all_history = requests.get(f"{API_URL}/history", headers=auth_headers(), timeout=30).json()
        product_names = sorted(set(h["image_name"] for h in all_history)) if all_history else []
    except requests.exceptions.ConnectionError:
        product_names = []
        st.error("Backend not reachable.")

    if product_names:
        selected_product = st.selectbox("Select a product", product_names)

        if selected_product:
            try:
                resp = requests.get(f"{API_URL}/history/product/{selected_product}", headers=auth_headers(), timeout=30)
                product_scans = resp.json()

                if product_scans:
                    st.write(f"### {selected_product} — {len(product_scans)} scan(s) on record")

                    scores = [s["compliance_score"] for s in product_scans if s["compliance_score"] is not None]
                    if scores:
                        col_a, col_b, col_c = st.columns(3)
                        col_a.metric("First Score", f"{scores[0]}%")
                        col_b.metric("Latest Score", f"{scores[-1]}%")
                        trend = "Improved" if scores[-1] > scores[0] else ("Declined" if scores[-1] < scores[0] else "No change")
                        col_c.metric("Trend", trend)

                    for i, s in enumerate(product_scans, 1):
                        with st.expander(f"Scan #{i} - {s['scan_time'][:19]} - {s['overall_status']} ({s.get('compliance_score', 'N/A')}%)"):
                            st.write(f"**Scanned by:** {s.get('scanned_by', 'N/A')}")
                            import json as _json
                            checks = _json.loads(s["checks_json"])
                            for c in checks:
                                st.write(f"- [{c['status']}] {c['field']}: {c['detail']}")
                else:
                    st.info("No scans found for this product.")
            except requests.exceptions.ConnectionError:
                st.error("Backend not reachable.")
    else:
        st.info("No scans yet. Go scan a product in the first tab.")

# ============================================================
# TAB 4 (admin only): Manage Users
# ============================================================
if st.session_state["role"] == "admin" and len(tab_objs) > 3:
    with tab_objs[3]:
        st.subheader("Create a new user")
        with st.form("create_user_form"):
            new_username = st.text_input("New username")
            new_password = st.text_input("New password", type="password")
            new_role = st.selectbox("Role", ["officer", "admin"])
            create_submitted = st.form_submit_button("Create user")

        if create_submitted:
            try:
                r = requests.post(
                    f"{API_URL}/register",
                    data={"username": new_username, "password": new_password, "role": new_role},
                    headers=auth_headers(), timeout=10
                )
                if r.status_code == 200:
                    st.success(f"User '{new_username}' created with role '{new_role}'.")
                else:
                    st.error(r.json().get("detail", "Could not create user."))
            except requests.exceptions.ConnectionError:
                st.error("Backend not reachable.")
