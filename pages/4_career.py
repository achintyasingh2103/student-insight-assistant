"""
pages/4_career.py
Page 4 — Career Compass showing RAG-grounded recommendations from Agent 3.
"""

import streamlit as st

st.set_page_config(page_title="Career Compass | Student Insight", page_icon="🧭", layout="wide")
st.title("🧭 Career Compass")

result = st.session_state.get("pipeline_results", {}).get(
    st.session_state.get("selected_student_id"))

if not result:
    st.info("👈 Go to Upload / Input and run an analysis first.")
    st.stop()

normalized = result["ingestion_result"]["normalized_data"]
career = result["career_result"]
name = normalized.get("name", "Student")

st.subheader(f"Career pathways for {name}")
st.info(career.get("overall_career_note", "—"))
st.divider()

recs = career.get("career_recommendations", [])
if not recs:
    st.warning("No career recommendations available.")
    st.stop()

for i, rec in enumerate(recs, 1):
    with st.expander(f"🎯 Path {i}: {rec.get('career_path', '—')}", expanded=(i == 1)):
        st.markdown(f"**Why this suits {name}:**")
        st.write(rec.get("why_suited", "—"))

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Next steps:**")
            for step in rec.get("next_steps", []):
                st.markdown(f"• {step}")
        with col2:
            exams = rec.get("entrance_exams", [])
            if exams:
                st.markdown("**Relevant entrance exams:**")
                for exam in exams:
                    st.markdown(f"• {exam}")
            skill = rec.get("skill_to_develop", "")
            if skill:
                st.markdown(f"**Priority skill to build:** `{skill}`")

if career.get("_validation_issues"):
    with st.expander("⚠️ Guardrails notes"):
        for issue in career["_validation_issues"]:
            st.caption(f"• {issue}")
