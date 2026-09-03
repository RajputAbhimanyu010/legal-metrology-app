"""
Frontend — Starter for: Ashish (upload/results) & Shikhar (dashboard)
Purpose: A simple Streamlit UI so the team has a working demo screen
         fast, without needing React. Extend/replace as needed.

Run with:
    streamlit run frontend/app.py

Make sure the backend is running first:
    uvicorn backend.main:app --reload
"""

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Legal Metrology Compliance Checker", layout="wide")
st.title("📦 Legal Metrology Compliance Checker")

tab1, tab2 = st.tabs(["Scan a Product", "Dashboard / History"])

# ---------------- TAB 1: Upload + Scan ----------------
with tab1:
    st.subheader("Upload a product label image")
    uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Uploaded label", width=300)

        if st.button("Run Compliance Check"):
            with st.spinner("Scanning label..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                response = requests.post(f"{API_URL}/scan", files=files)

            if response.status_code == 200:
                result = response.json()
                st.success(f"Overall Status: {result['overall_status']} — Score: {result['compliance_score']}%")

                st.write("### Checklist")
                for check in result["checks"]:
                    icon = "✅" if check["status"] == "PASS" else ("⚠️" if check["status"] == "WARN" else "❌")
                    st.write(f"{icon} **{check['field']}** — {check['detail']}")

                st.write("### Raw Extracted Text")
                st.text(result["extracted_text"])

                if st.button("Generate PDF Report"):
                    r = requests.get(f"{API_URL}/report/{result['scan_id']}")
                    st.write("Report saved at:", r.json().get("pdf_path"))
            else:
                st.error("Something went wrong. Is the backend running?")

# ---------------- TAB 2: Dashboard ----------------
with tab2:
    st.subheader("Scan History")
    try:
        history = requests.get(f"{API_URL}/history").json()
        if history:
            st.dataframe(history)

            violation_count = sum(1 for h in history if h["overall_status"] == "NON-COMPLIANT")
            st.metric("Total Scans", len(history))
            st.metric("Non-Compliant Products", violation_count)
        else:
            st.info("No scans yet — go scan a product in the first tab.")
    except requests.exceptions.ConnectionError:
        st.error("Backend not reachable. Run: uvicorn backend.main:app --reload")
