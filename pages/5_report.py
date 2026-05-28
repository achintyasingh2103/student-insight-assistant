"""
pages/5_report.py
Page 5 — Full narrative report from Agent 4 with PDF download.
"""

import streamlit as st
from reports.pdf_generator import generate_pdf

st.set_page_config(page_title="Report | Student Insight", page_icon="📄", layout="wide")
st.title("📄 Full Report & PDF Download")

result = st.session_state.get("pipeline_results", {}).get(
    st.session_state.get("selected_student_id"))

if not result:
    st.info("👈 Go to Upload / Input and run an analysis first.")
    st.stop()

normalized = result["ingestion_result"]["normalized_data"]
insight = result["insight_result"]
career = result["career_result"]
report = result["report_result"]
name = normalized.get("name", "Student")

st.subheader(f"Full report: {name}")

# ── Narrative sections ────────────────────────────────────────────────────────
st.markdown("### Executive Summary")
st.info(report.get("executive_summary", "—"))

col1, col2 = st.columns(2)
with col1:
    st.markdown("### Academic Analysis")
    st.write(report.get("academic_analysis", "—"))
with col2:
    st.markdown("### Personal Development")
    st.write(report.get("personal_development", "—"))

st.markdown("### Counselor Notes")
st.warning(report.get("counselor_notes", "—"))

st.markdown("### Message for Parents")
st.success(report.get("parent_message", "—"))

st.markdown("### Recommended Action Plan")
for i, action in enumerate(report.get("action_plan", []), 1):
    st.markdown(f"**{i}.** {action}")

st.divider()

# ── PDF Download buttons ──────────────────────────────────────────────────────
st.markdown("### 📥 Download PDF Report")
col_t, col_p = st.columns(2)

with col_t:
    if st.button("Generate Teacher Edition PDF"):
        with st.spinner("Generating PDF..."):
            try:
                pdf_bytes = generate_pdf(
                    student_data=normalized,
                    insight=insight,
                    career=career,
                    report=report,
                    audience="teacher",
                )
                st.download_button(
                    label="⬇️ Download Teacher Report",
                    data=pdf_bytes,
                    file_name=f"{name.replace(' ', '_')}_teacher_report.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"PDF generation failed: {e}")

with col_p:
    if st.button("Generate Parent Edition PDF"):
        with st.spinner("Generating PDF..."):
            try:
                pdf_bytes = generate_pdf(
                    student_data=normalized,
                    insight=insight,
                    career=career,
                    report=report,
                    audience="parent",
                )
                st.download_button(
                    label="⬇️ Download Parent Report",
                    data=pdf_bytes,
                    file_name=f"{name.replace(' ', '_')}_parent_report.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"PDF generation failed: {e}")

if report.get("_validation_issues"):
    with st.expander("⚠️ Guardrails notes"):
        for issue in report["_validation_issues"]:
            st.caption(f"• {issue}")
