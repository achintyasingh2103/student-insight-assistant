"""
pages/3_insights.py
Page 3 — Detailed insight report from Agent 2.
"""

import streamlit as st
from utils.helpers import archetype_emoji

st.set_page_config(page_title="Insights | Student Insight", page_icon="🧠", layout="wide")
st.title("🧠 Insight Report")

result = st.session_state.get("pipeline_results", {}).get(
    st.session_state.get("selected_student_id"))

if not result:
    st.info("👈 Go to Upload / Input and run an analysis first.")
    st.stop()

normalized = result["ingestion_result"]["normalized_data"]
insight = result["insight_result"]
name = normalized.get("name", "Student")

st.subheader(f"Analysis for {name}")

col1, col2, col3 = st.columns(3)
col1.metric("Behavioral Pattern", f"{archetype_emoji(insight.get('behavioral_pattern',''))} {insight.get('behavioral_pattern','—')}")
col2.metric("Learning Style", insight.get("learning_style", "—"))
col3.metric("Engagement Score", f"{insight.get('engagement_score', '—')}/10")

st.divider()

col_s, col_i = st.columns(2)

with col_s:
    st.markdown("### ✅ Top Strengths")
    for s in insight.get("top_strengths", []):
        st.success(f"• {s}")

with col_i:
    st.markdown("### 🌱 Growth Opportunities")
    for a in insight.get("improvement_areas", []):
        st.warning(f"• {a}")

st.divider()
st.markdown("### 🔍 Key Observation")
st.info(insight.get("key_observation", "—"))

confidence = insight.get("confidence_level", "—")
if isinstance(confidence, dict):
    conf_text = f"{confidence.get('level','—')} — {confidence.get('reasoning','')}"
else:
    conf_text = str(confidence)

st.markdown("### 💡 Confidence Assessment")
st.markdown(conf_text)

if insight.get("_validation_issues"):
    with st.expander("⚠️ Guardrails validation notes"):
        for issue in insight["_validation_issues"]:
            st.caption(f"• {issue}")
